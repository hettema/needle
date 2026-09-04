"""The HTTP API. Thin: every route reads or writes through `Live`, the doors
or the loops and returns a domain type. A move is persisted before the
response is built, and a failure is returned with the store's own words so
the page can show it on the card. A door that does not open answers 409
with its reason; a door the machine failed answers 502 with the machine's
words. Sessions push their events to `/api/hooks`.
"""

import asyncio
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from api.doors import DoorFailed, DoorRefused, Doors
from api.loops import Loops
from domain.board import BoardState, CardDetail, ProjectFile
from domain.card import Move
from domain.hook import HookEvent, HookPosted
from domain.lane import DoorResult
from domain.project import Project
from infrastructure import clock
from infrastructure.live import Live
from infrastructure.paths import db_path
from infrastructure.store import Store, StoreRefusal
from runtime.service import Runtime

STREAM_KEEPALIVE_SECONDS = 15.0


class StoreFailure(Exception):
    """A write failed for a reason the store did not choose; the page shows the words."""


class Answer(BaseModel):
    text: str


class StartBody(BaseModel):
    anyway: bool = False


class SignalAnswer(BaseModel):
    delivered: bool


class HooksReceived(BaseModel):
    received: int
    attributed: int
    """How many of them landed on a card of a registered project."""


async def board_events(
    live: Live, is_disconnected: Callable[[], Awaitable[bool]], keepalive: float
) -> AsyncIterator[str]:
    """The stream: the version now, then a new version each time the board changes.

    The page refetches on each event; the stream never carries the state, so
    there is one serialisation of the truth and it is the board endpoint's.
    """
    version = live.version
    yield f"event: board\ndata: {json.dumps({'version': version})}\n\n"
    while not live.closing and not await is_disconnected():
        latest = await live.wait_for_change(version, keepalive)
        if latest > version:
            version = latest
            yield f"event: board\ndata: {json.dumps({'version': version})}\n\n"
        else:
            yield ": keep-alive\n\n"


REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"


def create_app(store: Store | None = None, *, dist: Path | None = FRONTEND_DIST) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        owned = store is None
        live = Live(store or Store(db_path()))
        live.load()
        await live.start_watching()
        runtime = Runtime(live.store)
        loops = Loops(live, runtime)
        app.state.live = live
        app.state.loops = loops
        app.state.doors = Doors(live, runtime, loops)
        await loops.start()
        await loops.first_read()
        try:
            yield
        finally:
            await loops.stop()
            await live.stop()
            if owned:
                live.store.close()

    app = FastAPI(title="Needle", lifespan=lifespan)

    def live_of(request: Request) -> Live:
        return request.app.state.live

    async def live_for(request: Request, slug: str) -> Live:
        """The board, with the project list re-read if this slug is unknown: a
        deep link to a project registered a moment ago must not 409."""
        live = live_of(request)
        if slug not in live.projects:
            await live.sync_projects()
        return live

    @app.exception_handler(StoreRefusal)
    async def refused(request: Request, error: StoreRefusal) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(error)})

    @app.exception_handler(StoreFailure)
    async def failed(request: Request, error: StoreFailure) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": str(error)})

    @app.exception_handler(DoorRefused)
    async def door_refused(request: Request, error: DoorRefused) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(error)})

    @app.exception_handler(DoorFailed)
    async def door_failed(request: Request, error: DoorFailed) -> JSONResponse:
        return JSONResponse(status_code=502, content={"detail": str(error)})

    async def through_door(request: Request, slug: str, work: Callable[[Doors], DoorResult]):
        """A door runs off the loop's thread and under the loops' lock, so a
        door and a machine read never act on the same lane at once."""
        await live_for(request, slug)
        loops: Loops = request.app.state.loops
        doors: Doors = request.app.state.doors
        async with loops.lock:
            return await asyncio.to_thread(work, doors)

    @app.get("/api/projects", response_model=list[Project])
    async def projects(request: Request) -> list[Project]:
        live = live_of(request)
        await live.sync_projects()
        return [p.project for p in live.projects.values()]

    @app.get("/api/projects/{slug}/board", response_model=BoardState)
    async def board(slug: str, request: Request) -> BoardState:
        return (await live_for(request, slug)).board(slug)

    @app.get("/api/projects/{slug}/cards/{number}", response_model=CardDetail)
    async def card(slug: str, number: int, request: Request) -> CardDetail:
        return (await live_for(request, slug)).detail(slug, number)

    @app.post("/api/projects/{slug}/cards/{number}/move", response_model=BoardState)
    async def move(slug: str, number: int, body: Move, request: Request) -> BoardState:
        live = await live_for(request, slug)
        try:
            return live.move(slug, number, body.to)
        except StoreRefusal:
            raise
        except Exception as error:  # noqa: BLE001 — shown on the card, never hidden
            raise StoreFailure(f"The store refused: {type(error).__name__}: {error}") from error

    @app.post("/api/projects/{slug}/cards/{number}/start", response_model=DoorResult)
    async def start(slug: str, number: int, body: StartBody, request: Request) -> DoorResult:
        return await through_door(
            request, slug, lambda doors: doors.start(slug, number, anyway=body.anyway)
        )

    @app.post("/api/projects/{slug}/cards/{number}/answer", response_model=DoorResult)
    async def answer(slug: str, number: int, body: Answer, request: Request) -> DoorResult:
        return await through_door(
            request, slug, lambda doors: doors.answer(slug, number, body.text)
        )

    @app.post("/api/projects/{slug}/cards/{number}/watch", response_model=DoorResult)
    async def watch(slug: str, number: int, request: Request) -> DoorResult:
        return await through_door(request, slug, lambda doors: doors.watch(slug, number))

    @app.post("/api/projects/{slug}/cards/{number}/look", response_model=DoorResult)
    async def look(slug: str, number: int, request: Request) -> DoorResult:
        return await through_door(request, slug, lambda doors: doors.look(slug, number))

    @app.post("/api/projects/{slug}/cards/{number}/discuss", response_model=DoorResult)
    async def discuss(slug: str, number: int, request: Request) -> DoorResult:
        return await through_door(request, slug, lambda doors: doors.discuss(slug, number))

    @app.post("/api/projects/{slug}/cards/{number}/resume", response_model=DoorResult)
    async def resume(slug: str, number: int, request: Request) -> DoorResult:
        return await through_door(request, slug, lambda doors: doors.resume(slug, number))

    @app.post("/api/projects/{slug}/cards/{number}/stop", response_model=DoorResult)
    async def stop(slug: str, number: int, request: Request) -> DoorResult:
        return await through_door(request, slug, lambda doors: doors.stop(slug, number))

    @app.post("/api/projects/{slug}/cards/{number}/signal", response_model=DoorResult)
    async def signal(slug: str, number: int, body: SignalAnswer, request: Request) -> DoorResult:
        return await through_door(
            request, slug, lambda doors: doors.signal(slug, number, delivered=body.delivered)
        )

    @app.get("/api/projects/{slug}/cards/{number}/brief", response_class=PlainTextResponse)
    async def brief(slug: str, number: int, request: Request) -> str:
        live = await live_for(request, slug)
        doors: Doors = request.app.state.doors
        return doors.brief_for_lane(live.detail(slug, number), slug, overrode=None)

    @app.post("/api/hooks", response_model=HooksReceived)
    async def hooks(body: list[HookPosted], request: Request) -> HooksReceived:
        """What sessions push. Every event is kept; the ones inside a lane of
        a registered project move the board."""
        live = live_of(request)
        await live.sync_projects()
        loops: Loops = request.app.state.loops
        recorded: list[HookEvent] = await loops.hooks(body)
        return HooksReceived(
            received=len(recorded),
            attributed=sum(1 for e in recorded if e.card_number is not None),
        )

    @app.get("/api/projects/{slug}/files", response_model=ProjectFile)
    async def file(slug: str, path: str, request: Request) -> ProjectFile:
        live = await live_for(request, slug)
        project = live.projects.get(slug)
        if project is None:
            raise StoreRefusal(f'No project "{slug}" is on the board.')
        root = Path(project.project.path).resolve()
        if not path.startswith("docs/") or not path.endswith(".md") or ".." in path.split("/"):
            raise HTTPException(
                status_code=400, detail="Only markdown under the project's docs/ can be read."
            )
        target = (root / path).resolve()
        if not target.is_relative_to(root / "docs") or not target.is_file():
            raise HTTPException(status_code=404, detail=f"{path} is not in this project.")
        return ProjectFile(
            path=path,
            text=target.read_text(encoding="utf-8", errors="replace"),
            read_at=clock.now(),
        )

    @app.get("/api/projects/{slug}/stream")
    async def stream(slug: str, request: Request) -> StreamingResponse:
        live = await live_for(request, slug)
        if slug not in live.projects:
            raise StoreRefusal(f'No project "{slug}" is on the board.')

        return StreamingResponse(
            board_events(live, request.is_disconnected, STREAM_KEEPALIVE_SECONDS),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    if dist is not None and (dist / "index.html").is_file():
        index = dist / "index.html"

        # The page reads the project from the path (`/p/<slug>`), so a deep
        # link and a reload on a second project have to get the same page as
        # `/` does. StaticFiles alone answered them with 404 — found the
        # morning Needle was registered as its own second project and had no
        # way onto the screen (2026-09-04).
        @app.get("/p/{slug}", response_class=FileResponse, include_in_schema=False)
        async def project_page(slug: str) -> FileResponse:
            return FileResponse(index, media_type="text/html")

        app.mount("/", StaticFiles(directory=dist, html=True), name="page")
    else:

        @app.get("/", response_class=PlainTextResponse)
        async def no_page() -> str:
            return (
                "Needle's API is up but the page is not built.\n"
                "Run: cd frontend && npm ci && npm run build\n"
                "then start the server again.\n"
            )

    return app
