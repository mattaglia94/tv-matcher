// POST {id}: annulla una ricerca in corso
const { REPO, send, protezione, gh, trovaRun, leggiCorpo } = require("./_lib");

module.exports = async (req, res) => {
  if (!protezione(req, res)) return;
  const { id } = await leggiCorpo(req);
  const run = await trovaRun(String(id || ""));
  if (!run) return send(res, 404, { errore: "Ricerca non trovata" });
  const r = await gh(`/repos/${REPO}/actions/runs/${run.github_id}/cancel`, { metodo: "POST" });
  if (r.status !== 202) return send(res, 502, { errore: `Annullamento non riuscito (${r.status})` });
  return send(res, 200, { ok: true });
};
