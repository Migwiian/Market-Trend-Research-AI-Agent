from __future__ import annotations

from fastmcp import FastMCP

from mtrd.config import AppConfig
from mtrd.rag.query import generate_brief

mcp = FastMCP("market-trend-research-desk")


@mcp.tool()
def market_brief(topic: str, audience: str, lens: str) -> dict:
    """Generate a typed market brief."""
    config = AppConfig()
    brief = generate_brief(topic, audience, lens, config)
    return brief.model_dump()


if __name__ == "__main__":
    mcp.run()
