// app.js -> ferramentas usadas pelas telas internas (dashboards, chat, painel)

// ------------------------------------------------------------------
// SESSÃO: o "crachá" (token) fica guardado no navegador
// ------------------------------------------------------------------
const Sessao = {
  chave: "cp_sessao",
  pegar(chave = this.chave) {
    try { return JSON.parse(localStorage.getItem(chave)); } catch (e) { return null; }
  },
  salvar(dados, chave = this.chave) { localStorage.setItem(chave, JSON.stringify(dados)); },
  limpar(chave = this.chave) { localStorage.removeItem(chave); },
};

// Garante que quem abriu a página é do tipo certo; senão manda para o login
function exigirLogin(tipos, paginaLogin = "telaLogin.html", chave) {
  const s = Sessao.pegar(chave);
  if (!s || !s.token || (tipos && !tipos.includes(s.tipo))) {
    location.href = paginaLogin;
    throw new Error("sem login");
  }
  return s;
}

// ------------------------------------------------------------------
// API: toda conversa com o back-end passa por aqui (fetch)
// ------------------------------------------------------------------
class ErroApi extends Error {
  constructor(status, mensagem) { super(mensagem); this.status = status; this.ehErroDaApi = true; }
}

function textoDoErro(dados, status) {
  let d = dados && dados.detail;
  if (Array.isArray(d)) {                       // erro 422 do Pydantic vem em lista
    return d.map((e) => `${NOMES_CAMPOS[e.loc[e.loc.length - 1]] || e.loc[e.loc.length - 1]}: ${traduzir(e.msg)}`).join(" · ");
  }
  return d || `Erro ${status}`;
}

const NOMES_CAMPOS = {
  nome: "Nome", cpf: "CPF", rg: "RG", cep: "CEP", email: "E-mail", senha: "Senha", telefone: "Telefone",
  endereco: "Endereço", cidade: "Cidade", data_nascimento: "Data de nascimento", idade: "Idade",
  hora_fim: "Hora de fim", hora_inicio: "Hora de início", data: "Data", texto: "Mensagem",
  senha_nova: "Nova senha", valor: "Valor", codigo: "Código", validade: "Validade",
  categoria_profissional: "Categoria", nome_medicamento: "Medicamento", data_fim: "Data de fim",
};

function traduzir(msg) {
  return msg
    .replace(/^Value error, /, "")
    .replace(/String should have at least (\d+) characters?/, "mínimo de $1 caracteres")
    .replace(/String should have at most (\d+) characters?/, "máximo de $1 caracteres")
    .replace(/String should match pattern.*/, "formato inválido")
    .replace(/Input should be greater than or equal to (\S+)/, "precisa ser no mínimo $1")
    .replace(/Input should be less than or equal to (\S+)/, "precisa ser no máximo $1")
    .replace(/Input should be greater than (\S+)/, "precisa ser maior que $1")
    .replace(/Field required/, "obrigatório")
    .replace(/Input should be a valid date.*/, "data inválida")
    .replace(/Input should be a valid integer.*/, "precisa ser um número")
    .replace(/Input should be '.*/, "opção inválida");
}

async function api(caminho, metodo = "GET", corpo = null, chave) {
  const s = Sessao.pegar(chave);
  const opcoes = { method: metodo, headers: {} };
  if (s && s.token) opcoes.headers["Authorization"] = "Bearer " + s.token;
  if (corpo !== null) {
    opcoes.headers["Content-Type"] = "application/json";
    opcoes.body = JSON.stringify(corpo);
  }
  let resposta;
  try {
    resposta = await fetch(API_BASE_URL + caminho, opcoes);
  } catch (e) {
    throw new ErroApi(0, "Sem conexão com a API. Confira se o uvicorn está ligado.");
  }
  if (resposta.status === 204) return null;
  const tipo = resposta.headers.get("content-type") || "";
  const dados = tipo.includes("json") ? await resposta.json() : await resposta.blob();
  if (resposta.status === 401 && s && s.token) {        // token vencido: volta pro login
    Sessao.limpar(chave);
    setTimeout(() => location.reload(), 1200);
  }
  if (!resposta.ok) throw new ErroApi(resposta.status, textoDoErro(dados, resposta.status));
  return dados;
}

// ------------------------------------------------------------------
// TELA: avisos, janelas, carregando
// ------------------------------------------------------------------
function el(seletor, raiz = document) { return raiz.querySelector(seletor); }
function els(seletor, raiz = document) { return [...raiz.querySelectorAll(seletor)]; }

// Evita que um nome com < > quebre a página (e protege contra código malicioso)
function esc(texto) {
  if (texto === null || texto === undefined) return "";
  return String(texto).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function aviso(texto, tipo = "ok") {
  let caixa = el("#avisos");
  if (!caixa) {
    caixa = document.createElement("div");
    caixa.id = "avisos";
    caixa.setAttribute("aria-live", "polite");
    document.body.appendChild(caixa);
  }
  const item = document.createElement("div");
  item.className = "notificacao notificacao-" + tipo;
  item.textContent = texto;
  caixa.appendChild(item);
  setTimeout(() => item.classList.add("saindo"), tipo === "erro" ? 6000 : 3500);
  setTimeout(() => item.remove(), tipo === "erro" ? 6500 : 4000);
}

// Executa uma ação da API mostrando aviso de sucesso ou de erro
async function acao(promessa, sucesso) {
  try {
    const r = await promessa;
    if (sucesso) aviso(typeof sucesso === "function" ? sucesso(r) : sucesso, "ok");
    return r;
  } catch (e) {
    aviso(e.message, "erro");
    throw e;
  }
}

function abrirJanela(titulo, html, aoAbrir) {
  fecharJanela();
  const fundo = document.createElement("div");
  fundo.className = "janela-fundo";
  fundo.innerHTML = `<div class="janela" role="dialog" aria-modal="true" aria-label="${esc(titulo)}">
      <div class="janela-topo"><h3>${esc(titulo)}</h3>
      <button class="btn-icone" data-fechar aria-label="Fechar">✕</button></div>
      <div class="janela-corpo">${html}</div></div>`;
  fundo.addEventListener("click", (e) => { if (e.target === fundo || e.target.closest("[data-fechar]")) fecharJanela(); });
  document.body.appendChild(fundo);
  document.body.classList.add("sem-rolagem");
  const primeiro = fundo.querySelector("input, select, textarea, button:not([data-fechar])");
  // foco imediato no 1º campo (sem atraso: assim nunca "rouba" o cursor de quem já está digitando)
  if (primeiro && !fundo.contains(document.activeElement)) primeiro.focus({ preventScroll: true });
  if (aoAbrir) aoAbrir(fundo.querySelector(".janela-corpo"));
  return fundo;
}
function fecharJanela() {
  els(".janela-fundo").forEach((j) => j.remove());
  document.body.classList.remove("sem-rolagem");
}
document.addEventListener("keydown", (e) => { if (e.key === "Escape") fecharJanela(); });

function confirmar(texto, botao = "Confirmar") {
  return new Promise((ok) => {
    abrirJanela("Confirmação", `<p>${esc(texto)}</p>
      <div class="linha-botoes"><button class="btn btn-claro" data-fechar>Voltar</button>
      <button class="btn btn-perigo" id="sim">${esc(botao)}</button></div>`, (c) => {
      el("#sim", c).addEventListener("click", () => { fecharJanela(); ok(true); });
    });
  });
}

// Lê um formulário e devolve um objeto { campo: valor }
function lerFormulario(form) {
  const dados = {};
  for (const campo of form.elements) {
    if (!campo.name || campo.disabled) continue;
    if (campo.type === "checkbox") {
      if (campo.dataset.lista !== undefined) {
        dados[campo.name] = dados[campo.name] || [];
        if (campo.checked) dados[campo.name].push(isNaN(campo.value) ? campo.value : Number(campo.value));
      } else dados[campo.name] = campo.checked;
    } else if (campo.type === "radio") {
      if (campo.checked) dados[campo.name] = campo.value;
    } else if (campo.type === "number") {
      dados[campo.name] = campo.value === "" ? null : Number(campo.value);
    } else {
      const v = campo.value.trim();
      dados[campo.name] = v === "" ? null : v;
    }
  }
  return dados;
}

// ------------------------------------------------------------------
// FORMATOS
// ------------------------------------------------------------------
const reais = (v) => Number(v || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
function dataBR(valor, comHora = false) {
  if (!valor) return "—";
  const d = new Date(String(valor).length === 10 ? valor + "T12:00:00" : valor);
  const texto = d.toLocaleDateString("pt-BR");
  return comHora ? `${texto} ${d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}` : texto;
}
function diaSemana(valor) {
  return new Date(valor + "T12:00:00").toLocaleDateString("pt-BR", { weekday: "short" }).replace(".", "");
}
function horaCurta(valor) {
  const d = new Date(valor);
  const hoje = new Date();
  if (d.toDateString() === hoje.toDateString()) return d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
}
const hojeISO = () => { const d = new Date(); d.setMinutes(d.getMinutes() - d.getTimezoneOffset()); return d.toISOString().slice(0, 10); };

function selo(status) {
  const classes = {
    pago: "ok", aprovado: "ok", aceita: "ok", agendado: "ok", "concluído": "info", ativo: "ok", ativa: "ok", resolvido: "ok", resolvida: "ok", bom: "ok",
    pendente: "aviso", proposto: "aviso", "em andamento": "info", "em contato": "info", "atenção": "aviso", aberto: "aviso", nova: "perigo",
    planejada: "info", "prospecção": "info", "negociação": "aviso",
    atrasado: "perigo", recusado: "perigo", recusada: "perigo", cancelado: "neutro", encerrada: "neutro", inativo: "neutro", alerta: "perigo",
  };
  return `<span class="selo selo-${classes[status] || "neutro"}">${esc(status)}</span>`;
}

function avatar(iniciais, nome) {
  // cor fixa por nome (sempre a mesma para a mesma pessoa)
  let soma = 0;
  for (const c of nome || iniciais) soma += c.charCodeAt(0);
  return `<span class="avatar avatar-${soma % 6}" aria-hidden="true">${esc(iniciais)}</span>`;
}

const estrelas = (nota) => nota ? `<span class="estrelas" aria-label="nota ${nota}">${"★".repeat(Math.round(nota))}${"☆".repeat(5 - Math.round(nota))}</span> ${Number(nota).toFixed(1)}` : `<span class="suave">sem avaliações</span>`;

function vazio(texto) { return `<div class="vazio">${esc(texto)}</div>`; }

// ------------------------------------------------------------------
// LAYOUT DOS DASHBOARDS: menu lateral que vira gaveta no celular
// ------------------------------------------------------------------
function montarMenu(secoes, aoTrocar) {
  const lateral = el(".lateral");
  const botao = el(".btn-gaveta");
  const fundo = el(".gaveta-fundo");
  const fechar = () => document.body.classList.remove("gaveta-aberta");
  if (botao) botao.addEventListener("click", () => document.body.classList.toggle("gaveta-aberta"));
  if (fundo) fundo.addEventListener("click", fechar);
  els("[data-secao]", lateral).forEach((link) => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      irPara(link.dataset.secao);
      fechar();
    });
  });
  function irPara(secao) {
    if (!secoes.includes(secao)) secao = secoes[0];
    els("[data-secao]", lateral).forEach((l) => l.classList.toggle("ativo", l.dataset.secao === secao));
    els(".secao").forEach((s) => s.classList.toggle("escondido", s.id !== "secao-" + secao));
    history.replaceState(null, "", "#" + secao);
    window.scrollTo(0, 0);
    aoTrocar(secao);
  }
  // se o # da URL mudar (botão voltar, link "#agenda"), troca a seção também
  window.addEventListener("hashchange", () => irPara((location.hash || "").slice(1) || secoes[0]));
  irPara((location.hash || "").slice(1) || secoes[0]);
  return irPara;
}

// ------------------------------------------------------------------
// GRÁFICOS SIMPLES (sem biblioteca: funcionam até sem internet)
// ------------------------------------------------------------------
function graficoBarras(lista, campoRotulo, campoValor) {
  const max = Math.max(1, ...lista.map((x) => x[campoValor]));
  return `<div class="grafico-barras" role="img" aria-label="gráfico de barras">${lista.map((x) => `
    <div class="barra" title="${esc(x[campoRotulo])}: ${x[campoValor]}">
      <em>${x[campoValor] || ""}</em><i style="height:${(100 * x[campoValor]) / max}%"></i>
      <small>${esc(x[campoRotulo])}</small></div>`).join("")}</div>`;
}

function graficoLinha(serie, campoRotulo, campoValor, maximo = 100) {
  if (!serie.length) return vazio("Ainda não há registros para o gráfico.");
  const L = 600, A = 180, m = 26;
  const x = (i) => m + (serie.length === 1 ? (L - 2 * m) / 2 : (i * (L - 2 * m)) / (serie.length - 1));
  const y = (v) => A - m - (v / maximo) * (A - 2 * m);
  const pontos = serie.map((p, i) => `${x(i)},${y(p[campoValor])}`).join(" ");
  const faixas = [75, 50].map((v) => `<line x1="${m}" x2="${L - m}" y1="${y(v)}" y2="${y(v)}" stroke="rgba(255,255,255,.15)" stroke-dasharray="4 4"/>
      <text x="0" y="${y(v) + 4}" fill="#a8b8d0" font-size="11">${v}</text>`).join("");
  return `<div class="grafico-linha"><svg viewBox="0 0 ${L} ${A}" role="img" aria-label="evolução do índice">
    ${faixas}
    <polyline points="${pontos}" fill="none" stroke="#68beb5" stroke-width="3" stroke-linejoin="round"/>
    ${serie.map((p, i) => `<circle cx="${x(i)}" cy="${y(p[campoValor])}" r="5" fill="${p[campoValor] >= 75 ? "#81c784" : p[campoValor] >= 50 ? "#e7a82e" : "#ef7f7f"}"><title>${esc(p[campoRotulo])}: ${p[campoValor]}</title></circle>
      <text x="${x(i)}" y="${A - 4}" fill="#a8b8d0" font-size="11" text-anchor="middle">${esc(p[campoRotulo])}</text>`).join("")}
  </svg></div>`;
}

function barrasHorizontais(objeto) {
  const itens = Object.entries(objeto);
  if (!itens.length) return vazio("Sem dados ainda.");
  const max = Math.max(1, ...itens.map((i) => i[1]));
  return `<div class="barras-horizontais">${itens.map(([nome, v]) => `
    <div class="linha-h"><span>${esc(nome)}</span><div class="trilho"><i style="width:${(100 * v) / max}%"></i></div><b>${v}</b></div>`).join("")}</div>`;
}

const CORES = ["#68beb5", "#e7a82e", "#7fb5ef", "#b4557a", "#81c784", "#9c8ade"];
function rosca(partes, centro) {
  const total = partes.reduce((s, p) => s + p.valor, 0);
  let acumulado = 0;
  const fatias = partes.map((p, i) => {
    const ini = (acumulado / (total || 1)) * 100;
    acumulado += p.valor;
    return `${CORES[i % CORES.length]} ${ini}% ${(acumulado / (total || 1)) * 100}%`;
  }).join(", ");
  return `<div class="rosca"><div class="rosca-anel" style="background:conic-gradient(${total ? fatias : "rgba(255,255,255,.1) 0 100%"})"><b>${centro ?? total}</b></div>
    <div class="legenda">${partes.map((p, i) => `<span style="--c:${CORES[i % CORES.length]}">${esc(p.nome)}: <b>${p.valor}</b></span>`).join("")}</div></div>`;
}

function medidorBemEstar(be) {
  const v = be.indice_atual;
  const cor = v === null ? "rgba(255,255,255,.2)" : v >= 75 ? "#81c784" : v >= 50 ? "#e7a82e" : "#ef7f7f";
  return `<div class="medidor"><div class="medidor-anel" style="--p:${v || 0};--cor:${cor}"><b>${v === null ? "—" : Math.round(v)}</b></div>
    <div><div class="rotulo suave pequeno">ÍNDICE DE BEM-ESTAR (0 a 100)</div>
    <div style="margin:4px 0">${selo(be.faixa)}</div>
    <p class="suave pequeno">Calculado pelos registros diários: dor, sono, alimentação e humor.
    ${be.total_registros} registro(s) nos últimos 14 dias.</p></div></div>`;
}

function listaAlertas(alertas) {
  if (!alertas.length) return `<div class="alerta alerta-bom"><strong>Nenhum alerta</strong>Os últimos registros estão dentro do esperado.</div>`;
  return alertas.map((a) => `<div class="alerta alerta-${a.nivel}"><strong>${esc(a.titulo)}</strong>${esc(a.texto)}</div>`).join("") +
    `<p class="suave pequeno">Os alertas são regras simples que ajudam a perceber mudanças. Eles não substituem a avaliação do profissional de saúde.</p>`;
}

const CORES_TEMPO = { registro: "#68beb5", atendimento: "#7fb5ef", consulta: "#e7a82e", medicacao: "#9c8ade", avaliacao: "#f5c94a" };
function linhaDoTempo(eventos) {
  if (!eventos.length) return vazio("Nada registrado ainda.");
  return `<div class="tempo">${eventos.map((e) => `
    <div class="tempo-item ${e.futuro ? "futuro" : ""}" style="--c:${CORES_TEMPO[e.tipo] || "#68beb5"}">
      <time>${dataBR(e.quando, e.tipo !== "medicacao")}${e.futuro ? " · próximo" : ""}</time>
      <strong>${esc(e.titulo)}</strong><p>${esc(e.texto)}${e.autor ? ` <span class="suave">— ${esc(e.autor)}</span>` : ""}</p></div>`).join("")}</div>`;
}
