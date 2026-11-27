// UI for the InForce browser checker. Logic lives in checker.js; data in export.json.
import { check } from "./checker.js";

const SAMPLE = `PAYE is computed under the Personal Income Tax Act (PITA). First deduct the
Consolidated Relief Allowance (CRA): 20% of gross income plus the higher of
₦200,000 or 1% of gross income. Then apply the graduated bands to what is left:
the first ₦300,000 is taxed at 7%, and the next ₦300,000 at 11%, rising band by
band after that.

For the company, the gain on the building is not part of its income tax. It is
charged separately under the Capital Gains Tax Act, and companies pay capital
gains tax at 10% of the chargeable gain.`;

const $ = (id) => document.getElementById(id);
let DATA = null;

function el(tag, attrs = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") e.className = v; else e.setAttribute(k, v);
  }
  for (const k of kids) e.append(k instanceof Node ? k : document.createTextNode(k ?? ""));
  return e;
}

function render(result) {
  const out = $("result");
  out.replaceChildren();
  const v = result.verdict;
  const summary = {
    STALE: "Rests on repealed law.",
    SUSPECT: "Nothing repealed found, but some of it rests on unverified or unrecognised rules.",
    CURRENT: "Every claim found rests on law in force.",
    NO_CLAIMS: "No Nigerian tax law citations or recognised tax figures found.",
  }[v];
  out.append(el("p", { class: "verdict" }, el("span", { class: `badge ${v}` }, v), ` on ${result.on}. ${summary}`));
  if (!result.items.length) return;
  const table = el("table");
  table.append(el("thead", {}, el("tr", {}, ...["Line", "Claim", "Status", "Ended", "Now"].map((h) => el("th", {}, h)))));
  const body = el("tbody");
  for (const i of result.items) {
    let now = i.successor ?? (i.verdict === "REPEALED" ? "no replacement" : "");
    if (i.related?.length) now += (now ? " · " : "") + `related, not a successor: ${i.related.join("; ")}`;

    const status = el("td", {}, el("span", { class: `badge ${i.verdict}` }, i.verdict), i.verified ? "" : " *",
                      ...(i.editions ?? []).map((e) => el("div", { class: "note" }, `${e.version}: ${e.status}`)));
    const claim = el("td", {}, i.claim, i.note ? el("div", { class: "note" }, i.note) : "",
                     ...(i.ruleNotes ?? []).map((n) => el("div", { class: "note proviso" }, n)));
    claim.setAttribute("data-label", "Claim");
    status.setAttribute("data-label", "Status");
    body.append(el("tr", {}, el("td", { class: "num", "data-label": "Line" }, String(i.line)), claim, status,
                   el("td", { class: "date", "data-label": "Ended" }, i.endedOn ?? ""),
                   el("td", { "data-label": "Now" }, now,
                      ...(i.successorNotes ?? []).map((n) => el("div", { class: "note proviso" }, n)))));
  }
  table.append(body);
  out.append(el("div", { class: "scroll" }, table));
  if (result.items.some((i) => !i.verified)) {
    out.append(el("p", { class: "note" }, "* unverified: not yet checked against the Act's text by a human."));
  }
}

// Today in the visitor's own time zone (toISOString() is UTC: in Lagos just after midnight it is yesterday).
function today() {
  const t = new Date();
  return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}`;
}

const longDate = (iso) => new Date(`${iso}T12:00:00`).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });

function run() {
  if (!DATA) return;
  render(check($("text").value, DATA, $("on").value || today()));
}

async function init() {
  $("on").value = today();
  $("sample").addEventListener("click", () => { $("text").value = SAMPLE; run(); });
  $("go").addEventListener("click", run);
  $("on").addEventListener("change", run);
  try {
    const res = await fetch("export.json", { cache: "no-store" });
    DATA = await res.json();
    const n = Object.keys(DATA.rules).length;
    const v = DATA.verification;
    $("meta").textContent = `Law data exported ${longDate(DATA.generated)}: ${n} rules; ` +
      (v ? `${v.verified} of ${v.total} law entries verified against the Act's text` : `${DATA.unverified} rules not yet verified`) +
      `; statuses change on ${DATA.dates.slice(1).map(longDate).join(", ")}.`;
  } catch (e) {
    $("meta").textContent = "The law data could not be loaded, so nothing can be checked right now.";
  }
}
init();
