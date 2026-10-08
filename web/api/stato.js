// GET ?id=...: stato della ricerca (file salvato dal runner + stato del workflow GitHub)
const { send, protezione, leggiJSON, trovaRun } = require("./_lib");

module.exports = async (req, res) => {
  if (!protezione(req, res)) return;
  const id = String((req.query && req.query.id) || new URL(req.url, "http://x").searchParams.get("id") || "");
  if (!/^[\w-]+$/.test(id)) return send(res, 400, { errore: "id non valido" });
  const [stato, github] = await Promise.all([leggiJSON(`runs/${id}/stato.json`), trovaRun(id)]);
  if (!stato && !github) return send(res, 404, { errore: "Ricerca non trovata" });
  return send(res, 200, { stato, github });
};
