"""
Remote Model Context Protocol (FastMCP) Server for Orange Systems Sales Intelligence.
Conforms to Section 5 of Enterprise_AI_Sales_Intelligence_Platform_Annex.md.
Exposes prioritized lead discovery, verbatim signal evidence, grounded pitch generation,
and staged sales outreach to external AI agents (Claude Code, Antigravity, Cursor).
"""
import argparse
import json
import os
import sys

# Ensure bifidok_be root package is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from mcp.server.fastmcp import FastMCP
from services.leads_service import (
    format_grounded_pitch,
    query_prioritized_leads,
    query_signal_evidence,
    queue_sales_outreach,
)

# Instantiate FastMCP server as specified in Section 5.1
mcp = FastMCP("Orange-Systems-Intelligence")


@mcp.tool()
def get_prioritized_leads(service_line: str, min_score: int = 70) -> str:
    """Discovers top enterprise leads prioritized by verified buying signals."""
    leads = query_prioritized_leads(service_line=service_line, min_score=min_score)
    return json.dumps(leads, indent=2)


@mcp.tool()
def get_signal_evidence(domain: str) -> str:
    """Retrieves exact verbatim quotes and source links justifying why a company is ready to buy."""
    evidence = query_signal_evidence(domain=domain)
    return json.dumps(evidence, indent=2)


@mcp.tool()
def prepare_grounded_pitch(
    company_name: str,
    recipient_title: str,
    evidence_quote: str,
    value_prop: str,
) -> str:
    """Generates an executive-level value proposition explicitly grounded in verified evidence."""
    return format_grounded_pitch(
        company_name=company_name,
        recipient_title=recipient_title,
        evidence_quote=evidence_quote,
        value_prop=value_prop,
    )


@mcp.tool()
def send_sales_outreach_email(
    recipient_email: str,
    subject: str,
    email_body: str,
    dry_run: bool = True,
) -> str:
    """
    Stages or sends a sales outreach email.
    When dry_run=True, queues the draft in the Orange Dashboard for human approval.
    """
    result = queue_sales_outreach(
        recipient_email=recipient_email,
        subject=subject,
        email_body=email_body,
        dry_run=dry_run,
    )
    draft_id = result["draft_id"]

    if dry_run:
        return f"SUCCESS: Draft {draft_id} staged in Orange Dashboard queue for human review."
    return f"SUCCESS: Email dispatched to {recipient_email}."


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Orange Systems Remote FastMCP Server (Section 5)",
    )
    parser.add_argument(
        "--transport",
        choices=["sse", "stdio"],
        default="sse",
        help="Transport protocol (sse or stdio). Default: sse",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8001,
        help="Port for SSE transport server (default: 8001)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host address for SSE transport server (default: 0.0.0.0)",
    )

    args = parser.parse_args()

    mcp.settings.host = args.host
    mcp.settings.port = args.port

    print(
        f"Starting Orange-Systems-Intelligence FastMCP Server [{args.transport}] on {args.host}:{args.port}..."
    )
    mcp.run(transport=args.transport)
