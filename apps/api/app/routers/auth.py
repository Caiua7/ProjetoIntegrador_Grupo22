from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth import UsuarioAutenticado, usuario_atual

router = APIRouter(prefix="/auth", tags=["auth"])


class SessaoUsuario(BaseModel):
    id: UUID
    nome: str
    email: str
    perfil_codigo: str
    perfil_nome: str
    permissoes: list[str]


@router.get("/me", response_model=SessaoUsuario)
def me(usuario: UsuarioAutenticado = Depends(usuario_atual)) -> SessaoUsuario:
    return SessaoUsuario(
        id=usuario.id,
        nome=usuario.nome,
        email=usuario.email,
        perfil_codigo=usuario.perfil_codigo,
        perfil_nome=usuario.perfil_nome,
        permissoes=sorted(usuario.permissoes),
    )
