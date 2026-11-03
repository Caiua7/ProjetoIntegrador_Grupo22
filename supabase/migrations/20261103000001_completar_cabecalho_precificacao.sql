-- Campos comerciais e fiscais do cabecalho da simulacao (US57).
ALTER TABLE precificacao
    ADD COLUMN uf_destino CHAR(2),
    ADD COLUMN frete VARCHAR(3),
    ADD COLUMN regime_tributario VARCHAR(20);

ALTER TABLE precificacao
    ADD CONSTRAINT ck_precificacao_uf_destino CHECK (
        uf_destino IS NULL OR uf_destino IN (
            'AC','AL','AM','BA','CE','DF','ES','GO','MA','MG','MS','MT','PA','PB','PE','PI',
            'PR','RJ','RN','RO','RR','RS','SC','SE','SP','TO','EX'
        )
    ),
    ADD CONSTRAINT ck_precificacao_frete CHECK (frete IS NULL OR frete IN ('cif', 'fob')),
    ADD CONSTRAINT ck_precificacao_regime CHECK (
        regime_tributario IS NULL OR regime_tributario IN ('lucro_real', 'lucro_presumido', 'simples_nacional')
    ),
    ADD CONSTRAINT ck_precificacao_cabecalho_completo CHECK (
        uf_destino IS NOT NULL AND frete IS NOT NULL AND regime_tributario IS NOT NULL
    ) NOT VALID;

-- As colunas ficam nullable para preservar os registros legados. Novos
-- NOT VALID preserva cabecalhos legados incompletos, enquanto o CHECK passa
-- a ser aplicado a novas insercoes e atualizacoes feitas fora da API.
