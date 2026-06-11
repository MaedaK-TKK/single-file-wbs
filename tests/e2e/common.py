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
