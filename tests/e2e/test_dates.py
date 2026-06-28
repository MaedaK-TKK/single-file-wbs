"""日付欄: ISOテキスト固定・📅プロキシ連携・スラッシュ正規化・範囲外拒否"""
import json
from playwright.sync_api import sync_playwright
from common import VIEWER, check, finish, leaf, granted_handle_init, new_page

DATA = {"projects": [{"name": "P1", "milestones": [],
        "tasks": [leaf("1", "作業", ps="2026-06-01", pe="2026-06-05")]}]}

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
    saved = lambda: json.loads(pg.evaluate("()=>window.__file"))["projects"][0]["tasks"][0]

    info = pg.evaluate("""()=>{
      const i = document.querySelector('input[data-field="ps"]');
      return {type:i.type, value:i.value, ph:i.placeholder,
              btn:!!i.closest('.date-wrap').querySelector('button[data-cal]')};
    }""")
    check(info["type"] == "text" and info["value"] == "06-01" and info["ph"] == "MM-DD",
          "日付欄は今年なら短縮表示MM-DD（ISO由来・全環境で月/日順・#59）")
    check(info["btn"], "📅カレンダーボタンあり")

    pg.fill('input[data-field="pe"]', "2026/06/20")
    pg.dispatch_event('input[data-field="pe"]', "change")
    pg.wait_for_timeout(600)
    check(saved()["plan"]["end"] == "2026-06-20", "スラッシュ区切り入力を正規化して保存")

    pg.evaluate("""()=>{
      const w = document.querySelector('input[data-field="as"]').closest('.date-wrap');
      const px = w.querySelector('.cal-proxy');
      px.value='2026-06-03';
      px.dispatchEvent(new Event('change',{bubbles:true}));
    }""")
    pg.wait_for_timeout(600)
    check(saved()["actual"]["start"] == "2026-06-03", "📅で選んだ日付がテキスト経由で保存")

    pg.evaluate("""()=>{
      const w = document.querySelector('input[data-field="as"]').closest('.date-wrap');
      const px = w.querySelector('.cal-proxy');
      px.value='';                       // カレンダーの「クリア」押下を模擬
      px.dispatchEvent(new Event('change',{bubbles:true}));
    }""")
    pg.wait_for_timeout(600)
    check(saved()["actual"]["start"] is None, "📅のクリアで日付が消える（null保存）")

    # 📅クリック時、短縮表示(06-01)でも cal-proxy に full ISO が入る（#59回帰：これが空だとクリア不能だった）
    proxy = pg.evaluate("""()=>{
      const w = document.querySelector('input[data-field="ps"]').closest('.date-wrap');
      w.querySelector('button[data-cal]').click();
      return w.querySelector('.cal-proxy').value;
    }""")
    check(proxy == "2026-06-01", f"📅クリックで短縮形→full ISOをnativeへ（#59回帰）→ {proxy!r}")

    pg.fill('input[data-field="ps"]', "0002/07/15")
    pg.dispatch_event('input[data-field="ps"]', "change")
    pg.wait_for_timeout(600)
    check(saved()["plan"]["start"] == "2026-06-01", "範囲外年（1900-2099外）は保存しない")
    b.close()
finish(errors)
