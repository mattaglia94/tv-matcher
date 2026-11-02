// POST {id, nome}: cambia il nome di una ricerca già lanciata (salvato in config/nomi.json sul ramo dati).
const { send, protezione, leggiJSON, scriviJSON, leggiCorpo } = require("./_lib");

module.exports = async (req, res) => {
  if (!protezione(req, res)) return;
  if (req.method !== "POST") return send(res, 405, { errore: "Usa POST" });
  const { id, nome } = await leggiCorpo(req);
  const n = String(nome || "").replace(/\|/g, "/").trim().slice(0, 80);
  if (!/^[\w-]+$/.test(String(id || ""))) return send(res, 400, { errore: "Ricerca non valida" });
  if (!n) return send(res, 400, { errore: "Scrivi un nome" });
  const nomi = (await leggiJSON("config/nomi.json")) || {};
  nomi[id] = n;
  const w = await scriviJSON("config/nomi.json", nomi, `rinomina ricerca ${id}`);
  if (w.status !== 200 && w.status !== 201) return send(res, 502, { errore: `Nome non salvato (${w.status})` });
  return send(res, 200, { ok: true, nome: n });
};
