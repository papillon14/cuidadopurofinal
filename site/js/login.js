// login.js -> login de paciente, cuidador e familiar (a API descobre quem é)
const DESTINO = { paciente: "dashboardPacienteApp.html", familiar: "dashboardPacienteApp.html",
                  cuidador: "dashboardCuidador.html" };

// Já está logado? Vai direto para o painel
const atual = Sessao.pegar();
if (atual && DESTINO[atual.tipo]) location.href = DESTINO[atual.tipo];

const form = el("#form-login");
form.addEventListener("submit", async (evento) => {
  evento.preventDefault();               // não deixa a página recarregar
  const dados = lerFormulario(form);
  if (!dados.email || !dados.senha) return aviso("Preencha e-mail e senha.", "erro");
  const botao = el("button[type=submit]", form);
  botao.disabled = true;
  botao.textContent = "Entrando...";
  try {
    const r = await api("/login", "POST", dados);
    Sessao.salvar(r);                    // guarda o token no navegador
    location.href = DESTINO[r.tipo];
  } catch (e) {
    // e-mail da equipe digitado aqui? Entra pelo login da equipe e vai direto pro painel interno
    if (e.message.includes("equipe")) {
      try {
        const r = await api("/equipe/login", "POST", dados);
        Sessao.salvar(r, "cp_equipe");
        location.href = "dashboardAdmin.html";
        return;
      } catch (x) { e = x; }
    }
    aviso(e.message, "erro");
    botao.disabled = false;
    botao.textContent = "Entrar";
  }
});

// Botões de demonstração: preenchem o e-mail e a senha
els(".logins-teste button").forEach((b) => b.addEventListener("click", () => {
  el("#email").value = b.dataset.email;
  el("#senha").value = "cuidado123";
  el("#senha").focus();
}));
