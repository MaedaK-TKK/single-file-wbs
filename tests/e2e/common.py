"""E2Eテスト共通ヘルパー（依存: playwright のみ）"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]   # リポジトリルート
VIEWER = (ROOT / "wbs_viewer.html").as_uri()

_failures = []

def check(cond, msg):
    print(("OK  " if cond else "FAIL") + " " + msg)
    if not cond:
        _failures.append(msg)

def finish(errors=None):
    """JSエラーとFAILを集計して終了コードを返す"""
    errors = [e for e in (errors or []) if e]
    if errors:
        print("=== JSエラー ===", errors)
    print("=== RESULT ===", "ALL PASS" if not _failures and not errors
          else f"{len(_failures)} FAIL + {len(errors)} error")
    sys.exit(1 if (_failures or errors) else 0)

def load_test_json(name):
    return json.loads((ROOT / "tests" / name).read_text(encoding="utf-8"))

def leaf(id, name, asg="", ps=None, pe=None, as_=None, ae=None, qty=1, hours=8):
    return {"id": id, "name": name, "qty": qty, "hours": hours, "assignee": asg,
            "plan": {"start": ps, "end": pe},
            "actual": {"start": as_, "end": ae}, "note": ""}

# 本日を固定する init script。todayStr() は描画毎に new Date() を呼ぶので、これで
# イナズマ線・進行中バー等「本日依存」の描画を決定論化＝コミット可能なゴールデン/ピクセル基準が作れる。
PINNED_TODAY = "2026-06-15"
CLOCK_PIN = """(()=>{const FIXED=Date.UTC(2026,5,15,0,0,0);const _D=Date;
function F(...a){return a.length===0?new _D(FIXED):new _D(...a);}
F.prototype=_D.prototype;F.now=()=>FIXED;F.UTC=_D.UTC;F.parse=_D.parse;window.Date=F;})();"""


def new_page(browser, clock=CLOCK_PIN, **kwargs):
    """本日固定(CLOCK_PIN)を既定で注入したページを返す。

    テストの本日をビルド時刻に依存させない＝既定でドリフト不能にするための入口。
    本日依存の値（残り営業日・slip・イナズマ座標・進捗%）を断言しても、固定本日で安定する。
    実日（実行日）が必要なテスト（done/gantt_bars/date_shorthand）だけ clock=None で opt-out する。
    """
    pg = browser.new_page(**kwargs)
    if clock:
        pg.add_init_script(clock)
    return pg


def granted_handle_init(data):
    """書込可のフェイクFSAハンドル（メモリ上のファイル）。window.__file に内容、__writes に書込回数"""
    return """
window.__file = %s; window.__writes = 0;
const fh = {kind:'file',
  getFile: async()=> new File([window.__file],'wbs.json',{type:'application/json',lastModified:window.__mt||1000}),
  queryPermission: async()=>'granted', requestPermission: async()=>'granted',
  createWritable: async()=>{let b=null;return {write:async s=>{b=s;},abort:async()=>{},
    close:async()=>{window.__file=b;window.__mt=(window.__mt||1000)+1;window.__writes++;}}}};
window.showOpenFilePicker = async()=>[fh];
""" % json.dumps(json.dumps(data, ensure_ascii=False))
