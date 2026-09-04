"""The head and the column names stay on screen when a column scrolls (plan
06, item 4), checked on a running board through Chromium's DevTools protocol.

jsdom lays nothing out, so whether a pinned head is actually in the viewport
after a scroll cannot be asserted by the vitest suite. This drives headless
Chromium against a live server at a laptop's size: it scrolls one column by a
screenful, then reads the geometry — the app head, the attention line and
every open column's heading still inside the viewport, the scrolled column's
first card gone above its heading, and the first card of another column not
moved a pixel — and takes a screenshot. Run it before a review record that
claims the head and the column names never leave the screen.

    uv run python tools/scroll_check.py http://127.0.0.1:8480/ Backlog Executing /tmp/scroll.png
"""

import asyncio
import base64
import json
import subprocess
import sys
import time
import urllib.request

import websockets

PORT = 9342
WIDTH, HEIGHT = 1440, 900
"""A laptop: below the wide breakpoint, where the head folds to one line."""


async def call(
    ws: websockets.ClientConnection, counter: list[int], method: str, **params: object
) -> dict:
    counter[0] += 1
    await ws.send(json.dumps({"id": counter[0], "method": method, "params": params}))
    while True:
        message = json.loads(await ws.recv())
        if message.get("id") == counter[0]:
            return message.get("result", {})


def _rect(selector: str) -> str:
    return (
        f"(() => {{ const el = document.querySelector({json.dumps(selector)}); if (!el) return null; "
        "const r = el.getBoundingClientRect(); return [r.left, r.top, r.width, r.height]; })()"
    )


async def check(url: str, scrolled: str, still: str, screenshot: str) -> int:
    chromium = subprocess.Popen(
        [
            "chromium",
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--hide-scrollbars",
            f"--remote-debugging-port={PORT}",
            f"--window-size={WIDTH},{HEIGHT}",
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

            await call(
                ws,
                counter,
                "Emulation.setDeviceMetricsOverride",
                width=WIDTH,
                height=HEIGHT,
                deviceScaleFactor=1,
                mobile=False,
            )
            await call(ws, counter, "Page.navigate", url=url)
            column = f'[data-column="{scrolled}"]'
            other = f'[data-column="{still}"]'
            for _ in range(80):
                if await js(f"document.querySelectorAll('{column} article[data-card]').length >= 3"):
                    break
                await asyncio.sleep(0.25)
            first_card = f"{column} article[data-card]"
            other_card = f"{other} article[data-card]"
            heading = f"{column} .col-head h2"
            other_heading = f"{other} .col-head h2"
            before = {
                "card": await js(_rect(first_card)),
                "other": await js(_rect(other_card)),
                "heading": await js(_rect(heading)),
                "other_heading": await js(_rect(other_heading)),
            }
            if before["card"] is None or before["heading"] is None:
                print(f"{scrolled} has no cards or no heading on the page; nothing to scroll")
                return 2
            await js(
                f"(() => {{ const el = document.querySelector('{column}'); el.scrollTop = 600; "
                "el.dispatchEvent(new Event('scroll')); return el.scrollTop; })()"
            )
            await asyncio.sleep(0.5)
            after = {
                "head": await js(_rect(".app-head")),
                "attn": await js(_rect(".attn-line")),
                "heading": await js(_rect(heading)),
                "other_heading": await js(_rect(other_heading)),
                "card": await js(_rect(first_card)),
                "other": await js(_rect(other_card)),
                "folded": await js("document.querySelector('.head')?.dataset.folded"),
                "scrollTop": await js(f"document.querySelector('{column}').scrollTop"),
                "pageScroll": await js("window.scrollY"),
            }
            shot = await call(ws, counter, "Page.captureScreenshot", format="png")
            with open(screenshot, "wb") as out:
                out.write(base64.b64decode(shot["data"]))

            def in_view(rect: object) -> bool:
                return (
                    isinstance(rect, list)
                    and rect[1] >= 0
                    and rect[1] + rect[3] <= HEIGHT
                    and rect[3] > 0
                )

            findings = []
            if after["scrollTop"] in (0, None):
                findings.append(f"{scrolled} did not scroll (scrollTop {after['scrollTop']})")
            if after["pageScroll"]:
                findings.append(f"the page itself scrolled by {after['pageScroll']}")
            if not in_view(after["head"]):
                findings.append(f"the app head left the viewport: {after['head']}")
            if not in_view(after["attn"]):
                findings.append(f"the attention line left the viewport: {after['attn']}")
            if not in_view(after["heading"]):
                findings.append(f"{scrolled}'s heading left the viewport: {after['heading']}")
            if not in_view(after["other_heading"]):
                findings.append(f"{still}'s heading left the viewport: {after['other_heading']}")
            if isinstance(after["card"], list) and isinstance(after["heading"], list):
                if after["card"][1] >= after["heading"][1]:
                    findings.append(
                        f"{scrolled}'s first card did not move up under its heading: "
                        f"{before['card']} -> {after['card']}"
                    )
            # The head folds when a column scrolls, so every column rises with it;
            # what must not change is the other column's own scroll: its first
            # card's distance from its heading.
            def gap(card: object, head: object) -> float | None:
                if isinstance(card, list) and isinstance(head, list):
                    return round(card[1] - head[1], 2)
                return None

            if gap(after["other"], after["other_heading"]) != gap(before["other"], before["other_heading"]):
                findings.append(
                    f"{still} scrolled too: its first card sat {gap(before['other'], before['other_heading'])} "
                    f"under its heading and now sits {gap(after['other'], after['other_heading'])}"
                )
            if after["folded"] != "true":
                findings.append(f"the head did not fold to one line on a laptop (folded={after['folded']})")
            print(f"before: {json.dumps(before)}")
            print(f"after:  {json.dumps(after)}")
            print(f"shot:   {screenshot}")
            if findings:
                print("\n".join(f"FAIL: {f}" for f in findings))
                return 1
            print(
                f"the head, the attention line and the headings of {scrolled} and {still} stayed; "
                f"{scrolled} scrolled on its own and {still} did not move"
            )
            return 0
    finally:
        chromium.terminate()


def main() -> int:
    if len(sys.argv) != 5:
        print(__doc__)
        return 2
    return asyncio.run(check(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]))


if __name__ == "__main__":
    sys.exit(main())
