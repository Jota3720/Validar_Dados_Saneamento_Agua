# Validador de Dados de Saneamento e Agua

Pipeline nao destrutivo para inventariar, extrair, normalizar e validar cadastro SIG de agua e saneamento antes de modelacao hidraulica.

O projeto trabalha em modo read-only sobre Oracle/GeoMedia e gera apenas diagnosticos locais. Nao executa `UPDATE`, `DELETE`, `INSERT`, `MERGE`, `ALTER`, `DROP` ou alteracoes estruturais na base de producao.

## O que contem

- inventario de tabelas/views espaciais Oracle;
- configuracao manual de layers relevantes;
- extracao local das entidades confirmadas;
- validacao geometrica, topologica, atributiva, altimetrica e de metadados;
- exportacao de erros por regra, resumo global e relatorios;
- base preparada para evoluir para exportacao SWMM apenas numa fase posterior.

## Estrutura

```text
config/
docs/
scripts/
src/
tests/
outputs/
```

## Como usar

1. Criar `config/database.yaml` a partir de `config/database.example.yaml`.
2. Confirmar `config/layers_mapping.yaml` e `config/layers_mapping_water.yaml`.
3. Ajustar tolerancias em `config/tolerancias.yaml`.
4. Executar o inventario e depois o pipeline desejado.

Exemplos:

```powershell
python scripts/00_inventory_database.py --config config/database.yaml
python scripts/run_all.py --config config/project.yaml
python scripts/run_all_water.py --config config/project_water.yaml
```

## Nota importante

Os outputs gerados localmente nao sao versionados no repositório. Cada execucao escreve numa pasta de run propria em `outputs/`.
