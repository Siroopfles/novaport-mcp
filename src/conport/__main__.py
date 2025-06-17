import sys
import argparse
from .main import mcp_server

def main():
    """
    NovaPort MCP: A robust, multi-workspace context server for AI assistants.
    """
    parser = argparse.ArgumentParser(
        description="NovaPort MCP: A robust, multi-workspace context server for AI assistants.",
        prog="conport"
    )
    parser.add_argument(
        "--version", "-v", 
        action="version", 
        version="conport-v2 version 0.1.0-beta"
    )
    parser.add_argument(
        "command", 
        nargs="?", 
        choices=["start"],
        help="Command to execute (default: start)"
    )
    
    args = parser.parse_args()
    
    # Default naar start commando als geen commando gegeven
    if args.command is None or args.command == "start":
        print("Starting NovaPort-MCP server in STDIO mode...")
        print("This server is multi-workspace capable.")
        print("Waiting for tool calls with a 'workspace_id' argument...")
        mcp_server.run(transport="stdio")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()