from __future__ import annotations

from pathlib import Path

from torhubgen.selfcheck import perform_selfcheck


def write_required_docs(root: Path) -> None:
    (root / "docs").mkdir()
    (root / "readme.md").write_text("stub", encoding="utf-8")
    (root / "docs" / "threat-model.md").write_text("stub", encoding="utf-8")
    (root / "docs" / "development_process.md").write_text("stub", encoding="utf-8")


def test_selfcheck_reports_missing_tor_binary_without_hiding_other_checks(tmp_path: Path) -> None:
    write_required_docs(tmp_path)
    report = perform_selfcheck(project_root=tmp_path, which=lambda _: None)

    assert report.item("tor_binary").status == "failed"
    assert report.item("temp_directory").status == "ok"
    assert report.item("localhost_binding").status == "ok"
    assert report.item("lifetime_cap").status == "ok"
    assert report.item("required_docs").status == "ok"
    assert report.item("persistent_onion_keys").status == "ok"
