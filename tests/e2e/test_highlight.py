"""ガント十字ハイライト（#48）: マウス位置の行（横）と列（縦）を薄く強調する。
   描画パスに載せず mousemove のオーバーレイで実現（colHl/rowHl/leftColHl は display 切替）。
   ・ガント側 mousemove → 日付列(#colHl + #dates .d.hl)＋行(#rowHl + .lrow.hl)
   ・左表側 mousemove → データ列(#leftColHl)＋行(#rowHl)。縦は『今いるペインの列』に切替わる。"""
from playwright.sync_api import sync_playwright
from common import VIEWER, check, finish, leaf, new_page

DATA = {"projects": [{"name": "P", "milestones": [], "tasks": [
    leaf("1", "作業A", ps="2026-06-01", pe="2026-06-08", as_="2026-06-01", ae="2026-06-05"),
    leaf("2", "作業B", ps="2026-06-03", pe="2026-06-12"),
    leaf("3", "作業C", ps="2026-06-05", pe="2026-06-10"),
]}]}

errors = []
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = new_page(b, viewport={"width": 1500, "height": 900})
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(VIEWER)
    pg.evaluate("d=>window.renderData(d)", DATA); pg.wait_for_timeout(150)

    disp = lambda sel: pg.evaluate(f"()=>getComputedStyle(document.querySelector('{sel}')).display")
    state = lambda: pg.evaluate("""()=>({
      col:getComputedStyle(document.getElementById('colHl')).display,
      row:getComputedStyle(document.getElementById('rowHl')).display,
      lcol:getComputedStyle(document.getElementById('leftColHl')).display,
      dhl:document.querySelectorAll('#dates .d.hl').length,
      rhl:document.querySelectorAll('#leftRows .lrow.hl').length})""")

    # 初期はどのハイライトも非表示（display:none）
    s0 = state()
    check(s0["col"] == "none" and s0["row"] == "none" and s0["lcol"] == "none"
          and s0["dhl"] == 0 and s0["rhl"] == 0, f"初期は全ハイライト非表示 → {s0}")

    # --- ガント領域へマウス（ヘッダ下の本体に入れる）---
    rb = pg.query_selector("#right").bounding_box()
    pg.mouse.move(rb["x"] + rb["width"] / 2, rb["y"] + 80)
    pg.wait_for_timeout(60)
    sr = state()
    check(sr["col"] != "none" and sr["dhl"] == 1, f"ガント上：縦=日付列が1つhl（#colHl表示） → {sr}")
    check(sr["row"] != "none" and sr["rhl"] == 1, f"ガント上：横=対象行が1つhl（#rowHl表示） → {sr}")
    check(sr["lcol"] == "none", f"ガント上：左表データ列のhl(#leftColHl)は出ない → {sr}")

    # --- 左表領域へマウス（縦は左表データ列へ切替・日付列hlは消える）---
    lb = pg.query_selector("#left").bounding_box()
    pg.mouse.move(lb["x"] + lb["width"] / 2, lb["y"] + 80)
    pg.wait_for_timeout(60)
    sl = state()
    check(sl["lcol"] != "none", f"左表上：縦=データ列がhl（#leftColHl表示） → {sl}")
    check(sl["row"] != "none" and sl["rhl"] == 1, f"左表上：横=対象行hlは維持 → {sl}")
    check(sl["col"] == "none" and sl["dhl"] == 0, f"左表上：日付列hl(#colHl)は消える（縦は今いるペインへ） → {sl}")

    # ハイライトはクリックを邪魔しない（pointer-events:none）
    pe = pg.evaluate("""()=>['colHl','rowHl','leftColHl'].map(
      id=>getComputedStyle(document.getElementById(id)).pointerEvents)""")
    check(all(v == "none" for v in pe), f"オーバーレイは pointer-events:none（操作を遮らない） → {pe}")

    b.close()
finish(errors)
