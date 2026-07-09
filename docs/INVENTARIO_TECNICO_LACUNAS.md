# Inventário técnico de lacunas e plano de correcção

## Diagnóstico directo

O repositório está bem encaminhado como base de arquitectura, mas ainda não é um validador operacional completo. A maior parte da estrutura existe, mas vários componentes críticos ainda são placeholders ou contratos mínimos.

## O que está bem

- O projecto está separado por `config/`, `scripts/`, `src/`, `tests/`, `docs/` e `outputs/`.
- A abordagem é não destrutiva: leitura sobre Oracle/GeoMedia e outputs locais.
- Existem mappings separados para saneamento e água.
- Existem tolerâncias explícitas para snap, proximidade, isolamento, duplicados e comprimentos mínimos.
- Já há intenção de integração com Spatial Model Editor através de runners específicos.
- Existem testes iniciais para regras de geometria, atributos, metadados e topologia.

## O que não estava a correr bem

### 1. Pipeline principal ainda não executava validação real

`scripts/run_all.py` e `scripts/run_all_water.py` apenas criavam pastas. Isto permite uma demonstração superficial, mas não executa inventário, extracção, normalização, validação nem relatório real.

### 2. Regras sem catálogo formal

As regras existiam dispersas no código, sem uma matriz central com código, domínio, tema, severidade, tolerância, descrição e sugestão de correcção. Isto dificulta auditoria, evolução e apresentação interna.

### 3. Esquema de erros inconsistente

As funções devolviam colunas como `regra_id`, `tipo_erro` e `gravidade`, mas não havia um schema único para consumo por GeoMedia/Spatial Model. Isto cria problemas quando se juntam erros de água, saneamento, geometria, atributos e metadados.

### 4. Código demasiado orientado a saneamento

Algumas regras e códigos vinham com prefixo `SAN`, mesmo quando a lógica é comum a água e saneamento. Isto precisa de parametrização por domínio.

### 5. Topologia ainda era placeholder

`src/topology_rules.py` indicava explicitamente que a lógica completa estava fora do repo. Para Spatial Model/GeoMedia isto é frágil, porque a camada publicada não prova a validação de conectividade.

### 6. Inventário Oracle ainda é simulado

O script de inventário cria um relatório preparado, mas ainda não consulta metadados reais de Oracle Spatial, SRID, tipo geométrico ou contagem de registos.

### 7. Falta normalização de dados de entrada

Ainda falta transformar as layers Oracle num schema comum, por exemplo:

- `source_layer`
- `source_id`
- `model_group`
- `entity_type`
- `diameter_mm`
- `status`
- `geometry`
- `geometry_wkt`

Sem isto, as regras não conseguem ser genéricas.

### 8. Spatial Model ainda só deve orquestrar

Não faz sentido replicar toda a lógica em Spatial Model. O caminho mais robusto é usar Spatial Model para chamar o pipeline Python e ler os outputs finais no GeoMedia.

## O que foi acrescentado nesta revisão

- Catálogo central de regras em `config/rules_catalog.yaml`.
- Schema único de erros em `src/issue_schema.py`.
- Utilitário de catálogo de regras em `src/rule_catalog.py`.
- Contexto de execução com `run_id` e pastas por execução em `src/run_context.py`.
- Runners `run_all.py` e `run_all_water.py` passam a criar execução estruturada, manifesto, catálogo exportado e camada/tabela base de erros.
- Regras de geometria, atributos e metadados passam a aceitar domínio/prefixo.
- Topologia deixa de ser apenas placeholder e passa a ter validação mínima de endpoints com tolerância quando existe geometria Shapely.
- Project YAML passa a apontar para o catálogo de regras.

## O que continua em falta

### Essencial para ficar operacional

1. Implementar extracção real Oracle read-only.
2. Implementar normalização real das layers para GeoDataFrames comuns.
3. Persistir outputs reais em GPKG com geometria.
4. Completar validações de topologia com grafos NetworkX.
5. Validar nomes reais das views/tabelas no GeoMedia/Oracle.
6. Confirmar campos reais de diâmetro, material, estado, cotas, arruamento, freguesia e número de polícia.
7. Criar fixtures ou amostras anonimizadas para testes realistas.
8. Criar modelo Spatial Model mínimo que chame o runner e abra o GPKG final.

### Prioridade recomendada

1. Confirmar mappings Oracle.
2. Criar `01_extract_layers.py` funcional.
3. Criar `02_normalize_network.py` funcional.
4. Implementar `03_validate_geometry.py`, `04_validate_attributes.py`, `05_validate_topology.py`, `06_validate_metadata.py`.
5. Consolidar output único `validacao_erros.gpkg`.
6. Ligar Spatial Model apenas ao runner final.

## Decisão técnica recomendada

Manter arquitectura híbrida:

```text
Oracle/GeoMedia read-only
  ↓
Python: extracção, normalização, topologia, grafos, relatórios
  ↓
Outputs locais: GPKG, CSV, XLSX, HTML
  ↓
Spatial Model: orquestração e publicação
  ↓
GeoMedia: visualização, filtragem e correcção operacional
```

Esta abordagem é mais robusta do que tentar reconstruir toda a lógica no editor gráfico do Spatial Model.
