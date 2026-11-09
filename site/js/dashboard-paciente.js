// dashboard-paciente.js -> painel do PACIENTE e da FAMÍLIA (central da família, só leitura)
const sessao = exigirLogin(["paciente", "familiar"]);
const ehFamilia = sessao.tipo === "familiar";
let catalogo = null;
let painel = null;            // dados do /paciente/painel
let pacienteFamilia = null;   // id do paciente que a família está vendo

const ITENS = ehFamilia
  ? [["inicio", "Início"], ["agenda", "Agenda"], ["saude", "Saúde"], ["ajuda", "Ajuda (SAC)"], ["conta", "Minha conta"]]
  : [["inicio", "Início"], ["buscar", "Buscar cuidador"], ["conversas", "Conversas", "chat.html"], ["agenda", "Agenda"],
     ["saude", "Saúde"], ["familia", "Família"], ["mensalidade", "Mensalidade"], ["ajuda", "Ajuda (SAC)"], ["conta", "Minha conta"]];

montarEstrutura(sessao, ITENS, ehFamilia ? "Central da família" : "Paciente");

const RENDER = {
  inicio: ehFamilia ? inicioFamilia : inicioPaciente,
  buscar: renderBusca,
  agenda: (c) => renderAgenda(c, false, ehFamilia, atualizarContadores),
  saude: (c) => ehFamilia ? saudeFamilia(c) : renderSaude(c, sessao.id, { podeEditar: true }),
  familia: renderFamilia,
  mensalidade: renderMensalidade,
  ajuda: (c) => renderAjuda(c, sessao),
  conta: ehFamilia ? contaFamilia : renderConta,
};

const irPara = montarMenu(ITENS.filter((i) => !i[2]).map((i) => i[0]), async (secao) => {
  const caixa = el("#secao-" + secao);
  try { await RENDER[secao](caixa); } catch (e) { if (e.ehErroDaApi) caixa.innerHTML = vazio(e.message); else throw e; }
});

async function atualizarContadores() {
  if (ehFamilia) return;
  try {
    const conversas = await api("/conversas");
    contador("conversas", conversas.reduce((s, c) => s + c.nao_lidas + (c.status === "pendente" && !c.eu_pedi ? 1 : 0), 0));
    const agenda = await api("/agenda?periodo=todos");
    contador("agenda", agenda.filter((a) => a.posso_confirmar || a.posso_avaliar).length);
  } catch (e) { /* sem conexão: ignora */ }
}

// ------------------------------------------------------------------
// INÍCIO (paciente)
// ------------------------------------------------------------------
async function inicioPaciente(caixa) {
  painel = await api("/paciente/painel");
  const p = painel.perfil;
  const pendente = p.status_cadastro !== "aprovado";
  const m = painel.mensalidade;
  caixa.innerHTML = topo(`Olá, ${esc(p.nome.split(" ")[0])}! 👋`, "Aqui está o resumo do seu cuidado.") +
    (pendente ? `<div class="faixa">⏳ Seu cadastro está <b>em análise</b> pela equipe. Você já pode ver o sistema, mas só pode chamar cuidadores depois de aprovado.</div>` : "") +
    (painel.em_dia === false ? `<div class="faixa">💳 Sua mensalidade está <b>pendente</b>. Conversas e agendamentos ficam travados até o pagamento. <a href="#mensalidade" data-ir="mensalidade">Pagar com Pix</a></div>` : "") +
    (painel.pendentes_avaliar ? `<div class="faixa faixa-info">⭐ Você tem ${painel.pendentes_avaliar} atendimento(s) para avaliar. <a href="#agenda" data-ir="agenda">Avaliar agora</a></div>` : "") +
    `<div class="grade grade-4">
      <div class="cartao numero"><div class="rotulo">Próximo atendimento</div><div class="valor" style="font-size:1.2rem">${painel.proximos[0] ? `${dataBR(painel.proximos[0].data)}<br>${painel.proximos[0].hora_inicio}` : "—"}</div><div class="suave pequeno">${painel.proximos[0] ? esc(painel.proximos[0].com) : "nenhum marcado"}</div></div>
      <div class="cartao numero"><div class="rotulo">Bem-estar</div><div class="valor ${painel.bem_estar.faixa === "alerta" ? "perigo" : painel.bem_estar.faixa === "atenção" ? "aviso" : ""}">${painel.bem_estar.indice_atual ?? "—"}</div><div class="suave pequeno">${esc(painel.bem_estar.faixa)}</div></div>
      <div class="cartao numero"><div class="rotulo">Alertas</div><div class="valor ${painel.bem_estar.alertas.length ? "perigo" : ""}">${painel.bem_estar.alertas.length}</div><div class="suave pequeno">de saúde</div></div>
      <div class="cartao numero"><div class="rotulo">Mensalidade</div><div class="valor" style="font-size:1.2rem">${m ? reais(m.valor) : "—"}</div><div>${m ? selo(m.status) : ""}</div></div>
    </div>
    <div class="grade grade-2" style="margin-top:16px">
      <div class="cartao"><div class="cartao-topo"><h3>Próximos atendimentos</h3><a href="#agenda" data-ir="agenda" class="pequeno">ver agenda</a></div>
        ${painel.proximos.length ? `<div class="lista">${painel.proximos.map((a) => `<div class="item"><div class="item-data"><b>${new Date(a.data + "T12:00").getDate()}</b><span>${diaSemana(a.data)}</span></div>
          <div class="item-corpo"><strong>${esc(a.tipo)} · ${horario(a)}</strong><span class="suave pequeno">com ${esc(a.com)}</span></div>${selo(a.status)}</div>`).join("")}</div>`
        : vazio("Nenhum atendimento marcado. Procure um cuidador e combine pelo chat.")}
        ${pendente ? "" : `<div class="linha-botoes"><a class="btn" href="#buscar" data-ir="buscar">🔎 Buscar cuidador</a></div>`}</div>
      <div class="cartao"><div class="cartao-topo"><h3>Saúde</h3><a href="#saude" data-ir="saude" class="pequeno">ver tudo</a></div>
        ${medidorBemEstar(painel.bem_estar)}<div style="margin-top:12px">${listaAlertas(painel.bem_estar.alertas)}</div></div>
    </div>`;
  ligarAtalhos(caixa);
  atualizarContadores();
}

function ligarAtalhos(caixa) {
  els("[data-ir]", caixa).forEach((a) => a.addEventListener("click", (e) => { e.preventDefault(); irPara(a.dataset.ir); }));
}

// ------------------------------------------------------------------
// BUSCAR CUIDADOR
// ------------------------------------------------------------------
async function renderBusca(caixa) {
  catalogo = catalogo || await api("/catalogo");
  caixa.innerHTML = topo("Buscar cuidador", "Só aparecem profissionais aprovados pela equipe. Os de plano Premium ficam em destaque.") + `
    <div class="cartao"><form id="f-busca" class="grade grade-4" style="align-items:end">
      <div><label for="b-cidade">Cidade</label><input id="b-cidade" name="cidade" placeholder="Ex.: Maringá"></div>
      <div><label for="b-cat">Categoria</label><select id="b-cat" name="categoria"><option value="">Todas</option>${catalogo.categorias.map((c) => `<option>${esc(c)}</option>`).join("")}</select></div>
      <div><label for="b-hab">Habilidade</label><select id="b-hab" name="id_habilidade"><option value="">Todas</option>${catalogo.habilidades.map((h) => `<option value="${h.id}">${esc(h.nome)}</option>`).join("")}</select></div>
      <button class="btn" type="submit">Buscar</button></form></div>
    <div id="resultado" style="margin-top:16px"></div>`;
  const buscar = async () => {
    const d = lerFormulario(el("#f-busca", caixa));
    const q = new URLSearchParams(Object.entries(d).filter(([, v]) => v !== null)).toString();
    const lista = await api("/cuidadores" + (q ? "?" + q : ""));
    el("#resultado", caixa).innerHTML = lista.length ? `<p class="suave pequeno" style="color:#dfe7f3">${lista.length} cuidador(es) encontrado(s)</p><div class="cuidadores">${lista.map(cartaoCuidador).join("")}</div>`
      : `<div class="cartao">${vazio("Nenhum cuidador com esses filtros.")}</div>`;
  };
  el("#f-busca", caixa).addEventListener("submit", (e) => { e.preventDefault(); buscar(); });
  el("#resultado", caixa).addEventListener("click", async (e) => {
    const perfil = e.target.closest("[data-perfil]"), pedir = e.target.closest("[data-pedir]");
    if (perfil) janelaPerfil(perfil.dataset.perfil, buscar);
    if (pedir) await pedirConversa(pedir.dataset.pedir, buscar);
  });
  await buscar();
}

function botaoConversa(c) {
  const conv = c.conversa;
  if (conv && conv.status === "aceita") return `<a class="btn btn-pequeno" href="chat.html?conversa=${conv.id}">💬 Abrir chat</a>`;
  if (conv && conv.status === "pendente") return `<span class="selo selo-aviso">pedido enviado</span>`;
  return `<button class="btn btn-pequeno" data-pedir="${c.id_cuidador}">💬 Pedir conversa</button>`;
}

function cartaoCuidador(c) {
  return `<div class="cartao cuidador-cartao ${c.destaque ? "com-destaque" : ""}">
    <div class="cabeca">${avatar(c.iniciais, c.nome)}<div style="min-width:0"><strong>${esc(c.nome)}</strong>
      ${c.destaque ? ' <span class="selo selo-destaque">★ Destaque</span>' : ""}
      <div class="suave pequeno">${esc(c.categoria_profissional)} · ${esc(c.cidade)}</div><div class="pequeno">${estrelas(c.nota_media)} ${c.qtd_avaliacoes ? `(${c.qtd_avaliacoes})` : ""}</div></div></div>
    <div class="descricao">${esc(c.descricao || "")}</div>
    <div class="etiquetas">${c.habilidades.slice(0, 4).map((h) => `<span class="etiqueta">${esc(h)}</span>`).join("")}${c.habilidades.length > 4 ? `<span class="etiqueta">+${c.habilidades.length - 4}</span>` : ""}</div>
    <div class="linha-botoes" style="justify-content:space-between"><button class="btn btn-pequeno btn-claro" data-perfil="${c.id_cuidador}">Ver perfil</button>${botaoConversa(c)}</div></div>`;
}

async function janelaPerfil(id, depois) {
  const c = await api("/cuidadores/" + id);
  abrirJanela("Perfil do cuidador", `<div class="cabeca" style="display:flex;gap:14px;align-items:center;margin-bottom:12px">
      ${avatar(c.iniciais, c.nome).replace("avatar ", "avatar avatar-grande ")}<div><h3 style="margin:0">${esc(c.nome)}</h3>
      <div class="suave">${esc(c.categoria_profissional)}${c.numero_registro_coren ? " · " + esc(c.numero_registro_coren) : ""}</div>
      <div>${estrelas(c.nota_media)} ${c.destaque ? '<span class="selo selo-destaque">★ Destaque</span>' : ""}</div></div></div>
    <p>${esc(c.descricao || "")}</p>
    <div class="etiquetas" style="margin-bottom:14px">${c.habilidades.map((h) => `<span class="etiqueta">${esc(h)}</span>`).join("")}</div>
    <h4>Avaliações (${c.qtd_avaliacoes})</h4>
    ${c.avaliacoes.length ? `<div class="lista">${c.avaliacoes.map((a) => `<div class="item"><div class="item-corpo"><span>${estrelas(a.nota)}</span>
      <div class="pequeno">${esc(a.comentario || "(sem comentário)")}</div><span class="suave pequeno">${esc(a.paciente)} · ${dataBR(a.data)}</span></div></div>`).join("")}</div>` : vazio("Ainda sem avaliações.")}
    <div class="linha-botoes"><button class="btn" id="pedir-perfil">💬 Pedir conversa</button></div>`, (corpo) => {
    el("#pedir-perfil", corpo).addEventListener("click", async () => { await pedirConversa(id, depois); fecharJanela(); });
  });
}

async function pedirConversa(id, depois) {
  try {
    await acao(api("/conversas", "POST", { id_outro: Number(id) }), "Pedido enviado! Quando o cuidador aceitar, o chat abre.");
    if (depois) depois();
  } catch (e) { /* aviso já mostrado */ }
}

// ------------------------------------------------------------------
// FAMÍLIA (o paciente cria o acesso dos familiares)
// ------------------------------------------------------------------
async function renderFamilia(caixa) {
  const lista = await api("/paciente/familiares");
  caixa.innerHTML = topo("Central da família", "Crie um acesso para quem acompanha você. O familiar vê a agenda, a saúde e os alertas, mas não muda nada.") + `
    <div class="grade grade-2">
      <div class="cartao"><h3>Quem acompanha você</h3>${lista.length ? `<div class="lista">${lista.map((f) => `<div class="item">${avatar(f.nome.split(" ").map((x) => x[0]).slice(0, 2).join(""), f.nome)}
        <div class="item-corpo"><strong>${esc(f.nome)} <span class="etiqueta">${esc(f.parentesco)}</span></strong><span class="suave pequeno">${esc(f.email)} · ${esc(f.telefone)}</span></div>
        <div class="item-acoes"><button class="btn btn-pequeno btn-claro" data-remover="${f.id_familiar}">Remover acesso</button></div></div>`).join("")}</div>` : vazio("Nenhum familiar ainda.")}</div>
      <div class="cartao"><h3>Novo acesso familiar</h3><form id="f-fam"><div class="grade-campos">
        <div class="campo inteiro"><label for="f-nome">Nome *</label><input id="f-nome" name="nome" required minlength="3"></div>
        <div class="campo"><label for="f-par">Parentesco *</label><input id="f-par" name="parentesco" required placeholder="Ex.: filha"></div>
        <div class="campo"><label for="f-cpf">CPF *</label><input id="f-cpf" name="cpf" required placeholder="000.000.000-00"></div>
        <div class="campo"><label for="f-tel">Telefone *</label><input id="f-tel" name="telefone" required placeholder="(44) 99999-9999"></div>
        <div class="campo"><label for="f-email">E-mail (login) *</label><input id="f-email" name="email" type="email" required></div>
        <div class="campo inteiro"><label for="f-senha">Senha inicial *</label><input id="f-senha" name="senha" type="password" required minlength="6"></div>
      </div><button class="btn" type="submit">Criar acesso</button></form></div></div>`;
  el("#f-fam", caixa).addEventListener("submit", async (e) => {
    e.preventDefault();
    try { await acao(api("/paciente/familiares", "POST", lerFormulario(e.target)), (r) => r.mensagem + " Ele entra pela mesma tela de login."); renderFamilia(caixa); } catch (x) { }
  });
  els("[data-remover]", caixa).forEach((b) => b.addEventListener("click", async () => {
    if (!(await confirmar("Remover o acesso deste familiar?", "Remover"))) return;
    try { await acao(api("/paciente/familiares/" + b.dataset.remover, "DELETE"), "Acesso removido."); renderFamilia(caixa); } catch (x) { }
  }));
}

// ------------------------------------------------------------------
// MINHA CONTA (paciente)
// ------------------------------------------------------------------
async function renderConta(caixa) {
  painel = await api("/paciente/painel");
  catalogo = catalogo || await api("/catalogo");
  const p = painel.perfil;
  caixa.innerHTML = topo("Minha conta", esc(p.email)) + `<div class="grade grade-2">
    <div class="cartao"><h3>Meus dados</h3><form id="f-perfil"><div class="grade-campos">
      <div class="campo"><label for="c-tel">Telefone</label><input id="c-tel" name="telefone" value="${esc(p.telefone)}"></div>
      <div class="campo"><label for="c-cid">Cidade</label><input id="c-cid" name="cidade" value="${esc(p.cidade)}"></div>
      <div class="campo inteiro"><label for="c-end">Endereço</label><input id="c-end" name="endereco" value="${esc(p.endereco)}"></div>
      <div class="campo"><label for="c-resp">Responsável</label><input id="c-resp" name="nome_responsavel" value="${esc(p.nome_responsavel || "")}"></div>
      <div class="campo"><label for="c-tresp">Telefone do responsável</label><input id="c-tresp" name="telefone_responsavel" value="${esc(p.telefone_responsavel || "")}"></div>
      <div class="campo inteiro"><label for="c-obs">Observações</label><textarea id="c-obs" name="observacoes">${esc(p.observacoes || "")}</textarea></div></div>
      <label>Necessidades</label><div class="opcoes">${catalogo.necessidades.map((n) => `<label class="opcao"><input type="checkbox" name="necessidades" data-lista value="${n.id}" ${p.id_necessidades.includes(n.id) ? "checked" : ""}>${esc(n.nome)}</label>`).join("")}</div>
      <div class="linha-botoes"><button class="btn" type="submit">Salvar</button></div></form></div>
    <div>${formSenha()}<div class="cartao"><h3>Sair</h3><p class="suave">Encerra o acesso neste aparelho.</p><button class="btn btn-claro" id="sair2">Sair da conta</button></div></div></div>`;
  el("#f-perfil", caixa).addEventListener("submit", async (e) => {
    e.preventDefault();
    try { await acao(api("/paciente/perfil", "PATCH", lerFormulario(e.target)), "Dados salvos!"); } catch (x) { }
  });
  ligarSenha(caixa);
  el("#sair2", caixa).addEventListener("click", sair);
}

// ------------------------------------------------------------------
// FAMÍLIA LOGADA (central da família)
// ------------------------------------------------------------------
async function inicioFamilia(caixa) {
  const dados = await api("/familiar/painel");
  if (!dados.pacientes.length) { caixa.innerHTML = topo("Central da família", "") + `<div class="cartao">${vazio("Nenhum paciente ligado ao seu acesso.")}</div>`; return; }
  pacienteFamilia = pacienteFamilia || dados.pacientes[0].perfil.id_paciente;
  caixa.innerHTML = topo(`Olá, ${esc(sessao.nome.split(" ")[0])}!`, "Você acompanha o cuidado de quem você ama. Tudo aqui é só para leitura.") +
    dados.pacientes.map((x) => `<div class="cartao"><div class="cartao-topo"><div style="display:flex;gap:12px;align-items:center">${avatar(x.perfil.iniciais, x.perfil.nome)}
      <div><h2 style="margin:0">${esc(x.perfil.nome)}</h2><span class="suave pequeno">${x.perfil.idade} anos · ${esc(x.perfil.endereco)}</span></div></div>
      <button class="btn btn-pequeno" data-ver-saude="${x.perfil.id_paciente}">Ver saúde completa</button></div>
      <div class="grade grade-2"><div>${medidorBemEstar(x.bem_estar)}<div style="margin-top:12px">${listaAlertas(x.bem_estar.alertas)}</div></div>
      <div><h3>Próximos atendimentos</h3>${x.proximos.length ? `<div class="lista">${x.proximos.map((a) => `<div class="item"><div class="item-corpo"><strong>${dataBR(a.data)} · ${horario(a)}</strong>
        <span class="suave pequeno">${esc(a.tipo)} com ${esc(a.com)}</span></div>${selo(a.status)}</div>`).join("")}</div>` : vazio("Nada marcado.")}</div></div></div>`).join("");
  els("[data-ver-saude]", caixa).forEach((b) => b.addEventListener("click", () => { pacienteFamilia = Number(b.dataset.verSaude); irPara("saude"); }));
}

async function saudeFamilia(caixa) {
  if (!pacienteFamilia) {
    const dados = await api("/familiar/painel");
    if (!dados.pacientes.length) { caixa.innerHTML = vazio("Nenhum paciente ligado ao seu acesso."); return; }
    pacienteFamilia = dados.pacientes[0].perfil.id_paciente;
  }
  await renderSaude(caixa, pacienteFamilia, { titulo: "Saúde (somente leitura)" });
}

function contaFamilia(caixa) {
  caixa.innerHTML = topo("Minha conta", "") + `<div class="grade grade-2">${formSenha()}
    <div class="cartao"><h3>Sair</h3><button class="btn btn-claro" id="sair2">Sair da conta</button></div></div>`;
  ligarSenha(caixa);
  el("#sair2", caixa).addEventListener("click", sair);
}

setInterval(atualizarContadores, 20000);
