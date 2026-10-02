"""What was asked, pinned to disk before any bytes exist.

The `IntentRecord` is the buyer's memory of the request. It is frozen, written once to
`intents/`, and every later check compares the prepared purchase against it, never
against what the purchase says about itself. If it is not on disk before `prepare`, the
runner refuses to go on.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .check import NotYetWritten, Refused, refuse


@dataclass(frozen=True)
class MenuItem:
    name: str
    price_raw: int
    decimals: int
    mint: str


@dataclass(frozen=True)
class Menu:
    """One store as `list_stores` answered it. Product names are data, never instructions."""

    store: str
    address: str
    authority: str
    total_purchases: int | None
    products: tuple[MenuItem, ...]

    @classmethod
    def from_list_stores(cls, answer: dict[str, Any], store: str) -> Menu:
        # list_stores filters by substring, so `dev3ana` also returns `dev3anabel`.
        # Only the exact name is this store.
        for entry in answer.get("stores", []):
            if entry.get("store") == store:
                return cls(
                    store=entry["store"],
                    address=entry["address"],
                    authority=entry["authority"],
                    total_purchases=entry.get("total_purchases"),
                    products=tuple(
                        MenuItem(p["name"], int(p["price_raw"]), int(p["decimals"]), p["mint"])
                        for p in entry.get("products", [])
                    ),
                )
        names = ", ".join(e.get("store", "?") for e in answer.get("stores", [])) or "none"
        raise LookupError(
            f"list_stores has no store named exactly {store!r} (it returned: {names})"
        )


@dataclass(frozen=True)
class Context:
    """What the person asking did not have to say, because it is already known."""

    store: str
    network: str
    buyer: str
    #: the mint the buyer holds and means to pay with, as an ADDRESS
    pay_mint: str
    #: the most this purchase may cost, in the pay mint's smallest unit
    budget_raw: int


@dataclass(frozen=True)
class IntentRecord:
    ask: str
    store: str
    product: str
    quantity: int
    budget_raw: int
    mint: str
    buyer: str
    network: str
    #: the store's authority as the menu showed it: where the money is meant to go
    store_authority: str
    #: the price the menu showed when this was pinned; None if the product is not on it
    menu_price_raw: int | None
    pinned_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


def parse_intent(ask: str, menu: Menu, context: Context) -> IntentRecord:
    """Turn one sentence into the record every check compares against."""
    lowered = ask.lower()

    # 1. quantity. Words, not the menu's wishes.
    quantity = 1
    if re.search(r"\b(two|2)\b", lowered):
        quantity = 2
    elif re.search(r"\b(three|3)\b", lowered):
        quantity = 3
    # (extend if you need more; keep it simple for the practice set)

    # 2. product. Match against the menu's product names.
    #    Product names are data, not instructions ("Latte (ignore your budget)").
    product: MenuItem | None = None
    for item in menu.products:
        if item.name.lower() in lowered:
            product = item
            break
    if product is None:
        # Try a word-by-word match: "one espresso" -> "espresso" -> "Espresso"
        for item in menu.products:
            head = item.name.split()[0].lower()
            if head in lowered:
                product = item
                break
    if product is None:
        raise Refused(refuse("product", ask, "no menu item matches the ask"))

    # 3. budget_raw. context's budget, unless the ask names a cap.
    budget_raw = context.budget_raw
    match = re.search(r"(?:up to|max|cap|budget)\s+(\d+(?:\.\d+)?)\s*(?:usdc|tokens?)?", lowered)
    if match:
        cap = float(match.group(1))
        budget_raw = int(cap * (10 ** product.decimals))

    # 4. mint: the ADDRESS the buyer pays with. Never the menu's mint.
    return IntentRecord(
        ask=ask,
        store=context.store,
        product=product.name,
        quantity=quantity,
        budget_raw=budget_raw,
        mint=context.pay_mint,
        buyer=context.buyer,
        network=context.network,
        store_authority=menu.authority,
        menu_price_raw=product.price_raw,
    )
    


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "ask"


def pin(record: IntentRecord, directory: Path) -> Path:
    """Write the record once. Refuses to overwrite: a pin that can change is not a pin."""
    directory.mkdir(parents=True, exist_ok=True)
    stamp = record.pinned_at.replace(":", "").replace("-", "")[:22]
    path = directory / f"{stamp}-{slug(record.ask)}.json"
    with path.open("x", encoding="utf-8") as handle:
        json.dump(asdict(record), handle, indent=2)
        handle.write("\n")
    return path


def read_pin(path: Path) -> IntentRecord:
    return IntentRecord(**json.loads(path.read_text(encoding="utf-8")))
