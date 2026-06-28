"""file://権限フロー: 保存ピッカーfallback・ジェスチャー失効→再クリック・選択時切り詰めへの即書込・案内バー遷移"""
import json
from playwright.sync_api import sync_playwright
from common import VIEWER, check, finish, leaf, new_page

DATA = {"projects": [{"name": "P1", "milestones": [],
        "tasks": [leaf("1", "作業", ps="2026-06-01", pe="2026-06-05")]}]}

# file://模擬: 読取ハンドルは権限API不可。保存ピッカーは1回目=ジェスチャー失効、2回目=切り詰めの上で書込可ハンドル
INIT = """
window.__file = %s; window.__pick = 0; window.__cnt = {req:0, cw:0, picker:0};
const blocked = m => {throw new DOMException(m);};
const readHandle = {kind:'file', __id:'wbs',
  getFile: async()=> new File([window.__file],'wbs.json',{type:'application/json',lastModified:1000}),
  queryPermission: async()=>'prompt',
  requestPermission: async()=>{window.__cnt.req++; blocked("Not allowed to request permissions in this context.");},
  createWritable: async()=>{window.__cnt.cw++; blocked("Not allowed to request permissions in this context.");},
  isSameEntry: async(o)=>o.__id==='wbs'};
const writeHandle = {kind:'file', __id:'wbs',
  getFile: async()=> new File([window.__file??''],'wbs.json',{type:'application/json',lastModified:2000}),
  queryPermission: async()=>'granted',
  createWritable: async()=>{let b=null;return {write:async s=>{b=s;},abort:async()=>{},
    close:async()=>{if(b!=null)window.__file=b;}}},
  isSameEntry: async(o)=>o.__id==='wbs'};
window.showOpenFilePicker = async()=>[readHandle];
window.showSaveFilePicker = async()=>{
  window.__noticeAtPicker = document.getElementById('notice').textContent;
  window.__cnt.picker++;
  if(window.__cnt.picker===1){const e=new DOMException("Must be handling a user gesture to show a file picker.");
    Object.defineProperty(e,'name',{value:'NotAllowedError'}); throw e;}
  window.__file = '';   // Chromeの「選択時切り詰め」を再現
  return writeHandle;};
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

    # 1回目: ピッカーがジェスチャー失効 → 案内バーで再クリック誘導（編集ONにならない）
    pg.click("#editBtn"); pg.wait_for_timeout(300)
    check("on" not in (pg.get_attribute("#editBtn", "class") or ""), "ジェスチャー失効時は編集ONにならない")
    check("保存ダイアログが開きます" in (pg.evaluate("()=>window.__noticeAtPicker") or ""),
          "ピッカー表示時点で案内バーが出ている")
    check("もう一度「編集」を押して" in pg.inner_text("#notice") or "もう一度" in pg.inner_text("#notice"),
          "失効後は再クリック案内に切替")
    check(not [d for d in dialogs if "取得できませんでした" in d], "失敗アラートは出さない（バー案内のみ）")

    # 2回目: 前処理スキップで直接ピッカー → 選択時切り詰め → 即書込で空のまま残らない
    pg.click("#editBtn"); pg.wait_for_timeout(400)
    cnt = pg.evaluate("()=>window.__cnt")
    check("on" in (pg.get_attribute("#editBtn", "class") or ""), "2回目で編集ON")
    check(cnt["req"] == 1, f"2回目は requestPermission をスキップ -> {cnt}")
    content = pg.evaluate("()=>window.__file")
    check(content and len(content) > 10, "選択時切り詰め後に即書込（ファイルが空のまま残らない）")
    check(json.loads(content)["projects"][0]["name"] == "P1", "即書込の内容が読込データと一致")
    check(not pg.evaluate("()=>document.getElementById('notice').classList.contains('show')"),
          "成功後は案内バーが消える")

    # 編集→自動保存も新ハンドル経由で通る
    pg.fill('input[data-field="assignee"]', "佐藤")
    pg.dispatch_event('input[data-field="assignee"]', "change")
    pg.wait_for_timeout(600)
    check(json.loads(pg.evaluate("()=>window.__file"))["projects"][0]["tasks"][0]["assignee"] == "佐藤",
          "以後の編集が自動保存される")
    b.close()
finish(errors)
