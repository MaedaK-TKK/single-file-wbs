"""保存往復マトリクス: 各フィールドの編集が正しいJSONパスに保存される（applyFieldのfield→path対応）。
   #16でapplyFieldを書き換える時、pe↔ps の入れ替わり等はここでしか捕まらない。"""
import json
from playwright.sync_api import sync_playwright
from common import VIEWER, check, finish, granted_handle_init, new_page

# 全フィールドに異なる初期値を置き、編集後の混線（別パスへの保存）を検出
DATA = {"projects": [{"name": "P1", "milestones": [], "tasks": [
    {"id": "1", "name": "元の名前", "qty": 1, "hours": 8, "assignee": "元担当",
     "plan": {"start": "2026-06-01", "end": "2026-06-05"},
     "actual": {"start": "2026-06-01", "end": "2026-06-05"}, "note": "元の備考"}]}]}

# field名（DOM data-field） → (保存先パス, 入力値, 期待値)
CASES = [
    ("qty",      ["qty"],            "3",          3),
    ("hours",    ["hours"],          "24",         24),
    ("assignee", ["assignee"],       "新担当",      "新担当"),
    ("note",     ["note"],           "新備考",      "新備考"),
    ("ps",       ["plan", "start"],  "2026-07-01", "2026-07-01"),
    ("pe",       ["plan", "end"],    "2026-07-05", "2026-07-05"),
    ("as",       ["actual", "start"],"2026-07-02", "2026-07-02"),
    ("ae",       ["actual", "end"],  "2026-07-04", "2026-07-04"),
]

errors = []
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = new_page(b)
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("dialog", lambda d: d.accept())
    pg.add_init_script(granted_handle_init(DATA))
    pg.goto(VIEWER)
    pg.click("#openBtn"); pg.wait_for_timeout(150)
    pg.click("#editBtn"); pg.wait_for_timeout(200)

    def saved():
        return json.loads(pg.evaluate("()=>window.__file"))["projects"][0]["tasks"][0]

    def dig(obj, path):
        for k in path:
            obj = obj[k]
        return obj

    # name は再描画・折りたたみキーに影響しうるので最後に単独で検証
    for field, path, val, exp in CASES:
        pg.fill(f'input[data-field="{field}"]', val)
        pg.dispatch_event(f'input[data-field="{field}"]', "change")
        pg.wait_for_timeout(550)
        got = dig(saved(), path)
        check(got == exp, f'{field} → {".".join(path)} = {exp!r}（得 {got!r}）')

    # 混線していないこと（全パスが期待どおり同時に成立）
    s = saved()
    allok = (s["qty"] == 3 and s["hours"] == 24 and s["assignee"] == "新担当" and s["note"] == "新備考"
             and s["plan"] == {"start": "2026-07-01", "end": "2026-07-05"}
             and s["actual"] == {"start": "2026-07-02", "end": "2026-07-04"})
    check(allok, f"全フィールドが各パスに混線なく保存\n     {json.dumps(s, ensure_ascii=False)}")

    # name 編集（最後に）
    pg.fill('input[data-field="name"]', "改名後")
    pg.dispatch_event('input[data-field="name"]', "change")
    pg.wait_for_timeout(550)
    check(saved()["name"] == "改名後", "name → name")

    b.close()
finish(errors)
