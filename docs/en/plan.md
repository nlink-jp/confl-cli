# ccli development plan

## Development approach

- Build small, fix small: every phase stays in a state that can be released on its own
- Tests and implementation move together: every implementation file gets a matching test file, always as a pair
- Confirm the tests pass before committing

## Phases

### Phase 0: Project foundation ✅
**Goal**: establish the development environment and the project structure

- [x] Write the detailed specification (`docs/en/spec.md`)
- [x] Write the development plan (`docs/en/plan.md`)
- [x] Write `pyproject.toml` (dependencies and build settings)
- [x] Create the directory structure
- [x] Initialize `CHANGELOG.md`
- [x] Write `README.md`
- [x] Write `CLAUDE.md`
- [x] Write `.gitignore`
- [x] Confirm the uv environment is set up

### Phase 1: Configuration and authentication foundation ✅
**Goal**: manage credentials safely and confirm the connection to the Confluence API

Implementation:
- `src/ccli/config.py`: configuration handling (environment variables, falling back to the config file)
- `src/ccli/auth.py`: building the authenticated client
- `src/ccli/client/base.py`: the base class of the httpx-based API client

Tests:
- `tests/test_config.py`: environment variables, file loading, precedence
- `tests/test_client/test_base.py`: authentication headers, error handling

Done when: `ccli config show` / `ccli config init` work

### Phase 2: Spaces features ✅
**Goal**: listing and searching spaces

Implementation:
- `src/ccli/client/spaces.py`: the Spaces API client
- `src/ccli/commands/spaces.py`: the CLI command definitions
- `src/ccli/formatters/spaces.py`: the text/json output formatters

Tests:
- `tests/test_client/test_spaces.py`: parsing API responses, pagination
- `tests/test_commands/test_spaces.py`: end-to-end tests of the CLI command (with mocks)

Done when: `ccli spaces list` / `ccli spaces search` work

### Phase 3: Fetching a single page ✅
**Goal**: searching for pages and fetching one of them (text/html/json/storage output)

Implementation:
- `src/ccli/client/pages.py`: the Pages API client (search, get)
- `src/ccli/commands/pages.py`: the CLI command definitions (search, get)
- `src/ccli/formatters/pages.py`: the text/html/json formatters
- `src/ccli/converters/html_to_text.py`: HTML → Markdown/text conversion

Tests:
- `tests/test_client/test_pages.py`
- `tests/test_commands/test_pages.py`
- `tests/test_converters/test_html_to_text.py`

Done when: `ccli pages search` / `ccli pages get` work

### Phase 4: Fetching a page tree ✅
**Goal**: fetching child pages recursively

Implementation:
- Add `get_children()` / `get_tree()` to `src/ccli/client/pages.py`
- Add the `tree` subcommand to `src/ccli/commands/pages.py`
- Add tree rendering to `src/ccli/formatters/pages.py`

Tests:
- Tests of the depth limit
- A guard against circular references (as a precaution)

Done when: `ccli pages tree` works

### Phase 5: Fetching attachments ✅
**Goal**: fetching and saving the attachments tied to a page

Implementation:
- `src/ccli/client/attachments.py`: the Attachments API client
- `src/ccli/downloader.py`: streaming download

Tests:
- `tests/test_client/test_attachments.py`
- `tests/test_downloader.py`: streaming behaviour, building the save path

Done when: `ccli pages get --attachments` / `ccli pages tree --attachments` work

### Phase 6: Quality and finishing ✅
**Goal**: bringing it up to release quality

- [x] Every ruff error cleared (UP045, UP042, B904, B008 configuration, E741, E501)
- [x] mypy strict mode passes (pydantic plugin added)
- [x] Test coverage 94% (above the 80% target)
- [x] CHANGELOG.md records every phase
- [x] README.md and README.ja.md (both languages) given their final update
- [x] docs/en/plan.md marked complete for every phase

## Directory structure

```
ccli/
├── pyproject.toml
├── uv.lock
├── .python-version
├── .gitignore
├── README.md
├── CHANGELOG.md
├── CLAUDE.md
├── docs/
│   ├── en/
│   │   ├── spec.md
│   │   └── plan.md
│   └── ja/
│       ├── spec.ja.md
│       └── plan.ja.md
├── src/
│   └── ccli/
│       ├── __init__.py
│       ├── main.py            # Typer application entry point
│       ├── config.py          # configuration handling
│       ├── auth.py            # authentication
│       ├── exceptions.py      # custom exceptions
│       ├── client/
│       │   ├── __init__.py
│       │   ├── base.py        # httpx base client
│       │   ├── spaces.py      # Spaces API
│       │   ├── pages.py       # Pages API
│       │   └── attachments.py # Attachments API
│       ├── commands/
│       │   ├── __init__.py
│       │   ├── spaces.py      # the spaces subcommands
│       │   ├── pages.py       # the pages subcommands
│       │   └── config.py      # the config subcommands
│       ├── formatters/
│       │   ├── __init__.py
│       │   ├── base.py        # formatter base class
│       │   ├── text.py        # text output
│       │   ├── json_fmt.py    # json output
│       │   └── html_fmt.py    # html output
│       ├── converters/
│       │   ├── __init__.py
│       │   └── html_to_text.py
│       └── downloader.py      # streaming download
└── tests/
    ├── conftest.py
    ├── test_config.py
    ├── test_client/
    │   ├── __init__.py
    │   ├── test_base.py
    │   ├── test_spaces.py
    │   ├── test_pages.py
    │   └── test_attachments.py
    ├── test_commands/
    │   ├── __init__.py
    │   ├── test_spaces.py
    │   └── test_pages.py
    ├── test_formatters/
    │   ├── __init__.py
    │   └── test_json_fmt.py
    └── test_converters/
        ├── __init__.py
        └── test_html_to_text.py
```

## Dependencies

```toml
[project.dependencies]
typer = ">=0.12"
httpx = ">=0.27"
rich = ">=13"
pydantic = ">=2"
markdownify = ">=0.12"

[project.optional-dependencies]
dev = [
    "pytest>=8",
    "pytest-httpx>=0.30",
    "pytest-cov>=5",
    "ruff>=0.4",
    "mypy>=1.10",
]
```

## Development commands (planned)

```bash
# Set up the environment
uv sync --all-extras

# Run the tests
uv run pytest

# Run a single test file
uv run pytest tests/test_config.py -v

# Run the tests with coverage
uv run pytest --cov=ccli --cov-report=term-missing

# Lint / format
uv run ruff check .
uv run ruff format .

# Type check
uv run mypy src/

# Run the tool (during development)
uv run ccli --help
```
