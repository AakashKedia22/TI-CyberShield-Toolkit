# CyberShield Web UI: browser E2E test report

- **Target:** `http-api` branch @ `3ee6283` (React/Vite UI → crypto service :8000, target service :8001)
- **Runner:** Playwright (Chromium, headless), `frontend/e2e/tests.mjs`, against the live stack with isolated session and artifact storage
- **Date:** 2026-11-17
- **Result:** **37 / 43 passed, 6 failed.** All 6 failures are confirmed product bugs. No test-side failures remain and the browser reported no JS page errors.
- **Backend unit baseline (pytest, excluding `test_hsm.py`, which needs `python-pkcs11`):** 93 passed, 5 failed. All 5 failures are in `tests/test_certgen.py` and are `TypeError`s, probably tests that no longer match the code.

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
| T11 | Sessions | Public keys of a **non-active** session from the table | ❌ **BUG** |
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
| T23 | Certificates | Debug certificate with a malformed UID is rejected | ❌ **BUG** |
| T24 | Certificates | Device recovery certificate with a valid UID | ✅ |
| T25 | Images | Upload and sign an image (C29/FLASH); signed image downloads | ✅ |
| T26 | Images | Sign for RAM boot, key rev 2, debug option | ✅ |
| T27 | Images | Sign with "SBL enc" ticked | ❌ **BUG** |
| T28 | Images | Encrypt with the session key | ✅ |
| T29 | Images | Encrypt with an uploaded AES-256 key | ✅ |
| T30 | Images | Sec-Cfg without an image shows a guard message | ✅ |
| T31 | Images | Sec-Cfg without a CCS path shows a guard message | ✅ |
| T32 | Images/Jobs | Batch sign: job detail reaches a final status | ❌ **BUG** |
| T33 | Jobs | Jobs list shows the job with a working "view" link | ✅ |
| T34 | Jobs | "Stream live" toggles; log panel populated | ✅ |
| T35 | Jobs | Unknown job ID shows an error | ✅ |
| T36 | Artifacts | Upload with a purpose; listed and downloadable | ✅ |
| T37 | Artifacts | "Clear" empties the list | ✅ |
| T38 | Sessions | Deleting the active session clears the header and the list | ✅ |
| T39 | API key | No key: sessions list shows an auth error | ✅ |
| T40 | API key | Entering the key in the header makes the list load | ✅ |
| T41 | API key | Artifact upload with the key set | ❌ **BUG** |
| T42 | API key | Download links with the key set | ❌ **BUG** |

## Bugs found

1. **T32: Job detail never shows a finished job (frontend).** The batch job succeeded in about 1 s (the API reports `succeeded`, 2/2 signed) but the page shows `running` indefinitely with a full progress bar. *Cause:* `JobView.tsx` copies `job.status` into `useState` once and only updates it from the live stream, so the 1.5 s polling in `JobDetailPage` never reaches the status pill. The log panel is also only fetched once.
2. **T11: "Public keys" on any non-active row fails** with "Session token is not valid for this session". The UI sends the active session's token for every row, and the backend (`require_session`) only accepts a token for the same session. *Fix:* disable the button on non-active rows, or prompt for that session's password first.
3. **T41: Artifact upload ignores the API key** and gets 401 "Invalid API key". `artifactsApi.upload` (`api.ts`) calls `fetch` directly and never adds `X-API-Key`.
4. **T42: Downloads and live log streaming break when an API key is set** (HTTP 401). `DownloadLink` is a plain `<a href>` and `EventSource` can't send custom headers. *Fix:* fetch with headers and download as a blob, or let the server accept a short-lived signed URL or query token.
5. **T23: Debug certificate accepts a malformed UID** (backend). `dev_uid: "1234"` returns 200 with a certificate, even though the form says "128 hex chars". `dev_dbg_type: 99` is also accepted. Non-hex input (`"zz"`) is rejected. *Fix:* add `pattern=^[0-9a-fA-F]{128}$` and an allowed set of debug types in `DebugCertRequest`; the recovery request probably needs the same.
6. **T27: "SBL enc" makes signing fail with a 500** ("core operation aborted (exit 1)"; the server log says "Please give the key to be used for encryption"). The sign form has encryption checkboxes but no key upload, and the schema's `enc_key` / `fw_enc_key` / `kd_salt` aren't exposed. The backend should also return a 4xx validation error rather than a 500.

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
