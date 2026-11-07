// config.js -> descobre sozinho o endereço da API
//
//  * Abriu pelo uvicorn (http://127.0.0.1:8000)  -> API no mesmo endereço
//  * Abriu pelo Go Live (porta 5500, 5501...)    -> API na porta 8000
//  * Abriu com dois cliques no arquivo (file://) -> API em 127.0.0.1:8000
//  * Hospedado (https://cuidadopuro.com.br)       -> API no mesmo endereço
const API_BASE_URL = (() => {
  const { protocol, hostname, port, origin } = window.location;
  if (protocol === "file:") return "http://127.0.0.1:8000/api";
  if (port && port !== "8000") return `${protocol}//${hostname}:8000/api`;
  return origin + "/api";
})();
