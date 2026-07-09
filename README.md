# Validador de Dados de Saneamento e Água

Pipeline não destrutivo para inventariar, extrair, normalizar e validar cadastro SIG de água e saneamento antes de modelação hidráulica.

O projecto trabalha em modo **read-only** sobre Oracle/GeoMedia e gera apenas diagnósticos locais. Não executa `UPDATE`, `DELETE`, `INSERT`, `MERGE`, `ALTER`, `DROP` ou alterações estruturais na base de produção.

## Estado actual

Este repositório já contém a arquitectura base, mappings, catálogo de regras, esquema único de erros e runners preparados para integração com Spatial Model/GeoMedia.

Ainda não contém a extracção Oracle real nem a normalização completa das layers de produção. A fase actual é uma base segura para receber essa lógica sem comprometer a BD.

Ver também:

- `docs/INVENTARIO_TECNICO_LACUNAS.md`
- `config/rules_catalog.yaml`
- `spatial_models/README.md`

## O que contém

- inventário de tabelas/views espaciais Oracle;
- configuração manual de layers relevantes;
- extracção local das entidades confirmadas;
- validação geométrica, topológica, atributiva, altimétrica e de metadados;
- catálogo central de regras;
- schema único de erros para GeoMedia/Spatial Model;
- exportação de erros por regra, resumo global e relatórios;
- base preparada para evoluir para exportação SWMM apenas numa fase posterior.

## Estrutura

```text
config/
  database.example.yaml
  project.yaml
  project_water.yaml
  layers_mapping.yaml
  layers_mapping_water.yaml
  rules_catalog.yaml
  tolerancias.yaml

docs/
  INVENTARIO_TECNICO_LACUNAS.md

scripts/
  00_inventory_database.py
  run_all.py
  run_all_water.py
  sm_master_runner.py
  sm_master_runner_water.py

src/
  issue_schema.py
  rule_catalog.py
  run_context.py
  geometry_rules.py
  attribute_rules.py
  metadata_rules.py
  topology_rules.py

tests/
outputs/
```

## Como usar

1. Criar `config/database.yaml` a partir de `config/database.example.yaml`.
2. Confirmar `config/layers_mapping.yaml` e `config/layers_mapping_water.yaml`.
3. Ajustar tolerâncias em `config/tolerancias.yaml`.
4. Confirmar/expandir `config/rules_catalog.yaml`.
5. Executar o inventário e depois o pipeline desejado.

Exemplos:

```powershell
python scripts/00_inventory_database.py --config config/database.yaml
python scripts/run_all.py --config config/project.yaml
python scripts/run_all_water.py --config config/project_water.yaml
```

Os runners criam uma pasta de execução em:

```text
outputs/runs/<timestamp>_<dominio>/
  erros/
  exports/
  logs/
  relatorios/
```

## Integração com Spatial Model / GeoMedia

A estratégia recomendada é:

```text
Spatial Model
  ↓ chama runner Python
scripts/sm_master_runner.py
ou
scripts/sm_master_runner_water.py
  ↓ gera outputs locais
outputs/runs/<run_id>/erros/validacao_erros.csv|xlsx|gpkg
  ↓
GeoMedia lê e simboliza os erros
```

O Spatial Model não deve escrever na BD Oracle de produção. Deve apenas chamar o pipeline ou consumir os outputs locais.

## Nota importante

Os outputs gerados localmente não são versionados no repositório. Cada execução escreve numa pasta própria em `outputs/runs/`.

Credenciais reais nunca devem ser versionadas. O ficheiro `config/database.yaml` deve permanecer local.
