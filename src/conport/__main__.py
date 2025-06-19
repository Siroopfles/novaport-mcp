import typer

from .main import mcp_server

cli = typer.Typer(
    name="conport",
    help="NovaPort MCP: A robust, multi-workspace context server for AI assistants.",
    add_completion=False,
)


@cli.command(help="Starts the NovaPort-MCP server in STDIO mode (default command).")
def start():
    """Start the server in STDIO mode, waiting for tool calls with a 'workspace_id'."""
    print("Starting NovaPort-MCP server in STDIO mode...")
    print("This server is multi-workspace capable.")
    print("Waiting for tool calls with a 'workspace_id' argument...")
    mcp_server.run(transport="stdio")


@cli.command(help="Show the application's version and exit.")
def version():
    """Show the application's version and exit."""
    print("NovaPort-MCP version: 0.1.0-beta")


@cli.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """Handle CLI callback that invokes start command when no subcommand is given."""
    if ctx.invoked_subcommand is None:
        start()


if __name__ == "__main__":
    cli()
