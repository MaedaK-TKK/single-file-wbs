"""ガント予実バー（#65/#34）: 予定=背景帯／実績=前面バー／終了遅延=赤over+「+N」／着手遅れ=薄赤gap。
   golden は本日依存の使い捨てなので、こちらは『バー種別の有無』と『+N ラベル値』を構造的に固定する
   （px幾何は撮らない＝DAY_W/原点に依存しない・本日に依存しないケースを主軸に）。"""
import datetime
from playwright.sync_api import sync_playwright
from common import VIEWER, check, finish, leaf

TODAY = datetime.date.today()
def rel(days):
    return (TODAY + datetime.timedelta(days=days)).isoformat()

# フラット構成（タスク直下にリーフのみ）→ grows の非prow行が L1..L6 と同順に並ぶ
DATA = {"projects": [{"name": "P", "milestones": [], "tasks": [
    # L1 予定のみ（実績なし）
    leaf("1", "予定のみ", ps="2026-03-02", pe="2026-03-06"),
    # L2 予定どおり完了（遅延なし・着手遅れなし）
    leaf("2", "順当完了", ps="2026-03-02", pe="2026-03-06", as_="2026-03-02", ae="2026-03-06"),
    # L3 完了したが終了遅延 +3日（予定終了3/06→実績3/09）※本日非依存
    leaf("3", "終了遅延完了", ps="2026-03-02", pe="2026-03-06", as_="2026-03-02", ae="2026-03-09"),
    # L4 着手遅れ（予定3/02→実績3/04開始）して完了・終了は予定内
    leaf("4", "着手遅れ完了", ps="2026-03-02", pe="2026-03-10", as_="2026-03-04", ae="2026-03-09"),
    # L5 進行中・期限内（実績開始のみ・本日が予定内）→ over無し
    leaf("5", "進行中期内", ps=rel(-2), pe=rel(8), as_=rel(-2)),
    # L6 進行中・終了遅延（予定終了が4日前・本日まで未完）→ over有り・+4
    leaf("6", "進行中遅延", ps=rel(-8), pe=rel(-4), as_=rel(-8)),
]}]}

def kinds(bars):
    """['plan','actual cut','over'] → {'plan','actual','over'}（先頭クラスのみ）"""
    return {b.split()[0] for b in bars if b}

errors = []
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1500, "height": 900})
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(VIEWER)
    pg.evaluate("d=>window.renderData(d)", DATA); pg.wait_for_timeout(150)

    rows = pg.evaluate("""()=>[...document.querySelectorAll('#grows .grow')].map(g=>({
      cls:[...g.classList].filter(c=>c!=='grow').join(' '),
      bars:[...g.querySelectorAll('.bar')].map(b=>b.className.replace('bar','').replace(/\\s+/g,' ').trim()),
      delay:(g.querySelector('.delay')?g.querySelector('.delay').textContent:null)
    }))""")
    L = [r for r in rows if "prow" not in r["cls"]]   # プロジェクト帯を除いたリーフ行（L1..L6順）
    check(len(L) == 6, f"リーフ行が6本（grows非prow行）→ {len(L)}")

    # L1 予定のみ＝planバー1本だけ（実績/over/gapは無い）
    check(kinds(L[0]["bars"]) == {"plan"} and L[0]["delay"] is None,
          f"予定のみ＝planのみ・遅延ラベル無し → {L[0]['bars']}")

    # L2 順当完了＝plan+actual、over/gap無し、done行
    check(kinds(L[1]["bars"]) == {"plan", "actual"} and "done" in L[1]["cls"] and L[1]["delay"] is None,
          f"順当完了＝plan+actual・over/gap無し・done → {L[1]['bars']} cls={L[1]['cls']}")

    # L3 終了遅延完了＝over有り・actualはcut・+3（本日非依存）
    check("over" in kinds(L[2]["bars"]) and "actual cut" in L[2]["bars"] and L[2]["delay"] == "+3",
          f"終了遅延＝over+actual.cut・ラベル+3 → bars={L[2]['bars']} delay={L[2]['delay']}")

    # L4 着手遅れ＝gap有り・over無し
    check("gap" in kinds(L[3]["bars"]) and "over" not in kinds(L[3]["bars"]),
          f"着手遅れ＝gap有り・over無し → {L[3]['bars']}")

    # L5 進行中・期限内＝actual有り・over無し（着手ズレは出さない仕様）
    check("actual" in kinds(L[4]["bars"]) and "over" not in kinds(L[4]["bars"]) and L[4]["delay"] is None,
          f"進行中期内＝actual・over無し・遅延ラベル無し → {L[4]['bars']}")

    # L6 進行中・終了遅延＝over有り・+4（本日基準でpe+4日）
    check("over" in kinds(L[5]["bars"]) and L[5]["delay"] == "+4",
          f"進行中遅延＝over・ラベル+4（本日まで） → bars={L[5]['bars']} delay={L[5]['delay']}")

    # ラベルは数字のみ（「日」「進行中」を含まない＝最小表記）。正確値はツールチップへ
    check(all((r["delay"] is None) or (r["delay"].startswith("+") and r["delay"][1:].isdigit())
              for r in L), "遅延ラベルは『+数字』のみ（単位/状態語を含まない）")

    # ツールチップ（title）には正確な「終了遅延 +N日」が残る
    tip = pg.evaluate("""()=>{const b=[...document.querySelectorAll('#grows .grow')]
      .flatMap(g=>[...g.querySelectorAll('.bar.over')]); return b.length?b[0].getAttribute('title'):null;}""")
    check(tip and "終了遅延" in tip, f"overバーのtitleに『終了遅延 +N日』が残る → {tip!r}")

    b.close()
finish(errors)
