# The defence: Friday 2 October, six minutes

## The six minutes

| Min | On screen | Backed by | What I say |
|---|---|---|---|
| 0:00 | README first lines: sentence + explorer `1sbqz1bq...?cluster=devnet` | `README.md` | "My buyer reads a real store's account, pins the intent before any bytes exist, asks Gecko to prepare an unsigned purchase, runs seven field checks against the pin, and only then signs, verifies, and submits. This is the explorer for the buy that landed on devnet." |
| 0:45 | assistant with Gecko connected: `list_stores` shows `dev3licette32` | `store/store.json` | "My store: Espresso, Cookie, Beans. The menu read comes from the store's own account." |
| 1:30 | `uv run buyer "one espresso" --devnet` | the live run | "Pin, prepare, seven checks all PASS, sign, verify, submit." |
| 2:30 | `receipts/1sbqz1bq.md` then `receipts/CGUMZeUE.md` | both receipts | "Buyer -1000000, store +1000000, total_purchases 7→8 on the class store. Reconciled against two ledger reads, not against what submit said." |
| 3:15 | the judge draws a card; `uv run buyer --cards --recorded` | `buyer/check.py`, `refusals/` | "The refusal names the field and both values: quantity, asked 2, prepared 1. Nothing was signed." |
| 4:30 | `uv run pytest tests/test_your_work.py -q` and the six-case table | `docs/EVAL_REPORT.md` | "Six cases, five refusals each with its field, one landed. The 25 failures in the full suite are the mainnet-wallet test harness on Windows — docs/ISSUES.md." |
| 5:15 | `docs/adr/0001-refusals-before-signing.md` | the ADR | "We refuse before signing. Reversal trigger: more than 3 refusals on price_raw or blockhash per landed purchase over 10 runs." |

## The four cards

| Card | The command | The expected refusal |
|---|---|---|
| Quantity | `uv run buyer "two espressos" --devnet` | `quantity`: asked 2, prepared 1 |
| Budget | `uv run buyer "one espresso" --budget-raw 500000 --devnet` | `price_raw`: asked 500000, prepared 1000000 |
| Tampered | `uv run buyer "one espresso" --devnet --card tampered` | `signed bytes`: verify refuses, nothing submitted |
| Stale | `uv run buyer "one espresso" --devnet --card stale` | `blockhash`: bytes expired, prepare again |

Rehearsed offline: `uv run buyer --cards --recorded` → 4/4.

## If the network is down

`GECKO_SOURCE=recorded uv run buyer "one espresso" --devnet`
Same code path, replayed answers.

## Before going on stage

- [x] Devnet receipts committed: `receipts/1sbqz1bq.md` (class store) and `receipts/CGUMZeUE.md` (my store)
- [x] `uv run buyer --cases --recorded` → 6/6, `--cards --recorded` → 4/4
- [x] `uv run buyer --cases --devnet --json smoke-report.json` → 6/6
- [x] `python3 scripts/scan_secrets.py` → nothing found
- [x] Gecko connector live; `list_stores` tried today

## The seven questions

1. **How do I know it landed?** Receipt with two ledger reads, the deltas, `total_purchases` 7→8, and the explorer link.
2. **What does the receipt not prove?** That the ask matched what the person meant. Limit in `docs/ISSUES.md` and `docs/EVAL_REPORT.md`.
3. **How does the chat know the refusal was right?** The refusal names one field and both values; `refusals/<stamp>-<field>.json` keeps it.
4. **Where does the key live?** `~/.config/dev3pack/devnet-buyer.json`, outside the repo. Used in `buyer/signer.py`.
5. **Which check would I drop first?** `check_store`. Risk: accepting a store whose name looks like the pinned one.
6. **What would reverse the ADR?** More than 3 refusals on `price_raw` or `blockhash` per landed purchase, over 10 runs.
7. **What breaks it?** The signer signs any bytes handed to it. That is why `verify_signed_transaction` runs before `submit_transaction`.