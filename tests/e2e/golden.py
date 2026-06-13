"""ゴールデンマスター（characterization）: 全fixtureの『値レベルの描画結果』を凍結。
   生のHTMLでなく、画面が表現する値（セルテキスト・バー幾何・座標）を撮る＝
   属性順など無害な差では赤くせず、見た目に出る挙動変化だけを検出する。

   使い方:
     生成:  python golden.py --generate   → tests/e2e/golden.json を書き出し
     検証:  python golden.py             → golden.json と現在の描画を比較（差分ゼロでPASS）

   #16リファクタの『挙動を1バイトも変えない』を機械保証する使い捨ての網。
   表示仕様を意図的に変えたら --generate で撮り直す。"""
import json
import pathlib
import sys
from playwright.sync_api import sync_playwright
from common import ROOT, VIEWER

GOLDEN = pathlib.Path(__file__).resolve().parent / "golden.json"
FIXTURES = sorted((ROOT / "tests").glob("正常_*.json")) + sorted((ROOT / "tests").glob("異常_*.json"))

# 画面が表現する値だけを抽出（innerHTML全体ではなく意味のある中間表現）
CAPTURE = r"""()=>{
  const txt = el => (el ? el.innerText : null);
  const rows = [...document.querySelectorAll('#leftRows .lrow')].map(r=>({
    cls: [...r.classList].filter(c=>c!=='lrow').join(' '),
    cells: [...r.querySelectorAll('.c')].map(c=>c.innerText),
    links: [...r.querySelectorAll('.c.note a')].map(a=>a.getAttribute('href')),
  }));
  const bars = [...document.querySelectorAll('#grows .bar')].map(b=>({
    kind: b.className.replace('bar','').trim(),
    left: b.style.left, width: b.style.width,
  }));
  const ov = document.querySelector('#overlay');
  const poly = ov ? (ov.querySelector('polyline')||{}).getAttribute?.('points') : null;
  const ms = ov ? [...ov.querySelectorAll('rect')].map(r=>r.getAttribute('fill')) : [];
  const header = [...document.querySelectorAll('#leftHead .h, #leftHead .hgt, #leftHead .hsub')].map(h=>h.innerText);
  // stat(読込時刻)は実行ごとに変わる時計なので撮らない。poly/in-progressバーは本日依存だが同セッション内の生成→検証では一定
  return {rows, bars, poly, ms, header};
}"""

def capture_all():
    out = {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1500, "height": 900})
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(VIEWER)
        for fx in FIXTURES:
            data = json.loads(fx.read_text(encoding="utf-8"))
            pg.evaluate("d => window.renderData(d)", data)
            pg.wait_for_timeout(150)
            out[fx.name] = pg.evaluate(CAPTURE)
        b.close()
        if errs:
            print("=== JSエラー（撮影中）===", errs)
            sys.exit(2)
    return out

def main():
    cur = capture_all()
    if "--generate" in sys.argv:
        GOLDEN.write_text(json.dumps(cur, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"ゴールデン生成: {GOLDEN}  ({len(cur)} fixtures)")
        return
    if not GOLDEN.exists():
        print("golden.json が無い。先に --generate で生成してください。")
        sys.exit(1)
    gold = json.loads(GOLDEN.read_text(encoding="utf-8"))
    diffs = []
    for name in sorted(set(cur) | set(gold)):
        if cur.get(name) != gold.get(name):
            diffs.append(name)
    if diffs:
        print("=== ゴールデン不一致（挙動が変わった）===")
        for name in diffs:
            print(f"  ✗ {name}")
            g, c = gold.get(name, {}), cur.get(name, {})
            for key in sorted(set(g) | set(c)):
                if g.get(key) != c.get(key):
                    print(f"      [{key}] 期待={json.dumps(g.get(key), ensure_ascii=False)[:120]}")
                    print(f"            現在={json.dumps(c.get(key), ensure_ascii=False)[:120]}")
        sys.exit(1)
    print(f"=== ゴールデン一致: {len(cur)} fixtures 全て挙動不変 ===")

if __name__ == "__main__":
    main()
