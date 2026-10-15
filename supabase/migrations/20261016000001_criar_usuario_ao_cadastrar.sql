-- ============================================================
-- Migration: linha em `usuario` criada junto com o cadastro no Supabase Auth
-- Issue #44 (US03) — Sprint 1
-- Executar via: supabase db push
--
-- Quem se cadastra no Supabase Auth ganha automaticamente a linha em
-- `usuario`, com o mesmo id, mas INATIVA e com o perfil de menor alcance
-- (`executiva_contas`, só leitura). Sem ativação o RLS não libera nada e a
-- API responde 403 ("Peça a liberação ao administrador"): o cadastro não
-- dá acesso sozinho. Quem tem `acesso.administrar` ativa e escolhe o perfil.
--
-- O nome vem de `raw_user_meta_data->>'nome'` (ou 'full_name'); sem ele,
-- usa a parte do e-mail antes do @.
-- ============================================================

CREATE FUNCTION criar_usuario_do_auth()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    INSERT INTO usuario (id, nome, email, perfil_id, ativo)
    SELECT
        NEW.id,
        LEFT(COALESCE(
            NULLIF(TRIM(NEW.raw_user_meta_data->>'nome'), ''),
            NULLIF(TRIM(NEW.raw_user_meta_data->>'full_name'), ''),
            split_part(NEW.email, '@', 1)
        ), 150),
        NEW.email,
        p.id,
        FALSE
    FROM perfil p
    WHERE p.codigo = 'executiva_contas'
    ON CONFLICT DO NOTHING;  -- id ou e-mail já cadastrados: não bloqueia o cadastro

    RETURN NEW;
END;
$$;

REVOKE EXECUTE ON FUNCTION criar_usuario_do_auth() FROM PUBLIC;

CREATE TRIGGER trg_auth_criar_usuario
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION criar_usuario_do_auth();
