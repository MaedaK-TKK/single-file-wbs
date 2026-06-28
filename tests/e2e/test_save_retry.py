"""横入りエラーの自動リトライ: createWritable が初回だけ InvalidStateError を投げても、
   1拍おいて1回だけ再試行し保存が回復する（同期/AV の一瞬の横入りでデータを取りこぼさない）。
   writeNow の retry 分岐（#保存パス聖域）を壊す変更はここで捕まる。"""
import json
from playwright.sync_api import sync_playwright
from common import VIEWER, check, finish, new_page

DATA = {"projects": [{"name": "P1", "milestones": [], "tasks": [
    {"id": "1", "name": "元の名前", "qty": 1, "hours": 8, "assignee": "元担当",
     "plan": {"start": "2026-06-01", "end": "2026-06-05"},
     "actual": {"start": None, "end": None}, "note": "元の備考"}]}]}

# 初回 createWritable だけ InvalidStateError を投げ、2回目は成功するフェイクハンドル
INIT = """
window.__file = %s; window.__writes = 0; window.__cwCalls = 0;
const fh = {kind:'file',
  getFile: async()=> new File([window.__file],'wbs.json',{type:'application/json',lastModified:window.__mt||1000}),
  queryPermission: async()=>'granted', requestPermission: async()=>'granted',
  createWritable: async()=>{
    window.__cwCalls++;
    if(window.__cwCalls===1){ throw new DOMException("state had changed since it was read from disk","InvalidStateError"); }
    let b=null;
    return {write:async s=>{b=s;}, abort:async()=>{},
      close:async()=>{window.__file=b; window.__mt=(window.__mt||1000)+1; window.__writes++;}};
  }};
window.showOpenFilePicker = async()=>[fh];
""" % json.dumps(json.dumps(DATA, ensure_ascii=False))

errors, dialogs = [], []
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = new_page(b)
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("dialog", lambda d: (dialogs.append(d.message), d.accept()))
    pg.add_init_script(INIT)
    pg.goto(VIEWER)
    pg.click("#openBtn"); pg.wait_for_timeout(150)
    pg.click("#editBtn"); pg.wait_for_timeout(200)

    pg.fill('input[data-field="assignee"]', "新担当")
    pg.dispatch_event('input[data-field="assignee"]', "change")
    pg.wait_for_timeout(1200)   # debounce(400)+retry delay(250)+余裕

    cw = pg.evaluate("()=>window.__cwCalls")
    writes = pg.evaluate("()=>window.__writes")
    saved = json.loads(pg.evaluate("()=>window.__file"))["projects"][0]["tasks"][0]

    check(cw == 2, f"createWritable が2回呼ばれた（初回失敗→1回だけ再試行）得 {cw}")
    check(writes == 1, f"再試行で書込が1回成功した 得 {writes}")
    check(saved["assignee"] == "新担当", f"再試行後のファイルに編集が反映 得 {saved['assignee']!r}")
    # 自動回復したので「保存失敗」アラートは出ていないこと（出た＝リトライ未動作）
    check(not any("失敗" in d or "Save failed" in d or "Save failed:" in d for d in dialogs),
          f"保存失敗アラートが出ていない 得 {dialogs}")

    b.close()
finish(errors)
