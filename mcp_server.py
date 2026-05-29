#!/usr/bin/env python3
"""
Rappahannock Realty Group — MCP Server

Exposes Scout's listing and showing tools as an MCP server so any
MCP-compatible client (Claude Desktop, other agents) can connect.

Usage (local):
  python mcp_server.py

Claude Desktop config:
  {
    "mcpServers": {
      "rappahannock-realty": {
        "command": "python",
        "args": ["/absolute/path/to/rappahannock_realty/mcp_server.py"]
      }
    }
  }
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mcp.server.fastmcp import FastMCP
from app.tools.mock_db import init_db
from app.tools.handlers import (
    handle_search_listings,
    handle_get_listing_details,
    handle_schedule_showing,
    handle_estimate_mortgage,
)

init_db()
mcp = FastMCP("Rappahannock Realty Group")


@mcp.tool()
def search_properties(
    min_price: int = 0,
    max_price: int = 9999999,
    bedrooms: int = 0,
    bathrooms: float = 0.0,
    city: str = "",
    min_sqft: int = 0,
) -> dict:
    """Search active property listings in the Fredericksburg, VA area."""
    return handle_search_listings(min_price, max_price, bedrooms, bathrooms, city, min_sqft)


@mcp.tool()
def get_listing(listing_id: str) -> dict:
    """Get full details on a specific property listing by ID (e.g. RRG-1004)."""
    return handle_get_listing_details(listing_id)


@mcp.tool()
def schedule_showing(
    listing_id: str,
    name: str,
    email: str,
    preferred_date: str,
    preferred_time: str,
    phone: str = "",
) -> dict:
    """Schedule a property showing. Date: YYYY-MM-DD. Time: HH:MM (24-hour)."""
    return handle_schedule_showing(listing_id, name, email, preferred_date, preferred_time, phone)


@mcp.tool()
def mortgage_estimate(
    home_price: int,
    down_payment_pct: float = 20.0,
    term_years: int = 30,
    rate: float = 6.75,
) -> dict:
    """Calculate an estimated monthly mortgage payment."""
    return handle_estimate_mortgage(home_price, down_payment_pct, term_years, rate)


if __name__ == "__main__":
    mcp.run()
