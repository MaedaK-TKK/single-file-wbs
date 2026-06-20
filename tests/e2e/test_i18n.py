"""言語切替: 既定ja・ENトグルで全UI英語化・localStorage記憶・ja復帰"""
from playwright.sync_api import sync_playwright
from common import VIEWER, check, finish, leaf

DATA = {"projects": [{"name": "P1", "milestones": [],
        "tasks": [{"id": "1", "name": "工程", "children":
                   [leaf("1.1", "作業A", ps="2026-06-01", pe="2026-06-15", as_="2026-06-02")]}]}]}

errors = []
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_context().new_page()
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(VIEWER)
    check(pg.inner_text("#openBtn").startswith("ファイルを開く") and "ドラッグ" in pg.inner_text("#openBtn"), "既定は日本語")
    pg.evaluate("d=>window.renderData(d)", DATA); pg.wait_for_timeout(150)

    pg.click("#langBtn"); pg.wait_for_timeout(200)
    check(pg.inner_text("#openBtn").startswith("Open file") and "drag" in pg.inner_text("#openBtn"), "EN: ボタン英語化")
    heads = pg.inner_text("#leftHead")
    check("Task" in heads and "Plan" in heads and "Actual" in heads, "EN: 列見出し英語化")
    check("Period" in pg.inner_text("#stat"), "EN: ヘッダ統計英語化")
    check("active" in pg.inner_text("#leftRows"), "EN: 進行中→active")
    check(pg.get_attribute("html", "lang") == "en", "html lang=en")

    pg.reload(); pg.wait_for_timeout(200)
    check(pg.inner_text("#openBtn").startswith("Open file") and "drag" in pg.inner_text("#openBtn"), "リロード後もENを記憶")
    pg.click("#langBtn"); pg.wait_for_timeout(100)
    check(pg.inner_text("#openBtn").startswith("ファイルを開く") and "ドラッグ" in pg.inner_text("#openBtn"), "日本語へ復帰")
    b.close()
finish(errors)
