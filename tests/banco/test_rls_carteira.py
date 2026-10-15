"""Teste de isolamento entre perfis e carteiras (issue #45 / US04).

Critério de aceite: dado um analista restrito à carteira X, quando consulta
precificações, então não enxerga nenhum registro da carteira Y.

Cada teste cria os usuários abaixo dentro de uma transação desfeita ao final
e consulta o banco como o Supabase faria por eles: papel `authenticated` e o
id do usuário no `sub` do JWT. Os clientes e precificações vêm da carga de
desenvolvimento (supabase/seed/dev).
"""

import json
import uuid
from contextlib import contextmanager

import pytest

psycopg = pytest.importorskip("psycopg")

# nome: (perfil, carteira, ativo)
USUARIOS = {
    "analista_sudeste": ("analista_pricing", "CART-SUDESTE", True),
    "analista_sul": ("analista_pricing", "CART-SUL", True),
    "executiva_sudeste": ("executiva_contas", "CART-SUDESTE", True),
    "gerente_sul": ("gerente_comercial", "CART-SUL", True),
    "suprimentos": ("analista_suprimentos", None, True),
    "admin": ("administrador", None, True),
    "inativo_sudeste": ("analista_pricing", "CART-SUDESTE", False),
}

PRECIFICACOES_SUDESTE = {"PRC-2026-0148", "PRC-2026-0147", "PRC-2026-0144", "PRC-2026-0143", "PRC-2026-0142"}
PRECIFICACOES_SUL = {"PRC-2026-0145"}
PRECIFICACOES_EXPORTACAO = {"PRC-2026-0146"}
TODAS_AS_PRECIFICACOES = PRECIFICACOES_SUDESTE | PRECIFICACOES_SUL | PRECIFICACOES_EXPORTACAO


@pytest.fixture
def usuarios(conn):
    """Cria os usuários de teste e devolve {nome: id}."""
    with conn.transaction(force_rollback=True):
        ids = {}
        for nome, (perfil, carteira, ativo) in USUARIOS.items():
            ids[nome] = uuid.uuid4()
            conn.execute(
                "INSERT INTO usuario (id, nome, email, perfil_id, ativo) "
                "SELECT %s, %s, %s, id, %s FROM perfil WHERE codigo = %s",
                [ids[nome], nome, f"{nome}@neoprice.test", ativo, perfil],
            )
            if carteira:
                conn.execute(
                    "INSERT INTO usuario_carteira (usuario_id, carteira_id) "
                    "SELECT %s, id FROM carteira WHERE codigo = %s",
                    [ids[nome], carteira],
                )
        yield ids


@contextmanager
def como(conn, usuario_id, papel="authenticated"):
    """Executa o bloco com o papel e a identidade que o Supabase daria ao usuário."""
    claims = json.dumps({"sub": str(usuario_id), "role": papel})
    conn.execute("SELECT set_config('request.jwt.claims', %s, true)", [claims])
    conn.execute(f"SET LOCAL ROLE {papel}")
    try:
        yield
    finally:
        conn.execute("RESET ROLE")
        conn.execute("SELECT set_config('request.jwt.claims', '', true)")


def _codigos(conn, tabela: str) -> set[str]:
    return {codigo for (codigo,) in conn.execute(f"SELECT codigo FROM {tabela}")}


def _total(conn, tabela: str) -> int:
    return conn.execute(f"SELECT count(*) FROM {tabela}").fetchone()[0]


def _recusa(conn, sql: str, parametros=None) -> None:
    """O comando precisa ser barrado pelo banco (sem GRANT ou fora da política)."""
    with pytest.raises(psycopg.errors.InsufficientPrivilege), conn.transaction():
        conn.execute(sql, parametros)


def _id(conn, tabela: str, codigo: str):
    return conn.execute(f"SELECT id FROM {tabela} WHERE codigo = %s", [codigo]).fetchone()[0]


# ------------------------------------------------------------ critério de aceite


def test_analista_so_enxerga_precificacoes_da_propria_carteira(conn, usuarios):
    with como(conn, usuarios["analista_sudeste"]):
        assert _codigos(conn, "precificacao") == PRECIFICACOES_SUDESTE

    with como(conn, usuarios["analista_sul"]):
        assert _codigos(conn, "precificacao") == PRECIFICACOES_SUL


def test_busca_direta_por_precificacao_de_outra_carteira_volta_vazia(conn, usuarios):
    with como(conn, usuarios["analista_sudeste"]):
        achou = conn.execute("SELECT 1 FROM precificacao WHERE codigo = 'PRC-2026-0145'").fetchone()

    assert achou is None


def test_analista_so_enxerga_clientes_da_propria_carteira(conn, usuarios):
    with como(conn, usuarios["analista_sudeste"]):
        assert _codigos(conn, "cliente") == {"CLI-0001", "CLI-0002", "CLI-0005"}
        assert _codigos(conn, "carteira") == {"CART-SUDESTE"}

    with como(conn, usuarios["analista_sul"]):
        assert _codigos(conn, "cliente") == {"CLI-0004"}


def test_cliente_sem_carteira_so_aparece_para_quem_alcanca_todas(conn, usuarios):
    conn.execute("INSERT INTO cliente (codigo, razao_social, pais) VALUES ('CLI-SEM-CARTEIRA', 'Sem carteira', 'US')")

    with como(conn, usuarios["analista_sudeste"]):
        assert "CLI-SEM-CARTEIRA" not in _codigos(conn, "cliente")

    with como(conn, usuarios["admin"]):
        assert "CLI-SEM-CARTEIRA" in _codigos(conn, "cliente")


def test_administrador_enxerga_todas_as_carteiras(conn, usuarios):
    with como(conn, usuarios["admin"]):
        assert _codigos(conn, "precificacao") == TODAS_AS_PRECIFICACOES
        assert _total(conn, "cliente") == 5


# ------------------------------------------------------------ recorte por perfil


def test_suprimentos_nao_acessa_clientes_nem_precificacoes(conn, usuarios):
    with como(conn, usuarios["suprimentos"]):
        assert _total(conn, "precificacao") == 0
        assert _total(conn, "cliente") == 0
        assert _total(conn, "materia_prima") > 0
        assert _total(conn, "linha_producao") > 0


def test_executiva_nao_enxerga_dados_de_custo(conn, usuarios):
    with como(conn, usuarios["executiva_sudeste"]):
        assert _total(conn, "linha_producao") == 0
        assert _total(conn, "produtividade") == 0
        assert _total(conn, "aliquota_fiscal") == 0
        assert _codigos(conn, "precificacao") == PRECIFICACOES_SUDESTE


def test_so_quem_edita_cadastro_altera_materia_prima(conn, usuarios):
    alterar = "UPDATE materia_prima SET descricao = descricao || ' (rev)' WHERE codigo = 'MP-0001'"

    with como(conn, usuarios["analista_sudeste"]):
        assert conn.execute(alterar).rowcount == 0

    with como(conn, usuarios["suprimentos"]):
        assert conn.execute(alterar).rowcount == 1


def test_usuario_inativo_ou_sem_cadastro_nao_enxerga_nada(conn, usuarios):
    for usuario_id in (usuarios["inativo_sudeste"], uuid.uuid4()):
        with como(conn, usuario_id):
            assert _total(conn, "precificacao") == 0
            assert _total(conn, "cliente") == 0
            assert _total(conn, "materia_prima") == 0


def test_anonimo_nao_tem_acesso_as_tabelas(conn, usuarios):
    with como(conn, uuid.uuid4(), papel="anon"):
        _recusa(conn, "SELECT count(*) FROM precificacao")
        _recusa(conn, "SELECT count(*) FROM materia_prima")


# ------------------------------------------------------------ escrita


def test_analista_cria_precificacao_so_para_cliente_da_propria_carteira(conn, usuarios):
    produto = _id(conn, "produto", "PA-0001")
    cliente_sudeste = _id(conn, "cliente", "CLI-0001")
    cliente_sul = _id(conn, "cliente", "CLI-0004")
    inserir = (
        "INSERT INTO precificacao (codigo, cliente_id, produto_id, modalidade_comercial) "
        "VALUES (%s, %s, %s, 'full_service_nacional')"
    )

    with como(conn, usuarios["analista_sudeste"]):
        conn.execute(inserir, ["PRC-TESTE-1", cliente_sudeste, produto])
        _recusa(conn, inserir, ["PRC-TESTE-2", cliente_sul, produto])

        assert "PRC-TESTE-1" in _codigos(conn, "precificacao")


def test_executiva_nao_cria_precificacao(conn, usuarios):
    produto = _id(conn, "produto", "PA-0001")
    cliente_sudeste = _id(conn, "cliente", "CLI-0001")

    with como(conn, usuarios["executiva_sudeste"]):
        _recusa(
            conn,
            "INSERT INTO precificacao (codigo, cliente_id, produto_id, modalidade_comercial) "
            "VALUES ('PRC-TESTE-3', %s, %s, 'full_service_nacional')",
            [cliente_sudeste, produto],
        )


def test_gerente_aprova_so_na_propria_carteira(conn, usuarios):
    aprovar = "UPDATE precificacao SET status = 'aprovado' WHERE codigo = %s"

    with como(conn, usuarios["gerente_sul"]):
        assert conn.execute(aprovar, ["PRC-2026-0145"]).rowcount == 1
        assert conn.execute(aprovar, ["PRC-2026-0148"]).rowcount == 0


def test_precificacao_nao_pode_ser_movida_para_cliente_de_outra_carteira(conn, usuarios):
    cliente_sul = _id(conn, "cliente", "CLI-0004")

    with como(conn, usuarios["analista_sudeste"]):
        _recusa(conn, "UPDATE precificacao SET cliente_id = %s WHERE codigo = 'PRC-2026-0144'", [cliente_sul])


def test_ninguem_apaga_precificacao(conn, usuarios):
    with como(conn, usuarios["admin"]):
        _recusa(conn, "DELETE FROM precificacao WHERE codigo = 'PRC-2026-0144'")


# ------------------------------------------------------------ escalada de privilégio


def test_usuario_nao_muda_o_proprio_perfil_nem_a_propria_carteira(conn, usuarios):
    eu = usuarios["analista_sudeste"]
    perfil_admin = _id(conn, "perfil", "administrador")
    carteira_sul = _id(conn, "carteira", "CART-SUL")

    with como(conn, eu):
        assert conn.execute("UPDATE usuario SET perfil_id = %s WHERE id = %s", [perfil_admin, eu]).rowcount == 0
        _recusa(conn, "INSERT INTO usuario_carteira (usuario_id, carteira_id) VALUES (%s, %s)", [eu, carteira_sul])
        _recusa(
            conn,
            "INSERT INTO perfil_permissao (perfil_id, permissao_codigo) "
            "SELECT perfil_id, 'carteira.todas' FROM usuario WHERE id = %s",
            [eu],
        )

        assert _codigos(conn, "precificacao") == PRECIFICACOES_SUDESTE


def test_usuario_so_enxerga_o_proprio_cadastro(conn, usuarios):
    with como(conn, usuarios["analista_sudeste"]):
        assert [linha[0] for linha in conn.execute("SELECT id FROM usuario")] == [usuarios["analista_sudeste"]]

    with como(conn, usuarios["admin"]):
        assert _total(conn, "usuario") == len(USUARIOS)


def test_administrador_concede_carteira(conn, usuarios):
    carteira_sul = _id(conn, "carteira", "CART-SUL")

    with como(conn, usuarios["admin"]):
        conn.execute(
            "INSERT INTO usuario_carteira (usuario_id, carteira_id) VALUES (%s, %s)",
            [usuarios["analista_sudeste"], carteira_sul],
        )

    with como(conn, usuarios["analista_sudeste"]):
        assert _codigos(conn, "precificacao") == PRECIFICACOES_SUDESTE | PRECIFICACOES_SUL
