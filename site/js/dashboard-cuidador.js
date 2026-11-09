// dashboard-cuidador.js -> painel do CUIDADOR
const sessao = exigirLogin(["cuidador"]);
let painel = null;
let catalogo = null;
let pacienteAberto = null;

const ITENS = [["inicio", "Início"], ["pedidos", "Pedidos"], ["conversas", "Conversas", "chat.html"], ["agenda", "Agenda"],
  ["pacientes", "Meus pacientes"], ["buscar", "Buscar pacientes"], ["plano", "Meu plano"], ["mensalidade", "Mensalidade"],
  ["ajuda", "Ajuda (SAC)"], ["conta", "Meu perfil"]];
montarEstrutura(sessao, ITENS, "Cuidador");

const RENDER = {
  inicio: renderInicio, pedidos: renderPedidos, agenda: (c) => renderAgenda(c, true, false, atualizarContadores),
  pacientes: renderPacientes, buscar: renderBusca, plano: renderPlano, mensalidade: renderMensalidade,
  ajuda: (c) => renderAjuda(c, sessao), conta: renderPerfil,
};
const irPara = montarMenu(ITENS.filter((i) => !i[2]).map((i) => i[0]), async (secao) => {
  const caixa = el("#secao-" + secao);
  try { await RENDER[secao](caixa); } catch (e) { if (e.ehErroDaApi) caixa.innerHTML = vazio(e.message); else throw e; }
});

async function atualizarContadores() {
  try {
    const conversas = await api("/conversas");
    contador("pedidos", conversas.filter((c) => c.status === "pendente" && !c.eu_pedi).length);
    contador("conversas", conversas.reduce((s, c) => s + c.nao_lidas, 0));
    const agenda = await api("/agenda?periodo=futuros");
    contador("agenda", agenda.filter((a) => a.posso_confirmar).length);
  } catch (e) { /* ignora */ }
}

function ligarAtalhos(caixa) {
  els("[data-ir]", caixa).forEach((a) => a.addEventListener("click", (e) => { e.preventDefault(); irPara(a.dataset.ir); }));
}

// ------------------------------------------------------------------
// INÍCIO
// ------------------------------------------------------------------
async function renderInicio(caixa) {
  painel = await api("/cuidador/painel");
  const p = painel.perfil, pl = painel.plano, m = painel.mensalidade;
  const limite = pl.limite_conversas ? `${pl.conversas_abertas} de ${pl.limite_conversas}` : `${pl.conversas_abertas}`;
  caixa.innerHTML = topo(`Olá, ${esc(p.nome.split(" ")[0])}! 👋`, `Plano <b>${esc(pl.nome)}</b> ${pl.destaque ? '<span class="selo selo-destaque">★ Destaque</span>' : ""}`) +
    (p.status_cadastro !== "aprovado" ? `<div class="faixa">⏳ Seu cadastro está <b>em análise</b>. Assim que a equipe aprovar, você aparece na busca dos pacientes.</div>` : "") +
    (painel.pedidos_pendentes ? `<div class="faixa faixa-info">📨 Você tem ${painel.pedidos_pendentes} pedido(s) de conversa esperando resposta. <a href="#pedidos" data-ir="pedidos">Responder</a></div>` : "") +
    `<div class="grade grade-4">
      <div class="cartao numero"><div class="rotulo">Pedidos novos</div><div class="valor ${painel.pedidos_pendentes ? "aviso" : ""}">${painel.pedidos_pendentes}</div><div class="suave pequeno">de pacientes</div></div>
      <div class="cartao numero"><div class="rotulo">Conversas abertas</div><div class="valor">${limite}</div><div class="suave pequeno">${pl.limite_conversas ? "limite do plano" : "ilimitadas"}</div></div>
      <div class="cartao numero"><div class="rotulo">Atendimentos no mês</div><div class="valor">${painel.concluidos_mes}</div><div class="suave pequeno">concluídos</div></div>
      <div class="cartao numero"><div class="rotulo">Sua nota</div><div class="valor">${p.nota_media ?? "—"}</div><div class="suave pequeno">${p.qtd_avaliacoes} ${p.qtd_avaliacoes === 1 ? "avaliação" : "avaliações"}</div></div>
    </div>
    <div class="grade grade-2" style="margin-top:16px">
      <div class="cartao"><div class="cartao-topo"><h3>Próximos atendimentos</h3><a href="#agenda" data-ir="agenda" class="pequeno">ver agenda</a></div>
        ${painel.proximos.length ? `<div class="lista">${painel.proximos.map((a) => `<div class="item"><div class="item-data"><b>${new Date(a.data + "T12:00").getDate()}</b><span>${diaSemana(a.data)}</span></div>
          <div class="item-corpo"><strong>${esc(a.tipo)} · ${a.hora_inicio}–${a.hora_fim}</strong><span class="suave pequeno">${esc(a.com)} · ${esc(a.endereco)}</span></div>${selo(a.status)}</div>`).join("")}</div>`
        : vazio("Nenhum atendimento marcado.")}</div>
      <div class="cartao"><h3>Mensalidade</h3>${m ? `<p>${reais(m.valor)} · ${selo(m.status)}</p>` : vazio("Sem mensalidade neste mês.")}
        ${m && m.status !== "pago" ? `<a class="btn btn-pequeno" href="#mensalidade" data-ir="mensalidade">Pagar com Pix</a>` : ""}
        <h3 style="margin-top:18px">Seu plano</h3><p class="suave">${esc(pl.descricao)}</p>
        <a class="btn btn-pequeno btn-claro" href="#plano" data-ir="plano">Ver planos</a></div>
    </div>`;
  ligarAtalhos(caixa);
  atualizarContadores();
}

// ------------------------------------------------------------------
// PEDIDOS DE CONVERSA
// ------------------------------------------------------------------
async function renderPedidos(caixa) {
  const conversas = await api("/conversas");
  const recebidos = conversas.filter((c) => c.status === "pendente" && !c.eu_pedi);
  const enviados = conversas.filter((c) => c.status === "pendente" && c.eu_pedi);
  painel = painel || await api("/cuidador/painel");
  const pl = painel.plano;
  caixa.innerHTML = topo("Pedidos de conversa", "Aceite para abrir o chat com o paciente.") +
    (pl.limite_conversas ? `<div class="faixa faixa-info">Plano ${esc(pl.nome)}: até ${pl.limite_conversas} conversas abertas ao mesmo tempo. Agora: ${pl.conversas_abertas}.</div>` : "") +
    `<div class="cartao"><h3>Recebidos</h3>${recebidos.length ? `<div class="lista">${recebidos.map((c) => `<div class="item">${avatar(c.outro.iniciais, c.outro.nome)}
      <div class="item-corpo"><strong>${esc(c.outro.nome)}</strong><span class="suave pequeno">${esc(c.outro.cidade || "")} · ${dataBR(c.criado_em, true)}</span></div>
      <div class="item-acoes"><button class="btn btn-pequeno btn-claro" data-ficha="${c.outro.id}">Ver paciente</button>
      <button class="btn btn-pequeno btn-ok" data-responder="${c.id_conversa}" data-aceitar="1">Aceitar</button>
      <button class="btn btn-pequeno btn-claro" data-responder="${c.id_conversa}" data-aceitar="0">Recusar</button></div></div>`).join("")}</div>` : vazio("Nenhum pedido novo.")}</div>
    <div class="cartao"><h3>Enviados por você</h3>${enviados.length ? `<div class="lista">${enviados.map((c) => `<div class="item">${avatar(c.outro.iniciais, c.outro.nome)}
      <div class="item-corpo"><strong>${esc(c.outro.nome)}</strong><span class="suave pequeno">aguardando o paciente aceitar</span></div>${selo("pendente")}</div>`).join("")}</div>` : vazio("Nenhum pedido enviado.")}</div>`;
  els("[data-responder]", caixa).forEach((b) => b.addEventListener("click", async () => {
    const aceitar = b.dataset.aceitar === "1";
    try {
      await acao(api(`/conversas/${b.dataset.responder}/responder`, "POST", { aceitar }), aceitar ? "Pedido aceito! O chat está liberado." : "Pedido recusado.");
      if (aceitar) location.href = "chat.html?conversa=" + b.dataset.responder;
      else renderPedidos(caixa);
    } catch (x) { }
  }));
  els("[data-ficha]", caixa).forEach((b) => b.addEventListener("click", () => {
    const c = recebidos.find((x) => String(x.outro.id) === b.dataset.ficha);
    abrirJanela("Pedido de " + c.outro.nome, `<p>${esc(c.outro.nome)} quer conversar com você.</p>
      <p class="suave">Os dados completos (endereço, telefone e saúde) ficam liberados depois que você aceitar.</p>`);
  }));
  atualizarContadores();
}

// ------------------------------------------------------------------
// MEUS PACIENTES (conversa aceita) + ficha de saúde
// ------------------------------------------------------------------
async function renderPacientes(caixa) {
  if (pacienteAberto) return renderSaudePaciente(caixa);
  const lista = await api("/cuidador/pacientes");
  caixa.innerHTML = topo("Meus pacientes", "Pacientes com conversa aceita. Clique para ver a saúde e fazer o registro diário.") +
    (lista.length ? `<div class="cuidadores">${lista.map((p) => `<div class="cartao cuidador-cartao">
      <div class="cabeca">${avatar(p.iniciais, p.nome)}<div><strong>${esc(p.nome)}</strong><div class="suave pequeno">${p.idade} anos · ${esc(p.cidade)}</div></div></div>
      <div class="pequeno">📍 ${esc(p.endereco)}<br>📞 ${esc(p.telefone)}${p.nome_responsavel ? `<br>👤 ${esc(p.nome_responsavel)} ${esc(p.telefone_responsavel || "")}` : ""}</div>
      <div class="etiquetas">${p.necessidades.map((n) => `<span class="etiqueta">${esc(n)}</span>`).join("")}</div>
      <div>Bem-estar: <b>${p.indice_atual ?? "—"}</b> ${selo(p.faixa)} ${p.alertas ? `<span class="selo selo-perigo">${p.alertas} alerta(s)</span>` : ""}</div>
      <div class="linha-botoes" style="justify-content:space-between"><a class="btn btn-pequeno btn-claro" href="chat.html?conversa=${p.id_conversa}">💬 Chat</a>
        <button class="btn btn-pequeno" data-abrir="${p.id_paciente}">❤️ Saúde e registro</button></div></div>`).join("")}</div>`
      : `<div class="cartao">${vazio("Você ainda não tem pacientes. Aceite um pedido de conversa para começar.")}</div>`);
  els("[data-abrir]", caixa).forEach((b) => b.addEventListener("click", () => { pacienteAberto = Number(b.dataset.abrir); renderSaudePaciente(caixa); }));
}

async function renderSaudePaciente(caixa) {
  const ficha = await api(`/pacientes/${pacienteAberto}/ficha`);
  await renderSaude(caixa, pacienteAberto, { podeEditar: true, podeRegistrar: true, titulo: "Saúde de " + esc(ficha.nome) });
  const voltar = document.createElement("button");
  voltar.className = "btn btn-claro btn-pequeno";
  voltar.textContent = "← Voltar para meus pacientes";
  voltar.style.marginBottom = "12px";
  voltar.addEventListener("click", () => { pacienteAberto = null; renderPacientes(caixa); });
  caixa.prepend(voltar);
  if (ficha.observacoes) caixa.querySelector(".topo-pagina").insertAdjacentHTML("afterend", `<div class="faixa faixa-info">📋 ${esc(ficha.observacoes)}</div>`);
}

// ------------------------------------------------------------------
// BUSCAR PACIENTES (Padrão e Premium)
// ------------------------------------------------------------------
async function renderBusca(caixa) {
  painel = await api("/cuidador/painel");
  if (!painel.plano.pode_iniciar_conversa) {
    caixa.innerHTML = topo("Buscar pacientes", "") + `<div class="cartao"><h3>🔒 Disponível a partir do plano Padrão</h3>
      <p>No plano <b>${esc(painel.plano.nome)}</b> você recebe pedidos dos pacientes. Para procurar pacientes e mandar pedidos, mude para o Padrão ou o Premium.</p>
      <a class="btn" href="#plano" data-ir="plano">Ver planos</a></div>`;
    return ligarAtalhos(caixa);
  }
  caixa.innerHTML = topo("Buscar pacientes", "Pacientes aprovados que procuram cuidado. Os de maior dependência aparecem primeiro.") +
    `<div class="cartao"><form id="f-busca" style="display:flex;gap:8px;align-items:end;flex-wrap:wrap"><div style="flex:1;min-width:200px"><label for="b-cidade">Cidade</label>
      <input id="b-cidade" name="cidade" placeholder="Ex.: Maringá"></div><button class="btn" type="submit">Buscar</button></form></div><div id="resultado" style="margin-top:16px"></div>`;
  const buscar = async () => {
    const cidade = el("#b-cidade", caixa).value.trim();
    const lista = await api("/pacientes" + (cidade ? "?cidade=" + encodeURIComponent(cidade) : ""));
    el("#resultado", caixa).innerHTML = lista.length ? `<div class="cuidadores">${lista.map((p) => `<div class="cartao cuidador-cartao">
      <div class="cabeca">${avatar(p.iniciais, p.nome)}<div><strong>${esc(p.nome)}</strong><div class="suave pequeno">${p.idade} anos · ${esc(p.cidade)}</div></div></div>
      <div class="etiquetas">${p.necessidades.map((n) => `<span class="etiqueta">${esc(n)}</span>`).join("")}</div>
      <div class="pequeno">Dependência: ${selo(p.grau_dependencia === "alto" ? "alerta" : p.grau_dependencia === "moderado" ? "atenção" : "bom").replace(/>[^<]+</, `>${esc(p.grau_dependencia || "—")}<`)}</div>
      <div class="linha-botoes">${p.conversa && p.conversa.status === "aceita" ? `<a class="btn btn-pequeno" href="chat.html?conversa=${p.conversa.id}">💬 Abrir chat</a>`
        : p.conversa && p.conversa.status === "pendente" ? selo("pendente") : `<button class="btn btn-pequeno" data-pedir="${p.id_paciente}">💬 Pedir conversa</button>`}</div></div>`).join("")}</div>`
      : `<div class="cartao">${vazio("Nenhum paciente encontrado.")}</div>`;
    els("[data-pedir]", caixa).forEach((b) => b.addEventListener("click", async () => {
      try { await acao(api("/conversas", "POST", { id_outro: Number(b.dataset.pedir) }), "Pedido enviado ao paciente!"); buscar(); } catch (x) { }
    }));
  };
  el("#f-busca", caixa).addEventListener("submit", (e) => { e.preventDefault(); buscar(); });
  await buscar();
}

// ------------------------------------------------------------------
// MEU PLANO (comparar, trocar e relatório Premium)
// ------------------------------------------------------------------
async function renderPlano(caixa) {
  painel = await api("/cuidador/painel");
  catalogo = await api("/catalogo");
  const atual = painel.plano;
  const planos = catalogo.planos.filter((p) => p.publico === "cuidador");
  const sim = (v) => (v ? "✅" : "—");
  caixa.innerHTML = topo("Meu plano", `Você está no <b>${esc(atual.nome)}</b> · ${reais(atual.valor)}/mês`) + `
    <div class="cartao"><div class="tabela-caixa"><table class="responsiva"><thead><tr><th>Benefício</th>${planos.map((p) => `<th>${esc(p.nome)}<br><span class="suave">${reais(p.valor)}</span></th>`).join("")}</tr></thead><tbody>
      <tr><td data-rotulo="">Aparece na busca dos pacientes</td>${planos.map((p) => `<td data-rotulo="${esc(p.nome)}">✅</td>`).join("")}</tr>
      <tr><td data-rotulo="">Conversas abertas</td>${planos.map((p) => `<td data-rotulo="${esc(p.nome)}">${p.limite_conversas ? "até " + p.limite_conversas : "ilimitadas"}</td>`).join("")}</tr>
      <tr><td data-rotulo="">Procurar pacientes e mandar pedido</td>${planos.map((p) => `<td data-rotulo="${esc(p.nome)}">${sim(p.pode_iniciar_conversa)}</td>`).join("")}</tr>
      <tr><td data-rotulo="">Topo da busca + selo Destaque</td>${planos.map((p) => `<td data-rotulo="${esc(p.nome)}">${sim(p.destaque)}</td>`).join("")}</tr>
      <tr><td data-rotulo="">Relatório de visitas ao perfil</td>${planos.map((p) => `<td data-rotulo="${esc(p.nome)}">${sim(p.relatorio)}</td>`).join("")}</tr>
      <tr><td></td>${planos.map((p) => `<td>${p.id === atual.id ? selo("ativo") : `<button class="btn btn-pequeno" data-plano="${p.id}">Mudar para ${esc(p.nome)}</button>`}</td>`).join("")}</tr>
    </tbody></table></div></div><div id="relatorio"></div>`;
  els("[data-plano]", caixa).forEach((b) => b.addEventListener("click", async () => {
    if (!(await confirmar("Mudar de plano agora? A mensalidade deste mês (se não foi paga) passa a ter o novo valor.", "Mudar plano"))) return;
    try { await acao(api("/cuidador/plano", "PATCH", { id_plano: Number(b.dataset.plano) }), (r) => r.mensagem); renderPlano(caixa); } catch (x) { }
  }));
  if (atual.relatorio) {
    const r = await api("/cuidador/relatorio");
    el("#relatorio", caixa).innerHTML = `<div class="cartao"><h3>📊 Relatório Premium</h3><div class="grade grade-4">
      <div class="numero"><div class="rotulo">Visitas ao perfil</div><div class="valor">${r.visualizacoes_perfil}</div></div>
      <div class="numero"><div class="rotulo">Pedidos recebidos</div><div class="valor">${r.pedidos_recebidos}</div></div>
      <div class="numero"><div class="rotulo">Conversas aceitas</div><div class="valor">${r.conversas_aceitas}</div></div>
      <div class="numero"><div class="rotulo">Posição na busca</div><div class="valor">${r.posicao_na_busca}º</div></div></div></div>`;
  } else {
    el("#relatorio", caixa).innerHTML = `<div class="cartao"><h3>📊 Relatório de visitas</h3><p class="suave">Exclusivo do Premium: veja quantos pacientes visitaram seu perfil e sua posição na busca.</p></div>`;
  }
}

// ------------------------------------------------------------------
// MEU PERFIL
// ------------------------------------------------------------------
async function renderPerfil(caixa) {
  painel = await api("/cuidador/painel");
  catalogo = catalogo || await api("/catalogo");
  const p = painel.perfil;
  const semRegistro = p.categoria_profissional === "sem registro";
  caixa.innerHTML = topo("Meu perfil", `${esc(p.categoria_profissional)}${p.numero_registro_coren ? " · " + esc(p.numero_registro_coren) : ""}`) + `<div class="grade grade-2">
    <div class="cartao"><h3>Como os pacientes veem você</h3><form id="f-perfil">
      <div class="grade-campos"><div class="campo"><label for="p-tel">Telefone</label><input id="p-tel" name="telefone" value="${esc(p.telefone)}"></div>
      <div class="campo"><label for="p-cid">Cidade</label><input id="p-cid" name="cidade" value="${esc(p.cidade)}"></div>
      <div class="campo inteiro"><label for="p-desc">Sua experiência</label><textarea id="p-desc" name="descricao" maxlength="500">${esc(p.descricao || "")}</textarea></div></div>
      <label>Habilidades</label><div class="opcoes">${catalogo.habilidades.map((h) => `<label class="opcao"><input type="checkbox" name="habilidades" data-lista value="${h.id}"
        ${p.id_habilidades.includes(h.id) ? "checked" : ""} ${semRegistro && h.restrita_tecnico ? "disabled" : ""}>${esc(h.nome)}</label>`).join("")}</div>
      <div class="linha-botoes"><button class="btn" type="submit">Salvar perfil</button></div></form></div>
    <div>${formSenha()}<div class="cartao"><h3>Sair</h3><button class="btn btn-claro" id="sair2">Sair da conta</button></div></div></div>`;
  el("#f-perfil", caixa).addEventListener("submit", async (e) => {
    e.preventDefault();
    try { await acao(api("/cuidador/perfil", "PATCH", lerFormulario(e.target)), "Perfil salvo!"); } catch (x) { }
  });
  ligarSenha(caixa);
  el("#sair2", caixa).addEventListener("click", sair);
}

setInterval(atualizarContadores, 20000);
