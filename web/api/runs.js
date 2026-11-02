// GET: storico delle ricerche lanciate dal sito (escluse quelle eliminate)
const { send, protezione, elencoRun, leggiJSON } = require("./_lib");

module.exports = async (req, res) => {
  if (!protezione(req, res)) return;
  const [runs, nascoste, nomi] = await Promise.all([elencoRun(100), leggiJSON("config/nascoste.json"), leggiJSON("config/nomi.json")]);
  const via = new Set((nascoste && nascoste.ids) || []);
  const n = nomi || {};
  return send(res, 200, { runs: runs.filter((r) => !via.has(r.id)).slice(0, 60).map((r) => (n[r.id] ? { ...r, nome: n[r.id] } : r)) });
};
