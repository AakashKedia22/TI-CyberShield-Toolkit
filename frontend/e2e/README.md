# Browser end-to-end tests

Playwright tests that drive the web UI against the live stack:
the Vite dev server on :5173, the crypto service on :8000 and the target service on :8001.

## Prerequisites
- The stack is running: `./run_dev.sh` from the repo root.
- Playwright and Chromium are installed (`npm i -D playwright && npx playwright install chromium`
  in `frontend/`, or a global install that `import "playwright"` can resolve).
- The tests use `test_keys/rsa4096_test_pub.pem` (TI FEK), `host/bin/asm/f29h85x/ram_based_uart_sbl.bin`
  (the image to sign) and `host/src/apps/spt/f29_devel_keys/aes256.key`.

## Run
```bash
node frontend/e2e/tests.mjs                 # main suite (T01–T38)
node frontend/e2e/tests.mjs --only T05,T10  # selected tests
```

API-key group (T39–T42): restart the crypto service with `CST_CRYPTO_API_KEY=<key>`, then
```bash
API_KEY=<key> S1=<existing rsa session name> node frontend/e2e/tests.mjs --group apikey
```

| Env var | Default | Meaning |
|---------|---------|---------|
| `BASE_URL` | `http://localhost:5173` | UI under test |
| `REPO_ROOT` | two levels up from this folder | where the fixture files are read from |
| `OUT_DIR` | `frontend/e2e/results` | failure screenshots and JSON results |

The tests create sessions named `e2e_<run-id>_*` and recreate the `Development` session,
so run them against a throwaway `TISECPROV_SESSION_DIR` if you have sessions you care about.

Tests run in order in one browser tab and share state (the open session, uploaded files).
With `--only`, include the tests that set that state up, e.g. `--only T05,T15,T16,T17`.

Each test is labelled with its ID; see `TEST_REPORT.md` for the test list and the latest results.
Tests tagged `[known bug #N]` are expected to fail until that bug is fixed.
