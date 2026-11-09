-- =====================================================================
-- CUIDADO PURO — ARQUIVO 1 de 3: CRIAÇÃO DAS TABELAS (SQLite)
-- Convertido do MySQL (Workbench) para SQLite: sem servidor, sem senha.
--
-- O que mudou em relação ao MySQL:
--   AUTO_INCREMENT         -> INTEGER PRIMARY KEY AUTOINCREMENT
--   ENUM('a','b')          -> TEXT com CHECK (campo IN ('a','b'))
--   BOOLEAN                -> INTEGER 0/1 com CHECK
--   CREATE DATABASE / USE  -> não existe: o banco é o próprio arquivo .db
--
-- Ordem: primeiro as tabelas que são "apontadas", depois as que apontam.
-- =====================================================================

PRAGMA foreign_keys = ON;

-- Apaga tudo (ordem inversa) para poder rodar quantas vezes quiser
DROP TABLE IF EXISTS sessao;
DROP TABLE IF EXISTS log_erro;
DROP TABLE IF EXISTS visita;
DROP TABLE IF EXISTS cupom;
DROP TABLE IF EXISTS campanha;
DROP TABLE IF EXISTS parceria;
DROP TABLE IF EXISTS chamado_sac;
DROP TABLE IF EXISTS registro_diario;
DROP TABLE IF EXISTS consulta_medica;
DROP TABLE IF EXISTS medicacao;
DROP TABLE IF EXISTS avaliacao;
DROP TABLE IF EXISTS cuidado_tarefa;
DROP TABLE IF EXISTS cuidado;
DROP TABLE IF EXISTS mensagem;
DROP TABLE IF EXISTS conversa;
DROP TABLE IF EXISTS assinatura;
DROP TABLE IF EXISTS cuidador_habilidade;
DROP TABLE IF EXISTS paciente_necessidade;
DROP TABLE IF EXISTS paciente_familiar;
DROP TABLE IF EXISTS familiar;
DROP TABLE IF EXISTS paciente;
DROP TABLE IF EXISTS cuidador;
DROP TABLE IF EXISTS habilidade;
DROP TABLE IF EXISTS necessidade;
DROP TABLE IF EXISTS plano;
DROP TABLE IF EXISTS equipe_interna;

-- =====================================================================
-- 1. EQUIPE_INTERNA — 9 papéis. O ADM cadastra os outros.
-- =====================================================================
CREATE TABLE equipe_interna (
    id_equipe     INTEGER PRIMARY KEY AUTOINCREMENT,
    nome          VARCHAR(100) NOT NULL,
    cpf           VARCHAR(14)  NOT NULL UNIQUE,
    telefone      VARCHAR(20)  NOT NULL,
    cidade        VARCHAR(100) NOT NULL,
    email         VARCHAR(150) NOT NULL UNIQUE,
    senha_hash    VARCHAR(255) NOT NULL,
    papel         VARCHAR(20)  NOT NULL,
    status        VARCHAR(10)  NOT NULL DEFAULT 'ativo',
    data_criacao  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_equipe_papel  CHECK (papel IN ('ADM','suporte','SAC','financeiro','marketing',
                                                 'comercial','frontend','backend','banco')),
    CONSTRAINT ck_equipe_status CHECK (status IN ('ativo','inativo'))
);

-- =====================================================================
-- 2. PLANO — cada plano libera coisas diferentes (regras ficam aqui,
--    assim o comercial muda o preço sem mexer no código)
-- =====================================================================
CREATE TABLE plano (
    id_plano               INTEGER PRIMARY KEY AUTOINCREMENT,
    nome                   VARCHAR(30)    NOT NULL UNIQUE,
    publico                VARCHAR(10)    NOT NULL,           -- 'cuidador' ou 'paciente'
    valor                  NUMERIC(10,2)  NOT NULL,
    descricao              VARCHAR(255)   NOT NULL,
    limite_conversas       INTEGER,                           -- NULL = ilimitado
    pode_iniciar_conversa  INTEGER        NOT NULL DEFAULT 0, -- 1 = cuidador pode chamar pacientes
    destaque               INTEGER        NOT NULL DEFAULT 0, -- 1 = topo da busca + selo
    relatorio              INTEGER        NOT NULL DEFAULT 0, -- 1 = vê quem visitou o perfil
    ordem_busca            INTEGER        NOT NULL DEFAULT 0, -- maior aparece primeiro
    CONSTRAINT ck_plano_publico CHECK (publico IN ('cuidador','paciente')),
    CONSTRAINT ck_plano_valor   CHECK (valor > 0),
    CONSTRAINT ck_plano_flags   CHECK (pode_iniciar_conversa IN (0,1) AND destaque IN (0,1) AND relatorio IN (0,1))
);

-- =====================================================================
-- 3. NECESSIDADE e HABILIDADE (catálogos)
-- =====================================================================
CREATE TABLE necessidade (
    id_necessidade    INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_necessidade  VARCHAR(100) NOT NULL UNIQUE,
    grau_dependencia  VARCHAR(10)  NOT NULL,
    CONSTRAINT ck_nec_grau CHECK (grau_dependencia IN ('leve','moderado','alto'))
);

CREATE TABLE habilidade (
    id_habilidade     INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_habilidade   VARCHAR(100) NOT NULL UNIQUE,
    restrita_tecnico  INTEGER      NOT NULL DEFAULT 0,       -- 1 = só técnico/enfermeiro
    CONSTRAINT ck_hab_restrita CHECK (restrita_tecnico IN (0,1))
);

-- =====================================================================
-- 4. CUIDADOR
-- =====================================================================
CREATE TABLE cuidador (
    id_cuidador             INTEGER PRIMARY KEY AUTOINCREMENT,
    nome                    VARCHAR(100) NOT NULL,
    rg                      VARCHAR(20)  NOT NULL,
    cpf                     VARCHAR(14)  NOT NULL UNIQUE,
    idade                   INTEGER      NOT NULL,
    telefone                VARCHAR(20)  NOT NULL,
    cidade                  VARCHAR(100) NOT NULL,
    cep                     VARCHAR(9)   NOT NULL,
    categoria_profissional  VARCHAR(30)  NOT NULL,
    numero_registro_coren   VARCHAR(50),
    descricao               VARCHAR(500),                  -- NOVO: experiência, especialidades
    id_plano                INTEGER      NOT NULL,         -- NOVO: básico / padrão / premium
    visualizacoes_perfil    INTEGER      NOT NULL DEFAULT 0,
    origem                  VARCHAR(30),                   -- NOVO: como conheceu (marketing)
    email                   VARCHAR(150) NOT NULL UNIQUE,
    senha_hash              VARCHAR(255) NOT NULL,
    status_cadastro         VARCHAR(10)  NOT NULL DEFAULT 'pendente',
    data_criacao            DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_cuid_idade     CHECK (idade >= 18),
    CONSTRAINT ck_cuid_categoria CHECK (categoria_profissional IN
        ('sem registro','auxiliar de enfermagem','técnico de enfermagem','enfermeiro')),
    CONSTRAINT ck_cuid_coren     CHECK (
        (categoria_profissional = 'sem registro' AND numero_registro_coren IS NULL)
        OR (categoria_profissional <> 'sem registro' AND numero_registro_coren IS NOT NULL)),
    CONSTRAINT ck_cuid_status    CHECK (status_cadastro IN ('pendente','aprovado','recusado')),
    CONSTRAINT fk_cuid_plano     FOREIGN KEY (id_plano) REFERENCES plano(id_plano)
);

-- =====================================================================
-- 5. PACIENTE
-- =====================================================================
CREATE TABLE paciente (
    id_paciente           INTEGER PRIMARY KEY AUTOINCREMENT,
    nome                  VARCHAR(100) NOT NULL,
    rg                    VARCHAR(20)  NOT NULL,
    cpf                   VARCHAR(14)  NOT NULL UNIQUE,
    data_nascimento       DATE         NOT NULL,
    telefone              VARCHAR(20)  NOT NULL,
    endereco              VARCHAR(200) NOT NULL,           -- NOVO: rua, número, bairro
    cidade                VARCHAR(100) NOT NULL,
    cep                   VARCHAR(9)   NOT NULL,
    nome_responsavel      VARCHAR(100),                    -- NOVO
    telefone_responsavel  VARCHAR(20),
    observacoes           VARCHAR(500),                    -- NOVO: cuidados importantes
    origem                VARCHAR(30),                     -- NOVO: como conheceu (marketing)
    email                 VARCHAR(150) NOT NULL UNIQUE,
    senha_hash            VARCHAR(255) NOT NULL,
    status_cadastro       VARCHAR(10)  NOT NULL DEFAULT 'pendente',
    data_criacao          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_pac_status CHECK (status_cadastro IN ('pendente','aprovado','recusado'))
);

-- =====================================================================
-- 6. FAMILIAR — central da família (login próprio, só leitura)
-- =====================================================================
CREATE TABLE familiar (
    id_familiar   INTEGER PRIMARY KEY AUTOINCREMENT,
    nome          VARCHAR(100) NOT NULL,
    cpf           VARCHAR(14)  NOT NULL UNIQUE,
    email         VARCHAR(150) NOT NULL UNIQUE,
    senha_hash    VARCHAR(255) NOT NULL,
    telefone      VARCHAR(20)  NOT NULL,
    data_criacao  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- N:N — um paciente pode ter vários familiares e vice-versa
CREATE TABLE paciente_familiar (
    id_paciente_familiar  INTEGER PRIMARY KEY AUTOINCREMENT,
    id_paciente           INTEGER     NOT NULL,
    id_familiar           INTEGER     NOT NULL,
    parentesco            VARCHAR(30) NOT NULL,
    CONSTRAINT uq_pac_fam UNIQUE (id_paciente, id_familiar),
    FOREIGN KEY (id_paciente) REFERENCES paciente(id_paciente) ON DELETE CASCADE,
    FOREIGN KEY (id_familiar) REFERENCES familiar(id_familiar) ON DELETE CASCADE
);

-- N:N — necessidades do paciente
CREATE TABLE paciente_necessidade (
    id_paciente_necessidade  INTEGER PRIMARY KEY AUTOINCREMENT,
    id_paciente              INTEGER NOT NULL,
    id_necessidade           INTEGER NOT NULL,
    CONSTRAINT uq_pac_nec UNIQUE (id_paciente, id_necessidade),
    FOREIGN KEY (id_paciente)    REFERENCES paciente(id_paciente)       ON DELETE CASCADE,
    FOREIGN KEY (id_necessidade) REFERENCES necessidade(id_necessidade) ON DELETE CASCADE
);

-- N:N — habilidades do cuidador (NOVO)
CREATE TABLE cuidador_habilidade (
    id_cuidador_habilidade  INTEGER PRIMARY KEY AUTOINCREMENT,
    id_cuidador             INTEGER NOT NULL,
    id_habilidade           INTEGER NOT NULL,
    CONSTRAINT uq_cuid_hab UNIQUE (id_cuidador, id_habilidade),
    FOREIGN KEY (id_cuidador)   REFERENCES cuidador(id_cuidador)     ON DELETE CASCADE,
    FOREIGN KEY (id_habilidade) REFERENCES habilidade(id_habilidade) ON DELETE CASCADE
);

-- =====================================================================
-- 7. ASSINATURA — uma linha por MENSALIDADE (mês) de cada usuário
-- =====================================================================
CREATE TABLE assinatura (
    id_assinatura     INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo_usuario      VARCHAR(10)   NOT NULL,              -- 'cuidador' ou 'paciente'
    id_usuario        INTEGER       NOT NULL,              -- id_cuidador OU id_paciente
    id_plano          INTEGER       NOT NULL,
    referencia        VARCHAR(7)    NOT NULL,              -- mês: '2026-11'
    valor             NUMERIC(10,2) NOT NULL,              -- valor cobrado (com desconto)
    codigo_cupom      VARCHAR(30),
    status_pagamento  VARCHAR(10)   NOT NULL DEFAULT 'pendente',
    data_vencimento   DATE          NOT NULL,
    data_pagamento    DATETIME,
    codigo_pix        VARCHAR(200),
    CONSTRAINT uq_assinatura_mes UNIQUE (tipo_usuario, id_usuario, referencia),
    CONSTRAINT ck_ass_tipo   CHECK (tipo_usuario IN ('cuidador','paciente')),
    CONSTRAINT ck_ass_status CHECK (status_pagamento IN ('pago','pendente','atrasado')),
    CONSTRAINT ck_ass_valor  CHECK (valor >= 0),
    FOREIGN KEY (id_plano) REFERENCES plano(id_plano)
);

-- =====================================================================
-- 8. CONVERSA — o "pedido de conversa" (estilo MSN): um pede, o outro
--    aceita ou recusa. Só com 'aceita' o chat libera. (NOVO)
-- =====================================================================
CREATE TABLE conversa (
    id_conversa    INTEGER PRIMARY KEY AUTOINCREMENT,
    id_paciente    INTEGER     NOT NULL,
    id_cuidador    INTEGER     NOT NULL,
    iniciada_por   VARCHAR(10) NOT NULL,                   -- 'paciente' ou 'cuidador'
    status         VARCHAR(10) NOT NULL DEFAULT 'pendente',
    criado_em      DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    respondido_em  DATETIME,
    CONSTRAINT uq_conversa_par UNIQUE (id_paciente, id_cuidador),
    CONSTRAINT ck_conv_quem    CHECK (iniciada_por IN ('paciente','cuidador')),
    CONSTRAINT ck_conv_status  CHECK (status IN ('pendente','aceita','recusada','encerrada')),
    FOREIGN KEY (id_paciente) REFERENCES paciente(id_paciente) ON DELETE CASCADE,
    FOREIGN KEY (id_cuidador) REFERENCES cuidador(id_cuidador) ON DELETE CASCADE
);

CREATE TABLE mensagem (
    id_mensagem     INTEGER PRIMARY KEY AUTOINCREMENT,
    id_conversa     INTEGER     NOT NULL,
    remetente_tipo  VARCHAR(10) NOT NULL,
    remetente_id    INTEGER     NOT NULL,
    texto           TEXT        NOT NULL,
    lida            INTEGER     NOT NULL DEFAULT 0,
    enviado_em      DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_msg_tipo  CHECK (remetente_tipo IN ('paciente','cuidador','sistema')),
    CONSTRAINT ck_msg_texto CHECK (length(trim(texto)) > 0),
    FOREIGN KEY (id_conversa) REFERENCES conversa(id_conversa) ON DELETE CASCADE
);

-- =====================================================================
-- 9. CUIDADO — o AGENDAMENTO. Nasce como 'proposto' dentro do chat;
--    o outro lado confirma ('agendado'); o cuidador inicia e conclui.
--    Escala repetida = várias linhas com o mesmo grupo_repeticao.
-- =====================================================================
CREATE TABLE cuidado (
    id_cuidado       INTEGER PRIMARY KEY AUTOINCREMENT,
    id_conversa      INTEGER      NOT NULL,
    id_cuidador      INTEGER      NOT NULL,
    id_paciente      INTEGER      NOT NULL,
    proposto_por     VARCHAR(10)  NOT NULL,
    tipo             VARCHAR(30)  NOT NULL,
    data             DATE         NOT NULL,
    hora_inicio      VARCHAR(5)   NOT NULL,                -- 'HH:MM'
    hora_fim         VARCHAR(5)   NOT NULL,
    observacoes      VARCHAR(500),
    status           VARCHAR(15)  NOT NULL DEFAULT 'proposto',
    grupo_repeticao  VARCHAR(40),
    criado_em        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_cuidado_tipo    CHECK (tipo IN ('visita','plantão','acompanhamento','pós-alta')),
    CONSTRAINT ck_cuidado_status  CHECK (status IN
        ('proposto','agendado','em andamento','concluído','cancelado','recusado')),
    CONSTRAINT ck_cuidado_quem    CHECK (proposto_por IN ('paciente','cuidador')),
    -- fim MENOR que o início = plantão que termina no DIA SEGUINTE (ex.: 19:00 às 07:00)
    CONSTRAINT ck_cuidado_horario CHECK (hora_fim <> hora_inicio),
    FOREIGN KEY (id_conversa) REFERENCES conversa(id_conversa),
    FOREIGN KEY (id_cuidador) REFERENCES cuidador(id_cuidador),
    FOREIGN KEY (id_paciente) REFERENCES paciente(id_paciente)
);

-- Checklist de tarefas de cada atendimento (Modo Pós-Alta)
CREATE TABLE cuidado_tarefa (
    id_cuidado_tarefa  INTEGER PRIMARY KEY AUTOINCREMENT,
    id_cuidado         INTEGER      NOT NULL,
    descricao          VARCHAR(150) NOT NULL,
    realizado          INTEGER      NOT NULL DEFAULT 0,
    CONSTRAINT ck_tarefa_realizado CHECK (realizado IN (0,1)),
    FOREIGN KEY (id_cuidado) REFERENCES cuidado(id_cuidado) ON DELETE CASCADE
);

-- =====================================================================
-- 10. AVALIACAO — só de atendimento concluído, uma por atendimento.
--     Nota 1 ou 2 vai para o SAC. (NOVO)
-- =====================================================================
CREATE TABLE avaliacao (
    id_avaliacao  INTEGER PRIMARY KEY AUTOINCREMENT,
    id_cuidado    INTEGER      NOT NULL UNIQUE,
    id_paciente   INTEGER      NOT NULL,
    id_cuidador   INTEGER      NOT NULL,
    nota          INTEGER      NOT NULL,
    comentario    VARCHAR(500),
    status_sac    VARCHAR(15)  NOT NULL DEFAULT 'ok',
    criado_em     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_aval_nota CHECK (nota BETWEEN 1 AND 5),
    CONSTRAINT ck_aval_sac  CHECK (status_sac IN ('ok','nova','em contato','resolvida')),
    FOREIGN KEY (id_cuidado)  REFERENCES cuidado(id_cuidado),
    FOREIGN KEY (id_paciente) REFERENCES paciente(id_paciente),
    FOREIGN KEY (id_cuidador) REFERENCES cuidador(id_cuidador)
);

-- =====================================================================
-- 11. MODO PÓS-ALTA: medicação, consultas e REGISTRO DIÁRIO
-- =====================================================================
CREATE TABLE medicacao (
    id_medicacao      INTEGER PRIMARY KEY AUTOINCREMENT,
    id_paciente       INTEGER      NOT NULL,
    nome_medicamento  VARCHAR(150) NOT NULL,
    dosagem           VARCHAR(100) NOT NULL,
    horario           VARCHAR(100) NOT NULL,
    data_inicio       DATE         NOT NULL,
    data_fim          DATE,
    observacoes       TEXT,
    CONSTRAINT ck_med_datas CHECK (data_fim IS NULL OR data_fim >= data_inicio),
    FOREIGN KEY (id_paciente) REFERENCES paciente(id_paciente) ON DELETE CASCADE
);

CREATE TABLE consulta_medica (
    id_consulta    INTEGER PRIMARY KEY AUTOINCREMENT,
    id_paciente    INTEGER      NOT NULL,
    data_consulta  DATETIME     NOT NULL,
    nome_medico    VARCHAR(150) NOT NULL,
    especialidade  VARCHAR(100) NOT NULL,
    eh_retorno     INTEGER      NOT NULL DEFAULT 0,
    observacoes    TEXT,
    CONSTRAINT ck_cons_retorno CHECK (eh_retorno IN (0,1)),
    FOREIGN KEY (id_paciente) REFERENCES paciente(id_paciente) ON DELETE CASCADE
);

-- O cuidador anota como o paciente está. É daqui que saem a Linha do
-- Tempo, o Índice de Bem-Estar e os alertas de tendência. (NOVO)
CREATE TABLE registro_diario (
    id_registro          INTEGER PRIMARY KEY AUTOINCREMENT,
    id_paciente          INTEGER  NOT NULL,
    id_cuidador          INTEGER,
    id_cuidado           INTEGER,
    data_hora            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    pressao_sistolica    INTEGER,          -- ex.: 120 (de 120x80)
    pressao_diastolica   INTEGER,          -- ex.: 80
    glicemia             INTEGER,          -- mg/dL
    temperatura          NUMERIC(4,1),     -- °C
    dor                  INTEGER  NOT NULL,   -- 0 = sem dor ... 10 = dor máxima
    sono                 INTEGER  NOT NULL,   -- 0 = péssimo ... 10 = ótimo
    alimentacao          INTEGER  NOT NULL,
    humor                INTEGER  NOT NULL,
    observacao           VARCHAR(500),
    CONSTRAINT ck_reg_escalas CHECK (dor BETWEEN 0 AND 10 AND sono BETWEEN 0 AND 10
                                     AND alimentacao BETWEEN 0 AND 10 AND humor BETWEEN 0 AND 10),
    CONSTRAINT ck_reg_pressao CHECK (pressao_sistolica IS NULL OR pressao_sistolica BETWEEN 50 AND 260),
    FOREIGN KEY (id_paciente) REFERENCES paciente(id_paciente) ON DELETE CASCADE,
    FOREIGN KEY (id_cuidador) REFERENCES cuidador(id_cuidador),
    FOREIGN KEY (id_cuidado)  REFERENCES cuidado(id_cuidado)
);

-- =====================================================================
-- 12. SAC — reclamações e dúvidas (do site ou dos dashboards)
-- =====================================================================
CREATE TABLE chamado_sac (
    id_chamado    INTEGER PRIMARY KEY AUTOINCREMENT,
    autor_tipo    VARCHAR(10)  NOT NULL DEFAULT 'visitante',
    autor_id      INTEGER,
    nome          VARCHAR(100) NOT NULL,
    email         VARCHAR(150) NOT NULL,
    assunto       VARCHAR(100) NOT NULL,
    mensagem      TEXT         NOT NULL,
    status        VARCHAR(15)  NOT NULL DEFAULT 'aberto',
    resposta      TEXT,
    criado_em     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_sac_autor  CHECK (autor_tipo IN ('visitante','paciente','cuidador','familiar')),
    CONSTRAINT ck_sac_status CHECK (status IN ('aberto','em andamento','resolvido'))
);

-- =====================================================================
-- 13. MARKETING — parcerias, campanhas e cupons de desconto
-- =====================================================================
CREATE TABLE parceria (
    id_parceria   INTEGER PRIMARY KEY AUTOINCREMENT,
    nome          VARCHAR(150) NOT NULL,
    tipo          VARCHAR(20)  NOT NULL,
    contato       VARCHAR(100),
    telefone      VARCHAR(20),
    status        VARCHAR(15)  NOT NULL DEFAULT 'prospecção',
    observacoes   VARCHAR(500),
    criado_em     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_parc_tipo   CHECK (tipo IN ('hospital','clínica','operadora','farmácia','outro')),
    CONSTRAINT ck_parc_status CHECK (status IN ('prospecção','negociação','ativa','encerrada'))
);

CREATE TABLE campanha (
    id_campanha  INTEGER PRIMARY KEY AUTOINCREMENT,
    nome         VARCHAR(150) NOT NULL,
    canal        VARCHAR(30)  NOT NULL,
    objetivo     VARCHAR(255),
    data_inicio  DATE         NOT NULL,
    data_fim     DATE         NOT NULL,
    status       VARCHAR(15)  NOT NULL DEFAULT 'planejada',
    CONSTRAINT ck_camp_datas  CHECK (data_fim >= data_inicio),
    CONSTRAINT ck_camp_status CHECK (status IN ('planejada','ativa','encerrada'))
);

CREATE TABLE cupom (
    id_cupom              INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo                VARCHAR(30) NOT NULL UNIQUE,
    desconto_percentual   INTEGER     NOT NULL,
    validade              DATE        NOT NULL,
    usos                  INTEGER     NOT NULL DEFAULT 0,
    ativo                 INTEGER     NOT NULL DEFAULT 1,
    CONSTRAINT ck_cupom_desc  CHECK (desconto_percentual BETWEEN 1 AND 100),
    CONSTRAINT ck_cupom_ativo CHECK (ativo IN (0,1))
);

-- =====================================================================
-- 14. MONITORAMENTO — visitas reais (sem número fantasma) e erros
-- =====================================================================
CREATE TABLE visita (
    id_visita  INTEGER PRIMARY KEY AUTOINCREMENT,
    pagina     VARCHAR(150) NOT NULL,
    origem     VARCHAR(200),
    criado_em  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE log_erro (
    id_erro    INTEGER PRIMARY KEY AUTOINCREMENT,
    origem     VARCHAR(10)  NOT NULL,              -- 'site' (frontend) ou 'api' (backend)
    mensagem   VARCHAR(500) NOT NULL,
    detalhe    TEXT,
    pagina     VARCHAR(200),
    criado_em  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_log_origem CHECK (origem IN ('site','api'))
);

-- =====================================================================
-- 15. SESSAO — o "crachá" de quem fez login (token)
-- =====================================================================
CREATE TABLE sessao (
    token         VARCHAR(64) PRIMARY KEY,
    tipo_usuario  VARCHAR(10) NOT NULL,
    id_usuario    INTEGER     NOT NULL,
    criado_em     DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_sessao_tipo CHECK (tipo_usuario IN ('paciente','cuidador','familiar','equipe'))
);

-- =====================================================================
-- ÍNDICES (deixam as buscas mais rápidas)
-- =====================================================================
CREATE INDEX idx_cuidado_paciente  ON cuidado(id_paciente, data);
CREATE INDEX idx_cuidado_cuidador  ON cuidado(id_cuidador, data);
CREATE INDEX idx_mensagem_conversa ON mensagem(id_conversa, id_mensagem);
CREATE INDEX idx_registro_paciente ON registro_diario(id_paciente, data_hora);
CREATE INDEX idx_assinatura_user   ON assinatura(tipo_usuario, id_usuario);
CREATE INDEX idx_visita_data       ON visita(criado_em);
CREATE INDEX idx_cuidador_busca    ON cuidador(status_cadastro, cidade);
