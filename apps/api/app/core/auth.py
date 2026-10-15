"""Autenticação e autorização da API (US03, issue #44).

O front manda o access token do Supabase Auth no cabeçalho
`Authorization: Bearer <token>`. A API confirma o token no próprio Supabase
(serve para chave simétrica ou assimétrica e respeita logout e expiração) e
carrega o perfil e as permissões da tabela `usuario`. É a segunda camada de
autorização: quem barra o dado continua sendo o RLS (docs/controle-de-acesso.md).
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.infrastructure.supabase_client import supabase_servico

_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class UsuarioAutenticado:
    id: UUID
    nome: str
    email: str
    perfil_codigo: str
    perfil_nome: str
    permissoes: frozenset[str] = field(default_factory=frozenset)
    access_token: str = field(default="", repr=False)

    def tem_permissao(self, codigo: str) -> bool:
        return codigo in self.permissoes


def _nao_autenticado(motivo: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=motivo,
        headers={"WWW-Authenticate": "Bearer"},
    )


def validar_token(access_token: str) -> UUID:
    """Devolve o id do usuário dono do token ou levanta 401."""
    try:
        resposta = supabase_servico().auth.get_user(access_token)
    except RuntimeError:
        raise
    except Exception as erro:
        raise _nao_autenticado("Sessão inválida ou expirada.") from erro
    if resposta is None or resposta.user is None:
        raise _nao_autenticado("Sessão inválida ou expirada.")
    return UUID(resposta.user.id)


def carregar_usuario(db: Session, usuario_id: UUID) -> dict | None:
    linha = (
        db.execute(
            text(
                """
                SELECT u.nome, u.email, u.ativo, p.codigo AS perfil_codigo, p.nome AS perfil_nome,
                       COALESCE(
                           array_agg(pp.permissao_codigo) FILTER (WHERE pp.permissao_codigo IS NOT NULL),
                           '{}'
                       ) AS permissoes
                FROM usuario u
                JOIN perfil p ON p.id = u.perfil_id
                LEFT JOIN perfil_permissao pp ON pp.perfil_id = p.id
                WHERE u.id = :id
                GROUP BY u.id, p.id
                """
            ),
            {"id": usuario_id},
        )
        .mappings()
        .first()
    )
    return dict(linha) if linha else None


def usuario_atual(
    credenciais: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> UsuarioAutenticado:
    if credenciais is None or not credenciais.credentials:
        raise _nao_autenticado("Faça login para continuar.")

    usuario_id = validar_token(credenciais.credentials)
    dados = carregar_usuario(db, usuario_id)
    if dados is None or not dados["ativo"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário sem acesso ao NeoPrice. Peça a liberação ao administrador.",
        )

    return UsuarioAutenticado(
        id=usuario_id,
        nome=dados["nome"],
        email=dados["email"],
        perfil_codigo=dados["perfil_codigo"],
        perfil_nome=dados["perfil_nome"],
        permissoes=frozenset(dados["permissoes"]),
        access_token=credenciais.credentials,
    )


def exigir_permissao(codigo: str) -> Callable[..., UsuarioAutenticado]:
    """Dependência que barra com 403 quem não tem a permissão nomeada."""

    def _verificar(usuario: UsuarioAutenticado = Depends(usuario_atual)) -> UsuarioAutenticado:
        if not usuario.tem_permissao(codigo):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Seu perfil não tem a permissão {codigo}.",
            )
        return usuario

    return _verificar
