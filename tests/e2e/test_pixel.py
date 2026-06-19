"""ピクセル回帰（視覚リグレ）: 代表fixtureのスクショを baseline PNG と画素比較。
   PIL非依存＝ブラウザの canvas で面内diff（per-channel差>THRESHの画素割合がTOLを超えたら赤）。
   決定論化: CLOCK_PIN で本日固定・固定ビューポート・device_scale_factor=1・同一Chromium。

   生成:  python test_pixel.py --generate   → tests/e2e/baseline/<fixture>.png を書き出し
   検証:  python test_pixel.py             → baseline と比較（run_all はこちら）
   ※ baseline は『このChromiumでの見た目』。意図的に表示を変えたら --generate で撮り直してコミット。

   注意（正直）: 画素比較は環境依存（別マシン/別Chromiumのfont描画差で偽陽性）。
   このリポでは固定環境での実行を前提とし、TOLでサブピクセルのにじみを吸収する。"""
import base64
import pathlib
import sys
from common import VIEWER, CLOCK_PIN, check, finish, load_test_json
from playwright.sync_api import sync_playwright

BASE_DIR = pathlib.Path(__file__).resolve().parent / "baseline"
FIXTURES = ["正常_終了遅延.json", "正常_4階層ネスト.json",
            "正常_複数4プロジェクト.json", "正常_カスタムキー.json"]
VIEWPORT = {"width": 1500, "height": 900}
THRESH = 16          # per-channel 差の許容（サブピクセルのにじみ）
TOL_RATIO = 0.001    # 不一致画素が全体の 0.1% を超えたら回帰とみなす

DIFF_JS = r"""async ([baseURL, curURL, thresh]) => {
  const load = src => new Promise((res, rej) => {
    const im = new Image(); im.onload = () => res(im); im.onerror = rej; im.src = src; });
  const [a, b] = await Promise.all([load(baseURL), load(curURL)]);
  if (a.width !== b.width || a.height !== b.height)
    return {dim: false, aw: a.width, ah: a.height, bw: b.width, bh: b.height};
  const cv = document.createElement('canvas'); cv.width = a.width; cv.height = a.height;
  const cx = cv.getContext('2d', {willReadFrequently: true});
  cx.drawImage(a, 0, 0); const da = cx.getImageData(0, 0, a.width, a.height).data;
  cx.clearRect(0, 0, a.width, a.height);
  cx.drawImage(b, 0, 0); const db = cx.getImageData(0, 0, a.width, a.height).data;
  let mism = 0;
  for (let i = 0; i < da.length; i += 4) {
    const d = Math.max(Math.abs(da[i]-db[i]), Math.abs(da[i+1]-db[i+1]), Math.abs(da[i+2]-db[i+2]));
    if (d > thresh) mism++;
  }
  return {dim: true, mism, total: da.length / 4, w: a.width, h: a.height};
}"""


def shot(pg, fixture):
    pg.evaluate("d => window.renderData(d)", load_test_json(fixture))
    pg.wait_for_timeout(150)
    return pg.screenshot(full_page=True)


def data_url(png_bytes):
    return "data:image/png;base64," + base64.b64encode(png_bytes).decode()


def main():
    generate = "--generate" in sys.argv
    BASE_DIR.mkdir(exist_ok=True)
    errors = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport=VIEWPORT, device_scale_factor=1)
        pg.add_init_script(CLOCK_PIN)
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.goto(VIEWER)
        for fx in FIXTURES:
            cur = shot(pg, fx)
            bpath = BASE_DIR / (fx.replace(".json", "") + ".png")
            if generate:
                bpath.write_bytes(cur)
                print(f"  baseline: {bpath.name} ({len(cur)} bytes)")
                continue
            if not bpath.exists():
                check(False, f"{fx}: baseline 不在（--generate で生成を）")
                continue
            r = pg.evaluate(DIFF_JS, [data_url(bpath.read_bytes()), data_url(cur), THRESH])
            if not r["dim"]:
                check(False, f"{fx}: 画像サイズ不一致 base={r['aw']}x{r['ah']} cur={r['bw']}x{r['bh']}（レイアウト変化）")
                continue
            ratio = r["mism"] / r["total"]
            check(ratio <= TOL_RATIO,
                  f"{fx}: 不一致 {r['mism']}/{r['total']} 画素 = {ratio*100:.3f}% (許容 {TOL_RATIO*100:.2f}%・{r['w']}x{r['h']})")
        b.close()
    if generate:
        print("baseline 生成完了")
        return
    finish(errors)


if __name__ == "__main__":
    main()
