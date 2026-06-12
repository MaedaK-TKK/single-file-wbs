"""D&D読込: 正常JSON・空ファイルのエラー表示（名前+サイズ）・ハンドル空読み時のフォールバック"""
import json
from playwright.sync_api import sync_playwright
from common import VIEWER, check, finish, leaf

DATA = json.dumps({"projects": [{"name": "P", "milestones": [],
        "tasks": [leaf("1", "A", ps="2026-06-01", pe="2026-06-05")]}]}, ensure_ascii=False)

errors, dialogs = [], []
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page()
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("dialog", lambda d: (dialogs.append(d.message), d.accept()))
    pg.goto(VIEWER)
    drop = lambda txt, name: pg.evaluate("""(a)=>{
      const dt = new DataTransfer();
      dt.items.add(new File([a.txt], a.name, {type:'application/json'}));
      document.getElementById('openBtn').dispatchEvent(new DragEvent('drop',{bubbles:true,cancelable:true,dataTransfer:dt}));
    }""", {"txt": txt, "name": name})

    drop(DATA, "wbs.json"); pg.wait_for_timeout(250)
    check(len(pg.query_selector_all("#leftRows .lrow")) > 0, "正常JSONのドロップで描画")

    dialogs.clear()
    drop("", "empty.json"); pg.wait_for_timeout(250)
    check(any("empty.json" in d and "0" in d for d in dialogs), f"空ファイルは名前+サイズ付きでエラー表示 -> {dialogs}")

    dialogs.clear()
    pg.evaluate("""(txt)=>{
      DataTransferItem.prototype.getAsFileSystemHandle = async function(){
        return {kind:'file', getFile: async()=> new File([''],'wbs.json',{type:'application/json'})};
      };
      const dt = new DataTransfer();
      dt.items.add(new File([txt],'wbs.json',{type:'application/json'}));
      document.getElementById('openBtn').dispatchEvent(new DragEvent('drop',{bubbles:true,cancelable:true,dataTransfer:dt}));
    }""", DATA)
    pg.wait_for_timeout(250)
    check(len(pg.query_selector_all("#leftRows .lrow")) > 0 and not dialogs,
          "ハンドルが空を返してもfiles[]フォールバックで描画")
    b.close()
finish(errors)
