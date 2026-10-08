// Funzioni comuni alle API (Vercel non pubblica i file che iniziano con "_").
const crypto = require("crypto");

const REPO = process.env.GITHUB_REPO || "mattaglia94/tv-matcher";
const TOKEN = process.env.GITHUB_TOKEN || "";
const PASSWORD = process.env.APP_PASSWORD || "";
const SECRET = process.env.SESSION_SECRET || PASSWORD + "-tvm";
const BRANCH_DATI = "dati";
const WORKFLOW = "sito.yml";
const API = "https://api.github.com";

function send(res, status, body) {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");
  res.end(JSON.stringify(body));
}

function firma(exp) {
  return crypto.createHmac("sha256", SECRET).update(String(exp)).digest("hex");
}

function creaCookie() {
  const exp = Date.now() + 30 * 24 * 3600 * 1000;
  return `tvm=${exp}.${firma(exp)}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=${30 * 24 * 3600}`;
}

function autenticato(req) {
  if (!PASSWORD) return true; // nessuna password configurata: sito aperto
  const m = /(?:^|;\s*)tvm=(\d+)\.([a-f0-9]+)/.exec(req.headers.cookie || "");
  if (!m) return false;
  const exp = Number(m[1]);
  if (exp < Date.now()) return false;
  const atteso = firma(exp);
  return atteso.length === m[2].length && crypto.timingSafeEqual(Buffer.from(atteso), Buffer.from(m[2]));
}

// Blocca la richiesta se non autenticata o se manca la configurazione. Ritorna true se può proseguire.
function protezione(req, res) {
  if (!autenticato(req)) { send(res, 401, { errore: "Accesso richiesto" }); return false; }
  if (!TOKEN) { send(res, 500, { errore: "Configurazione incompleta: manca GITHUB_TOKEN su Vercel" }); return false; }
  return true;
}

async function gh(percorso, { metodo = "GET", corpo, raw = false } = {}) {
  const r = await fetch(API + percorso, {
    method: metodo,
    headers: {
      Authorization: `Bearer ${TOKEN}`,
      Accept: raw ? "application/vnd.github.raw+json" : "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "User-Agent": "tv-matcher-web",
      ...(corpo ? { "Content-Type": "application/json" } : {}),
    },
    body: corpo ? JSON.stringify(corpo) : undefined,
  });
  const testo = await r.text();
  let dati = null;
  try { dati = testo ? JSON.parse(testo) : null; } catch { dati = testo; }
  return { status: r.status, dati };
}

let _defaultBranch = null;
async function branchPrincipale() {
  if (_defaultBranch) return _defaultBranch;
  const r = await gh(`/repos/${REPO}`);
  _defaultBranch = (r.dati && r.dati.default_branch) || "main";
  return _defaultBranch;
}

async function assicuraBranchDati() {
  const r = await gh(`/repos/${REPO}/git/ref/heads/${BRANCH_DATI}`);
  if (r.status === 200) return;
  const base = await branchPrincipale();
  const ref = await gh(`/repos/${REPO}/git/ref/heads/${base}`);
  await gh(`/repos/${REPO}/git/refs`, { metodo: "POST", corpo: { ref: `refs/heads/${BRANCH_DATI}`, sha: ref.dati.object.sha } });
}

async function leggiJSON(percorso) {
  const r = await gh(`/repos/${REPO}/contents/${percorso}?ref=${BRANCH_DATI}`, { raw: true });
  if (r.status !== 200) return null;
  return typeof r.dati === "string" ? JSON.parse(r.dati) : r.dati;
}

async function scriviJSON(percorso, oggetto, messaggio) {
  await assicuraBranchDati();
  const esistente = await gh(`/repos/${REPO}/contents/${percorso}?ref=${BRANCH_DATI}`);
  const corpo = {
    message: messaggio || `aggiorna ${percorso}`,
    content: Buffer.from(JSON.stringify(oggetto, null, 1)).toString("base64"),
    branch: BRANCH_DATI,
  };
  if (esistente.status === 200 && esistente.dati.sha) corpo.sha = esistente.dati.sha;
  return gh(`/repos/${REPO}/contents/${percorso}`, { metodo: "PUT", corpo });
}

// Esecuzioni del workflow lanciate dal sito: run-name = "<id> | <nome>"
async function elencoRun(quanti = 50) {
  const r = await gh(`/repos/${REPO}/actions/workflows/${WORKFLOW}/runs?per_page=${quanti}`);
  if (r.status !== 200) return [];
  return (r.dati.workflow_runs || []).map((w) => {
    const [id, ...nome] = String(w.display_title || "").split(" | ");
    return {
      id: id.trim(), nome: nome.join(" | ").trim(), github_id: w.id,
      status: w.status, conclusion: w.conclusion, creato: w.created_at, aggiornato: w.updated_at, url: w.html_url,
    };
  });
}

async function trovaRun(id) {
  return (await elencoRun(100)).find((r) => r.id === id) || null;
}

async function leggiCorpo(req) {
  if (req.body && typeof req.body === "object") return req.body;
  if (typeof req.body === "string") { try { return JSON.parse(req.body); } catch { return {}; } }
  const pezzi = [];
  for await (const c of req) pezzi.push(c);
  try { return JSON.parse(Buffer.concat(pezzi).toString() || "{}"); } catch { return {}; }
}

module.exports = {
  REPO, PASSWORD, WORKFLOW, send, creaCookie, autenticato, protezione, gh, branchPrincipale,
  leggiJSON, scriviJSON, elencoRun, trovaRun, leggiCorpo,
};
