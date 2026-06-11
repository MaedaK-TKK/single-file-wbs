"""備考のURL自動リンク: URLそのまま表示・クエリ付きURL・javascript:不リンク・HTML注入エスケープ維持"""
from playwright.sync_api import sync_playwright
from common import VIEWER, check, finish, leaf

def L(id, note):
    return leaf(id, "t"+id, ps="2026-06-01", pe="2026-06-05") | {"note": note}

URL1 = "https://github.com/example/repo/issues/16"
URL2 = "https://example.com/spec?a=1&b=2"
DATA = {"projects": [{"name": "P", "milestones": [], "tasks": [
    L("1", URL1 + " 構造化"),
    L("2", "仕様: " + URL2),
    L("3", "javascript:alert(1) は無効"),
    L("4", '<script>alert(1)</script> <a href="x">注入</a>'),
]}]}

errors = []
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page()
    pg.on("pageerror", lambda e: errors.append(str(e)))
    dlg = []
    pg.on("dialog", lambda d: (dlg.append(1), d.dismiss()))
    pg.goto(VIEWER)
    pg.evaluate("d=>window.renderData(d)", DATA); pg.wait_for_timeout(150)
    cells = pg.query_selector_all("#leftRows .lrow.leaf .c.note")   # leaf行のみ（プロジェクト行を除外）

    a1 = cells[0].query_selector("a")
    check(a1 is not None and a1.inner_text() == URL1 and a1.get_attribute("href") == URL1,
          "URLがそのままリンク表示される")
    check(a1.get_attribute("target") == "_blank" and "noopener" in (a1.get_attribute("rel") or ""),
          "target=_blank と rel=noopener が付く")
    check("構造化" in cells[0].inner_text(), "URL以外のテキストは残る")

    a2 = cells[1].query_selector("a")
    check(a2 is not None and a2.get_attribute("href") == URL2 and a2.inner_text() == URL2,
          "クエリ（&）付きURLも切れずにリンク化")

    check(cells[2].query_selector("a") is None, "javascript: はリンク化しない")
    check(cells[3].query_selector("a") is None and not dlg
          and "<script>" in cells[3].inner_text(),
          "HTML/scriptタグ注入はエスケープ表示のまま（実行されない）")
    b.close()
finish(errors)
