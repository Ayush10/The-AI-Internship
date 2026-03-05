"""McpToolset factory for Supabase MCP connection.

Uses selfhosted-supabase-mcp (HenkDz) for self-hosted Supabase instances.
Supports both stdio mode (local dev) and HTTP mode (containerized/remote).
"""

import os


def get_supabase_toolset(read_only: bool = False):
    """Create an McpToolset connected to the Supabase MCP server.

    Connection mode is determined by SUPABASE_MCP_URL:
    - Starts with http:// or https:// → HTTP transport (StreamableHTTPConnectionParams)
    - Empty or absent → stdio transport (StdioServerParameters) using selfhosted-supabase-mcp

    Args:
        read_only: If True, use the anon key (limited access).
                   If False, use the service role key (full write access).
    """
    from google.adk.tools.mcp_tool import McpToolset

    mcp_url = os.environ.get("SUPABASE_MCP_URL", "")

    if mcp_url.startswith("http://") or mcp_url.startswith("https://"):
        # HTTP-based MCP server (selfhosted-supabase-mcp in HTTP mode)
        from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams

        headers = {}
        jwt_secret = os.environ.get("MCP_JWT_SECRET", "")
        if jwt_secret:
            headers["Authorization"] = f"Bearer {jwt_secret}"

        return McpToolset(
            connection_params=StreamableHTTPConnectionParams(
                url=mcp_url,
                headers=headers,
            )
        )

    # Stdio-based MCP — selfhosted-supabase-mcp via bunx
    from google.adk.tools.mcp_tool.mcp_session_manager import StdioServerParameters

    supabase_url = os.environ.get("SUPABASE_URL", "http://localhost:8000")
    anon_key = os.environ.get("SUPABASE_ANON_KEY", "")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    db_url = os.environ.get("SUPABASE_DB_URL", "")

    # Use service key for write access, anon key for read-only
    api_key = anon_key if read_only else (service_key or anon_key)

    args = [
        "-y", "selfhosted-supabase-mcp",
        "--url", supabase_url,
        "--anon-key", anon_key,
        "--transport", "stdio",
    ]

    # Add service key for write access
    if not read_only and service_key:
        args.extend(["--service-key", service_key])

    # Add direct DB URL for privileged operations
    if db_url:
        args.extend(["--db-url", db_url])

    return McpToolset(
        connection_params=StdioServerParameters(
            command="npx",
            args=args,
        )
    )
