"""コーパス回帰: tests/ の全fixtureを読み込み、JSエラー/NaN無し（graceful degradation）。
   正常_=正しく描画・異常_=崩れてもクラッシュしない。非オブジェクトトップはinlineでも併検。"""
import json
import pathlib
from playwright.sync_api import sync_playwright
from common import ROOT, VIEWER, check, finish, new_page

FIXTURES = sorted((ROOT / "tests").glob("正常_*.json")) + sorted((ROOT / "tests").glob("異常_*.json"))
INLINE = [("null", None), ("空配列", []), ("数値", 7), ("文字列", "x"), ("空オブジェクト", {})]

errors = []
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = new_page(b, viewport={"width": 1500, "height": 820})
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("console", lambda m: errors.append("console:" + m.text) if m.type == "error" else None)
    pg.goto(VIEWER)

    def render_no_crash(label, data):
        before = len(errors)
        pg.evaluate("d => window.renderData(d)", data)
        pg.wait_for_timeout(120)
        body_nan = pg.evaluate("()=>document.body.innerText.includes('NaN')")
        # オーバーレイ座標にNaNが無いこと（SVG全体が壊れる事故の再発防止）
        poly_nan = pg.evaluate("""()=>{const o=document.querySelector('#overlay polyline');
            if(!o)return false; return (o.getAttribute('points')||'').includes('NaN');}""")
        ok = len(errors) == before and not body_nan and not poly_nan
        check(ok, f"no-crash/no-NaN: {label}")

    for fx in FIXTURES:
        render_no_crash(fx.name, json.loads(fx.read_text(encoding="utf-8")))
    for label, val in INLINE:
        render_no_crash(f"inline:{label}", val)

    b.close()
finish(errors)
