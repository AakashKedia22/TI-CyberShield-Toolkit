# TI CyberShield Toolkit — Service Architecture

Version: 0.1.0 · Status: proposal · Machine-readable contract: [`openapi.yaml`](openapi.yaml)

This document defines the target architecture for upgrading the TI CyberShield
Toolkit (tisecprov) from a monolithic CLI/GUI into two HTTP services consumed by
any frontend. Today the frontend is the PyQt5 wizard; tomorrow it is a React SPA
in the browser.

## 1. Overview

```
┌────────────────────────────────────────────────────────────┐
│  Frontend (today: PyQt wizard → tomorrow: React SPA)       │
│  Talks ONLY to HTTP APIs. No crypto, no hardware access.   │
└───────────────┬──────────────────────────┬─────────────────┘
                │  HTTPS / JSON            │  HTTPS / JSON
                ▼                          ▼
┌────────────────────────────┐  ┌────────────────────────────┐
│ Backend #1  "crypto/HSM"   │  │ Backend #2  "target"       │
│ Stateless; all sensitive   │  │ Near-hardware; stateful     │
│ key material lives here    │  │ Serial (UART) + CCS (JTAG)  │
│ · sessions & keys          │  │ · SoC ID / device type      │
│ · certs (OTP/ROT/debug/    │  │ · key & code provisioning   │
│   recovery)                │  │ · device recovery flow      │
│ · image sign / encrypt     │  │ · binary download           │
│ · SoC ID parsing           │  │ · serial port discovery     │
└────────────────────────────┘  └────────────────────────────┘
```

The API is a single OpenAPI spec with two tags (`crypto`, `target`) served
behind one origin. A gateway (the crypto service) serves the SPA statically and
reverse-proxies `/target/*` and `/jobs/*` to the target service.

## 2. Hard boundaries

| Capability | Backend #1 (crypto) | Backend #2 (target) |
|---|---|---|
| Generate/own SMPK/BMPK/MEK | yes | no |
| Password-protected key sessions | yes | no |
| Sign/encrypt images, certs | yes | no |
| Parse SoC ID | yes (pure) | no |
| Serial port / UART access | no | yes |
| CCS / JTAG access | no | yes |
| Flash keys / code to device | no | yes |
| Hold private keys | yes | never |

**Rule:** B2 never performs a cryptographic operation and never sees a private
key. It only receives public artifacts (certificates, signed/encrypted images)
to flash. B1 never touches hardware.

This split exists because B2 must run on the machine with the serial port and
CCS, while B1 can run on a secure host (ideally with the HSM attached) and be
shared by many engineers.

## 3. Contract summary

Full request/response schemas are in [`openapi.yaml`](openapi.yaml). Highlights:

### Backend #1 — crypto (`tag: crypto`)
- `POST /sessions` — generate keys, create session (`genkeys`)
- `POST /sessions/{name}/open` — password → short-lived `X-Session-Token`
- `GET /sessions/{name}/public-keys` — public keys + wrapped MEKs only
- `POST /devices/{d}/certificates` — OTP key certificate (`gencert`)
- `POST /devices/{d}/certificates/rot|debug|recovery` — auxiliary certs
- `POST /devices/{d}/images/sign|sign-seccfg|encrypt` — signing/encryption
- `POST /devices/{d}/images/sign-batch` — prebuilt set signing (async job)
- `POST /devices/{d}/socid/parse` — `parseSoCId`

### Backend #2 — target (`tag: target`)
- `GET /ports`, `GET /devices` — discovery
- `POST /targets/socid` — `getSoCId` (UART)
- `POST /targets/type/uart|jtag` — device type detection
- `POST /targets/{d}/key-provisioning` — `uart_keyprov` / `jtag_keyprov`
- `POST /targets/{d}/code-provisioning` — `uart_codeprov` / `jtag_codeprov`
- `POST /targets/recovery/enable|uid-secap|validate` — recovery flow
- `POST /targets/download` — `download_binary`

### Shared (`tag: jobs`, `tag: artifacts`)
- `POST /artifacts`, `GET /artifacts/{id}` — file transfer store
- `POST /jobs`, `GET /jobs/{id}`, `DELETE /jobs/{id}` — async jobs
- `GET /jobs/{id}/logs`, `GET /jobs/{id}/stream` — paginated / SSE logs

## 4. Async job model

All **target** operations are asynchronous jobs because they interact with
hardware, are long-running, cancellable, and stream logs. Batch signing on B1 is
also a job. Everything else on B1 is synchronous.

```jsonc
{
  "id": "a1b2...", "service": "target", "type": "key_provisioning",
  "status": "running", "progress": 60, "exit_code": null,
  "logs_url": "/jobs/a1b2.../logs", "stream_url": "/jobs/a1b2.../stream",
  "created_at": "...", "started_at": "...", "finished_at": null
}
```

Lifecycle: `queued → running → succeeded | failed | cancelled`.

- **Cancel** maps to the existing `cancel_event` threading.Event already wired
  into `run_key_provisioning_uart/jtag`, `run_code_provisioning_uart/jtag`, and
  `_drain_proc/_drain_jtag`.
- **Logs** come from the existing `_drain_proc` / `_drain_jtag` capture loops,
  emitted as SSE `text/event-stream` events.
- **Progress**: a numeric 0–100; UART transfer lines ("send N bytes") can seed
  byte-progress; otherwise phase-based (0 start, 50 flashing, 100 done).

## 5. Error model

```jsonc
{ "error": { "code": "TARGET_TIMEOUT", "message": "No SoC ID received", "details": {} } }
```

| Condition | Code | HTTP |
|---|---|---|
| `ValueError` / validation | `INVALID_ARGUMENT` | 400 |
| missing session token / API key | `UNAUTHORIZED` | 401 |
| missing session/device/job/artifact | `*_NOT_FOUND` | 404 |
| session exists, conflicting state | `SESSION_EXISTS` / `CONFLICT` | 409 |
| process exit code != 0 | `TARGET_TIMEOUT` / `INTERNAL` | 502 |
| user cancelled | `OPERATION_CANCELLED` | 409 |

## 6. Function → endpoint mapping

| Current function | Endpoint |
|---|---|
| `generate_keys`, `create_development_session` | `POST /sessions`, `POST /sessions/{name}/development` |
| `generate_certificate(_from_args)` | `POST /devices/{d}/certificates` |
| `gen_rot_cert` / `gen_debug_auth_cert` / `gen_device_recovery_cert` | `POST /devices/{d}/certificates/{rot,debug,recovery}` |
| `sign_encrypt` / `sign_sec_cfg` / `encrypt_binary_command` | `POST /devices/{d}/images/{sign,sign-seccfg,encrypt}` |
| `sign_all_prebuilt_binaries` | `POST /devices/{d}/images/sign-batch` |
| `invoke_parseSoCID` | `POST /devices/{d}/socid/parse` |
| `getSoCId` | `POST /targets/socid` |
| `run_get_device_type_uart` / `run_get_device_type_jtag` | `POST /targets/type/{uart,jtag}` |
| `run_key_provisioning_uart/jtag` | `POST /targets/{d}/key-provisioning` |
| `run_code_provisioning_uart/jtag` | `POST /targets/{d}/code-provisioning` |
| `enable_device_recovery` / `run_get_device_uid_secap` / `send_device_recovery_cert` | `POST /targets/recovery/{enable,uid-secap,validate}` |
| `download_binary` / `list_ports` | `POST /targets/download` / `GET /ports` |

The existing `apps.spt.*`, `apps.tifs.*`, and `tisecprov.*` modules become the
**core libraries** that both services import — CLI/GUI and services share the
same code, so no logic is forked.

## 7. End-to-end flow (F29 key + code provisioning)

1. `POST /artifacts` — upload TI FEK pub.
2. `POST /sessions` — generate keys; `POST /sessions/{name}/open` → token.
3. `POST /devices/f29h85x/certificates` → `CertificateResult` artifact refs.
4. `POST /devices/f29h85x/images/sign-batch` (job) → signed prebuilt images.
5. `POST /artifacts` — upload `ram_based_uart_sbl.bin` kernel (project bin).
6. `POST /targets/f29h85x/key-provisioning` (UART) → job; stream logs; on
   success device state HS-FS → HSKP.
7. `POST /targets/f29h85x/code-provisioning` (UART) → job; stream logs.
8. `GET /artifacts/{id}` — download any cert / signed image for archival.

## 8. Security

- TLS everywhere; static `X-API-Key` per service; `X-Session-Token` (short
  lived, from `/sessions/{name}/open`) scopes crypto operations.
- The session **password is exchanged exactly once** (the open call). A browser
  SPA never retains it; private keys never leave B1.
- B1 is a signing oracle → rate-limit and audit-log every operation.
- B2 exposes no key material; validate artifact `purpose` on upload.

## 9. React frontend (future)

- **Thin client**: no crypto in the browser, no hardware access; only HTTP + SSE.
- **Typed SDK**: generate a TypeScript client from `openapi.yaml`
  (`openapi-typescript` or `openapi-generator`). Single source of truth.
- **State**: TanStack Query for sessions/artifacts/jobs; a WebSocket/SSE hook
  for live job logs (replaces `log_parser.py` / `LogManager`).
- **Page mapping from the Qt wizard** (port is mechanical):
  `LandingPage` → sessions + cert form; `ConfigPage` → device detect + batch
  sign; `ProvisioningPage` → job list + progress + results dialog.
- **Deployment**: B1 serves the built SPA and proxies B2 → single origin, no
  CORS, unified auth.

## 10. Suggested phasing

1. **Freeze the contract** — `openapi.yaml` is the acceptance test.
2. **B1** — add HTTP layer over existing core; CLI keeps calling the same core.
3. **B2** — async job server; the provisioning functions already accept
   `cancel_event` / `register_proc_cb`, so this is a clean fit.
4. **Dogfood** — port the PyQt wizard to consume the APIs.
5. **React SPA** — build against the generated SDK, reusing the same flow.