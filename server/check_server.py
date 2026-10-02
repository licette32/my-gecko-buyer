"""A small MCP server that answers one question: should this purchase be signed?

Rebuilds an IntentRecord and a Prepared from the caller's dicts, runs check_all,
and returns the verdict. Keyless: it never loads a signer, and it works entirely
on recorded answers.
"""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from buyer.check import check_all
from buyer.intent import IntentRecord
from buyer.prepared import Prepared

from .guard import is_public_url

server = MCPServer("check-purchase")


@server.tool()
def check_purchase(
    intent: dict[str, Any],
    prepared_answer: dict[str, Any],
    rpc_url: str | None = None,
) -> dict[str, Any]:
    """Decide whether a prepared purchase matches the pinned intent.

    Returns passed, the field that refused (if any), what was asked, and what
    was found. If rpc_url is given and is not public, refuses before fetching.
    """
    if rpc_url is not None and not is_public_url(rpc_url):
        return {
            "passed": False,
            "field": "rpc_url",
            "asked": "a public https URL",
            "found": rpc_url,
            "reason": "not-public: the guard refused before any socket opened",
        }

    record = IntentRecord(**intent)
    prepared = Prepared.from_answer(prepared_answer)
    verdict = check_all(record, prepared)

    if verdict.unwritten is not None:
        return {
            "passed": False,
            "field": "unwritten",
            "asked": None,
            "found": str(verdict.unwritten),
        }
    if verdict.refusal is not None:
        r = verdict.refusal
        return {"passed": False, "field": r.field, "asked": r.asked, "found": r.found}
    return {"passed": True, "field": None, "asked": None, "found": None}


if __name__ == "__main__":
    server.run()
