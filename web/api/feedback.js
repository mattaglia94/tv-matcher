// Feedback degli utenti: solo raccolta, non modifica il motore né il catalogo.
// Un file per feedback sul ramo dati (feedback/<id>.json): nessun conflitto se due persone scrivono insieme.
// GET  -> elenco (più recenti prima)
// POST {nome, tipo, messaggio, asin, paese, negozio, modello, link, ricerca} -> nuovo feedback
// PATCH {id, stato} -> stato di valutazione (nuovo / in valutazione / applicato / scartato)
const { REPO, send, protezione, gh, leggiJSON, scriviJSON, leggiCorpo } = require("./_lib");

const TIPI = ["Abbinamento errato", "Modello mancante", "Suggerimento", "Problema del sito", "Altro"];
const STATI = ["nuovo", "in valutazione", "applicato", "scartato"];
const taglia = (v, n) => String(v ?? "").trim().slice(0, n);

module.exports = async (req, res) => {
  if (!protezione(req, res)) return;

  if (req.method === "GET") {
    const dir = await gh(`/repos/${REPO}/contents/feedback?ref=dati`);
    if (dir.status === 404) return send(res, 200, { feedback: [] });
    if (dir.status !== 200 || !Array.isArray(dir.dati)) return send(res, 502, { errore: `Lettura non riuscita (${dir.status})` });
    const file = dir.dati.filter((f) => f.name.endsWith(".json")).sort((a, b) => b.name.localeCompare(a.name)).slice(0, 300);
    const lista = await Promise.all(file.map(async (f) => {
      try { return await leggiJSON(f.path); } catch { return null; }
    }));
    return send(res, 200, { feedback: lista.filter(Boolean) });
  }

  if (req.method === "POST") {
    const b = await leggiCorpo(req);
    const messaggio = taglia(b.messaggio, 4000);
    if (messaggio.length < 3) return send(res, 400, { errore: "Scrivi il feedback" });
    const ora = new Date();
    const id = ora.toISOString().replace(/[-:T]/g, "").slice(0, 14) + "-" + Math.random().toString(36).slice(2, 6);
    const fb = {
      id, data: ora.toISOString(), stato: "nuovo",
      nome: taglia(b.nome, 80), tipo: TIPI.includes(b.tipo) ? b.tipo : "Altro", messaggio,
      asin: taglia(b.asin, 20).toUpperCase(), paese: taglia(b.paese, 4).toUpperCase(), negozio: taglia(b.negozio, 60),
      modello: taglia(b.modello, 80), link: /^https?:\/\//i.test(b.link || "") ? taglia(b.link, 600) : "",
      ricerca: taglia(b.ricerca, 60),
    };
    const w = await scriviJSON(`feedback/${id}.json`, fb, `feedback: ${fb.tipo}`);
    if (w.status !== 200 && w.status !== 201) return send(res, 502, { errore: `Invio non riuscito (${w.status})` });
    return send(res, 201, { ok: true, feedback: fb });
  }

  if (req.method === "PATCH") {
    const { id, stato } = await leggiCorpo(req);
    if (!/^[\w-]+$/.test(String(id || "")) || !STATI.includes(stato)) return send(res, 400, { errore: "Richiesta non valida" });
    const fb = await leggiJSON(`feedback/${id}.json`);
    if (!fb) return send(res, 404, { errore: "Feedback non trovato" });
    fb.stato = stato;
    const w = await scriviJSON(`feedback/${id}.json`, fb, `feedback ${id}: ${stato}`);
    if (w.status !== 200 && w.status !== 201) return send(res, 502, { errore: `Salvataggio non riuscito (${w.status})` });
    return send(res, 200, { ok: true, feedback: fb });
  }

  return send(res, 405, { errore: "Metodo non ammesso" });
};
