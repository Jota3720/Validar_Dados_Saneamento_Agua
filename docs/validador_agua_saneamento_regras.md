# Regras do Validador de Agua e Saneamento

Este documento resume a metodologia do projeto:

- inventario da base Oracle em read-only;
- confirmacao manual das layers relevantes;
- extracao local para GeoPackage/CSV;
- normalizacao de nomes e campos;
- validacao geometrica, topologica, atributiva e de metadados;
- exportacao de erros por regra e de um conjunto master;
- relatorio final em Markdown e HTML.

## Criticidade

- CRITICA: impede construcao fiavel do modelo;
- ALTA: prejudica fortemente a modelacao;
- MEDIA: reduz qualidade, mas pode ser aceitavel;
- BAIXA/AVISO: situacao a validar.

## Regras base

### Geometria
- geometria invalida;
- linha de comprimento zero/quase zero;
- multipart indevido;
- duplicado geometrico;
- sobreposicao parcial;
- auto-intersecoes/anomalias;
- CRS inconsistente ou nao metrico.

### Topologia
- no/nodo sem ligacao relevante;
- nodo perto mas sem tocar;
- link sem nodo proximo;
- extremidades de link sem nodo;
- endpoint perto mas nao coincidente;
- links a cruzarem sem nodo valido;
- node grau 0/1 conforme contexto;
- componentes isoladas.

### Atributos e metadados
- ID nulo/duplicado;
- estado em falta ou incompatível;
- diametro em falta ou invalido;
- material em falta;
- tipo de rede em falta;
- cotas em falta quando aplicaveis;
- arruamento, freguesia CAOP e numero de policia em falta quando a coluna e aplicavel.

### Nuances importantes
- ramais podem tocar diretamente em tubagens;
- alguns elementos tocam ramais e isso nao e erro por si;
- ligações em agua usam as camadas `GIA.V*` para geometria e atributos;
- em saneamento, as vistas `GIA.E*` sao a referencia para topologia e geometria;
- numero de policia so se avalia em ramais e ligacoes de ramal quando o campo existe;
- SN nao e erro em si, apenas um valor possivel.
