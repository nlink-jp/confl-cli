from enum import StrEnum

import typer

from ..auth import build_client
from ..client.base import ConfluenceClient
from ..client.spaces import SpacesClient
from ..config import load_config
from ..exceptions import CCLIError, ConfigError
from ..formatters.base import use_color
from ..formatters.json_fmt import print_json
from ..formatters.text import print_spaces

spaces_app = typer.Typer(help="Space operations.")


class OutputFormat(StrEnum):
    text = "text"
    json = "json"


class SpaceType(StrEnum):
    global_ = "global"
    personal = "personal"


def _make_spaces_client() -> SpacesClient:
    try:
        config = load_config()
    except ConfigError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=exc.exit_code) from None
    return SpacesClient(ConfluenceClient(build_client(config)))


@spaces_app.command("list")
def spaces_list(
    limit: int = typer.Option(25, "--limit", "-n", help="Maximum number of results."),
    space_type: SpaceType | None = typer.Option(None, "--type", help="Filter by space type."),
    format: OutputFormat = typer.Option(OutputFormat.text, "--format", "-f"),
) -> None:
    """List spaces."""
    client = _make_spaces_client()
    try:
        spaces = client.list(
            limit=limit,
            space_type=space_type.value if space_type else None,
        )
    except CCLIError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=exc.exit_code) from None

    if format == OutputFormat.json:
        print_json([s.model_dump(by_alias=False) for s in spaces])
    else:
        print_spaces(spaces, color=use_color())


@spaces_app.command("search")
def spaces_search(
    query: str = typer.Argument(help="Search query (matches space name or key)."),
    limit: int = typer.Option(25, "--limit", "-n", help="Maximum number of results."),
    format: OutputFormat = typer.Option(OutputFormat.text, "--format", "-f"),
) -> None:
    """Search spaces by name or key."""
    client = _make_spaces_client()
    try:
        spaces = client.search(query=query, limit=limit)
    except CCLIError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=exc.exit_code) from None

    if format == OutputFormat.json:
        print_json([s.model_dump(by_alias=False) for s in spaces])
    else:
        print_spaces(spaces, color=use_color())
