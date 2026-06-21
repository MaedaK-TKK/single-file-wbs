"""描画回帰: 2段見出し・イナズマ線座標・NaN無し（tests/正常_終了遅延.json 前提・日付独立の計算式で検証）"""
from datetime import date
from playwright.sync_api import sync_playwright
from common import VIEWER, CLOCK_PIN, check, finish, load_test_json

DAY_W, HALF = 22, 11
def x(d, range_start):
    y, m, dd = map(int, d.split("-"))
    y0, m0, d0 = map(int, range_start.split("-"))
    return round((date(y, m, dd) - date(y0, m0, d0)).days * DAY_W + HALF, 1)

errors = []
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1500, "height": 820})
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    pg.add_init_script(CLOCK_PIN)   # 本日を 2026-06-15 に固定（実日付依存で将来赤くなるのを防ぐ・golden/pixelと統一）
    pg.goto(VIEWER)
    pg.evaluate("d => window.renderData(d)", load_test_json("正常_終了遅延.json"))
    pg.wait_for_timeout(200)

    check(len(pg.query_selector_all("#leftHead .hg")) == 2, "2段見出し（予定/実績）が2グループ")
    poly = pg.get_attribute("#overlay polyline", "points")
    xs = [round(float(pair.split(",")[0]), 1) for pair in poly.strip().split(" ")]
    check(not any(v != v for v in xs), "polyline に NaN 無し")

    today = pg.evaluate("()=>{const n=new Date();return new Date(Date.UTC(n.getFullYear(),n.getMonth(),n.getDate())).toISOString().slice(0,10);}")
    RS = min("2026-05-20", today)  # rangeStart = データ最小日(5/20) と本日の小さい方
    xT = x(today, RS)
    # 期待値（仕様: 完了/期限内=本日線、終了遅延=plan.end、着手遅延=plan.start）
    exp = [xT,
           x("2026-06-05", RS), x("2026-05-30", RS),
           xT if today <= "2026-06-10" else x("2026-06-10", RS),
           x(min("2026-06-05", today), RS) if today > "2026-06-05" else xT,  # 着手遅延は6/5経過後のみ
           xT, xT, xT, xT,
           x("2026-06-04", RS), x("2026-06-06", RS), xT]
    check(xs == exp, f"イナズマ点 x列が仕様どおり\n     得={xs}\n     期={exp}")
    b.close()
finish(errors)
