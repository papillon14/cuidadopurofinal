-- =====================================================================
-- CUIDADO PURO — ARQUIVO 3 de 3: CONSULTAS (SELECT e JOIN)
-- Rode DEPOIS do 01_tabelas.sql e do 02_inserts.sql
-- O resultado esperado de cada consulta está anotado em cima dela.
-- =====================================================================

-- 1) Equipe interna e seus papéis -> 9 linhas
SELECT id_equipe, nome, email, papel, status
FROM equipe_interna
ORDER BY id_equipe;

-- 2) Cadastros PENDENTES para o suporte aprovar (UNION junta duas tabelas)
--    -> Beatriz Santos (cuidador) e Roberto Alencar (paciente)
SELECT 'cuidador' AS tipo, nome, email, data_criacao FROM cuidador WHERE status_cadastro = 'pendente'
UNION ALL
SELECT 'paciente' AS tipo, nome, email, data_criacao FROM paciente WHERE status_cadastro = 'pendente';

-- 3) BUSCA DE CUIDADORES como o paciente vê (JOIN plano + LEFT JOIN avaliação)
--    Só aprovados, Premium primeiro, depois Padrão, depois Básico.
--    -> Carlos (Premium, nota 5.0), Marcos (Padrão, nota 2.0), Ana (Básico, sem nota)
SELECT c.nome,
       c.categoria_profissional,
       p.nome                         AS plano,
       CASE WHEN p.destaque = 1 THEN 'DESTAQUE' ELSE '' END AS selo,
       ROUND(AVG(a.nota), 1)          AS nota_media,
       COUNT(a.id_avaliacao)          AS qtd_avaliacoes
FROM cuidador c
JOIN plano p          ON p.id_plano = c.id_plano
LEFT JOIN avaliacao a ON a.id_cuidador = c.id_cuidador
WHERE c.status_cadastro = 'aprovado'
GROUP BY c.id_cuidador
ORDER BY p.ordem_busca DESC, nota_media DESC;

-- 4) Habilidades de cada cuidador (N:N com 3 tabelas) -> GROUP_CONCAT junta numa linha
SELECT c.nome, GROUP_CONCAT(h.nome_habilidade, ', ') AS habilidades
FROM cuidador c
JOIN cuidador_habilidade ch ON ch.id_cuidador = c.id_cuidador
JOIN habilidade h           ON h.id_habilidade = ch.id_habilidade
GROUP BY c.id_cuidador;

-- 5) Necessidades de cada paciente e o grau mais alto
--    -> Tereza: alto | Enzo: leve | Roberto: moderado
SELECT pa.nome,
       GROUP_CONCAT(n.nome_necessidade, ', ') AS necessidades,
       CASE MAX(CASE n.grau_dependencia WHEN 'alto' THEN 3 WHEN 'moderado' THEN 2 ELSE 1 END)
            WHEN 3 THEN 'alto' WHEN 2 THEN 'moderado' ELSE 'leve' END AS grau_mais_alto
FROM paciente pa
JOIN paciente_necessidade pn ON pn.id_paciente = pa.id_paciente
JOIN necessidade n           ON n.id_necessidade = pn.id_necessidade
GROUP BY pa.id_paciente;

-- 6) Conversas com o nome dos dois lados -> 3 linhas (2 aceitas, 1 pendente)
SELECT co.id_conversa, pa.nome AS paciente, cu.nome AS cuidador, co.iniciada_por, co.status,
       (SELECT COUNT(*) FROM mensagem m WHERE m.id_conversa = co.id_conversa) AS mensagens
FROM conversa co
JOIN paciente pa ON pa.id_paciente = co.id_paciente
JOIN cuidador cu ON cu.id_cuidador = co.id_cuidador;

-- 7) O chat da conversa 1, com o nome de quem mandou cada mensagem -> 4 linhas
SELECT m.enviado_em,
       CASE m.remetente_tipo WHEN 'paciente' THEN pa.nome ELSE cu.nome END AS quem,
       m.texto
FROM mensagem m
JOIN conversa co ON co.id_conversa = m.id_conversa
JOIN paciente pa ON pa.id_paciente = co.id_paciente
JOIN cuidador cu ON cu.id_cuidador = co.id_cuidador
WHERE m.id_conversa = 1
ORDER BY m.id_mensagem;

-- 8) AGENDA: atendimentos com paciente, cuidador e endereço -> 4 linhas
SELECT cd.data, cd.hora_inicio || ' às ' || cd.hora_fim AS horario, cd.tipo, cd.status,
       pa.nome AS paciente, pa.endereco, cu.nome AS cuidador
FROM cuidado cd
JOIN paciente pa ON pa.id_paciente = cd.id_paciente
JOIN cuidador cu ON cu.id_cuidador = cd.id_cuidador
ORDER BY cd.data;

-- 9) Checklist de tarefas por atendimento: feitas / total
--    -> atendimento 1: 3/3 | 2: 0/2 | 3: 1/1
SELECT id_cuidado, SUM(realizado) AS feitas, COUNT(*) AS total
FROM cuidado_tarefa
GROUP BY id_cuidado;

-- 10) Avaliações que foram para o SAC (nota 1 ou 2) -> Marcos, nota 2
SELECT a.nota, a.comentario, a.status_sac, pa.nome AS paciente, cu.nome AS cuidador
FROM avaliacao a
JOIN paciente pa ON pa.id_paciente = a.id_paciente
JOIN cuidador cu ON cu.id_cuidador = a.id_cuidador
WHERE a.nota <= 2;

-- 11) ÍNDICE DE BEM-ESTAR (0 a 100) de cada registro da Tereza
--     Fórmula: média de (10 - dor), sono, alimentação e humor, vezes 10.
--     -> começa em 82.5 e cai até 45.0: o bem-estar está CAINDO
SELECT date(data_hora) AS dia,
       pressao_sistolica || 'x' || pressao_diastolica AS pressao,
       ROUND(((10 - dor) + sono + alimentacao + humor) / 4.0 * 10, 1) AS indice_bem_estar
FROM registro_diario
WHERE id_paciente = 1
ORDER BY data_hora;

-- 12) ALERTA DE TENDÊNCIA: registros com pressão alta (>= 140 x 90)
--     -> 3 dias seguidos (os 3 últimos): o sistema sinaliza
SELECT date(data_hora) AS dia, pressao_sistolica, pressao_diastolica
FROM registro_diario
WHERE id_paciente = 1 AND (pressao_sistolica >= 140 OR pressao_diastolica >= 90)
ORDER BY data_hora;

-- 13) LINHA DO TEMPO da Tereza: junta 4 tabelas diferentes em ordem de data
SELECT data_hora AS quando, 'Registro diário' AS evento, observacao AS detalhe
  FROM registro_diario WHERE id_paciente = 1
UNION ALL
SELECT data || ' ' || hora_inicio, 'Atendimento (' || status || ')', tipo
  FROM cuidado WHERE id_paciente = 1
UNION ALL
SELECT data_consulta, 'Consulta médica', especialidade || ' - ' || nome_medico
  FROM consulta_medica WHERE id_paciente = 1
UNION ALL
SELECT data_inicio, 'Início de medicação', nome_medicamento || ' ' || dosagem
  FROM medicacao WHERE id_paciente = 1
ORDER BY quando DESC;

-- 14) FINANCEIRO: mensalidades do mês atual por status (com nome do usuário)
SELECT a.referencia, a.tipo_usuario,
       COALESCE(c.nome, p.nome) AS usuario,
       pl.nome AS plano, a.valor, a.status_pagamento
FROM assinatura a
JOIN plano pl         ON pl.id_plano = a.id_plano
LEFT JOIN cuidador c  ON a.tipo_usuario = 'cuidador' AND c.id_cuidador = a.id_usuario
LEFT JOIN paciente p  ON a.tipo_usuario = 'paciente' AND p.id_paciente = a.id_usuario
WHERE a.referencia = strftime('%Y-%m','now','localtime')
ORDER BY a.status_pagamento;

-- 15) Receita do mês atual: quanto já entrou e quanto falta
--     -> recebido 129.80 | a receber 179.50
SELECT ROUND(SUM(CASE WHEN status_pagamento = 'pago' THEN valor ELSE 0 END), 2) AS recebido,
       ROUND(SUM(CASE WHEN status_pagamento <> 'pago' THEN valor ELSE 0 END), 2) AS a_receber
FROM assinatura
WHERE referencia = strftime('%Y-%m','now','localtime');

-- 16) COMERCIAL: quantos cuidadores aprovados em cada plano
--     -> Básico 1 | Padrão 1 | Premium 1
SELECT pl.nome AS plano, pl.valor, COUNT(c.id_cuidador) AS cuidadores
FROM plano pl
LEFT JOIN cuidador c ON c.id_plano = pl.id_plano AND c.status_cadastro = 'aprovado'
WHERE pl.publico = 'cuidador'
GROUP BY pl.id_plano
ORDER BY pl.ordem_busca;

-- 17) MARKETING: de onde vieram os cadastros (pacientes + cuidadores)
SELECT origem, COUNT(*) AS cadastros
FROM (SELECT origem FROM paciente UNION ALL SELECT origem FROM cuidador)
GROUP BY origem
ORDER BY cadastros DESC;

-- 18) CENTRAL DA FAMÍLIA: qual familiar acompanha qual paciente
SELECT f.nome AS familiar, pf.parentesco, pa.nome AS paciente
FROM familiar f
JOIN paciente_familiar pf ON pf.id_familiar = f.id_familiar
JOIN paciente pa          ON pa.id_paciente = pf.id_paciente;

-- =====================================================================
-- TESTES DE ERRO DE PROPÓSITO (tire o -- de UMA linha: tem que dar ERRO)
-- =====================================================================
-- INSERT INTO avaliacao (id_cuidado, id_paciente, id_cuidador, nota) VALUES (1, 1, 1, 4);       -- UNIQUE: atendimento já avaliado
-- INSERT INTO avaliacao (id_cuidado, id_paciente, id_cuidador, nota) VALUES (2, 1, 1, 6);       -- CHECK: nota só de 1 a 5
-- INSERT INTO conversa (id_paciente, id_cuidador, iniciada_por) VALUES (1, 1, 'paciente');      -- UNIQUE: essa conversa já existe
-- INSERT INTO cuidado (id_conversa, id_cuidador, id_paciente, proposto_por, tipo, data, hora_inicio, hora_fim)
--        VALUES (1, 1, 1, 'paciente', 'visita', '2026-12-01', '10:00', '09:00');                -- CHECK: fim antes do início
-- INSERT INTO cuidador (nome, rg, cpf, idade, telefone, cidade, cep, categoria_profissional, numero_registro_coren, id_plano, email, senha_hash)
--        VALUES ('X', '1', '000', 30, '1', 'M', '1', 'sem registro', 'COREN 1', 1, 'x@x.com', 'h'); -- CHECK: sem registro não tem COREN
-- INSERT INTO equipe_interna (nome, cpf, telefone, cidade, email, senha_hash, papel)
--        VALUES ('X', '1', '1', 'M', 'y@y.com', 'h', 'estagiario');                             -- CHECK: papel fora da lista
