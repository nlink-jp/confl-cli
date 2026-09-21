# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`ccli` is a CLI tool for operating Atlassian Confluence Cloud from the command line.
Built with Python + uv, following UNIX philosophy (pipe-friendly, stdout/stderr separation).

See `docs/en/spec.md` for detailed specifications and `docs/en/plan.md` for the development roadmap. The Japanese counterparts are `docs/ja/spec.ja.md` and `docs/ja/plan.ja.md`.

## Development Commands

```bash
# Install dependencies (including dev tools)
uv sync --all-extras

# Run all tests
uv run pytest

# Run a single test file
uv run pytest tests/test_config.py -v

# Run tests with coverage
uv run pytest --cov=ccli --cov-report=term-missing

# Lint
uv run ruff check .

# Format
uv run ruff format .

# Type check
uv run mypy src/

# Run the CLI (development)
uv run confl-cli --help
```

## Project Rules

- **Security first**: Never accept credentials via CLI arguments. Use environment variables or config file (`~/.config/ccli/config.toml`, permissions 600).
- **Test with implementation**: Every source file must have a corresponding test file. Write tests alongside the code, not after.
- **Test before commit**: All tests must pass before committing.
- **Small and focused**: Keep functions small. Fix bugs in the smallest possible scope.
- **Update docs with features**: When adding or changing features, update `docs/en/spec.md` and `docs/ja/spec.ja.md`, `README.md` and `README.ja.md`, and `CHANGELOG.md`. A document and its translation change in the same commit.
- **Changelog required**: Every change goes into `CHANGELOG.md` under `[Unreleased]`.

## Architecture

```
src/ccli/
├── main.py            # Typer app entry point; version via importlib.metadata
├── config.py          # Config loading: env vars → config file fallback
├── auth.py            # Builds authenticated httpx client
├── exceptions.py      # Custom exceptions with exit codes
├── downloader.py      # Streaming file download with retry; safe_attachment_dest
├── client/            # Confluence REST API wrappers (httpx)
│   ├── base.py        # Base client: auth, retry, rate-limit handling
│   ├── spaces.py      # v2 /spaces endpoints
│   ├── pages.py       # v1/v2 /pages endpoints (search, get, tree)
│   └── attachments.py # v1 /attachments endpoints + streaming download
├── commands/          # Typer command definitions (thin layer over client)
│   ├── spaces.py
│   ├── pages.py
│   └── config.py
├── formatters/        # Output rendering (text/json/html)
│   ├── base.py        # Detects tty; routes to appropriate formatter
│   ├── text.py        # Rich-based colored/table output; UTC→local time conversion
│   ├── json_fmt.py    # JSON serialization to stdout
│   └── html_fmt.py    # Raw HTML output
└── converters/
    └── html_to_text.py  # HTML → Markdown via markdownify
```

### Key Design Decisions

**stdout/stderr separation**: Data goes to stdout; progress, warnings, and errors go to stderr. This allows `confl-cli pages get ID --format json | jq '.'` to work correctly.

**tty auto-detection**: When stdout is not a tty (pipe/redirect), color and table formatting are automatically disabled. `--no-color` and the `NO_COLOR` env var also disable it.

**Config priority**: `CONFLUENCE_URL` / `CONFLUENCE_USERNAME` / `CONFLUENCE_API_TOKEN` environment variables take precedence over `~/.config/ccli/config.toml`.

**Error exit codes**: Defined in `exceptions.py` — 1=auth failure, 2=forbidden, 3=not found, 4=network error, 5=rate limit, 6=config error, 99=unexpected. Scripts can branch on these.

**Rate limit retry**: The base client retries on HTTP 429 with exponential backoff (max 3 attempts). 5xx and network errors are also retried.

**Attachment storage**: Saved under `<output-dir>/<page-id>/<filename>`. In JSON output, the `saved_path` field reflects the actual saved location.

**Tree API strategy**: `pages tree` uses the v1 REST API for all node metadata — `GET /wiki/rest/api/content/{id}?expand=version,history` for the root and `GET /wiki/rest/api/content/{id}/child/page?expand=version,history` for children. This is the only way to get `version.when` (updated_at), `history.createdDate` (created_at), and `_links.webui` (url) in a single request. The Confluence v2 `/pages/{id}/children` endpoint returns none of these fields.

**Timestamp display**: JSON output always stores raw UTC ISO 8601 strings. Text formatters (`formatters/text.py`) convert to local time via `_local_dt()` using `datetime.astimezone()`.

**Page content download in tree**: `pages tree --page-format <fmt> --output-dir <dir>` saves each page body to `<dir>/<page-id>/page.md|.html|.json|.xml`. Requires `--output-dir`. Compatible with `--attachments`.

## Key Libraries

| Library | Purpose |
|---------|---------|
| Typer | CLI framework (type-hint based) |
| httpx | HTTP client (sync, streaming support) |
| Rich | Terminal output (tables, colors, tty-aware) |
| Pydantic v2 | API response models and validation |
| markdownify | HTML → Markdown conversion |
| tomllib | Config file parsing (stdlib, Python 3.11+) |
| pytest-httpx | Mock httpx requests in tests |
