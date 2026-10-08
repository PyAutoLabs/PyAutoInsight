from copy import deepcopy

import pytest
import yaml

from insight import board, decisions


def row(key="solver", day="2026-10-08", repo="PyAutoInsight"):
    return {
        "id": key,
        "title": "NNLS <solver> & choice",
        "date": day,
        "url": f"https://github.com/PyAutoLabs/{repo}/blob/main/decisions/{key}.md",
    }


def write(root, rows):
    (root / "decisions.yaml").write_text(yaml.safe_dump({"decisions": rows}))
    (root / "decisions").mkdir(exist_ok=True)
    for item in rows:
        (root / "decisions" / f"{item['id']}.md").write_text(
            f"# {item['title']}\n\nDate: {item['date']}\n"
        )


def test_records_sorted_and_cross_organ_has_one_canonical_url(tmp_path):
    rows = [row("old", "2026-09-01"), row("new", repo="PyAutoPulse")]
    write(tmp_path, rows)
    (tmp_path / "decisions/new.md").unlink()
    loaded = decisions.load(tmp_path)
    assert [r["id"] for r in loaded] == ["new", "old"]
    html = decisions.render_html(loaded)
    assert 'target="_blank" rel="noopener"' in html
    assert "NNLS &lt;solver&gt; &amp; choice" in html
    assert "NNLS <solver>" not in html
    assert loaded[0]["url"] in html
    assert loaded[0]["url"] in decisions.markdown(loaded)


@pytest.mark.parametrize(
    "mutation",
    [
        {"url": "javascript:alert(1)"},
        {"url": "https://github.com.evil/PyAutoLabs/PyAutoInsight/blob/main/decisions/solver.md"},
        {"url": "https://github.com/PyAutoLabs/PyAutoInsight/blob/main/decisions/other.md"},
        {"date": "2026-02-30"},
        {"date": "2026-1-01"},
        {"id": "../escape"},
        {"title": "bad\nheading"},
        {"extra": "typo"},
    ],
)
def test_invalid_index_rejected(tmp_path, mutation):
    entry = row()
    entry.update(mutation)
    (tmp_path / "decisions.yaml").write_text(yaml.safe_dump({"decisions": [entry]}))
    with pytest.raises(ValueError):
        decisions.load(tmp_path)


def test_duplicate_missing_and_mismatched_owned_records(tmp_path):
    entry = row()
    write(tmp_path, [entry, deepcopy(entry)])
    with pytest.raises(ValueError, match="duplicate"):
        decisions.load(tmp_path)
    write(tmp_path, [entry])
    (tmp_path / "decisions/solver.md").write_text("# Different\nDate: 2026-10-08\n")
    with pytest.raises(ValueError, match="differ"):
        decisions.load(tmp_path)
    (tmp_path / "decisions/solver.md").unlink()
    with pytest.raises(ValueError, match="Missing"):
        decisions.load(tmp_path)


def test_board_disclosure_and_markdown_include_history(monkeypatch):
    monkeypatch.setattr(decisions, "load", lambda: [row(repo="PyAutoPulse")])
    html = board.render_html([])
    assert 'href="#decision-history"' in html
    assert 'id="decision-history"' in html
    assert "NNLS &lt;solver&gt; &amp; choice" in html
    assert "Decision History" in board.render_markdown([])
    assert row(repo="PyAutoPulse")["url"] in board.render_markdown([])
    monkeypatch.setattr(decisions, "load", lambda: [])
    assert "No decisions recorded yet." in board.render_html([])


def test_cli_rejects_invalid_decision_index(monkeypatch, capsys):
    from insight import cli

    def invalid():
        raise ValueError("broken decision index")

    monkeypatch.setattr(decisions, "load", invalid)
    assert cli.main(["check", "--offline"]) == 1
    assert "FAIL decisions: broken decision index" in capsys.readouterr().out
