// chat.js -> chat paciente <-> cuidador, estilo MSN.
// Busca mensagens novas a cada 3 segundos (teste com duas janelas: uma normal e uma anônima).
const sessao = exigirLogin(["paciente", "cuidador"]);
const PAINEL = sessao.tipo === "cuidador" ? "dashboardCuidador.html" : "dashboardPacienteApp.html";
el("#voltar-painel").href = PAINEL;

let conversas = [];
let aberta = null;          // conversa aberta
let ultimaId = 0;           // última mensagem já mostrada
let carregando = false;
const DIAS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];

// ------------------------------------------------------------------
// LISTA DE CONTATOS
// ------------------------------------------------------------------
async function carregarConversas() {
  conversas = await api("/conversas");
  const grupos = [
    ["Pedidos para você", conversas.filter((c) => c.status === "pendente" && !c.eu_pedi)],
    ["Conversas", conversas.filter((c) => c.status === "aceita")],
    ["Aguardando resposta", conversas.filter((c) => c.status === "pendente" && c.eu_pedi)],
    ["Encerradas", conversas.filter((c) => ["encerrada", "recusada"].includes(c.status))],
  ];
  el("#contatos").innerHTML = conversas.length ? grupos.filter((g) => g[1].length).map(([titulo, lista]) =>
    `<h3>${titulo}</h3>` + lista.map((c) => `<button class="contato ${aberta && aberta.id_conversa === c.id_conversa ? "ativo" : ""}" data-id="${c.id_conversa}">
      ${avatar(c.outro.iniciais, c.outro.nome)}
      <span class="info"><strong>${esc(c.outro.nome)}</strong><span>${c.ultima_mensagem ? esc(c.ultima_mensagem.texto) : "Sem mensagens"}</span></span>
      <span class="lado">${c.ultima_mensagem ? horaCurta(c.ultima_mensagem.enviado_em) : ""}${c.nao_lidas ? `<span class="bolinha">${c.nao_lidas}</span>` : ""}</span></button>`).join("")).join("")
    : `<div style="padding:16px">${vazio(sessao.tipo === "paciente" ? "Nenhuma conversa ainda. Vá em Buscar cuidador e peça uma conversa." : "Nenhuma conversa ainda. Quando um paciente pedir, aparece aqui.")}</div>`;
}

el("#contatos").addEventListener("click", (e) => {
  const b = e.target.closest(".contato");
  if (b) abrir(Number(b.dataset.id));
});

// ------------------------------------------------------------------
// CONVERSA ABERTA
// ------------------------------------------------------------------
async function abrir(id) {
  aberta = conversas.find((c) => c.id_conversa === id);
  if (!aberta) return;
  ultimaId = 0;
  history.replaceState(null, "", "?conversa=" + id);
  el("#chat").classList.add("abriu-conversa");
  els(".contato").forEach((c) => c.classList.toggle("ativo", Number(c.dataset.id) === id));
  const o = aberta.outro;
  const detalhe = o.tipo === "cuidador" ? `${esc(o.categoria)}${o.destaque ? ' · <span class="selo selo-destaque">★ Destaque</span>' : ""}` : esc(o.cidade || "paciente");
  el("#janela").innerHTML = `
    <div class="chat-topo">
      <button class="btn-icone" id="voltar-lista" aria-label="Voltar para contatos">←</button>
      ${avatar(o.iniciais, o.nome)}<div class="info"><strong>${esc(o.nome)}</strong><span class="suave pequeno">${detalhe}</span></div>
      ${aberta.status === "aceita" ? `<button class="btn btn-pequeno" id="propor" title="Propor agendamento">📅 <span class="texto-btn">Propor agendamento</span></button>
        <button class="btn-icone" id="encerrar" title="Encerrar conversa" aria-label="Encerrar conversa">⏏</button>` : selo(aberta.status)}
    </div>
    <div class="chat-msgs" id="msgs" aria-live="polite"></div>
    <div id="rodape"></div>`;
  el("#voltar-lista").addEventListener("click", () => { el("#chat").classList.remove("abriu-conversa"); aberta = null; carregarConversas(); });
  if (aberta.status === "aceita") {
    el("#propor").addEventListener("click", janelaProposta);
    el("#encerrar").addEventListener("click", encerrar);
  }
  montarRodape();
  await buscarMensagens();
  await mostrarPropostas();
}

function montarRodape() {
  const r = el("#rodape");
  if (aberta.status === "aceita") {
    r.innerHTML = `<form class="chat-enviar" id="f-msg"><textarea id="texto" placeholder="Escreva uma mensagem..." maxlength="2000" aria-label="Mensagem"></textarea>
      <button class="btn" type="submit" aria-label="Enviar">➤</button></form>`;
    const texto = el("#texto");
    texto.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); el("#f-msg").requestSubmit(); } });
    el("#f-msg").addEventListener("submit", enviar);
    if (window.innerWidth > 900) texto.focus();
  } else if (aberta.status === "pendente" && !aberta.eu_pedi) {
    r.innerHTML = `<div class="chat-enviar" style="flex-wrap:wrap;align-items:center"><span style="flex:1;min-width:200px">${esc(aberta.outro.nome)} quer conversar com você.</span>
      <button class="btn btn-ok" data-resp="1">Aceitar</button><button class="btn btn-claro" data-resp="0">Recusar</button></div>`;
    els("[data-resp]", r).forEach((b) => b.addEventListener("click", async () => {
      try {
        await acao(api(`/conversas/${aberta.id_conversa}/responder`, "POST", { aceitar: b.dataset.resp === "1" }),
          b.dataset.resp === "1" ? "Conversa aceita! Pode escrever." : "Pedido recusado.");
        const id = aberta.id_conversa;
        await carregarConversas();
        abrir(id);
      } catch (x) { }
    }));
  } else if (aberta.status === "pendente") {
    r.innerHTML = `<div class="chat-enviar suave">⏳ Aguardando ${esc(aberta.outro.nome)} aceitar o pedido de conversa.</div>`;
  } else {
    r.innerHTML = `<div class="chat-enviar suave">Esta conversa está ${esc(aberta.status)}.${sessao.tipo === "paciente" || aberta.status === "encerrada"
      ? ` <button class="btn btn-pequeno" id="reabrir">Pedir de novo</button>` : ""}</div>`;
    const re = el("#reabrir");
    if (re) re.addEventListener("click", async () => {
      try { await acao(api("/conversas", "POST", { id_outro: aberta.outro.id }), "Pedido enviado!"); await carregarConversas(); abrir(aberta.id_conversa); } catch (x) { }
    });
  }
}

function htmlMensagem(m) {
  if (m.remetente_tipo === "sistema") return `<div class="msg msg-sistema">${esc(m.texto)}<time>${dataBR(m.enviado_em, true)}</time></div>`;
  return `<div class="msg ${m.minha ? "msg-minha" : "msg-outro"}">${esc(m.texto)}<time>${horaCurta(m.enviado_em)}</time></div>`;
}

async function buscarMensagens() {
  if (!aberta || carregando) return;
  carregando = true;
  try {
    const id = aberta.id_conversa;
    const r = await api(`/conversas/${id}/mensagens?depois_de=${ultimaId}`);
    if (!aberta || aberta.id_conversa !== id) return;
    const caixa = el("#msgs");
    const noFim = caixa.scrollHeight - caixa.scrollTop - caixa.clientHeight < 80;
    if (r.mensagens.length) {
      caixa.querySelectorAll(".proposta").forEach((p) => p.remove());
      caixa.insertAdjacentHTML("beforeend", r.mensagens.map(htmlMensagem).join(""));
      ultimaId = r.mensagens[r.mensagens.length - 1].id_mensagem;
      if (noFim || r.mensagens.some((m) => m.minha)) caixa.scrollTop = caixa.scrollHeight;
      if (r.mensagens.some((m) => m.remetente_tipo === "sistema")) mostrarPropostas();
    } else if (!caixa.children.length) {
      caixa.innerHTML = `<div class="chat-vazio">Nenhuma mensagem ainda.</div>`;
    }
    if (r.status !== aberta.status) {          // o outro aceitou/recusou/encerrou
      await carregarConversas();
      abrir(id);
    }
  } catch (e) { /* sem conexão: tenta de novo no próximo ciclo */ }
  finally { carregando = false; }
}

// Propostas de agendamento esperando confirmação aparecem dentro do chat
async function mostrarPropostas() {
  if (!aberta || aberta.status !== "aceita") return;
  const agenda = await api("/agenda?periodo=futuros");
  const props = agenda.filter((a) => a.id_conversa === aberta.id_conversa && a.status === "proposto");
  const grupos = {};
  props.forEach((p) => { const k = p.grupo_repeticao || "x" + p.id_cuidado; (grupos[k] = grupos[k] || []).push(p); });
  const caixa = el("#msgs");
  caixa.querySelectorAll(".proposta").forEach((p) => p.remove());
  caixa.querySelectorAll(".chat-vazio").forEach((p) => p.remove());
  Object.values(grupos).forEach((g) => {
    const a = g[0];
    caixa.insertAdjacentHTML("beforeend", `<div class="proposta"><strong>📅 Proposta de ${esc(a.tipo)}</strong>
      <div class="pequeno">${g.length > 1 ? `${g.length} atendimentos, de ${dataBR(a.data)} a ${dataBR(g[g.length - 1].data)}` : `${dataBR(a.data)} (${diaSemana(a.data)})`}, das ${a.hora_inicio} às ${a.hora_fim}${a.hora_fim < a.hora_inicio ? " do dia seguinte" : ""}</div>
      ${a.tarefas.length ? `<div class="pequeno suave">Tarefas: ${a.tarefas.map((t) => esc(t.descricao)).join(", ")}</div>` : ""}
      ${a.posso_confirmar ? `<div class="linha-botoes"><button class="btn btn-pequeno btn-ok" data-prop="${a.id_cuidado}" data-ok="1">Confirmar</button>
        <button class="btn btn-pequeno btn-claro" data-prop="${a.id_cuidado}" data-ok="0">Recusar</button></div>` : `<div class="pequeno suave">Aguardando ${esc(aberta.outro.nome)} confirmar.</div>`}</div>`);
  });
  els("[data-prop]", caixa).forEach((b) => b.addEventListener("click", async () => {
    try {
      await acao(api(`/agendamentos/${b.dataset.prop}/responder`, "POST", { aceitar: b.dataset.ok === "1" }),
        (r) => b.dataset.ok === "1" ? `${r.quantidade} atendimento(s) confirmado(s)! Já está na agenda.` : "Proposta recusada.");
      await buscarMensagens();
      mostrarPropostas();
    } catch (x) { }
  }));
  caixa.scrollTop = caixa.scrollHeight;
}

async function enviar(e) {
  e.preventDefault();
  const campo = el("#texto");
  const texto = campo.value.trim();
  if (!texto) return;
  campo.value = "";
  try {
    await api(`/conversas/${aberta.id_conversa}/mensagens`, "POST", { texto });
    await buscarMensagens();
  } catch (erro) {
    aviso(erro.message, "erro");
    campo.value = texto;
  }
}

async function encerrar() {
  if (!(await confirmar(`Encerrar a conversa com ${aberta.outro.nome}? Vocês podem abrir de novo depois com um novo pedido.`, "Encerrar"))) return;
  try {
    await acao(api(`/conversas/${aberta.id_conversa}/encerrar`, "POST"), "Conversa encerrada.");
    const id = aberta.id_conversa;
    await carregarConversas();
    abrir(id);
  } catch (x) { }
}

// ------------------------------------------------------------------
// PROPOR AGENDAMENTO (data, horário, tipo, tarefas e repetição)
// ------------------------------------------------------------------
function janelaProposta() {
  abrirJanela("Propor agendamento", `<form id="f-prop">
    <div class="grade-campos">
      <div class="campo"><label for="data">Data *</label><input id="data" name="data" type="date" required min="${hojeISO()}" value="${hojeISO()}"></div>
      <div class="campo"><label for="tipo">Tipo *</label><select id="tipo" name="tipo"><option>visita</option><option>plantão</option><option>acompanhamento</option><option>pós-alta</option></select></div>
      <div class="campo"><label for="hora_inicio">Início *</label><input id="hora_inicio" name="hora_inicio" type="time" required value="08:00"></div>
      <div class="campo"><label for="hora_fim">Fim *</label><input id="hora_fim" name="hora_fim" type="time" required value="12:00"></div>
    </div>
    <p class="ajuda" style="margin-top:-8px">Plantão noturno: se o fim for antes do início (ex.: 19:00 às 07:00), ele termina no dia seguinte. Para testar rápido, marque 10 minutos para hoje.</p>
    <div class="campo"><label for="observacoes">Observações</label><textarea id="observacoes" name="observacoes" maxlength="500" placeholder="Ex.: levar aparelho de pressão"></textarea></div>
    <div class="campo"><label for="tarefas">Tarefas do atendimento (uma por linha)</label><textarea id="tarefas" placeholder="Dar remédio às 8h&#10;Medir pressão&#10;Caminhada de 15 min"></textarea></div>
    <label class="opcao" style="margin-bottom:10px"><input type="checkbox" id="repetir"> Repetir toda semana (escala)</label>
    <div id="caixa-repetir" class="escondido"><label>Dias da semana</label>
      <div class="opcoes" style="grid-template-columns:repeat(auto-fill,minmax(70px,1fr))">${DIAS.map((d, i) => `<label class="opcao"><input type="checkbox" name="repetir_dias" data-lista value="${i}">${d}</label>`).join("")}</div>
      <div class="campo" style="margin-top:10px"><label for="repetir_ate">Repetir até</label><input id="repetir_ate" name="repetir_ate" type="date" min="${hojeISO()}"></div></div>
    <div class="linha-botoes"><button class="btn" type="submit">Enviar proposta</button></div></form>`, (c) => {
    el("#repetir", c).addEventListener("change", (e) => el("#caixa-repetir", c).classList.toggle("escondido", !e.target.checked));
    el("#f-prop", c).addEventListener("submit", async (e) => {
      e.preventDefault();
      const d = lerFormulario(e.target);
      d.tarefas = el("#tarefas", c).value.split("\n").map((t) => t.trim()).filter(Boolean);
      if (!el("#repetir", c).checked) { d.repetir_dias = []; d.repetir_ate = null; }
      try {
        await acao(api(`/conversas/${aberta.id_conversa}/agendamentos`, "POST", d),
          (r) => r.quantidade > 1 ? `Escala proposta: ${r.quantidade} atendimentos. Aguardando confirmação.` : "Proposta enviada! Aguardando confirmação.");
        fecharJanela();
        await buscarMensagens();
        mostrarPropostas();
      } catch (x) { }
    });
  });
}

// ------------------------------------------------------------------
// INÍCIO + atualização automática
// ------------------------------------------------------------------
(async () => {
  try {
    await carregarConversas();
    const pedida = Number(new URLSearchParams(location.search).get("conversa"));
    if (pedida && conversas.some((c) => c.id_conversa === pedida)) abrir(pedida);
    else if (window.innerWidth > 900 && conversas.length) abrir(conversas[0].id_conversa);
  } catch (e) { aviso(e.message, "erro"); }
})();
setInterval(buscarMensagens, 3000);
setInterval(() => { if (!document.hidden) carregarConversas().catch(() => {}); }, 10000);
