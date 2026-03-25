# ccli 開発計画

## 開発方針

- 小さく作って小さく治す：各フェーズは独立してリリース可能な状態を維持
- テストと実装を同時進行：実装ファイルに対応するテストファイルを必ずセットで作成
- コミット前にテスト通過を確認

## フェーズ構成

### Phase 0: プロジェクト基盤 ✅
**目標**: 開発環境・プロジェクト構造の確立

- [x] 詳細仕様書作成（`docs/spec.md`）
- [x] 開発計画作成（`docs/plan.md`）
- [x] `pyproject.toml` 作成（依存関係・ビルド設定）
- [x] ディレクトリ構造の作成
- [x] `CHANGELOG.md` 初期化
- [x] `README.md` 作成
- [x] `CLAUDE.md` 作成
- [x] `.gitignore` 作成
- [x] uv 環境セットアップ確認

### Phase 1: 設定・認証基盤 ✅
**目標**: 認証情報の安全な管理と Confluence API 接続確認

実装:
- `src/ccli/config.py`: 設定管理（環境変数 → 設定ファイル フォールバック）
- `src/ccli/auth.py`: 認証クライアント生成
- `src/ccli/client/base.py`: httpx ベースの API クライアント基底クラス

テスト:
- `tests/test_config.py`: 環境変数・ファイル読み込み、優先順位
- `tests/test_client/test_base.py`: 認証ヘッダー、エラーハンドリング

完了条件: `ccli config show` / `ccli config init` が動作する

### Phase 2: Spaces 機能 ✅
**目標**: スペースの一覧・検索

実装:
- `src/ccli/client/spaces.py`: Spaces API クライアント
- `src/ccli/commands/spaces.py`: CLI コマンド定義
- `src/ccli/formatters/spaces.py`: text/json 出力フォーマッター

テスト:
- `tests/test_client/test_spaces.py`: API レスポンスのパース、ページネーション
- `tests/test_commands/test_spaces.py`: CLI コマンドの E2E テスト（モック使用）

完了条件: `ccli spaces list` / `ccli spaces search` が動作する

### Phase 3: Pages 単体取得 ✅
**目標**: ページの検索・単体取得（text/html/json/storage 出力）

実装:
- `src/ccli/client/pages.py`: Pages API クライアント（search, get）
- `src/ccli/commands/pages.py`: CLI コマンド定義（search, get）
- `src/ccli/formatters/pages.py`: text/html/json フォーマッター
- `src/ccli/converters/html_to_text.py`: HTML → Markdown/テキスト変換

テスト:
- `tests/test_client/test_pages.py`
- `tests/test_commands/test_pages.py`
- `tests/test_converters/test_html_to_text.py`

完了条件: `ccli pages search` / `ccli pages get` が動作する

### Phase 4: Pages ツリー取得 ✅
**目標**: 再帰的な子ページ取得

実装:
- `src/ccli/client/pages.py` に `get_children()` / `get_tree()` を追加
- `src/ccli/commands/pages.py` に `tree` サブコマンド追加
- `src/ccli/formatters/pages.py` にツリー表示を追加

テスト:
- 深さ制限のテスト
- 循環参照ガード（念のため）

完了条件: `ccli pages tree` が動作する

### Phase 5: 添付ファイル取得 ✅
**目標**: ページに紐付いた添付ファイルの取得・保存

実装:
- `src/ccli/client/attachments.py`: Attachments API クライアント
- `src/ccli/downloader.py`: ストリーミングダウンロード

テスト:
- `tests/test_client/test_attachments.py`
- `tests/test_downloader.py`: ストリーミング動作、保存パス生成

完了条件: `ccli pages get --attachments` / `ccli pages tree --attachments` が動作する

### Phase 6: 品質・仕上げ ✅
**目標**: リリース品質への引き上げ

- [x] ruff 全エラー解消（UP045, UP042, B904, B008 設定, E741, E501）
- [x] mypy strict モード通過（pydantic plugin 追加）
- [x] テストカバレッジ 94%（目標 80% 超）
- [x] CHANGELOG.md 全フェーズ記載
- [x] README.md・README.ja.md（日英二言語）最終更新
- [x] docs/plan.md 全フェーズ完了マーク

## ディレクトリ構造

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
│   ├── spec.md
│   └── plan.md
├── src/
│   └── ccli/
│       ├── __init__.py
│       ├── main.py            # Typer アプリケーション エントリポイント
│       ├── config.py          # 設定管理
│       ├── auth.py            # 認証
│       ├── exceptions.py      # カスタム例外
│       ├── client/
│       │   ├── __init__.py
│       │   ├── base.py        # httpx ベースクライアント
│       │   ├── spaces.py      # Spaces API
│       │   ├── pages.py       # Pages API
│       │   └── attachments.py # Attachments API
│       ├── commands/
│       │   ├── __init__.py
│       │   ├── spaces.py      # spaces サブコマンド群
│       │   ├── pages.py       # pages サブコマンド群
│       │   └── config.py      # config サブコマンド群
│       ├── formatters/
│       │   ├── __init__.py
│       │   ├── base.py        # フォーマッター基底クラス
│       │   ├── text.py        # text 出力
│       │   ├── json_fmt.py    # json 出力
│       │   └── html_fmt.py    # html 出力
│       ├── converters/
│       │   ├── __init__.py
│       │   └── html_to_text.py
│       └── downloader.py      # ストリーミングダウンロード
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

## 依存ライブラリ

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

## 開発コマンド（予定）

```bash
# 環境セットアップ
uv sync --all-extras

# テスト実行
uv run pytest

# 単一テストファイル実行
uv run pytest tests/test_config.py -v

# カバレッジ付きテスト
uv run pytest --cov=ccli --cov-report=term-missing

# Lint / フォーマット
uv run ruff check .
uv run ruff format .

# 型チェック
uv run mypy src/

# ツール実行（開発中）
uv run ccli --help
```
