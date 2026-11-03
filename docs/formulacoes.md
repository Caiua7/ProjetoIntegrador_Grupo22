# Formulações de produto

O `PUT /formulacoes/{produto_id}` substitui a composição completa do produto. A API envia a lista para `salvar_formulacao_produto`, que valida a permissão e o estado ativo do produto, cria ou atualiza o cabeçalho e substitui os itens dentro da mesma transação. Uma falha em validação, constraint ou trigger reverte toda a operação.

Quantidades aceitam até seis casas decimais (precisão `NUMERIC(14,6)`) e perdas até quatro casas (precisão `NUMERIC(7,4)`, limite de 0 a 100). A API e o frontend transportam esses valores como strings decimais; a validação no navegador não os converte para ponto flutuante. A migration `20261103000002_salvar_formulacao_atomicamente.sql` adiciona a RPC usada pela API.

A formulação permanece vinculada ao produto. Origem do material fornecido pelo cliente, recálculo e rentabilidade são atributos do cenário de precificação e dependem do modelo/versionamento de cenários e da homologação do cálculo antes de serem persistidos ou exibidos.
