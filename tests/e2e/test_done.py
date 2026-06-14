"""完了チェックボックス（#37）: 先頭の✓トグルで実績終了=今日／解除でnull。
   リーフのみ操作可（集計ノードは読み取り✓）。未着手チェックは着手も今日に補完。"""
import json
import datetime
from playwright.sync_api import sync_playwright
from common import VIEWER, check, finish, granted_handle_init

TODAY = datetime.date.today().isoformat()
DATA = {"projects": [{"name": "P1", "milestones": [], "tasks": [
    {"id": "1", "name": "工程", "children": [
        {"id": "1.1", "name": "未着手", "qty": 1, "hours": 8, "assignee": "A",
         "plan": {"start": "2026-06-10", "end": "2026-06-20"}, "actual": {"start": None, "end": None}, "note": ""},
        {"id": "1.2", "name": "進行中", "qty": 1, "hours": 8, "assignee": "B",
         "plan": {"start": "2026-06-10", "end": "2026-06-20"}, "actual": {"start": "2026-06-10", "end": None}, "note": ""},
        {"id": "1.3", "name": "完了済", "qty": 1, "hours": 8, "assignee": "C",
         "plan": {"start": "2026-06-01", "end": "2026-06-05"}, "actual": {"start": "2026-06-01", "end": "2026-06-05"}, "note": ""}]}]}]}

errors = []
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1400, "height": 500})
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("dialog", lambda d: d.accept())
    pg.add_init_script(granted_handle_init(DATA))
    pg.goto(VIEWER)
    pg.click("#openBtn"); pg.wait_for_timeout(150)
    pg.click("#editBtn"); pg.wait_for_timeout(200)

    def leaves():
        return json.loads(pg.evaluate("()=>window.__file"))["projects"][0]["tasks"][0]["children"]
    def click_chk(i):
        pg.evaluate("i=>document.querySelectorAll('#leftRows .lrow.leaf .donechk')[i].click()", i)
        pg.wait_for_timeout(600)

    # チェックボックスはリーフ3行のみ（集計ノード「工程」には出ない）
    nchk = pg.evaluate("()=>document.querySelectorAll('#leftRows .donechk').length")
    check(nchk == 3, f"完了チェックはリーフのみ（3個）→ {nchk}")
    init = pg.eval_on_selector_all("#leftRows .donechk", "els=>els.map(e=>e.classList.contains('on'))")
    check(init == [False, False, True], f"初期チェック状態（完了行のみon）→ {init}")

    click_chk(0)  # 未着手→完了
    s = leaves()
    check(s[0]["actual"]["end"] == TODAY and s[0]["actual"]["start"] == TODAY,
          f"未着手をチェック→完了（end=今日・着手も今日補完）→ {s[0]['actual']}")

    click_chk(1)  # 進行中→完了（着手日は保持）
    s = leaves()
    check(s[1]["actual"]["end"] == TODAY and s[1]["actual"]["start"] == "2026-06-10",
          f"進行中をチェック→完了（end=今日・着手日保持）→ {s[1]['actual']}")

    click_chk(2)  # 完了→解除
    s = leaves()
    check(s[2]["actual"]["end"] is None and s[2]["actual"]["start"] == "2026-06-01",
          f"完了を解除→未完了（end=null・着手日保持）→ {s[2]['actual']}")

    b.close()
finish(errors)
