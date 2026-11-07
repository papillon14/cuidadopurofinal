// site.js -> roda em TODAS as páginas:
//   1. menu ☰ do celular nas páginas públicas
//   2. conta a visita (painel do Marketing) — número REAL, sem fantasma
//   3. avisa a API quando dá erro de JavaScript (painel do Frontend)
//   4. registra o service worker (app instalável / PWA)
(function () {
  const pagina = location.pathname.replace(/^.*?(\/telas\/|\/index\.html|\/$)/, "$1") || "/";

  // 1. Menu do celular
  document.addEventListener("DOMContentLoaded", () => {
    const botao = document.querySelector(".btn-menu");
    const barra = document.querySelector(".navbar");
    if (botao && barra) {
      botao.setAttribute("aria-label", "Abrir menu");
      botao.addEventListener("click", () => barra.classList.toggle("menu-aberto"));
    }
  });

  if (typeof API_BASE_URL === "undefined") return;

  // 2. Visita (uma por página por sessão do navegador)
  try {
    const chave = "cp_visita_" + pagina;
    if (!sessionStorage.getItem(chave)) {
      sessionStorage.setItem(chave, "1");
      const origem = document.referrer && !document.referrer.startsWith(location.origin) ? document.referrer : null;
      fetch(API_BASE_URL + "/tracking/visita", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pagina: pagina.slice(0, 150), origem: origem ? origem.slice(0, 200) : null }),
      }).catch(() => {});
    }
  } catch (e) { /* navegador sem sessionStorage: ignora */ }

  // 3. Erros de JavaScript vão para o painel do Frontend
  let enviados = 0;
  function reportar(mensagem, detalhe) {
    if (enviados++ > 5) return;
    fetch(API_BASE_URL + "/logs/erro-site", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mensagem: String(mensagem).slice(0, 500),
                             detalhe: detalhe ? String(detalhe).slice(0, 4000) : null, pagina }),
    }).catch(() => {});
  }
  window.addEventListener("error", (e) => reportar(e.message, `${e.filename}:${e.lineno}\n${e.error && e.error.stack}`));
  window.addEventListener("unhandledrejection", (e) => {
    const r = e.reason || {};
    if (r.ehErroDaApi) return; // erro esperado (ex.: senha errada) não é bug
    reportar(r.message || r, r.stack);
  });

  // 4. PWA
  if ("serviceWorker" in navigator && location.protocol !== "file:") {
    const raiz = location.pathname.includes("/telas/") ? "../" : "./";
    window.addEventListener("load", () => navigator.serviceWorker.register(raiz + "service-worker.js").catch(() => {}));
  }
})();
