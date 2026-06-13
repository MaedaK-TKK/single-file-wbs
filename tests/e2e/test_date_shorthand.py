"""日付ショートハンド入力＋適応型表示（#59）: 611/6-11等→full ISO・年補完・他年はfull表示。
   聖域（applyFieldの日付パース）。データはfull ISOのまま保存・1900-2099ガード維持。"""
import json
import datetime
from playwright.sync_api import sync_playwright
from common import VIEWER, check, finish, leaf, granted_handle_init

YEAR = datetime.date.today().year
DATA = {"projects": [{"name": "P1", "milestones": [], "tasks": [
    leaf("1", "今年タスク", ps=f"{YEAR}-06-01", pe=f"{YEAR}-06-05"),
    leaf("2", "他年タスク", ps="2099-01-15", pe="2099-01-20")]}]}

errors = []
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page()
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("dialog", lambda d: d.accept())
    pg.add_init_script(granted_handle_init(DATA))
    pg.goto(VIEWER)
    pg.click("#openBtn"); pg.wait_for_timeout(150)
    pg.click("#editBtn"); pg.wait_for_timeout(200)

    def saved(i):
        return json.loads(pg.evaluate("()=>window.__file"))["projects"][0]["tasks"][i]
    def setfield(path, field, val):
        sel = f'input[data-path="{path}"][data-field="{field}"]'
        pg.fill(sel, val); pg.dispatch_event(sel, "change"); pg.wait_for_timeout(550)

    # 表示：今年は短縮 MM-DD、他年は full ISO（年が"意外"な時だけ見せる）
    vals = pg.evaluate("""()=>{
        const v=(p,f)=>document.querySelector(`input[data-path="${p}"][data-field="${f}"]`).value;
        return {y1:v('0/0','ps'), other:v('0/1','ps')};
    }""")
    check(vals["y1"] == "06-01", f"今年は短縮表示 06-01 → {vals['y1']}")
    check(vals["other"] == "2099-01-15", f"他年は full ISO 表示 → {vals['other']}")

    # ショートハンド入力（611=MDD・年は既存値=今年で補完）
    setfield("0/0", "ps", "611")
    check(saved(0)["plan"]["start"] == f"{YEAR}-06-11", f"611→{YEAR}-06-11（年補完）→ {saved(0)['plan']['start']}")

    # 0815=MMDD
    setfield("0/0", "pe", "0815")
    check(saved(0)["plan"]["end"] == f"{YEAR}-08-15", f"0815→{YEAR}-08-15 → {saved(0)['plan']['end']}")

    # 区切りあり 7-3 / 7/3
    setfield("0/0", "as", "7-3")
    check(saved(0)["actual"]["start"] == f"{YEAR}-07-03", f"7-3→{YEAR}-07-03 → {saved(0)['actual']['start']}")

    # 他年タスクの月日変更：年は既存(2099)を保持
    setfield("0/1", "pe", "0331")
    check(saved(1)["plan"]["end"] == "2099-03-31", f"他年は既存年2099を保持→ {saved(1)['plan']['end']}")

    # full ISO 直接入力も従来どおり通る
    setfield("0/0", "ae", "2030-12-31")
    check(saved(0)["actual"]["end"] == "2030-12-31", f"full ISO直接→ {saved(0)['actual']['end']}")

    # 解釈不能・範囲外は無視（ゴミを保存しない）
    before = saved(0)["plan"]["start"]
    setfield("0/0", "ps", "99999")
    check(saved(0)["plan"]["start"] == before, f"解釈不能(99999)は無視→ {saved(0)['plan']['start']}")

    b.close()
finish(errors)
