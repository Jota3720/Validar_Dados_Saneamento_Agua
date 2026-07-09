# Guia Completo do Validador de Agua e Saneamento

## Objectivo

Preparar cadastro SIG para modelacao hidraulica/hidrologica sem alterar a base de producao. O sistema identifica anomalias, classifica gravidade e exporta erros para correcao manual no SIG.

## Fluxo

1. Inventario da BD Oracle.
2. Confirmacao manual das layers e campos.
3. Extracao local das entidades relevantes.
4. Normalizacao de links, nodes, ramais e zonas.
5. Validacao geometrica.
6. Validacao topologica e conectividade.
7. Validacao atributiva e de metadados.
8. Exportacao master de erros.
9. Relatorio final.
10. Exportacao SWMM apenas mais tarde, se os criterios minimos forem cumpridos.

## Outputs

- `outputs/exports/` para dados normalizados;
- `outputs/erros/` para erros master e por regra;
- `outputs/relatorios/` para inventario, resumos e relatórios;
- `outputs/runs/` para snapshots completos por execucao.

## Ficheiros principais

- `config/database.example.yaml`
- `config/layers_mapping.yaml`
- `config/layers_mapping_water.yaml`
- `config/tolerancias.yaml`
- `config/project.yaml`
- `config/project_water.yaml`
- `scripts/run_all.py`
- `scripts/run_all_water.py`
- `scripts/00_inventory_database.py`
- `scripts/01_extract_layers.py`
- `scripts/01_extract_layers_water.py`
- `scripts/03_validate_geometry.py`
- `scripts/04_validate_topology_nodes_links.py`
- `scripts/06_validate_attributes.py`
- `scripts/09_generate_report.py`

## Regras de saida

Cada erro deve transportar:

- `error_id`
- `regra_id`
- `categoria`
- `tipo_erro`
- `gravidade`
- `source_layer`
- `source_id`
- `related_layer`
- `related_id`
- `tolerancia_m`
- `descricao`
- `acao_sugerida`
- `data_execucao`
- `confidence`
- `falso_positivo_possivel`
- `geometry`

## Notas para auditoria

- o pipeline e repetivel;
- os outputs sao locais e nao destrutivos;
- a classificacao automatica de layers e apenas uma proposta;
- os casos ambíguos devem ser marcados como possiveis falsos positivos;
- os campos e regras podem ser refinados sem alterar a metodologia.
