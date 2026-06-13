"""セキュリティ回帰: XSSエスケープ（esc）と color属性インジェクション（isColor）。
   #16でセル生成を書き換える時、1列でもesc()を忘れたらここが赤くなる。"""
from playwright.sync_api import sync_playwright
from common import VIEWER, check, finish, load_test_json

errors = []
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1500, "height": 700})
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(VIEWER)

    # alert が呼ばれたら捕捉（注入が実行された証拠）
    pg.evaluate("()=>{window.__xss=false; const o=window.alert; window.alert=()=>{window.__xss=true;};}")

    # --- XSSエスケープ（特殊文字fixture）---
    pg.evaluate("d=>window.renderData(d)", load_test_json("正常_特殊文字エスケープ.json"))
    pg.wait_for_timeout(200)
    check(not pg.evaluate("()=>window.__xss"), "特殊文字: alertが実行されない")
    # name/note/assignee セルに <script> 要素が生DOM化していない
    inj = pg.evaluate("()=>document.querySelectorAll('#leftRows script').length")
    check(inj == 0, "特殊文字: <script>が生DOMになっていない")
    # 実体参照として表示されている（escが効いている）= テキストに <script> の文字が残る
    body = pg.inner_text("#leftRows")
    check("<script>" in body or "alert(1)" in body, "特殊文字: タグはテキストとして可視（esc済み）")

    # --- color属性インジェクション（isColor）---
    pg.evaluate("d=>window.renderData(d)", load_test_json("異常_color注入.json"))
    pg.wait_for_timeout(200)
    check(not pg.evaluate("()=>window.__xss"), "color注入: alertが実行されない")
    ov = pg.eval_on_selector("#overlay", "el=>el.outerHTML")
    check("onload" not in ov, "color注入: onload属性が注入されていない")
    check(pg.evaluate("()=>document.querySelectorAll('#overlay script').length") == 0,
          "color注入: overlay内に<script>が無い")
    # 正当な #hex のMSは描画される（防御が過剰でない）
    fills = pg.eval_on_selector_all("#overlay rect", "els=>els.map(e=>e.getAttribute('fill'))")
    check(any(f == "#22c55e" for f in fills), "color注入: 正当な#hexは描画される")
    # 不正colorはデフォルト色に落ちる＝生の不正文字列はfillに出ない
    check(all(f is None or f.startswith("#") for f in fills),
          "color注入: fillは#hexのみ（不正値はデフォルト化）")

    b.close()
finish(errors)
