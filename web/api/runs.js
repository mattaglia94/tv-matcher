// GET: storico delle ricerche lanciate dal sito
const { send, protezione, elencoRun } = require("./_lib");

module.exports = async (req, res) => {
  if (!protezione(req, res)) return;
  return send(res, 200, { runs: await elencoRun(50) });
};
