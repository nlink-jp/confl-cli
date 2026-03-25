from enum import Enum
from pathlib import Path
from typing import Optional

import httpx
import typer

from ..auth import build_client
from ..client.attachments import AttachmentsClient
from ..client.base import ConfluenceClient
from ..client.pages import PageNode, PagesClient
from ..config import Config, load_config
from ..downloader import download_file, safe_attachment_dest
from ..exceptions import CCLIError, ConfigError
from ..formatters.base import use_color
from ..formatters.html_fmt import print_html
from ..formatters.json_fmt import print_json
from ..formatters.text import print_page, print_page_summaries, print_page_tree

pages_app = typer.Typer(help="Page operations.")


class OutputFormat(str, Enum):
    text = "text"
    json = "json"
    html = "html"
    storage = "storage"  # Confluence Storage Format (XHTML-like source)


class TreeOutputFormat(str, Enum):
    text = "text"
    json = "json"


def _setup() -> tuple[Config, httpx.Client, ConfluenceClient]:
    try:
        config = load_config()
    except ConfigError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=exc.exit_code)
    http_client = build_client(config)
    return config, http_client, ConfluenceClient(http_client)


@pages_app.command("search")
def pages_search(
    query: str = typer.Argument(help="Search query (full-text search via CQL)."),
    space: Optional[str] = typer.Option(None, "--space", "-s", help="Filter by space key."),
    limit: int = typer.Option(25, "--limit", "-n", help="Maximum number of results."),
    format: OutputFormat = typer.Option(OutputFormat.text, "--format", "-f"),
) -> None:
    """Search pages by full-text query."""
    config, _, cc = _setup()
    try:
        summaries = PagesClient(cc, config.confluence.url).search(
            query=query, space_key=space, limit=limit
        )
    except CCLIError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=exc.exit_code)

    if format == OutputFormat.json:
        print_json([s.model_dump() for s in summaries])
    else:
        print_page_summaries(summaries, color=use_color())


@pages_app.command("get")
def pages_get(
    page_id: str = typer.Argument(help="Page ID."),
    format: OutputFormat = typer.Option(OutputFormat.text, "--format", "-f"),
    with_attachments: bool = typer.Option(False, "--attachments", help="Fetch attachment metadata."),
    output_dir: Optional[Path] = typer.Option(
        None, "--output-dir", help="Download attachments to this directory."
    ),
) -> None:
    """Get a single page by ID."""
    config, http_client, cc = _setup()
    try:
        page = PagesClient(cc, config.confluence.url).get(page_id)
    except CCLIError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=exc.exit_code)

    if with_attachments or output_dir:
        try:
            attachments = AttachmentsClient(cc).list(page_id)
        except CCLIError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(code=exc.exit_code)

        if output_dir:
            for att in attachments:
                try:
                    dest = safe_attachment_dest(output_dir, page_id, att.filename)
                    download_file(http_client, att.download_url, dest)
                    att.saved_path = str(dest)
                except Exception as exc:  # noqa: BLE001
                    typer.echo(f"Warning: could not download {att.filename}: {exc}", err=True)

        page.attachments = attachments

    if format == OutputFormat.json:
        print_json(page.model_dump())
    elif format == OutputFormat.html:
        print_html(page.body_html)
    elif format == OutputFormat.storage:
        print(page.body_storage)
    else:
        print_page(page, color=use_color())


@pages_app.command("tree")
def pages_tree(
    page_id: str = typer.Argument(help="Root page ID."),
    depth: Optional[int] = typer.Option(
        None, "--depth", "-d", help="Max recursion depth (default: unlimited)."
    ),
    format: TreeOutputFormat = typer.Option(TreeOutputFormat.text, "--format", "-f"),
    with_attachments: bool = typer.Option(False, "--attachments", help="Fetch attachment metadata."),
    output_dir: Optional[Path] = typer.Option(
        None, "--output-dir", help="Download attachments to this directory."
    ),
) -> None:
    """Get a page and all its descendants as a tree."""
    config, http_client, cc = _setup()
    try:
        tree = PagesClient(cc, config.confluence.url).get_tree(page_id, depth=depth)
    except CCLIError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=exc.exit_code)

    if with_attachments or output_dir:
        _populate_tree_attachments(
            tree, AttachmentsClient(cc), http_client, output_dir
        )

    if format == TreeOutputFormat.json:
        print_json(tree.model_dump())
    else:
        print_page_tree(tree, color=use_color())


def _populate_tree_attachments(
    node: PageNode,
    attach_client: AttachmentsClient,
    http_client: httpx.Client,
    output_dir: Optional[Path],
) -> None:
    """Recursively fetch (and optionally download) attachments for every node."""
    try:
        attachments = attach_client.list(node.id)
    except CCLIError as exc:
        typer.echo(f"Warning: attachments for {node.id} unavailable: {exc}", err=True)
        attachments = []

    if output_dir:
        for att in attachments:
            try:
                dest = safe_attachment_dest(output_dir, node.id, att.filename)
                download_file(http_client, att.download_url, dest)
                att.saved_path = str(dest)
            except Exception as exc:  # noqa: BLE001
                typer.echo(f"Warning: could not download {att.filename}: {exc}", err=True)

    node.attachments = attachments

    for child in node.children:
        _populate_tree_attachments(child, attach_client, http_client, output_dir)
