// cadastro.js -> formulários de cadastro do paciente e do cuidador
const form = el("#form-cadastro");
const tipo = form.dataset.tipo;               // "paciente" ou "cuidador"
let catalogo = null;

// ------------------------------------------------------------------
// Máscaras: o campo vai se formatando enquanto a pessoa digita
// ------------------------------------------------------------------
const MASCARAS = {
  cpf: (n) => n.slice(0, 11).replace(/(\d{3})(\d)/, "$1.$2").replace(/(\d{3})(\d)/, "$1.$2").replace(/(\d{3})(\d{1,2})$/, "$1-$2"),
  cep: (n) => n.slice(0, 8).replace(/(\d{5})(\d)/, "$1-$2"),
  telefone: (n) => n.slice(0, 11).replace(/^(\d{2})(\d)/, "($1) $2").replace(/(\d)(\d{4})$/, "$1-$2"),
};
els("[data-mascara]").forEach((campo) => campo.addEventListener("input", () => {
  campo.value = MASCARAS[campo.dataset.mascara](campo.value.replace(/\D/g, ""));
}));

// ------------------------------------------------------------------
// Carrega listas do banco (necessidades, habilidades, planos)
// ------------------------------------------------------------------
async function carregarCatalogo() {
  try {
    catalogo = await api("/catalogo");
  } catch (e) {
    aviso(e.message, "erro");
    return;
  }
  el("#origem").innerHTML += catalogo.origens.map((o) => `<option>${esc(o)}</option>`).join("");

  if (tipo === "paciente") {
    el("#lista-necessidades").innerHTML = catalogo.necessidades.map((n) => `
      <label class="opcao"><input type="checkbox" name="necessidades" data-lista value="${n.id}">
        <span>${esc(n.nome)}<small>Grau ${esc(n.grau)}</small></span></label>`).join("");
    const plano = catalogo.planos.find((p) => p.publico === "paciente");
    el("#info-plano").innerHTML = plano
      ? `Mensalidade do paciente: <strong>${reais(plano.valor)}</strong> por mês (pagamento por Pix). ${esc(plano.descricao)}`
      : "";
    el("#data_nascimento").max = hojeISO();
  } else {
    el("#categoria_profissional").innerHTML = catalogo.categorias.map((c) => `<option>${esc(c)}</option>`).join("");
    el("#lista-habilidades").innerHTML = catalogo.habilidades.map((h) => `
      <label class="opcao"><input type="checkbox" name="habilidades" data-lista value="${h.id}" data-restrita="${h.restrita_tecnico}">
        <span>${esc(h.nome)}${h.restrita_tecnico ? "<small>Só auxiliar, técnico ou enfermeiro</small>" : ""}</span></label>`).join("");
    el("#lista-planos").innerHTML = catalogo.planos.filter((p) => p.publico === "cuidador").map((p, i) => `
      <label class="opcao"><input type="radio" name="id_plano" value="${p.id}" ${i === 0 ? "checked" : ""}>
        <span><strong>${esc(p.nome)} · ${reais(p.valor)}/mês</strong>${p.destaque ? ' <span class="selo selo-destaque">Destaque</span>' : ""}
        <small>${esc(p.descricao)}</small></span></label>`).join("");
    el("#categoria_profissional").addEventListener("change", ajustarCategoria);
    ajustarCategoria();
  }
}

// Cuidador "sem registro": esconde o COREN e bloqueia habilidades técnicas
function ajustarCategoria() {
  const semRegistro = el("#categoria_profissional").value === "sem registro";
  el("#campo-coren").classList.toggle("escondido", semRegistro);
  els("[data-restrita=true]").forEach((c) => {
    c.disabled = semRegistro;
    if (semRegistro) c.checked = false;
  });
  el("#ajuda-habilidades").textContent = semRegistro
    ? "Injetável, sonda e curativos ficam bloqueados para quem não tem registro no COREN." : "";
}

// ------------------------------------------------------------------
// Envio
// ------------------------------------------------------------------
form.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const obrigatorio = els("[required]", form).find((c) => !c.closest(".escondido") && !c.value.trim());
  if (obrigatorio) {
    obrigatorio.focus();
    return aviso(`Preencha: ${obrigatorio.labels[0].textContent.replace("*", "").trim()}`, "erro");
  }
  if (el("#senha").value !== el("#senha2").value) return aviso("As duas senhas estão diferentes.", "erro");

  const dados = lerFormulario(form);
  if (tipo === "cuidador") {
    dados.id_plano = Number(dados.id_plano);
    if (dados.categoria_profissional === "sem registro") dados.numero_registro_coren = null;
  }
  const botao = el("button[type=submit]", form);
  botao.disabled = true;
  botao.textContent = "Enviando...";
  try {
    const r = await api(`/cadastro/${tipo}`, "POST", dados);
    el("#caixa-form").innerHTML = `
      <p class="olho">Cadastro enviado</p>
      <h1>Tudo certo, ${esc(r.nome.split(" ")[0])}! 🎉</h1>
      <p>${esc(r.mensagem)}</p>
      <div class="destaque-caixa"><strong>O que acontece agora?</strong><br>
        1. A equipe de suporte confere e aprova o seu cadastro.<br>
        2. Você já pode entrar com o seu e-mail e senha.<br>
        3. ${tipo === "paciente" ? "Depois de aprovado, você procura cuidadores e conversa pelo chat."
                                  : "Depois de aprovado, você aparece na busca dos pacientes."}</div>
      <div class="linha-botoes"><a class="btn" href="telaLogin.html">Ir para o login</a></div>`;
    window.scrollTo(0, 0);
  } catch (e) {
    aviso(e.message, "erro");
    botao.disabled = false;
    botao.textContent = "Enviar cadastro";
  }
});

carregarCatalogo();
