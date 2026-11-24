.PHONY: test lint vuln

test:
	uv run --extra dev pytest

lint:
	uv run --extra dev ruff check src tests
	uv run --extra dev ruff format --check src tests
	uv run --extra dev mypy src

# vuln: known advisories in the locked dependencies; exits 1 on a finding.
# Run before tagging a release (CONVENTIONS §Release Checklist).
vuln:
	uv audit --frozen --preview-features audit-command
