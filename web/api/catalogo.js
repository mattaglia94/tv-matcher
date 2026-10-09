// GET/PUT: modifiche al catalogo marche e serie (il catalogo predefinito è /catalogo.json)
const { send, protezione, leggiJSON, scriviJSON, leggiCorpo } = require("./_lib");

const PERCORSO = "config/catalogo.json";
const TEC = ["LED", "QLED", "MINILED", "NEOQLED", "OLED"];
const FASCE = ["BASE", "ENTRY", "MID", "PREMIUM", "TOP"];

function pulisci(m) {
  if (m.rimossa) return { marca: String(m.marca || "").slice(0, 60), rimossa: true };
  return {
    marca: String(m.marca || "").trim().slice(0, 60),
    alias: (m.alias || []).map((a) => String(a).trim().toUpperCase().slice(0, 40)).filter(Boolean).slice(0, 12),
    note: String(m.note || "").slice(0, 300),
    fascia_predefinita: FASCE.includes(m.fascia_predefinita) ? m.fascia_predefinita : "",
    tecnologia_predefinita: TEC.includes(m.tecnologia_predefinita) ? m.tecnologia_predefinita : "",
    serie: (m.serie || []).filter((s) => s && String(s.serie || "").trim()).slice(0, 200).map((s) => ({
      serie: String(s.serie).trim().toUpperCase().slice(0, 30),
      tecnologia: TEC.includes(s.tecnologia) ? s.tecnologia : "LED",
      fascia: FASCE.includes(s.fascia) ? s.fascia : "ENTRY",
      descrizione: String(s.descrizione || "").slice(0, 120),
      ...(s.famiglia ? { famiglia: String(s.famiglia).toUpperCase().replace(/[^A-Z0-9-]/g, "").slice(0, 40) } : {}),
      ...(s.pro === true || s.pro === false ? { pro: s.pro } : {}),
    })),
  };
}

module.exports = async (req, res) => {
  if (!protezione(req, res)) return;
  if (req.method === "GET") return send(res, 200, { utente: (await leggiJSON(PERCORSO)) || { marche: [] } });
  if (req.method === "PUT") {
    const b = await leggiCorpo(req);
    if (!b || !Array.isArray(b.marche)) return send(res, 400, { errore: "Formato non valido" });
    const marche = b.marche.map(pulisci).filter((m) => m.marca);
    const r = await scriviJSON(PERCORSO, { marche, aggiornato: new Date().toISOString() }, "aggiorna catalogo marche dal sito");
    if (r.status !== 200 && r.status !== 201) return send(res, 502, { errore: `Salvataggio non riuscito (${r.status})` });
    return send(res, 200, { ok: true });
  }
  return send(res, 405, { errore: "Metodo non supportato" });
};
