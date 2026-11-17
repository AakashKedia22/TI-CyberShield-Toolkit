// End-to-end browser tests for the CyberShield web UI (http-api branch).
// Runs against the live stack: Vite :5173 -> crypto :8000 / target :8001.
// Usage: see frontend/e2e/README.md
import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));

const BASE = process.env.BASE_URL ?? "http://localhost:5173";
const ROOT = process.env.REPO_ROOT ?? path.resolve(HERE, "../.."); // repo root
const OUT = path.resolve(process.env.OUT_DIR ?? path.join(HERE, "results"));
const FEK = path.join(ROOT, "test_keys/rsa4096_test_pub.pem");
const IMAGE = path.join(ROOT, "host/bin/asm/f29h85x/ram_based_uart_sbl.bin");
const AES = path.join(ROOT, "host/src/apps/spt/f29_devel_keys/aes256.key");
const UID = "a1".repeat(64); // 128 hex chars
const RUN = Date.now().toString(36);
const S1 = process.env.S1 ?? `e2e_${RUN}_rsa`;
const S2 = `e2e_${RUN}_ecc`;
const PW = "Passw0rd!";

fs.mkdirSync(OUT, { recursive: true });

const tests = [];
const T = (id, title, fn, opts = {}) => tests.push({ id, title, fn, ...opts });

// ---------------------------------------------------------------- helpers
const card = (page, heading) =>
  page.locator("section.card").filter({ has: page.getByRole("heading", { name: heading }) });
const nav = async (page, label) => {
  await page.locator("nav.sidebar").getByRole("link", { name: label, exact: true }).click();
};
const errorBox = (page) => page.locator(".error-box");
const notice = (page) => page.locator(".notice-box");
async function expectText(locator, re, timeout = 15000) {
  await locator.first().waitFor({ state: "visible", timeout });
  const end = Date.now() + timeout;
  let t = "";
  while (Date.now() < end) {
    t = await locator.first().innerText().catch(() => "");
    if (re.test(t)) return t;
    await new Promise((r) => setTimeout(r, 200));
  }
  throw new Error(`expected ${re} but got: ${t.slice(0, 300)}`);
}
async function expectNoError(page) {
  if (await errorBox(page).count()) {
    throw new Error("unexpected error box: " + (await errorBox(page).first().innerText()));
  }
}
async function download(page, link) {
  const href = await link.getAttribute("href");
  const res = await page.request.get(BASE + href);
  const body = await res.body();
  return { status: res.status(), size: body.length, href };
}
async function openSession(page, name, pw) {
  await nav(page, "Sessions");
  const c = card(page, "Open an existing session");
  await c.getByLabel("Name").fill(name);
  await c.getByLabel("Password").fill(pw);
  await c.getByRole("button", { name: "Open" }).click();
  await expectText(notice(page), new RegExp(`Session "${name}" opened`));
}
const row = (page, name) =>
  card(page, "Existing sessions").locator("tbody tr").filter({ has: page.locator("td", { hasText: new RegExp(`^${name}`) }) });

// ================================================================ SHELL
T("T01", "App shell loads: brand, 5 nav links, crypto health = up", async (page) => {
  await page.goto(BASE);
  await expectText(page.locator(".brand"), /TI CyberShield Toolkit/);
  const links = await page.locator("nav.sidebar a").allInnerTexts();
  if (links.join("|") !== "Sessions|Certificates|Images|Artifacts|Jobs") throw new Error("nav: " + links);
  await expectText(page.locator("button.health"), /crypto up/);
  await expectText(page.locator(".topbar"), /no session opened/);
});

T("T02", "Each nav link routes to its page and marks itself active", async (page) => {
  for (const [label, h1, url] of [
    ["Certificates", "Certificates", "/certificates"],
    ["Images", "Images", "/images"],
    ["Artifacts", "Artifacts", "/artifacts"],
    ["Jobs", "Jobs", "/jobs"],
    ["Sessions", "Sessions & keys", "/"],
  ]) {
    await nav(page, label);
    await expectText(page.locator("h1"), new RegExp(h1.replace("&", "&")));
    if (new URL(page.url()).pathname !== url) throw new Error(`url ${page.url()} != ${url}`);
    const active = await page.locator("nav.sidebar a.active").innerText();
    if (active !== label) throw new Error(`active=${active}`);
  }
});

T("T03", "Health pill shows 'crypto down' when service unreachable, recovers on click", async (page) => {
  await page.route("**/api/crypto/health", (r) => r.fulfill({ status: 502, body: "" }));
  await page.reload();
  await expectText(page.locator("button.health"), /crypto down/);
  await page.unroute("**/api/crypto/health");
  await page.locator("button.health").click();
  await expectText(page.locator("button.health"), /crypto up/);
});

T("T04", "Certificates and Images are gated until a session is opened", async (page) => {
  await nav(page, "Certificates");
  await expectText(page.locator(".card"), /Open a session on the Sessions page first/);
  await nav(page, "Images");
  await expectText(page.locator(".card"), /Open a session on the Sessions page first/);
});

// ================================================================ SESSIONS
T("T05", "Create session (rsa4k/rsa4k) auto-opens it and lists it as active", async (page) => {
  await nav(page, "Sessions");
  const c = card(page, /Create session/);
  await c.getByLabel("Name").fill(S1);
  await c.getByLabel("Password").fill(PW);
  await c.getByRole("button", { name: /Generate & open/ }).click();
  await expectText(notice(page), new RegExp(`Session "${S1}" created and opened`), 120000);
  await expectText(page.locator(".active-session"), new RegExp(S1));
  await expectText(row(page, S1), /active/);
}, { timeout: 150000 });

T("T06", "Creating a session with a duplicate name shows an error", async (page) => {
  const c = card(page, /Create session/);
  await c.getByLabel("Name").fill(S1);
  await c.getByLabel("Password").fill(PW);
  await c.getByRole("button", { name: /Generate & open/ }).click();
  await expectText(errorBox(page), /exist/i, 60000);
});

T("T07", "Create session with ECC keys (secp384r1 / secp256r1)", async (page) => {
  await page.reload();
  const c = card(page, /Create session/);
  await c.getByLabel("Name").fill(S2);
  await c.getByLabel("Password").fill(PW);
  await c.getByLabel("SMPK").selectOption("secp384r1");
  await c.getByLabel("BMPK").selectOption("secp256r1");
  await c.getByRole("button", { name: /Generate & open/ }).click();
  await expectText(notice(page), new RegExp(`Session "${S2}" created and opened`), 120000);
}, { timeout: 150000 });

T("T08", "Opening a session with the wrong password shows an error", async (page) => {
  const c = card(page, "Open an existing session");
  await c.getByLabel("Name").fill(S1);
  await c.getByLabel("Password").fill("wrong-password");
  await c.getByRole("button", { name: "Open" }).click();
  await expectText(errorBox(page), /./, 30000);
  // active session must not change
  await expectText(page.locator(".active-session"), new RegExp(S2));
});

T("T09", "Open session via the table 'Open' button (password prompt)", async (page) => {
  page.once("dialog", (d) => d.accept(PW));
  await row(page, S1).getByRole("button", { name: "Open" }).click();
  await expectText(notice(page), new RegExp(`Session "${S1}" opened`), 30000);
  await expectText(row(page, S1), /active/);
});

T("T10", "Public keys of the active session are listed and downloadable", async (page) => {
  await row(page, S1).getByRole("button", { name: "Public keys" }).click();
  const box = page.locator(".box").filter({ hasText: "Public keys" });
  await expectText(box, /Public keys \(\d+\)/);
  const n = await box.locator("a.download").count();
  if (n < 2) throw new Error(`only ${n} public key links`);
  const d = await download(page, box.locator("a.download").first());
  if (d.status !== 200 || d.size === 0) throw new Error(`download ${JSON.stringify(d)}`);
});

T("T11", "Public keys of a NON-active session (table button) [known bug #2]", async (page) => {
  await row(page, S2).getByRole("button", { name: "Public keys" }).click();
  await page.waitForTimeout(1500);
  await expectNoError(page);
});

T("T12", "Create F29 Development session and open it with the published password", async (page) => {
  await page.getByRole("button", { name: "Create F29 Development session" }).click();
  await expectText(notice(page), /Development session created/, 120000);
  await expectText(row(page, "Development"), /Development/);
  await openSession(page, "Development", "develop123#");
}, { timeout: 150000 });

T("T13", "Clear session resets the header and re-gates Certificates", async (page) => {
  await page.locator(".topbar").getByRole("button", { name: "Clear" }).click();
  await expectText(page.locator(".topbar"), /no session opened/);
  await nav(page, "Certificates");
  await expectText(page.locator(".card"), /Open a session/);
});

T("T14", "Reloading the page drops the opened session (in-memory token)", async (page) => {
  await openSession(page, S1, PW);
  await page.reload();
  await expectText(page.locator(".topbar"), /no session opened/);
  await openSession(page, S1, PW); // restore for following tests
});

// ================================================================ CERTIFICATES
T("T15", "Generate OTP cert before uploading TI FEK shows a clear error", async (page) => {
  await nav(page, "Certificates");
  await card(page, "OTP key certificate").getByRole("button", { name: "Generate certificate" }).click();
  await expectText(errorBox(page), /Upload the TI FEK public key first/);
});

T("T16", "Upload TI FEK public key", async (page) => {
  const c = card(page, "TI FEK public key");
  await c.locator('input[type=file]').setInputFiles(FEK);
  await c.getByRole("button", { name: "Upload" }).click();
  await expectText(c.locator("p.muted"), /uploaded:/);
});

T("T17", "Generate OTP key certificate with defaults; primary/secondary/final downloadable", async (page) => {
  const c = card(page, "OTP key certificate");
  await c.getByRole("button", { name: "Generate certificate" }).click();
  await expectText(notice(page), /Certificate generated successfully/, 120000);
  const links = c.locator(".box a.download");
  if ((await links.count()) !== 3) throw new Error("expected 3 cert links");
  for (let i = 0; i < 3; i++) {
    const d = await download(page, links.nth(i));
    if (d.status !== 200 || d.size === 0) throw new Error(`cert ${i}: ${JSON.stringify(d)}`);
  }
}, { timeout: 150000 });

T("T18", "Generate OTP cert with protect flags + extended OTP row", async (page) => {
  const c = card(page, "OTP key certificate");
  for (const f of ["MSV protect", "Keycnt protect", "SMPK/SMEK protect", "BMPK/BMEK protect"]) {
    await c.getByLabel(f).check();
  }
  await c.getByLabel("Value").fill("0x80000001");
  await c.getByLabel("Index").fill("4");
  await c.getByLabel("Size (bits)").fill("128");
  await c.getByRole("button", { name: "Generate certificate" }).click();
  await expectText(notice(page), /Certificate generated successfully/, 120000);
  await expectNoError(page);
}, { timeout: 150000 });

T("T18b", "Extended OTP index not a multiple of 4 is rejected with a readable error", async (page) => {
  const c = card(page, "OTP key certificate");
  await c.getByLabel("Index").fill("1");
  await c.getByRole("button", { name: "Generate certificate" }).click();
  await expectText(errorBox(page), /multiple of/, 60000);
  await c.getByLabel("Value").fill("");
}, { timeout: 90000 });

T("T19", "Invalid MSV value is rejected with an error", async (page) => {
  await page.reload();
  await openSession(page, S1, PW);
  await nav(page, "Certificates");
  const fek = card(page, "TI FEK public key");
  await fek.locator('input[type=file]').setInputFiles(FEK);
  await fek.getByRole("button", { name: "Upload" }).click();
  await expectText(fek.locator("p.muted"), /uploaded:/);
  const c = card(page, "OTP key certificate");
  await c.getByLabel("MSV", { exact: true }).fill("not-hex");
  await c.getByRole("button", { name: "Generate certificate" }).click();
  await expectText(errorBox(page), /./, 60000);
}, { timeout: 120000 });

T("T20", "Invalid key count (e.g. 7) is rejected with an error", async (page) => {
  const c = card(page, "OTP key certificate");
  await c.getByLabel("MSV", { exact: true }).fill("0x1E22D");
  await c.getByLabel("Key count").fill("7");
  await c.getByRole("button", { name: "Generate certificate" }).click();
  await page.waitForTimeout(500);
  await expectText(page.locator(".error-box, .notice-box"), /./, 60000);
  if (!(await errorBox(page).count())) throw new Error("keycnt=7 was accepted: " + (await notice(page).innerText()));
}, { timeout: 90000 });

T("T21", "Generate ROT switching certificate", async (page) => {
  await card(page, "ROT switching certificate").getByRole("button", { name: "Generate ROT cert" }).click();
  await expectText(notice(page), /ROT switching certificate generated/, 60000);
  const d = await download(page, card(page, "ROT switching certificate").locator("a.download"));
  if (d.status !== 200 || d.size === 0) throw new Error(JSON.stringify(d));
}, { timeout: 90000 });

T("T22", "Generate debug certificate with a valid 128-hex UID", async (page) => {
  const c = card(page, "Debug certificate");
  await c.getByLabel(/Device UID/).fill(UID);
  await c.getByRole("button", { name: "Generate" }).click();
  await expectText(notice(page), /Debug certificate generated/, 60000);
}, { timeout: 90000 });

T("T23", "Debug certificate with a malformed UID is rejected", async (page) => {
  const c = card(page, "Debug certificate");
  await c.getByLabel(/Device UID/).fill("1234");
  await c.getByRole("button", { name: "Generate" }).click();
  await expectText(errorBox(page), /./, 60000);
}, { timeout: 90000 });

T("T24", "Generate device recovery certificate with a valid UID", async (page) => {
  const c = card(page, "Device recovery certificate");
  await c.getByLabel(/Device UID/).fill(UID);
  await c.getByRole("button", { name: "Generate" }).click();
  await expectText(notice(page), /recovery certificate generated/, 60000);
}, { timeout: 90000 });

// ================================================================ IMAGES
T("T25", "Upload image and sign it (C29 / FLASH defaults); signed image downloadable", async (page) => {
  await nav(page, "Images");
  const up = card(page, "Upload image");
  await up.locator('input[type=file]').setInputFiles(IMAGE);
  await up.getByRole("button", { name: "Upload" }).click();
  await expectText(up.locator("p.muted"), /image:/);
  const c = card(page, /Sign application/);
  await c.getByRole("button", { name: "Sign" }).click();
  await expectText(notice(page), /Image signed successfully/, 120000);
  const d = await download(page, c.locator("a.download"));
  if (d.status !== 200 || d.size === 0) throw new Error(JSON.stringify(d));
}, { timeout: 150000 });

T("T26", "Sign for RAM boot with key rev 2 and debug option", async (page) => {
  const c = card(page, /Sign application/);
  await c.getByLabel("Boot").selectOption("RAM");
  await c.getByLabel("Load addr").fill("0x200E1000");
  await c.getByLabel("Key rev").selectOption("2");
  await c.getByLabel("Debug").fill("DBG_SOC_DEFAULT");
  await c.getByRole("button", { name: "Sign" }).click();
  await expectText(notice(page), /Image signed successfully/, 120000);
  await expectNoError(page);
}, { timeout: 150000 });

T("T27", "Sign with SBL encryption enabled", async (page) => {
  const c = card(page, /Sign application/);
  await c.getByLabel("SBL enc").check();
  await c.getByRole("button", { name: "Sign" }).click();
  await expectText(page.locator(".error-box, .notice-box"), /./, 120000);
  await expectNoError(page);
}, { timeout: 150000 });

T("T28", "Encrypt image using the session key (no uploaded key)", async (page) => {
  const c = card(page, "Encrypt binary");
  await c.getByRole("button", { name: "Encrypt" }).click();
  await expectText(page.locator(".error-box, .notice-box"), /./, 120000);
  await expectNoError(page);
}, { timeout: 150000 });

T("T29", "Encrypt image with an uploaded AES-256 key", async (page) => {
  const c = card(page, "Encrypt binary");
  await c.locator('input[type=file]').setInputFiles(AES);
  await c.getByRole("button", { name: "Upload key" }).click();
  await page.waitForTimeout(1000);
  await c.getByRole("button", { name: "Encrypt" }).click();
  await expectText(notice(page), /Image encrypted successfully/, 120000);
}, { timeout: 150000 });

T("T30", "Sign Sec-Cfg without an image shows 'Upload a seccfg image first'", async (page) => {
  await card(page, /Sign Sec-Cfg/).getByRole("button", { name: "Sign Sec-Cfg" }).click();
  await expectText(errorBox(page), /Upload a seccfg image first/);
});

T("T31", "Sign Sec-Cfg without a CCS path shows 'CCS path is required'", async (page) => {
  const c = card(page, /Sign Sec-Cfg/);
  await c.locator('input[type=file]').setInputFiles(IMAGE);
  await page.waitForTimeout(1000);
  await c.getByRole("button", { name: "Sign Sec-Cfg" }).click();
  await expectText(errorBox(page), /CCS path is required/);
});

T("T32", "Batch sign starts an async job and links to its detail page", async (page) => {
  await card(page, /Batch sign/).getByRole("button", { name: /Start batch sign/ }).click();
  const link = card(page, /Batch sign/).locator("a");
  await link.waitFor({ timeout: 30000 });
  await link.click();
  await page.waitForURL(/\/jobs\/crypto\//);
  await page.locator(".jobview").waitFor();
  // wait for terminal state
  await page.locator(".jobview .pill").filter({ hasText: /succeeded|failed|cancelled/ }).waitFor({ timeout: 120000 });
  const status = await page.locator(".jobview .pill").innerText();
  const log = await page.locator("pre.log").innerText();
  if (status !== "succeeded") throw new Error(`job ${status}; error: ${(await errorBox(page).allInnerTexts()).join(" ") || log.slice(-300)}`);
}, { timeout: 180000 });

// ================================================================ JOBS
T("T33", "Jobs page lists the batch job with status and a working 'view' link", async (page) => {
  await nav(page, "Jobs");
  const r = page.locator("tbody tr").filter({ hasText: "crypto" });
  await r.first().waitFor({ timeout: 10000 });
  await r.first().getByRole("link", { name: "view" }).click();
  await page.locator(".jobview").waitFor();
});

T("T34", "Job detail: 'Stream live' toggles and log panel is populated", async (page) => {
  await page.getByRole("button", { name: "Stream live" }).click();
  await page.getByRole("button", { name: "Stop stream" }).waitFor();
  const log = await page.locator("pre.log").innerText();
  if (!log || log === "(no log output yet)") throw new Error("empty log");
  await page.getByRole("button", { name: "Stop stream" }).click();
});

T("T35", "Unknown job id shows an error instead of loading forever", async (page) => {
  await page.goto(BASE + "/jobs/crypto/does-not-exist");
  await expectText(errorBox(page), /./, 10000);
});

// ================================================================ ARTIFACTS
T("T36", "Upload a file on the Artifacts page; it appears in the list and downloads", async (page) => {
  await page.goto(BASE + "/artifacts");
  const c = card(page, "Upload file");
  await c.locator('input[type=file]').setInputFiles(FEK);
  await c.getByLabel("Purpose").selectOption("tifek");
  await c.getByRole("button", { name: "Upload" }).click();
  await expectText(c.locator("p.muted"), /uploaded:/);
  const listed = card(page, /Known artifacts/).locator("tbody tr");
  if ((await listed.count()) < 1) throw new Error("not listed");
  const d = await download(page, listed.first().locator("a.download"));
  if (d.status !== 200 || d.size === 0) throw new Error(JSON.stringify(d));
});

T("T37", "Clear empties the known-artifacts list", async (page) => {
  await card(page, /Known artifacts/).getByRole("button", { name: "Clear" }).click();
  await expectText(card(page, /Known artifacts/), /Nothing yet/);
});

// ================================================================ SESSION DELETE (last, destructive)
T("T38", "Deleting the active session clears it from header and list", async (page) => {
  await openSession(page, S2, PW);
  await row(page, S2).getByRole("button", { name: "Delete" }).click();
  await expectText(page.locator(".topbar"), /no session opened/);
  await page.waitForTimeout(1000);
  if (await row(page, S2).count()) throw new Error("still listed");
});

// ================================================================ API KEY (needs crypto restarted with CST_CRYPTO_API_KEY)
T("T39", "[API key mode] without key: sessions list fails with an error", async (page) => {
  await page.evaluate(() => localStorage.removeItem("cst-api-key"));
  await page.goto(BASE);
  await expectText(errorBox(page), /API key|401|UNAUTHORIZED/i, 10000);
}, { group: "apikey" });

T("T40", "[API key mode] entering the key in the header makes the sessions list load", async (page) => {
  await page.locator("input.apikey").fill(process.env.API_KEY);
  await page.reload();
  await page.waitForTimeout(1500);
  await expectNoError(page);
  await expectText(row(page, S1), new RegExp(S1));
}, { group: "apikey" });

T("T41", "[API key mode] artifact upload works with key set [known bug #1]", async (page) => {
  await page.goto(BASE + "/artifacts");
  const c = card(page, "Upload file");
  await c.locator('input[type=file]').setInputFiles(FEK);
  await c.getByRole("button", { name: "Upload" }).click();
  await expectText(page.locator(".error-box, p.muted"), /./, 10000);
  await expectNoError(page);
}, { group: "apikey" });

T("T42", "[API key mode] download links work with key set [known bug #1]", async (page) => {
  await openSession(page, S1, PW);
  await row(page, S1).getByRole("button", { name: "Public keys" }).click();
  const link = page.locator(".box a.download").first();
  await link.waitFor({ timeout: 15000 });
  const href = await link.getAttribute("href");
  // what a browser click does: plain GET, no custom headers
  const res = await page.request.get(BASE + href);
  if (res.status() !== 200) throw new Error(`plain download GET -> HTTP ${res.status()}`);
}, { group: "apikey" });

// ================================================================ runner
const args = process.argv.slice(2);
const only = args.includes("--only") ? args[args.indexOf("--only") + 1].split(",") : null;
const group = args.includes("--group") ? args[args.indexOf("--group") + 1] : "main";
const selected = tests.filter((t) => (only ? only.includes(t.id) : (t.group ?? "main") === group));

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1400, height: 1000 } });
const page = await ctx.newPage();
const consoleErrors = [];
page.on("pageerror", (e) => consoleErrors.push(String(e)));
await page.goto(BASE);

const results = [];
for (const t of selected) {
  const start = Date.now();
  page.setDefaultTimeout(t.timeout ?? 20000);
  let status = "PASS", error = "";
  try {
    await Promise.race([
      t.fn(page),
      new Promise((_, rej) => setTimeout(() => rej(new Error("test timeout")), t.timeout ?? 60000)),
    ]);
  } catch (e) {
    status = "FAIL";
    error = String(e.message ?? e).split("\n")[0].slice(0, 400);
    await page.screenshot({ path: path.join(OUT, `${t.id}.png`), fullPage: true }).catch(() => {});
  }
  const ms = Date.now() - start;
  results.push({ id: t.id, title: t.title, status, ms, error });
  console.log(`${status === "PASS" ? "✔" : "✘"} ${t.id} ${t.title} (${ms}ms)${error ? "\n     → " + error : ""}`);
}
await browser.close();
fs.writeFileSync(path.join(OUT, `results-${group}.json`), JSON.stringify({ results, consoleErrors }, null, 2));
const failed = results.filter((r) => r.status === "FAIL").length;
console.log(`\n${results.length - failed} passed, ${failed} failed; page errors: ${consoleErrors.length}`);
