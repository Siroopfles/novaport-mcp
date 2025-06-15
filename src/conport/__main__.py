import typer
from .main import mcp_server
cli = typer.Typer(help="ConPort v2: A robust context server for AI assistants.")
@cli.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        print("Starting ConPort server in STDIO mode...")
        mcp_server.run(transport="stdio")
if __name__ == "__main__": cli()