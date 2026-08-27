-- =============================================================================
-- LegalIA - PostgreSQL bootstrap
-- =============================================================================
-- Runs ONCE, on an empty data directory, before Alembic ever connects.
-- Scope is deliberately narrow: extensions and database-level configuration
-- that migrations should not own. All tables, indexes and constraints belong to
-- Alembic (see backend/alembic/versions/).
-- =============================================================================

-- --- Extensions --------------------------------------------------------------

-- Vector storage and ANN indexes for chunk embeddings.
CREATE EXTENSION IF NOT EXISTS vector;

-- Trigram matching: used for fuzzy lookups on document titles and citation
-- strings ("Sentencia C-355 de 2006" vs "C-355/06"), where full-text search
-- alone is too rigid.
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Accent-insensitive comparisons. Colombian legal text is inconsistently
-- accented across sources, so lookups must survive "articulo" vs "artículo".
CREATE EXTENSION IF NOT EXISTS unaccent;

-- gen_random_uuid() for primary keys.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- --- Full-text search configuration ------------------------------------------
-- The lexical half of hybrid retrieval searches Spanish legal prose. The stock
-- 'spanish' configuration stems correctly but keeps accents, which makes
-- retrieval sensitive to source-side accent noise. This configuration chains
-- unaccent before the Spanish stemmer so 'articulo' and 'artículo' produce the
-- same lexeme.
--
-- Referenced from application code and migrations as 'legal_es'. Changing this
-- name is a breaking change: every stored tsvector would need rebuilding.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_ts_config WHERE cfgname = 'legal_es'
    ) THEN
        CREATE TEXT SEARCH CONFIGURATION legal_es (COPY = spanish);

        ALTER TEXT SEARCH CONFIGURATION legal_es
            ALTER MAPPING FOR asciiword, asciihword, hword_asciipart,
                              word, hword, hword_part
            WITH unaccent, spanish_stem;
    END IF;
END
$$;

-- --- Database defaults -------------------------------------------------------

-- Make legal_es the default so an unqualified to_tsvector()/to_tsquery() in an
-- ad-hoc query behaves like the application does. Application code and
-- migrations still pass the configuration explicitly rather than relying on
-- this default.
--
-- ALTER DATABASE needs a literal identifier, and the target name is only known
-- at runtime from POSTGRES_DB, so it is resolved via current_database().
DO $$
BEGIN
    EXECUTE format(
        'ALTER DATABASE %I SET default_text_search_config = %L',
        current_database(),
        'public.legal_es'
    );
END
$$;

-- --- Verification ------------------------------------------------------------
-- Fails the container's init phase loudly if an extension did not land, instead
-- of surfacing later as a confusing migration error.
DO $$
DECLARE
    missing text;
BEGIN
    SELECT string_agg(required, ', ')
      INTO missing
      FROM (VALUES ('vector'), ('pg_trgm'), ('unaccent'), ('pgcrypto')) AS t(required)
     WHERE NOT EXISTS (
        SELECT 1 FROM pg_extension WHERE extname = t.required
     );

    IF missing IS NOT NULL THEN
        RAISE EXCEPTION 'LegalIA bootstrap failed, missing extensions: %', missing;
    END IF;

    RAISE NOTICE 'LegalIA bootstrap complete: vector, pg_trgm, unaccent, pgcrypto, legal_es';
END
$$;
