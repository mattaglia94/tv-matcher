// GET /api/diagnosi: controlla passo per passo cosa vede il sito su GitHub (non mostra mai il token).
const { REPO, WORKFLOW, send, autenticato, gh } = require("./_lib");

module.exports = async (req, res) => {
  if (!autenticato(req)) return send(res, 401, { errore: "Entra prima nel sito con la password, poi riapri questa pagina" });
  const t = process.env.GITHUB_TOKEN || "";
  const esito = {
    "1_token_presente": t ? `sì (${t.length} caratteri, inizia con "${t.slice(0, 11)}…")` : "NO: manca GITHUB_TOKEN su Vercel",
    "1b_spazi_nel_token": /\s/.test(t) ? "SÌ: il token contiene spazi o a capo, va reincollato" : "no",
    "2_repo_usato": JSON.stringify(REPO),
    "2b_spazi_nel_repo": /\s/.test(REPO) ? "SÌ: GITHUB_REPO contiene spazi o a capo" : "no",
  };
  if (!t) return send(res, 200, esito);
  const u = await gh("/user");
  esito["3_token_valido"] = u.status === 200 ? `sì, utente ${u.dati.login}` : `NO (${u.status}): ${u.dati && u.dati.message}`;
  const r = await gh(`/repos/${REPO}`);
  esito["4_repo_visibile"] = r.status === 200 ? `sì (privato: ${r.dati.private}, branch principale: ${r.dati.default_branch})` : `NO (${r.status}): il token non vede ${REPO}`;
  const w = await gh(`/repos/${REPO}/actions/workflows`);
  esito["5_workflow_trovati"] = w.status === 200 ? (w.dati.workflows || []).map((x) => `${x.name} → ${x.path} (${x.state})`) : `NO (${w.status}): ${w.dati && w.dati.message}`;
  const s = await gh(`/repos/${REPO}/actions/workflows/${WORKFLOW}`);
  esito["6_workflow_sito"] = s.status === 200 ? `sì: ${s.dati.path}, stato ${s.dati.state}` : `NO (${s.status}): GitHub non trova .github/workflows/${WORKFLOW}`;
  return send(res, 200, esito);
};
