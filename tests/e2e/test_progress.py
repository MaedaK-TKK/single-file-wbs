"""進捗2軸ビュー 段階1（#63）: _progress の量子化・時間ベースより優先・フォールバック、
   4分割クリック入力（_progress/_progressAt/_progressBy 保存）・着手日の自動セット・0%トグルで着手日維持。
   本日は CLOCK_PIN=2026-06-15 固定（フォールバック%を決定論計算）。"""
import json
from playwright.sync_api import sync_playwright
from common import VIEWER, CLOCK_PIN, granted_handle_init, check, finish

DATA = {"projects": [{"name": "P", "milestones": [], "tasks": [
    {"id": "1", "name": "工程", "children": [
        {"id": "1.1", "name": "override", "qty": 1, "hours": 8, "assignee": "佐藤",
         "plan": {"start": "2026-06-01", "end": "2026-06-30"},
         "actual": {"start": "2026-06-05", "end": None}, "_progress": 73, "note": ""},   # 73→75=3マス（時間ベースより優先）
        {"id": "1.2", "name": "fallback", "qty": 1, "hours": 8, "assignee": "鈴木",
         "plan": {"start": "2026-06-10", "end": "2026-06-20"},
         "actual": {"start": "2026-06-10", "end": None}, "note": ""},                    # _progress無→(15-10)/10=50%→2マス
        {"id": "1.3", "name": "未着手", "qty": 1, "hours": 8, "assignee": "田中",
         "plan": {"start": "2026-06-12", "end": "2026-06-18"},
         "actual": {"start": None, "end": None}, "note": ""},                            # 0マス
        {"id": "1.4", "name": "完了タスク", "qty": 1, "hours": 8, "assignee": "高橋",
         "plan": {"start": "2026-06-01", "end": "2026-06-05"},
         "actual": {"start": "2026-06-01", "end": "2026-06-05"}, "note": ""},            # 100%=4マス
    ]}
]}]}

# 行名に substring 一致する行の、塗られた進捗マス数を返す
FILLED = """name=>{for(const r of document.querySelectorAll('#leftRows .lrow')){
  const nm=(r.querySelector('.c.name')||{}).innerText||'';
  if(nm.includes(name))return r.querySelectorAll('.c.prog .qi.on').length;}
  return -1;}"""
# 編集モード：行名(name入力)一致行の q番目(1..4)マスをクリック
CLICK_Q = """([name,q])=>{for(const r of document.querySelectorAll('#leftRows .lrow')){
  const nm=((r.querySelector('.nm-in')||{}).value)||'';
  if(nm.includes(name)){r.querySelectorAll('.c.prog .qi')[q-1].click();return true;}}return false;}"""

errors = []
with sync_playwright() as p:
    b = p.chromium.launch()
    # --- 表示：量子化・優先・フォールバック・自動0/100 ---
    pg = b.new_page(viewport={"width": 1500, "height": 700})
    pg.add_init_script(CLOCK_PIN)
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(VIEWER)
    pg.evaluate("d => window.renderData(d)", DATA)
    pg.wait_for_timeout(200)
    check(pg.evaluate(FILLED, "override") == 3, f"_progress=73 → 75%(3マス)・時間ベースより優先（得 {pg.evaluate(FILLED, 'override')}）")
    check(pg.evaluate(FILLED, "fallback") == 2, f"_progress無 → 時間ベース50%(2マス)にフォールバック（得 {pg.evaluate(FILLED, 'fallback')}）")
    check(pg.evaluate(FILLED, "未着手") == 0, f"未着手(actual.start無) → 0マス（得 {pg.evaluate(FILLED, '未着手')}）")
    check(pg.evaluate(FILLED, "完了タスク") == 4, f"完了(actual.end有) → 100%(4マス)（得 {pg.evaluate(FILLED, '完了タスク')}）")
    pg.close()

    # --- 編集：クリック入力・着手日自動・0%トグル ---
    ep = b.new_page(viewport={"width": 1500, "height": 700})
    ep.add_init_script(CLOCK_PIN)
    ep.add_init_script(granted_handle_init(DATA))
    ep.on("pageerror", lambda e: errors.append(str(e)))
    ep.on("dialog", lambda d: d.accept())
    ep.goto(VIEWER)
    ep.click("#openBtn"); ep.wait_for_timeout(150)
    ep.click("#editBtn"); ep.wait_for_timeout(250)

    def leaf13():
        kids = json.loads(ep.evaluate("()=>window.__file"))["projects"][0]["tasks"][0]["children"]
        return next(c for c in kids if c["id"] == "1.3")

    # 未着手(1.3)の3マス目クリック → 75%・着手日=今日
    ep.evaluate(CLICK_Q, ["未着手", 3]); ep.wait_for_timeout(550)
    n = leaf13()
    check(n.get("_progress") == 75, f"クリックで _progress=75 保存（得 {n.get('_progress')}）")
    check(n.get("_progressBy") == "manual", f"_progressBy=manual（得 {n.get('_progressBy')}）")
    check(isinstance(n.get("_progressAt"), str) and n.get("_progressAt"), f"_progressAt 記録（得 {n.get('_progressAt')}）")
    check(n.get("actual", {}).get("start") == "2026-06-15", f"未着手→着手日に今日を自動セット（得 {n.get('actual', {}).get('start')}）")

    # 同じ3マス目を再クリック → 0%・着手日は残る（決定A）
    ep.evaluate(CLICK_Q, ["未着手", 3]); ep.wait_for_timeout(550)
    n2 = leaf13()
    check(n2.get("_progress") == 0, f"先端の再クリックで0%トグル（得 {n2.get('_progress')}）")
    check(n2.get("actual", {}).get("start") == "2026-06-15", f"0%に戻しても着手日は残る（得 {n2.get('actual', {}).get('start')}）")

    b.close()
finish(errors)
