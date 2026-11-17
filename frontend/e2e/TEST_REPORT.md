# CyberShield Web UI: browser E2E test report

- **Target:** `http-api` @ `dc2d76d` plus the fixes on `claude/vibrant-wozniak-jqg82c`
- **Runner:** Playwright (Chromium, headless), `frontend/e2e/tests.mjs`, against the live stack with isolated session and artifact storage
- **Date:** 2026-11-17

## Current status: 46 / 46 passed

| Run | Result |
|-----|--------|
| Main group (T01–T38, 41 tests) | ✅ 41 passed |
| API-key group (T39–T43, crypto started with `CST_CRYPTO_API_KEY`) | ✅ 5 passed |
| Backend pytest (excluding `test_hsm.py`, which needs `python-pkcs11`) | 101 passed, 5 failed. The 5 failures are older and unrelated: `TypeError`s in `tests/test_certgen.py`. |

The first run, against unmodified `http-api` @ `3ee6283`, scored **37/43**. All 6 failures were product bugs, and all 6 are now fixed (see below).

## Bugs found and fixed

| # | Test | Bug | Fix |
|---|------|-----|-----|
| 1 | T32 | Job detail page stayed on "running" after the job finished | `JobView` syncs status and progress from the polled job, re-fetches the log when they change, and `JobDetailPage` stops polling once the job reaches a final status |
| 2 | T11 | "Public keys" failed for any session other than the active one | The UI prompts for that session's password, opens it, then loads its keys |
| 3 | T41 | Artifact upload didn't send `X-API-Key` | A single `authHeaders()` in `api.ts` is now used by every request, including uploads |
| 4 | T42/T43 | Download links and live log streaming got a 401 with an API key set | With a key set, downloads go through fetch + blob. The job stream now uses fetch with SSE parsing instead of `EventSource` |
| 5 | T23 | Debug and recovery certificates accepted a malformed UID and any debug type | Schemas require exactly 128 hex characters and a debug type of 0–4 (400 otherwise). The UI uses a labelled debug-type picker that defaults to DBG_PUBLIC_ENABLE (2) instead of DBG_FULL_ENABLE (4) |
| 6 | T27 | Ticking an encryption option without a key gave a 500 | The sign form has key uploads for SBL/TIFS and FW encryption and checks for them before submitting. The schema rejects `sbl_enc`/`tifs_enc` without `enc_key` and `fw_enc` without `fw_enc_key` (400), including on Sec-Cfg |

## Test list and results

| ID | Area | Test | Result |
|----|------|------|--------|
| T01 | Shell | App loads: brand, 5 nav links, health pill "crypto up" | ✅ |
| T02 | Shell | Each nav link routes correctly and is marked active | ✅ |
| T03 | Shell | Health pill shows "down" when crypto is unreachable and recovers on click | ✅ |
| T04 | Shell | Certificates and Images are gated until a session is opened | ✅ |
| T05 | Sessions | Create session (rsa4k/rsa4k): auto-opened, listed as active | ✅ |
| T06 | Sessions | Duplicate session name shows an error | ✅ |
| T07 | Sessions | Create session with ECC (secp384r1 / secp256r1) | ✅ |
| T08 | Sessions | Wrong password: error shown, active session unchanged | ✅ |
| T09 | Sessions | Open a session from the table (password prompt) | ✅ |
| T10 | Sessions | Public keys of the active session are listed and downloadable | ✅ |
| T11 | Sessions | Public keys of a non-active session prompts for its password and opens it | ✅ |
| T12 | Sessions | Create the F29 Development session and open it | ✅ |
| T13 | Sessions | "Clear" resets the header and re-gates Certificates | ✅ |
| T14 | Sessions | Page reload drops the opened session (documents current behaviour) | ✅ |
| T15 | Certificates | Generate without a TI FEK shows a clear error | ✅ |
| T16 | Certificates | Upload the TI FEK public key | ✅ |
| T17 | Certificates | OTP cert with defaults; primary/secondary/final download | ✅ |
| T18 | Certificates | OTP cert with 4 protect flags and an extended OTP row (index 4) | ✅ |
| T18b | Certificates | Extended OTP index not a multiple of 4 is rejected | ✅ |
| T19 | Certificates | Invalid MSV is rejected | ✅ |
| T20 | Certificates | Invalid key count (7) is rejected | ✅ |
| T21 | Certificates | ROT switching certificate generated and downloadable | ✅ |
| T22 | Certificates | Debug certificate with a valid 128-hex UID | ✅ |
| T22b | Certificates | Debug type is a labelled picker defaulting to DBG_PUBLIC_ENABLE | ✅ |
| T23 | Certificates | Debug certificate with a malformed UID is rejected | ✅ |
| T24 | Certificates | Device recovery certificate with a valid UID | ✅ |
| T25 | Images | Upload and sign an image (C29/FLASH); signed image downloads | ✅ |
| T26 | Images | Sign for RAM boot, key rev 2, debug option | ✅ |
| T27 | Images | SBL encryption without a key is blocked with a clear message | ✅ |
| T27b | Images | SBL encryption with an uploaded key signs successfully | ✅ |
| T28 | Images | Encrypt with the session key | ✅ |
| T29 | Images | Encrypt with an uploaded AES-256 key | ✅ |
| T30 | Images | Sec-Cfg without an image shows a guard message | ✅ |
| T31 | Images | Sec-Cfg without a CCS path shows a guard message | ✅ |
| T32 | Images/Jobs | Batch sign: job detail reaches a final status | ✅ |
| T33 | Jobs | Jobs list shows the job with a working "view" link | ✅ |
| T34 | Jobs | "Stream live" toggles; log panel populated | ✅ |
| T35 | Jobs | Unknown job ID shows an error | ✅ |
| T36 | Artifacts | Upload with a purpose; listed and downloadable | ✅ |
| T37 | Artifacts | "Clear" empties the list | ✅ |
| T38 | Sessions | Deleting the active session clears the header and the list | ✅ |
| T39 | API key | No key: sessions list shows an auth error | ✅ |
| T40 | API key | Entering the key in the header makes the list load | ✅ |
| T41 | API key | Artifact upload with the key set | ✅ |
| T42 | API key | Clicking a download link saves the file | ✅ |
| T43 | API key | Batch job reaches "succeeded"; live log stream works | ✅ |

## Not covered (needs hardware or isn't in the UI)
- Device detection, key provisioning, code provisioning, SoC ID, recovery and flash download. The target service has endpoints for these, but the UI has no page for them yet.
- PKCS#11/HSM sessions (needs `python-pkcs11` and a token).
- Sec-Cfg signing on the success path (needs a CCS install).

## Reproduce
```bash
# services + UI
./run_dev.sh
# tests (see frontend/e2e/README.md)
node frontend/e2e/tests.mjs
# API-key group: restart crypto with CST_CRYPTO_API_KEY=<k>, then
API_KEY=<k> S1=<existing rsa session> node tests.mjs --group apikey
```
Failure screenshots are written to `frontend/e2e/results/` (gitignored) (T11, T23, T27, T32, T41, T42).
