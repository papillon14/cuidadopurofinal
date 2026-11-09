// dashboard-comum.js -> partes iguais nos dashboards do paciente, do cuidador e da família

const ICONES = {
  inicio: "🏠", buscar: "🔎", conversas: "💬", pedidos: "📨", agenda: "📅", saude: "❤️", pacientes: "🧑‍⚕️",
  familia: "👪", plano: "⭐", mensalidade: "💳", ajuda: "🛟", conta: "⚙️",
};

// Monta o menu lateral e o topo com o nome do usuário
function montarEstrutura(sessao, itens, subtitulo) {
  el(".lateral nav").innerHTML = itens.map(([id, nome, href]) => href
    ? `<a href="${href}"><span class="icone">${ICONES[id]}</span>${nome}<span class="contador escondido" id="cont-${id}"></span></a>`
    : `<a href="#${id}" data-secao="${id}"><span class="icone">${ICONES[id]}</span>${nome}<span class="contador escondido" id="cont-${id}"></span></a>`).join("");
  el(".usuario-caixa").innerHTML = `${avatar(sessao.iniciais || "?", sessao.nome)}
    <div><strong>${esc(sessao.nome)}</strong><small>${esc(subtitulo)}</small></div>
    <button class="btn-icone" id="sair" title="Sair" aria-label="Sair">⎋</button>`;
  el("#sair").addEventListener("click", sair);
  el(".conteudo").innerHTML = itens.filter((i) => !i[2]).map(([id]) => `<section class="secao escondido" id="secao-${id}"></section>`).join("");
}

async function sair() {
  try { await api("/logout", "POST"); } catch (e) { /* já saiu */ }
  Sessao.limpar();
  location.href = "telaLogin.html";
}

function contador(id, n) {
  const c = el("#cont-" + id);
  if (!c) return;
  c.textContent = n;
  c.classList.toggle("escondido", !n);
}

function topo(titulo, texto, botoes = "") {
  return `<div class="topo-pagina"><div><h1>${titulo}</h1>${texto ? `<p>${texto}</p>` : ""}</div><div>${botoes}</div></div>`;
}

// ------------------------------------------------------------------
// AGENDA (paciente, cuidador e família)
// ------------------------------------------------------------------
function itemAgenda(a, souCuidador, somenteLeitura) {
  const d = new Date(a.data + "T12:00:00");
  const outro = souCuidador ? a.paciente.nome : a.cuidador.nome;
  const botoes = [];
  if (!somenteLeitura) {
    if (a.posso_confirmar) botoes.push(`<button class="btn btn-pequeno btn-ok" data-acao="confirmar" data-id="${a.id_cuidado}">Confirmar</button>
                                        <button class="btn btn-pequeno btn-claro" data-acao="recusar" data-id="${a.id_cuidado}">Recusar</button>`);
    if (souCuidador && a.status === "agendado") botoes.push(`<button class="btn btn-pequeno" data-acao="iniciar" data-id="${a.id_cuidado}">▶ Iniciar</button>`);
    if (souCuidador && ["agendado", "em andamento"].includes(a.status)) botoes.push(`<button class="btn btn-pequeno btn-ok" data-acao="concluir" data-id="${a.id_cuidado}">✔ Concluir</button>`);
    if (souCuidador && ["em andamento", "concluído"].includes(a.status)) botoes.push(`<button class="btn btn-pequeno btn-claro" data-acao="registro" data-id="${a.id_cuidado}" data-paciente="${a.paciente.id}">📝 Registro de saúde</button>`);
    if (a.posso_avaliar) botoes.push(`<button class="btn btn-pequeno" data-acao="avaliar" data-id="${a.id_cuidado}">⭐ Avaliar</button>`);
    if (["proposto", "agendado"].includes(a.status) && !a.posso_confirmar) botoes.push(`<button class="btn btn-pequeno btn-claro" data-acao="cancelar" data-id="${a.id_cuidado}">Cancelar</button>`);
  }
  const tarefas = a.tarefas.length ? `<div class="etiquetas">${a.tarefas.map((t) => souCuidador && !somenteLeitura && ["em andamento", "agendado"].includes(a.status)
    ? `<label class="etiqueta" style="cursor:pointer"><input type="checkbox" data-tarefa="${t.id}" data-cuidado="${a.id_cuidado}" ${t.realizado ? "checked" : ""}> ${esc(t.descricao)}</label>`
    : `<span class="etiqueta">${t.realizado ? "✅" : "⬜"} ${esc(t.descricao)}</span>`).join("")}</div>` : "";
  return `<div class="item">
    <div class="item-data"><b>${d.getDate()}</b><span>${d.toLocaleDateString("pt-BR", { month: "short" }).replace(".", "")} · ${diaSemana(a.data)}</span></div>
    <div class="item-corpo"><strong>${esc(a.tipo[0].toUpperCase() + a.tipo.slice(1))} · ${horario(a)} ${selo(a.status)}</strong>
      <span class="suave pequeno">com ${esc(outro)}${souCuidador ? ` · ${esc(a.paciente.endereco)}` : ""}${a.grupo_repeticao ? " · escala" : ""}</span>
      ${a.observacoes ? `<div class="pequeno">${esc(a.observacoes)}</div>` : ""}
      ${a.status === "proposto" && !a.posso_confirmar ? `<div class="pequeno suave">Aguardando a confirmação de ${esc(outro)}.</div>` : ""}
      ${tarefas}
      ${a.avaliacao ? `<div class="pequeno">Avaliação: ${estrelas(a.avaliacao.nota)} ${a.avaliacao.comentario ? "— " + esc(a.avaliacao.comentario) : ""}</div>` : ""}
    </div>
    <div class="item-acoes">${botoes.join("")}</div></div>`;
}

async function renderAgenda(caixa, souCuidador, somenteLeitura, aoMudar) {
  caixa.innerHTML = topo("Agenda", souCuidador ? "Inicie, conclua e registre como o paciente está." :
    somenteLeitura ? "Atendimentos combinados (somente leitura)." : "Atendimentos combinados no chat. Depois de concluído, avalie o cuidador.") +
    `<div class="cartao"><div class="abas" style="max-width:360px"><button data-periodo="futuros" class="ativo">Próximos</button><button data-periodo="passados">Anteriores</button></div><div id="lista-agenda"></div></div>`;
  let periodo = "futuros";
  async function carregar() {
    const lista = await api("/agenda?periodo=" + periodo);
    if (periodo === "passados") lista.reverse();
    el("#lista-agenda", caixa).innerHTML = lista.length ? `<div class="lista">${lista.map((a) => itemAgenda(a, souCuidador, somenteLeitura)).join("")}</div>`
      : vazio(periodo === "futuros" ? "Nenhum atendimento marcado. Combine pelo chat e use o botão 📅 Propor agendamento." : "Nenhum atendimento anterior.");
  }
  els("[data-periodo]", caixa).forEach((b) => b.addEventListener("click", () => {
    periodo = b.dataset.periodo;
    els("[data-periodo]", caixa).forEach((x) => x.classList.toggle("ativo", x === b));
    carregar();
  }));
  // os botões são ligados UMA vez só; a função de recarregar é trocada a cada abertura
  caixa._recarregarAgenda = async () => { await carregar(); if (aoMudar) aoMudar(); };
  if (!caixa._agendaLigada) {
    ligarAcoesAgenda(caixa, () => caixa._recarregarAgenda());
    caixa._agendaLigada = true;
  }
  await carregar();
}

function ligarAcoesAgenda(caixa, recarregar) {
  caixa.addEventListener("click", async (e) => {
    const b = e.target.closest("[data-acao]");
    if (!b) return;
    const id = b.dataset.id;
    try {
      if (b.dataset.acao === "confirmar") await acao(api(`/agendamentos/${id}/responder`, "POST", { aceitar: true }), (r) => `${r.quantidade} atendimento(s) confirmado(s)!`);
      if (b.dataset.acao === "recusar") await acao(api(`/agendamentos/${id}/responder`, "POST", { aceitar: false }), "Proposta recusada.");
      if (b.dataset.acao === "iniciar") await acao(api(`/agendamentos/${id}/iniciar`, "POST"), "Atendimento iniciado.");
      if (b.dataset.acao === "concluir") await acao(api(`/agendamentos/${id}/concluir`, "POST"), "Atendimento concluído! O paciente já pode avaliar.");
      if (b.dataset.acao === "cancelar") {
        if (!(await confirmar("Cancelar este atendimento?", "Cancelar atendimento"))) return;
        await acao(api(`/agendamentos/${id}/cancelar`, "POST"), "Atendimento cancelado.");
      }
      if (b.dataset.acao === "avaliar") return janelaAvaliar(id, recarregar);
      if (b.dataset.acao === "registro") return janelaRegistro(b.dataset.paciente, id, recarregar);
      recarregar();
    } catch (erro) { /* aviso já mostrado */ }
  });
  caixa.addEventListener("change", async (e) => {
    const t = e.target.closest("[data-tarefa]");
    if (!t) return;
    try { await api(`/agendamentos/${t.dataset.cuidado}/tarefas/${t.dataset.tarefa}`, "PATCH", { realizado: t.checked }); }
    catch (erro) { aviso(erro.message, "erro"); t.checked = !t.checked; }
  });
}

function janelaAvaliar(id, depois) {
  abrirJanela("Avaliar atendimento", `<form id="f-aval">
    <p>Como foi o atendimento?</p>
    <div class="opcoes" style="grid-template-columns:repeat(5,1fr)">${[1, 2, 3, 4, 5].map((n) => `
      <label class="opcao" style="justify-content:center"><input type="radio" name="nota" value="${n}" ${n === 5 ? "checked" : ""}> ${n}★</label>`).join("")}</div>
    <div class="campo" style="margin-top:12px"><label for="comentario">Comentário</label>
      <textarea id="comentario" name="comentario" maxlength="500" placeholder="Conte como foi (opcional)"></textarea></div>
    <p class="suave pequeno">Notas 1 e 2 são encaminhadas para o SAC, que entra em contato.</p>
    <div class="linha-botoes"><button class="btn" type="submit">Enviar avaliação</button></div></form>`, (c) => {
    el("#f-aval", c).addEventListener("submit", async (e) => {
      e.preventDefault();
      const d = lerFormulario(e.target);
      try {
        await acao(api(`/agendamentos/${id}/avaliacao`, "POST", { nota: Number(d.nota), comentario: d.comentario }),
          (r) => r.foi_para_sac ? "Avaliação enviada. O SAC vai entrar em contato." : "Obrigado pela avaliação!");
        fecharJanela();
        depois();
      } catch (erro) { /* aviso já mostrado */ }
    });
  });
}

// ------------------------------------------------------------------
// REGISTRO DIÁRIO DE SAÚDE (cuidador)
// ------------------------------------------------------------------
function escala(nome, rotulo, valor, ajuda) {
  return `<div class="campo"><label for="${nome}">${rotulo}</label>
    <div class="escala"><span class="pequeno suave">0</span><input type="range" id="${nome}" name="${nome}" min="0" max="10" value="${valor}"
      oninput="this.nextElementSibling.nextElementSibling.value=this.value"><span class="pequeno suave">10</span><output>${valor}</output></div>
    <p class="ajuda">${ajuda}</p></div>`;
}

function janelaRegistro(idPaciente, idCuidado, depois) {
  abrirJanela("Registro diário de saúde", `<form id="f-reg">
    <p class="suave pequeno">Os campos de medida são opcionais. As 4 escalas alimentam o Índice de Bem-Estar.</p>
    <div class="grade-campos">
      <div class="campo"><label for="pressao_sistolica">Pressão (máxima)</label><input id="pressao_sistolica" name="pressao_sistolica" type="number" min="50" max="260" placeholder="ex.: 120"></div>
      <div class="campo"><label for="pressao_diastolica">Pressão (mínima)</label><input id="pressao_diastolica" name="pressao_diastolica" type="number" min="30" max="180" placeholder="ex.: 80"></div>
      <div class="campo"><label for="glicemia">Glicemia (mg/dL)</label><input id="glicemia" name="glicemia" type="number" min="20" max="600" placeholder="ex.: 100"></div>
      <div class="campo"><label for="temperatura">Temperatura (°C)</label><input id="temperatura" name="temperatura" type="number" step="0.1" min="33" max="43" placeholder="ex.: 36.5"></div>
    </div>
    ${escala("dor", "Dor", 0, "0 = sem dor · 10 = dor máxima")}
    ${escala("sono", "Sono", 7, "0 = dormiu muito mal · 10 = dormiu muito bem")}
    ${escala("alimentacao", "Alimentação", 7, "0 = não comeu · 10 = comeu muito bem")}
    ${escala("humor", "Humor", 7, "0 = muito abatido · 10 = muito bem-disposto")}
    <div class="campo"><label for="observacao">Observação</label><textarea id="observacao" name="observacao" maxlength="500" placeholder="Ex.: caminhou 15 minutos, reclamou de tontura..."></textarea></div>
    <div class="linha-botoes"><button class="btn" type="submit">Salvar registro</button></div></form>`, (c) => {
    el("#f-reg", c).addEventListener("submit", async (e) => {
      e.preventDefault();
      const d = lerFormulario(e.target);
      ["dor", "sono", "alimentacao", "humor"].forEach((k) => (d[k] = Number(d[k])));
      if (idCuidado) d.id_cuidado = Number(idCuidado);
      try {
        const r = await acao(api(`/pacientes/${idPaciente}/registros`, "POST", d), "Registro salvo!");
        fecharJanela();
        if (r.bem_estar.alertas.some((a) => a.nivel === "alto")) aviso("Atenção: o registro gerou alerta. Veja a aba de saúde do paciente.", "erro");
        if (depois) depois();
      } catch (erro) { /* aviso já mostrado */ }
    });
  });
}

// ------------------------------------------------------------------
// SAÚDE DO PACIENTE (Modo Pós-Alta): bem-estar, alertas, remédios,
// consultas, registros e linha do tempo
// ------------------------------------------------------------------
async function renderSaude(caixa, idPaciente, opcoes = {}) {
  const { podeEditar = false, podeRegistrar = false, titulo = "Saúde · Modo Pós-Alta" } = opcoes;
  caixa.innerHTML = topo(titulo, "Remédios, consultas, registros diários e a evolução do paciente.",
    podeRegistrar ? `<button class="btn" id="novo-registro">📝 Novo registro diário</button>` : "") + `<div id="saude-corpo">${vazio("Carregando...")}</div>`;
  const [be, meds, consultas, registros, tempo] = await Promise.all([
    api(`/pacientes/${idPaciente}/bem-estar`), api(`/pacientes/${idPaciente}/medicacoes`),
    api(`/pacientes/${idPaciente}/consultas`), api(`/pacientes/${idPaciente}/registros`),
    api(`/pacientes/${idPaciente}/linha-do-tempo`)]);
  const recarregar = () => renderSaude(caixa, idPaciente, opcoes);
  if (podeRegistrar) el("#novo-registro", caixa).addEventListener("click", () => janelaRegistro(idPaciente, null, recarregar));

  el("#saude-corpo", caixa).innerHTML = `
    <div class="grade grade-2">
      <div class="cartao"><h3>Bem-estar</h3>${medidorBemEstar(be)}
        <h3 style="margin-top:16px">Evolução (14 dias)</h3>${graficoLinha(be.serie, "data", "indice")}</div>
      <div class="cartao"><h3>Alertas de tendência</h3>${listaAlertas(be.alertas)}</div>
    </div>
    <div class="grade grade-2" style="margin-top:16px">
      <div class="cartao"><div class="cartao-topo"><h3>💊 Medicações</h3>${podeEditar ? `<button class="btn btn-pequeno" id="nova-med">+ Adicionar</button>` : ""}</div>
        ${meds.length ? `<div class="lista">${meds.map((m) => `<div class="item"><div class="item-corpo">
          <strong>${esc(m.nome_medicamento)} · ${esc(m.dosagem)} ${m.ativa ? "" : selo("encerrada")}</strong>
          <span class="suave pequeno">🕗 ${esc(m.horario)} · desde ${dataBR(m.data_inicio)}${m.data_fim ? " até " + dataBR(m.data_fim) : ""}</span>
          ${m.observacoes ? `<div class="pequeno">${esc(m.observacoes)}</div>` : ""}</div>
          ${podeEditar ? `<div class="item-acoes"><button class="btn-icone" title="Remover" aria-label="Remover medicação" data-apagar-med="${m.id_medicacao}">🗑</button></div>` : ""}</div>`).join("")}</div>` : vazio("Nenhuma medicação cadastrada.")}
      </div>
      <div class="cartao"><div class="cartao-topo"><h3>🩺 Consultas</h3>${podeEditar ? `<button class="btn btn-pequeno" id="nova-consulta">+ Adicionar</button>` : ""}</div>
        ${consultas.length ? `<div class="lista">${consultas.map((c) => `<div class="item"><div class="item-corpo">
          <strong>${esc(c.especialidade)} · ${esc(c.nome_medico)} ${c.futura ? selo("agendado") : ""}</strong>
          <span class="suave pequeno">${dataBR(c.data_consulta, true)}${c.eh_retorno ? " · retorno" : ""}</span>
          ${c.observacoes ? `<div class="pequeno">${esc(c.observacoes)}</div>` : ""}</div>
          ${podeEditar ? `<div class="item-acoes"><button class="btn-icone" title="Remover" aria-label="Remover consulta" data-apagar-consulta="${c.id_consulta}">🗑</button></div>` : ""}</div>`).join("")}</div>` : vazio("Nenhuma consulta cadastrada.")}
      </div>
    </div>
    <div class="grade grade-2" style="margin-top:16px">
      <div class="cartao"><h3>📈 Registros diários</h3>
        ${registros.length ? `<div class="tabela-caixa"><table class="responsiva"><thead><tr><th>Data</th><th>Pressão</th><th>Glicemia</th><th>Temp.</th><th class="num">Índice</th></tr></thead><tbody>
        ${registros.slice(0, 15).map((r) => `<tr><td data-rotulo="Data">${dataBR(r.data_hora, true)}</td><td data-rotulo="Pressão">${r.pressao || "—"}</td>
          <td data-rotulo="Glicemia">${r.glicemia ?? "—"}</td><td data-rotulo="Temp.">${r.temperatura ? r.temperatura + " °C" : "—"}</td>
          <td class="num" data-rotulo="Índice">${selo(r.indice >= 75 ? "bom" : r.indice >= 50 ? "atenção" : "alerta").replace(/>[^<]+</, `>${r.indice}<`)}</td></tr>`).join("")}
        </tbody></table></div>` : vazio("O cuidador ainda não fez registros.")}</div>
      <div class="cartao"><h3>🕒 Linha do tempo</h3><div style="max-height:520px;overflow-y:auto">${linhaDoTempo(tempo)}</div></div>
    </div>`;

  if (podeEditar) {
    el("#nova-med", caixa).addEventListener("click", () => abrirJanela("Nova medicação", `<form id="f-med">
      <div class="grade-campos">
        <div class="campo inteiro"><label for="nome_medicamento">Medicamento *</label><input id="nome_medicamento" name="nome_medicamento" required placeholder="Ex.: Losartana"></div>
        <div class="campo"><label for="dosagem">Dose *</label><input id="dosagem" name="dosagem" required placeholder="Ex.: 50 mg"></div>
        <div class="campo"><label for="horario">Horário *</label><input id="horario" name="horario" required placeholder="Ex.: 08:00 e 20:00"></div>
        <div class="campo"><label for="data_inicio">Início *</label><input id="data_inicio" name="data_inicio" type="date" required value="${hojeISO()}"></div>
        <div class="campo"><label for="data_fim">Fim (se tiver)</label><input id="data_fim" name="data_fim" type="date"></div>
        <div class="campo inteiro"><label for="observacoes">Observações</label><textarea id="observacoes" name="observacoes" maxlength="500"></textarea></div>
      </div><div class="linha-botoes"><button class="btn" type="submit">Salvar</button></div></form>`, (c) => {
      el("#f-med", c).addEventListener("submit", async (e) => {
        e.preventDefault();
        try { await acao(api(`/pacientes/${idPaciente}/medicacoes`, "POST", lerFormulario(e.target)), "Medicação adicionada."); fecharJanela(); recarregar(); } catch (x) { }
      });
    }));
    el("#nova-consulta", caixa).addEventListener("click", () => abrirJanela("Nova consulta", `<form id="f-cons">
      <div class="grade-campos">
        <div class="campo"><label for="data_consulta">Data e hora *</label><input id="data_consulta" name="data_consulta" type="datetime-local" required></div>
        <div class="campo"><label for="especialidade">Especialidade *</label><input id="especialidade" name="especialidade" required placeholder="Ex.: Cardiologia"></div>
        <div class="campo inteiro"><label for="nome_medico">Médico(a) *</label><input id="nome_medico" name="nome_medico" required placeholder="Ex.: Dra. Ana Lima"></div>
        <div class="campo inteiro"><label class="opcao"><input type="checkbox" name="eh_retorno"> É um retorno</label></div>
        <div class="campo inteiro"><label for="obs">Observações</label><textarea id="obs" name="observacoes" maxlength="500"></textarea></div>
      </div><div class="linha-botoes"><button class="btn" type="submit">Salvar</button></div></form>`, (c) => {
      el("#f-cons", c).addEventListener("submit", async (e) => {
        e.preventDefault();
        try { await acao(api(`/pacientes/${idPaciente}/consultas`, "POST", lerFormulario(e.target)), "Consulta adicionada."); fecharJanela(); recarregar(); } catch (x) { }
      });
    }));
    caixa._recarregarSaude = recarregar;
    if (!caixa._saudeLigada) {          // liga a lixeira UMA vez só
      caixa._saudeLigada = true;
      caixa.addEventListener("click", async (e) => {
        const med = e.target.closest("[data-apagar-med]"), cons = e.target.closest("[data-apagar-consulta]");
        if (!med && !cons) return;
        if (!(await confirmar("Remover este item?", "Remover"))) return;
        try {
          if (med) await acao(api(`/medicacoes/${med.dataset.apagarMed}`, "DELETE"), "Removido.");
          if (cons) await acao(api(`/consultas/${cons.dataset.apagarConsulta}`, "DELETE"), "Removido.");
          caixa._recarregarSaude();
        } catch (x) { }
      });
    }
  }
}

// ------------------------------------------------------------------
// MENSALIDADE (Pix simulado)
// ------------------------------------------------------------------
async function renderMensalidade(caixa) {
  const lista = await api("/mensalidades");
  caixa.innerHTML = topo("Mensalidade", "Pagamento por Pix. Nesta demonstração o Pix é simulado: ninguém paga de verdade.") +
    `<div class="cartao">${lista.length ? `<div class="tabela-caixa"><table class="responsiva"><thead><tr><th>Mês</th><th>Plano</th><th>Vencimento</th><th class="num">Valor</th><th>Situação</th><th></th></tr></thead><tbody>
    ${lista.map((m) => `<tr><td data-rotulo="Mês">${m.referencia.split("-").reverse().join("/")}</td><td data-rotulo="Plano">${esc(m.plano)}</td>
      <td data-rotulo="Vencimento">${dataBR(m.data_vencimento)}</td>
      <td class="num" data-rotulo="Valor">${reais(m.valor)}${m.codigo_cupom ? ` <span class="etiqueta">${esc(m.codigo_cupom)}</span>` : ""}</td>
      <td data-rotulo="Situação">${selo(m.status_pagamento)}</td>
      <td class="num">${m.status_pagamento !== "pago" ? `<button class="btn btn-pequeno" data-pagar="${m.id_assinatura}">Pagar com Pix</button>` : dataBR(m.data_pagamento)}</td></tr>`).join("")}
    </tbody></table></div>` : vazio("Nenhuma mensalidade ainda.")}</div>`;
  els("[data-pagar]", caixa).forEach((b) => b.addEventListener("click", () => janelaPix(b.dataset.pagar, () => renderMensalidade(caixa))));
}

function janelaPix(id, depois) {
  abrirJanela("Pagar com Pix", `<form id="f-cupom"><div class="campo"><label for="cupom">Tem cupom de desconto?</label>
      <div style="display:flex;gap:8px"><input id="cupom" name="cupom" placeholder="Ex.: FEIRA10" style="text-transform:uppercase">
      <button class="btn" type="submit">Gerar QR Code</button></div></div></form><div id="area-pix"></div>`, (c) => {
    el("#f-cupom", c).addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        const r = await api(`/mensalidades/${id}/pix`, "POST", { cupom: el("#cupom", c).value.trim() || null });
        el("#area-pix", c).innerHTML = `<div class="pix-caixa">
          <p>Valor: <strong style="font-size:1.3rem">${reais(r.valor)}</strong>${r.valor < r.valor_cheio ? ` <s class="suave">${reais(r.valor_cheio)}</s>` : ""}</p>
          <div class="qr">${r.qrcode_svg}</div><code>${esc(r.codigo_pix)}</code>
          <p class="faixa faixa-info pequeno">${esc(r.aviso)}</p>
          <button class="btn btn-ok btn-bloco" id="confirmar-pix">Confirmar pagamento (simulado)</button></div>`;
        el("#confirmar-pix", c).addEventListener("click", async () => {
          try { await acao(api(`/mensalidades/${id}/confirmar`, "POST"), "Pagamento confirmado! Obrigado."); fecharJanela(); depois(); } catch (x) { }
        });
      } catch (erro) { aviso(erro.message, "erro"); }
    });
  });
}

// ------------------------------------------------------------------
// AJUDA (SAC) e CONTA (troca de senha)
// ------------------------------------------------------------------
async function renderAjuda(caixa, sessao) {
  const meus = await api("/sac/meus-chamados");
  caixa.innerHTML = topo("Ajuda · Fale com o SAC", "Dúvidas, reclamações ou sugestões. A equipe responde por aqui.") + `
    <div class="grade grade-2"><div class="cartao"><h3>Nova mensagem</h3><form id="f-sac">
      <div class="campo"><label for="assunto">Assunto *</label><input id="assunto" name="assunto" required minlength="3" maxlength="100" placeholder="Ex.: Dúvida sobre o pagamento"></div>
      <div class="campo"><label for="mensagem">Mensagem *</label><textarea id="mensagem" name="mensagem" required minlength="5" maxlength="2000"></textarea></div>
      <button class="btn" type="submit">Enviar ao SAC</button></form></div>
    <div class="cartao"><h3>Minhas mensagens</h3>${meus.length ? `<div class="lista">${meus.map((c) => `<div class="item"><div class="item-corpo">
      <strong>${esc(c.assunto)} ${selo(c.status)}</strong><span class="suave pequeno">${dataBR(c.criado_em, true)}</span>
      <div class="pequeno">${esc(c.mensagem)}</div>${c.resposta ? `<div class="destaque-caixa pequeno" style="margin-top:6px"><b>Resposta do SAC:</b> ${esc(c.resposta)}</div>` : ""}</div></div>`).join("")}</div>` : vazio("Você ainda não mandou mensagens.")}</div></div>`;
  el("#f-sac", caixa).addEventListener("submit", async (e) => {
    e.preventDefault();
    const d = lerFormulario(e.target);
    try {
      const me = await api("/me");
      await acao(api("/sac/chamados", "POST", { ...d, nome: sessao.nome, email: me.email }), "Mensagem enviada ao SAC!");
      renderAjuda(caixa, sessao);
    } catch (x) { }
  });
}

function formSenha() {
  return `<div class="cartao"><h3>Trocar senha</h3><form id="f-senha">
    <div class="campo"><label for="senha_atual">Senha atual</label><input id="senha_atual" name="senha_atual" type="password" required autocomplete="current-password"></div>
    <div class="campo"><label for="senha_nova">Nova senha</label><input id="senha_nova" name="senha_nova" type="password" required minlength="6" autocomplete="new-password"></div>
    <button class="btn" type="submit">Salvar nova senha</button></form></div>`;
}
function ligarSenha(caixa, chave) {
  el("#f-senha", caixa).addEventListener("submit", async (e) => {
    e.preventDefault();
    try { await acao(api("/me/senha", "POST", lerFormulario(e.target), chave), "Senha alterada!"); e.target.reset(); } catch (x) { }
  });
}
