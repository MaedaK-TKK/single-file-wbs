"""ゴールデンマスター回帰（run_all 標準ゲート）: golden.json（コミット済みベースライン）と
   現在の描画が完全一致することを確認。差分が出たら『意図しない見た目の変化』として赤くする。
   表示仕様を意図的に変えたら golden.py --generate で撮り直し、差分をレビューしてコミット。"""
from common import check, finish
import golden

errors = []
try:
    cur = golden.capture_all()
    diffs = golden.diff_against_golden(cur)
    check(not diffs, f"ゴールデン {len(cur)} スナップショット 全一致（差分: {diffs}）")
except SystemExit as e:
    # capture_all は JSエラーで、diff_against_golden は golden.json 不在で sys.exit する
    errors.append(f"golden 実行が中断（exit={e.code}・JSエラー or golden.json 不在）")
finish(errors)
