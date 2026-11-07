// painel.js -> PAINEL INTERNO. Um painel só: o menu muda conforme o papel.
const CHAVE = "cp_equipe";                      // sessão da equipe separada da do paciente/cuidador
const papi = (caminho, metodo = "GET", corpo = null) => api(caminho, metodo, corpo, CHAVE);

const SECOES = {
  geral: ["📊", "Visão geral"], equipe: ["👥", "Equipe"], cadastros: ["✅", "Cadastros"], usuarios: ["🗂️", "Usuários"],
  sac: ["🛟", "SAC"], financeiro: ["💰", "Financeiro"], marketing: ["📣", "Marketing"], comercial: ["🏷️", "Comercial"],
  frontend: ["🖥️", "Frontend"], backend: ["⚙️", "Backend"], banco: ["🗄️", "Banco de dados"], conta: ["🔑", "Minha conta"],
};
const NOMES_PAPEL = { ADM: "Administrador", suporte: "Suporte", SAC: "SAC", financeiro: "Financeiro", marketing: "Marketing",
  comercial: "Comercial", frontend: "Frontend", backend: "Backend", banco: "Banco de dados" };

// ------------------------------------------------------------------
// LOGIN
// ------------------------------------------------------------------
async function iniciar() {
  const s = Sessao.pegar(CHAVE);
  if (!s) return mostrarLogin();
  try {
    const menu = await papi("/painel/menu");
    abrirPainel(menu);
  } catch (e) {
    Sessao.limpar(CHAVE);
    mostrarLogin();
  }
}

function mostrarLogin() {
  el("#tela-login").classList.remove("escondido");
  el("#tela-painel").classList.add("escondido");
}

el("#form-login").addEventListener("submit", async (e) => {
  e.preventDefault();
  const d = lerFormulario(e.target);
  try {
    const r = await api("/equipe/login", "POST", d);
    Sessao.salvar(r, CHAVE);
    el("#tela-login").classList.add("escondido");
    abrirPainel(await papi("/painel/menu"));
  } catch (erro) { aviso(erro.message, "erro"); }
});
els(".logins-teste button").forEach((b) => b.addEventListener("click", () => {
  el("#email").value = b.dataset.email;
  el("#senha").value = b.dataset.senha || "equipe123";
}));

let irPara;
function abrirPainel(menu) {
  el("#tela-painel").classList.remove("escondido");
  el(".lateral nav").innerHTML = menu.secoes.map((s) => `<a href="#${s}" data-secao="${s}"><span class="icone">${SECOES[s][0]}</span>${SECOES[s][1]}</a>`).join("");
  el(".usuario-caixa").innerHTML = `${avatar(menu.iniciais, menu.nome)}<div><strong>${esc(menu.nome)}</strong><small>${esc(NOMES_PAPEL[menu.papel])}</small></div>
    <button class="btn-icone" id="sair" title="Sair" aria-label="Sair">⎋</button>`;
  el("#sair").addEventListener("click", async () => {
    try { await papi("/logout", "POST"); } catch (x) { }
    Sessao.limpar(CHAVE);
    location.replace(location.pathname);
  });
  el(".conteudo").innerHTML = menu.secoes.map((s) => `<section class="secao escondido" id="secao-${s}"></section>`).join("");
  irPara = montarMenu(menu.secoes, async (secao) => {
    const caixa = el("#secao-" + secao);
    try { await RENDER[secao](caixa, menu); } catch (e) { if (e.ehErroDaApi) caixa.innerHTML = vazio(e.message); else throw e; }
  });
}

const topo = (t, p, b = "") => `<div class="topo-pagina"><div><h1>${t}</h1>${p ? `<p>${p}</p>` : ""}</div><div>${b}</div></div>`;
const numero = (rotulo, valor, sub = "", cls = "") => `<div class="cartao numero"><div class="rotulo">${rotulo}</div><div class="valor ${cls}">${valor}</div><div class="suave pequeno">${sub}</div></div>`;
const mes = (ref) => ref.split("-").reverse().join("/");

// ------------------------------------------------------------------
// ADM: visão geral e equipe
// ------------------------------------------------------------------
async function renderGeral(caixa) {
  const g = await papi("/painel/geral");
  const u = g.usuarios;
  caixa.innerHTML = topo("Visão geral", "Todos os números vêm do banco de dados em tempo real.") + `
    <div class="grade grade-4">
      ${numero("Usuários", u.pacientes + u.cuidadores + u.familiares, `${u.pacientes} pacientes · ${u.cuidadores} cuidadores`)}
      ${numero("Cadastros pendentes", g.pendentes, "esperando o suporte", g.pendentes ? "aviso" : "")}
      ${numero("Visitas (30 dias)", g.visitas_30_dias, "acessos reais ao site")}
      ${numero("Receita do mês", reais(g.receita_mes), `a receber ${reais(g.a_receber_mes)}`)}
      ${numero("Mensalidades atrasadas", g.atrasadas, "para o financeiro", g.atrasadas ? "perigo" : "")}
      ${numero("Conversas ativas", g.conversas_ativas, "pacientes ↔ cuidadores")}
      ${numero("Atendimentos", g.atendimentos_futuros, `agendados · ${g.atendimentos_concluidos} concluídos`)}
      ${numero("SAC", g.avaliacoes_sac + g.chamados_abertos, `${g.avaliacoes_sac} ${g.avaliacoes_sac === 1 ? "avaliação ruim" : "avaliações ruins"} · ${g.chamados_abertos} ${g.chamados_abertos === 1 ? "chamado" : "chamados"}`, g.avaliacoes_sac ? "perigo" : "")}
    </div>
    <div class="grade grade-2" style="margin-top:16px">
      <div class="cartao"><div class="cartao-topo"><h3>Visitas ao site · últimos 14 dias</h3><span class="suave pequeno">nota média da plataforma: ${g.nota_media_plataforma || "—"} ★</span></div>
        ${graficoBarras(g.visitas_por_dia, "data", "visitas")}
        ${g.visitas_30_dias ? "" : `<p class="suave pequeno">Ainda sem visitas: o gráfico cresce conforme as pessoas abrem o site.</p>`}</div>
      <div class="cartao"><h3>Usuários por tipo</h3>${rosca([{ nome: "Pacientes", valor: u.pacientes }, { nome: "Cuidadores", valor: u.cuidadores },
        { nome: "Familiares", valor: u.familiares }, { nome: "Equipe ativa", valor: u.equipe }])}</div>
    </div>`;
}

async function renderEquipe(caixa, menu) {
  const lista = await papi("/painel/equipe");
  caixa.innerHTML = topo("Equipe interna", "Cadastre quem trabalha na plataforma. Cada pessoa entra com o próprio e-mail e vê só a parte do seu papel.",
    `<button class="btn" id="novo-membro">+ Novo membro</button>`) + `
    <div class="cartao"><div class="tabela-caixa"><table class="responsiva"><thead><tr><th>Nome</th><th>E-mail</th><th>Papel</th><th>Situação</th><th></th></tr></thead><tbody>
    ${lista.map((m) => `<tr><td data-rotulo="Nome"><strong>${esc(m.nome)}</strong></td><td data-rotulo="E-mail">${esc(m.email)}</td>
      <td data-rotulo="Papel"><select data-papel="${m.id_equipe}" ${m.id_equipe === Sessao.pegar(CHAVE).id ? "disabled" : ""} style="min-height:34px;padding:4px 8px">
        ${Object.keys(NOMES_PAPEL).map((p) => `<option value="${p}" ${p === m.papel ? "selected" : ""}>${NOMES_PAPEL[p]}</option>`).join("")}</select></td>
      <td data-rotulo="Situação">${selo(m.status)}</td>
      <td class="num">${m.id_equipe === Sessao.pegar(CHAVE).id ? '<span class="suave pequeno">você</span>' : `
        <button class="btn btn-pequeno btn-claro" data-senha="${m.id_equipe}">Nova senha</button>
        <button class="btn btn-pequeno ${m.status === "ativo" ? "btn-perigo" : "btn-ok"}" data-status="${m.id_equipe}" data-novo="${m.status === "ativo" ? "inativo" : "ativo"}">${m.status === "ativo" ? "Desativar" : "Ativar"}</button>`}</td></tr>`).join("")}
    </tbody></table></div></div>`;
  const recarregar = () => renderEquipe(caixa, menu);
  el("#novo-membro", caixa).addEventListener("click", () => abrirJanela("Novo membro da equipe", `<form id="f-membro"><div class="grade-campos">
      <div class="campo inteiro"><label for="m-nome">Nome *</label><input id="m-nome" name="nome" required minlength="3"></div>
      <div class="campo inteiro"><label for="m-email">E-mail (login) *</label><input id="m-email" name="email" type="email" required placeholder="nome@cuidadopuro.com"></div>
      <div class="campo"><label for="m-cpf">CPF *</label><input id="m-cpf" name="cpf" required placeholder="000.000.000-00"></div>
      <div class="campo"><label for="m-tel">Telefone *</label><input id="m-tel" name="telefone" required></div>
      <div class="campo"><label for="m-cid">Cidade *</label><input id="m-cid" name="cidade" required value="Maringá"></div>
      <div class="campo"><label for="m-papel">Papel *</label><select id="m-papel" name="papel">${Object.keys(NOMES_PAPEL).filter((p) => p !== "ADM").map((p) => `<option value="${p}">${NOMES_PAPEL[p]}</option>`).join("")}<option value="ADM">Administrador</option></select></div>
      <div class="campo inteiro"><label for="m-senha">Senha inicial</label><input id="m-senha" name="senha" minlength="6" placeholder="Deixe em branco para o sistema gerar"></div>
    </div><div class="linha-botoes"><button class="btn" type="submit">Cadastrar</button></div></form>`, (c) => {
    el("#f-membro", c).addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        const r = await acao(papi("/painel/equipe", "POST", lerFormulario(e.target)), "Membro cadastrado!");
        abrirJanela("Acesso criado", `<p>Passe estes dados para <b>${esc(r.nome)}</b>:</p>
          <div class="destaque-caixa"><b>Endereço:</b> painel da equipe (Acesso da equipe)<br><b>E-mail:</b> ${esc(r.email)}<br><b>Senha:</b> <code style="font-size:1.1rem">${esc(r.senha_inicial)}</code></div>
          <p class="suave pequeno" style="margin-top:10px">A pessoa pode trocar a senha em "Minha conta", se quiser.</p>
          <div class="linha-botoes"><button class="btn" data-fechar>Entendi</button></div>`);
        recarregar();
      } catch (x) { }
    });
  }));
  els("[data-papel]", caixa).forEach((s) => s.addEventListener("change", async () => {
    try { await acao(papi("/painel/equipe/" + s.dataset.papel, "PATCH", { papel: s.value }), "Papel alterado."); } catch (x) { recarregar(); }
  }));
  els("[data-status]", caixa).forEach((b) => b.addEventListener("click", async () => {
    try { await acao(papi("/painel/equipe/" + b.dataset.status, "PATCH", { status: b.dataset.novo }), b.dataset.novo === "ativo" ? "Acesso reativado." : "Acesso desativado (o histórico continua guardado)."); recarregar(); } catch (x) { }
  }));
  els("[data-senha]", caixa).forEach((b) => b.addEventListener("click", async () => {
    try {
      const r = await papi(`/painel/equipe/${b.dataset.senha}/nova-senha`, "POST");
      abrirJanela("Nova senha", `<p>${esc(r.mensagem)}</p><div class="destaque-caixa">Senha: <code style="font-size:1.1rem">${esc(r.senha_inicial)}</code></div>
        <div class="linha-botoes"><button class="btn" data-fechar>OK</button></div>`);
    } catch (x) { aviso(x.message, "erro"); }
  }));
}

// ------------------------------------------------------------------
// SUPORTE
// ------------------------------------------------------------------
async function renderCadastros(caixa, menu, status = "pendente") {
  const lista = await papi("/painel/cadastros?status_cadastro=" + status);
  caixa.innerHTML = topo("Cadastros", "Confira os dados (e o COREN dos profissionais) antes de aprovar.") + `
    <div class="cartao"><div class="abas" style="max-width:420px">${["pendente", "aprovado", "recusado"].map((s) => `<button data-st="${s}" class="${s === status ? "ativo" : ""}">${s}s</button>`).join("")}</div>
    ${lista.length ? `<div class="lista">${lista.map((u) => `<div class="item" style="align-items:flex-start">${avatar(u.nome.split(" ").map((x) => x[0]).slice(0, 2).join(""), u.nome)}
      <div class="item-corpo"><strong>${esc(u.nome)} <span class="etiqueta">${u.tipo}</span></strong>
        <span class="suave pequeno">${esc(u.email)} · CPF ${esc(u.cpf)} · ${esc(u.telefone)} · ${esc(u.cidade)} · ${dataBR(u.data_criacao, true)}</span>
        <div class="pequeno" style="margin-top:6px">${Object.entries(u.detalhes).map(([k, v]) => `<div><b>${esc(k)}:</b> ${esc(v)}</div>`).join("")}</div></div>
      <div class="item-acoes">${status !== "aprovado" ? `<button class="btn btn-pequeno btn-ok" data-decidir="${u.tipo}/${u.id}" data-st="aprovado">Aprovar</button>` : ""}
        ${status !== "recusado" ? `<button class="btn btn-pequeno btn-perigo" data-decidir="${u.tipo}/${u.id}" data-st="recusado">Recusar</button>` : ""}</div></div>`).join("")}</div>`
      : vazio(`Nenhum cadastro ${status}.`)}</div>`;
  els(".abas [data-st]", caixa).forEach((b) => b.addEventListener("click", () => renderCadastros(caixa, menu, b.dataset.st)));
  els("[data-decidir]", caixa).forEach((b) => b.addEventListener("click", async () => {
    try { await acao(papi("/painel/cadastros/" + b.dataset.decidir, "POST", { status: b.dataset.st }), (r) => r.mensagem); renderCadastros(caixa, menu, status); } catch (x) { }
  }));
}

async function renderUsuarios(caixa) {
  const lista = await papi("/painel/usuarios");
  caixa.innerHTML = topo("Usuários", `${lista.length} pessoas cadastradas.`) + `<div class="cartao">
    <div class="campo" style="max-width:340px"><label for="filtro">Procurar</label><input id="filtro" placeholder="Nome, e-mail ou tipo"></div>
    <div class="tabela-caixa"><table class="responsiva"><thead><tr><th>Nome</th><th>Tipo</th><th>Plano</th><th>Cidade</th><th>Situação</th><th>Desde</th></tr></thead><tbody id="corpo-usuarios"></tbody></table></div></div>`;
  const desenhar = (f = "") => {
    const t = f.toLowerCase();
    el("#corpo-usuarios", caixa).innerHTML = lista.filter((u) => !t || `${u.nome} ${u.email} ${u.tipo}`.toLowerCase().includes(t)).map((u) => `<tr>
      <td data-rotulo="Nome"><strong>${esc(u.nome)}</strong><br><span class="suave pequeno">${esc(u.email)}</span></td><td data-rotulo="Tipo">${esc(u.tipo)}</td>
      <td data-rotulo="Plano">${esc(u.plano)}</td><td data-rotulo="Cidade">${esc(u.cidade)}</td><td data-rotulo="Situação">${selo(u.status)}</td><td data-rotulo="Desde">${dataBR(u.data_criacao)}</td></tr>`).join("");
  };
  el("#filtro", caixa).addEventListener("input", (e) => desenhar(e.target.value));
  desenhar();
}

// ------------------------------------------------------------------
// SAC
// ------------------------------------------------------------------
async function renderSac(caixa) {
  const [avaliacoes, chamados] = await Promise.all([papi("/painel/sac/avaliacoes"), papi("/painel/sac/chamados")]);
  caixa.innerHTML = topo("SAC", "Avaliações ruins (nota 1 ou 2) e mensagens enviadas pelo site e pelos usuários.") + `
    <div class="cartao"><h3>⚠️ Avaliações ruins</h3>${avaliacoes.length ? `<div class="lista">${avaliacoes.map((a) => `<div class="item" style="align-items:flex-start">
      <div class="item-corpo"><strong>${estrelas(a.nota)} · ${esc(a.paciente.nome)} avaliou ${esc(a.cuidador.nome)}</strong>
        <div>"${esc(a.comentario || "sem comentário")}"</div>
        <span class="suave pequeno">${dataBR(a.criado_em, true)} · paciente: ${esc(a.paciente.telefone)} · cuidador: ${esc(a.cuidador.telefone)}</span></div>
      <div class="item-acoes"><select data-aval="${a.id_avaliacao}" style="min-height:34px;padding:4px 8px">${["nova", "em contato", "resolvida"].map((s) => `<option ${s === a.status_sac ? "selected" : ""}>${s}</option>`).join("")}</select></div></div>`).join("")}</div>` : vazio("Nenhuma avaliação ruim. 🎉")}</div>
    <div class="cartao"><h3>📨 Chamados</h3>${chamados.length ? `<div class="lista">${chamados.map((c) => `<div class="item" style="align-items:flex-start">
      <div class="item-corpo"><strong>${esc(c.assunto)} ${selo(c.status)}</strong><span class="suave pequeno">${esc(c.nome)} (${esc(c.autor_tipo)}) · ${esc(c.email)} · ${dataBR(c.criado_em, true)}</span>
        <div class="pequeno">${esc(c.mensagem)}</div>${c.resposta ? `<div class="destaque-caixa pequeno" style="margin-top:6px"><b>Resposta:</b> ${esc(c.resposta)}</div>` : ""}</div>
      <div class="item-acoes"><button class="btn btn-pequeno" data-chamado="${c.id_chamado}">Responder</button></div></div>`).join("")}</div>` : vazio("Nenhum chamado.")}</div>`;
  els("[data-aval]", caixa).forEach((s) => s.addEventListener("change", async () => {
    try { await acao(papi("/painel/sac/avaliacoes/" + s.dataset.aval, "PATCH", { status_sac: s.value }), "Situação atualizada."); } catch (x) { }
  }));
  els("[data-chamado]", caixa).forEach((b) => b.addEventListener("click", () => {
    const c = chamados.find((x) => String(x.id_chamado) === b.dataset.chamado);
    abrirJanela("Responder chamado", `<p><b>${esc(c.assunto)}</b><br>${esc(c.mensagem)}</p><form id="f-resp">
      <div class="campo"><label for="resposta">Resposta</label><textarea id="resposta" name="resposta">${esc(c.resposta || "")}</textarea></div>
      <div class="campo"><label for="st">Situação</label><select id="st" name="status">${["aberto", "em andamento", "resolvido"].map((s) => `<option ${s === c.status ? "selected" : ""}>${s}</option>`).join("")}</select></div>
      <div class="linha-botoes"><button class="btn" type="submit">Salvar</button></div></form>`, (j) => {
      el("#f-resp", j).addEventListener("submit", async (e) => {
        e.preventDefault();
        try { await acao(papi("/painel/sac/chamados/" + c.id_chamado, "PATCH", lerFormulario(e.target)), "Chamado atualizado. O usuário vê a resposta no painel dele."); fecharJanela(); renderSac(caixa); } catch (x) { }
      });
    });
  }));
}

// ------------------------------------------------------------------
// FINANCEIRO
// ------------------------------------------------------------------
async function renderFinanceiro(caixa, menu, ref, filtro = "") {
  const f = await papi(`/painel/financeiro?${ref ? "referencia_mes=" + ref + "&" : ""}${filtro ? "status_pagamento=" + filtro : ""}`);
  const r = f.resumo;
  caixa.innerHTML = topo("Financeiro", "Mensalidades de pacientes e cuidadores (Pix simulado).", `<button class="btn btn-claro" id="gerar">Gerar mensalidades do próximo mês</button>`) + `
    <div class="cartao" style="display:flex;gap:12px;flex-wrap:wrap;align-items:end">
      <div><label for="ref">Mês</label><select id="ref">${f.meses.map((m) => `<option value="${m}" ${m === f.referencia ? "selected" : ""}>${mes(m)}</option>`).join("")}</select></div>
      <div><label for="filtro-st">Situação</label><select id="filtro-st"><option value="">Todas</option>${["pago", "pendente", "atrasado"].map((s) => `<option ${s === filtro ? "selected" : ""}>${s}</option>`).join("")}</select></div></div>
    <div class="grade grade-3" style="margin-top:16px">
      ${numero("Recebido", reais(r.pago.valor), `${r.pago.quantidade} pagas`)}
      ${numero("Pendente", reais(r.pendente.valor), `${r.pendente.quantidade} no prazo`, "aviso")}
      ${numero("Atrasado", reais(r.atrasado.valor), `${r.atrasado.quantidade} vencidas`, r.atrasado.quantidade ? "perigo" : "")}</div>
    <div class="grade grade-2" style="margin-top:16px">
      <div class="cartao"><h3>Recebido por mês</h3>${graficoBarras(f.historico.map((h) => ({ mes: mes(h.referencia).slice(0, 5), v: Math.round(h.recebido) })), "mes", "v")}</div>
      <div class="cartao"><h3>Situação do mês</h3>${rosca([{ nome: "Pagas", valor: r.pago.quantidade }, { nome: "Pendentes", valor: r.pendente.quantidade }, { nome: "Atrasadas", valor: r.atrasado.quantidade }])}</div></div>
    <div class="cartao"><div class="tabela-caixa"><table class="responsiva"><thead><tr><th>Usuário</th><th>Tipo</th><th>Plano</th><th>Vencimento</th><th class="num">Valor</th><th>Situação</th><th></th></tr></thead><tbody>
    ${f.mensalidades.map((m) => `<tr><td data-rotulo="Usuário"><strong>${esc(m.usuario)}</strong></td><td data-rotulo="Tipo">${esc(m.tipo_usuario)}</td><td data-rotulo="Plano">${esc(m.plano)}</td>
      <td data-rotulo="Vencimento">${dataBR(m.data_vencimento)}</td><td class="num" data-rotulo="Valor">${reais(m.valor)}${m.codigo_cupom ? ` <span class="etiqueta">${esc(m.codigo_cupom)}</span>` : ""}</td>
      <td data-rotulo="Situação">${selo(m.status_pagamento)}</td>
      <td class="num">${m.status_pagamento !== "pago" ? `<button class="btn btn-pequeno btn-claro" data-pago="${m.id_assinatura}">Dar baixa</button>` : `<span class="suave pequeno">${dataBR(m.data_pagamento)}</span>`}</td></tr>`).join("") || `<tr><td colspan="7">${vazio("Nenhuma mensalidade.")}</td></tr>`}
    </tbody></table></div></div>`;
  el("#ref", caixa).addEventListener("change", (e) => renderFinanceiro(caixa, menu, e.target.value, filtro));
  el("#filtro-st", caixa).addEventListener("change", (e) => renderFinanceiro(caixa, menu, f.referencia, e.target.value));
  el("#gerar", caixa).addEventListener("click", async () => {
    try { await acao(papi("/painel/financeiro/gerar-proximo-mes", "POST"), (x) => `${x.criadas} mensalidade(s) criada(s) para ${mes(x.referencia)}.`); renderFinanceiro(caixa, menu, f.referencia, filtro); } catch (x) { }
  });
  els("[data-pago]", caixa).forEach((b) => b.addEventListener("click", async () => {
    if (!(await confirmar("Dar baixa manual nesta mensalidade (pagamento confirmado por fora)?", "Dar baixa"))) return;
    try { await acao(papi(`/painel/financeiro/${b.dataset.pago}/marcar-pago`, "POST"), "Baixa registrada."); renderFinanceiro(caixa, menu, f.referencia, filtro); } catch (x) { }
  }));
}

// ------------------------------------------------------------------
// MARKETING
// ------------------------------------------------------------------
async function renderMarketing(caixa) {
  const m = await papi("/painel/marketing");
  caixa.innerHTML = topo("Marketing", "Divulgação, captação de clientes e parcerias.") + `
    <div class="grade grade-3">${numero("Visitas (30 dias)", m.visitas_30_dias, "acessos reais")}
      ${numero("Novos cadastros (30 dias)", m.cadastros_30_dias, "pacientes + cuidadores")}
      ${numero("Conversão", m.conversao === null ? "—" : m.conversao + "%", "cadastros ÷ visitas")}</div>
    <div class="grade grade-2" style="margin-top:16px">
      <div class="cartao"><h3>Visitas · 14 dias</h3>${graficoBarras(m.visitas_por_dia, "data", "visitas")}</div>
      <div class="cartao"><h3>Como conheceram o Cuidado Puro</h3>${barrasHorizontais(m.origem_cadastros)}
        <h3 style="margin-top:16px">Sites que trouxeram visitas</h3>${barrasHorizontais(Object.fromEntries(Object.entries(m.sites_de_origem).map(([k, v]) => [k.replace(/^https?:\/\/(www\.)?/, "").split("/")[0], v])))}</div></div>
    <div class="cartao"><div class="cartao-topo"><h3>🤝 Parcerias</h3><button class="btn btn-pequeno" id="nova-parceria">+ Parceria</button></div>
      ${m.parcerias.length ? `<div class="tabela-caixa"><table class="responsiva"><thead><tr><th>Nome</th><th>Tipo</th><th>Contato</th><th>Situação</th><th></th></tr></thead><tbody>
      ${m.parcerias.map((p) => `<tr><td data-rotulo="Nome"><strong>${esc(p.nome)}</strong>${p.observacoes ? `<br><span class="suave pequeno">${esc(p.observacoes)}</span>` : ""}</td><td data-rotulo="Tipo">${esc(p.tipo)}</td>
        <td data-rotulo="Contato">${esc(p.contato || "—")}<br><span class="suave pequeno">${esc(p.telefone || "")}</span></td>
        <td data-rotulo="Situação"><select data-parceria="${p.id}" style="min-height:34px;padding:4px 8px">${["prospecção", "negociação", "ativa", "encerrada"].map((s) => `<option ${s === p.status ? "selected" : ""}>${s}</option>`).join("")}</select></td>
        <td class="num"><button class="btn-icone" data-apagar-parceria="${p.id}" aria-label="Apagar">🗑</button></td></tr>`).join("")}</tbody></table></div>` : vazio("Nenhuma parceria.")}</div>
    <div class="grade grade-2">
      <div class="cartao"><div class="cartao-topo"><h3>📣 Campanhas</h3><button class="btn btn-pequeno" id="nova-campanha">+ Campanha</button></div>
        ${m.campanhas.length ? `<div class="lista">${m.campanhas.map((c) => `<div class="item"><div class="item-corpo"><strong>${esc(c.nome)} ${selo(c.status)}</strong>
          <span class="suave pequeno">${esc(c.canal)} · ${dataBR(c.data_inicio)} a ${dataBR(c.data_fim)}</span>${c.objetivo ? `<div class="pequeno">${esc(c.objetivo)}</div>` : ""}</div>
          <button class="btn-icone" data-apagar-campanha="${c.id}" aria-label="Apagar">🗑</button></div>`).join("")}</div>` : vazio("Nenhuma campanha.")}</div>
      <div class="cartao"><div class="cartao-topo"><h3>🎟️ Cupons de desconto</h3><button class="btn btn-pequeno" id="novo-cupom">+ Cupom</button></div>
        ${m.cupons.length ? `<div class="lista">${m.cupons.map((c) => `<div class="item"><div class="item-corpo"><strong><code>${esc(c.codigo)}</code> · ${c.desconto_percentual}% ${selo(c.valido ? "ativo" : "inativo")}</strong>
          <span class="suave pequeno">válido até ${dataBR(c.validade)} · usado ${c.usos} vez(es)</span></div>
          <button class="btn btn-pequeno btn-claro" data-cupom="${c.id}">${c.ativo ? "Desativar" : "Ativar"}</button></div>`).join("")}</div>` : vazio("Nenhum cupom.")}</div></div>`;
  const recarregar = () => renderMarketing(caixa);
  const formJanela = (titulo, campos, rota, msg) => abrirJanela(titulo, `<form id="f-mk"><div class="grade-campos">${campos}</div>
    <div class="linha-botoes"><button class="btn" type="submit">Salvar</button></div></form>`, (c) => {
    el("#f-mk", c).addEventListener("submit", async (e) => {
      e.preventDefault();
      try { await acao(papi(rota, "POST", lerFormulario(e.target)), msg); fecharJanela(); recarregar(); } catch (x) { }
    });
  });
  el("#nova-parceria", caixa).addEventListener("click", () => formJanela("Nova parceria", `
    <div class="campo inteiro"><label for="pn">Nome *</label><input id="pn" name="nome" required placeholder="Ex.: Hospital Municipal"></div>
    <div class="campo"><label for="pt">Tipo *</label><select id="pt" name="tipo">${["hospital", "clínica", "operadora", "farmácia", "outro"].map((t) => `<option>${t}</option>`).join("")}</select></div>
    <div class="campo"><label for="ps">Situação</label><select id="ps" name="status">${["prospecção", "negociação", "ativa"].map((t) => `<option>${t}</option>`).join("")}</select></div>
    <div class="campo"><label for="pc">Contato</label><input id="pc" name="contato"></div><div class="campo"><label for="ptel">Telefone</label><input id="ptel" name="telefone"></div>
    <div class="campo inteiro"><label for="po">Observações</label><textarea id="po" name="observacoes"></textarea></div>`, "/painel/marketing/parcerias", "Parceria cadastrada!"));
  el("#nova-campanha", caixa).addEventListener("click", () => formJanela("Nova campanha", `
    <div class="campo inteiro"><label for="cn">Nome *</label><input id="cn" name="nome" required></div>
    <div class="campo"><label for="cc">Canal *</label><input id="cc" name="canal" required placeholder="Instagram, WhatsApp, feira..."></div>
    <div class="campo"><label for="cs">Situação</label><select id="cs" name="status"><option>planejada</option><option>ativa</option><option>encerrada</option></select></div>
    <div class="campo"><label for="ci">Início *</label><input id="ci" name="data_inicio" type="date" required value="${hojeISO()}"></div>
    <div class="campo"><label for="cf">Fim *</label><input id="cf" name="data_fim" type="date" required></div>
    <div class="campo inteiro"><label for="co">Objetivo</label><input id="co" name="objetivo"></div>`, "/painel/marketing/campanhas", "Campanha cadastrada!"));
  el("#novo-cupom", caixa).addEventListener("click", () => formJanela("Novo cupom", `
    <div class="campo"><label for="uc">Código *</label><input id="uc" name="codigo" required placeholder="Ex.: NATAL20" style="text-transform:uppercase"></div>
    <div class="campo"><label for="ud">Desconto (%) *</label><input id="ud" name="desconto_percentual" type="number" min="1" max="100" required value="10"></div>
    <div class="campo inteiro"><label for="uv">Válido até *</label><input id="uv" name="validade" type="date" required></div>`, "/painel/marketing/cupons", "Cupom criado! Já funciona no Pix."));
  els("[data-parceria]", caixa).forEach((s) => s.addEventListener("change", async () => {
    const p = m.parcerias.find((x) => String(x.id) === s.dataset.parceria);
    try { await acao(papi("/painel/marketing/parcerias/" + p.id, "PATCH", { ...p, status: s.value }), "Parceria atualizada."); } catch (x) { }
  }));
  els("[data-apagar-parceria]", caixa).forEach((b) => b.addEventListener("click", async () => {
    if (!(await confirmar("Apagar esta parceria?", "Apagar"))) return;
    try { await acao(papi("/painel/marketing/parcerias/" + b.dataset.apagarParceria, "DELETE"), "Parceria apagada."); recarregar(); } catch (x) { }
  }));
  els("[data-apagar-campanha]", caixa).forEach((b) => b.addEventListener("click", async () => {
    if (!(await confirmar("Apagar esta campanha?", "Apagar"))) return;
    try { await acao(papi("/painel/marketing/campanhas/" + b.dataset.apagarCampanha, "DELETE"), "Campanha apagada."); recarregar(); } catch (x) { }
  }));
  els("[data-cupom]", caixa).forEach((b) => b.addEventListener("click", async () => {
    try { await acao(papi(`/painel/marketing/cupons/${b.dataset.cupom}/alternar`, "POST"), (r) => r.ativo ? "Cupom ativado." : "Cupom desativado."); recarregar(); } catch (x) { }
  }));
}

// ------------------------------------------------------------------
// COMERCIAL
// ------------------------------------------------------------------
async function renderComercial(caixa) {
  const c = await papi("/painel/comercial");
  caixa.innerHTML = topo("Comercial", "Preço e regras dos planos. O novo valor já aparece no site e vale para as próximas mensalidades.") + `
    <div class="grade grade-2"><div class="cartao"><h3>Assinantes por plano</h3>${rosca(c.planos.map((p) => ({ nome: p.nome, valor: p.assinantes })))}</div>
      ${numero("Receita mensal prevista", reais(c.receita_mensal_prevista), "se todos os aprovados pagarem")}</div>
    <div class="cartao"><div class="tabela-caixa"><table class="responsiva"><thead><tr><th>Plano</th><th>Público</th><th class="num">Valor</th><th>Regras</th><th class="num">Assinantes</th><th class="num">Receita</th><th></th></tr></thead><tbody>
    ${c.planos.map((p) => `<tr><td data-rotulo="Plano"><strong>${esc(p.nome)}</strong><br><span class="suave pequeno">${esc(p.descricao)}</span></td><td data-rotulo="Público">${esc(p.publico)}</td>
      <td class="num" data-rotulo="Valor">${reais(p.valor)}</td>
      <td data-rotulo="Regras">${p.publico === "cuidador" ? `<div class="etiquetas"><span class="etiqueta">${p.limite_conversas ? "até " + p.limite_conversas + " conversas" : "conversas ilimitadas"}</span>
        ${p.pode_iniciar_conversa ? '<span class="etiqueta">chama pacientes</span>' : ""}${p.destaque ? '<span class="etiqueta">destaque</span>' : ""}${p.relatorio ? '<span class="etiqueta">relatório</span>' : ""}</div>` : "—"}</td>
      <td class="num" data-rotulo="Assinantes">${p.assinantes}</td><td class="num" data-rotulo="Receita">${reais(p.receita_prevista)}</td>
      <td class="num"><button class="btn btn-pequeno" data-plano="${p.id}">Editar</button></td></tr>`).join("")}</tbody></table></div></div>`;
  els("[data-plano]", caixa).forEach((b) => b.addEventListener("click", () => {
    const p = c.planos.find((x) => String(x.id) === b.dataset.plano);
    abrirJanela("Editar plano " + p.nome, `<form id="f-plano"><div class="campo"><label for="pv">Valor mensal (R$) *</label><input id="pv" name="valor" type="number" step="0.01" min="1" required value="${p.valor}"></div>
      <div class="campo"><label for="pd">Descrição</label><textarea id="pd" name="descricao">${esc(p.descricao)}</textarea></div>
      ${p.publico === "cuidador" ? `<div class="campo"><label for="pl">Limite de conversas abertas</label><input id="pl" name="limite_conversas" type="number" min="1" value="${p.limite_conversas || ""}" placeholder="vazio = ilimitado"></div>` : ""}
      <div class="linha-botoes"><button class="btn" type="submit">Salvar</button></div></form>`, (j) => {
      el("#f-plano", j).addEventListener("submit", async (e) => {
        e.preventDefault();
        const d = lerFormulario(e.target);
        if (p.publico === "cuidador" && d.limite_conversas === null) { d.sem_limite = true; delete d.limite_conversas; }
        try { await acao(papi("/painel/comercial/planos/" + p.id, "PATCH", d), "Plano atualizado!"); fecharJanela(); renderComercial(caixa); } catch (x) { }
      });
    });
  }));
}

// ------------------------------------------------------------------
// FRONTEND, BACKEND e BANCO
// ------------------------------------------------------------------
function listaErros(erros) {
  return erros.length ? `<div class="lista">${erros.map((e) => `<div class="item" style="align-items:flex-start"><div class="item-corpo">
    <strong style="color:var(--perigo)">${esc(e.mensagem)}</strong><span class="suave pequeno">${dataBR(e.criado_em, true)} · ${esc(e.pagina || "")}</span>
    ${e.detalhe ? `<details><summary class="pequeno">detalhes</summary><pre class="pequeno" style="white-space:pre-wrap;overflow-x:auto">${esc(e.detalhe)}</pre></details>` : ""}</div></div>`).join("")}</div>`
    : vazio("Nenhum erro registrado. 🎉");
}

async function renderFrontend(caixa) {
  const f = await papi("/painel/frontend");
  caixa.innerHTML = topo("Frontend", "O site visto de dentro: páginas mais usadas e erros de JavaScript que os usuários tiveram.") + `
    <div class="grade grade-2"><div class="cartao"><h3>Páginas mais acessadas</h3>${barrasHorizontais(Object.fromEntries(f.paginas_mais_acessadas.map((p) => [p.pagina.replace("/telas/", "").replace(".html", "") || "início", p.visitas])))}</div>
      <div class="cartao"><h3>Visitas · 14 dias</h3>${graficoBarras(f.visitas_por_dia, "data", "visitas")}</div></div>
    <div class="cartao"><div class="cartao-topo"><h3>Erros do site (${f.total_erros})</h3>${f.total_erros ? `<button class="btn btn-pequeno btn-claro" id="limpar">Limpar lista</button>` : ""}</div>${listaErros(f.erros)}</div>`;
  const l = el("#limpar", caixa);
  if (l) l.addEventListener("click", async () => { try { await acao(papi("/painel/logs/site", "DELETE"), "Lista limpa."); renderFrontend(caixa); } catch (x) { } });
}

async function renderBackend(caixa) {
  const b = await papi("/painel/backend");
  caixa.innerHTML = topo("Backend", "Saúde da API. Os contadores zeram quando o uvicorn reinicia.", `<a class="btn btn-claro" href="${API_BASE_URL.replace(/\/api$/, "")}/docs" target="_blank" rel="noopener">Abrir Swagger ↗</a>`) + `
    <div class="grade grade-4">${numero("Status", "● online", "API respondendo")}${numero("No ar há", b.tempo_no_ar, "desde " + dataBR(b.no_ar_desde, true))}
      ${numero("Requisições", b.requisicoes, "desde que ligou")}${numero("Tempo médio", b.tempo_medio_ms + " ms", `${b.erros_500} erro(s) 500`, b.erros_500 ? "perigo" : "")}</div>
    <div class="grade grade-2" style="margin-top:16px">
      <div class="cartao"><h3>Rotas mais usadas</h3><div class="tabela-caixa"><table class="responsiva"><thead><tr><th>Rota</th><th class="num">Chamadas</th><th class="num">Tempo médio</th></tr></thead><tbody>
        ${b.rotas_mais_usadas.map((r) => `<tr><td data-rotulo="Rota"><code class="pequeno">${esc(r.rota)}</code></td><td class="num" data-rotulo="Chamadas">${r.chamadas}</td><td class="num" data-rotulo="Tempo">${r.tempo_medio_ms} ms</td></tr>`).join("")}</tbody></table></div></div>
      <div class="cartao"><div class="cartao-topo"><h3>Erros da API (${b.total_erros})</h3>${b.total_erros ? `<button class="btn btn-pequeno btn-claro" id="limpar">Limpar lista</button>` : ""}</div>${listaErros(b.erros)}</div></div>`;
  const l = el("#limpar", caixa);
  if (l) l.addEventListener("click", async () => { try { await acao(papi("/painel/logs/api", "DELETE"), "Lista limpa."); renderBackend(caixa); } catch (x) { } });
}

async function renderBanco(caixa) {
  const d = await papi("/painel/banco");
  caixa.innerHTML = topo("Banco de dados", "SQLite em modo WAL. Arquivo: " + esc(d.arquivo), `<button class="btn" id="backup">⬇ Baixar backup</button>`) + `
    <div class="grade grade-4">${numero("Tamanho", d.tamanho_kb + " KB", `+ ${d.tamanho_wal_kb} KB no arquivo -wal`)}${numero("Tabelas", d.total_tabelas)}
      ${numero("Linhas", d.total_linhas, "somando todas as tabelas")}${numero("Integridade", d.integridade === "ok" ? "✔ ok" : esc(d.integridade), "PRAGMA integrity_check", d.integridade === "ok" ? "" : "perigo")}</div>
    <div class="cartao" style="margin-top:16px"><h3>Linhas por tabela</h3>${barrasHorizontais(Object.fromEntries(d.tabelas.map((t) => [t.tabela, t.linhas || 0])))}</div>
    <div class="cartao"><h3>Para zerar o banco (dias da feira)</h3><p class="suave">Desligue a API (Ctrl+C) e rode no terminal: <code>python3 carregar_exemplos.py</code>. O banco volta só com os dados de exemplo.</p></div>`;
  el("#backup", caixa).addEventListener("click", async () => {
    try {
      const arquivo = await papi("/painel/banco/backup");
      const link = document.createElement("a");
      link.href = URL.createObjectURL(arquivo);
      link.download = `cuidado_puro_backup_${hojeISO()}.db`;
      link.click();
      aviso("Backup baixado! Guarde no Drive ou num pen drive.");
    } catch (x) { aviso(x.message, "erro"); }
  });
}

function renderConta(caixa, menu) {
  caixa.innerHTML = topo("Minha conta", `${esc(menu.nome)} · ${esc(NOMES_PAPEL[menu.papel])}`) + `<div class="grade grade-2">
    <div class="cartao"><h3>Trocar senha</h3><p class="suave pequeno">Opcional: se quiser, mantenha a senha que o ADM passou.</p><form id="f-senha">
      <div class="campo"><label for="sa">Senha atual</label><input id="sa" name="senha_atual" type="password" required></div>
      <div class="campo"><label for="sn">Nova senha</label><input id="sn" name="senha_nova" type="password" minlength="6" required></div>
      <button class="btn" type="submit">Salvar</button></form></div>
    <div class="cartao"><h3>O que o seu papel vê</h3><p>${menu.secoes.filter((s) => s !== "conta").map((s) => SECOES[s][1]).join(", ")}</p></div></div>`;
  el("#f-senha", caixa).addEventListener("submit", async (e) => {
    e.preventDefault();
    try { await acao(papi("/me/senha", "POST", lerFormulario(e.target)), "Senha alterada!"); e.target.reset(); } catch (x) { }
  });
}

const RENDER = { geral: renderGeral, equipe: renderEquipe, cadastros: (c, m) => renderCadastros(c, m), usuarios: renderUsuarios, sac: renderSac,
  financeiro: (c, m) => renderFinanceiro(c, m), marketing: renderMarketing, comercial: renderComercial, frontend: renderFrontend,
  backend: renderBackend, banco: renderBanco, conta: renderConta };

iniciar();
