import typer
from .main import mcp_server

cli = typer.Typer(help="NovaPort MCP: A robust, multi-workspace context server for AI assistants.")

@cli.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    Start de NovaPort MCP server. Draait standaard in STDIO modus voor client integratie.
    """
    if ctx.invoked_subcommand is None:
        print("Starting NovaPort-MCP server in STDIO mode...")
        print("This server is multi-workspace capable.")
        print("Waiting for tool calls with a 'workspace_id' argument...")
        mcp_server.run(transport="stdio")

if __name__ == "__main__":
    cli()