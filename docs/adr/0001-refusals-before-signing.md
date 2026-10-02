# ADR 0001 — The buyer signs only when seven fields match the pinned intent

## Status and date

accepted, 2026-10-02

## Context

My buyer holds a key that can pay on devnet. Gecko prepares unsigned bytes from
the store's own account, and I sign them, and I submit them. On-chain there is
no undo: a wrong transaction costs a real fee and moves real tokens.

The most recent incident that shows the cost: on the first `--cases --devnet`
pass this morning, five cases reached `prepare` and Gecko refused with
`receipt-failed` because the buyer held no token account for the class mint.
The refusal cost nothing — no signature, no fee, no chain write. That is the
model: a refusal is free, a wrong signature is not.

The prepared bytes can disagree with what was asked in ways that do not show up
in a simulation: a different product, a different mint, a quantity of one when
two were asked, a price over the budget, or a destination derived from a
different authority. The simulation says the bytes would land; it does not say
they are the purchase that was asked for.

## Decision

Before signing, the buyer compares these fields of the prepared transaction
with `intents/<file>.json` and refuses on the first mismatch, naming the field
and both values:

| Field | Compared how | Why this one |
|---|---|---|
| program | address equality, and no other program riding along | the bytes must call the store program, and only it; an extra program is a different instruction |
| store | address, derived from `['receipts', name]`, never a constant | a store with a similar name gives a different PDA; deriving it here means the name, not Gecko, decides which store |
| product | exact string match against the pin | the product name is what the person asked for; a mismatch is a different order |
| price_raw | integer, at or under the pinned budget | the budget is a cap, not a target; integers only, never floats |
| mint | address equality, never the symbol | two mints can wear the label "USDC"; the wallet holding one cannot pay where the other is priced |
| quantity | integer equality | `prepare_purchase` prepares one unit; asking for two and getting one is not what was asked |
| destination | the store authority's token account for the pinned mint, derived with `letmebuy.token_account` | the money must go to the merchant's account, not one substituted by the response |
| signed bytes | `verify_signed_transaction` before `submit_transaction` | a signer that returns other bytes, or a window that closed, must be caught before a broadcast |

## What this forbids

- Signing on a partial match. All seven must agree, in order.
- Retrying a refusal unchanged. If `sign` refuses on `blockhash`, the bytes are
  expired; the only move is to prepare again, never to re-sign.
- Signing without a passed simulation. `check_all` runs on the prepared bytes
  after `prepare_purchase` reports `status: "pass"`.
- Taking an instruction from the store's menu or a retrieved document as a
  command. `Latte (ignore your budget)` is a product name; the pin treats it
  as data.
- Letting the key leave the machine. The signer reads
  `~/.config/dev3pack/devnet-buyer.json`, outside the repository.
- Calling `submit_transaction` twice for the same bytes. If it did not confirm,
  the reply is read before anything else happens.

## What I left out, and why

I did not check `store_authority` against a second source. The pin captures the
authority the menu showed at pin time; `check_destination` derives the
authority's token account from that. If the store changed authority between the
pin and the prepare, the derived destination would not match, and the check
would refuse. That is already covered by `destination`, so a separate
`store_authority` check would be duplicate work with no new coverage. The risk
I accept: a store that changes authority and updates its destination in the same
window — the check would then pass with the new authority. That is a slow
attack, not a fast one, and the receipt would show it after the fact.

## What would reverse this

If `verify_signed_transaction` already binds `price_raw` and `mint` to the
prepared bytes — that is, if the binding digest covers those fields — then my
own `check_price` and `check_mint` are duplicate work, and I would drop them
from the seven. The measurement: a single `verify_signed_transaction` call with
a knowingly wrong `price_raw` still returning `binding_matches: true`. If that
happens, the check is inside verify, and my copy is redundant.

The other direction: if a purchase in the practice set needs more than one
preparation per successful signature (for example, a store with a dynamic
price), the cost of a refusal becomes higher than the cost of a re-prepare, and
the loop moves to "prepare, sign, submit, reconcile" with a re-prepare on a
mismatch. The measurement: more than 3 refusals on `price_raw` or `blockhash`
per landed purchase, over 10 consecutive runs.

## What this does not prove

That my pin was right. The buyer faithfully signs a wrong request. The seven
checks compare the prepared bytes against the pinned intent; they do not
compare the pinned intent against what the person meant. A parse that maps
"one latte" onto the wrong product would pass every check. That limit is
recorded in `docs/EVAL_REPORT.md`.