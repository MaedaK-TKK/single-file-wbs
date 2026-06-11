"""日付欄: ISOテキスト固定・📅プロキシ連携・スラッシュ正規化・範囲外拒否"""
import json
from playwright.sync_api import sync_playwright
from common import VIEWER, check, finish, leaf, granted_handle_init

DATA = {"projects": [{"name": "P1", "milestones": [],
        "tasks": [leaf("1", "作業", ps="2026-06-01", pe="2026-06-05")]}]}

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
    saved = lambda: json.loads(pg.evaluate("()=>window.__file"))["projects"][0]["tasks"][0]

    info = pg.evaluate("""()=>{
      const i = document.querySelector('input[data-field="ps"]');
      return {type:i.type, value:i.value, ph:i.placeholder,
              btn:!!i.closest('.date-wrap').querySelector('button[data-cal]')};
    }""")
    check(info["type"] == "text" and info["value"] == "2026-06-01" and info["ph"] == "YYYY-MM-DD",
          "日付欄はISO固定のテキスト（全環境で年/月/日順）")
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

    pg.fill('input[data-field="ps"]', "0002/07/15")
    pg.dispatch_event('input[data-field="ps"]', "change")
    pg.wait_for_timeout(600)
    check(saved()["plan"]["start"] == "2026-06-01", "範囲外年（1900-2099外）は保存しない")
    b.close()
finish(errors)
