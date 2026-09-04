"""A real pointer drag on a running board, driven through Chromium's DevTools protocol.

jsdom cannot lay out a page, so the pointer path of drag-and-drop — the one
the owner uses most — cannot be exercised by the vitest suite. This drives
headless Chromium against a live server: press on the second card of a ranked
column, move to the top of the first, read the gap's words, release, and read
the order the store answered with. Run it before a review record that claims
"a dropped card lands where the preview said".

    uv run python tools/drag_check.py http://127.0.0.1:8480/ "Up next" /tmp/drag.png
"""

import asyncio
import base64
import json
import subprocess
import sys
import time
import urllib.request

import websockets

PORT = 9341


async def call(
    ws: websockets.ClientConnection, counter: list[int], method: str, **params: object
) -> dict:
    counter[0] += 1
    await ws.send(json.dumps({"id": counter[0], "method": method, "params": params}))
    while True:
        message = json.loads(await ws.recv())
        if message.get("id") == counter[0]:
            return message.get("result", {})


async def check(url: str, column: str, screenshot: str) -> int:
    chromium = subprocess.Popen(
        [
            "chromium",
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--hide-scrollbars",
            f"--remote-debugging-port={PORT}",
            "--window-size=1440,900",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        page = None
        for _ in range(50):
            try:
                targets = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json"))
                page = next(t for t in targets if t["type"] == "page")
                break
            except Exception:  # noqa: BLE001 — chromium is still starting
                time.sleep(0.2)
        if page is None:
            print("chromium did not come up")
            return 2
        counter = [0]
        async with websockets.connect(page["webSocketDebuggerUrl"], max_size=50_000_000) as ws:

            async def js(expression: str) -> object:
                result = await call(
                    ws, counter, "Runtime.evaluate", expression=expression, returnByValue=True
                )
                return result.get("result", {}).get("value")

            cards = f"document.querySelectorAll('[data-column=\"{column}\"] article[data-card]')"
            await call(
                ws,
                counter,
                "Emulation.setDeviceMetricsOverride",
                width=1440,
                height=900,
                deviceScaleFactor=1,
                mobile=False,
            )
            await call(ws, counter, "Page.navigate", url=url)
            for _ in range(60):
                if await js(f"{cards}.length >= 2"):
                    break
                await asyncio.sleep(0.25)
            before = await js(f"Array.from({cards}).map(e => e.dataset.card)")
            if not isinstance(before, list) or len(before) < 2:
                print(f"{column} has fewer than two cards on the page; nothing to drag")
                return 2
            src, dst = before[1], before[0]

            async def box(number: object) -> list[float]:
                rect = f"document.getElementById('card-{number}').getBoundingClientRect()"
                value = await js(
                    f"(() => {{ const r = {rect}; return [r.left, r.top, r.width, r.height]; }})()"
                )
                assert isinstance(value, list)
                return value

            sx, sy, sw, _sh = await box(src)
            dx, dy, dw, _dh = await box(dst)
            x0, y0 = sx + sw / 2, sy + 20
            tx, ty = dx + dw / 2, dy + 8
            await call(ws, counter, "Input.dispatchMouseEvent", type="mouseMoved", x=x0, y=y0)
            await call(
                ws,
                counter,
                "Input.dispatchMouseEvent",
                type="mousePressed",
                x=x0,
                y=y0,
                button="left",
                clickCount=1,
            )
            for i in range(1, 16):
                await call(
                    ws,
                    counter,
                    "Input.dispatchMouseEvent",
                    type="mouseMoved",
                    x=x0 + (tx - x0) * i / 15,
                    y=y0 + (ty - y0) * i / 15,
                    button="left",
                )
                await asyncio.sleep(0.04)
            await asyncio.sleep(0.4)
            gap = await js("(document.querySelector('.drop-gap .lands') || {}).textContent || null")
            shot = await call(ws, counter, "Page.captureScreenshot", format="png")
            with open(screenshot, "wb") as out:
                out.write(base64.b64decode(shot["data"]))
            await call(
                ws,
                counter,
                "Input.dispatchMouseEvent",
                type="mouseReleased",
                x=tx,
                y=ty,
                button="left",
                clickCount=1,
            )
            after = before
            for _ in range(40):
                await asyncio.sleep(0.1)
                after = await js(f"Array.from({cards}).map(e => e.dataset.card)")
                if after != before:
                    break
            failed = await js("!!document.querySelector('.card.failed')")
            print(f"before: {before}")
            print(f"gap:    {gap}")
            print(f"after:  {after}  failed-on-page: {failed}")
            print(f"shot:   {screenshot}")
            expected = [src, dst, *before[2:]]
            if gap is None or after != expected or failed:
                print("the drop did not land where the preview said")
                return 1
            print("the drop landed where the preview said")
            return 0
    finally:
        chromium.terminate()


def main() -> int:
    if len(sys.argv) != 4:
        print(__doc__)
        return 2
    return asyncio.run(check(sys.argv[1], sys.argv[2], sys.argv[3]))


if __name__ == "__main__":
    sys.exit(main())
