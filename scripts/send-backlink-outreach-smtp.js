#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const DASHBOARD_ROOT = process.env.VOYAGER_DASHBOARD_ROOT || "/Users/Jordi/Documents/Codex/2026-05-11/puedes-crear-un-repo-nuevo-en";
const ENV_PATH = process.env.VOYAGER_SMTP_ENV || path.join(DASHBOARD_ROOT, ".env.local");
const nodemailer = require(path.join(DASHBOARD_ROOT, "node_modules", "nodemailer"));

const EXPECTED_FROM = "info@voyagerballoons.eu";
const QUEUE_FILE = path.join(ROOT, "data", "backlinks", "media-pack", "batches", "send-queue-01.csv");
const REPORT_DIR = path.join(ROOT, "data", "backlinks", "reports");

function readEnv(file) {
  const env = {};
  for (const rawLine of fs.readFileSync(file, "utf8").split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;
    const index = line.indexOf("=");
    if (index === -1) continue;
    const key = line.slice(0, index).trim();
    let value = line.slice(index + 1).trim();
    value = value.replace(/^['"]|['"]$/g, "");
    env[key] = value;
  }
  return env;
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

function readArg(name, fallback = "") {
  const index = process.argv.indexOf(name);
  return index === -1 ? fallback : process.argv[index + 1] || fallback;
}

function hasFlag(name) {
  return process.argv.includes(name);
}

function loadQueue() {
  const queueFile = readArg("--queue", QUEUE_FILE);
  return parseCsv(fs.readFileSync(queueFile, "utf8"));
}

function filterQueue(rows) {
  const only = readArg("--only", "");
  const domains = only ? new Set(only.split(",").map((item) => item.trim()).filter(Boolean)) : null;
  return rows.filter((row) => {
    if (row.status !== "ready_to_send") return false;
    if (row.channel !== "email") return false;
    if (!row.to_or_url || !row.to_or_url.includes("@")) return false;
    if (domains && !domains.has(row.domain)) return false;
    return true;
  });
}

function subjectFor(row) {
  return row.subject || `Editorial resource from Voyager Balloons EU`;
}

async function main() {
  const env = readEnv(ENV_PATH);
  const smtpUser = (env.SMTP_USER || "").toLowerCase();
  if (smtpUser !== EXPECTED_FROM) {
    throw new Error(`Envio bloqueado: SMTP_USER debe ser ${EXPECTED_FROM}, recibido ${smtpUser || "(vacio)"}`);
  }
  if (!env.SMTP_APP_PASSWORD) throw new Error("Envio bloqueado: falta SMTP_APP_PASSWORD");

  const selected = filterQueue(loadQueue());
  if (!selected.length) {
    console.log("No hay emails ready_to_send para enviar.");
    return;
  }

  if (!hasFlag("--yes")) {
    console.log("Modo simulacion. Se enviarian:");
    selected.forEach((row) => console.log(`- ${row.domain} -> ${row.to_or_url} | ${subjectFor(row)}`));
    console.log("Para enviar de verdad, ejecuta con --yes.");
    return;
  }

  const transport = nodemailer.createTransport({
    host: env.SMTP_HOST || "smtp.gmail.com",
    port: Number(env.SMTP_PORT || 465),
    secure: Number(env.SMTP_PORT || 465) === 465,
    requireTLS: Number(env.SMTP_PORT || 465) === 587,
    auth: { user: env.SMTP_USER, pass: env.SMTP_APP_PASSWORD },
    tls: { servername: env.SMTP_HOST || "smtp.gmail.com" },
  });

  fs.mkdirSync(REPORT_DIR, { recursive: true });
  const sentRows = [];
  for (const row of selected) {
    const bodyFile = path.resolve(ROOT, row.body_file);
    const text = fs.readFileSync(bodyFile, "utf8");
    const info = await transport.sendMail({
      from: `Voyager Balloons EU <${EXPECTED_FROM}>`,
      replyTo: EXPECTED_FROM,
      to: row.to_or_url,
      subject: subjectFor(row),
      text,
    });
    sentRows.push({
      sent_at: new Date().toISOString(),
      domain: row.domain,
      to: row.to_or_url,
      subject: subjectFor(row),
      message_id: info.messageId || "",
      provider: "smtp",
      from: EXPECTED_FROM,
    });
    console.log(`Enviado: ${row.domain} -> ${row.to_or_url}`);
  }

  const logFile = path.join(REPORT_DIR, `smtp-outreach-sent-${new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19)}.csv`);
  writeCsv(logFile, sentRows, ["sent_at", "domain", "to", "subject", "message_id", "provider", "from"]);
  console.log(`Log: ${path.relative(ROOT, logFile)}`);
}

main().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
