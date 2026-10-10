// GET ?id=...: stato della ricerca (file salvato dal runner + stato del workflow GitHub).
// Le ricerche grandi girano divise in parti (runs/<id>/parte_<k>.json): qui si riuniscono in un unico stato.
const { REPO, send, protezione, gh, leggiJSON, trovaRun } = require("./_lib");

function unisci(parti) {
  parti = parti.filter(Boolean).sort((a, b) => (a.parte || 0) - (b.parte || 0));
  if (!parti.length) return null;
  const base = parti[0];
  const stati = parti.map((p) => p.stato);
  const fatti = parti.reduce((t, p) => t + ((p.avanzamento && p.avanzamento.fatti) || 0), 0);
  const totale = parti.reduce((t, p) => t + ((p.avanzamento && p.avanzamento.totale) || 0), 0);
  const attesi = base.parti || parti.length;
  const inCorso = stati.includes("in_corso") || parti.length < attesi;
  const risultati = parti.flatMap((p) => p.risultati || []).sort((a, b) => (a._i ?? 0) - (b._i ?? 0));
  const log = parti.flatMap((p, k) => (p.log || []).map((r) => (parti.length > 1 ? r.replace(/^(\S+) /, `$1 [${k + 1}] `) : r)))
    .sort().slice(-120);
  const correnti = parti.filter((p) => p.stato === "in_corso").map((p) => p.avanzamento && p.avanzamento.corrente).filter(Boolean);
  return {
    ...base,
    stato: inCorso ? "in_corso" : stati.includes("errore") ? "errore" : "completato",
    errore: parti.map((p) => p.errore).filter(Boolean).join(" · ") || undefined,
    iniziato: parti.map((p) => p.iniziato).filter(Boolean).sort()[0],
    finito: inCorso ? null : parti.map((p) => p.finito).filter(Boolean).sort().pop(),
    avanzamento: {
      fatti, totale: Math.max(totale, fatti, 1),
      corrente: inCorso ? (parti.length > 1 ? `${attesi} parti in parallelo · ` : "") + (correnti[0] || "Avvio") : "Completato",
    },
    log, risultati,
  };
}

module.exports = async (req, res) => {
  if (!protezione(req, res)) return;
  const id = String((req.query && req.query.id) || new URL(req.url, "http://x").searchParams.get("id") || "");
  if (!/^[\w-]+$/.test(id)) return send(res, 400, { errore: "id non valido" });
  const [cartella, github] = await Promise.all([gh(`/repos/${REPO}/contents/runs/${id}?ref=dati`), trovaRun(id)]);
  const file = cartella.status === 200 && Array.isArray(cartella.dati) ? cartella.dati.map((f) => f.name) : [];
  let stato = null;
  const parti = file.filter((n) => /^parte_\d+\.json$/.test(n));
  if (parti.length) stato = unisci(await Promise.all(parti.map((n) => leggiJSON(`runs/${id}/${n}`))));
  else if (file.includes("stato.json")) stato = await leggiJSON(`runs/${id}/stato.json`);
  if (!stato && !github) return send(res, 404, { errore: "Ricerca non trovata" });
  return send(res, 200, { stato, github });
};
