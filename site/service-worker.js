// service-worker.js -> faz o site virar um APP instalável (PWA)
//
// Estratégia:
//  * Telas (HTML, CSS, JS): busca na internet primeiro (sempre a versão nova);
//    se estiver sem internet, usa a cópia guardada.
//  * Imagens e ícones: usa a cópia guardada (mais rápido).
//  * API (/api/...): NUNCA guarda. Dados de saúde e chat sempre vêm do servidor.
const VERSAO = "cuidado-puro-v7";
const ESSENCIAIS = [
  "./", "./index.html", "./manifest.json",
  "./css/style.css", "./css/app.css",
  "./js/config.js", "./js/site.js", "./js/app.js",
  "./telas/telaLogin.html", "./telas/img/logo_(2).png", "./telas/img/marble.jpeg",
  "./icons/icon-192.png", "./icons/icon-512.png",
];

self.addEventListener("install", (evento) => {
  evento.waitUntil(caches.open(VERSAO).then((cache) => cache.addAll(ESSENCIAIS)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (evento) => {
  evento.waitUntil(caches.keys()
    .then((nomes) => Promise.all(nomes.filter((n) => n !== VERSAO).map((n) => caches.delete(n))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", (evento) => {
  const pedido = evento.request;
  const url = new URL(pedido.url);
  if (pedido.method !== "GET" || url.pathname.includes("/api/") || url.origin !== location.origin) return;

  if (pedido.destination === "image") {
    evento.respondWith(caches.match(pedido).then((guardado) => guardado || fetch(pedido).then((resposta) => {
      const copia = resposta.clone();
      caches.open(VERSAO).then((cache) => cache.put(pedido, copia));
      return resposta;
    })));
    return;
  }
  evento.respondWith(fetch(pedido).then((resposta) => {
    const copia = resposta.clone();
    caches.open(VERSAO).then((cache) => cache.put(pedido, copia));
    return resposta;
  }).catch(() => caches.match(pedido).then((guardado) => guardado || caches.match("./telas/telaLogin.html"))));
});
