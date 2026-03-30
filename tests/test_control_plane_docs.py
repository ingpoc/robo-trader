from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
AGENTS_PATH = REPO_ROOT / "AGENTS.md"
DOCS_INDEX_PATH = REPO_ROOT / "docs" / "README.md"
TESTS_README_PATH = REPO_ROOT / "tests" / "README.md"
VALIDATOR_README_PATH = REPO_ROOT / "tests" / "validator" / "README.md"
REMOVED_FILES = (
    REPO_ROOT / "tests" / "validator" / "UI_FUNCTIONAL_TESTING_REFERENCE.md",
    REPO_ROOT / "docs" / "agent-sdk-skills-archive" / "market-monitor" / "SKILL.md",
    REPO_ROOT / "docs" / "agent-sdk-skills-archive" / "portfolio-analysis" / "SKILL.md",
    REPO_ROOT / "docs" / "agent-sdk-skills-archive" / "risk-management" / "SKILL.md",
    REPO_ROOT / "docs" / "agent-sdk-skills-archive" / "trade-execution" / "SKILL.md",
)
VALIDATION_DOCS = (
    REPO_ROOT / "tests" / "services" / "VALIDATION_STRATEGY.md",
    REPO_ROOT / "tests" / "validator" / "README.md",
)
FORBIDDEN_CLAUDE_MARKERS = (
    "## Rules",
    "## Critical Rules",
    "## Workflow",
    "## Startup Ritual",
    "## First Thing",
    "## Project Purpose",
    "## Role Separation",
    "## Two-Agent System",
)


def _repo_claude_files() -> list[Path]:
    return sorted(REPO_ROOT.rglob("CLAUDE.md"))


def test_agents_md_avoids_publish_baseline_reference() -> None:
    content = AGENTS_PATH.read_text()

    assert "Organization/reports/publish" not in content
    assert "docs/workflow/zerodha-broker-control-plane.md" in content
    assert "docs/workflow/codex-runtime-control-plane.md" in content


def test_repo_claude_files_are_adapter_only() -> None:
    claude_files = _repo_claude_files()

    assert claude_files, "Expected repo-local CLAUDE.md files to exist."

    for path in claude_files:
        content = path.read_text()
        nonempty_lines = [line for line in content.splitlines() if line.strip()]

        assert "Canonical local policy: repo-local `AGENTS.md`" in content, path
        assert "Policy mode: `defer_to_agents`" in content, path
        assert "Follow repo-local `AGENTS.md` first." in content, path
        assert len(nonempty_lines) <= 12, path
        for marker in FORBIDDEN_CLAUDE_MARKERS:
            assert marker not in content, f"{path} contains forbidden marker: {marker}"


def test_validation_docs_stay_reference_only() -> None:
    for path in VALIDATION_DOCS:
        content = path.read_text()

        assert "Backtracking Functional Validation" not in content, path
        assert "Testing Methodology" not in content, path
        assert "docs/workflow/browser-testing-control-plane.md" in content, path


def test_docs_index_does_not_reference_removed_setup_guides() -> None:
    content = DOCS_INDEX_PATH.read_text()

    assert "ZERODHA_OAUTH_SETUP.md" not in content
    assert "CLAUDE_SDK_SETUP_GUIDE.md" not in content


def test_stale_validation_and_archive_files_are_removed() -> None:
    assert "UI_FUNCTIONAL_TESTING_REFERENCE.md" not in TESTS_README_PATH.read_text()
    assert "UI_FUNCTIONAL_TESTING_REFERENCE.md" not in VALIDATOR_README_PATH.read_text()
    for path in REMOVED_FILES:
        assert not path.exists(), path
