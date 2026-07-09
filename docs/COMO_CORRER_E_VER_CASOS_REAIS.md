# Como correr e ver casos reais da base de dados

Este guia assume que `config/database.yaml` já existe localmente no Codex e que contém credenciais read-only para Oracle.

## 1. Actualizar a pasta local

```powershell
git pull origin main
```

## 2. Teste pequeno antes de correr tudo

Para evitar uma extracção pesada logo à primeira, podes editar temporariamente:

- `config/project.yaml`
- `config/project_water.yaml`

E colocar:

```yaml
extraction:
  row_limit: 500
```

Depois de validares que tudo corre, volta a `row_limit: null`.

## 3. Correr saneamento

```powershell
python scripts/run_all.py --config config/project.yaml
```

Output principal:

```text
outputs/runs/<timestamp>_saneamento/
```

Verifica:

```text
exports/raw/*.csv
exports/normalizado/network_normalized.csv
erros/validacao_erros.csv
erros/validacao_erros_legivel.xlsx
erros/validacao_erros.gpkg
relatorios/resumo_erros_por_regra.xlsx
relatorios/amostra_casos_reais.xlsx
relatorios/extracao_layers.xlsx
relatorios/normalizacao_resumo.xlsx
```

## 4. Correr água

```powershell
python scripts/run_all_water.py --config config/project_water.yaml
```

Output principal:

```text
outputs/runs/<timestamp>_agua/
```

Verifica os mesmos ficheiros.

## 5. Onde olhar primeiro

### Para leitura humana

Abrir:

```text
erros/validacao_erros_legivel.xlsx
```

Colunas principais:

- `gravidade`
- `tema`
- `regra`
- `camada`
- `id_entidade`
- `erro`
- `correcao_sugerida`
- `geometria_wkt`

### Para resumo

Abrir:

```text
relatorios/resumo_erros_por_regra.xlsx
```

Isto mostra quantos erros existem por regra, severidade e tema.

### Para amostra rápida

Abrir:

```text
relatorios/amostra_casos_reais.xlsx
```

Mostra os primeiros 50 erros ordenados por severidade.

### Para GeoMedia/QGIS

Abrir:

```text
erros/validacao_erros.gpkg
```

Layer:

```text
validacao_erros
```

Se o GPKG não for criado, confirma se tens `geopandas`, `shapely`, `fiona/pyogrio` instalados e se os erros têm `geometry_wkt` válido.

## 6. Testar por etapas

Extracção:

```powershell
python scripts/01_extract_layers.py --config config/project.yaml
python scripts/01_extract_layers.py --config config/project_water.yaml
```

Normalização da última run:

```powershell
python scripts/02_normalize_network.py --config config/project.yaml
python scripts/02_normalize_network.py --config config/project_water.yaml
```

Validações isoladas:

```powershell
python scripts/03_validate_geometry.py --config config/project.yaml
python scripts/04_validate_attributes.py --config config/project.yaml
python scripts/05_validate_intersections.py --config config/project.yaml
python scripts/06_validate_metadata.py --config config/project.yaml
```

Para água, troca para:

```powershell
--config config/project_water.yaml
```

## 7. Como escolher um caso real para comparar

Começa pelo ficheiro:

```text
relatorios/amostra_casos_reais.xlsx
```

Escolhe uma linha com:

- `gravidade = CRITICA` ou `ALTA`
- `tema = TOPOLOGIA` ou `ATRIBUTOS`
- `id_entidade` preenchido

Depois procura esse `id_entidade` no GeoMedia/Oracle e compara com o que o validador antigo dizia.

## 8. Interpretação dos primeiros resultados

Se aparecerem muitos erros de `Diâmetro em falta`, provavelmente falta mapear o campo real de diâmetro no normalizador.

Se aparecerem muitos erros de metadados, confirma se os nomes dos campos reais são estes ou se têm variantes no Oracle.

Se aparecerem muitos erros topológicos, primeiro valida se o `geometry_wkt` está correcto e se a tolerância em `config/tolerancias.yaml` é razoável.

## 9. Segurança

A extracção usa SELECT e escreve apenas outputs locais. O pipeline não deve alterar a BD Oracle.
