// POST: avvia una nuova ricerca sul workflow GitHub "Run dal sito"
const { REPO, WORKFLOW, send, protezione, gh, branchPrincipale, leggiCorpo } = require("./_lib");

module.exports = async (req, res) => {
  if (!protezione(req, res)) return;
  if (req.method !== "POST") return send(res, 405, { errore: "Usa POST" });
  const b = await leggiCorpo(req);
  const asin = (b.asin || []).filter((a) => /^B0[A-Z0-9]{8}$/.test(a.asin));
  const retailer = (b.retailer || []).filter((r) => r.attivo !== false && r.url && r.nome);
  if (!asin.length) return send(res, 400, { errore: "Nessun ASIN valido" });
  if (!retailer.length) return send(res, 400, { errore: "Nessun marketplace selezionato" });
  const ora = new Date();
  const id = ora.toISOString().replace(/[-:T]/g, "").slice(0, 14) + "-" + Math.random().toString(36).slice(2, 6);
  const nome = String(b.nome || "").replace(/\|/g, "/").slice(0, 80);
  const config = JSON.stringify({ nome, asin, retailer, parametri: b.parametri || {} });
  if (config.length > 60000) return send(res, 400, { errore: "Troppi ASIN in una sola ricerca: dividili in più ricerche (max ~2.000)" });
  const r = await gh(`/repos/${REPO}/actions/workflows/${WORKFLOW}/dispatches`, {
    metodo: "POST",
    corpo: { ref: await branchPrincipale(), inputs: { run_id: id, nome, config } },
  });
  if (r.status !== 204 && r.status !== 200) {
    return send(res, 502, { errore: `GitHub ha rifiutato l'avvio (${r.status}): ${(r.dati && r.dati.message) || ""}` });
  }
  return send(res, 200, { id });
};
