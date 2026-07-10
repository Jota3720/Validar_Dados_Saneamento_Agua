# Estado actual e plano de recuperação

Data de referência: 2026-07-10

Este documento é a fonte única de verdade temporária para recuperar o controlo do projecto.

## Regra principal

Até a auditoria local estar concluída:

- não apagar pastas;
- não substituir o projecto antigo;
- não executar `git reset --hard`;
- não fazer `git clean`;
- não copiar ficheiros entre pastas;
- não fazer `git pull`, `git push` ou novos commits sem primeiro identificar a pasta e o estado Git;
- não alterar regras topológicas apenas para reduzir o número de erros.

## O que está confirmado no GitHub `main`

O repositório oficial é:

```text
Jota3720/Validar_Dados_Saneamento_Agua
```

O GitHub contém uma arquitectura de pipeline com:

- configurações separadas para água e saneamento;
- mappings de layers;
- catálogo de regras;
- schema comum de erros;
- extracção Oracle read-only em `src/extraction.py` através de `python-oracledb`/`pandas`;
- normalização em `src/normalization.py`;
- validações geométricas, atributivas, de metadados e topológicas;
- runners completos `scripts/run_all.py` e `scripts/run_all_water.py`;
- outputs CSV/XLSX e, quando possível, GeoPackage.

## O que NÃO está confirmado no GitHub

À data deste documento, não estava comprovadamente presente em `main` a correcção local descrita pelo Codex para truncagem WKT por SQL*Plus com:

```sql
SET LONG ...
SET LONGCHUNKSIZE ...
```

Também não estava confirmado no GitHub o relatório local que alegava a redução dos erros topológicos de água de 20 878 para 3 253.

Isto não significa que o trabalho se perdeu. Significa apenas que pode estar:

- numa pasta local diferente;
- num workspace sem `.git`;
- num commit local ainda não enviado;
- em outputs locais não versionados.

## Divergência técnica que precisa de ser resolvida

Existem indícios de dois caminhos de extracção:

1. pipeline oficial baseada em `src/extraction.py` e `python-oracledb`;
2. scripts locais/antigos baseados em SQL*Plus.

O projecto deve terminar com um único caminho oficial de extracção, ou com dois backends explicitamente configurados e testados. Não devem existir duas implementações silenciosamente diferentes.

## Objectivo imediato

Antes de continuar a desenvolver, precisamos de responder com evidência a cinco perguntas:

1. Quantas pastas/cópias do projecto existem no computador?
2. Qual contém `.git` e aponta para o repositório oficial?
3. Qual contém as alterações mais recentes do Codex?
4. Quais são as últimas runs reais de água e saneamento?
5. Quais são os primeiros 20 erros reais de cada domínio, sem geometria sensível?

## Ferramenta de auditoria

Foi adicionado:

```text
scripts/99_generate_audit_bundle.py
```

Este script não altera código, não liga à Oracle e não apaga nada. Apenas:

- regista o estado Git da pasta onde é executado;
- procura as runs locais mais recentes;
- gera uma amostra pequena de erros de água e saneamento;
- remove colunas de geometria da amostra;
- cria um pacote em `outputs/auditoria/`.

Execução:

```powershell
python scripts/99_generate_audit_bundle.py
```

## Critério para retomar o desenvolvimento

Só retomamos alterações quando tivermos:

- o caminho absoluto da pasta oficial;
- `git status` e `git log` dessa pasta;
- o pacote de auditoria;
- um CSV pequeno de água;
- um CSV pequeno de saneamento;
- confirmação de qual extractor produziu cada run.

Depois disso, as decisões serão tomadas por comparação de resultados reais, não por suposições.