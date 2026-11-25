// InForce browser checker: claim extraction and lookup. No law is decided here.
// Statuses come from web/export.json, computed by Cypher against the Relate law pack at each
// date where a status can change; the patterns are the same ones `inforce check` uses.
// Mirrors inforce/cite_parser.py and inforce/check.py (tests/test_web.py compares the two).

function lineOf(text, pos) {
  let n = 1;
  for (let i = 0; i < pos; i++) if (text[i] === "\n") n++;
  return n;
}

function sectionNear(text, start, end, sec) {
  const before = text.slice(Math.max(0, start - 30), start);
  const reBefore = new RegExp(sec.source + String.raw`\s+of(?:\s+the)?\s*$`, sec.flags);
  const mb = before.match(reBefore);
  if (mb) return mb.groups.num;
  const reAfter = new RegExp(String.raw`^[\s,]*(?:\(\s*)?` + sec.source, sec.flags);
  const ma = text.slice(end, end + 25).match(reAfter);
  return ma ? ma.groups.num : null;
}

function allMatches(text, pat) {
  const flags = pat.flags.includes("g") ? pat.flags : pat.flags + "g";
  return [...text.matchAll(new RegExp(pat.source, flags))];
}

export function extract(text, P) {
  const found = [];
  for (const act of P.acts) {
    for (const alias of act.aliases) {
      for (const m of allMatches(text, alias)) {
        found.push({ kind: "citation", text: m[0], start: m.index, act: act.short,
                     section: sectionNear(text, m.index, m.index + m[0].length, P.section) });
      }
    }
  }
  for (const c of P.concepts) {
    for (const m of allMatches(text, c)) found.push({ kind: "concept", text: m[0], start: m.index, rule: c.rule });
  }
  for (const f of P.figures) {
    for (const m of allMatches(text, f)) {
      const g = m.groups || {};
      found.push({ kind: "figure", text: m[0].split(/\s+/).join(" "), start: m.index, topic: f.topic,
                   value: Math.round(parseFloat(g.pct) / 100 * 1e6) / 1e6,
                   amount: g.amount ? g.amount.replace(/\D/g, "") : null });
    }
  }
  const key = (c) => JSON.stringify([c.kind, c.act ?? null, c.section ?? null, c.rule ?? null,
                                     c.topic ?? null, c.value ?? null, c.amount ?? null]);
  const merged = new Map();
  for (const c of found.sort((a, b) => a.start - b.start)) {
    const k = key(c);
    if (merged.has(k)) merged.get(k).mentions++;
    else merged.set(k, { ...c, mentions: 1, line: lineOf(text, c.start) });
  }
  // A bare mention of an Act also cited with a section is the same citation.
  for (const [k, c] of [...merged]) {
    if (c.kind === "citation" && !c.section) {
      const sectioned = [...merged.values()].find((x) => x.kind === "citation" && x.act === c.act && x.section);
      if (sectioned) { sectioned.mentions += c.mentions; merged.delete(k); }
    }
  }
  return [...merged.values()].sort((a, b) => a.start - b.start);
}

export function dateIndex(dates, on) {
  let idx = 0;
  dates.forEach((d, i) => { if (d <= on) idx = i; });
  return idx;
}

const numbers = (s) => new Set((s || "").match(/\d[\d,]*/g)?.map((n) => n.replace(/,/g, "")) ?? []);

export function resolve(c, data, idx) {
  const item = (ref, verdict, at, extra = {}) => ({
    line: c.line, claim: c.text, kind: c.kind, ref, verdict, mentions: c.mentions,
    endedOn: at?.endedOn ?? null, successor: at?.successor ?? null, successorRef: at?.successorRef ?? null,
    related: at?.related ?? [], ...extra,
  });
  if (c.kind === "concept") {
    const r = data.rules[c.rule];
    if (!r) return [item(c.rule, "NOT_RECOGNISED", null, { verified: false })];
    return [item(c.rule, r.at[idx].status, r.at[idx], { verified: r.verified, source: r.source })];
  }
  if (c.kind === "figure") {
    let hits = Object.entries(data.rules).filter(([, r]) =>
      r.topic === c.topic && r.value !== null && Math.abs(r.value - c.value) < 1e-6);
    if (c.amount) hits = hits.filter(([, r]) => numbers(r.text).has(c.amount));
    if (!hits.length) return [item(null, "NOT_RECOGNISED", null, { verified: false })];
    return hits.map(([id, r]) => item(id, r.at[idx].status, r.at[idx], { verified: r.verified, source: r.source }));
  }
  if (c.section) {
    const p = data.provisions[`${c.act}|${c.section}`];
    if (p) return [item(p.akn, p.at[idx].status, p.at[idx], { verified: p.verified, claim: `${c.text} s. ${c.section}` })];
  }
  const a = data.acts[c.act];
  if (!a) return [item(c.act, "NOT_RECOGNISED", null, { verified: false })];
  const note = c.section ? `section ${c.section} is not in the law pack; status is for the whole Act` : null;
  return [item(a.akn, a.at[idx].status, a.at[idx], {
    verified: a.verified, source: a.source, note,
    claim: c.section ? `${c.text} s. ${c.section}` : c.text })];
}

export function overall(items) {
  if (!items.length) return "NO_CLAIMS";
  if (items.some((i) => i.verdict === "REPEALED")) return "STALE";
  if (items.some((i) => !i.verified || ["NOT_RECOGNISED", "NOT_YET", "UNKNOWN"].includes(i.verdict))) return "SUSPECT";
  return "CURRENT";
}

export function check(text, data, on) {
  const idx = dateIndex(data.dates, on);
  const items = extract(text, data.patterns).flatMap((c) => resolve(c, data, idx));
  return { verdict: overall(items), on, items };
}
