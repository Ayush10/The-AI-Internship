"""McpToolset factory for Supabase MCP connection.

Uses @supabase/mcp-server-postgrest (official) for PostgREST-based database access.
Provides postgrestRequest and sqlToRest tools to agents.
"""

import os


def get_supabase_toolset(read_only: bool = False):
    """Create an McpToolset connected to the Supabase PostgREST MCP server.

    Uses @supabase/mcp-server-postgrest which communicates via PostgREST API.
    Tools: postgrestRequest (HTTP to PostgREST), sqlToRest (SQL -> PostgREST).

    Args:
        read_only: If True, use the anon key. If False, use the service role key.
    """
    from google.adk.tools.mcp_tool import McpToolset
    from google.adk.tools.mcp_tool.mcp_session_manager import StdioServerParameters

    supabase_url = os.environ.get("SUPABASE_URL", "http://localhost:8000")
    anon_key = os.environ.get("SUPABASE_ANON_KEY", "")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    # PostgREST endpoint is at /rest/v1
    postgrest_url = f"{supabase_url}/rest/v1"

    # Use anon key for read-only, service role key for read-write
    api_key = anon_key if read_only else (service_key or anon_key)

    return McpToolset(
        connection_params=StdioServerParameters(
            command="npx",
            args=[
                "-y", "@supabase/mcp-server-postgrest",
                "--apiUrl", postgrest_url,
                "--apiKey", api_key,
                "--schema", "public",
            ],
        )
    )
