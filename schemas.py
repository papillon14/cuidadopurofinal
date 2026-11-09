# schemas.py -> a "porta de entrada" da API: confere o formato do que chega.
# Se algo vier errado, o Pydantic devolve 422 dizendo qual campo.
from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

EMAIL = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
CPF = r"^\d{3}\.?\d{3}\.?\d{3}-?\d{2}$"
CEP = r"^\d{5}-?\d{3}$"
HORA = r"^([01]\d|2[0-3]):[0-5]\d$"

CATEGORIAS = Literal["sem registro", "auxiliar de enfermagem", "técnico de enfermagem", "enfermeiro"]
ORIGENS = Literal["Google", "Instagram", "Facebook", "Indicação", "Feira", "Parceria", "Outro"]
PAPEIS = Literal["ADM", "suporte", "SAC", "financeiro", "marketing", "comercial", "frontend", "backend", "banco"]


def formatar_cpf(valor: str) -> str:
    n = "".join(c for c in valor if c.isdigit())
    return f"{n[:3]}.{n[3:6]}.{n[6:9]}-{n[9:]}"


def formatar_cep(valor: str) -> str:
    n = "".join(c for c in valor if c.isdigit())
    return f"{n[:5]}-{n[5:]}"


class _ComCpf(BaseModel):
    @field_validator("cpf", check_fields=False)
    @classmethod
    def _cpf(cls, v):
        return formatar_cpf(v)

    @field_validator("cep", check_fields=False)
    @classmethod
    def _cep(cls, v):
        return formatar_cep(v)

    @field_validator("email", check_fields=False)
    @classmethod
    def _email(cls, v):
        return v.strip().lower()


# ---------------- ACESSO ----------------
class Login(BaseModel):
    email: str = Field(pattern=EMAIL, max_length=150)
    senha: str = Field(min_length=1, max_length=100)


class TrocarSenha(BaseModel):
    senha_atual: str = Field(min_length=1)
    senha_nova: str = Field(min_length=6, max_length=100)


# ---------------- CADASTRO ----------------
class PacienteCreate(_ComCpf):
    nome: str = Field(min_length=3, max_length=100)
    rg: str = Field(min_length=4, max_length=20)
    cpf: str = Field(pattern=CPF)
    data_nascimento: date
    telefone: str = Field(min_length=8, max_length=20)
    endereco: str = Field(min_length=5, max_length=200, description="Rua, número e bairro")
    cidade: str = Field(min_length=2, max_length=100)
    cep: str = Field(pattern=CEP)
    nome_responsavel: Optional[str] = Field(default=None, max_length=100)
    telefone_responsavel: Optional[str] = Field(default=None, max_length=20)
    observacoes: Optional[str] = Field(default=None, max_length=500)
    origem: Optional[ORIGENS] = None
    necessidades: List[int] = Field(default_factory=list, description="ids da tabela necessidade")
    email: str = Field(pattern=EMAIL, max_length=150)
    senha: str = Field(min_length=6, max_length=100)

    @field_validator("data_nascimento")
    @classmethod
    def _nascimento(cls, v):
        if v > date.today():
            raise ValueError("a data de nascimento não pode ser no futuro")
        return v


class CuidadorCreate(_ComCpf):
    nome: str = Field(min_length=3, max_length=100)
    rg: str = Field(min_length=4, max_length=20)
    cpf: str = Field(pattern=CPF)
    idade: int = Field(ge=18, le=100)
    telefone: str = Field(min_length=8, max_length=20)
    cidade: str = Field(min_length=2, max_length=100)
    cep: str = Field(pattern=CEP)
    categoria_profissional: CATEGORIAS
    numero_registro_coren: Optional[str] = Field(default=None, max_length=50)
    descricao: Optional[str] = Field(default=None, max_length=500)
    habilidades: List[int] = Field(default_factory=list, description="ids da tabela habilidade")
    id_plano: int = Field(description="1 = Básico, 2 = Padrão, 3 = Premium")
    origem: Optional[ORIGENS] = None
    email: str = Field(pattern=EMAIL, max_length=150)
    senha: str = Field(min_length=6, max_length=100)


# ---------------- PERFIS ----------------
class PacienteUpdate(BaseModel):
    telefone: Optional[str] = Field(default=None, min_length=8, max_length=20)
    endereco: Optional[str] = Field(default=None, min_length=5, max_length=200)
    cidade: Optional[str] = Field(default=None, min_length=2, max_length=100)
    nome_responsavel: Optional[str] = Field(default=None, max_length=100)
    telefone_responsavel: Optional[str] = Field(default=None, max_length=20)
    observacoes: Optional[str] = Field(default=None, max_length=500)
    necessidades: Optional[List[int]] = None


class CuidadorUpdate(BaseModel):
    telefone: Optional[str] = Field(default=None, min_length=8, max_length=20)
    cidade: Optional[str] = Field(default=None, min_length=2, max_length=100)
    descricao: Optional[str] = Field(default=None, max_length=500)
    habilidades: Optional[List[int]] = None


class TrocarPlano(BaseModel):
    id_plano: int


class FamiliarCreate(_ComCpf):
    nome: str = Field(min_length=3, max_length=100)
    cpf: str = Field(pattern=CPF)
    telefone: str = Field(min_length=8, max_length=20)
    parentesco: str = Field(min_length=2, max_length=30)
    email: str = Field(pattern=EMAIL, max_length=150)
    senha: str = Field(min_length=6, max_length=100)


# ---------------- CONVERSA E CHAT ----------------
class PedidoConversa(BaseModel):
    id_outro: int = Field(description="id do cuidador (se você é paciente) ou do paciente (se é cuidador)")


class Resposta(BaseModel):
    aceitar: bool


class MensagemCreate(BaseModel):
    texto: str = Field(min_length=1, max_length=2000)


# ---------------- AGENDA ----------------
class AgendamentoCreate(BaseModel):
    tipo: Literal["visita", "plantão", "acompanhamento", "pós-alta"]
    data: date
    hora_inicio: str = Field(pattern=HORA, examples=["08:00"])
    hora_fim: str = Field(pattern=HORA, examples=["08:30"])
    observacoes: Optional[str] = Field(default=None, max_length=500)
    tarefas: List[str] = Field(default_factory=list, max_length=15)
    repetir_dias: List[int] = Field(default_factory=list,
                                    description="dias da semana para repetir: 0=segunda ... 6=domingo")
    repetir_ate: Optional[date] = None

    @field_validator("hora_fim")
    @classmethod
    def _fim_diferente(cls, v, info):
        """Fim depois do início = mesmo dia. Fim ANTES do início = termina no dia seguinte
        (plantão noturno, ex.: 19:00 às 07:00). Só não pode ser igual."""
        inicio = info.data.get("hora_inicio")
        if inicio and v == inicio:
            raise ValueError("a hora de fim não pode ser igual à hora de início")
        return v


class Tarefa(BaseModel):
    realizado: bool


class AvaliacaoCreate(BaseModel):
    nota: int = Field(ge=1, le=5)
    comentario: Optional[str] = Field(default=None, max_length=500)


# ---------------- SAÚDE (MODO PÓS-ALTA) ----------------
class MedicacaoCreate(BaseModel):
    nome_medicamento: str = Field(min_length=2, max_length=150)
    dosagem: str = Field(min_length=1, max_length=100)
    horario: str = Field(min_length=1, max_length=100)
    data_inicio: date
    data_fim: Optional[date] = None
    observacoes: Optional[str] = Field(default=None, max_length=500)


class ConsultaCreate(BaseModel):
    data_consulta: datetime
    nome_medico: str = Field(min_length=2, max_length=150)
    especialidade: str = Field(min_length=2, max_length=100)
    eh_retorno: bool = False
    observacoes: Optional[str] = Field(default=None, max_length=500)


class RegistroCreate(BaseModel):
    id_cuidado: Optional[int] = None
    pressao_sistolica: Optional[int] = Field(default=None, ge=50, le=260)
    pressao_diastolica: Optional[int] = Field(default=None, ge=30, le=180)
    glicemia: Optional[int] = Field(default=None, ge=20, le=600)
    temperatura: Optional[float] = Field(default=None, ge=33, le=43)
    dor: int = Field(ge=0, le=10, description="0 = sem dor, 10 = dor máxima")
    sono: int = Field(ge=0, le=10)
    alimentacao: int = Field(ge=0, le=10)
    humor: int = Field(ge=0, le=10)
    observacao: Optional[str] = Field(default=None, max_length=500)


# ---------------- MENSALIDADE ----------------
class GerarPix(BaseModel):
    cupom: Optional[str] = Field(default=None, max_length=30)


# ---------------- SAC ----------------
class ChamadoCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=100)
    email: str = Field(pattern=EMAIL, max_length=150)
    assunto: str = Field(min_length=3, max_length=100)
    mensagem: str = Field(min_length=5, max_length=2000)


class ChamadoUpdate(BaseModel):
    status: Literal["aberto", "em andamento", "resolvido"]
    resposta: Optional[str] = Field(default=None, max_length=2000)


class AvaliacaoSacUpdate(BaseModel):
    status_sac: Literal["nova", "em contato", "resolvida"]


# ---------------- MONITORAMENTO ----------------
class VisitaCreate(BaseModel):
    pagina: str = Field(min_length=1, max_length=150)
    origem: Optional[str] = Field(default=None, max_length=200)


class ErroSiteCreate(BaseModel):
    mensagem: str = Field(min_length=1, max_length=500)
    detalhe: Optional[str] = Field(default=None, max_length=4000)
    pagina: Optional[str] = Field(default=None, max_length=200)


# ---------------- PAINEL INTERNO ----------------
class EquipeCreate(_ComCpf):
    nome: str = Field(min_length=3, max_length=100)
    cpf: str = Field(pattern=CPF)
    telefone: str = Field(min_length=8, max_length=20)
    cidade: str = Field(min_length=2, max_length=100)
    email: str = Field(pattern=EMAIL, max_length=150)
    papel: PAPEIS
    senha: Optional[str] = Field(default=None, min_length=6, max_length=100,
                                 description="Se não mandar, o sistema gera uma senha")


class EquipeUpdate(BaseModel):
    papel: Optional[PAPEIS] = None
    status: Optional[Literal["ativo", "inativo"]] = None
    telefone: Optional[str] = Field(default=None, min_length=8, max_length=20)
    cidade: Optional[str] = Field(default=None, min_length=2, max_length=100)


class StatusCadastro(BaseModel):
    status: Literal["aprovado", "recusado", "pendente"]


class PlanoUpdate(BaseModel):
    valor: Optional[float] = Field(default=None, gt=0, le=10000)
    descricao: Optional[str] = Field(default=None, min_length=5, max_length=255)
    limite_conversas: Optional[int] = Field(default=None, ge=1, le=1000)
    sem_limite: Optional[bool] = None


class ParceriaCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=150)
    tipo: Literal["hospital", "clínica", "operadora", "farmácia", "outro"]
    contato: Optional[str] = Field(default=None, max_length=100)
    telefone: Optional[str] = Field(default=None, max_length=20)
    status: Literal["prospecção", "negociação", "ativa", "encerrada"] = "prospecção"
    observacoes: Optional[str] = Field(default=None, max_length=500)


class CampanhaCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=150)
    canal: str = Field(min_length=2, max_length=30)
    objetivo: Optional[str] = Field(default=None, max_length=255)
    data_inicio: date
    data_fim: date
    status: Literal["planejada", "ativa", "encerrada"] = "planejada"

    @field_validator("data_fim")
    @classmethod
    def _fim(cls, v, info):
        if info.data.get("data_inicio") and v < info.data["data_inicio"]:
            raise ValueError("a data de fim precisa ser depois do início")
        return v


class CupomCreate(BaseModel):
    codigo: str = Field(min_length=3, max_length=30, pattern=r"^[A-Za-z0-9]+$")
    desconto_percentual: int = Field(ge=1, le=100)
    validade: date
    ativo: bool = True
