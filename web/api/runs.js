// GET: storico delle ricerche lanciate dal sito (escluse quelle eliminate)
const { send, protezione, elencoRun, leggiJSON } = require("./_lib");

module.exports = async (req, res) => {
  if (!protezione(req, res)) return;
  const [runs, nascoste] = await Promise.all([elencoRun(100), leggiJSON("config/nascoste.json")]);
  const via = new Set((nascoste && nascoste.ids) || []);
  return send(res, 200, { runs: runs.filter((r) => !via.has(r.id)).slice(0, 60) });
};
