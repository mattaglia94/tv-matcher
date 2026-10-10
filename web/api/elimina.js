// POST {ids: [...]}: elimina ricerche dallo storico.
// Le nasconde sempre (config/nascoste.json) e prova anche a cancellare il workflow su GitHub e il file dei risultati.
const { REPO, send, protezione, gh, leggiJSON, scriviJSON, elencoRun, leggiCorpo } = require("./_lib");

module.exports = async (req, res) => {
  if (!protezione(req, res)) return;
  if (req.method !== "POST") return send(res, 405, { errore: "Usa POST" });
  const { ids } = await leggiCorpo(req);
  const voluti = new Set((Array.isArray(ids) ? ids : []).map(String).filter((x) => /^[\w-]+$/.test(x)));
  if (!voluti.size) return send(res, 400, { errore: "Nessuna ricerca indicata" });
  const runs = (await elencoRun(100)).filter((r) => voluti.has(r.id));
  const attive = runs.filter((r) => r.status !== "completed");
  if (attive.length) return send(res, 409, { errore: "Una ricerca in corso non si può eliminare: annullala prima" });
  const nascoste = (await leggiJSON("config/nascoste.json")) || { ids: [] };
  const tutte = [...new Set([...(nascoste.ids || []), ...voluti])].slice(-2000);
  const w = await scriviJSON("config/nascoste.json", { ids: tutte }, "storico: nascondi ricerche");
  if (w.status !== 200 && w.status !== 201) return send(res, 502, { errore: `Eliminazione non riuscita (${w.status})` });
  // pulizia "vera", se il token lo permette (non blocca l'esito)
  await Promise.all(runs.map(async (r) => {
    try {
      await gh(`/repos/${REPO}/actions/runs/${r.github_id}`, { metodo: "DELETE" });
      const dir = await gh(`/repos/${REPO}/contents/runs/${r.id}?ref=dati`);  // stato.json o parte_<k>.json
      for (const f of (dir.status === 200 && Array.isArray(dir.dati) ? dir.dati : [])) {
        await gh(`/repos/${REPO}/contents/${f.path}`, { metodo: "DELETE", corpo: { message: `elimina ricerca ${r.id}`, sha: f.sha, branch: "dati" } });
      }
    } catch { /* resta comunque nascosta */ }
  }));
  return send(res, 200, { ok: true, eliminate: voluti.size });
};
