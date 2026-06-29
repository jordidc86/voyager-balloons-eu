#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const DATA_DIR = path.join(ROOT, "data", "backlinks");
const TEMPLATE_DIR = path.join(ROOT, "templates", "outreach");
const REPORT_DIR = path.join(DATA_DIR, "reports");
const DRAFT_DIR = path.join(DATA_DIR, "drafts");

const OPPORTUNITIES = path.join(DATA_DIR, "opportunities.csv");
const LINK_AUDIT = path.join(DATA_DIR, "link_audit.csv");
const COMPETITORS = path.join(DATA_DIR, "competitors.json");

const SAFE_STATUSES = new Set(["new", "qualified", "drafted", "approved", "sent", "replied", "won", "lost", "do_not_contact"]);
const NO_DRAFT_STATUSES = new Set(["sent", "replied", "won", "lost", "do_not_contact"]);

const TEMPLATE_BY_TYPE = {
  hotel: "hotel.md",
  rural_lodging: "hotel.md",
  travel_blog: "blog-media.md",
  international_travel_blog: "blog-media.md",
  media_blog: "blog-media.md",
  national_media: "blog-media.md",
  travel_guide: "blog-media.md",
  international_travel_guide: "blog-media.md",
  local_media: "blog-media.md",
  institutional_directory: "directory.md",
  marketplace_directory: "directory.md",
  tour_marketplace: "directory.md",
  affiliate_platform: "directory.md",
  gift_marketplace: "directory.md",
  experience_platform: "directory.md",
  creator: "creator.md",
  influencer: "creator.md",
  owned_social: "partner.md",
  partner: "partner.md",
};

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function todayStamp() {
  return new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
}

function readText(file) {
  return fs.readFileSync(file, "utf8");
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let value = "";
  let quoted = false;

  for (let i = 0; i < text.length; i++) {
    const char = text[i];
    const next = text[i + 1];

    if (quoted && char === '"' && next === '"') {
      value += '"';
      i++;
      continue;
    }

    if (char === '"') {
      quoted = !quoted;
      continue;
    }

    if (!quoted && char === ",") {
      row.push(value);
      value = "";
      continue;
    }

    if (!quoted && (char === "\n" || char === "\r")) {
      if (char === "\r" && next === "\n") i++;
      row.push(value);
      if (row.some((cell) => cell !== "")) rows.push(row);
      row = [];
      value = "";
      continue;
    }

    value += char;
  }

  if (value || row.length) {
    row.push(value);
    if (row.some((cell) => cell !== "")) rows.push(row);
  }

  if (!rows.length) return [];
  const headers = rows[0].map((header) => header.trim());
  return rows.slice(1).map((cells) => {
    const record = {};
    headers.forEach((header, index) => {
      record[header] = (cells[index] || "").trim();
    });
    return record;
  });
}

function csvEscape(value) {
  const stringValue = value == null ? "" : String(value);
  if (/[",\n\r]/.test(stringValue)) return `"${stringValue.replace(/"/g, '""')}"`;
  return stringValue;
}

function writeCsv(file, rows, headers) {
  const output = [
    headers.join(","),
    ...rows.map((row) => headers.map((header) => csvEscape(row[header])).join(",")),
  ].join("\n");
  fs.writeFileSync(file, `${output}\n`);
}

function readOpportunities() {
  const rows = parseCsv(readText(OPPORTUNITIES));
  for (const row of rows) {
    if (!SAFE_STATUSES.has(row.status)) {
      throw new Error(`Estado no valido para ${row.domain}: ${row.status}`);
    }
  }
  return rows;
}

function domainFromUrl(value) {
  if (!value) return "";
  try {
    const input = value.startsWith("http") ? value : `https://${value}`;
    return new URL(input).hostname.replace(/^www\./, "").toLowerCase();
  } catch {
    return value.replace(/^www\./, "").toLowerCase();
  }
}

function slugify(value) {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80);
}

function scoreOpportunity(row) {
  let score = 0;
  const reasons = [];
  const domain = domainFromUrl(row.domain || row.url_or_profile);

  const relevantTypes = new Set([
    "hotel",
    "rural_lodging",
    "travel_blog",
    "international_travel_blog",
    "travel_guide",
    "international_travel_guide",
    "media_blog",
    "national_media",
    "local_media",
    "institutional_directory",
    "gift_marketplace",
    "marketplace_directory",
    "tour_marketplace",
    "affiliate_platform",
  ]);

  if (relevantTypes.has(row.type)) {
    score += 25;
    reasons.push("relevancia turistica/local");
  }

  if (["warm", "owned"].includes(row.relationship)) {
    score += 20;
    reasons.push("relacion previa o control propio");
  } else if (row.relationship === "cold") {
    score += 6;
  }

  if (row.priority === "P0") {
    score += 20;
    reasons.push("prioridad P0");
  } else if (row.priority === "P1") {
    score += 12;
  } else if (row.priority === "P2") {
    score += 5;
  }

  if (row.email || row.instagram) {
    score += 12;
    reasons.push("contacto directo disponible");
  }

  if (row.target_url && row.target_url.includes("voyagerballoons.eu")) {
    score += 8;
    reasons.push("landing destino definida");
  }

  if (row.competitor_linked) {
    score += 8;
    reasons.push("menciona/enlaza competidor");
  }

  if (/(tourism|travel|traveler|traveller|trip|guide|madrid|spain|segovia|things|experience|activity|balloon|turismo|viaje|escapada|blog|tripadvisor|civitatis|viator|getyourguide|klook|musement|tiqets|headout|fever)/i.test(domain)) {
    score += 10;
    reasons.push("dominio semanticamente relevante");
  }

  if (["international_travel_blog", "international_travel_guide", "national_media"].includes(row.type)) {
    score += 12;
    reasons.push("audiencia nacional/internacional prioritaria");
  }

  if (/(madrid|spain|segovia|day.trip|things.to.do|escapada|viajes|traveler|lonelyplanet|roughguides|fodors|getyourguide|viator|klook|musement|tiqets|headout|fever)/i.test(`${domain} ${row.url_or_profile} ${row.notes}`)) {
    score += 8;
    reasons.push("encaje con demanda de Madrid/Espana");
  }

  if (["competitor", "do_not_contact"].includes(row.relationship) || row.status === "do_not_contact") {
    score = 0;
    reasons.push("excluido para contacto");
  }

  const risk = estimateRisk(row);
  if (risk === "high") score -= 15;
  if (risk === "medium") score -= 5;

  return {
    score: Math.max(0, Math.min(100, score)),
    risk,
    reasons: reasons.join("; "),
  };
}

function estimateRisk(row) {
  if (row.relationship === "competitor" || row.status === "do_not_contact") return "high";
  if (["marketplace_directory", "gift_marketplace", "experience_platform", "tour_marketplace", "affiliate_platform"].includes(row.type)) return "medium";
  if (row.offer && /(vuelo|regalo|comision|commission|sorteo)/i.test(row.offer)) return "medium";
  return "low";
}

function scoreCommand() {
  ensureDir(REPORT_DIR);
  const rows = readOpportunities().map((row) => {
    const scored = scoreOpportunity(row);
    const recommendedStatus = row.status === "new" && scored.score >= 55 ? "qualified" : row.status;
    return {
      ...row,
      score: scored.score,
      risk: scored.risk,
      recommended_status: recommendedStatus,
      score_reasons: scored.reasons,
    };
  });

  const headers = [
    "score",
    "risk",
    "recommended_status",
    "domain",
    "url_or_profile",
    "type",
    "priority",
    "status",
    "relationship",
    "offer",
    "target_url",
    "contact_name",
    "email",
    "instagram",
    "competitor_linked",
    "score_reasons",
    "notes",
  ];

  rows.sort((a, b) => Number(b.score) - Number(a.score) || a.domain.localeCompare(b.domain));
  const reportFile = path.join(REPORT_DIR, `opportunity-score-${todayStamp()}.csv`);
  writeCsv(reportFile, rows, headers);

  const top = rows
    .filter((row) => !NO_DRAFT_STATUSES.has(row.status))
    .slice(0, 12)
    .map((row) => `${row.score}/100 ${row.domain} (${row.type}, ${row.risk}) -> ${row.target_url}`)
    .join("\n");

  console.log(`Informe creado: ${path.relative(ROOT, reportFile)}`);
  console.log("\nTop oportunidades:");
  console.log(top || "No hay oportunidades cualificables.");
}

function templateNameFor(row) {
  if (row.offer === "hotel_pack") return "hotel.md";
  if (row.offer === "creator_collaboration") return "creator.md";
  if (row.offer === "profile_update") return "partner.md";
  if (row.offer === "profile_optimization") return "directory.md";
  if (row.offer === "gift_collaboration") return "directory.md";
  return TEMPLATE_BY_TYPE[row.type] || "blog-media.md";
}

function renderTemplate(row) {
  const templateFile = path.join(TEMPLATE_DIR, templateNameFor(row));
  const fallbackName = row.contact_name || `equipo de ${row.domain}`;
  return readText(templateFile).replace(/\{\{(\w+)\}\}/g, (_, key) => {
    if (key === "contact_name") return fallbackName;
    return row[key] || "";
  });
}

function draftCommand(args) {
  ensureDir(DRAFT_DIR);
  const limit = Number(readArg(args, "--limit", "20"));
  const minScore = Number(readArg(args, "--min-score", "50"));
  const batchDir = path.join(DRAFT_DIR, todayStamp());
  ensureDir(batchDir);

  const rows = readOpportunities()
    .map((row) => ({ ...row, ...scoreOpportunity(row) }))
    .filter((row) => !NO_DRAFT_STATUSES.has(row.status))
    .filter((row) => row.score >= minScore)
    .sort((a, b) => Number(b.score) - Number(a.score) || a.domain.localeCompare(b.domain))
    .slice(0, limit);

  const indexRows = [];
  for (const row of rows) {
    const filename = `${String(Math.round(row.score)).padStart(3, "0")}-${slugify(row.domain)}.md`;
    const file = path.join(batchDir, filename);
    const body = renderTemplate(row);
    const metadata = [
      "---",
      `domain: ${row.domain}`,
      `url_or_profile: ${row.url_or_profile}`,
      `type: ${row.type}`,
      `priority: ${row.priority}`,
      `score: ${row.score}`,
      `risk: ${row.risk}`,
      `status: draft_pending_approval`,
      `target_url: ${row.target_url}`,
      "---",
      "",
    ].join("\n");

    fs.writeFileSync(file, `${metadata}${body}\n`);
    indexRows.push({
      file: path.relative(ROOT, file),
      domain: row.domain,
      score: row.score,
      risk: row.risk,
      target_url: row.target_url,
      notes: row.notes,
    });
  }

  writeCsv(path.join(batchDir, "index.csv"), indexRows, ["file", "domain", "score", "risk", "target_url", "notes"]);
  console.log(`Borradores creados: ${path.relative(ROOT, batchDir)}`);
  console.log(`Total: ${rows.length}`);
}

async function fetchHtml(url) {
  const response = await fetch(url, {
    redirect: "follow",
    headers: {
      "user-agent": "VoyagerBalloonsSEOAudit/1.0 (+https://www.voyagerballoons.eu/)",
      accept: "text/html,application/xhtml+xml",
    },
  });
  const text = await response.text();
  return { status: response.status, url: response.url, text };
}

function findLink(html, targetUrl) {
  if (!html || !targetUrl) return { found: false, rel: "", anchor: "" };
  const targetDomain = domainFromUrl(targetUrl);
  const anchorRegex = /<a\b[^>]*href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/gi;
  let match;

  while ((match = anchorRegex.exec(html))) {
    const href = match[1];
    const anchorHtml = match[2] || "";
    const anchor = anchorHtml.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
    const wholeTag = match[0];
    const relMatch = wholeTag.match(/\brel=["']([^"']+)["']/i);
    if (href.includes(targetUrl) || domainFromUrl(href) === targetDomain) {
      return {
        found: true,
        rel: relMatch ? relMatch[1] : "",
        anchor,
      };
    }
  }

  return { found: html.includes(targetUrl) || html.includes(targetDomain), rel: "", anchor: "" };
}

async function auditCommand() {
  ensureDir(REPORT_DIR);
  const rows = readOpportunities().filter((row) => row.status === "won" || row.status === "sent" || row.status === "replied");
  const now = new Date().toISOString();
  const output = [];

  for (const row of rows) {
    const record = {
      domain: row.domain,
      url_or_profile: row.url_or_profile,
      target_url: row.target_url,
      expected_anchor: "",
      last_checked_at: now,
      http_status: "",
      link_found: "false",
      rel: "",
      anchor: "",
      status: row.status,
      notes: "",
    };

    try {
      const html = await fetchHtml(row.url_or_profile);
      const link = findLink(html.text, row.target_url);
      record.http_status = html.status;
      record.link_found = String(link.found);
      record.rel = link.rel;
      record.anchor = link.anchor;
      record.notes = link.found ? "link_or_mention_found" : "no_target_link_found";
    } catch (error) {
      record.notes = `fetch_error: ${error.message}`;
    }

    output.push(record);
  }

  const headers = ["domain", "url_or_profile", "target_url", "expected_anchor", "last_checked_at", "http_status", "link_found", "rel", "anchor", "status", "notes"];
  writeCsv(LINK_AUDIT, output, headers);
  const reportFile = path.join(REPORT_DIR, `link-audit-${todayStamp()}.csv`);
  writeCsv(reportFile, output, headers);
  console.log(`Auditoria creada: ${path.relative(ROOT, reportFile)}`);
  console.log(`Total revisado: ${output.length}`);
}

async function scanCommand(args) {
  const input = readArg(args, "--input", path.join(DATA_DIR, "candidate_urls.txt"));
  if (!fs.existsSync(input)) {
    throw new Error(`No existe ${input}. Crea un TXT con una URL por linea o usa --input <archivo>.`);
  }

  ensureDir(REPORT_DIR);
  const competitors = JSON.parse(readText(COMPETITORS));
  const urls = readText(input)
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith("#"));

  const output = [];
  for (const url of urls) {
    const record = {
      source_url: url,
      http_status: "",
      page_title: "",
      competitor_mentions: "",
      voyager_link_found: "false",
      recommended_type: "new_opportunity",
      notes: "",
    };

    try {
      const html = await fetchHtml(url);
      record.http_status = html.status;
      const titleMatch = html.text.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
      record.page_title = titleMatch ? titleMatch[1].replace(/\s+/g, " ").trim() : "";
      const lowerHtml = html.text.toLowerCase();
      record.competitor_mentions = competitors
        .filter((competitor) => lowerHtml.includes(competitor.domain.toLowerCase()) || lowerHtml.includes(competitor.name.toLowerCase()))
        .map((competitor) => competitor.domain)
        .join(";");
      record.voyager_link_found = String(lowerHtml.includes("voyagerballoons.eu"));
      if (record.competitor_mentions) record.recommended_type = "competitor_backlink";
      if (lowerHtml.includes("hotel") || lowerHtml.includes("alojamiento")) record.recommended_type = "hotel";
    } catch (error) {
      record.notes = `fetch_error: ${error.message}`;
    }

    output.push(record);
  }

  const reportFile = path.join(REPORT_DIR, `candidate-scan-${todayStamp()}.csv`);
  writeCsv(reportFile, output, ["source_url", "http_status", "page_title", "competitor_mentions", "voyager_link_found", "recommended_type", "notes"]);
  console.log(`Escaneo creado: ${path.relative(ROOT, reportFile)}`);
  console.log(`URLs revisadas: ${output.length}`);
}

function readArg(args, name, fallback) {
  const index = args.indexOf(name);
  if (index === -1) return fallback;
  return args[index + 1] || fallback;
}

function help() {
  console.log(`Uso:
  node scripts/backlink-outreach.js score
  node scripts/backlink-outreach.js draft --limit 20 --min-score 50
  node scripts/backlink-outreach.js audit
  node scripts/backlink-outreach.js scan --input data/backlinks/candidate_urls.txt

El sistema nunca envia mensajes. Solo puntua oportunidades, genera borradores y audita enlaces publicados.`);
}

async function main() {
  const [command, ...args] = process.argv.slice(2);
  if (!command || command === "help" || command === "--help") return help();
  if (command === "score") return scoreCommand();
  if (command === "draft") return draftCommand(args);
  if (command === "audit") return auditCommand(args);
  if (command === "scan") return scanCommand(args);
  throw new Error(`Comando desconocido: ${command}`);
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
