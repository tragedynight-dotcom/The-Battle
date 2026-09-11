"""Streamlit Community Cloud는 접속이 없으면 잠긴다.

단순 curl은 껍데기 HTML만 받아 잠금을 풀지 못한다.
브라우저로 열어 웹소켓이 붙어야 깨어난다.
"""
from __future__ import annotations

import os
import sys
import time

from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

DEFAULT_URL = "https://thebattle.streamlit.app"
WAKE = [
    "Yes, get this app back up!",
    "Yes, get this app back up",
    "Get this app back up",
    "앱을 다시 실행",
    "다시 실행",
]


def main() -> int:
    url = (os.environ.get("STREAMLIT_URL") or "").strip() or DEFAULT_URL
    if not url.startswith("http"):
        print(f"주소가 올바르지 않습니다: {url!r}", file=sys.stderr)
        return 1
    print("open", url)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=120_000)
        time.sleep(5)
        woke = False
        for label in WAKE:
            btn = page.get_by_role("button", name=label)
            try:
                if btn.count() and btn.first.is_visible():
                    print("wake", label)
                    btn.first.click()
                    page.wait_for_load_state("domcontentloaded", timeout=180_000)
                    woke = True
                    break
            except PlaywrightTimeout:
                pass
        if not woke:
            # 버튼 문구가 바뀐 경우 텍스트로 한 번 더 시도
            try:
                alt = page.locator("button").filter(has_text="back up")
                if alt.count() and alt.first.is_visible():
                    print("wake (filter)")
                    alt.first.click()
                    woke = True
            except Exception:
                pass
        print("already up" if not woke else "waking")
        time.sleep(45)
        print("title", page.title())
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
