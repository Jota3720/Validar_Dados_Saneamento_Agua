# Spatial Model Editor

Este repositorio publica a base do projeto para uso com GeoMedia / Spatial Model Editor.

Os modelos publicados aqui servem como referencia da metodologia. A logica de validacao principal vive no pipeline Python e os modelos SM devem chamar esse pipeline ou ler os outputs gerados localmente.

Regra pratica:

- usar um input de directorio para apontar para a raiz do projeto;
- usar um operador de execucao para chamar `scripts/run_all.py` ou `scripts/run_all_water.py`;
- ligar um output de ficheiro para receber a shape/ficheiro final gerado pelo script;
- manter o modelo sem escrita na BD de producao.
