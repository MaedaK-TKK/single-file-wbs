"""全体caret: 状態記号・状態依存tooltip・全展開/全たたみ・Ctrl+Z復旧・個別操作後の無効化"""
from playwright.sync_api import sync_playwright
from common import VIEWER, check, finish, leaf

DATA = {"projects": [
    {"name": "P1", "milestones": [], "tasks": [{"id": "1", "name": "工程A",
        "children": [leaf("1.1", "a", ps="2026-06-01", pe="2026-06-05"),
                     leaf("1.2", "b", ps="2026-06-01", pe="2026-06-05")]}]},
    {"name": "P2", "milestones": [], "tasks": [{"id": "1", "name": "工程B",
        "children": [leaf("1.1", "c", ps="2026-06-01", pe="2026-06-05")]}]}]}

errors = []
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page()
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(VIEWER)
    pg.evaluate("d=>window.renderData(d)", DATA); pg.wait_for_timeout(150)
    rows = lambda: len(pg.query_selector_all("#leftRows .lrow"))
    title = lambda: pg.get_attribute("#allCaret", "title") or ""

    all_rows = rows()
    check(pg.inner_text("#allCaret") == "▼", "全部開いている時はヘッダ▼")
    check("折りたたまれます" in title(), "▼時のtooltipは折りたたみ予告")

    pg.click('[data-collapse="T|P1|1"]'); pg.wait_for_timeout(100)
    mixed_rows = rows()
    check(mixed_rows < all_rows and pg.inner_text("#allCaret") == "▶", "混在状態でヘッダ▶")
    check("展開されます" in title(), "▶時のtooltipは展開予告")

    pg.click("#allCaret"); pg.wait_for_timeout(100)
    check(rows() == all_rows, "▶クリックで全展開")
    pg.keyboard.press("Control+z"); pg.wait_for_timeout(100)
    check(rows() == mixed_rows, "Ctrl+Zで混在状態に復元")

    pg.click("#allCaret"); pg.wait_for_timeout(100)  # ▶→全展開
    pg.click("#allCaret"); pg.wait_for_timeout(100)  # ▼→全たたみ
    check(rows() == 2, "▼クリックで全たたみ（プロジェクト行のみ）")
    pg.keyboard.press("Control+z"); pg.wait_for_timeout(100)
    check(rows() == all_rows, "全たたみもCtrl+Zで復元")

    pg.click("#allCaret"); pg.wait_for_timeout(100)            # 全たたみ（snapshot保持）
    pg.click('[data-collapse="P|P1"]'); pg.wait_for_timeout(100)  # 手で1つ開く
    manual = rows()
    pg.keyboard.press("Control+z"); pg.wait_for_timeout(100)
    check(rows() == manual, "個別操作後のCtrl+Zは無効（手作業を破壊しない）")
    b.close()
finish(errors)
