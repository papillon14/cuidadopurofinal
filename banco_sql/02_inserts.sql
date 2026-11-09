-- =====================================================================
-- CUIDADO PURO — ARQUIVO 2 de 3: INSERTS (dados de exemplo)
-- Rode DEPOIS do 01_tabelas.sql
--
-- * As datas usam date('now', ...) -> sempre ficam "atuais", não importa
--   o dia em que você rodar.
-- * As senhas estão com HASH (embaralhadas). As senhas de verdade são:
--     ADM ............................ admin123
--     resto da equipe ................ equipe123
--     pacientes, cuidadores, família . cuidado123
-- * CPFs com dígitos verificadores válidos e sem números repetidos.
-- =====================================================================

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------
-- EQUIPE INTERNA: um usuário de cada papel (9)
-- ---------------------------------------------------------------------
INSERT INTO equipe_interna (nome, cpf, telefone, cidade, email, senha_hash, papel) VALUES
('Paulo Henrique (ADM)', '526.018.159-06', '(44) 99911-0001', 'Maringá', 'adm@cuidadopuro.com',
 'pbkdf2$100000$cp01adm$d61c2193abb7b23e786084759be59fd09e2cdfa749f918260e79461b1926d76c', 'ADM'),
('Larissa Suporte',      '083.016.613-05', '(44) 99911-0002', 'Maringá', 'suporte@cuidadopuro.com',
 'pbkdf2$100000$cp02eqp$d6a7e23e72d41a9643a38e6e5f10ec6f1f8dd5ef06b36a6f58fce43843cf135f', 'suporte'),
('Diego SAC',            '186.091.390-34', '(44) 99911-0003', 'Maringá', 'sac@cuidadopuro.com',
 'pbkdf2$100000$cp02eqp$d6a7e23e72d41a9643a38e6e5f10ec6f1f8dd5ef06b36a6f58fce43843cf135f', 'SAC'),
('Renata Financeiro',    '996.030.824-30', '(44) 99911-0004', 'Maringá', 'financeiro@cuidadopuro.com',
 'pbkdf2$100000$cp02eqp$d6a7e23e72d41a9643a38e6e5f10ec6f1f8dd5ef06b36a6f58fce43843cf135f', 'financeiro'),
('Bruna Marketing',      '628.194.821-12', '(44) 99911-0005', 'Maringá', 'marketing@cuidadopuro.com',
 'pbkdf2$100000$cp02eqp$d6a7e23e72d41a9643a38e6e5f10ec6f1f8dd5ef06b36a6f58fce43843cf135f', 'marketing'),
('Felipe Comercial',     '993.518.190-19', '(44) 99911-0006', 'Maringá', 'comercial@cuidadopuro.com',
 'pbkdf2$100000$cp02eqp$d6a7e23e72d41a9643a38e6e5f10ec6f1f8dd5ef06b36a6f58fce43843cf135f', 'comercial'),
('Samuel Frontend',      '937.865.797-41', '(44) 99911-0007', 'Maringá', 'frontend@cuidadopuro.com',
 'pbkdf2$100000$cp02eqp$d6a7e23e72d41a9643a38e6e5f10ec6f1f8dd5ef06b36a6f58fce43843cf135f', 'frontend'),
('Matheus Backend',      '543.231.948-97', '(44) 99911-0008', 'Maringá', 'backend@cuidadopuro.com',
 'pbkdf2$100000$cp02eqp$d6a7e23e72d41a9643a38e6e5f10ec6f1f8dd5ef06b36a6f58fce43843cf135f', 'backend'),
('Paulo Banco de Dados', '757.491.186-06', '(44) 99911-0009', 'Maringá', 'banco@cuidadopuro.com',
 'pbkdf2$100000$cp02eqp$d6a7e23e72d41a9643a38e6e5f10ec6f1f8dd5ef06b36a6f58fce43843cf135f', 'banco');

-- ---------------------------------------------------------------------
-- PLANOS (ids 1 a 4)
-- ---------------------------------------------------------------------
INSERT INTO plano (nome, publico, valor, descricao, limite_conversas, pode_iniciar_conversa, destaque, relatorio, ordem_busca) VALUES
('Básico',   'cuidador', 29.90, 'Aparece na busca e recebe pedidos de conversa (até 3 conversas abertas).', 3,    0, 0, 0, 1),
('Padrão',   'cuidador', 59.90, 'Conversas ilimitadas, aparece acima do Básico e pode chamar pacientes.',   NULL, 1, 0, 0, 2),
('Premium',  'cuidador', 99.90, 'Tudo do Padrão + topo da busca, selo Destaque e relatório de visitas ao perfil.', NULL, 1, 1, 1, 3),
('Paciente', 'paciente', 29.90, 'Acesso completo: busca de cuidadores, chat, agenda e Modo Pós-Alta.',      NULL, 1, 0, 0, 0);

-- ---------------------------------------------------------------------
-- CATÁLOGOS
-- ---------------------------------------------------------------------
INSERT INTO necessidade (nome_necessidade, grau_dependencia) VALUES
('Alzheimer / demência',                        'alto'),     -- 1
('Monitoramento de sinais vitais',              'leve'),     -- 2
('Sonda nasoenteral (SNE)',                     'alto'),     -- 3
('Recuperação de cirurgia',                     'moderado'), -- 4
('Acompanhamento pediátrico',                   'leve'),     -- 5
('Mobilidade reduzida / risco de queda',        'moderado'), -- 6
('Diabetes (controle de glicemia)',             'moderado'), -- 7
('Companhia e apoio nas atividades do dia',     'leve');     -- 8

INSERT INTO habilidade (nome_habilidade, restrita_tecnico) VALUES
('Medicação injetável (IM / SC)',          1),  -- 1
('Manejo e higiene de sonda',              1),  -- 2
('Curativos',                              1),  -- 3
('Banho e higiene pessoal',                0),  -- 4
('Alimentação e hidratação',               0),  -- 5
('Aferição de pressão e glicemia',         0),  -- 6
('Acompanhamento em consultas e passeios', 0),  -- 7
('Cuidados com idosos com demência',       0);  -- 8

-- ---------------------------------------------------------------------
-- CUIDADORES: um de cada plano + 1 pendente + 1 recusado
-- ---------------------------------------------------------------------
INSERT INTO cuidador (nome, rg, cpf, idade, telefone, cidade, cep, categoria_profissional, numero_registro_coren,
                      descricao, id_plano, visualizacoes_perfil, origem, email, senha_hash, status_cadastro, data_criacao) VALUES
('Carlos Souza',    '44.123.456-7', '252.760.189-87', 36, '(44) 99811-1111', 'Maringá', '87013-000',
 'técnico de enfermagem', 'COREN-PR 885512-TE',
 '10 anos em home care com idosos. Experiência com Alzheimer, curativos e medicação injetável.',
 3, 14, 'Instagram', 'carlos.souza@email.com',
 'pbkdf2$100000$cp03usr$d9b249e866e025a1f90888f440f57e0003b895589fba3e26e8f00be1a3fe13bf', 'aprovado',
 datetime('now','localtime','-40 days')),                                                         -- 1 Premium
('Ana Silva',       '44.987.654-2', '555.979.711-15', 29, '(44) 99811-2222', 'Maringá', '87020-000',
 'sem registro', NULL,
 'Cuidadora de idosos há 4 anos. Companhia, alimentação, banho e passeios.',
 1, 3, 'Indicação', 'ana.silva@email.com',
 'pbkdf2$100000$cp03usr$d9b249e866e025a1f90888f440f57e0003b895589fba3e26e8f00be1a3fe13bf', 'aprovado',
 datetime('now','localtime','-30 days')),                                                         -- 2 Básico
('Marcos Oliveira', '33.456.789-1', '471.049.746-01', 40, '(44) 99811-3333', 'Maringá', '87030-000',
 'enfermeiro', 'COREN-PR 412233',
 'Enfermeiro com foco em pediatria e pós-operatório. Plantões de 12h.',
 2, 6, 'Google', 'marcos.oliveira@email.com',
 'pbkdf2$100000$cp03usr$d9b249e866e025a1f90888f440f57e0003b895589fba3e26e8f00be1a3fe13bf', 'aprovado',
 datetime('now','localtime','-25 days')),                                                         -- 3 Padrão
('Beatriz Santos',  '55.111.222-3', '507.529.170-80', 32, '(44) 99811-4444', 'Maringá', '87040-000',
 'auxiliar de enfermagem', 'COREN-PR 991144-AE',
 'Auxiliar de enfermagem, disponível em finais de semana.',
 1, 0, 'Feira', 'beatriz.santos@email.com',
 'pbkdf2$100000$cp03usr$d9b249e866e025a1f90888f440f57e0003b895589fba3e26e8f00be1a3fe13bf', 'pendente',
 datetime('now','localtime','-1 days')),                                                          -- 4 pendente
('Juliana Prado',   '66.222.333-4', '342.366.712-55', 27, '(44) 99811-5555', 'Londrina', '86010-000',
 'sem registro', NULL, 'Documentos ilegíveis no cadastro.',
 1, 0, 'Instagram', 'juliana.prado@email.com',
 'pbkdf2$100000$cp03usr$d9b249e866e025a1f90888f440f57e0003b895589fba3e26e8f00be1a3fe13bf', 'recusado',
 datetime('now','localtime','-10 days'));                                                         -- 5 recusado

INSERT INTO cuidador_habilidade (id_cuidador, id_habilidade) VALUES
(1,1),(1,3),(1,4),(1,6),(1,8),
(2,4),(2,5),(2,7),(2,8),
(3,1),(3,2),(3,3),(3,6),
(4,4),(4,5),(4,6);

-- ---------------------------------------------------------------------
-- PACIENTES
-- ---------------------------------------------------------------------
INSERT INTO paciente (nome, rg, cpf, data_nascimento, telefone, endereco, cidade, cep, nome_responsavel,
                      telefone_responsavel, observacoes, origem, email, senha_hash, status_cadastro, data_criacao) VALUES
('Tereza Lawson',       '11.222.333-4', '768.426.846-50', '1945-06-20', '(44) 98811-3333',
 'Rua das Palmeiras, 120 - Zona 7', 'Maringá', '87013-100', 'Mariana Lawson (filha)', '(44) 98811-3334',
 'Alzheimer em estágio moderado. Hipertensa.', 'Indicação', 'tereza@email.com',
 'pbkdf2$100000$cp03usr$d9b249e866e025a1f90888f440f57e0003b895589fba3e26e8f00be1a3fe13bf', 'aprovado',
 datetime('now','localtime','-35 days')),                                                          -- 1
('Enzo Gabriel Santos', '66.777.888-9', '563.212.233-60', date('now','localtime','-2 years'), '(44) 99122-3344',
 'Av. Brasil, 2500, ap. 31 - Centro', 'Maringá', '87020-100', 'Patrícia Santos (mãe)', '(44) 99122-3345',
 'Bebê em acompanhamento pediátrico.', 'Google', 'enzo.familia@email.com',
 'pbkdf2$100000$cp03usr$d9b249e866e025a1f90888f440f57e0003b895589fba3e26e8f00be1a3fe13bf', 'aprovado',
 datetime('now','localtime','-20 days')),                                                          -- 2
('Roberto Alencar',     '22.555.666-7', '079.244.026-91', '1982-11-05', '(44) 99844-5566',
 'Rua Santos Dumont, 88 - Zona 3', 'Maringá', '87030-100', NULL, NULL,
 'Pós-operatório de joelho.', 'Feira', 'roberto.alencar@email.com',
 'pbkdf2$100000$cp03usr$d9b249e866e025a1f90888f440f57e0003b895589fba3e26e8f00be1a3fe13bf', 'pendente',
 datetime('now','localtime','-1 days'));                                                           -- 3 pendente

INSERT INTO paciente_necessidade (id_paciente, id_necessidade) VALUES
(1,1),(1,2),(1,6),
(2,5),
(3,4),(3,6);

-- ---------------------------------------------------------------------
-- FAMILIARES (central da família)
-- ---------------------------------------------------------------------
INSERT INTO familiar (nome, cpf, email, senha_hash, telefone) VALUES
('Mariana Lawson',  '859.952.890-47', 'mariana.lawson@email.com',
 'pbkdf2$100000$cp03usr$d9b249e866e025a1f90888f440f57e0003b895589fba3e26e8f00be1a3fe13bf', '(44) 98811-3334'),
('Patrícia Santos', '786.666.176-67', 'patricia.santos@email.com',
 'pbkdf2$100000$cp03usr$d9b249e866e025a1f90888f440f57e0003b895589fba3e26e8f00be1a3fe13bf', '(44) 99122-3345');

INSERT INTO paciente_familiar (id_paciente, id_familiar, parentesco) VALUES
(1, 1, 'filha'),
(2, 2, 'mãe');

-- ---------------------------------------------------------------------
-- MENSALIDADES: mês passado e mês atual
-- ---------------------------------------------------------------------
INSERT INTO assinatura (tipo_usuario, id_usuario, id_plano, referencia, valor, status_pagamento, data_vencimento, data_pagamento) VALUES
-- mês passado
('cuidador', 1, 3, strftime('%Y-%m','now','localtime','start of month','-1 month'), 99.90, 'pago',
 date('now','localtime','start of month','-1 month','+9 days'), datetime('now','localtime','start of month','-1 month','+8 days')),
('cuidador', 2, 1, strftime('%Y-%m','now','localtime','start of month','-1 month'), 29.90, 'atrasado',
 date('now','localtime','start of month','-1 month','+9 days'), NULL),
('cuidador', 3, 2, strftime('%Y-%m','now','localtime','start of month','-1 month'), 59.90, 'pago',
 date('now','localtime','start of month','-1 month','+9 days'), datetime('now','localtime','start of month','-1 month','+5 days')),
('paciente', 1, 4, strftime('%Y-%m','now','localtime','start of month','-1 month'), 29.90, 'pago',
 date('now','localtime','start of month','-1 month','+9 days'), datetime('now','localtime','start of month','-1 month','+9 days')),
('paciente', 2, 4, strftime('%Y-%m','now','localtime','start of month','-1 month'), 29.90, 'pago',
 date('now','localtime','start of month','-1 month','+9 days'), datetime('now','localtime','start of month','-1 month','+2 days')),
-- mês atual
('cuidador', 1, 3, strftime('%Y-%m','now','localtime'), 99.90, 'pago',
 date('now','localtime','start of month','+9 days'), datetime('now','localtime','start of month','+1 days')),
('cuidador', 2, 1, strftime('%Y-%m','now','localtime'), 29.90, 'pendente', date('now','localtime','start of month','+9 days'), NULL),
('cuidador', 3, 2, strftime('%Y-%m','now','localtime'), 59.90, 'pendente', date('now','localtime','start of month','+9 days'), NULL),
('cuidador', 4, 1, strftime('%Y-%m','now','localtime'), 29.90, 'pendente', date('now','localtime','start of month','+9 days'), NULL),
('paciente', 1, 4, strftime('%Y-%m','now','localtime'), 29.90, 'pendente', date('now','localtime','start of month','+9 days'), NULL),
('paciente', 2, 4, strftime('%Y-%m','now','localtime'), 29.90, 'pago',
 date('now','localtime','start of month','+9 days'), datetime('now','localtime','start of month')),
('paciente', 3, 4, strftime('%Y-%m','now','localtime'), 29.90, 'pendente', date('now','localtime','start of month','+9 days'), NULL);

-- ---------------------------------------------------------------------
-- CONVERSAS (pedido -> aceita -> chat)
-- ---------------------------------------------------------------------
INSERT INTO conversa (id_paciente, id_cuidador, iniciada_por, status, criado_em, respondido_em) VALUES
(1, 1, 'paciente', 'aceita',   datetime('now','localtime','-12 days'), datetime('now','localtime','-12 days','+2 hours')), -- 1 Tereza x Carlos
(2, 3, 'cuidador', 'aceita',   datetime('now','localtime','-8 days'),  datetime('now','localtime','-8 days','+1 hours')),  -- 2 Enzo x Marcos
(1, 2, 'paciente', 'pendente', datetime('now','localtime','-3 hours'), NULL);                                             -- 3 Tereza pediu à Ana

INSERT INTO mensagem (id_conversa, remetente_tipo, remetente_id, texto, lida, enviado_em) VALUES
(1, 'paciente', 1, 'Olá Carlos! Minha mãe precisa de acompanhamento de manhã, 3 vezes por semana.', 1, datetime('now','localtime','-12 days','+3 hours')),
(1, 'cuidador', 1, 'Bom dia! Tenho disponibilidade segunda, quarta e sexta, das 8h às 12h.',        1, datetime('now','localtime','-12 days','+4 hours')),
(1, 'paciente', 1, 'Perfeito! Vou propor o agendamento por aqui.',                                   1, datetime('now','localtime','-12 days','+5 hours')),
(1, 'cuidador', 1, 'Combinado. Ontem a pressão dela estava um pouco alta, vou acompanhar.',          0, datetime('now','localtime','-1 days')),
(2, 'cuidador', 3, 'Olá! Vi que o Enzo precisa de acompanhamento pediátrico. Posso ajudar?',         1, datetime('now','localtime','-8 days')),
(2, 'paciente', 2, 'Oi Marcos! Pode sim, precisamos de alguém nas tardes de terça.',                 1, datetime('now','localtime','-8 days','+2 hours'));

-- ---------------------------------------------------------------------
-- AGENDAMENTOS (cuidado)
-- ---------------------------------------------------------------------
INSERT INTO cuidado (id_conversa, id_cuidador, id_paciente, proposto_por, tipo, data, hora_inicio, hora_fim, observacoes, status, criado_em) VALUES
(1, 1, 1, 'paciente', 'acompanhamento', date('now','localtime','-2 days'), '08:00', '12:00', 'Café da manhã, remédios e caminhada.', 'concluído', datetime('now','localtime','-11 days')), -- 1
(1, 1, 1, 'paciente', 'acompanhamento', date('now','localtime','+1 days'), '08:00', '12:00', 'Levar aparelho de pressão.',           'agendado',  datetime('now','localtime','-11 days')), -- 2
(2, 3, 2, 'cuidador', 'visita',         date('now','localtime','-3 days'), '14:00', '17:00', NULL,                                    'concluído', datetime('now','localtime','-7 days')),  -- 3
(2, 3, 2, 'cuidador', 'visita',         date('now','localtime','+2 days'), '14:00', '17:00', 'Mesma rotina da última visita.',        'proposto',  datetime('now','localtime','-1 days'));  -- 4

INSERT INTO cuidado_tarefa (id_cuidado, descricao, realizado) VALUES
(1, 'Dar Rivastigmina às 8h',        1),
(1, 'Medir pressão',                 1),
(1, 'Caminhada de 15 minutos',       1),
(2, 'Dar Rivastigmina às 8h',        0),
(2, 'Medir pressão (anotar no app)', 0),
(3, 'Dar mamadeira às 15h',          1);

-- ---------------------------------------------------------------------
-- AVALIAÇÕES (a nota 2 cai no SAC)
-- ---------------------------------------------------------------------
INSERT INTO avaliacao (id_cuidado, id_paciente, id_cuidador, nota, comentario, status_sac, criado_em) VALUES
(1, 1, 1, 5, 'Carlos é muito atencioso e pontual. Minha mãe adorou!', 'ok',   datetime('now','localtime','-2 days','+6 hours')),
(3, 2, 3, 2, 'Chegou 40 minutos atrasado e não avisou.',             'nova', datetime('now','localtime','-3 days','+5 hours'));

-- ---------------------------------------------------------------------
-- MODO PÓS-ALTA
-- ---------------------------------------------------------------------
INSERT INTO medicacao (id_paciente, nome_medicamento, dosagem, horario, data_inicio, data_fim, observacoes) VALUES
(1, 'Rivastigmina', '4,6 mg (adesivo)', '08:00',         date('now','localtime','-60 days'), NULL, 'Trocar o adesivo todo dia, em local diferente da pele.'),
(1, 'Losartana',    '50 mg',            '08:00 e 20:00', date('now','localtime','-90 days'), NULL, NULL),
(2, 'Vitamina D',   '2 gotas',          '09:00',         date('now','localtime','-15 days'), date('now','localtime','+45 days'), NULL);

INSERT INTO consulta_medica (id_paciente, data_consulta, nome_medico, especialidade, eh_retorno, observacoes) VALUES
(1, datetime('now','localtime','start of day','+5 days','+9 hours'),  'Dr. Ricardo Nunes', 'Geriatria',  1, 'Levar exames de sangue.'),
(1, datetime('now','localtime','start of day','-20 days','+14 hours'), 'Dra. Sílvia Rocha', 'Cardiologia', 0, 'Ajustou a dose da Losartana.'),
(2, datetime('now','localtime','start of day','+10 days','+10 hours'), 'Dra. Helena Prado', 'Pediatria',  0, 'Consulta de rotina.');

-- Registros diários da Tereza: pressão SUBINDO e bem-estar CAINDO
-- nos últimos dias -> o sistema vai mostrar alertas de tendência.
INSERT INTO registro_diario (id_paciente, id_cuidador, data_hora, pressao_sistolica, pressao_diastolica, glicemia, temperatura, dor, sono, alimentacao, humor, observacao) VALUES
(1, 1, datetime('now','localtime','start of day','-7 days','+9 hours'), 124, 80, 102, 36.4, 1, 8, 8, 8, 'Bem disposta, caminhou 20 minutos.'),
(1, 1, datetime('now','localtime','start of day','-6 days','+9 hours'), 126, 82,  98, 36.5, 1, 8, 9, 8, NULL),
(1, 1, datetime('now','localtime','start of day','-5 days','+9 hours'), 128, 82, 105, 36.6, 2, 7, 8, 8, NULL),
(1, 1, datetime('now','localtime','start of day','-4 days','+9 hours'), 132, 84, 101, 36.5, 2, 7, 7, 7, 'Reclamou um pouco de dor no joelho.'),
(1, 1, datetime('now','localtime','start of day','-3 days','+9 hours'), 142, 92, 110, 36.7, 4, 5, 6, 6, 'Dormiu mal.'),
(1, 1, datetime('now','localtime','start of day','-2 days','+9 hours'), 146, 94, 108, 36.6, 5, 5, 5, 5, 'Mais agitada à tarde.'),
(1, 1, datetime('now','localtime','start of day','-1 days','+9 hours'), 148, 95, 112, 36.8, 5, 4, 5, 4, 'Pressão alta de novo. Família avisada.'),
(2, 3, datetime('now','localtime','start of day','-3 days','+15 hours'), NULL, NULL, NULL, 36.6, 0, 8, 9, 9, 'Mamou bem e brincou.'),
(2, 3, datetime('now','localtime','start of day','-10 days','+15 hours'), NULL, NULL, NULL, 36.9, 1, 7, 8, 8, NULL);

-- ---------------------------------------------------------------------
-- SAC, MARKETING
-- ---------------------------------------------------------------------
INSERT INTO chamado_sac (autor_tipo, autor_id, nome, email, assunto, mensagem, status, criado_em) VALUES
('paciente',  2,    'Patrícia Santos', 'enzo.familia@email.com', 'Atraso no atendimento',
 'O cuidador chegou atrasado na última visita. Gostaria de um retorno.', 'aberto', datetime('now','localtime','-3 days','+6 hours')),
('visitante', NULL, 'Jorge Lima',      'jorge@email.com',        'Dúvida sobre planos',
 'O plano do paciente cobre mais de um idoso na mesma casa?', 'resolvido', datetime('now','localtime','-6 days'));

UPDATE chamado_sac SET resposta = 'Olá Jorge! Cada paciente tem seu próprio cadastro e mensalidade.' WHERE id_chamado = 2;

INSERT INTO parceria (nome, tipo, contato, telefone, status, observacoes) VALUES
('Hospital Santa Rita',     'hospital',  'Dra. Cláudia (alta hospitalar)', '(44) 3027-1000', 'negociação', 'Interesse em indicar o Modo Pós-Alta na alta.'),
('Clínica Viver Bem',       'clínica',   'Rodrigo',                        '(44) 3025-2200', 'ativa',      'Indica pacientes de geriatria.'),
('Farmácia Popular Centro', 'farmácia',  'Gerente Ana',                    '(44) 3026-3300', 'prospecção', NULL);

INSERT INTO campanha (nome, canal, objetivo, data_inicio, data_fim, status) VALUES
('Feira de Projetos',      'presencial', 'Mostrar o app e captar os primeiros usuários.', date('now','localtime'), date('now','localtime','+30 days'), 'ativa'),
('Instagram — Dia do Idoso','instagram', 'Divulgar o Modo Pós-Alta para famílias.',      date('now','localtime','-30 days'), date('now','localtime','-20 days'), 'encerrada');

INSERT INTO cupom (codigo, desconto_percentual, validade, usos, ativo) VALUES
('FEIRA10',    10, date('now','localtime','+60 days'), 0, 1),
('BEMVINDO50', 50, date('now','localtime','+15 days'), 2, 1);

-- A tabela VISITA começa vazia de propósito: ela só conta acessos reais.
