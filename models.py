# models.py -> as MESMAS tabelas do banco_sql/01_tabelas.sql, em Python
from datetime import datetime

from sqlalchemy import (Column, Integer, String, Text, Numeric, Date, DateTime,
                        ForeignKey, CheckConstraint, UniqueConstraint)
from sqlalchemy.orm import relationship

from database import Base

agora = datetime.now  # hora local do computador


def Dinheiro():
    # asdecimal=False: o SQLite não tem DECIMAL de verdade; devolve número normal
    return Numeric(10, 2, asdecimal=False)


class EquipeInterna(Base):
    __tablename__ = "equipe_interna"
    __table_args__ = (
        CheckConstraint("papel IN ('ADM','suporte','SAC','financeiro','marketing',"
                        "'comercial','frontend','backend','banco')", name="ck_equipe_papel"),
        CheckConstraint("status IN ('ativo','inativo')", name="ck_equipe_status"),
    )
    id_equipe = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False)
    cpf = Column(String(14), nullable=False, unique=True)
    telefone = Column(String(20), nullable=False)
    cidade = Column(String(100), nullable=False)
    email = Column(String(150), nullable=False, unique=True)
    senha_hash = Column(String(255), nullable=False)
    papel = Column(String(20), nullable=False)
    status = Column(String(10), nullable=False, default="ativo")
    data_criacao = Column(DateTime, nullable=False, default=agora)


class Plano(Base):
    __tablename__ = "plano"
    __table_args__ = (
        CheckConstraint("publico IN ('cuidador','paciente')", name="ck_plano_publico"),
        CheckConstraint("valor > 0", name="ck_plano_valor"),
    )
    id_plano = Column(Integer, primary_key=True)
    nome = Column(String(30), nullable=False, unique=True)
    publico = Column(String(10), nullable=False)
    valor = Column(Dinheiro(), nullable=False)
    descricao = Column(String(255), nullable=False)
    limite_conversas = Column(Integer)          # None = ilimitado
    pode_iniciar_conversa = Column(Integer, nullable=False, default=0)
    destaque = Column(Integer, nullable=False, default=0)
    relatorio = Column(Integer, nullable=False, default=0)
    ordem_busca = Column(Integer, nullable=False, default=0)


class Necessidade(Base):
    __tablename__ = "necessidade"
    __table_args__ = (CheckConstraint("grau_dependencia IN ('leve','moderado','alto')", name="ck_nec_grau"),)
    id_necessidade = Column(Integer, primary_key=True)
    nome_necessidade = Column(String(100), nullable=False, unique=True)
    grau_dependencia = Column(String(10), nullable=False)


class Habilidade(Base):
    __tablename__ = "habilidade"
    id_habilidade = Column(Integer, primary_key=True)
    nome_habilidade = Column(String(100), nullable=False, unique=True)
    restrita_tecnico = Column(Integer, nullable=False, default=0)


class Cuidador(Base):
    __tablename__ = "cuidador"
    __table_args__ = (
        CheckConstraint("idade >= 18", name="ck_cuid_idade"),
        CheckConstraint("categoria_profissional IN ('sem registro','auxiliar de enfermagem',"
                        "'técnico de enfermagem','enfermeiro')", name="ck_cuid_categoria"),
        CheckConstraint("(categoria_profissional = 'sem registro' AND numero_registro_coren IS NULL) OR "
                        "(categoria_profissional <> 'sem registro' AND numero_registro_coren IS NOT NULL)",
                        name="ck_cuid_coren"),
        CheckConstraint("status_cadastro IN ('pendente','aprovado','recusado')", name="ck_cuid_status"),
    )
    id_cuidador = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False)
    rg = Column(String(20), nullable=False)
    cpf = Column(String(14), nullable=False, unique=True)
    idade = Column(Integer, nullable=False)
    telefone = Column(String(20), nullable=False)
    cidade = Column(String(100), nullable=False)
    cep = Column(String(9), nullable=False)
    categoria_profissional = Column(String(30), nullable=False)
    numero_registro_coren = Column(String(50))
    descricao = Column(String(500))
    id_plano = Column(Integer, ForeignKey("plano.id_plano"), nullable=False)
    visualizacoes_perfil = Column(Integer, nullable=False, default=0)
    origem = Column(String(30))
    email = Column(String(150), nullable=False, unique=True)
    senha_hash = Column(String(255), nullable=False)
    status_cadastro = Column(String(10), nullable=False, default="pendente")
    data_criacao = Column(DateTime, nullable=False, default=agora)

    plano = relationship("Plano")
    habilidades = relationship("Habilidade", secondary="cuidador_habilidade", order_by="Habilidade.id_habilidade")


class Paciente(Base):
    __tablename__ = "paciente"
    __table_args__ = (CheckConstraint("status_cadastro IN ('pendente','aprovado','recusado')", name="ck_pac_status"),)
    id_paciente = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False)
    rg = Column(String(20), nullable=False)
    cpf = Column(String(14), nullable=False, unique=True)
    data_nascimento = Column(Date, nullable=False)
    telefone = Column(String(20), nullable=False)
    endereco = Column(String(200), nullable=False)
    cidade = Column(String(100), nullable=False)
    cep = Column(String(9), nullable=False)
    nome_responsavel = Column(String(100))
    telefone_responsavel = Column(String(20))
    observacoes = Column(String(500))
    origem = Column(String(30))
    email = Column(String(150), nullable=False, unique=True)
    senha_hash = Column(String(255), nullable=False)
    status_cadastro = Column(String(10), nullable=False, default="pendente")
    data_criacao = Column(DateTime, nullable=False, default=agora)

    necessidades = relationship("Necessidade", secondary="paciente_necessidade",
                                order_by="Necessidade.id_necessidade")


class Familiar(Base):
    __tablename__ = "familiar"
    id_familiar = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False)
    cpf = Column(String(14), nullable=False, unique=True)
    email = Column(String(150), nullable=False, unique=True)
    senha_hash = Column(String(255), nullable=False)
    telefone = Column(String(20), nullable=False)
    data_criacao = Column(DateTime, nullable=False, default=agora)


class PacienteFamiliar(Base):
    __tablename__ = "paciente_familiar"
    __table_args__ = (UniqueConstraint("id_paciente", "id_familiar", name="uq_pac_fam"),)
    id_paciente_familiar = Column(Integer, primary_key=True)
    id_paciente = Column(Integer, ForeignKey("paciente.id_paciente", ondelete="CASCADE"), nullable=False)
    id_familiar = Column(Integer, ForeignKey("familiar.id_familiar", ondelete="CASCADE"), nullable=False)
    parentesco = Column(String(30), nullable=False)

    paciente = relationship("Paciente")
    familiar = relationship("Familiar")


class PacienteNecessidade(Base):
    __tablename__ = "paciente_necessidade"
    __table_args__ = (UniqueConstraint("id_paciente", "id_necessidade", name="uq_pac_nec"),)
    id_paciente_necessidade = Column(Integer, primary_key=True)
    id_paciente = Column(Integer, ForeignKey("paciente.id_paciente", ondelete="CASCADE"), nullable=False)
    id_necessidade = Column(Integer, ForeignKey("necessidade.id_necessidade", ondelete="CASCADE"), nullable=False)


class CuidadorHabilidade(Base):
    __tablename__ = "cuidador_habilidade"
    __table_args__ = (UniqueConstraint("id_cuidador", "id_habilidade", name="uq_cuid_hab"),)
    id_cuidador_habilidade = Column(Integer, primary_key=True)
    id_cuidador = Column(Integer, ForeignKey("cuidador.id_cuidador", ondelete="CASCADE"), nullable=False)
    id_habilidade = Column(Integer, ForeignKey("habilidade.id_habilidade", ondelete="CASCADE"), nullable=False)


class Assinatura(Base):
    """Uma linha por mensalidade (mês) de cada usuário."""
    __tablename__ = "assinatura"
    __table_args__ = (
        UniqueConstraint("tipo_usuario", "id_usuario", "referencia", name="uq_assinatura_mes"),
        CheckConstraint("tipo_usuario IN ('cuidador','paciente')", name="ck_ass_tipo"),
        CheckConstraint("status_pagamento IN ('pago','pendente','atrasado')", name="ck_ass_status"),
        CheckConstraint("valor >= 0", name="ck_ass_valor"),
    )
    id_assinatura = Column(Integer, primary_key=True)
    tipo_usuario = Column(String(10), nullable=False)
    id_usuario = Column(Integer, nullable=False)
    id_plano = Column(Integer, ForeignKey("plano.id_plano"), nullable=False)
    referencia = Column(String(7), nullable=False)
    valor = Column(Dinheiro(), nullable=False)
    codigo_cupom = Column(String(30))
    status_pagamento = Column(String(10), nullable=False, default="pendente")
    data_vencimento = Column(Date, nullable=False)
    data_pagamento = Column(DateTime)
    codigo_pix = Column(String(200))

    plano = relationship("Plano")


class Conversa(Base):
    __tablename__ = "conversa"
    __table_args__ = (
        UniqueConstraint("id_paciente", "id_cuidador", name="uq_conversa_par"),
        CheckConstraint("iniciada_por IN ('paciente','cuidador')", name="ck_conv_quem"),
        CheckConstraint("status IN ('pendente','aceita','recusada','encerrada')", name="ck_conv_status"),
    )
    id_conversa = Column(Integer, primary_key=True)
    id_paciente = Column(Integer, ForeignKey("paciente.id_paciente", ondelete="CASCADE"), nullable=False)
    id_cuidador = Column(Integer, ForeignKey("cuidador.id_cuidador", ondelete="CASCADE"), nullable=False)
    iniciada_por = Column(String(10), nullable=False)
    status = Column(String(10), nullable=False, default="pendente")
    criado_em = Column(DateTime, nullable=False, default=agora)
    respondido_em = Column(DateTime)

    paciente = relationship("Paciente")
    cuidador = relationship("Cuidador")


class Mensagem(Base):
    __tablename__ = "mensagem"
    __table_args__ = (
        CheckConstraint("remetente_tipo IN ('paciente','cuidador','sistema')", name="ck_msg_tipo"),
        CheckConstraint("length(trim(texto)) > 0", name="ck_msg_texto"),
    )
    id_mensagem = Column(Integer, primary_key=True)
    id_conversa = Column(Integer, ForeignKey("conversa.id_conversa", ondelete="CASCADE"), nullable=False)
    remetente_tipo = Column(String(10), nullable=False)
    remetente_id = Column(Integer, nullable=False)
    texto = Column(Text, nullable=False)
    lida = Column(Integer, nullable=False, default=0)
    enviado_em = Column(DateTime, nullable=False, default=agora)


class Cuidado(Base):
    """O agendamento. proposto -> agendado -> em andamento -> concluído."""
    __tablename__ = "cuidado"
    __table_args__ = (
        CheckConstraint("tipo IN ('visita','plantão','acompanhamento','pós-alta')", name="ck_cuidado_tipo"),
        CheckConstraint("status IN ('proposto','agendado','em andamento','concluído','cancelado','recusado')",
                        name="ck_cuidado_status"),
        CheckConstraint("proposto_por IN ('paciente','cuidador')", name="ck_cuidado_quem"),
        CheckConstraint("hora_fim > hora_inicio", name="ck_cuidado_horario"),
    )
    id_cuidado = Column(Integer, primary_key=True)
    id_conversa = Column(Integer, ForeignKey("conversa.id_conversa"), nullable=False)
    id_cuidador = Column(Integer, ForeignKey("cuidador.id_cuidador"), nullable=False)
    id_paciente = Column(Integer, ForeignKey("paciente.id_paciente"), nullable=False)
    proposto_por = Column(String(10), nullable=False)
    tipo = Column(String(30), nullable=False)
    data = Column(Date, nullable=False)
    hora_inicio = Column(String(5), nullable=False)
    hora_fim = Column(String(5), nullable=False)
    observacoes = Column(String(500))
    status = Column(String(15), nullable=False, default="proposto")
    grupo_repeticao = Column(String(40))
    criado_em = Column(DateTime, nullable=False, default=agora)

    paciente = relationship("Paciente")
    cuidador = relationship("Cuidador")
    tarefas = relationship("CuidadoTarefa", cascade="all, delete-orphan",
                           order_by="CuidadoTarefa.id_cuidado_tarefa")
    avaliacao = relationship("Avaliacao", uselist=False)


class CuidadoTarefa(Base):
    __tablename__ = "cuidado_tarefa"
    id_cuidado_tarefa = Column(Integer, primary_key=True)
    id_cuidado = Column(Integer, ForeignKey("cuidado.id_cuidado", ondelete="CASCADE"), nullable=False)
    descricao = Column(String(150), nullable=False)
    realizado = Column(Integer, nullable=False, default=0)


class Avaliacao(Base):
    __tablename__ = "avaliacao"
    __table_args__ = (
        CheckConstraint("nota BETWEEN 1 AND 5", name="ck_aval_nota"),
        CheckConstraint("status_sac IN ('ok','nova','em contato','resolvida')", name="ck_aval_sac"),
    )
    id_avaliacao = Column(Integer, primary_key=True)
    id_cuidado = Column(Integer, ForeignKey("cuidado.id_cuidado"), nullable=False, unique=True)
    id_paciente = Column(Integer, ForeignKey("paciente.id_paciente"), nullable=False)
    id_cuidador = Column(Integer, ForeignKey("cuidador.id_cuidador"), nullable=False)
    nota = Column(Integer, nullable=False)
    comentario = Column(String(500))
    status_sac = Column(String(15), nullable=False, default="ok")
    criado_em = Column(DateTime, nullable=False, default=agora)

    paciente = relationship("Paciente")
    cuidador = relationship("Cuidador")


class Medicacao(Base):
    __tablename__ = "medicacao"
    id_medicacao = Column(Integer, primary_key=True)
    id_paciente = Column(Integer, ForeignKey("paciente.id_paciente", ondelete="CASCADE"), nullable=False)
    nome_medicamento = Column(String(150), nullable=False)
    dosagem = Column(String(100), nullable=False)
    horario = Column(String(100), nullable=False)
    data_inicio = Column(Date, nullable=False)
    data_fim = Column(Date)
    observacoes = Column(Text)


class ConsultaMedica(Base):
    __tablename__ = "consulta_medica"
    id_consulta = Column(Integer, primary_key=True)
    id_paciente = Column(Integer, ForeignKey("paciente.id_paciente", ondelete="CASCADE"), nullable=False)
    data_consulta = Column(DateTime, nullable=False)
    nome_medico = Column(String(150), nullable=False)
    especialidade = Column(String(100), nullable=False)
    eh_retorno = Column(Integer, nullable=False, default=0)
    observacoes = Column(Text)


class RegistroDiario(Base):
    __tablename__ = "registro_diario"
    __table_args__ = (
        CheckConstraint("dor BETWEEN 0 AND 10 AND sono BETWEEN 0 AND 10 AND alimentacao BETWEEN 0 AND 10 "
                        "AND humor BETWEEN 0 AND 10", name="ck_reg_escalas"),
    )
    id_registro = Column(Integer, primary_key=True)
    id_paciente = Column(Integer, ForeignKey("paciente.id_paciente", ondelete="CASCADE"), nullable=False)
    id_cuidador = Column(Integer, ForeignKey("cuidador.id_cuidador"))
    id_cuidado = Column(Integer, ForeignKey("cuidado.id_cuidado"))
    data_hora = Column(DateTime, nullable=False, default=agora)
    pressao_sistolica = Column(Integer)
    pressao_diastolica = Column(Integer)
    glicemia = Column(Integer)
    temperatura = Column(Numeric(4, 1, asdecimal=False))
    dor = Column(Integer, nullable=False)
    sono = Column(Integer, nullable=False)
    alimentacao = Column(Integer, nullable=False)
    humor = Column(Integer, nullable=False)
    observacao = Column(String(500))

    cuidador = relationship("Cuidador")


class ChamadoSac(Base):
    __tablename__ = "chamado_sac"
    __table_args__ = (CheckConstraint("status IN ('aberto','em andamento','resolvido')", name="ck_sac_status"),)
    id_chamado = Column(Integer, primary_key=True)
    autor_tipo = Column(String(10), nullable=False, default="visitante")
    autor_id = Column(Integer)
    nome = Column(String(100), nullable=False)
    email = Column(String(150), nullable=False)
    assunto = Column(String(100), nullable=False)
    mensagem = Column(Text, nullable=False)
    status = Column(String(15), nullable=False, default="aberto")
    resposta = Column(Text)
    criado_em = Column(DateTime, nullable=False, default=agora)


class Parceria(Base):
    __tablename__ = "parceria"
    __table_args__ = (
        CheckConstraint("tipo IN ('hospital','clínica','operadora','farmácia','outro')", name="ck_parc_tipo"),
        CheckConstraint("status IN ('prospecção','negociação','ativa','encerrada')", name="ck_parc_status"),
    )
    id_parceria = Column(Integer, primary_key=True)
    nome = Column(String(150), nullable=False)
    tipo = Column(String(20), nullable=False)
    contato = Column(String(100))
    telefone = Column(String(20))
    status = Column(String(15), nullable=False, default="prospecção")
    observacoes = Column(String(500))
    criado_em = Column(DateTime, nullable=False, default=agora)


class Campanha(Base):
    __tablename__ = "campanha"
    __table_args__ = (
        CheckConstraint("data_fim >= data_inicio", name="ck_camp_datas"),
        CheckConstraint("status IN ('planejada','ativa','encerrada')", name="ck_camp_status"),
    )
    id_campanha = Column(Integer, primary_key=True)
    nome = Column(String(150), nullable=False)
    canal = Column(String(30), nullable=False)
    objetivo = Column(String(255))
    data_inicio = Column(Date, nullable=False)
    data_fim = Column(Date, nullable=False)
    status = Column(String(15), nullable=False, default="planejada")


class Cupom(Base):
    __tablename__ = "cupom"
    __table_args__ = (CheckConstraint("desconto_percentual BETWEEN 1 AND 100", name="ck_cupom_desc"),)
    id_cupom = Column(Integer, primary_key=True)
    codigo = Column(String(30), nullable=False, unique=True)
    desconto_percentual = Column(Integer, nullable=False)
    validade = Column(Date, nullable=False)
    usos = Column(Integer, nullable=False, default=0)
    ativo = Column(Integer, nullable=False, default=1)


class Visita(Base):
    __tablename__ = "visita"
    id_visita = Column(Integer, primary_key=True)
    pagina = Column(String(150), nullable=False)
    origem = Column(String(200))
    criado_em = Column(DateTime, nullable=False, default=agora)


class LogErro(Base):
    __tablename__ = "log_erro"
    __table_args__ = (CheckConstraint("origem IN ('site','api')", name="ck_log_origem"),)
    id_erro = Column(Integer, primary_key=True)
    origem = Column(String(10), nullable=False)
    mensagem = Column(String(500), nullable=False)
    detalhe = Column(Text)
    pagina = Column(String(200))
    criado_em = Column(DateTime, nullable=False, default=agora)


class Sessao(Base):
    __tablename__ = "sessao"
    __table_args__ = (
        CheckConstraint("tipo_usuario IN ('paciente','cuidador','familiar','equipe')", name="ck_sessao_tipo"),
    )
    token = Column(String(64), primary_key=True)
    tipo_usuario = Column(String(10), nullable=False)
    id_usuario = Column(Integer, nullable=False)
    criado_em = Column(DateTime, nullable=False, default=agora)
