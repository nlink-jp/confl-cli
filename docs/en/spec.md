# ccli detailed specification

## 1. Overview

A CLI tool for operating Atlassian Confluence Cloud from the command line.
It follows the UNIX philosophy and is designed to be combined with other commands through pipes.
Its main features are searching for and fetching spaces and pages, and fetching attachments.

## 2. Target environment

| Item | Value |
|------|------|
| Confluence edition | Cloud (REST API v2) |
| Target OS | macOS / Linux / Windows |
| Python version | 3.11 or later |
| Package management | uv |

## 3. Authentication

### Method
Confluence Cloud's HTTP Basic authentication:
- Username: the email address
- Password: an API Token (issued at <https://id.atlassian.com/manage-profile/security/api-tokens>)

### Handling credentials (security first)

Precedence (highest first):

1. **Environment variables** (recommended)
   ```
   CONFLUENCE_URL=https://your-domain.atlassian.net
   CONFLUENCE_USERNAME=you@example.com
   CONFLUENCE_API_TOKEN=your-api-token
   ```

2. **A config file** (the fallback)
   - Path: `~/.config/ccli/config.toml` (follows the XDG Base Directory spec; on Windows, `%APPDATA%\ccli\config.toml`)
   - Permission `600` is set when the file is created (on Windows, an equivalent restriction through the ACL)

**Prohibited**: passing the token as a command-line argument (to prevent leakage through the process list)

## 4. CLI command structure

```
confl-cli [global options] <command> <subcommand> [arguments] [options]
```

### Global options

| Option | Description |
|-----------|------|
| `--no-color` | Disable coloured output |
| `--version` | Print the version (obtained dynamically from `importlib.metadata`) |

### 4.1 The spaces command

#### `confl-cli spaces list`
Lists every space.

```
confl-cli spaces list [--limit N] [--type personal|global]
```

Example text output:
```
KEY       NAME                     TYPE      STATUS
DEV       Development              global    current
~john     John's Space             personal  current
```

#### `confl-cli spaces search <query>`
Searches spaces by a query string (a client-side substring match).

```
confl-cli spaces search <query> [--limit N]
```

#### `confl-cli spaces export <space-key>`
Exports every page in a space as a tree. The home page ID is resolved through the v1 API, and the rest is handled by the same logic as `pages tree`.

```
confl-cli spaces export <space-key>
  [--depth N]
  [--format {text,json}]
  [--attachments]
  [--output-dir DIR]
  [--page-format {text,html,json,storage}]
  [--no-rewrite-links]
```

`--page-format` must be used together with `--output-dir`.

### 4.2 The pages command

#### `confl-cli pages search <query>`
Full-text searches pages (CQL).

```
confl-cli pages search <query> [--space SPACE_KEY] [--limit N] [--format {text,json}]
```

Example text output (timestamps in local time, `YYYY-MM-DD HH:MM`):
```
ID          SPACE   TITLE                    LAST MODIFIED
123456789   DEV     Getting Started Guide    2024-01-15 19:00
987654321   ARCH    System Architecture      2024-01-10 14:30
```

#### `confl-cli pages get <page-id>`
Fetches the given page.

```
confl-cli pages get <page-id> [--format {text,html,json,storage}] [--attachments] [--output-dir DIR]
```

| Option | Description |
|-----------|------|
| `--format` | `text`=converted to Markdown (the default), `html`=raw HTML, `json`=structured data, `storage`=Confluence Storage Format |
| `--attachments` | Also fetch the attachment metadata |
| `--output-dir DIR` | Download the attachments and save them |

The metadata line in text output: `Space: XX  |  Version: N  |  Updated: YYYY-MM-DD HH:MM  |  Author: name`

JSON output schema:
```json
{
  "id": "string",
  "title": "string",
  "space_key": "string",
  "space_name": "string",
  "version": "number",
  "created_at": "ISO8601 UTC",
  "updated_at": "ISO8601 UTC",
  "author": { "display_name": "string", "email": "string | null" },
  "body_html": "string",
  "body_storage": "string",
  "url": "string",
  "parent_id": "string | null",
  "attachments": [
    {
      "id": "string",
      "filename": "string",
      "media_type": "string",
      "size_bytes": "number",
      "download_url": "string",
      "saved_path": "string | null"
    }
  ]
}
```

#### `confl-cli pages tree <page-id>`
Fetches child pages recursively, starting from the given page.

```
confl-cli pages tree <page-id> [--format {text,json}] [--depth N]
                               [--attachments] [--output-dir DIR]
                               [--page-format {text,html,json,storage}]
```

| Option | Description |
|-----------|------|
| `--depth N` | The maximum recursion depth (default: unlimited) |
| `--format` | The output format of the tree structure (`text` or `json`) |
| `--attachments` | Fetch each page's attachments |
| `--output-dir DIR` | Where the attachments and the page bodies are saved |
| `--page-format` | The format the page body is saved in. `--output-dir` is required |

Example text output (timestamps in local time):
```
Getting Started (123456789)  2024-01-15 19:00
├── Installation (111111111)  2024-01-12 10:30
│   └── Docker Setup (222222222)  2024-01-10 09:00
└── Configuration (333333333)  2024-01-08 15:45
```

The files saved when `--page-format` is given:

| Format | File name |
|------|-----------|
| `text` | `<output-dir>/<page-id>/page.md` |
| `html` | `<output-dir>/<page-id>/page.html` |
| `json` | `<output-dir>/<page-id>/page.json` |
| `storage` | `<output-dir>/<page-id>/page.xml` |

JSON output schema (per node):
```json
{
  "id": "string",
  "title": "string",
  "url": "string",
  "created_at": "ISO8601 UTC",
  "updated_at": "ISO8601 UTC",
  "attachments": [ { "id": "...", "filename": "...", "saved_path": "..." } ],
  "children": [ { /* the same structure */ } ]
}
```

### 4.3 The config command

#### `confl-cli config init`
Initializes the config file interactively.

#### `confl-cli config show`
Prints the current configuration (the API Token is masked).

## 5. Output design (the UNIX philosophy)

### Separating stdout and stderr
- **stdout**: the data itself only (text/html/json)
- **stderr**: progress, warnings, error messages

### Automatic tty detection
- When stdout is a tty: coloured output and table formatting are enabled
- When stdout is not a tty (a pipe or a redirect): colour codes are stripped and the output is plain text
- `--no-color` and the `NO_COLOR` environment variable can also disable it

### The json format
- Only JSON is written to stdout as the data
- With `--format json`, nothing but JSON is written anywhere other than stderr

## 6. Attachment handling

- When the `--attachments` flag is given, the metadata and the binary are fetched
- Large files are downloaded as a stream (memory efficiency first)
- The save directory structure: `<output-dir>/<page-id>/<filename>`
- In JSON output: the save path is stored in the `saved_path` field

## 7. Error handling

| Error kind | Exit code |
|-----------|-----------|
| Authentication failure (401) | 1 |
| Insufficient permission (403) | 2 |
| Resource not found (404) | 3 |
| Network error | 4 |
| API rate limit (429) | 5 |
| Config file error | 6 |
| Anything else | 99 |

- The exit codes are designed on the assumption that they are built into scripts
- On a rate limit, it retries with exponential backoff (at most 3 times)
- Every error message is written to stderr

## 8. Config file format

`~/.config/ccli/config.toml`:
```toml
[confluence]
url = "https://your-domain.atlassian.net"
username = "you@example.com"
api_token = "your-api-token"

[defaults]
format = "text"
limit = 25
```

## 9. Libraries used (candidates)

| Purpose | Library |
|------|-----------|
| CLI framework | Typer |
| HTTP client | httpx |
| Terminal output | Rich |
| Data models and validation | Pydantic v2 |
| Config file parsing | tomllib (standard library, 3.11+) |
| HTML → Markdown conversion | markdownify |
| Testing | pytest + pytest-httpx + pytest-cov |
