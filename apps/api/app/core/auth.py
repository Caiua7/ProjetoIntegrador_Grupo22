"""Autenticação e autorização da API (US03, issue #44).

O front manda o access token do Supabase Auth no cabeçalho
`Authorization: Bearer <token>`. A API confirma o token no próprio Supabase
(serve para chave simétrica ou assimétrica e respeita logout e expiração) e
carrega o perfil e as permissões da tabela `usuario`. É a segunda camada de
autorização: quem barra o dado continua sendo o RLS (docs/controle-de-acesso.md).
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from supabase_auth.errors import AuthApiError, AuthInvalidJwtError, AuthSessionMissingError

from app.infrastructure.database import get_db
from app.infrastructure.supabase_client import supabase_servico

_bearer = HTTPBearer(auto_error=False)
logger = logging.getLogger("neoprice.auth")


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


def _token_recusado(erro: Exception) -> bool:
    """O Supabase recusou o token (inválido, expirado, usuário removido).

    Timeout, falha de rede, limite de taxa (429) e erro 5xx do Supabase não
    dizem nada sobre o token: tratá-los como 401 desloga o usuário por causa
    de uma falha passageira (visto no teste de carga da issue #59).
    """
    if isinstance(erro, AuthInvalidJwtError | AuthSessionMissingError):
        return True
    return isinstance(erro, AuthApiError) and erro.status in {400, 401, 403, 404}


def validar_token(access_token: str) -> UUID:
    """Devolve o id do usuário dono do token; 401 se recusado, 503 se o Supabase falhar."""
    for tentativa in (1, 2):
        try:
            resposta = supabase_servico().auth.get_user(access_token)
            break
        except RuntimeError:
            raise
        except Exception as erro:
            if _token_recusado(erro):
                raise _nao_autenticado("Sessão inválida ou expirada.") from erro
            if tentativa == 2:
                logger.exception("falha ao validar o token no Supabase")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Não foi possível confirmar sua sessão agora. Tente de novo em instantes.",
                ) from erro
    if resposta is None or resposta.user is None:
        raise _nao_autenticado("Sessão inválida ou expirada.")
    return UUID(resposta.user.id)


def carregar_usuario(db: Session, usuario_id: UUID) -> dict | None:
    """Perfil e permissões do usuário.

    Vai pela API REST do Supabase (HTTPS, porta 443) com a chave de serviço, e
    não por conexão direta ao Postgres: redes de faculdade e de empresa
    costumam bloquear as portas 5432/6543, e o login não pode depender delas.
    `db` fica na assinatura por compatibilidade com quem substitui a função.
    """
    del db
    try:
        resposta = (
            supabase_servico()
            .table("usuario")
            .select("nome, email, ativo, perfil:perfil_id(codigo, nome, perfil_permissao(permissao_codigo))")
            .eq("id", str(usuario_id))
            .limit(1)
            .execute()
        )
    except RuntimeError:
        raise
    except Exception as erro:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Não foi possível carregar seu perfil agora. Tente de novo em instantes.",
        ) from erro

    linhas = resposta.data or []
    if not linhas:
        return None
    linha = linhas[0]
    perfil = linha.get("perfil") or {}
    return {
        "nome": linha["nome"],
        "email": linha["email"],
        "ativo": linha["ativo"],
        "perfil_codigo": perfil.get("codigo", ""),
        "perfil_nome": perfil.get("nome", ""),
        "permissoes": sorted(item["permissao_codigo"] for item in perfil.get("perfil_permissao") or []),
    }


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
