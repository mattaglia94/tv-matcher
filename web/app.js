/* TV Finder — logica del sito (JavaScript puro, nessun framework). */
(() => {
  "use strict";
  const T = window.TVM;
  const app = document.getElementById("app");

  // ------------------------------------------------------------------ utilità
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const clona = (o) => JSON.parse(JSON.stringify(o));
  // parametri salvati prima della modalità: "stessa marca" spenta = ricerca di concorrenti
  function normalizzaParametri(p) {
    const vecchio = p && p.stessa_marca;
    const out = Object.assign(clona(T.parametriDefault), p || {});
    if (vecchio && !(p && p.modalita)) out.modalita = vecchio.attivo === false ? "concorrente" : "stessa_marca";
    delete out.stessa_marca;
    return out;
  }
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
  const testoEsito = (e) => (S.ricercaIdentica && e === "nessun_simile" ? "Stesso modello non presente" : ESITI[e]);
  const ESITI = { saltato: "Saltato", trovato: "Trovato", non_presente: "Prodotto non presente", nessun_simile: "Nessun modello simile", errore: "Ricerca non riuscita", illeggibile: "Sito non consultabile" };
  const ESITI_NOTA = {
    non_presente: "Nessuna TV con la marca e la diagonale cercate nel catalogo del retailer.",
    nessun_simile: "Ci sono TV con la marca e la diagonale cercate, ma nessuno rispetta i criteri.",
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
  S.bozza.parametri = normalizzaParametri(S.bozza.parametri);
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
        const corretti = { "https://www.expert.it/search?q={q}": "https://www.expert.it/it/it/exp/shop/search?terms={q}" };
        impostazioni.retailer.forEach((r) => { if (corretti[r.url]) r.url = corretti[r.url]; });
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
    if (vista === "catalogo") return vistaCatalogo();
    if (vista === "feedback") return vistaFeedback();
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
          <div><h1>TV Finder</h1><p class="tenue" style="margin-top:10px">Trova lo stesso modello o i modelli simili alle TV Amazon sui retailer europei.</p></div>
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
            <p class="tenue">Parti da una lista di ASIN Amazon: il motore trova, per ogni retailer, lo stesso modello oppure la TV più simile.</p>
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
  const DOMINI_AMZ = { "amazon.it": "IT", "amazon.de": "DE", "amazon.fr": "FR", "amazon.es": "ES", "amazon.co.uk": "UK" };
  const AMZ_DI = Object.fromEntries(Object.entries(DOMINI_AMZ).map(([d, p]) => [p, d]));
  function estraiAsin(testo, paeseDef) {
    const trovati = [], visti = new Set();
    for (const riga of String(testo).split(/\r?\n|,(?=\s*(?:B0|https?:))/i)) {
      const R = riga.toUpperCase();
      // link Amazon: il paese viene dal dominio
      const link = [...riga.matchAll(/amazon\.(it|de|fr|es|co\.uk)\/[^\s"']*?(?:dp|gp\/product|gp\/aw\/d)\/(B0[A-Z0-9]{8})/gi)];
      link.forEach((m) => { const pa = DOMINI_AMZ["amazon." + m[1].toLowerCase()]; const k = m[2].toUpperCase() + pa; if (!visti.has(k)) { visti.add(k); trovati.push({ asin: m[2].toUpperCase(), paese: pa, modello: "" }); } });
      const asins = (R.replace(/HTTPS?:\/\/\S+/g, " ").match(/\bB0[A-Z0-9]{8}\b/g) || []);
      if (!asins.length) continue;
      const pm = R.replace(/HTTPS?:\/\/\S+/g, " ").match(/(?:^|[^A-Z])(IT|DE|FR|ES|UK|GB)(?:[^A-Z]|$)/);
      const pa = pm ? (pm[1] === "GB" ? "UK" : pm[1]) : paeseDef;
      asins.forEach((x) => { if (!visti.has(x + pa)) { visti.add(x + pa); trovati.push({ asin: x, paese: pa, modello: "" }); } });
    }
    return trovati;
  }
  function aggiungiAsin(lista) {
    const presenti = new Set(S.bozza.asin.map((a) => a.asin + a.paese));
    let nuovi = 0;
    lista.forEach((a) => {
      if (presenti.has(a.asin + a.paese)) return;
      a._nuovo = true;  // il modello non si precompila più: la base è sempre la pagina Amazon
      S.bozza.asin.push(a); presenti.add(a.asin + a.paese); nuovi++;
    });
    salvaBozza();
    toast(nuovi ? `${nuovi} ASIN aggiunti` : "Erano già tutti in lista", nuovi ? "ok" : "");
    return nuovi;
  }
  function statoAsin(a) {
    const noto = S.anagrafica[`${a.asin}|${a.paese}`];
    if (S.bozza.mancanti?.includes(a.asin) && !a.modello) return { cls: "attenzione", t: "Serve il modello" };
    if (a.modello) return { cls: "info", t: "Modello a mano (solo se Amazon non basta)" };
    if (noto && noto.modello) return { cls: "ok", t: `Già cercato: ${noto.modello}` };
    return { cls: "", t: "Letto da Amazon" };
  }

  function passoAsin(box) {
    const b = S.bozza;
    S.filtroAsin = S.filtroAsin || "";
    box.innerHTML = `
      <section class="scheda">
        <div class="scheda-testa">
          <div><h2>Quali TV vuoi confrontare?</h2>
          <p class="tenue">Incolla ASIN o link Amazon in qualsiasi formato: uno per riga, separati da virgole o copiati da Excel. Il paese si legge dal link (amazon.de → Germania) o dalla riga, altrimenti vale quello predefinito.</p></div>
        </div>
        <div class="griglia-2 asin-griglia">
          <div class="asin-input">
            <div class="paese-scelta" role="radiogroup" aria-label="Paese predefinito">
              <span class="tenue piccolo">Paese predefinito</span>
              ${T.paesi.map((p) => `<button type="button" role="radio" aria-checked="${p.codice === b.paeseDefault}" class="${p.codice === b.paeseDefault ? "attivo" : ""}" data-pd="${p.codice}" title="${p.nome}">${p.bandiera} ${p.codice}</button>`).join("")}
            </div>
            <div class="incolla">
              <textarea id="taAsin" placeholder="Incolla qui: B0F457MQCQ, B0F4548TCQ;DE oppure https://www.amazon.it/dp/B0F45BLD1H" aria-label="ASIN o link Amazon"></textarea>
              <div class="anteprima" id="anteprima" aria-live="polite"></div>
            </div>
            <div class="riga-strumenti">
              <button class="btn primario" type="button" id="btnAggiungi" disabled>Aggiungi</button>
              <label class="btn" for="fileAsin">${ICONE.carica} Carica file</label>
              <input type="file" id="fileAsin" accept=".csv,.txt,.xlsx,.xls" hidden>
              ${b.asin.length ? "" : '<button class="btn fantasma piccolo" type="button" id="btnEsempio">Prova con 2 esempi</button>'}
            </div>
            <div class="dropzona" id="drop" aria-hidden="true">${ICONE.carica}<span>Oppure trascina qui un CSV o un Excel: leggo tutti gli ASIN che contiene</span></div>
          </div>
          <div>
            <div class="lista-testa">
              <div><div class="contatore" id="contaAsin">${b.asin.length}</div><span class="tenue piccolo">ASIN nella ricerca${b.asin.length ? ` · ${[...new Set(b.asin.map((a) => a.paese))].map((c) => paese(c).bandiera).join(" ")}` : ""}</span></div>
              ${b.asin.length ? `<div class="lista-strumenti">
                ${b.asin.length > 6 ? `<input type="search" id="filtroAsin" placeholder="Filtra" value="${esc(S.filtroAsin)}" aria-label="Filtra ASIN" style="width:120px">` : ""}
                <select id="paeseTutti" aria-label="Paese per tutti" style="width:auto"><option value="">Paese per tutti…</option>${T.paesi.map((p) => `<option value="${p.codice}">${p.bandiera} ${p.nome}</option>`).join("")}</select>
                <button class="btn fantasma piccolo" type="button" id="btnSvuota">Svuota</button></div>` : ""}
            </div>
            ${b.asin.length ? `<div class="lista-asin" id="listaAsin"></div>
              <p class="tenue piccolo" style="margin-top:10px">Il modello è facoltativo: se lo scrivi il motore salta Amazon (utile quando Amazon blocca). I modelli trovati vengono ricordati.</p>`
              : `<div class="vuoto vuoto-asin"><div class="tv-anim" aria-hidden="true">${ICONE.tv}</div><p class="tenue">La lista è vuota. Incolla gli ASIN qui accanto, carica un file o prova con gli esempi.</p></div>`}
          </div>
        </div>
      </section>`;
    const ta = document.getElementById("taAsin"), btnAgg = document.getElementById("btnAggiungi"), ant = document.getElementById("anteprima");
    const aggiornaAnteprima = () => {
      const l = estraiAsin(ta.value, b.paeseDefault);
      const presenti = new Set(b.asin.map((a) => a.asin + a.paese));
      const nuovi = l.filter((a) => !presenti.has(a.asin + a.paese));
      btnAgg.disabled = !nuovi.length;
      btnAgg.textContent = nuovi.length ? `Aggiungi ${nuovi.length} ASIN` : "Aggiungi";
      if (!ta.value.trim()) { ant.innerHTML = ""; return; }
      ant.innerHTML = l.length
        ? `${l.slice(0, 24).map((a, k) => `<span class="chip-asin ${presenti.has(a.asin + a.paese) ? "doppio" : ""}" style="--k:${k}">${paese(a.paese).bandiera} ${a.asin}</span>`).join("")}${l.length > 24 ? `<span class="tenue piccolo">+${l.length - 24}</span>` : ""}
           <span class="tenue piccolo anteprima-nota">${nuovi.length} nuovi${l.length - nuovi.length ? ` · ${l.length - nuovi.length} già in lista` : ""}</span>`
        : '<span class="tenue piccolo">Nessun ASIN riconosciuto: un ASIN inizia con B0 ed è lungo 10 caratteri.</span>';
    };
    ta.oninput = aggiornaAnteprima;
    ta.onkeydown = (e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey) && !btnAgg.disabled) btnAgg.click(); };
    box.querySelectorAll("[data-pd]").forEach((x) => (x.onclick = () => {
      b.paeseDefault = x.dataset.pd; salvaBozza();
      box.querySelectorAll("[data-pd]").forEach((y) => { y.classList.toggle("attivo", y === x); y.setAttribute("aria-checked", y === x); });
      aggiornaAnteprima();
    }));
    btnAgg.onclick = () => { if (aggiungiAsin(estraiAsin(ta.value, b.paeseDefault))) vistaNuova(); };
    const es = document.getElementById("btnEsempio");
    if (es) es.onclick = () => { ta.value = "https://www.amazon.it/dp/B0F45BLD1H\nB0H448LDSH;IT"; aggiornaAnteprima(); ta.focus(); };
    const s2 = document.getElementById("btnSvuota");
    if (s2) s2.onclick = () => { if (confirm("Svuotare la lista degli ASIN?")) { b.asin = []; delete b.mancanti; salvaBozza(); vistaNuova(); } };
    const pt = document.getElementById("paeseTutti");
    if (pt) pt.onchange = () => { if (pt.value) { b.asin.forEach((a) => (a.paese = pt.value)); salvaBozza(); vistaNuova(); } };
    const disegnaLista = () => {
      const el = document.getElementById("listaAsin");
      if (!el) return;
      const q = S.filtroAsin.trim().toUpperCase();
      el.innerHTML = b.asin.map((a, i) => ({ a, i })).filter(({ a }) => !q || (a.asin + " " + a.modello).toUpperCase().includes(q)).map(({ a, i }) => {
        const st = statoAsin(a);
        return `
        <div class="riga-asin ${a._nuovo ? "nuova" : ""} ${st.cls === "attenzione" ? "manca" : ""}" style="--k:${Math.min(i, 12)}">
          <select data-i="${i}" data-campo="paese" aria-label="Paese di ${esc(a.asin)}">${T.paesi.map((p) => `<option value="${p.codice}" ${p.codice === a.paese ? "selected" : ""}>${p.bandiera} ${p.codice}</option>`).join("")}</select>
          <a class="codice-asin" href="https://www.${AMZ_DI[a.paese] || "amazon.it"}/dp/${esc(a.asin)}" target="_blank" rel="noopener" title="Apri su Amazon">${esc(a.asin)}</a>
          <input type="text" data-i="${i}" data-campo="modello" value="${esc(a.modello)}" placeholder="${st.cls === "attenzione" ? "scrivi il modello" : "Modello (facoltativo)"}" aria-label="Modello di ${esc(a.asin)}">
          <span class="chip ${st.cls}">${st.t}</span>
          <button class="btn fantasma piccolo" type="button" data-rimuovi="${i}" aria-label="Rimuovi ${esc(a.asin)}">✕</button>
        </div>`;
      }).join("") || '<p class="tenue piccolo" style="padding:12px">Nessun ASIN corrisponde al filtro.</p>';
      b.asin.forEach((a) => delete a._nuovo);
      el.querySelectorAll("[data-rimuovi]").forEach((x) => (x.onclick = () => {
        const riga = x.closest(".riga-asin"); riga.classList.add("via");
        setTimeout(() => { b.asin.splice(Number(x.dataset.rimuovi), 1); salvaBozza(); vistaNuova(); }, 180);
      }));
      el.querySelectorAll("[data-campo]").forEach((x) => (x.onchange = () => {
        const v = x.dataset.campo === "modello" ? x.value.trim().toUpperCase() : x.value;
        b.asin[Number(x.dataset.i)][x.dataset.campo] = v; salvaBozza();
        if (x.dataset.campo === "paese") vistaNuova(); else disegnaLista();
      }));
    };
    const fa = document.getElementById("filtroAsin");
    if (fa) fa.oninput = rimbalzo((e) => { S.filtroAsin = e.target.value; disegnaLista(); }, 120);
    disegnaLista();
    const drop = document.getElementById("drop"), file = document.getElementById("fileAsin"), zona = box.querySelector(".asin-input");
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
      if (aggiungiAsin(l)) vistaNuova();
    };
    file.onchange = () => leggiFile(file.files[0]);
    zona.ondragover = (e) => { e.preventDefault(); drop.classList.add("sopra"); };
    zona.ondragleave = (e) => { if (!zona.contains(e.relatedTarget)) drop.classList.remove("sopra"); };
    zona.ondrop = (e) => { e.preventDefault(); drop.classList.remove("sopra"); leggiFile(e.dataTransfer.files[0]); };
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
  const testoVoce = (v, P) => (typeof v.testo === "string" ? v.testo : v.testo[P.modalita] || "");
  const nomeModalita = (P) => (T.modalita.find((m) => m.valore === P.modalita) || T.modalita[0]).titolo;
  const LIVELLI = {
    stretto: { titolo: "Stretto", testo: "Pochi risultati, molto vicini", imposta: (P) => {
      Object.assign(P.pollici, { attivo: true, tolleranza: 0 }); ["famiglia", "tecnologia", "risoluzione", "refresh", "pro"].forEach((k) => (P[k].attivo = true));
      Object.assign(P.anno, { attivo: true, accetta_ignoto: false }); } },
    bilanciato: { titolo: "Bilanciato", testo: "Consigliato: le regole del documento", imposta: (P) => {
      Object.assign(P.pollici, { attivo: true, tolleranza: 0 }); ["famiglia", "tecnologia", "risoluzione", "refresh", "pro"].forEach((k) => (P[k].attivo = true));
      Object.assign(P.anno, { attivo: true, accetta_ignoto: true }); } },
    largo: { titolo: "Largo", testo: "Più risultati, anche meno simili", imposta: (P) => {
      Object.assign(P.pollici, { attivo: true, tolleranza: 3 }); ["famiglia", "tecnologia", "risoluzione"].forEach((k) => (P[k].attivo = true));
      P.refresh.attivo = false; P.pro.attivo = false; P.anno.attivo = false; } },
  };
  function livelloDi(P) {
    for (const [k, l] of Object.entries(LIVELLI)) {
      const prova = normalizzaParametri(clona(P)); l.imposta(prova);
      const chiavi = ["pollici", "famiglia", "tecnologia", "risoluzione", "refresh", "pro", "anno"];
      if (chiavi.every((c) => JSON.stringify(prova[c]) === JSON.stringify(P[c]))) return k;
    }
    return "personalizzato";
  }
  function frase(P) {
    if (P.ricerca === "identico") return "Cerca <strong>lo stesso modello</strong> della TV Amazon: stesso codice, anche con le varianti di paese o di canale (es. QE55Q7FAAUXZT = QE55Q7FAATXZT), stessa diagonale. Se il negozio indica un anno diverso da Amazon, il risultato lo segnala.";
    const conc = P.modalita === "concorrente";
    const parti = [conc ? "TV di <strong>altre marche</strong>" : "TV della <strong>stessa marca</strong> con codice diverso"];
    if (P.pollici.attivo) parti.push(P.pollici.tolleranza ? `diagonale entro <strong>±${P.pollici.tolleranza}"</strong>` : "<strong>stessa diagonale</strong>");
    if (P.tecnologia.attivo) parti.push("stessa <strong>tecnologia</strong>");
    if (P.famiglia.attivo) parti.push(conc ? "<strong>fascia</strong> uguale o vicina" : "stessa <strong>famiglia</strong>");
    if (P.risoluzione.attivo) parti.push("stessa risoluzione");
    if (P.refresh.attivo) parti.push("stessa frequenza");
    if (P.anno.attivo) parti.push(`${P.anno.modo === "fisso" ? `anno <strong>${P.anno.valore}</strong>` : "<strong>stesso anno</strong> della TV Amazon"}${P.anno.accetta_ignoto ? " (o non indicato)" : ""}`);
    if (!conc && P.pro.attivo) parti.push("PRO solo con PRO");
    return "Cerco " + parti.join(", ") + ".";
  }
  function passoParametri(box) {
    const P = S.bozza.parametri;
    const preset = S.impostazioni.preset || [];
    const sw = (k, on) => `<label class="switch"><input type="checkbox" data-on="${k}" ${on ? "checked" : ""} aria-label="Attiva ${k}"><span></span></label>`;
    const controllo = (v) => {
      const p = P[v.chiave];
      if (v.controllo === "tolleranza") return `<div class="controlli"><label class="campo" style="grid-auto-flow:column;align-items:center">Tolleranza ±<input type="number" min="0" max="20" step="1" data-num="pollici.tolleranza" value="${p.tolleranza}"> pollici</label><span class="tenue piccolo">0 = stessa diagonale</span></div>`;
      if (v.controllo === "anno") return `<div class="controlli"><label class="campo" style="grid-auto-flow:column;align-items:center">Anno<select data-anno-modo><option value="asin" ${p.modo !== "fisso" ? "selected" : ""}>Stesso della TV Amazon</option><option value="fisso" ${p.modo === "fisso" ? "selected" : ""}>Anno fisso</option></select></label>
        <label class="campo" style="grid-auto-flow:column;align-items:center">${p.modo === "fisso" ? "Anno fisso" : "Se l'anno Amazon non si ricava"}<input type="number" min="2020" max="2035" data-num="anno.valore" value="${p.valore}"></label>
        <label class="check"><input type="checkbox" data-bool="anno.accetta_ignoto" ${p.accetta_ignoto ? "checked" : ""}> Accetta i modelli con anno non ricavabile (segnalati "da verificare")</label></div>`;
      if (v.controllo === "equivalenze") return `<div class="controlli"><span class="tenue piccolo">Considera equivalenti:</span>
        ${(p.equivalenze || []).map((g, gi) => `<span class="chip info">${g.map((t) => T.nomeTecnologia[t] || t).join(" = ")} <button type="button" class="btn fantasma piccolo" data-togli-eq="${gi}" aria-label="Rimuovi equivalenza" style="padding:0 4px">✕</button></span>`).join("") || '<span class="chip">nessuna</span>'}
        <span class="equiv"><select id="eqA" style="width:auto">${T.tecnologie.map((t) => `<option value="${t}">${T.nomeTecnologia[t]}</option>`).join("")}</select> = <select id="eqB" style="width:auto">${T.tecnologie.map((t, i) => `<option value="${t}" ${i === 2 ? "selected" : ""}>${T.nomeTecnologia[t]}</option>`).join("")}</select>
        <button class="btn piccolo" type="button" id="eqAgg">Aggiungi</button></span></div>`;
      if (v.controllo === "regole") return `<p class="piccolo" style="margin-top:8px">Famiglie e fasce di ogni marca si vedono e si modificano nel <a href="#/catalogo">Catalogo</a>.</p>`;
      return "";
    };
    const liv = livelloDi(P);
    box.innerHTML = `
      <section class="scheda">
        <h2>Tipo di ricerca</h2>
        <div class="modalita" role="radiogroup" aria-label="Tipo di ricerca">
          ${[["identico", "=", "Stesso modello", "Cerca nei negozi esattamente il modello Amazon, con il suo codice"], ["simile", "≈", "Modello simile", "Cerca un modello simile per caratteristiche, con le regole qui sotto"]].map(([v, ic, t, d]) => `
            <label class="modalita-opz ${(P.ricerca || "simile") === v ? "scelta" : ""}">
              <input type="radio" name="ricerca" value="${v}" ${(P.ricerca || "simile") === v ? "checked" : ""}>
              <span class="modalita-icona" aria-hidden="true">${ic}</span>
              <strong>${t}</strong><span>${d}</span>
            </label>`).join("")}
        </div>
        ${P.ricerca === "identico" ? `<p class="frase-criteri" id="fraseCriteri">${frase(P)}</p>` : `
        <h3 style="margin-top:26px">Cosa cerchi?</h3>
        <div class="modalita" role="radiogroup" aria-label="Modalità di ricerca">
          ${T.modalita.map((m) => `
            <label class="modalita-opz ${P.modalita === m.valore ? "scelta" : ""}">
              <input type="radio" name="modalita" value="${m.valore}" ${P.modalita === m.valore ? "checked" : ""}>
              <span class="modalita-icona" aria-hidden="true">${m.valore === "concorrente" ? "⇄" : "↻"}</span>
              <strong>${m.titolo}</strong><span>${m.testo}</span>
            </label>`).join("")}
        </div>
        <h3 style="margin-top:26px">Quanto devono essere simili?</h3>
        <div class="livelli" role="radiogroup" aria-label="Livello di somiglianza">
          ${Object.entries(LIVELLI).map(([k, l], i) => `
            <button type="button" role="radio" aria-checked="${liv === k}" class="livello ${liv === k ? "scelto" : ""}" data-liv="${k}">
              <span class="livello-barre" aria-hidden="true">${[0, 1, 2].map((j) => `<i class="${j <= 2 - i ? "on" : ""}"></i>`).join("")}</span>
              <strong>${l.titolo}</strong><span class="tenue piccolo">${l.testo}</span>
            </button>`).join("")}
        </div>
        <p class="frase-criteri" id="fraseCriteri">${frase(P)}${liv === "personalizzato" ? ' <span class="chip attenzione">personalizzato</span>' : ""}</p>`}
      </section>
      <details class="scheda avanzate" ${liv === "personalizzato" || S.avanzateAperte ? "open" : ""} id="avanzate">
        <summary><h3 style="display:inline">Personalizza i criteri</h3> <span class="tenue piccolo">interruttori singoli, preset salvati, opzioni dei risultati</span></summary>
        <div class="preset-barra" style="margin-top:14px">
          <select id="selPreset" aria-label="Preset salvati">
            <option value="">Impostazioni personalizzate</option>
            <option value="__std">Standard (regole del documento)</option>
            ${preset.map((p, i) => `<option value="${i}" ${S.bozza.preset === String(i) ? "selected" : ""}>${esc(p.nome)}</option>`).join("")}
          </select>
          <button class="btn piccolo" type="button" id="salvaPreset">Salva come preset</button>
          ${S.bozza.preset !== "" && S.bozza.preset !== "__std" && preset[S.bozza.preset] ? '<button class="btn fantasma piccolo pericolo" type="button" id="eliminaPreset">Elimina preset</button>' : ""}
        </div>
      ${P.ricerca === "identico" ? "" : T.parametriInfo.map((g) => `
        <section class="gruppo-param">
          <h3>${g.gruppo}</h3>${g.nota ? `<p class="tenue piccolo">${g.nota}</p>` : ""}
          ${g.voci.filter((v) => !v.solo || v.solo === P.modalita).map((v) => `
            <div class="param ${P[v.chiave].attivo ? "" : "spento"}">
              ${sw(v.chiave, P[v.chiave].attivo)}
              <div><h4>${v.titolo}</h4><p>${testoVoce(v, P)}</p>${P[v.chiave].attivo ? controllo(v) : ""}</div>
            </div>`).join("")}
        </section>`).join("")}
      <section class="gruppo-param">
        <h3>Risultati</h3>
        <div class="opz-avanzate" style="margin-top:14px">
          <label class="campo">Modelli simili da mostrare per ogni marketplace
            <select data-num="max_match"><option value="1" ${P.max_match == 1 ? "selected" : ""}>1, il più vicino</option><option value="2" ${P.max_match == 2 ? "selected" : ""}>Fino a 2</option><option value="3" ${P.max_match == 3 ? "selected" : ""}>Fino a 3</option></select>
          </label>
          <div class="param" style="grid-template-columns:auto 1fr;padding:12px">
            <label class="switch"><input type="checkbox" data-bool="verifica_url" ${P.verifica_url ? "checked" : ""} aria-label="Verifica pagina prodotto"><span></span></label>
            <div><h4>Verifica la pagina prodotto</h4><p>Apre ogni link scelto: controlla che sia attivo e legge anno e caratteristiche. Più lento ma più affidabile.</p></div>
          </div>
          <div class="param" style="grid-template-columns:auto 1fr;padding:12px">
            <label class="switch"><input type="checkbox" data-bool="ponte_idealo" ${P.ponte_idealo ? "checked" : ""} aria-label="Usa idealo come ponte"><span></span></label>
            <div><h4>Se un sito blocca la ricerca, usa un comparatore</h4><p>Cerca il modello simile su idealo (nel Regno Unito su PriceRunner) e tiene solo le offerte di quel retailer. Il risultato è segnalato come trovato tramite servizio terzo.</p></div>
          </div>
        </div>
      </section>
      </details>`;
    document.getElementById("avanzate").addEventListener("toggle", (e) => { S.avanzateAperte = e.target.open; });
    box.querySelectorAll("[data-liv]").forEach((x) => (x.onclick = () => { LIVELLI[x.dataset.liv].imposta(P); cambia(); }));
    const cambia = () => { S.bozza.preset = ""; salvaBozza(); passoParametri(box); };
    const imposta = (path, val) => { const [a, b] = path.split("."); if (b) P[a][b] = val; else P[a] = val; };
    box.querySelectorAll('input[name="modalita"]').forEach((x) => (x.onchange = () => { P.modalita = x.value; cambia(); }));
    box.querySelectorAll('input[name="ricerca"]').forEach((x) => (x.onchange = () => { P.ricerca = x.value; cambia(); }));
    box.querySelectorAll("[data-on]").forEach((x) => (x.onchange = () => { P[x.dataset.on].attivo = x.checked; cambia(); }));
    box.querySelectorAll("[data-num]").forEach((x) => (x.onchange = () => { imposta(x.dataset.num, Number(x.value)); cambia(); }));
    box.querySelectorAll("[data-bool]").forEach((x) => (x.onchange = () => { imposta(x.dataset.bool, x.checked); cambia(); }));
    box.querySelectorAll("[data-anno-modo]").forEach((x) => (x.onchange = () => { P.anno.modo = x.value; cambia(); }));
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
      else if (v !== "") S.bozza.parametri = normalizzaParametri(clona(preset[Number(v)].parametri));
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
    // misurato: ~12 ASIN per macchina, fino a 8 macchine in parallelo; ~15 s per coppia ASIN×negozio su ogni macchina
    const parti = Math.max(1, Math.min(8, Math.ceil(coperti.length / 12)));
    const perParte = Math.ceil(coperti.length / parti), negoziMedi = coppie / Math.max(1, coperti.length);
    const minuti = Math.max(3, Math.round(3 + perParte * negoziMedi * 0.25));
    const attivi = T.parametriInfo.flatMap((g) => g.voci).filter((v) => P[v.chiave].attivo && (!v.solo || v.solo === P.modalita));
    if (!b.nome) b.nome = `Ricerca ${new Date().toLocaleDateString("it-IT", { month: "long", year: "numeric" })}`;
    box.innerHTML = `
      <section class="scheda">
        <h2>Tutto pronto</h2>
        <p class="tenue" style="margin-top:6px">Il motore gira su GitHub: puoi chiudere la pagina, cambiare dispositivo o perdere la connessione. Ritrovi la ricerca nello <a href="#/esecuzioni">Storico</a>.</p>
        <label class="campo" style="margin-top:20px">Nome della ricerca<input type="text" id="nomeRicerca" maxlength="80" value="${esc(b.nome)}"></label>
        <div class="riepilogo">
          <div><strong>${coperti.length}</strong><span class="tenue piccolo">ASIN da confrontare${coperti.length < b.asin.length ? ` (${b.asin.length - coperti.length} senza marketplace)` : ""}</span></div>
          <div><strong>${ret.length}</strong><span class="tenue piccolo">marketplace in ${[...new Set(ret.map((r) => r.paese))].map((c) => paese(c).bandiera).join(" ")}</span></div>
          <div><strong>~${minuti} min</strong><span class="tenue piccolo">durata stimata${parti > 1 ? ` · ${parti} parti in parallelo` : ""}</span></div>
        </div>
        <p class="piccolo tenue">Modalità: <span class="chip info">${nomeModalita(P)}</span></p>
        <p class="piccolo tenue">Criteri attivi: ${attivi.map((v) => `<span class="chip">${v.titolo}${v.chiave === "pollici" && P.pollici.tolleranza ? ` ±${P.pollici.tolleranza}"` : ""}${v.chiave === "anno" ? (P.anno.modo === "fisso" ? ` ${P.anno.valore}` : " = Amazon") : ""}</span>`).join(" ") || "nessuno"}</p>
        <div style="margin-top:26px;display:flex;gap:12px;flex-wrap:wrap;align-items:center">
          <button class="btn primario grande" type="button" id="btnAvvia" ${coperti.length ? "" : "disabled"}>${ICONE.play} Avvia la ricerca</button>
          <span class="tenue piccolo" id="msgAvvio"></span>
        </div>
      </section>`;
    document.getElementById("nomeRicerca").oninput = (e) => { b.nome = e.target.value; salvaBozza(); };
    document.getElementById("btnAvvia").onclick = async (e) => {
      const btn = e.currentTarget;
      btn.disabled = true;
      const anim = animazioneAvvio(coperti.length, ret.length);
      try {
        const { id } = await api("run", { metodo: "POST", corpo: {
          nome: b.nome, retailer: ret, parametri: P,
          asin: coperti.map((a) => ({ asin: a.asin, paese: a.paese, ...(a.modello ? { modello: a.modello } : {}) })),
        } });
        const recenti = memoria.leggi("recenti", []);
        memoria.scrivi("recenti", [id, ...recenti].slice(0, 20));
        await anim.ok();
        ultimoControllo = 0;
        location.hash = `#/run/${id}`;
      } catch (err) {
        anim.errore(err.message);
        btn.disabled = false;
        document.getElementById("msgAvvio").textContent = err.message;
      }
    };
    piedePasso(box, { avanti: false });
  }

  // animazione a schermo intero mentre la ricerca viene inviata a GitHub
  function animazioneAvvio(nAsin, nRet) {
    const lento = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const el = document.createElement("div");
    el.className = "avvio-sfondo";
    el.setAttribute("role", "status");
    const fasi = ["Preparo la configurazione", `Invio ${nAsin} ASIN e ${nRet} marketplace`, "Accendo il motore su GitHub"];
    el.innerHTML = `
      <div class="avvio">
        <div class="avvio-tv" aria-hidden="true">
          <div class="schermo">${["#FFD23F", "#2EE6F0", "#4BE38E", "#FF4FA3", "#7B61FF"].map((c, k) => `<i style="--c:${c};--k:${k}"></i>`).join("")}<span class="scansione"></span></div>
          <div class="piede-tv"></div>
        </div>
        <h2 id="avvioTitolo">Avvio la ricerca…</h2>
        <ol class="avvio-fasi">${fasi.map((f, k) => `<li data-f="${k}"><span class="spunta"></span>${f}</li>`).join("")}</ol>
      </div>`;
    document.body.appendChild(el);
    requestAnimationFrame(() => el.classList.add("visibile"));
    let fase = 0;
    const segna = () => { const li = el.querySelector(`[data-f="${fase}"]`); if (li) li.classList.add("fatto"); fase++; };
    const t = setInterval(() => { if (fase < fasi.length - 1) segna(); }, lento ? 650 : 50);
    const inizio = Date.now();
    const chiudi = () => { el.classList.remove("visibile"); setTimeout(() => el.remove(), 350); };
    return {
      async ok() {
        await new Promise((r) => setTimeout(r, Math.max(0, (lento ? 1900 : 200) - (Date.now() - inizio))));
        clearInterval(t);
        while (fase < fasi.length) segna();
        el.classList.add("partita");
        el.querySelector("#avvioTitolo").textContent = "Ricerca partita!";
        if (lento) el.querySelector(".avvio").insertAdjacentHTML("beforeend", `<div class="coriandoli" aria-hidden="true">${Array.from({ length: 22 }, (_, k) => `<i style="--k:${k};--c:${["#FFD23F", "#2EE6F0", "#4BE38E", "#FF4FA3", "#7B61FF"][k % 5]}"></i>`).join("")}</div>`);
        await new Promise((r) => setTimeout(r, lento ? 1100 : 100));
        chiudi();
      },
      errore(msg) { clearInterval(t); chiudi(); toast("Avvio non riuscito: " + msg, "errore"); },
    };
  }

  // contatori che salgono fino al valore
  function animaNumeri(box) {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    box.querySelectorAll("[data-num-anim]").forEach((el) => {
      const fine = Number(el.dataset.numAnim), suff = el.dataset.suff || "", t0 = performance.now(), dur = 700;
      if (!fine) return;
      const passo = (t) => { const p = Math.min(1, (t - t0) / dur), v = Math.round(fine * (1 - Math.pow(1 - p, 3))); el.textContent = v + suff; if (p < 1) requestAnimationFrame(passo); };
      requestAnimationFrame(passo);
    });
  }

  // ------------------------------------------------------------------ esecuzione e risultati
  const filtri = { testo: "", paese: "", retailer: "", esito: "" };

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
    S.runAttuale = id;
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
      const prima = S.codPrecedente;
      disegnaRun(id, dati, st, primo);
      if (!primo && ["corso", "coda"].includes(prima) && st.cod === "completato") {
        toast("Ricerca completata", "ok");
        document.getElementById("runPagina")?.classList.add("festa");
      }
      S.codPrecedente = st.cod;
      primo = false;
      if (["completato", "errore", "annullato"].includes(st.cod)) { clearInterval(S.polling); aggiornaPill(true); }
    };
    await ciclo();
    S.polling = setInterval(() => { if (!document.hidden) ciclo(); }, 6000);
  }

  function disegnaRun(id, dati, st, primo) {
    const s = dati.stato || {}, gh = dati.github || {};
    S.statoRun = s; // i pulsanti leggono sempre l'ultimo stato ricevuto
    S.ricercaIdentica = (s.config?.parametri?.ricerca === "identico");
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
      document.getElementById("motoreVivo").hidden = !inCorso;
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
          <div class="motore-vivo" id="motoreVivo" ${inCorso ? "" : "hidden"} aria-hidden="true"><span class="radar"><i></i></span><span class="tenue piccolo">Il motore sta cercando sui siti dei retailer…</span></div>
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
      S.bozza = { asin: c.asin.map((a) => ({ modello: "", ...a })), nome: "", paeseDefault: c.asin[0]?.paese || "IT", parametri: normalizzaParametri(c.parametri), preset: "" };
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
        parametri: normalizzaParametri(s.config?.parametri), preset: "",
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
    const pos = ris.reduce((n, r) => n + Object.values(r.match || {}).filter((m) => m.length).length, 0);
    const perc = copertura ? Math.round((pos / copertura) * 100) : 0;
    // esiti per marketplace: barra impilata
    const GRUPPI = [["trovato", "Trovato", "ok"], ["nessun_simile", "Nessun simile", "medio"], ["non_presente", "Non presente", "neutro"], ["errore", "Non leggibile", "errore"], ["saltato", "Saltato", "spento"]];
    const gruppo = (e) => (e === "illeggibile" ? "errore" : e || "saltato");
    const perRet = retNomi.filter((x) => ris.some((r) => r.paese === x.paese)).map((x) => {
      const c = {}; ris.filter((r) => r.paese === x.paese).forEach((r) => { const g = gruppo((r.esito || {})[x.nome] || (r.errore ? "saltato" : "")); if ((r.esito || {})[x.nome] || r.errore) c[g] = (c[g] || 0) + 1; });
      return { r: x, c, tot: Object.values(c).reduce((a2, b2) => a2 + b2, 0) };
    });
    box.innerHTML = `
      <div class="kpi">
        <div><strong><span data-num-anim="${ris.length}">${ris.length}</span>${inCorso ? `<span class="tenue" style="font-size:1rem">/${s.config?.asin?.length || "?"}</span>` : ""}</strong><span class="tenue piccolo">ASIN elaborati</span></div>
        <div><strong data-num-anim="${conMatch}">${conMatch}</strong><span class="tenue piccolo">con almeno un modello simile</span></div>
        <div><strong data-num-anim="${totMatch}">${totMatch}</strong><span class="tenue piccolo">modelli simili trovati</span></div>
        <div class="kpi-anello"><svg viewBox="0 0 36 36" aria-hidden="true"><circle cx="18" cy="18" r="15.9" class="anello-fondo"/><circle cx="18" cy="18" r="15.9" class="anello-valore" style="--p:${perc}"/></svg><div><strong data-num-anim="${perc}" data-suff="%">${perc}%</strong><span class="tenue piccolo">confronti con esito positivo</span></div></div>
      </div>
      ${perRet.length ? `<section class="scheda grafico-ret">
        <div class="grafico-testa"><h3>Esiti per marketplace</h3>
          <span class="legenda">${GRUPPI.filter(([g]) => perRet.some((x) => x.c[g])).map(([g, n, cl]) => `<span><i class="seg-${cl}"></i>${n}</span>`).join("")}</span></div>
        ${perRet.map((x) => `
          <button type="button" class="riga-ret ${filtri.retailer === x.r.nome ? "attiva" : ""}" data-filtra-ret="${esc(x.r.nome)}" title="Mostra solo ${esc(x.r.nome)}">
            <span class="nome-ret">${paese(x.r.paese).bandiera} ${esc(x.r.nome)}</span>
            <span class="barra-imp">${GRUPPI.filter(([g]) => x.c[g]).map(([g, n, cl]) => `<i class="seg-${cl}" style="--w:${(x.c[g] / Math.max(1, x.tot)) * 100}%" title="${n}: ${x.c[g]}"></i>`).join("")}</span>
            <span class="tenue piccolo num-ret">${x.c.trovato || 0}/${x.tot}</span>
          </button>`).join("")}
      </section>` : ""}
      <div class="filtri">
        <input type="search" id="fTesto" placeholder="Cerca ASIN o modello" value="${esc(filtri.testo)}" aria-label="Cerca">
        ${paesiR.length > 1 ? `<select id="fPaese"><option value="">Tutti i paesi</option>${paesiR.map((c) => `<option value="${c}" ${filtri.paese === c ? "selected" : ""}>${paese(c).bandiera} ${paese(c).nome}</option>`).join("")}</select>` : ""}
        <select id="fRet"><option value="">Tutti i marketplace</option>${retNomi.map((r) => `<option ${filtri.retailer === r.nome ? "selected" : ""}>${esc(r.nome)}</option>`).join("")}</select>
        <span class="segmenti" role="group" aria-label="Filtra per esito">
          ${[["", "Tutti"], ["match", "Con simili"], ["nomatch", "Senza"], ["errori", "Da verificare"]].map(([v, n]) => `<button type="button" data-fe="${v}" class="${filtri.esito === v ? "attivo" : ""}">${n}</button>`).join("")}
        </span>
        <span style="margin-left:auto" class="segmenti" role="group" aria-label="Vista">
          <button type="button" data-vista="schede" class="${S.vistaRisultati === "schede" ? "attivo" : ""}">Schede</button>
          <button type="button" data-vista="tabella" class="${S.vistaRisultati === "tabella" ? "attivo" : ""}">Tabella</button>
        </span>
      </div>
      <div id="elencoRis"></div>`;
    animaNumeri(box);
    box.querySelectorAll(".kpi > div").forEach((d, i) => d.style.setProperty("--i", i));
    requestAnimationFrame(() => box.querySelector(".grafico-ret")?.classList.add("anima"));
    const ridisegna = () => elencoRisultati(document.getElementById("elencoRis"), ris, retNomi);
    document.getElementById("fTesto").oninput = rimbalzo((e) => { filtri.testo = e.target.value; ridisegna(); }, 200);
    const fp = document.getElementById("fPaese"); if (fp) fp.onchange = (e) => { filtri.paese = e.target.value; ridisegna(); };
    document.getElementById("fRet").onchange = (e) => { filtri.retailer = e.target.value; ridisegna(); };
    box.querySelectorAll("[data-fe]").forEach((x) => (x.onclick = () => {
      filtri.esito = x.dataset.fe; box.querySelectorAll("[data-fe]").forEach((y) => y.classList.toggle("attivo", y === x)); ridisegna();
    }));
    box.querySelectorAll("[data-filtra-ret]").forEach((x) => (x.onclick = () => {
      filtri.retailer = filtri.retailer === x.dataset.filtraRet ? "" : x.dataset.filtraRet;
      document.getElementById("fRet").value = filtri.retailer;
      box.querySelectorAll("[data-filtra-ret]").forEach((y) => y.classList.toggle("attiva", y.dataset.filtraRet === filtri.retailer)); ridisegna();
    }));
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
    if (a.fascia) out.push(`Fascia ${T.nomeFascia[a.fascia] || a.fascia}`);
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
      const conSimili = Object.values(m).some((x) => x.length);
      if (filtri.esito === "match" && !conSimili) return false;
      if (filtri.esito === "nomatch" && conSimili) return false;
      if (filtri.esito === "errori" && !(r.errore || Object.values(r.esito || {}).some((e) => e === "errore" || e === "illeggibile") || r.amazon?.fascia_fonte === "stimata" || Object.values(m).flat().some((x) => x.nota || x.via))) return false;
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
              return `<td>${m.length ? m.map((x) => `<a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.modello)}</a>${x.nota ? ` <span class="chip attenzione">${esc(x.nota)}</span>` : ""}`).join("<br>") : `<span class="${e === "errore" ? "chip errore" : "tenue"}">${e ? testoEsito(e) : "—"}</span>`}</td>`;
            }).join("")}
          </tr>`).join("")}</tbody>
        </table></div>`;
      return;
    }
    box.innerHTML = lista.map((r, k) => {
      const a = r.amazon || {};
      return `
        <article class="asin-card" style="--k:${Math.min(k, 10)}">
          <div class="amazon-lato">
            ${foto(a.img, a.modello)}
            <div style="display:flex;justify-content:space-between;gap:8px;align-items:center"><span class="chip">${paese(r.paese).bandiera} Amazon ${esc(r.paese)}</span><a class="piccolo" href="${esc(a.url)}" target="_blank" rel="noopener">${esc(r.asin)}</a></div>
            <div class="modello">${esc(a.modello || "Modello non riconosciuto")}</div>
            <div class="etichette">${etichetteInfo(a)}</div>
            ${a.titolo ? `<p class="titolo-amz">${esc(a.titolo)}</p>` : ""}
            ${r.errore ? `<span class="chip errore" style="white-space:normal">${esc(r.errore === "captcha Amazon" ? "Amazon ha bloccato la lettura (captcha): scrivi il modello e rilancia" : r.errore)}</span>` : ""}
            ${a.marca_nuova ? `<span class="chip attenzione" style="white-space:normal">Marca nuova: ${esc(a.marca)} non è nel catalogo</span>` : ""}
            ${a.fascia_fonte === "stimata" ? `<span class="chip attenzione" style="white-space:normal">Fascia stimata dal prezzo${a.prezzo ? ` (${esc(a.prezzo)})` : ""}</span>` : ""}
            ${!r.errore && a.fonte && !/^Amazon( \(letto[^)]*\))?$/.test(a.fonte) ? `<span class="chip ${a.fonte === "ricerca web" ? "attenzione" : "info"}" style="white-space:normal">${a.fonte === "ricerca web" ? "Modello ricavato dal web: verificalo" : a.fonte.includes("modello inserito") ? "Codice non scritto su Amazon: usato il modello a mano" : a.fonte === "inserito a mano" ? "Amazon non leggibile: usato il modello a mano" : esc(a.fonte)}</span>` : ""}
          </div>
          <div class="match-griglia">
            ${retDi(r).map((ret) => {
              const m = (r.match || {})[ret.nome];
              const es = (r.esito || {})[ret.nome];
              if (es === "saltato" || (m === undefined && r.errore)) return `<div class="match-tile nessuno"><div class="retailer">${esc(ret.nome)}</div><span class="piccolo">Saltato: serve il modello Amazon</span></div>`;
              if (m === undefined) return `<div class="match-tile nessuno"><div class="retailer">${esc(ret.nome)}</div><span>In attesa</span></div>`;
              if (!m.length) {
                const e = (r.esito || {})[ret.nome] || "nessun_simile";
                return `<div class="match-tile nessuno ${e}"><div class="retailer">${esc(ret.nome)}<span class="chip ${e === "errore" || e === "illeggibile" ? "errore" : ""}">${testoEsito(e)}</span></div><span class="piccolo">${ESITI_NOTA[e] || ""}${(r.ponte || {})[ret.nome] ? ` Cercato anche su ${esc(r.ponte[ret.nome])}: nessuna offerta di ${esc(ret.nome)} per un modello simile.` : ""}</span></div>`;
              }
              const [x, ...altri] = m;
              return `
                <div class="match-tile trovato">
                  <div class="retailer"><span>${esc(ret.nome)}</span>${x.via ? `<span class="chip attenzione">via ${esc(x.via)}</span>` : x.nota ? `<span class="chip attenzione">${esc(x.nota)}</span>` : '<span class="chip ok">simile</span>'}</div>
                  ${x.via ? `<p class="piccolo tenue">Il sito di ${esc(ret.nome)} non era leggibile: offerta trovata sul comparatore ${esc(x.via)}${x.prezzo ? ` (${esc(x.prezzo)})` : ""}. Il link passa da ${esc(x.via)}.${x.pagina_comparatore ? ` <a href="${esc(x.pagina_comparatore)}" target="_blank" rel="noopener">Scheda sul comparatore</a>` : ""}</p>` : ""}
                  ${foto(x.img, x.modello)}
                  <div class="modello">${esc(x.modello)}</div>
                  ${x.titolo ? `<p class="titolo-ret" title="${esc(x.titolo)}">${esc(x.titolo)}</p>` : ""}
                  <div class="etichette">${etichetteInfo(x)}</div>
                  <a class="vai" href="${esc(x.url)}" target="_blank" rel="noopener">Apri la pagina prodotto</a>
                  <button type="button" class="segnala" data-segnala="${esc(JSON.stringify({ asin: r.asin, paese: r.paese, negozio: ret.nome, modello: x.modello, link: x.url, amazon: a.modello || "" }))}">Segnala questo abbinamento</button>
                  ${altri.length ? `<div class="altri">Anche: ${altri.map((y) => `<a href="${esc(y.url)}" target="_blank" rel="noopener">${esc(y.modello)}</a>`).join(", ")}</div>` : ""}
                </div>`;
            }).join("") || '<p class="tenue">Nessun marketplace per questo paese.</p>'}
          </div>
        </article>`;
    }).join("");
    box.querySelectorAll("[data-segnala]").forEach((b) => (b.onclick = () => {
      const d = JSON.parse(b.dataset.segnala);
      S.fbBozza = { tipo: "Abbinamento errato", asin: d.asin, paese: d.paese, negozio: d.negozio, modello: d.modello, link: d.link,
        ricerca: S.runAttuale || "", messaggio: `Amazon ${d.amazon || d.asin} → ${d.negozio} ${d.modello}: ` };
      location.hash = "#/feedback";
    }));
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
          return [e && e !== "trovato" ? testoEsito(e) : "", ""];
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
        <div class="barra-storico" id="barraStorico" hidden>
          <label class="check"><input type="checkbox" id="selTutte"> Seleziona tutte le concluse</label>
          <button class="btn piccolo pericolo" type="button" id="btnEliminaSel" disabled>Elimina selezionate</button>
        </div>
        <div id="listaRun"><div class="attesa"><span class="caricamento"></span></div></div>
      </div>`;
    const box = document.getElementById("listaRun"), barra = document.getElementById("barraStorico");
    const sel = new Set();
    let elenco = [];
    const aggiornaBarra = () => {
      const b2 = document.getElementById("btnEliminaSel");
      b2.disabled = !sel.size;
      b2.textContent = sel.size ? `Elimina ${sel.size} ${sel.size === 1 ? "ricerca" : "ricerche"}` : "Elimina selezionate";
      const concluse = elenco.filter((r) => r.status === "completed");
      document.getElementById("selTutte").checked = concluse.length > 0 && concluse.every((r) => sel.has(r.id));
    };
    const elimina = async (ids) => {
      const righe = ids.map((id) => box.querySelector(`[data-run="${CSS.escape(id)}"]`)).filter(Boolean);
      righe.forEach((r) => r.classList.add("in-uscita"));
      try {
        await api("elimina", { metodo: "POST", corpo: { ids } });
        await new Promise((r) => setTimeout(r, 250));
        ids.forEach((id) => sel.delete(id));
        toast(ids.length === 1 ? "Ricerca eliminata" : `${ids.length} ricerche eliminate`, "ok");
        disegna();
      } catch (e) { righe.forEach((r) => r.classList.remove("in-uscita")); toast(e.message, "errore"); }
    };
    const disegna = async () => {
      try {
        const { runs } = await api("runs");
        elenco = runs;
        barra.hidden = !runs.some((r) => r.status === "completed");
        if (!runs.length) {
          box.innerHTML = `<div class="vuoto"><div class="tv-anim" style="width:140px">${ICONE.tv}</div><h2>Ancora nessuna ricerca</h2><p class="tenue">Le ricerche avviate compariranno qui, con lo stato e i risultati.</p><a class="btn primario" href="#/nuova/1">Inizia una ricerca</a></div>`;
          return;
        }
        box.innerHTML = `<div class="lista-run">${runs.map((r, k) => {
          const st = statoRun(null, r), attiva = r.status !== "completed";
          const etichetta = attiva ? (r.status === "queued" ? "In coda" : "In corso") : st.testo;
          return `<div class="run-riga" data-run="${esc(r.id)}" style="--k:${Math.min(k, 12)}">
            <label class="check" title="${attiva ? "Una ricerca in corso non si può eliminare" : "Seleziona"}"><input type="checkbox" data-sel="${esc(r.id)}" ${attiva ? "disabled" : ""} ${sel.has(r.id) ? "checked" : ""} aria-label="Seleziona ${esc(r.nome || r.id)}"></label>
            <a class="run-link" href="#/run/${esc(r.id)}"><strong>${esc(r.nome || r.id)}</strong><span class="tenue piccolo">${dataBreve(r.creato)} · durata ${durata(r.creato, attiva ? null : r.aggiornato)}</span></a>
            <span class="chip ${attiva ? "info" : st.chip}">${attiva ? '<span class="puntino"></span>' : ""}${etichetta}</span>
            <button class="btn fantasma piccolo pericolo" type="button" data-elimina-run="${esc(r.id)}" ${attiva ? "disabled" : ""} aria-label="Elimina ${esc(r.nome || r.id)}" title="Elimina">✕</button>
          </div>`;
        }).join("")}</div>`;
        box.querySelectorAll("[data-sel]").forEach((x) => (x.onchange = () => { if (x.checked) sel.add(x.dataset.sel); else sel.delete(x.dataset.sel); aggiornaBarra(); }));
        box.querySelectorAll("[data-elimina-run]").forEach((x) => (x.onclick = () => {
          const r = runs.find((y) => y.id === x.dataset.eliminaRun);
          if (confirm(`Eliminare "${r?.nome || x.dataset.eliminaRun}"? I risultati non saranno più consultabili.`)) elimina([x.dataset.eliminaRun]);
        }));
        aggiornaBarra();
        if (runs.some((r) => r.status !== "completed")) S.polling = S.polling || setInterval(() => { if (!document.hidden) disegna(); }, 15000);
      } catch (e) {
        box.innerHTML = `<div class="vuoto"><p class="tenue">Non riesco a leggere le ricerche: ${esc(e.message)}</p></div>`;
      }
    };
    document.getElementById("selTutte").onchange = (e) => {
      elenco.filter((r) => r.status === "completed").forEach((r) => (e.target.checked ? sel.add(r.id) : sel.delete(r.id)));
      box.querySelectorAll("[data-sel]:not(:disabled)").forEach((x) => (x.checked = e.target.checked));
      aggiornaBarra();
    };
    document.getElementById("btnEliminaSel").onclick = () => {
      if (sel.size && confirm(`Eliminare ${sel.size} ${sel.size === 1 ? "ricerca" : "ricerche"} dallo storico?`)) elimina([...sel]);
    };
    disegna();
  }

  // ------------------------------------------------------------------ catalogo marche e serie
  const NOMI_FASCIA = { BASE: "Base", ENTRY: "Entry", MID: "Media", PREMIUM: "Premium", TOP: "Top" };
  const TEC_CAT = ["LED", "QLED", "MINILED", "NEOQLED", "OLED"];
  async function caricaCatalogo() {
    if (S.catalogo) return S.catalogo;
    const [def, ut] = await Promise.all([
      fetch("catalogo.json", { cache: "no-store" }).then((r) => r.json()),
      api("catalogo").then((r) => r.utente).catch(() => ({ marche: [] })),
    ]);
    const base = new Map(def.marche.map((m) => [m.marca.toUpperCase(), m]));
    const marche = new Map(def.marche.map((m) => [m.marca.toUpperCase(), clona(m)]));
    (ut.marche || []).forEach((m) => { const k = m.marca.toUpperCase(); if (m.rimossa) marche.delete(k); else marche.set(k, clona(m)); });
    S.catalogo = { def, base, marche: [...marche.values()], rimosse: new Set((ut.marche || []).filter((m) => m.rimossa).map((m) => m.marca.toUpperCase())), sporco: false };
    return S.catalogo;
  }
  const firma = (m) => JSON.stringify({ a: [...(m.alias || [])].sort(), n: m.note || "", f: m.fascia_predefinita || "", t: m.tecnologia_predefinita || "",
    s: (m.serie || []).map((x) => [x.serie, x.tecnologia, x.fascia, x.descrizione || "", x.famiglia || "", x.pro ?? null]) });
  function statoMarca(C, m) {
    const b = C.base.get(m.marca.toUpperCase());
    if (!b) return "nuova";
    return firma(b) === firma(m) ? "" : "modificata";
  }
  // classificazione indicativa di un titolo (stessa logica del motore: alias marca + prefisso più lungo della serie)
  function provaTitolo(C, titolo) {
    const T2 = " " + titolo.toUpperCase().replace(/["”″]/g, " ").replace(/\s+/g, " ") + " ";
    let marca = null, lung = 0;
    C.marche.forEach((m) => [m.marca, ...(m.alias || [])].forEach((a) => {
      const A = a.toUpperCase().replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      if (a.length > lung && new RegExp(`(^|[^A-Z0-9])${A}([^A-Z0-9]|$)`).test(T2)) { marca = m; lung = a.length; }
    }));
    if (!marca) return { esito: "Marca non in catalogo: il motore userà la marca indicata da Amazon e stimerà la fascia dal prezzo." };
    const pro = /\bPRO\b/.test(T2);
    const chiavi = (T2.match(/\b[A-Z]{0,4}\d{2,3}[A-Z]{1,4}\d{0,4}[A-Z0-9]*\b/g) || []).map((c) => c.replace(/^[A-Z]{0,4}?(\d{2,3})/, "")).concat((T2.match(/\bOLED\d{2,3}[A-Z]/g) || []).map((c) => "OLED" + c.slice(-1)));
    let voce = null, punti = -1;
    (marca.serie || []).forEach((v) => {
      const sv = v.serie.toUpperCase(), comp = sv.replace(/ /g, "");
      if (v.pro !== undefined && v.pro !== null && v.pro !== pro) return;
      let p = -1;
      if (chiavi.some((k) => k.startsWith(comp))) p = 100 + comp.length * 2;
      else if ((comp.length >= 4 || sv.includes(" ")) && T2.includes(" " + sv + " ")) p = comp.length;
      else if (T2.includes(" " + sv + " ")) p = comp.length;
      if (p > punti) { voce = v; punti = p; }
    });
    if (voce) return { marca: marca.marca, voce, esito: `${marca.marca} · serie ${voce.serie}${voce.descrizione ? ` (${voce.descrizione})` : ""}` };
    if (marca.fascia_predefinita) return { marca: marca.marca, voce: { tecnologia: marca.tecnologia_predefinita || "?", fascia: marca.fascia_predefinita }, esito: `${marca.marca} · serie non in catalogo: uso la fascia predefinita della marca` };
    return { marca: marca.marca, esito: `${marca.marca} · serie non riconosciuta: aggiungila qui sotto, oppure il motore stimerà la fascia dal prezzo` };
  }

  async function vistaCatalogo() {
    app.innerHTML = `<div class="attesa vista"><span class="caricamento"></span><p class="tenue">Carico il catalogo…</p></div>`;
    let C;
    try { C = await caricaCatalogo(); } catch (e) { app.innerHTML = `<div class="vuoto vista"><p class="tenue">Catalogo non disponibile: ${esc(e.message)}</p></div>`; return; }
    S.filtroCat = S.filtroCat || "";
    app.innerHTML = `
      <div class="vista">
        <div class="intestazione">
          <div><h1>Marche e serie</h1>
          <p class="tenue">Il motore riconosce una TV da marca e serie: qui decidi tecnologia e fascia di ogni serie. Le fasce (Base, Entry, Media, Premium, Top) servono a confrontare marche diverse. Le modifiche valgono per tutte le ricerche successive.</p></div>
          <div style="display:flex;gap:10px;flex-wrap:wrap"><button class="btn" type="button" id="catNuova">+ Nuova marca</button><button class="btn primario" type="button" id="catSalva" disabled>Salva modifiche</button></div>
        </div>
        <section class="scheda prova-titolo">
          <h3>Prova un titolo</h3>
          <p class="tenue piccolo">Incolla il nome di una TV come appare su Amazon o su un retailer: vedi subito come viene classificato (anteprima indicativa).</p>
          <input type="text" id="catProva" placeholder="es. TCL 65C7L SQD-Mini LED 4K 144Hz" value="${esc(S.provaCat || "")}" aria-label="Titolo da provare">
          <div id="catEsito" class="prova-esito" aria-live="polite"></div>
        </section>
        <div class="filtri" style="margin-top:22px">
          <input type="search" id="catFiltro" placeholder="Cerca marca o serie" value="${esc(S.filtroCat)}" aria-label="Cerca nel catalogo">
          <span class="tenue piccolo" id="catConta"></span>
        </div>
        <div id="catLista" class="cat-lista"></div>
      </div>`;
    const lista = document.getElementById("catLista");
    const salva = document.getElementById("catSalva");
    const segnaSporco = () => { C.sporco = true; salva.disabled = false; salva.textContent = "Salva modifiche •"; };
    const opz = (vals, sel, nomi) => vals.map((v) => `<option value="${v}" ${v === sel ? "selected" : ""}>${nomi ? nomi[v] || v : v}</option>`).join("");
    const disegnaProva = () => {
      const t = document.getElementById("catProva").value.trim();
      S.provaCat = t;
      const box = document.getElementById("catEsito");
      if (!t) { box.innerHTML = ""; return; }
      const r = provaTitolo(C, t);
      box.innerHTML = `<span class="prova-riga">${esc(r.esito)}</span>${r.voce ? `<span class="chip info">${esc(T.nomeTecnologia[r.voce.tecnologia] || r.voce.tecnologia)}</span><span class="chip fascia-${(r.voce.fascia || "").toLowerCase()}">Fascia ${esc(NOMI_FASCIA[r.voce.fascia] || r.voce.fascia)}</span>` : ""}`;
    };
    const disegna = () => {
      const q = S.filtroCat.trim().toUpperCase();
      const vis = C.marche.filter((m) => !q || m.marca.toUpperCase().includes(q) || (m.alias || []).some((a) => a.includes(q)) || (m.serie || []).some((x) => x.serie.includes(q) || (x.descrizione || "").toUpperCase().includes(q)));
      document.getElementById("catConta").textContent = `${vis.length} marche · ${vis.reduce((n, m) => n + (m.serie || []).length, 0)} serie`;
      lista.innerHTML = vis.map((m) => {
        const i = C.marche.indexOf(m), st = statoMarca(C, m);
        return `
        <details class="cat-marca" data-m="${i}" ${S.catAperte?.has(m.marca) ? "open" : ""}>
          <summary>
            <span class="cat-nome">${esc(m.marca)}</span>
            ${st ? `<span class="chip ${st === "nuova" ? "ok" : "attenzione"}">${st}</span>` : ""}
            <span class="tenue piccolo">${(m.serie || []).length} serie${m.fascia_predefinita ? ` · predefinita ${esc(NOMI_FASCIA[m.fascia_predefinita])}` : ""}</span>
            <span class="cat-fasce" aria-hidden="true">${["BASE", "ENTRY", "MID", "PREMIUM", "TOP"].map((f) => `<i class="fascia-${f.toLowerCase()}" style="--n:${(m.serie || []).filter((x) => x.fascia === f).length}"></i>`).join("")}</span>
            <span class="freccia" aria-hidden="true"></span>
          </summary>
          <div class="cat-corpo">
            <div class="cat-campi">
              <label class="campo">Nomi alternativi (separati da virgola)<input type="text" data-k="alias" value="${esc((m.alias || []).join(", "))}"></label>
              <label class="campo">Fascia se la serie non è in elenco<select data-k="fascia_predefinita"><option value="">Nessuna (stima dal prezzo)</option>${opz(["BASE", "ENTRY", "MID", "PREMIUM", "TOP"], m.fascia_predefinita, NOMI_FASCIA)}</select></label>
              <label class="campo">Tecnologia predefinita<select data-k="tecnologia_predefinita"><option value="">Dal titolo</option>${opz(TEC_CAT, m.tecnologia_predefinita, T.nomeTecnologia)}</select></label>
              <label class="campo cat-note">Note<input type="text" data-k="note" value="${esc(m.note || "")}"></label>
            </div>
            <div class="matrice-wrap"><table class="cat-tab">
              <thead><tr><th title="Inizio del codice serie, es. QN9 vale per QN90…QN94">Serie</th><th>Descrizione</th><th>Tecnologia</th><th>Fascia</th><th title="Facoltativo: serie con la stessa famiglia sono alternative tra loro">Famiglia</th><th title="Solo per le marche che distinguono i modelli PRO">PRO</th><th></th></tr></thead>
              <tbody>${(m.serie || []).map((x, j) => `
                <tr data-s="${j}">
                  <td><input type="text" data-c="serie" value="${esc(x.serie)}" aria-label="Serie" style="width:96px;text-transform:uppercase"></td>
                  <td><input type="text" data-c="descrizione" value="${esc(x.descrizione || "")}" aria-label="Descrizione"></td>
                  <td><select data-c="tecnologia" aria-label="Tecnologia">${opz(TEC_CAT, x.tecnologia, T.nomeTecnologia)}</select></td>
                  <td><select data-c="fascia" aria-label="Fascia" class="sel-fascia fascia-${(x.fascia || "").toLowerCase()}">${opz(["BASE", "ENTRY", "MID", "PREMIUM", "TOP"], x.fascia, NOMI_FASCIA)}</select></td>
                  <td><input type="text" data-c="famiglia" value="${esc(x.famiglia || "")}" aria-label="Famiglia" style="width:140px"></td>
                  <td><select data-c="pro" aria-label="PRO"><option value="" ${x.pro == null ? "selected" : ""}>Tutti</option><option value="si" ${x.pro === true ? "selected" : ""}>Solo PRO</option><option value="no" ${x.pro === false ? "selected" : ""}>No PRO</option></select></td>
                  <td><button class="btn fantasma piccolo pericolo" type="button" data-togli="${j}" aria-label="Elimina serie">✕</button></td>
                </tr>`).join("")}</tbody>
            </table></div>
            <div class="cat-azioni">
              <button class="btn piccolo" type="button" data-agg>+ Aggiungi serie</button>
              ${st === "modificata" ? '<button class="btn fantasma piccolo" type="button" data-ripristina>Ripristina originale</button>' : ""}
              <button class="btn fantasma piccolo pericolo" type="button" data-elimina-marca>Elimina marca</button>
            </div>
          </div>
        </details>`;
      }).join("") || '<div class="vuoto"><p class="tenue">Nessuna marca corrisponde alla ricerca.</p></div>';
      S.catAperte = S.catAperte || new Set();
      lista.querySelectorAll(".cat-marca").forEach((d) => {
        const m = C.marche[Number(d.dataset.m)];
        d.addEventListener("toggle", () => { if (d.open) S.catAperte.add(m.marca); else S.catAperte.delete(m.marca); });
        d.querySelectorAll("[data-k]").forEach((x) => (x.onchange = () => {
          const k = x.dataset.k;
          m[k] = k === "alias" ? x.value.split(",").map((a) => a.trim().toUpperCase()).filter(Boolean) : x.value;
          segnaSporco(); disegna(); disegnaProva();
        }));
        d.querySelectorAll("tr[data-s]").forEach((tr) => {
          const v = m.serie[Number(tr.dataset.s)];
          tr.querySelectorAll("[data-c]").forEach((x) => (x.onchange = () => {
            const c = x.dataset.c;
            if (c === "pro") { if (x.value === "si") v.pro = true; else if (x.value === "no") v.pro = false; else delete v.pro; }
            else if (c === "famiglia" && !x.value.trim()) delete v.famiglia;
            else v[c] = c === "serie" || c === "famiglia" ? x.value.trim().toUpperCase() : x.value;
            if (c === "fascia") x.className = `sel-fascia fascia-${x.value.toLowerCase()}`;
            segnaSporco(); disegnaProva();
          }));
        });
        d.querySelectorAll("[data-togli]").forEach((b) => (b.onclick = () => { m.serie.splice(Number(b.dataset.togli), 1); segnaSporco(); disegna(); disegnaProva(); }));
        d.querySelector("[data-agg]").onclick = () => {
          m.serie = m.serie || [];
          m.serie.push({ serie: "", tecnologia: m.tecnologia_predefinita || "LED", fascia: m.fascia_predefinita || "ENTRY", descrizione: "" });
          segnaSporco(); disegna();
          const righe = lista.querySelectorAll(`.cat-marca[data-m="${C.marche.indexOf(m)}"] tr[data-s]`);
          righe[righe.length - 1]?.querySelector("input")?.focus();
        };
        const rip = d.querySelector("[data-ripristina]");
        if (rip) rip.onclick = () => { C.marche[C.marche.indexOf(m)] = clona(C.base.get(m.marca.toUpperCase())); segnaSporco(); disegna(); disegnaProva(); };
        d.querySelector("[data-elimina-marca]").onclick = () => {
          if (!confirm(`Eliminare ${m.marca} dal catalogo? Le sue TV non verranno più riconosciute per serie.`)) return;
          C.marche.splice(C.marche.indexOf(m), 1);
          if (C.base.has(m.marca.toUpperCase())) C.rimosse.add(m.marca.toUpperCase());
          segnaSporco(); disegna(); disegnaProva();
        };
      });
    };
    document.getElementById("catFiltro").oninput = rimbalzo((e) => { S.filtroCat = e.target.value; disegna(); }, 150);
    document.getElementById("catProva").oninput = rimbalzo(disegnaProva, 150);
    document.getElementById("catNuova").onclick = () => {
      const nome = (prompt("Nome della marca (es. Bang & Olufsen):") || "").trim();
      if (!nome) return;
      if (C.marche.some((m) => m.marca.toUpperCase() === nome.toUpperCase())) return toast("Marca già presente", "errore");
      C.marche.unshift({ marca: nome, alias: [nome.toUpperCase()], note: "", fascia_predefinita: "ENTRY", tecnologia_predefinita: "", serie: [] });
      C.rimosse.delete(nome.toUpperCase());
      S.catAperte = S.catAperte || new Set(); S.catAperte.add(nome);
      S.filtroCat = ""; document.getElementById("catFiltro").value = "";
      segnaSporco(); disegna();
    };
    salva.onclick = async () => {
      const vuote = C.marche.flatMap((m) => (m.serie || []).filter((x) => !x.serie.trim()).map(() => m.marca));
      if (vuote.length) return toast(`Ci sono serie senza codice in: ${[...new Set(vuote)].join(", ")}`, "errore");
      const modifiche = C.marche.filter((m) => statoMarca(C, m)).map((m) => clona(m))
        .concat([...C.rimosse].filter((k) => !C.marche.some((m) => m.marca.toUpperCase() === k)).map((k) => ({ marca: C.base.get(k)?.marca || k, rimossa: true })));
      salva.disabled = true; salva.innerHTML = '<span class="caricamento"></span> Salvo…';
      try {
        await api("catalogo", { metodo: "PUT", corpo: { marche: modifiche } });
        C.sporco = false; salva.textContent = "Salvato ✓"; toast("Catalogo salvato: vale dalla prossima ricerca", "ok");
        setTimeout(() => { if (!C.sporco) salva.textContent = "Salva modifiche"; }, 2500);
      } catch (e) { salva.disabled = false; salva.textContent = "Salva modifiche •"; toast("Non salvato: " + e.message, "errore"); }
    };
    disegna(); disegnaProva();
  }
  window.addEventListener("beforeunload", (e) => { if (S.catalogo?.sporco) { e.preventDefault(); e.returnValue = ""; } });

  // ------------------------------------------------------------------ guida e tutorial
  const SLIDE = [
    { titolo: "Benvenuto in TV Finder", testo: "Parti da una lista di ASIN Amazon e trova, per ogni retailer europeo, lo stesso modello oppure la TV più simile.", colore: "var(--giallo)" },
    { titolo: "Incolla gli ASIN", testo: "Copia da Excel, scrivi uno per riga o carica un file. Il paese si legge dalla riga oppure si sceglie per ogni ASIN.", colore: "var(--ciano)" },
    { titolo: "Scegli marketplace e criteri", testo: "Spunta i retailer su cui cercare e decidi quando due TV sono simili: pollici, tecnologia, fascia, anno e altro.", colore: "var(--verde)" },
    { titolo: "Avvia e chiudi pure", testo: "La ricerca gira su GitHub: le ricerche grandi si dividono su più macchine in parallelo (100 ASIN in circa 20–30 minuti). Puoi chiudere il browser: la ritrovi nello Storico, con i risultati da scaricare in Excel.", colore: "var(--magenta)" },
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
            <li><div><h3>Imposta la somiglianza</h3><p>Scegli se cerchi un'alternativa della stessa marca o un concorrente equivalente, poi quanto stretto deve essere il confronto: Stretto, Bilanciato (le regole del documento) o Largo. Per regolare i singoli criteri apri "Personalizza i criteri".</p></div></li>
            <li><div><h3>Tieni aggiornato il Catalogo</h3><p>Nel Catalogo trovi marche e serie con tecnologia e fascia. Puoi aggiungere una marca, una serie nuova o correggere una fascia: vale dalla ricerca successiva. Con "Prova un titolo" vedi subito come viene classificata una TV.</p></div></li>
            <li><div><h3>Avvia e attendi</h3><p>Il motore gira su GitHub. Una ricerca da 10 ASIN su 4 retailer richiede circa 10–15 minuti; da 100 ASIN circa 20–30 minuti, perché si divide su più macchine in parallelo. Puoi chiudere la pagina: la pillola verde in alto e lo Storico ti riportano all'avanzamento.</p></div></li>
            <li><div><h3>Leggi e scarica</h3><p>Per ogni ASIN vedi i modelli simili per retailer con foto e link. "Anno da verificare" segnala i modelli il cui anno non si ricava dal codice. Scarica l'Excel con un foglio per paese più il foglio Dettaglio con tutti i candidati scartati e il motivo.</p></div></li>
          </ol>
          <aside class="scheda faq">
            <h3>Domande frequenti</h3>
            <details><summary>Perché un retailer non trova niente?</summary><p>Il sito può aver cambiato l'indirizzo di ricerca o bloccato l'accesso automatico. Controlla l'URL nel passo Marketplace e guarda il foglio Dettaglio: "ricerca: timeout" o "HTTP 403" indicano un blocco.</p></details>
            <details><summary>Amazon ha bloccato la lettura (captcha): cosa faccio?</summary><p>Amazon a volte blocca le visite automatiche. Il motore riprova con indirizzi diversi e poi cerca l'ASIN sul web. Se non basta, apri la ricerca, premi "Completa i modelli mancanti", scrivi il modello accanto all'ASIN (basta il codice, es. 85U8075F) e avvia. Il modello resta salvato per le ricerche successive.</p></details>
                        <details><summary>Cosa vuol dire "anno da verificare"?</summary><p>Il codice non dichiara l'anno e il titolo non lo riporta. Il modello rispetta gli altri criteri: verifica l'anno sulla pagina prodotto o spegni "Accetta anno non ricavabile".</p></details>
            <details><summary>Posso lanciare più ricerche insieme?</summary><p>Sì, girano in parallelo su GitHub. Ognuna compare nello Storico con il suo stato.</p></details>
            <details><summary>Il prezzo viene letto?</summary><p>Solo per le TV che non sono nel Catalogo: se marca o serie sono sconosciute, la fascia viene stimata dal prezzo al pollice e il risultato lo segnala. Per tutti gli altri il confronto si basa su codice modello, pollici e caratteristiche tecniche.</p></details>
            <details><summary>Usa l'intelligenza artificiale?</summary><p>No. Il motore segue regole fisse: legge le pagine dei siti con un browser automatico, riconosce i modelli con il Catalogo (marche, serie, fasce) e confronta le caratteristiche. Nessun servizio di AI viene chiamato.</p></details>
            <details><summary>Una TV di una marca nuova?</summary><p>Funziona anche senza fare nulla: la marca viene presa da Amazon e la fascia stimata dal prezzo. Per risultati più precisi aggiungi la marca e le sue serie nel <a href="#/catalogo">Catalogo</a>.</p></details>
          </aside>
        </div>
      </div>`;
    document.getElementById("rivedi").onclick = tutorial;
  }

  // ------------------------------------------------------------------ feedback (solo raccolta: non cambia il motore)
  const TIPI_FB = ["Abbinamento errato", "Modello mancante", "Suggerimento", "Problema del sito", "Altro"];
  const STATI_FB = ["nuovo", "in valutazione", "applicato", "scartato"];
  const filtroFb = { stato: "", tipo: "" };

  async function vistaFeedback() {
    const b = S.fbBozza || {};
    S.fbBozza = null;
    const nome = memoria.leggi("fbNome", "");
    app.innerHTML = `
      <div class="vista">
        <div class="intestazione"><div><h1>Feedback</h1><p class="tenue">Segnala un abbinamento sbagliato, un modello mancante o un'idea. I feedback vengono solo raccolti: il tool non cambia finché non vengono valutati.</p></div></div>
        <div class="fb-griglia">
          <form class="scheda fb-form" id="fFb">
            <h3>Nuovo feedback</h3>
            <div class="griglia-2">
              <label class="campo">Il tuo nome <span class="tenue piccolo">facoltativo</span><input type="text" name="nome" maxlength="80" value="${esc(nome)}" autocomplete="name"></label>
              <label class="campo">Tipo<select name="tipo">${TIPI_FB.map((t) => `<option ${t === (b.tipo || "") ? "selected" : ""}>${t}</option>`).join("")}</select></label>
            </div>
            <label class="campo">Feedback<textarea name="messaggio" required maxlength="4000" placeholder="Cosa non va, o cosa miglioreresti?">${esc(b.messaggio || "")}</textarea></label>
            <details class="fb-rif" ${b.asin ? "open" : ""}><summary>Riferimento a una TV <span class="tenue piccolo">facoltativo</span></summary>
              <div class="griglia-2">
                <label class="campo">ASIN<input type="text" name="asin" maxlength="20" value="${esc(b.asin || "")}"></label>
                <label class="campo">Paese<select name="paese"><option value="">—</option>${["IT", "DE", "FR", "ES", "UK"].map((p) => `<option ${p === b.paese ? "selected" : ""}>${p}</option>`).join("")}</select></label>
                <label class="campo">Negozio<input type="text" name="negozio" maxlength="60" value="${esc(b.negozio || "")}"></label>
                <label class="campo">Modello trovato<input type="text" name="modello" maxlength="80" value="${esc(b.modello || "")}"></label>
              </div>
              <label class="campo">Link<input type="url" name="link" maxlength="600" value="${esc(b.link || "")}" placeholder="https://"></label>
            </details>
            <input type="hidden" name="ricerca" value="${esc(b.ricerca || "")}">
            <div><button class="btn primario" type="submit">Invia feedback</button></div>
            <p class="piccolo tenue">Il testo viene salvato nell'archivio del tool su GitHub, che è pubblico: non scrivere dati personali o riservati.</p>
          </form>
          <section class="scheda fb-lista">
            <div class="lista-testa"><h3>Feedback ricevuti <span class="tenue" id="fbConta"></span></h3>
              <div class="filtri">
                <select id="fbStato"><option value="">Tutti gli stati</option>${STATI_FB.map((x) => `<option ${x === filtroFb.stato ? "selected" : ""}>${x}</option>`).join("")}</select>
                <select id="fbTipo"><option value="">Tutti i tipi</option>${TIPI_FB.map((x) => `<option ${x === filtroFb.tipo ? "selected" : ""}>${x}</option>`).join("")}</select>
                <button class="btn piccolo" type="button" id="fbXlsx">Scarica Excel</button>
              </div>
            </div>
            <div id="fbElenco"><div class="caricamento">${barre}</div></div>
          </section>
        </div>
      </div>`;
    let tutti = [];
    const disegna = () => {
      const lista = tutti.filter((f) => (!filtroFb.stato || f.stato === filtroFb.stato) && (!filtroFb.tipo || f.tipo === filtroFb.tipo));
      document.getElementById("fbConta").textContent = tutti.length ? `(${lista.length}${lista.length !== tutti.length ? ` di ${tutti.length}` : ""})` : "";
      const el = document.getElementById("fbElenco");
      if (!lista.length) { el.innerHTML = `<div class="vuoto"><p class="tenue">${tutti.length ? "Nessun feedback con questi filtri." : "Ancora nessun feedback."}</p></div>`; return; }
      el.innerHTML = lista.map((f) => `
        <article class="fb-voce stato-${esc(f.stato.replace(/ /g, "-"))}">
          <div class="fb-testa"><span class="chip">${esc(f.tipo)}</span><span class="piccolo tenue">${esc(f.nome || "Anonimo")} · ${dataBreve(f.data)}</span>
            <select data-stato="${esc(f.id)}" aria-label="Stato">${STATI_FB.map((x) => `<option ${x === f.stato ? "selected" : ""}>${x}</option>`).join("")}</select></div>
          <p class="fb-testo">${esc(f.messaggio)}</p>
          ${f.asin || f.negozio || f.modello || f.link ? `<p class="piccolo tenue">${[f.paese && f.asin ? `${f.paese} ${f.asin}` : f.asin, f.negozio, f.modello].filter(Boolean).map(esc).join(" · ")}${f.link ? ` · <a href="${esc(f.link)}" target="_blank" rel="noopener">link</a>` : ""}${f.ricerca ? ` · <a href="#/run/${esc(f.ricerca)}">ricerca</a>` : ""}</p>` : ""}
        </article>`).join("");
      el.querySelectorAll("[data-stato]").forEach((s) => (s.onchange = async () => {
        s.disabled = true;
        try {
          await api("feedback", { metodo: "PATCH", corpo: { id: s.dataset.stato, stato: s.value } });
          const f = tutti.find((x) => x.id === s.dataset.stato); if (f) f.stato = s.value;
          toast("Stato aggiornato", "ok"); disegna();
        } catch (e) { toast(e.message, "errore"); s.disabled = false; }
      }));
    };
    const carica = async () => {
      try { tutti = (await api("feedback")).feedback || []; disegna(); }
      catch (e) { document.getElementById("fbElenco").innerHTML = `<p class="errore-testo">${esc(e.message)}</p>`; }
    };
    document.getElementById("fbStato").onchange = (e) => { filtroFb.stato = e.target.value; disegna(); };
    document.getElementById("fbTipo").onchange = (e) => { filtroFb.tipo = e.target.value; disegna(); };
    document.getElementById("fbXlsx").onclick = () => {
      if (!window.XLSX) return toast("Generatore Excel non ancora caricato, riprova", "errore");
      const righe = [["Data", "Nome", "Tipo", "Stato", "Feedback", "Paese", "ASIN", "Negozio", "Modello", "Link", "Ricerca"],
        ...tutti.map((f) => [f.data.slice(0, 16).replace("T", " "), f.nome, f.tipo, f.stato, f.messaggio, f.paese, f.asin, f.negozio, f.modello, f.link, f.ricerca])];
      const wb = XLSX.utils.book_new();
      const ws = XLSX.utils.aoa_to_sheet(righe);
      ws["!cols"] = [16, 16, 18, 14, 70, 6, 12, 16, 18, 40, 22].map((w) => ({ wch: w }));
      XLSX.utils.book_append_sheet(wb, ws, "Feedback");
      XLSX.writeFile(wb, `TV_Finder_feedback_${new Date().toISOString().slice(0, 10)}.xlsx`);
    };
    document.getElementById("fFb").onsubmit = async (e) => {
      e.preventDefault();
      const form = e.target, btn = form.querySelector("button[type=submit]");
      const corpo = Object.fromEntries(new FormData(form));
      memoria.scrivi("fbNome", corpo.nome || "");
      btn.disabled = true;
      try {
        const { feedback } = await api("feedback", { metodo: "POST", corpo });
        tutti.unshift(feedback); disegna();
        form.messaggio.value = ""; ["asin", "negozio", "modello", "link", "ricerca"].forEach((k) => (form[k].value = "")); form.paese.value = "";
        toast("Grazie! Feedback inviato", "ok");
      } catch (err) { toast("Feedback non inviato: " + err.message, "errore"); }
      btn.disabled = false;
    };
    carica();
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
