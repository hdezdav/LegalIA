# Corpus de demostración

Los archivos de este directorio son un corpus **mínimo y de demostración**, cuyo
único propósito es ejercitar el pipeline completo: ingestion → chunking →
embeddings → retrieval → citations.

## Advertencia sobre el contenido

**Estos extractos NO son una fuente oficial y no deben usarse como referencia
jurídica.** Fueron transcritos para pruebas técnicas y pueden contener errores,
omisiones o texto desactualizado.

Antes de cualquier uso real:

1. Verifica cada texto contra su fuente oficial
   (SUIN-Juriscol, Diario Oficial, portal de la Corte correspondiente).
2. Reingiere el documento con `--source-url` apuntando a esa fuente.
3. Establece la vigencia con `--status`, que **nunca** se infiere del texto.

## Vigencia

La ingestion marca por defecto `DESCONOCIDO`. Eso es deliberado: una norma casi
nunca dice en su propio texto que fue derogada, así que asumir `VIGENTE` porque
nada lo contradijo es exactamente el error que el estado `DESCONOCIDO` existe
para evitar.

Para marcar un documento como vigente hay que decirlo explícitamente:

```bash
python -m ingestion.main --file corpus/constitucion_extracto.txt \
  --status VIGENTE \
  --source-name "Constitución Política de Colombia" \
  --source-url "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=4125"
```

## Cómo cargarlo

```bash
# Desde la raíz del repositorio, con el stack levantado
./scripts/ingest.sh --directory corpus/

# O directamente, sin Docker
PYTHONPATH=backend:. .venv/bin/python -m ingestion.main --directory corpus/
```

Para ver qué haría sin escribir nada:

```bash
PYTHONPATH=backend:. .venv/bin/python -m ingestion.main --directory corpus/ --dry-run
```

## Corpus real

El corpus definitivo (SUIN-Juriscol, CENDOJ, Corte Constitucional, Corte Suprema,
Consejo de Estado) es una fase posterior. Ver `docs/ROADMAP.md`.
