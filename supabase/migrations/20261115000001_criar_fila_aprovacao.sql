-- ============================================================
-- Migration: fila de aprovação do gerente
-- Issue #67 (US36) — Sprint 5
-- Executar via: supabase db push
--
-- O gerente olha exceção, não rotina: a fila mostra as precificações em
-- aprovação da carteira dele, com a data em que foram submetidas e a
-- margem da versão vigente do cenário, para separar o que está fora da
-- política.
--
-- A política de margem passa a ser um parâmetro global versionado por
-- vigência (#49): `margem_minima_contribuicao_percentual`, a margem de
-- contribuição mínima, em fração (0.24 = 24%).
-- ============================================================

ALTER TABLE parametro_global DROP CONSTRAINT ck_parametro_global_codigo;
ALTER TABLE parametro_global ADD CONSTRAINT ck_parametro_global_codigo CHECK (codigo IN (
    'perda_percentual',
    'taxa_financeira_mensal_percentual',
    'prazo_medio_padrao_dias',
    'desvio_maximo_cotacao_percentual',
    'margem_minima_contribuicao_percentual'
));

-- ============================================================
-- VISÃO: fila_aprovacao
-- Uma linha por precificação em aprovação. Roda como dona das tabelas
-- para trazer o nome de quem submeteu (o RLS de `usuario` só mostra o
-- próprio cadastro) e aplica ela mesma o acesso: quem aprova, enxerga
-- custo e alcança a carteira do cliente. security_barrier impede que um
-- filtro do usuário vaze linhas.
--
-- `submetido_em` é a última submissão registrada (#66); precificações
-- anteriores a essa trilha usam a data da última alteração.
-- ============================================================
CREATE VIEW fila_aprovacao WITH (security_barrier = true) AS
SELECT
    p.id                                    AS precificacao_id,
    p.codigo,
    p.cliente_id,
    cl.razao_social                         AS cliente_nome,
    p.produto_id,
    pr.descricao                            AS produto_descricao,
    p.modalidade_comercial,
    p.uf_destino,
    p.homologacao_pendente,
    COALESCE(sub.ocorrido_em, p.updated_at) AS submetido_em,
    sub.responsavel_id                      AS submetido_por_id,
    u.nome                                  AS submetido_por_nome,
    vig.id                                  AS cenario_id,
    vig.versao                              AS cenario_versao,
    vig.volume,
    vig.preco_bruto,
    vig.margem_contribuicao_valor,
    vig.margem_contribuicao_percentual,
    ant.versao                              AS versao_anterior
FROM precificacao p
JOIN cliente cl ON cl.id = p.cliente_id
JOIN produto pr ON pr.id = p.produto_id
LEFT JOIN LATERAL (
    SELECT h.ocorrido_em, h.responsavel_id
    FROM historico_status_precificacao h
    WHERE h.precificacao_id = p.id AND h.status_novo = 'em_aprovacao'
    ORDER BY h.ocorrido_em DESC
    LIMIT 1
) sub ON true
LEFT JOIN usuario u ON u.id = sub.responsavel_id
LEFT JOIN LATERAL (
    SELECT c.id, c.versao, c.volume, c.preco_bruto, c.margem_contribuicao_valor, c.margem_contribuicao_percentual
    FROM cenario c
    WHERE c.precificacao_id = p.id
    ORDER BY c.versao DESC
    LIMIT 1
) vig ON true
LEFT JOIN LATERAL (
    SELECT c.versao
    FROM cenario c
    WHERE c.precificacao_id = p.id AND c.versao < vig.versao
    ORDER BY c.versao DESC
    LIMIT 1
) ant ON true
WHERE p.status = 'em_aprovacao'
  AND usuario_tem_permissao('precificacao.aprovar')
  AND usuario_tem_permissao('custo.ler')
  AND usuario_acessa_cliente(p.cliente_id);

REVOKE ALL ON fila_aprovacao FROM PUBLIC, anon;
GRANT SELECT ON fila_aprovacao TO authenticated, service_role;
