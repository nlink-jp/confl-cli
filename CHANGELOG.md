# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-03-25

### Added
- Project scaffolding: `pyproject.toml`, MIT license, `.gitignore`, `CLAUDE.md`
- Exception hierarchy (`CCLIError` and subclasses) with typed exit codes (1–6)
- Configuration system: env vars (`CONFLUENCE_URL/USERNAME/API_TOKEN`) and TOML file (`~/.config/ccli/config.toml`); `config init` / `config show` commands
- HTTP client with Basic Auth, 30 s timeout, and automatic 429 retry with exponential backoff
- Spaces commands: `spaces list` (paginated), `spaces search` (client-side substring match)
- Pages commands: `pages search` (CQL full-text), `pages get` (text/html/json/storage formats), `pages tree` (recursive with optional depth limit)
- Confluence Storage Format output (`--format storage`) exposing the raw XHTML-like internal format
- Attachment support: `--attachments` flag fetches metadata; `--output-dir` streams downloads to disk for both `pages get` and `pages tree`
- Path-traversal defense in `safe_attachment_dest`: basename stripping, null-byte removal, degenerate name rejection, page-id sanitisation, and `is_relative_to()` final guard
- TTY-aware output: Rich tables/tree with color when stdout is a terminal; plain text when piped; `NO_COLOR` respected
- 124 tests, 94 % line coverage; ruff and mypy (strict) clean
