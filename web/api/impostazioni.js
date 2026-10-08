// GET/PUT: marketplace e preset dei parametri, condivisi tra tutti i dispositivi
const { send, protezione, leggiJSON, scriviJSON, leggiCorpo } = require("./_lib");

const PERCORSO = "config/impostazioni.json";

module.exports = async (req, res) => {
  if (!protezione(req, res)) return;
  if (req.method === "GET") return send(res, 200, { impostazioni: await leggiJSON(PERCORSO) });
  if (req.method === "PUT") {
    const b = await leggiCorpo(req);
    if (!b || !Array.isArray(b.retailer)) return send(res, 400, { errore: "Formato non valido" });
    const r = await scriviJSON(PERCORSO, { retailer: b.retailer, preset: b.preset || [], aggiornato: new Date().toISOString() }, "aggiorna impostazioni dal sito");
    if (r.status !== 200 && r.status !== 201) return send(res, 502, { errore: `Salvataggio non riuscito (${r.status})` });
    return send(res, 200, { ok: true });
  }
  return send(res, 405, { errore: "Metodo non supportato" });
};
