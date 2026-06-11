# E2E テスト（headless Chromium / Playwright）

`wbs_viewer.html` の描画・編集・保存・権限フローを headless Chromium で検証します。
File System Access API はフェイクハンドルで模擬しているため、**実ファイルには一切書き込みません**。

## 実行方法

```bash
pip install playwright
playwright install chromium
python tests/e2e/run_all.py        # 全部
python tests/e2e/test_render.py    # 個別
```

## スイート一覧

| ファイル | 検証内容 |
|---|---|
| test_render.py | 2段見出し・イナズマ線の座標（仕様式で日付非依存）・NaN無し |
| test_edit.py | 編集パイプライン（保存・`_`キー保持・id採番・同期render・旧形式変換・誤上書き防止・外部変更検知） |
| test_collapse.py | 全体caret（▼▶/状態依存tooltip/全展開・全たたみ/Ctrl+Z復旧） |
| test_dates.py | 日付欄（ISO固定表示・📅連携・スラッシュ正規化・範囲外拒否） |
| test_permissions.py | file://権限フロー（保存ピッカー/ジェスチャー再試行/選択時切り詰めへの即書込/案内バー） |
| test_load.py | D&D読込の堅牢性（空ファイルのエラー表示・ハンドル空読みフォールバック） |
| test_ui.py | 保存状態表示の遷移・クリックターゲット寸法 |
| test_i18n.py | 言語切替（EN/日本語・localStorage記憶） |

注意: 実ブラウザの保存ダイアログ・権限UIは headless では検証できません。
Chrome メジャー更新後は実機での30秒スモーク（開く→編集ON→1編集→保存済表示）を推奨します。
