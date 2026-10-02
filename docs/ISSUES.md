# Issues

## 2026-10-02: `--cases --devnet` returned 1/6 before the class tokens arrived

- **What I saw:** running

      uv run buyer --cases --devnet

  printed `1/6 cases match what the fixtures expect`. Cases 3-module, 4-tip,
  5-beans and the trap all failed at `prepare` with:

      [  NO] prepare   Gecko refused, receipt-failed: the simulation did not pass, so no transaction is returned: a transaction that reverts against observed
      state would only cost you a fee on chain. Likely cause: sender_token_account 3pvh2xZtPhjiKUkS2Q74jz6r1x77YXmGiA6Hd11UFRtQ does not exist on devnet —
      the buyer holds no token account for the store

  Case 2-ticket was the only one that matched.

- **What was actually wrong:** nothing in the buyer. My buyer holds no token
  account for `dev3pack-cafe` because the class tokens had not been sent yet
  (`getTokenAccountsByOwner` returned `class tokens: NONE`). Gecko prepares a
  purchase against observed state, and with no sender token account the
  simulation reverts, so Gecko refuses at `prepare` before the buyer can run any
  field check.

- **How I found it:** I re-ran the token query for the class mint
  `Eoqdd43nFQ9HzGq8HjBRVLCV6aTqCFRiwHy1ZVQheYSi` and got `NONE`. The failing
  `prepare` message named the missing `sender_token_account` directly. Case
  2-ticket passing confirmed the buyer itself was fine: that refusal happens on
  `product`, before any token movement.

- **What I changed:** nothing in the code. The failure is expected until the
  instructor funds the buyer from the class funder. Once the class tokens land,
  re-running `--cases --devnet` should move cases 3 to 6 from `receipt-failed`
  to real field refusals.

- **What it cost:** nothing. No signature was created, no SOL was spent. The
  `refusals/` directory filled with five `receipt-failed` entries, which are
  infrastructure failures, not field refusals, so they are not evidence for the
  capstone.

- **Would the checks have caught it?** No, and here is why: the checks compare
  what was asked against what was prepared. There is no prepared transaction to
  compare against when Gecko refuses at `prepare`. This is a precondition of the
  check, not something the check can catch.

- **After the fix:** once the class tokens landed (~11:40 today), the same
  command printed `6/6 cases match what the fixtures expect`. Case 1 landed
  and wrote `receipts/1sbqz1bq.json`; cases 2-6 refused on their field with
  both values.

## 2026-10-02: full `uv run pytest` failed 25 tests on Windows from an existing mainnet wallet

- **What I saw:** running

      uv run pytest

  printed `25 failed, 73 passed, 2 skipped`. Every failure in
  `tests/test_mainnet_wallet.py` (23 tests) and two in `tests/test_signer.py`
  carried the same captured stdout:

      refusing: C:\Users\bever\.config\dev3pack\mainnet-wallet.json already exists,
      and it may hold money. Nothing was changed.
        `show` prints its address. Never delete it while it holds a balance.

  Two `test_signer.py` failures were different: a `FileExistsError` on
  `C:\Users\bever\.config\dev3pack` and a `DID NOT RAISE SystemExit` when a
  mainnet purchase was attempted without a wallet.

- **What was actually wrong:** the tests are not hermetic on Windows. They call
  `monkeypatch.setenv("HOME", str(tmp_path))` to isolate the home directory, but
  `Path.home()` on Windows reads `USERPROFILE` (and `HOMEDRIVE`/`HOMEPATH`), not
  `HOME`. The tests still resolve to the real home, find the real mainnet wallet
  I had already created, and the `create` command correctly refuses to overwrite
  it. The code is right; the test isolation is what breaks.

- **How I found it:** the captured stdout of every failure named the real path
  `C:\Users\bever\.config\dev3pack\mainnet-wallet.json`. That path only exists if
  `monkeypatch.setenv("HOME", ...)` had no effect. Re-running without the mainnet
  tests — `uv run pytest --ignore=tests/test_mainnet_wallet.py -k "not mainnet"`
  — gave `69 passed, 2 skipped, 6 deselected`, confirming none of my own code
  was failing.

- **What I changed:** nothing in the code. I did not delete or rename the real
  mainnet wallet, because the message says it may hold money and the README says
  never to delete it while it holds a balance. The workaround is to run the test
  suite without the mainnet tests on Windows.

- **What it cost:** nothing beyond a few minutes of confusion. No key was
  touched, no transaction was signed.

- **Would the checks have caught it?** No, and here is why: this is a test
  harness problem, not a buyer or signer problem. The seven field checks run
  inside the buyer and have nothing to do with how pytest isolates the home
  directory. The wallet's refusal to overwrite an existing key is the correct
  behavior the checks rely on, not something to fix.