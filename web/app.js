/* TV Matcher — logica del sito (JavaScript puro, nessun framework). */
(() => {
  "use strict";
  const T = window.TVM;
  const app = document.getElementById("app");

  // ------------------------------------------------------------------ utilità
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const clona = (o) => JSON.parse(JSON.stringify(o));
  const paese = (c) => T.paesi.find((p) => p.codice === c) || { codice: c, nome: c, bandiera: "🏳️" };
  const memoria = {
    leggi(k, def) { try { const v = localStorage.getItem("tvm_" + k); return v ? JSON.parse(v) : def; } catch { return def; } },
    scrivi(k, v) { try { localStorage.setItem("tvm_" + k, JSON.stringify(v)); } catch { /* memoria non disponibile */ } },
  };
  function toast(testo, tipo = "") {
    const el = document.createElement("div");
    el.className = "toast " + tipo;
    el.textContent = testo;
    document.getElementById("toast").appendChild(el);
    setTimeout(() => el.remove(), 4200);
  }
  function rimbalzo(fn, ms) { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; }
  function dataBreve(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    return d.toLocaleDateString("it-IT", { day: "numeric", month: "short", year: "numeric" }) + ", " + d.toLocaleTimeString("it-IT", { hour: "2-digit", minute: "2-digit" });
  }
  function durata(da, a) {
    if (!da) return "";
    const s = Math.max(0, Math.round(((a ? new Date(a) : new Date()) - new Date(da)) / 1000));
    const m = Math.floor(s / 60);
    return m ? `${m} min ${s % 60} s` : `${s} s`;
  }
  const ICONE = {
    carica: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 16V4M7 9l5-5 5 5"/><path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3"/></svg>',
    scarica: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 4v12M7 11l5 5 5-5"/><path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3"/></svg>',
    play: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5.5v13a1 1 0 0 0 1.5.86l10.5-6.5a1 1 0 0 0 0-1.72L9.5 4.64A1 1 0 0 0 8 5.5z"/></svg>',
    tv: '<svg viewBox="0 0 64 48" fill="none"><rect x="2" y="2" width="60" height="38" rx="7" stroke="#A9A3D6" stroke-width="3"/><path d="M22 46h20" stroke="#A9A3D6" stroke-width="3" stroke-linecap="round"/><g opacity=".8"><rect x="10" y="10" width="8.8" height="22" fill="#FFD23F"/><rect x="18.8" y="10" width="8.8" height="22" fill="#2EE6F0"/><rect x="27.6" y="10" width="8.8" height="22" fill="#4BE38E"/><rect x="36.4" y="10" width="8.8" height="22" fill="#FF4FA3"/><rect x="45.2" y="10" width="8.8" height="22" fill="#7B61FF"/></g></svg>',
  };
  const ESITI = { saltato: "Saltato", trovato: "Trovato", non_presente: "Prodotto non presente", nessun_simile: "Nessun modello simile", errore: "Ricerca non riuscita", illeggibile: "Risultati non leggibili" };
  const ESITI_NOTA = {
    non_presente: "Nessun TV di questa marca e diagonale nel catalogo del retailer.",
    nessun_simile: "Ci sono TV della stessa marca e diagonale, ma nessuno rispetta i criteri.",
    errore: "Il sito non ha risposto o ha bloccato la ricerca: riprova più tardi.",
    illeggibile: "La pagina si è aperta ma non mostrava TV leggibili (probabile blocco): verifica a mano.",
  };
  const barre = '<div class="barre" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i></div>';

  // ------------------------------------------------------------------ API
  async function api(percorso, { metodo = "GET", corpo } = {}) {
    const r = await fetch("/api/" + percorso, {
      method: metodo, credentials: "same-origin",
      headers: corpo ? { "Content-Type": "application/json" } : {},
      body: corpo ? JSON.stringify(corpo) : undefined,
    });
    let dati = {};
    try { dati = await r.json(); } catch { /* risposta vuota */ }
    if (r.status === 401 && percorso !== "login") { location.hash = "#/login"; throw new Error("Accesso richiesto"); }
    if (!r.ok) throw new Error(dati.errore || `Errore ${r.status}`);
    return dati;
  }

  // ------------------------------------------------------------------ stato
  const S = {
    impostazioni: { retailer: clona(T.retailer), preset: [] },
    anagrafica: {},
    bozza: memoria.leggi("bozza", null) || { asin: [], nome: "", paeseDefault: "IT", parametri: clona(T.parametriDefault), preset: "" },
    passo: 1,
    polling: null,
    vistaRisultati: memoria.leggi("vista", "schede"),
  };
  S.bozza.parametri = Object.assign(clona(T.parametriDefault), S.bozza.parametri || {});
  const salvaBozza = () => memoria.scrivi("bozza", S.bozza);
  const salvaImpostazioni = rimbalzo(async () => {
    try { await api("impostazioni", { metodo: "PUT", corpo: S.impostazioni }); toast("Impostazioni salvate", "ok"); }
    catch (e) { toast("Impostazioni non salvate: " + e.message, "errore"); }
  }, 1200);

  async function caricaImpostazioni() {
    try {
      const { impostazioni, anagrafica } = await api("impostazioni");
      S.anagrafica = anagrafica || {};
      if (impostazioni && Array.isArray(impostazioni.retailer) && impostazioni.retailer.length) {
        S.impostazioni = { retailer: impostazioni.retailer, preset: impostazioni.preset || [] };
      }
    } catch { /* restano i predefiniti */ }
  }

  // ------------------------------------------------------------------ router
  async function router() {
    clearInterval(S.polling);
    S.polling = null;
    const [, vista, arg] = (location.hash || "#/nuova").split("/");
    document.querySelectorAll("[data-nav]").forEach((a) => a.classList.toggle("attivo", a.dataset.nav === vista || (vista === "run" && a.dataset.nav === "esecuzioni")));
    document.getElementById("topbar").hidden = vista === "login";
    if (vista === "login") return vistaLogin();
    aggiornaPill();
    if (vista === "run" && arg) return vistaRun(arg);
    if (vista === "esecuzioni") return vistaStorico();
    if (vista === "guida") return vistaGuida();
    if (arg) S.passo = Math.min(4, Math.max(1, Number(arg) || 1));
    vistaNuova();
  }
  window.addEventListener("hashchange", router);

  // pill "ricerca in corso" in alto: riprende la sessione da qualunque pagina
  let ultimoControllo = 0;
  async function aggiornaPill(forza) {
    if (!forza && Date.now() - ultimoControllo < 25000) return;
    ultimoControllo = Date.now();
    try {
      const { runs } = await api("runs");
      const attive = runs.filter((r) => r.status !== "completed");
      clearTimeout(S.timerPill);
      if (attive.length) S.timerPill = setTimeout(() => aggiornaPill(true), 20000);
      const pill = document.getElementById("pillAttiva");
      pill.hidden = !attive.length;
      if (attive.length) {
        document.getElementById("pillTesto").textContent = attive.length === 1 ? `In corso: ${attive[0].nome || "ricerca"}` : `${attive.length} ricerche in corso`;
        pill.href = attive.length === 1 ? `#/run/${attive[0].id}` : "#/esecuzioni";
      }
    } catch { /* silenzioso */ }
  }

  // ------------------------------------------------------------------ login
  function vistaLogin() {
    app.innerHTML = `
      <section class="login vista">
        <div class="login-box">
          <img src="logo.svg" alt="" width="84" height="84">
          <div><h1>TV Matcher</h1><p class="tenue" style="margin-top:10px">Trova i modelli simili ai TV Amazon sui retailer europei.</p></div>
          ${barre}
          <form id="fLogin">
            <label class="campo">Password<input type="password" id="pwd" autocomplete="current-password" required autofocus></label>
            <button class="btn primario grande" type="submit">Entra</button>
            <p class="errore-testo" id="errLogin"></p>
          </form>
        </div>
      </section>`;
    document.getElementById("fLogin").onsubmit = async (e) => {
      e.preventDefault();
      const btn = e.target.querySelector("button");
      btn.disabled = true;
      try {
        await api("login", { metodo: "POST", corpo: { password: document.getElementById("pwd").value } });
        await caricaImpostazioni();
        location.hash = "#/nuova";
        if (!memoria.leggi("tutorial", false)) setTimeout(tutorial, 300);
      } catch (err) {
        document.getElementById("errLogin").textContent = err.message;
        btn.disabled = false;
      }
    };
  }

  // ------------------------------------------------------------------ nuova ricerca
  const PASSI = [
    { titolo: "ASIN", sotto: "Incolla o carica la lista" },
    { titolo: "Marketplace", sotto: "Dove cercare" },
    { titolo: "Somiglianza", sotto: "Quando due TV sono simili" },
    { titolo: "Avvio", sotto: "Riepilogo e run" },
  ];

  function vistaNuova() {
    const p = S.passo;
    app.innerHTML = `
      <div class="vista">
        <div class="intestazione">
          <div>
            <h1>Nuova ricerca</h1>
            <p class="tenue">Parti da una lista di ASIN Amazon: il motore trova, per ogni retailer, il TV più simile con un codice modello diverso.</p>
          </div>
        </div>
        <div class="wizard">
          <ol class="passi">
            ${PASSI.map((x, i) => `
              <li class="${i + 1 === p ? "corrente" : i + 1 < p ? "fatto" : ""}">
                <button type="button" data-passo="${i + 1}" ${i + 1 === p ? 'aria-current="step"' : ""}>
                  <span class="num">${i + 1 < p ? "✓" : i + 1}</span>
                  <span class="titolo-passo">${x.titolo}<span class="sotto">${x.sotto}</span></span>
                </button>
              </li>`).join("")}
          </ol>
          <div id="contenutoPasso"></div>
        </div>
      </div>`;
    app.querySelectorAll("[data-passo]").forEach((b) => (b.onclick = () => { location.hash = `#/nuova/${b.dataset.passo}`; }));
    const box = document.getElementById("contenutoPasso");
    ({ 1: passoAsin, 2: passoMarketplace, 3: passoParametri, 4: passoAvvio })[p](box);
  }

  function piedePasso(box, { avanti = true, testoAvanti = "Avanti", bloccato = false } = {}) {
    const d = document.createElement("div");
    d.className = "azioni-passo";
    d.innerHTML = `
      ${S.passo > 1 ? '<button class="btn" type="button" data-dir="-1">Indietro</button>' : "<span></span>"}
      ${avanti ? `<button class="btn primario" type="button" data-dir="1" ${bloccato ? "disabled" : ""}>${testoAvanti}</button>` : ""}`;
    d.querySelectorAll("[data-dir]").forEach((b) => (b.onclick = () => { location.hash = `#/nuova/${S.passo + Number(b.dataset.dir)}`; }));
    box.appendChild(d);
  }

  // ---------------- passo 1: ASIN
  function estraiAsin(testo, paeseDef) {
    const trovati = [];
    for (const riga of String(testo).split(/\r?\n/)) {
      const asins = riga.toUpperCase().match(/\bB0[A-Z0-9]{8}\b/g);
      if (!asins) continue;
      const pm = riga.toUpperCase().match(/(?:^|[^A-Z])(IT|DE|FR|ES|UK|GB)(?:[^A-Z]|$)/);
      const pa = pm ? (pm[1] === "GB" ? "UK" : pm[1]) : paeseDef;
      asins.forEach((a) => trovati.push({ asin: a, paese: pa, modello: "" }));
    }
    return trovati;
  }
  function aggiungiAsin(lista) {
    const presenti = new Set(S.bozza.asin.map((a) => a.asin + a.paese));
    let nuovi = 0;
    lista.forEach((a) => {
      if (presenti.has(a.asin + a.paese)) return;
      const noto = S.anagrafica[`${a.asin}|${a.paese}`];
      if (!a.modello && noto && noto.modello) a.modello = noto.modello;
      S.bozza.asin.push(a); presenti.add(a.asin + a.paese); nuovi++;
    });
    salvaBozza();
    toast(nuovi ? `${nuovi} ASIN aggiunti` : "Nessun ASIN nuovo trovato", nuovi ? "ok" : "");
  }

  function passoAsin(box) {
    const b = S.bozza;
    box.innerHTML = `
      <section class="scheda">
        <div class="scheda-testa">
          <div><h2>Quali TV vuoi confrontare?</h2>
          <p class="tenue">Incolla gli ASIN in qualsiasi formato: uno per riga, separati da virgole o copiati da Excel. Se sulla riga c'è anche il paese (IT, DE, FR, ES, UK) viene letto in automatico.
          Se conosci il modello scrivilo nella colonna Modello: il motore salta Amazon, che a volte blocca le ricerche automatiche. I modelli trovati vengono ricordati per le ricerche successive.</p></div>
        </div>
        <div class="griglia-2">
          <div>
            <textarea id="taAsin" placeholder="B0F457MQCQ&#10;B0F4548TCQ;IT&#10;B0F457M449  DE" aria-label="Lista ASIN"></textarea>
            <div class="riga-strumenti">
              <label class="campo" style="grid-auto-flow:column;align-items:center;gap:8px">Paese predefinito
                <select id="selPaese" style="width:auto">${T.paesi.map((p) => `<option value="${p.codice}" ${p.codice === b.paeseDefault ? "selected" : ""}>${p.bandiera} ${p.nome}</option>`).join("")}</select>
              </label>
              <button class="btn primario" type="button" id="btnAggiungi">Aggiungi ASIN</button>
            </div>
            <label class="dropzona" id="drop" style="margin-top:16px">
              ${ICONE.carica}
              <span><strong>Carica un file</strong><br><span class="piccolo">CSV, TXT o Excel: leggo tutti gli ASIN che contiene</span></span>
              <input type="file" id="fileAsin" accept=".csv,.txt,.xlsx,.xls" hidden>
            </label>
          </div>
          <div>
            <div style="display:flex;justify-content:space-between;align-items:flex-end;gap:10px">
              <div><div class="contatore">${b.asin.length}</div><span class="tenue piccolo">ASIN nella ricerca</span></div>
              ${b.asin.length ? '<button class="btn fantasma piccolo" type="button" id="btnSvuota">Svuota lista</button>' : ""}
            </div>
            ${b.asin.length ? `
              <div class="lista-scroll" style="margin-top:12px">
                <table class="tabella-asin">
                  <thead><tr><th>ASIN</th><th>Paese</th><th title="Facoltativo: se lo scrivi, il motore non apre Amazon">Modello (facolt.)</th><th></th></tr></thead>
                  <tbody>${b.asin.map((a, i) => `
                    <tr>
                      <td>${esc(a.asin)}</td>
                      <td><select data-i="${i}" data-campo="paese">${T.paesi.map((p) => `<option value="${p.codice}" ${p.codice === a.paese ? "selected" : ""}>${p.bandiera} ${p.codice}</option>`).join("")}</select></td>
                      <td><input type="text" data-i="${i}" data-campo="modello" value="${esc(a.modello)}" placeholder="${b.mancanti && b.mancanti.includes(a.asin) ? "scrivi il modello" : "es. 55E7Q"}" style="padding:5px 8px${b.mancanti && b.mancanti.includes(a.asin) && !a.modello ? ";border-color:var(--giallo)" : ""}"
                        title="${S.anagrafica[`${a.asin}|${a.paese}`] ? "Modello già noto da una ricerca precedente" : ""}"></td>
                      <td><button class="btn fantasma piccolo" type="button" data-rimuovi="${i}" aria-label="Rimuovi ${esc(a.asin)}">✕</button></td>
                    </tr>`).join("")}</tbody>
                </table>
              </div>` : `<div class="vuoto" style="padding:34px 10px"><div style="width:120px">${ICONE.tv}</div><p class="tenue">La lista è vuota. Incolla gli ASIN a sinistra o carica un file.</p></div>`}
          </div>
        </div>
      </section>`;
    const ta = document.getElementById("taAsin");
    document.getElementById("selPaese").onchange = (e) => { b.paeseDefault = e.target.value; salvaBozza(); };
    document.getElementById("btnAggiungi").onclick = () => {
      const l = estraiAsin(ta.value, b.paeseDefault);
      if (!l.length) return toast("Non ho trovato ASIN validi (formato B0 + 8 caratteri)", "errore");
      aggiungiAsin(l); vistaNuova();
    };
    const s = document.getElementById("btnSvuota");
    if (s) s.onclick = () => { if (confirm("Svuotare la lista degli ASIN?")) { b.asin = []; salvaBozza(); vistaNuova(); } };
    box.querySelectorAll("[data-rimuovi]").forEach((x) => (x.onclick = () => { b.asin.splice(Number(x.dataset.rimuovi), 1); salvaBozza(); vistaNuova(); }));
    box.querySelectorAll("[data-campo]").forEach((x) => (x.onchange = () => { b.asin[Number(x.dataset.i)][x.dataset.campo] = x.value.trim().toUpperCase(); salvaBozza(); }));
    const drop = document.getElementById("drop"), file = document.getElementById("fileAsin");
    const leggiFile = async (f) => {
      if (!f) return;
      let testo = "";
      if (/\.xlsx?$/i.test(f.name)) {
        if (!window.XLSX) return toast("Lettore Excel non ancora caricato, riprova tra un secondo", "errore");
        const wb = XLSX.read(await f.arrayBuffer());
        testo = wb.SheetNames.map((n) => XLSX.utils.sheet_to_csv(wb.Sheets[n], { FS: ";" })).join("\n");
      } else testo = await f.text();
      const l = estraiAsin(testo, b.paeseDefault);
      if (!l.length) return toast(`Nessun ASIN trovato in ${f.name}`, "errore");
      aggiungiAsin(l); vistaNuova();
    };
    file.onchange = () => leggiFile(file.files[0]);
    drop.ondragover = (e) => { e.preventDefault(); drop.classList.add("sopra"); };
    drop.ondragleave = () => drop.classList.remove("sopra");
    drop.ondrop = (e) => { e.preventDefault(); drop.classList.remove("sopra"); leggiFile(e.dataTransfer.files[0]); };
    piedePasso(box, { bloccato: !b.asin.length });
  }

  // ---------------- passo 2: marketplace
  function paesiAsin() { return [...new Set(S.bozza.asin.map((a) => a.paese))]; }

  function passoMarketplace(box) {
    const R = S.impostazioni.retailer;
    const usati = paesiAsin();
    const ordine = [...usati, ...T.paesi.map((p) => p.codice).filter((c) => !usati.includes(c))];
    const altri = [...new Set(R.map((r) => r.paese))].filter((c) => !ordine.includes(c));
    box.innerHTML = `
      <section class="scheda">
        <div class="scheda-testa">
          <div><h2>Su quali marketplace cercare?</h2>
          <p class="tenue">Ogni ASIN viene cercato sui marketplace attivi del suo paese. Le modifiche valgono per tutti e restano salvate.</p></div>
          <div class="riga-strumenti" style="margin:0">
            <button class="btn piccolo" type="button" id="tuttiOn">Seleziona tutti</button>
            <button class="btn piccolo" type="button" id="tuttiOff">Deseleziona tutti</button>
            <button class="btn fantasma piccolo" type="button" id="ripristina">Ripristina predefiniti</button>
          </div>
        </div>
        <div id="blocchiPaese">
          ${[...ordine, ...altri].map((c) => {
            const lista = R.map((r, i) => ({ ...r, i })).filter((r) => r.paese === c);
            const att = lista.filter((r) => r.attivo).length;
            const p = paese(c);
            return `
              <details class="paese-blocco" ${usati.includes(c) || S.apertiPaese?.has(c) ? "open" : ""} data-blocco="${c}">
                <summary class="paese-testa">
                  <label class="check"><input type="checkbox" data-paese-tutti="${c}" ${lista.length && att === lista.length ? "checked" : ""} aria-label="Tutti i marketplace ${p.nome}"></label>
                  <span class="bandiera" aria-hidden="true">${p.bandiera}</span>
                  <h3>${esc(p.nome)}</h3>
                  ${usati.includes(c) ? `<span class="chip info">${S.bozza.asin.filter((a) => a.paese === c).length} ASIN</span>` : '<span class="chip">nessun ASIN</span>'}
                  <span class="chip ${att ? "ok" : ""}" style="margin-left:0">${att}/${lista.length} attivi</span>
                  <span class="freccia" aria-hidden="true"></span>
                </summary>
                ${lista.map((r) => rigaRetailer(r)).join("")}
                <div class="retailer-riga" style="grid-template-columns:1fr">
                  <button class="btn fantasma piccolo" type="button" data-aggiungi="${c}" style="justify-self:start">+ Aggiungi marketplace in ${esc(p.nome)}</button>
                </div>
              </details>`;
          }).join("")}
        </div>
        <details style="margin-top:16px"><summary>Come scrivere l'URL di ricerca</summary>
          <p class="tenue piccolo">Apri il sito del retailer, cerca ad esempio <em>hisense 55</em> e copia l'indirizzo della pagina dei risultati. Poi sostituisci il testo cercato con <code>{q}</code>.
          Esempio: <code>https://www.mediaworld.it/it/search.html?query={q}</code></p>
        </details>
      </section>`;
    S.apertiPaese = S.apertiPaese || new Set();
    box.querySelectorAll("[data-blocco]").forEach((d) => d.addEventListener("toggle", () => { if (d.open) S.apertiPaese.add(d.dataset.blocco); else S.apertiPaese.delete(d.dataset.blocco); }));
    box.querySelectorAll("[data-paese-tutti]").forEach((x) => x.addEventListener("click", (e) => e.stopPropagation()));
    const ridisegna = () => { salvaImpostazioni(); passoMarketplace(box); };
    box.querySelectorAll("[data-attiva]").forEach((x) => (x.onchange = () => { R[Number(x.dataset.attiva)].attivo = x.checked; ridisegna(); }));
    box.querySelectorAll("[data-paese-tutti]").forEach((x) => (x.onchange = () => { R.forEach((r) => { if (r.paese === x.dataset.paeseTutti) r.attivo = x.checked; }); ridisegna(); }));
    box.querySelectorAll("[data-modifica]").forEach((x) => (x.onclick = () => { R[Number(x.dataset.modifica)]._mod = true; passoMarketplace(box); }));
    box.querySelectorAll("[data-elimina]").forEach((x) => (x.onclick = () => {
      const r = R[Number(x.dataset.elimina)];
      if (confirm(`Eliminare ${r.nome}?`)) { R.splice(Number(x.dataset.elimina), 1); ridisegna(); }
    }));
    box.querySelectorAll("[data-salva]").forEach((x) => (x.onclick = () => {
      const i = Number(x.dataset.salva), riga = x.closest(".retailer-riga");
      const nome = riga.querySelector("[data-n]").value.trim(), url = riga.querySelector("[data-u]").value.trim();
      if (!nome || !/^https?:\/\/.+\{q\}/.test(url)) return toast("Serve un nome e un URL che inizi con http e contenga {q}", "errore");
      Object.assign(R[i], { nome, url }); delete R[i]._mod; ridisegna();
    }));
    box.querySelectorAll("[data-annulla]").forEach((x) => (x.onclick = () => {
      const i = Number(x.dataset.annulla);
      if (!R[i].nome) R.splice(i, 1); else delete R[i]._mod;
      passoMarketplace(box);
    }));
    box.querySelectorAll("[data-aggiungi]").forEach((x) => (x.onclick = () => { R.push({ paese: x.dataset.aggiungi, nome: "", url: "", attivo: true, _mod: true }); passoMarketplace(box); }));
    document.getElementById("tuttiOn").onclick = () => { R.forEach((r) => (r.attivo = true)); ridisegna(); };
    document.getElementById("tuttiOff").onclick = () => { R.forEach((r) => (r.attivo = false)); ridisegna(); };
    document.getElementById("ripristina").onclick = () => {
      if (confirm("Ripristinare l'elenco originale dei marketplace? Le modifiche fatte andranno perse.")) { S.impostazioni.retailer = clona(T.retailer); salvaImpostazioni(); passoMarketplace(box); }
    };
    const scoperti = usati.filter((c) => !R.some((r) => r.paese === c && r.attivo));
    if (scoperti.length) {
      const avv = document.createElement("p");
      avv.className = "chip attenzione";
      avv.style.cssText = "margin-top:16px;white-space:normal;padding:8px 14px";
      avv.textContent = `Nessun marketplace attivo per: ${scoperti.map((c) => paese(c).nome).join(", ")}. Gli ASIN di questi paesi non verranno confrontati.`;
      box.querySelector(".scheda").appendChild(avv);
    }
    piedePasso(box, { bloccato: !usati.some((c) => R.some((r) => r.paese === c && r.attivo)) });
  }

  function rigaRetailer(r) {
    if (r._mod) {
      return `
        <div class="retailer-riga modifica">
          <span></span>
          <input type="text" data-n value="${esc(r.nome)}" placeholder="Nome" aria-label="Nome marketplace">
          <input type="url" data-u value="${esc(r.url)}" placeholder="https://…{q}" aria-label="URL di ricerca">
          <span style="display:flex;gap:6px"><button class="btn primario piccolo" type="button" data-salva="${r.i}">Salva</button><button class="btn fantasma piccolo" type="button" data-annulla="${r.i}">Annulla</button></span>
        </div>`;
    }
    return `
      <div class="retailer-riga ${r.attivo ? "" : "spento"}">
        <label class="check"><input type="checkbox" data-attiva="${r.i}" ${r.attivo ? "checked" : ""} aria-label="Attiva ${esc(r.nome)}"></label>
        <span class="nome" style="font-weight:600">${esc(r.nome)}</span>
        <span class="url" title="${esc(r.url)}">${esc(r.url)}</span>
        <span style="display:flex;gap:4px">
          <button class="btn fantasma piccolo" type="button" data-modifica="${r.i}">Modifica</button>
          <button class="btn fantasma piccolo pericolo" type="button" data-elimina="${r.i}" aria-label="Elimina ${esc(r.nome)}">✕</button>
        </span>
      </div>`;
  }

  // ---------------- passo 3: parametri
  function passoParametri(box) {
    const P = S.bozza.parametri;
    const preset = S.impostazioni.preset || [];
    const sw = (k, on) => `<label class="switch"><input type="checkbox" data-on="${k}" ${on ? "checked" : ""} aria-label="Attiva ${k}"><span></span></label>`;
    const controllo = (v) => {
      const p = P[v.chiave];
      if (v.controllo === "tolleranza") return `<div class="controlli"><label class="campo" style="grid-auto-flow:column;align-items:center">Tolleranza ±<input type="number" min="0" max="20" step="1" data-num="pollici.tolleranza" value="${p.tolleranza}"> pollici</label><span class="tenue piccolo">0 = stessa diagonale</span></div>`;
      if (v.controllo === "anno") return `<div class="controlli"><label class="campo" style="grid-auto-flow:column;align-items:center">Anno<input type="number" min="2020" max="2035" data-num="anno.valore" value="${p.valore}"></label>
        <label class="check"><input type="checkbox" data-bool="anno.accetta_ignoto" ${p.accetta_ignoto ? "checked" : ""}> Accetta i modelli con anno non ricavabile (segnalati "da verificare")</label></div>`;
      if (v.controllo === "equivalenze") return `<div class="controlli"><span class="tenue piccolo">Considera equivalenti:</span>
        ${(p.equivalenze || []).map((g, gi) => `<span class="chip info">${g.map((t) => T.nomeTecnologia[t] || t).join(" = ")} <button type="button" class="btn fantasma piccolo" data-togli-eq="${gi}" aria-label="Rimuovi equivalenza" style="padding:0 4px">✕</button></span>`).join("") || '<span class="chip">nessuna</span>'}
        <span class="equiv"><select id="eqA" style="width:auto">${T.tecnologie.map((t) => `<option value="${t}">${T.nomeTecnologia[t]}</option>`).join("")}</select> = <select id="eqB" style="width:auto">${T.tecnologie.map((t, i) => `<option value="${t}" ${i === 2 ? "selected" : ""}>${T.nomeTecnologia[t]}</option>`).join("")}</select>
        <button class="btn piccolo" type="button" id="eqAgg">Aggiungi</button></span></div>`;
      if (v.controllo === "regole") return `<details style="margin-top:10px"><summary>Vedi le regole di famiglia per marca</summary>
        ${Object.entries(T.regole).map(([m, rr]) => `<h4 style="margin-top:10px">${m}</h4><table class="regole-tab">${rr.map(([c, f]) => `<tr><td>${esc(c)}</td><td>${esc(f)}</td></tr>`).join("")}</table>`).join("")}</details>`;
      return "";
    };
    box.innerHTML = `
      <section class="scheda">
        <div class="scheda-testa">
          <div><h2>Quando due TV sono simili?</h2>
          <p class="tenue">Accendi i criteri da rispettare. Il modello con lo stesso codice dell'ASIN è sempre escluso. Più criteri accendi, più i risultati sono precisi ma rari.</p></div>
        </div>
        <div class="preset-barra">
          <select id="selPreset" aria-label="Preset salvati">
            <option value="">Impostazioni personalizzate</option>
            <option value="__std">Standard (regole del documento)</option>
            ${preset.map((p, i) => `<option value="${i}" ${S.bozza.preset === String(i) ? "selected" : ""}>${esc(p.nome)}</option>`).join("")}
          </select>
          <button class="btn piccolo" type="button" id="salvaPreset">Salva come preset</button>
          ${S.bozza.preset !== "" && S.bozza.preset !== "__std" && preset[S.bozza.preset] ? '<button class="btn fantasma piccolo pericolo" type="button" id="eliminaPreset">Elimina preset</button>' : ""}
        </div>
      </section>
      ${T.parametriInfo.map((g) => `
        <section class="scheda gruppo-param">
          <h3>${g.gruppo}</h3>${g.nota ? `<p class="tenue piccolo">${g.nota}</p>` : ""}
          ${g.voci.map((v) => `
            <div class="param ${P[v.chiave].attivo ? "" : "spento"}">
              ${sw(v.chiave, P[v.chiave].attivo)}
              <div><h4>${v.titolo}</h4><p>${v.testo}</p>${P[v.chiave].attivo ? controllo(v) : ""}</div>
            </div>`).join("")}
        </section>`).join("")}
      <section class="scheda">
        <h3>Risultati</h3>
        <div class="opz-avanzate" style="margin-top:14px">
          <label class="campo">Modelli simili da mostrare per ogni marketplace
            <select data-num="max_match"><option value="1" ${P.max_match == 1 ? "selected" : ""}>1, il più vicino</option><option value="2" ${P.max_match == 2 ? "selected" : ""}>Fino a 2</option><option value="3" ${P.max_match == 3 ? "selected" : ""}>Fino a 3</option></select>
          </label>
          <div class="param" style="grid-template-columns:auto 1fr;padding:12px">
            <label class="switch"><input type="checkbox" data-bool="verifica_url" ${P.verifica_url ? "checked" : ""} aria-label="Verifica pagina prodotto"><span></span></label>
            <div><h4>Verifica la pagina prodotto</h4><p>Apre ogni link scelto: controlla che sia attivo e legge anno e caratteristiche. Più lento ma più affidabile.</p></div>
          </div>
        </div>
      </section>`;
    const cambia = () => { S.bozza.preset = ""; salvaBozza(); passoParametri(box); };
    const imposta = (path, val) => { const [a, b] = path.split("."); if (b) P[a][b] = val; else P[a] = val; };
    box.querySelectorAll("[data-on]").forEach((x) => (x.onchange = () => { P[x.dataset.on].attivo = x.checked; cambia(); }));
    box.querySelectorAll("[data-num]").forEach((x) => (x.onchange = () => { imposta(x.dataset.num, Number(x.value)); cambia(); }));
    box.querySelectorAll("[data-bool]").forEach((x) => (x.onchange = () => { imposta(x.dataset.bool, x.checked); cambia(); }));
    box.querySelectorAll("[data-togli-eq]").forEach((x) => (x.onclick = () => { P.tecnologia.equivalenze.splice(Number(x.dataset.togliEq), 1); cambia(); }));
    const eq = document.getElementById("eqAgg");
    if (eq) eq.onclick = () => {
      const a = document.getElementById("eqA").value, b2 = document.getElementById("eqB").value;
      if (a === b2) return toast("Scegli due tecnologie diverse", "errore");
      P.tecnologia.equivalenze = P.tecnologia.equivalenze || [];
      P.tecnologia.equivalenze.push([a, b2]); cambia();
    };
    document.getElementById("selPreset").onchange = (e) => {
      const v = e.target.value;
      if (v === "__std") S.bozza.parametri = clona(T.parametriDefault);
      else if (v !== "") S.bozza.parametri = Object.assign(clona(T.parametriDefault), clona(preset[Number(v)].parametri));
      S.bozza.preset = v === "__std" ? "" : v;
      salvaBozza(); passoParametri(box);
    };
    document.getElementById("salvaPreset").onclick = () => {
      const nome = prompt("Nome del preset (es. Largo, Solo stessa marca):");
      if (!nome) return;
      S.impostazioni.preset = preset;
      preset.push({ nome: nome.slice(0, 40), parametri: clona(P) });
      S.bozza.preset = String(preset.length - 1);
      salvaBozza(); salvaImpostazioni(); passoParametri(box);
    };
    const el = document.getElementById("eliminaPreset");
    if (el) el.onclick = () => {
      if (!confirm("Eliminare il preset?")) return;
      preset.splice(Number(S.bozza.preset), 1); S.bozza.preset = ""; salvaBozza(); salvaImpostazioni(); passoParametri(box);
    };
    piedePasso(box);
  }

  // ---------------- passo 4: avvio
  function retailerUsati() {
    const usati = paesiAsin();
    return S.impostazioni.retailer.filter((r) => r.attivo && r.nome && usati.includes(r.paese)).map(({ _mod, ...r }) => r);
  }
  function passoAvvio(box) {
    const b = S.bozza, ret = retailerUsati(), P = b.parametri;
    const coperti = b.asin.filter((a) => ret.some((r) => r.paese === a.paese));
    const coppie = coperti.reduce((n, a) => n + ret.filter((r) => r.paese === a.paese).length, 0);
    const minuti = Math.max(2, Math.round((coperti.length * 12 + coppie * (P.verifica_url ? 45 : 28)) / 60)) + 2;
    const attivi = T.parametriInfo.flatMap((g) => g.voci).filter((v) => P[v.chiave].attivo);
    if (!b.nome) b.nome = `Ricerca ${new Date().toLocaleDateString("it-IT", { month: "long", year: "numeric" })}`;
    box.innerHTML = `
      <section class="scheda">
        <h2>Tutto pronto</h2>
        <p class="tenue" style="margin-top:6px">Il motore gira su GitHub: puoi chiudere la pagina, cambiare dispositivo o perdere la connessione. Ritrovi la ricerca nello <a href="#/esecuzioni">Storico</a>.</p>
        <label class="campo" style="margin-top:20px">Nome della ricerca<input type="text" id="nomeRicerca" maxlength="80" value="${esc(b.nome)}"></label>
        <div class="riepilogo">
          <div><strong>${coperti.length}</strong><span class="tenue piccolo">ASIN da confrontare${coperti.length < b.asin.length ? ` (${b.asin.length - coperti.length} senza marketplace)` : ""}</span></div>
          <div><strong>${ret.length}</strong><span class="tenue piccolo">marketplace in ${[...new Set(ret.map((r) => r.paese))].map((c) => paese(c).bandiera).join(" ")}</span></div>
          <div><strong>~${minuti} min</strong><span class="tenue piccolo">durata stimata</span></div>
        </div>
        <p class="piccolo tenue">Criteri attivi: ${attivi.map((v) => `<span class="chip">${v.titolo}${v.chiave === "pollici" && P.pollici.tolleranza ? ` ±${P.pollici.tolleranza}"` : ""}${v.chiave === "anno" ? ` ${P.anno.valore}` : ""}</span>`).join(" ") || "nessuno"}</p>
        <div style="margin-top:26px;display:flex;gap:12px;flex-wrap:wrap;align-items:center">
          <button class="btn primario grande" type="button" id="btnAvvia" ${coperti.length ? "" : "disabled"}>${ICONE.play} Avvia la ricerca</button>
          <span class="tenue piccolo" id="msgAvvio"></span>
        </div>
      </section>`;
    document.getElementById("nomeRicerca").oninput = (e) => { b.nome = e.target.value; salvaBozza(); };
    document.getElementById("btnAvvia").onclick = async (e) => {
      const btn = e.currentTarget;
      btn.disabled = true;
      document.getElementById("msgAvvio").innerHTML = '<span class="caricamento"></span> Avvio su GitHub…';
      try {
        const { id } = await api("run", { metodo: "POST", corpo: {
          nome: b.nome, retailer: ret, parametri: P,
          asin: coperti.map((a) => ({ asin: a.asin, paese: a.paese, ...(a.modello ? { modello: a.modello } : {}) })),
        } });
        const recenti = memoria.leggi("recenti", []);
        memoria.scrivi("recenti", [id, ...recenti].slice(0, 20));
        toast("Ricerca avviata", "ok");
        ultimoControllo = 0;
        location.hash = `#/run/${id}`;
      } catch (err) {
        btn.disabled = false;
        document.getElementById("msgAvvio").textContent = err.message;
      }
    };
    piedePasso(box, { avanti: false });
  }

  // ------------------------------------------------------------------ esecuzione e risultati
  const filtri = { testo: "", paese: "", retailer: "", soloMatch: false };

  function statoRun(stato, gh) {
    if (stato && stato.stato === "completato") return { cod: "completato", testo: "Completata", chip: "ok" };
    if (stato && stato.stato === "errore") return { cod: "errore", testo: "Interrotta per errore", chip: "errore" };
    if (gh && gh.status === "completed") {
      if (gh.conclusion === "cancelled") return { cod: "annullato", testo: "Annullata", chip: "attenzione" };
      if (gh.conclusion !== "success") return { cod: "errore", testo: "Interrotta", chip: "errore" };
      return { cod: "completato", testo: "Completata", chip: "ok" };
    }
    if (!stato) return { cod: "coda", testo: gh && gh.status === "queued" ? "In coda su GitHub" : "In preparazione", chip: "info" };
    return { cod: "corso", testo: "In corso", chip: "info" };
  }

  async function vistaRun(id) {
    app.innerHTML = `<div class="attesa vista"><span class="caricamento"></span><p class="tenue">Carico la ricerca…</p></div>`;
    let primo = true;
    const ciclo = async () => {
      let dati;
      try { dati = await api(`stato?id=${encodeURIComponent(id)}`); }
      catch (e) {
        if (primo) app.innerHTML = `<div class="vuoto vista"><h2>Ricerca non trovata</h2><p class="tenue">${esc(e.message)}. Se l'hai appena avviata, attendi qualche secondo e ricarica.</p><a class="btn" href="#/esecuzioni">Vai allo storico</a></div>`;
        return;
      }
      const st = statoRun(dati.stato, dati.github);
      disegnaRun(id, dati, st, primo);
      primo = false;
      if (["completato", "errore", "annullato"].includes(st.cod)) { clearInterval(S.polling); aggiornaPill(true); }
    };
    await ciclo();
    S.polling = setInterval(() => { if (!document.hidden) ciclo(); }, 6000);
  }

  function disegnaRun(id, dati, st, primo) {
    const s = dati.stato || {}, gh = dati.github || {};
    S.statoRun = s; // i pulsanti leggono sempre l'ultimo stato ricevuto
    const av = s.avanzamento || { fatti: 0, totale: 1, corrente: st.testo };
    const perc = st.cod === "completato" ? 100 : Math.min(99, Math.round((av.fatti / Math.max(1, av.totale)) * 100));
    const inCorso = st.cod === "corso" || st.cod === "coda";
    const risultati = s.risultati || [];
    const nome = s.nome || gh.nome || "Ricerca";
    // aggiornamento leggero se la pagina è già disegnata: evita salti durante il polling
    const esistente = document.getElementById("runPagina");
    if (esistente && esistente.dataset.id === id && !primo) {
      document.getElementById("runStato").className = `chip ${st.chip}`;
      document.getElementById("runStato").textContent = st.testo;
      impostaProgresso(perc, inCorso);
      document.getElementById("runCorrente").textContent = av.corrente || st.testo;
      document.getElementById("runConteggio").textContent = `${av.fatti}/${av.totale} confronti · ${durata(s.iniziato || gh.creato, s.finito)}`;
      const con = document.getElementById("console");
      if (con) { const giu = con.scrollTop + con.clientHeight >= con.scrollHeight - 10; con.textContent = (s.log || []).join("\n"); if (giu) con.scrollTop = con.scrollHeight; }
      document.getElementById("btnAnnulla").hidden = !inCorso;
      document.getElementById("notaPrep").hidden = !(!dati.stato && inCorso);
      document.getElementById("btnExport").disabled = !risultati.length;
      document.getElementById("btnMancanti").hidden = !(risultati.some((r) => r.errore) && !inCorso);
      const n = document.getElementById("risultatiZona");
      if (n.dataset.conta !== String(risultati.length) || !inCorso) { n.dataset.conta = risultati.length; disegnaRisultati(n, s, inCorso); }
      return;
    }
    app.innerHTML = `
      <div class="vista" id="runPagina" data-id="${esc(id)}">
        <div class="run-testa">
          <div>
            <h1>${esc(nome)}</h1>
            <div class="meta">
              <span class="chip ${st.chip}" id="runStato">${st.testo}</span>
              <span class="chip">Avviata ${dataBreve(s.iniziato || gh.creato)}</span>
              ${gh.url ? `<a class="chip" href="${esc(gh.url)}" target="_blank" rel="noopener">Dettagli tecnici su GitHub</a>` : ""}
            </div>
          </div>
          <div style="display:flex;gap:10px;flex-wrap:wrap">
            <button class="btn pericolo" type="button" id="btnAnnulla" ${inCorso ? "" : "hidden"}>Annulla</button>
            <button class="btn" type="button" id="btnMancanti" ${risultati.some((r) => r.errore) && !inCorso ? "" : "hidden"}>Completa i modelli mancanti</button>
            <button class="btn" type="button" id="btnDuplica">Riusa le impostazioni</button>
            <button class="btn primario" type="button" id="btnExport" ${risultati.length ? "" : "disabled"}>${ICONE.scarica} Scarica xlsx</button>
          </div>
        </div>
        <section class="scheda" style="margin-top:24px">
          <div class="progresso ${inCorso ? "attivo" : ""}" id="progresso" style="margin-top:0">
            <div class="traccia"><div class="riempi" id="riempi"></div></div>
            <div class="dati"><span id="runCorrente">${esc(av.corrente || st.testo)}</span><span class="tenue" id="runConteggio">${av.fatti}/${av.totale} confronti · ${durata(s.iniziato || gh.creato, s.finito)}</span></div>
          </div>
          ${s.errore ? `<p class="chip errore" style="white-space:normal;padding:8px 12px;margin-top:10px">${esc(s.errore)}</p>` : ""}
          <details ${inCorso ? "open" : ""} style="margin-top:14px"><summary>Registro attività</summary><div class="console" id="console">${esc((s.log || []).join("\n")) || "In attesa che il motore parta…"}</div></details>
          <p class="tenue piccolo" id="notaPrep" style="margin-top:10px" ${!dati.stato && inCorso ? "" : "hidden"}>GitHub sta preparando la macchina: di solito serve meno di un minuto. Puoi chiudere la pagina, la ricerca prosegue.</p>
        </section>
        <div id="risultatiZona" data-conta="${risultati.length}"></div>
      </div>`;
    impostaProgresso(perc, inCorso);
    const con = document.getElementById("console");
    con.scrollTop = con.scrollHeight;
    document.getElementById("btnAnnulla").onclick = async () => {
      if (!confirm("Annullare la ricerca? I risultati già trovati restano consultabili.")) return;
      try { await api("annulla", { metodo: "POST", corpo: { id } }); toast("Annullamento richiesto"); } catch (e) { toast(e.message, "errore"); }
    };
    document.getElementById("btnDuplica").onclick = () => {
      const c = S.statoRun.config;
      if (!c) return toast("Configurazione non ancora disponibile", "errore");
      S.bozza = { asin: c.asin.map((a) => ({ modello: "", ...a })), nome: "", paeseDefault: c.asin[0]?.paese || "IT", parametri: Object.assign(clona(T.parametriDefault), c.parametri), preset: "" };
      salvaBozza();
      toast("Impostazioni caricate: controlla e avvia", "ok");
      location.hash = "#/nuova/1";
    };
    document.getElementById("btnExport").onclick = () => esportaXlsx(S.statoRun);
    document.getElementById("btnMancanti").onclick = () => {
      const s = S.statoRun;
      const falliti = (s.risultati || []).filter((r) => r.errore);
      S.bozza = {
        asin: falliti.map((r) => ({ asin: r.asin, paese: r.paese, modello: "" })),
        mancanti: falliti.map((r) => r.asin),
        nome: `${s.nome || "Ricerca"}: modelli mancanti`, paeseDefault: falliti[0]?.paese || "IT",
        parametri: Object.assign(clona(T.parametriDefault), s.config?.parametri || {}), preset: "",
      };
      salvaBozza();
      toast("Scrivi il modello accanto a ogni ASIN evidenziato, poi avvia", "ok");
      location.hash = "#/nuova/1";
    };
    disegnaRisultati(document.getElementById("risultatiZona"), s, inCorso);
  }

  function impostaProgresso(perc, attivo) {
    const r = document.getElementById("riempi"), traccia = r.parentElement;
    r.style.width = perc + "%";
    r.style.backgroundSize = `${traccia.clientWidth}px 100%`; // le 5 barre restano fisse mentre la barra cresce
    document.getElementById("progresso").classList.toggle("attivo", attivo);
  }

  function disegnaRisultati(box, s, inCorso) {
    const ris = s.risultati || [];
    if (!ris.length) { box.innerHTML = inCorso ? "" : `<div class="vuoto"><p class="tenue">Nessun risultato salvato.</p></div>`; return; }
    const retNomi = [...new Map((s.config?.retailer || []).map((r) => [r.nome, r])).values()];
    const paesiR = [...new Set(ris.map((r) => r.paese))];
    const conMatch = ris.filter((r) => Object.values(r.match || {}).some((m) => m.length)).length;
    const totMatch = ris.reduce((n, r) => n + Object.values(r.match || {}).reduce((k, m) => k + m.length, 0), 0);
    const copertura = ris.reduce((n, r) => n + Object.keys(r.match || {}).length, 0);
    box.innerHTML = `
      <div class="kpi">
        <div><strong>${ris.length}${inCorso ? `<span class="tenue" style="font-size:1rem">/${s.config?.asin?.length || "?"}</span>` : ""}</strong><span class="tenue piccolo">ASIN elaborati</span></div>
        <div><strong>${conMatch}</strong><span class="tenue piccolo">con almeno un modello simile</span></div>
        <div><strong>${totMatch}</strong><span class="tenue piccolo">modelli simili trovati</span></div>
        <div><strong>${ris.reduce((n, r) => n + Object.values(r.esito || {}).filter((e) => e === "non_presente").length, 0)}</strong><span class="tenue piccolo">confronti con prodotto non presente</span></div>
        <div><strong>${copertura ? Math.round((ris.reduce((n, r) => n + Object.values(r.match || {}).filter((m) => m.length).length, 0) / copertura) * 100) : 0}%</strong><span class="tenue piccolo">confronti con esito positivo</span></div>
      </div>
      <div class="filtri">
        <input type="text" id="fTesto" placeholder="Cerca ASIN o modello" value="${esc(filtri.testo)}" aria-label="Cerca">
        ${paesiR.length > 1 ? `<select id="fPaese"><option value="">Tutti i paesi</option>${paesiR.map((c) => `<option value="${c}" ${filtri.paese === c ? "selected" : ""}>${paese(c).bandiera} ${paese(c).nome}</option>`).join("")}</select>` : ""}
        <select id="fRet"><option value="">Tutti i marketplace</option>${retNomi.map((r) => `<option ${filtri.retailer === r.nome ? "selected" : ""}>${esc(r.nome)}</option>`).join("")}</select>
        <label class="check piccolo"><input type="checkbox" id="fSolo" ${filtri.soloMatch ? "checked" : ""}> Solo con modelli simili</label>
        <span style="margin-left:auto" class="segmenti" role="group" aria-label="Vista">
          <button type="button" data-vista="schede" class="${S.vistaRisultati === "schede" ? "attivo" : ""}">Schede</button>
          <button type="button" data-vista="tabella" class="${S.vistaRisultati === "tabella" ? "attivo" : ""}">Tabella</button>
        </span>
      </div>
      <div id="elencoRis"></div>`;
    const ridisegna = () => elencoRisultati(document.getElementById("elencoRis"), ris, retNomi);
    document.getElementById("fTesto").oninput = rimbalzo((e) => { filtri.testo = e.target.value; ridisegna(); }, 200);
    const fp = document.getElementById("fPaese"); if (fp) fp.onchange = (e) => { filtri.paese = e.target.value; ridisegna(); };
    document.getElementById("fRet").onchange = (e) => { filtri.retailer = e.target.value; ridisegna(); };
    document.getElementById("fSolo").onchange = (e) => { filtri.soloMatch = e.target.checked; ridisegna(); };
    box.querySelectorAll("[data-vista]").forEach((b) => (b.onclick = () => {
      S.vistaRisultati = b.dataset.vista; memoria.scrivi("vista", S.vistaRisultati);
      box.querySelectorAll("[data-vista]").forEach((x) => x.classList.toggle("attivo", x === b)); ridisegna();
    }));
    ridisegna();
  }

  function foto(url, alt) {
    if (!url) return `<div class="foto vuota">${ICONE.tv}</div>`;
    return `<div class="foto"><img src="${esc(url)}" alt="${esc(alt)}" loading="lazy" referrerpolicy="no-referrer" onerror="this.parentElement.classList.add('vuota');this.parentElement.innerHTML=window.TVM_TV"></div>`;
  }
  window.TVM_TV = ICONE.tv;

  function etichetteInfo(a) {
    const out = [];
    if (a.pollici) out.push(`${a.pollici}"`);
    if (a.tecnologia) out.push(T.nomeTecnologia[a.tecnologia] || a.tecnologia);
    if (a.risoluzione) out.push(a.risoluzione);
    if (a.anno) out.push(a.anno);
    if (a.pro) out.push("PRO");
    return out.map((x) => `<span class="chip">${esc(x)}</span>`).join("");
  }

  function elencoRisultati(box, ris, retNomi) {
    const q = filtri.testo.trim().toUpperCase();
    const lista = ris.filter((r) => {
      if (filtri.paese && r.paese !== filtri.paese) return false;
      const m = r.match || {};
      if (filtri.soloMatch && !Object.values(m).some((x) => x.length)) return false;
      if (q) {
        const testo = [r.asin, r.amazon?.modello, r.amazon?.titolo, ...Object.values(m).flat().map((x) => x.modello)].join(" ").toUpperCase();
        if (!testo.includes(q)) return false;
      }
      return true;
    });
    if (!lista.length) { box.innerHTML = '<div class="vuoto"><p class="tenue">Nessun ASIN corrisponde ai filtri.</p></div>'; return; }
    const retDi = (r) => retNomi.filter((x) => x.paese === r.paese && (!filtri.retailer || x.nome === filtri.retailer));
    if (S.vistaRisultati === "tabella") {
      const colonne = retNomi.filter((x) => (!filtri.retailer || x.nome === filtri.retailer) && lista.some((r) => r.paese === x.paese));
      box.innerHTML = `
        <div class="matrice-wrap"><table class="matrice">
          <thead><tr><th>ASIN</th><th>Modello Amazon</th>${colonne.map((c) => `<th>${paese(c.paese).bandiera} ${esc(c.nome)}</th>`).join("")}</tr></thead>
          <tbody>${lista.map((r) => `<tr>
            <td><a href="${esc(r.amazon?.url)}" target="_blank" rel="noopener">${esc(r.asin)}</a></td>
            <td class="mod">${esc(r.amazon?.modello || "—")}</td>
            ${colonne.map((c) => {
              if (c.paese !== r.paese) return '<td class="tenue">·</td>';
              const m = (r.match || {})[c.nome] || [];
              const e = (r.esito || {})[c.nome];
              return `<td>${m.length ? m.map((x) => `<a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.modello)}</a>${x.nota ? ` <span class="chip attenzione">${esc(x.nota)}</span>` : ""}`).join("<br>") : `<span class="${e === "errore" ? "chip errore" : "tenue"}">${e ? ESITI[e] : "—"}</span>`}</td>`;
            }).join("")}
          </tr>`).join("")}</tbody>
        </table></div>`;
      return;
    }
    box.innerHTML = lista.map((r) => {
      const a = r.amazon || {};
      return `
        <article class="asin-card">
          <div class="amazon-lato">
            ${foto(a.img, a.modello)}
            <div style="display:flex;justify-content:space-between;gap:8px;align-items:center"><span class="chip">${paese(r.paese).bandiera} Amazon ${esc(r.paese)}</span><a class="piccolo" href="${esc(a.url)}" target="_blank" rel="noopener">${esc(r.asin)}</a></div>
            <div class="modello">${esc(a.modello || "Modello non riconosciuto")}</div>
            <div class="etichette">${etichetteInfo(a)}</div>
            ${a.titolo ? `<p class="titolo-amz">${esc(a.titolo)}</p>` : ""}
            ${r.errore ? `<span class="chip errore" style="white-space:normal">${esc(r.errore === "captcha Amazon" ? "Amazon ha bloccato la lettura (captcha): scrivi il modello e rilancia" : r.errore)}</span>` : ""}
            ${!r.errore && a.fonte && a.fonte !== "Amazon" ? `<span class="chip ${a.fonte === "ricerca web" ? "attenzione" : "info"}" style="white-space:normal">${a.fonte === "ricerca web" ? "Modello ricavato dal web: verificalo" : a.fonte === "anagrafica" ? "Modello da ricerche precedenti" : "Modello inserito a mano"}</span>` : ""}
          </div>
          <div class="match-griglia">
            ${retDi(r).map((ret) => {
              const m = (r.match || {})[ret.nome];
              const es = (r.esito || {})[ret.nome];
              if (es === "saltato" || (m === undefined && r.errore)) return `<div class="match-tile nessuno"><div class="retailer">${esc(ret.nome)}</div><span class="piccolo">Saltato: serve il modello Amazon</span></div>`;
              if (m === undefined) return `<div class="match-tile nessuno"><div class="retailer">${esc(ret.nome)}</div><span>In attesa</span></div>`;
              if (!m.length) {
                const e = (r.esito || {})[ret.nome] || "nessun_simile";
                return `<div class="match-tile nessuno ${e}"><div class="retailer">${esc(ret.nome)}<span class="chip ${e === "errore" || e === "illeggibile" ? "errore" : ""}">${ESITI[e]}</span></div><span class="piccolo">${ESITI_NOTA[e] || ""}</span></div>`;
              }
              const [x, ...altri] = m;
              return `
                <div class="match-tile">
                  <div class="retailer"><span>${esc(ret.nome)}</span>${x.nota ? `<span class="chip attenzione">${esc(x.nota)}</span>` : '<span class="chip ok">simile</span>'}</div>
                  ${foto(x.img, x.modello)}
                  <div class="modello">${esc(x.modello)}</div>
                  ${x.titolo ? `<p class="titolo-ret" title="${esc(x.titolo)}">${esc(x.titolo)}</p>` : ""}
                  <div class="etichette">${etichetteInfo(x)}</div>
                  <a class="vai" href="${esc(x.url)}" target="_blank" rel="noopener">Apri la pagina prodotto</a>
                  ${altri.length ? `<div class="altri">Anche: ${altri.map((y) => `<a href="${esc(y.url)}" target="_blank" rel="noopener">${esc(y.modello)}</a>`).join(", ")}</div>` : ""}
                </div>`;
            }).join("") || '<p class="tenue">Nessun marketplace per questo paese.</p>'}
          </div>
        </article>`;
    }).join("");
  }

  // ------------------------------------------------------------------ export xlsx
  function esportaXlsx(s) {
    if (!window.XLSX) return toast("Generatore Excel non ancora caricato, riprova", "errore");
    const ris = s.risultati || [], retTutti = s.config?.retailer || [];
    const wb = XLSX.utils.book_new();
    [...new Set(ris.map((r) => r.paese))].forEach((c) => {
      const ret = retTutti.filter((r) => r.paese === c);
      const righe = [
        ["ASIN", "Amazon product name", "Amazon Model", ...ret.flatMap((r) => [r.nome, ""])],
        ["", "", "", ...ret.flatMap(() => ["Model Name", "Product URL"])],
      ];
      ris.filter((r) => r.paese === c).forEach((r) => {
        righe.push([r.asin, r.amazon?.titolo || "", r.amazon?.modello || "", ...ret.flatMap((x) => {
          const m = (r.match || {})[x.nome] || [];
          const e = (r.esito || {})[x.nome];
          if (m.length) return [m.map((y) => y.modello).join(" / "), m.map((y) => y.url).join(" ")];
          return [e && e !== "trovato" ? ESITI[e] : "", ""];
        })]);
      });
      const ws = XLSX.utils.aoa_to_sheet(righe);
      ws["!merges"] = [0, 1, 2].map((k) => ({ s: { r: 0, c: k }, e: { r: 1, c: k } })).concat(ret.map((_, i) => ({ s: { r: 0, c: 3 + i * 2 }, e: { r: 0, c: 4 + i * 2 } })));
      ws["!cols"] = [{ wch: 13 }, { wch: 55 }, { wch: 18 }, ...ret.flatMap(() => [{ wch: 18 }, { wch: 50 }])];
      XLSX.utils.book_append_sheet(wb, ws, `Matching ${c}`.slice(0, 31));
    });
    const det = [["ASIN", "Paese", "Fonte", "Modello trovato", "Famiglia", "Pollici", "Anno", "URL", "Esito", "Ricerca"]];
    ris.forEach((r) => {
      det.push([r.asin, r.paese, "Amazon", r.amazon?.modello, r.amazon?.famiglia, r.amazon?.pollici, r.amazon?.anno, r.amazon?.url, r.errore || "riferimento", ""]);
      (r.dettaglio || []).forEach((d) => det.push([r.asin, r.paese, d.retailer, d.modello || "", d.famiglia || "", d.pollici || "", d.anno || "", d.url || "", d.esito || "", d.ricerca || ""]));
    });
    const wd = XLSX.utils.aoa_to_sheet(det);
    wd["!cols"] = [{ wch: 13 }, { wch: 6 }, { wch: 16 }, { wch: 18 }, { wch: 28 }, { wch: 8 }, { wch: 7 }, { wch: 60 }, { wch: 34 }, { wch: 26 }];
    XLSX.utils.book_append_sheet(wb, wd, "Dettaglio");
    const nome = (s.nome || "Matching_TV").replace(/[^\w\- ]+/g, "").trim().replace(/\s+/g, "_");
    XLSX.writeFile(wb, `${nome}_${(s.iniziato || "").slice(0, 10)}.xlsx`);
  }

  // ------------------------------------------------------------------ storico
  async function vistaStorico() {
    app.innerHTML = `
      <div class="vista">
        <div class="intestazione"><div><h1>Storico</h1><p class="tenue">Tutte le ricerche lanciate dal sito, da qualsiasi dispositivo. Apri una ricerca per vederne risultati o avanzamento.</p></div>
          <a class="btn primario" href="#/nuova/1">Nuova ricerca</a></div>
        <div id="listaRun"><div class="attesa"><span class="caricamento"></span></div></div>
      </div>`;
    const box = document.getElementById("listaRun");
    const disegna = async () => {
      try {
        const { runs } = await api("runs");
        if (!runs.length) {
          box.innerHTML = `<div class="vuoto"><div style="width:140px">${ICONE.tv}</div><h2>Ancora nessuna ricerca</h2><p class="tenue">Le ricerche avviate compariranno qui, con lo stato e i risultati.</p><a class="btn primario" href="#/nuova/1">Inizia una ricerca</a></div>`;
          return;
        }
        box.innerHTML = `<div class="lista-run">${runs.map((r) => {
          const st = statoRun(null, r);
          const etichetta = r.status !== "completed" ? (r.status === "queued" ? "In coda" : "In corso") : st.testo;
          return `<a class="run-riga" href="#/run/${esc(r.id)}">
            <div><strong>${esc(r.nome || r.id)}</strong><div class="tenue piccolo">${dataBreve(r.creato)} · durata ${durata(r.creato, r.status === "completed" ? r.aggiornato : null)}</div></div>
            <span class="chip ${r.status !== "completed" ? "info" : st.chip}">${r.status !== "completed" ? '<span class="puntino"></span>' : ""}${etichetta}</span>
            <span class="tenue">Apri</span></a>`;
        }).join("")}</div>`;
        if (runs.some((r) => r.status !== "completed")) S.polling = S.polling || setInterval(() => { if (!document.hidden) disegna(); }, 15000);
      } catch (e) {
        box.innerHTML = `<div class="vuoto"><p class="tenue">Non riesco a leggere le ricerche: ${esc(e.message)}</p></div>`;
      }
    };
    disegna();
  }

  // ------------------------------------------------------------------ guida e tutorial
  const SLIDE = [
    { titolo: "Benvenuto in TV Matcher", testo: "Parti da una lista di ASIN Amazon e trova, per ogni retailer europeo, il TV più simile con un codice modello diverso.", colore: "var(--giallo)" },
    { titolo: "Incolla gli ASIN", testo: "Copia da Excel, scrivi uno per riga o carica un file. Il paese si legge dalla riga oppure si sceglie per ogni ASIN.", colore: "var(--ciano)" },
    { titolo: "Scegli marketplace e criteri", testo: "Spunta i retailer su cui cercare e decidi quando due TV sono simili: pollici, tecnologia, fascia, anno e altro.", colore: "var(--verde)" },
    { titolo: "Avvia e chiudi pure", testo: "La ricerca gira su GitHub per 10–30 minuti. Puoi chiudere il browser: la ritrovi nello Storico, con i risultati da scaricare in Excel.", colore: "var(--magenta)" },
  ];
  function tutorial() {
    let i = 0;
    const m = document.createElement("div");
    m.className = "modale-sfondo";
    m.setAttribute("role", "dialog");
    m.setAttribute("aria-modal", "true");
    const disegna = () => {
      const s = SLIDE[i];
      m.innerHTML = `
        <div class="modale">
          <div class="illustrazione">
            <svg viewBox="0 0 320 150" width="320" height="150" aria-hidden="true">
              <rect x="${110 + i * 6}" y="${18 - i * 2}" width="150" height="96" rx="14" fill="none" stroke="#7B61FF" stroke-width="5" opacity=".7"/>
              <clipPath id="tc"><rect x="60" y="38" width="150" height="96" rx="14"/></clipPath>
              <g clip-path="url(#tc)">${["#FFD23F", "#2EE6F0", "#4BE38E", "#FF4FA3", "#7B61FF"].map((c, k) => `<rect x="${60 + k * 30}" y="38" width="30" height="96" fill="${c}" opacity="${k <= i ? 1 : 0.18}"/>`).join("")}</g>
              <rect x="60" y="38" width="150" height="96" rx="14" fill="none" stroke="#F1EEFF" stroke-width="4"/>
            </svg>
          </div>
          <div class="corpo"><h2>${s.titolo}</h2><p class="tenue">${s.testo}</p></div>
          <div class="piede">
            <div class="puntini">${SLIDE.map((_, k) => `<i class="${k === i ? "on" : ""}"></i>`).join("")}</div>
            <div style="display:flex;gap:8px">
              <button class="btn fantasma" type="button" data-t="salta">${i < SLIDE.length - 1 ? "Salta" : ""}</button>
              <button class="btn primario" type="button" data-t="avanti">${i < SLIDE.length - 1 ? "Avanti" : "Inizia"}</button>
            </div>
          </div>
        </div>`;
      m.querySelector('[data-t="avanti"]').focus();
      m.querySelector('[data-t="avanti"]').onclick = () => { if (i < SLIDE.length - 1) { i++; disegna(); } else chiudi(); };
      m.querySelector('[data-t="salta"]').onclick = chiudi;
    };
    const chiudi = () => { memoria.scrivi("tutorial", true); m.remove(); };
    m.addEventListener("keydown", (e) => { if (e.key === "Escape") chiudi(); });
    document.body.appendChild(m);
    disegna();
  }

  function vistaGuida() {
    app.innerHTML = `
      <div class="vista">
        <div class="intestazione"><div><h1>Guida</h1><p class="tenue">Tutto quello che serve per lanciare una ricerca e leggere i risultati.</p></div>
          <button class="btn" type="button" id="rivedi">Rivedi il tutorial</button></div>
        <div class="guida">
          <ol>
            <li><div><h3>Inserisci gli ASIN</h3><p>Incolla la lista o carica un CSV/Excel. Ogni ASIN ha un paese: lo leggo dalla riga (es. <code>B0F457MQCQ;IT</code>) o uso il paese predefinito. Se Amazon non risponde, scrivi a mano il modello nella colonna facoltativa.</p></div></li>
            <li><div><h3>Scegli i marketplace</h3><p>Spunta i retailer su cui cercare. Puoi modificare un URL, aggiungerne di nuovi o disattivarli: le modifiche valgono per tutti e restano salvate.</p></div></li>
            <li><div><h3>Imposta la somiglianza</h3><p>Accendi i criteri da rispettare. La configurazione standard segue il documento di matching: stessi pollici, stessa famiglia e fascia, anno 2026, PRO separati. Salva le combinazioni che usi spesso come preset.</p></div></li>
            <li><div><h3>Avvia e attendi</h3><p>Il motore gira su GitHub. Una ricerca da 10 ASIN su 4 retailer richiede circa 20 minuti. Puoi chiudere la pagina: la pillola verde in alto e lo Storico ti riportano all'avanzamento.</p></div></li>
            <li><div><h3>Leggi e scarica</h3><p>Per ogni ASIN vedi i modelli simili per retailer con foto e link. "Anno da verificare" segnala i modelli il cui anno non si ricava dal codice. Scarica l'Excel con un foglio per paese più il foglio Dettaglio con tutti i candidati scartati e il motivo.</p></div></li>
          </ol>
          <aside class="scheda faq">
            <h3>Domande frequenti</h3>
            <details><summary>Perché un retailer non trova niente?</summary><p>Il sito può aver cambiato l'indirizzo di ricerca o bloccato l'accesso automatico. Controlla l'URL nel passo Marketplace e guarda il foglio Dettaglio: "ricerca: timeout" o "HTTP 403" indicano un blocco.</p></details>
            <details><summary>Amazon ha bloccato la lettura (captcha): cosa faccio?</summary><p>Amazon a volte blocca le visite automatiche. Il motore riprova con indirizzi diversi e poi cerca l'ASIN sul web. Se non basta, apri la ricerca, premi "Completa i modelli mancanti", scrivi il modello accanto all'ASIN (basta il codice, es. 85U8075F) e avvia. Il modello resta salvato per le ricerche successive.</p></details>
                        <details><summary>Cosa vuol dire "anno da verificare"?</summary><p>Il codice non dichiara l'anno e il titolo non lo riporta. Il modello rispetta gli altri criteri: verifica l'anno sulla pagina prodotto o spegni "Accetta anno non ricavabile".</p></details>
            <details><summary>Posso lanciare più ricerche insieme?</summary><p>Sì, girano in parallelo su GitHub. Ognuna compare nello Storico con il suo stato.</p></details>
            <details><summary>Il prezzo viene letto?</summary><p>No: il confronto si basa solo su codice modello, pollici e caratteristiche tecniche.</p></details>
          </aside>
        </div>
      </div>`;
    document.getElementById("rivedi").onclick = tutorial;
  }

  // ------------------------------------------------------------------ avvio
  (async () => {
    try {
      const { autenticato } = await api("login");
      if (!autenticato) { history.replaceState(null, "", "#/login"); return router(); }
    } catch { /* sito senza API (anteprima): prosegue */ }
    await caricaImpostazioni();
    if (!location.hash || location.hash === "#/login") history.replaceState(null, "", "#/nuova");
    await router();
    if (!memoria.leggi("tutorial", false)) tutorial();
  })();
})();
