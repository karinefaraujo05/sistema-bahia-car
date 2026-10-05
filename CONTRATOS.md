# Modelos de contrato

> **MODELO PROVISÓRIO. NÃO USAR COM CLIENTES ANTES DA REVISÃO DE UM ADVOGADO.**
> Este texto foi escrito como ponto de partida técnico. Ele não substitui orientação jurídica. Cada cláusula está marcada com `<!-- REVISAR COM ADVOGADO -->` nos templates HTML.

## Como usar este arquivo (para o Claude Code)

- Converta cada modelo em template HTML do Django em `contratos/templates/contratos/`, um arquivo por modelo, com os blocos comuns em `partials/`.
- Os placeholders usam a sintaxe de template do Django: `{{ variavel }}` e `{% if %}`.
- O filtro `|extenso` escreve valores por extenso em reais. Implemente com a biblioteca `num2words` (`lang="pt_BR"`). Verifique se a saída em moeda está correta e escreva testes para valores com centavos.
- Antes de gerar, o sistema verifica se todos os campos usados no modelo estão preenchidos. Se faltar algo, mostra a lista do que falta, com link para preencher. Nunca gera contrato com campo vazio ou "None".
- Todo contrato gerado tem numeração sequencial única (`{{ contrato.numero }}`) e é salvo como Documento do negócio.

## Qual modelo usar

| Situação | Quem é dono do carro | Modelo |
|---|---|---|
| Loja compra um carro de um particular | Particular → Loja | **A. Compra pela loja** |
| Loja vende um carro dela | Loja → Cliente | **B. Venda pela loja** |
| Loja vende carro dela e recebe o carro do cliente como parte do pagamento | Loja ↔ Cliente | **C. Troca com a loja** |
| Particular deixa o carro na loja para ser vendido | Continua do particular | **D. Consignação** |
| Venda de carro consignado, ou negócio entre dois particulares que a loja intermediou (venda ou troca) | Particular → Particular | **E. Intermediação** |

Uma operação pode gerar mais de um contrato. Exemplo: cliente entrega o carro dele como parte do pagamento de um carro consignado. Isso é um contrato E (venda do consignado) mais um contrato A (loja comprando o carro do cliente), ou um E de troca, dependendo de quem fica com o carro do cliente. Na dúvida, o sistema pergunta "O carro que o cliente deu fica com quem?".

---

## Blocos comuns

### [B1] Cabeçalho

```
{{ contrato.titulo }}
Contrato nº {{ contrato.numero }}
```

### [B2] Qualificação da loja

```
{{ loja.razao_social }}, pessoa jurídica de direito privado, inscrita no CNPJ sob o nº {{ loja.cnpj }}, com sede em {{ loja.endereco }}, {{ loja.cidade }}/{{ loja.uf }}, CEP {{ loja.cep }}, neste ato representada por {{ loja.representante_nome }}, inscrito no CPF sob o nº {{ loja.representante_cpf }}, doravante denominada {{ papel_loja }}.
```

### [B3] Qualificação de pessoa

Pessoa física:

```
{{ p.nome }}, {{ p.nacionalidade }}, {{ p.estado_civil }}, {{ p.profissao }}, portador(a) da cédula de identidade RG nº {{ p.rg }} {{ p.rg_orgao_emissor }}, inscrito(a) no CPF sob o nº {{ p.cpf }}, residente e domiciliado(a) em {{ p.endereco }}, {{ p.cidade }}/{{ p.uf }}, CEP {{ p.cep }}, telefone {{ p.telefone }}, doravante denominado(a) {{ papel }}.
```

Pessoa jurídica:

```
{{ p.nome }}, pessoa jurídica de direito privado, inscrita no CNPJ sob o nº {{ p.cnpj }}, com sede em {{ p.endereco }}, {{ p.cidade }}/{{ p.uf }}, CEP {{ p.cep }}, neste ato representada por {{ p.representante_nome }}, CPF {{ p.representante_cpf }}, doravante denominada {{ papel }}.
```

### [B4] Identificação de veículo

Renderizar como tabela, uma por veículo:

```
Marca/Modelo: {{ v.marca }} {{ v.modelo }}
Ano fabricação/modelo: {{ v.ano_fabricacao }}/{{ v.ano_modelo }}
Cor: {{ v.cor }}            Combustível: {{ v.combustivel }}
Placa: {{ v.placa }}        Renavam: {{ v.renavam }}
Chassi: {{ v.chassi }}
Quilometragem na entrega: {{ item.km_entrega }} km
Proprietário(a) no documento: {{ v.proprietario_registral }}
Valor atribuído neste contrato: R$ {{ item.valor }} ({{ item.valor|extenso }})
```

### [B5] Alienação fiduciária (incluir só se o veículo tiver financiamento ativo)

```
O veículo {{ v.placa }} encontra-se alienado fiduciariamente a {{ v.credor_alienacao }}, com saldo devedor declarado pelo(a) devedor(a) de R$ {{ v.saldo_devedor }} ({{ v.saldo_devedor|extenso }}), em {{ v.parcelas_restantes }} parcelas de R$ {{ v.valor_parcela }}, com vencimento todo dia {{ v.dia_vencimento }}{% if v.parcelas_vencidas %}, havendo {{ v.parcelas_vencidas }} parcela(s) vencida(s) e não paga(s){% endif %}.

As partes declaram ter ciência de que, enquanto não houver quitação, a propriedade do veículo pertence ao credor fiduciário, e de que a transferência para o nome do adquirente depende da quitação do financiamento ou da anuência expressa do credor. As partes declaram ainda ter ciência de que assumir o pagamento das parcelas sem a anuência do credor não torna o adquirente proprietário perante o credor nem perante o órgão de trânsito.

{{ clausula_quitacao }}
```

`clausula_quitacao` é escolhida no formulário entre:

1. "A quitação do saldo devedor será feita por {{ responsavel }} até {{ data }}, mediante apresentação do comprovante à outra parte."
2. "O saldo devedor será descontado do preço e pago diretamente ao credor por {{ responsavel }}."
3. "As partes buscarão a anuência do credor para a transferência do financiamento, e a entrega definitiva do veículo fica condicionada a essa anuência."

### [B6] Entrega e débitos

```
A entrega do(s) veículo(s) ocorre em {{ entrega.data }}, às {{ entrega.hora }}, no endereço {{ entrega.local }}, com a quilometragem indicada na identificação do veículo.

São de responsabilidade de quem entrega o veículo todas as multas, infrações, tributos, taxas e encargos com fato gerador até a data e hora da entrega, inclusive os que forem notificados depois. A partir da data e hora da entrega, a responsabilidade é de quem recebe o veículo.

IPVA e licenciamento do exercício de {{ entrega.ano }}: {{ regra_ipva }}.
```

`regra_ipva` vem de uma lista configurável. Valor padrão em branco, obrigando a escolha.

### [B7] Documentação e transferência

```
Quem entrega o veículo se obriga a assinar a Autorização para Transferência de Propriedade do Veículo (ATPV-e) ou o documento equivalente exigido pelo órgão de trânsito, em até {{ prazo_assinatura }} dias úteis contados {{ marco_assinatura }}, e a entregar o manual, a chave reserva ({{ v.tem_chave_reserva|sim_nao }}) e demais documentos do veículo.

Quem recebe o veículo se obriga a providenciar a transferência de propriedade junto ao órgão de trânsito no prazo legal de 30 (trinta) dias, arcando com as respectivas despesas{% if despesas_transferencia_outra_parte %}, exceto {{ despesas_transferencia_outra_parte }}{% endif %}.

Quem entrega o veículo fica autorizado a comunicar a venda ao órgão de trânsito, nos termos do art. 134 do Código de Trânsito Brasileiro, independentemente da transferência pelo adquirente.
```

### [B8] Declarações de quem entrega o veículo

```
Quem entrega o veículo declara, sob as penas da lei, que:
a) é legítimo proprietário(a) ou está autorizado(a) pelo proprietário registral a aliená-lo{% if v.proprietario_registral_diferente %}, conforme {{ v.documento_autorizacao }}, anexo a este contrato{% endif %};
b) o veículo não possui restrição judicial, administrativa, de furto ou roubo, nem ônus além dos expressamente descritos neste contrato;
c) não tem conhecimento de adulteração de chassi, motor ou hodômetro;
d) o veículo {% if v.sinistro_declarado %}sofreu {{ v.sinistro_descricao }}{% else %}não sofreu sinistro com perda total ou dano de grande monta, até onde é de seu conhecimento{% endif %};
e) as avarias conhecidas são: {{ v.avarias_declaradas|default:"nenhuma declarada" }}.

Quem entrega o veículo responde pela evicção, nos termos da lei.
```

### [B9] Descumprimento

```
A parte que descumprir qualquer obrigação deste contrato pagará à outra multa de {{ multa_percentual }}% sobre o valor total do negócio, sem prejuízo de perdas e danos comprovados, podendo a parte prejudicada optar pela rescisão do contrato ou pela exigência de seu cumprimento.
```

### [B10] Dados pessoais

```
Os dados pessoais das partes constantes deste contrato serão tratados exclusivamente para a execução deste contrato, para o cumprimento de obrigações legais e regulatórias e para o exercício regular de direitos, nos termos da Lei nº 13.709/2018 (LGPD).
```

### [B11] Foro e assinaturas

```
Fica eleito o foro da comarca de {{ loja.cidade }}/{{ loja.uf }} para dirimir quaisquer questões decorrentes deste contrato.

E por estarem justas e contratadas, as partes assinam o presente instrumento em {{ vias }} vias de igual teor, na presença das testemunhas abaixo.

{{ loja.cidade }}/{{ loja.uf }}, {{ contrato.data|date:"j \d\e F \d\e Y" }}.

[linha de assinatura, nome e CPF/CNPJ de cada parte]

Testemunhas:
1. ______________________  Nome:                 CPF:
2. ______________________  Nome:                 CPF:
```

---

## A. Compra pela loja

Título: CONTRATO DE COMPRA E VENDA DE VEÍCULO AUTOMOTOR
Partes: **VENDEDOR(A)** = particular [B3]; **COMPRADORA** = loja [B2]

**Cláusula 1ª. Objeto.** O(A) VENDEDOR(A) vende à COMPRADORA o veículo abaixo identificado, livre e desembaraçado de quaisquer ônus, salvo os expressamente descritos neste contrato. [B4]

**Cláusula 2ª. Preço e pagamento.** O preço total é de R$ {{ negocio.valor_total }} ({{ negocio.valor_total|extenso }}), pago da seguinte forma: {{ negocio.detalhes_pagamento }}.
{% if v.alienado %}Do preço será deduzido o saldo devedor do financiamento, quitado conforme a cláusula seguinte.{% endif %}

**Cláusula 3ª. Financiamento.** {% if v.alienado %}[B5]{% else %}O(A) VENDEDOR(A) declara que o veículo não possui alienação fiduciária ou financiamento ativo.{% endif %}

**Cláusula 4ª. Declarações do(a) vendedor(a).** [B8]
Fica o(a) VENDEDOR(A) responsável por vícios ocultos preexistentes à entrega que não tenham sido declarados, nos termos da lei civil.

**Cláusula 5ª. Entrega e débitos.** [B6]

**Cláusula 6ª. Documentação.** [B7]
O(A) VENDEDOR(A) autoriza desde já a COMPRADORA a anunciar, expor e revender o veículo.

**Cláusula 7ª. Descumprimento.** [B9]
**Cláusula 8ª. Dados pessoais.** [B10]
[B11]

---

## B. Venda pela loja

Título: CONTRATO DE COMPRA E VENDA DE VEÍCULO AUTOMOTOR
Partes: **VENDEDORA** = loja [B2]; **COMPRADOR(A)** = cliente [B3]

**Cláusula 1ª. Objeto.** A VENDEDORA vende ao(à) COMPRADOR(A) o veículo abaixo identificado, de sua propriedade. [B4]

**Cláusula 2ª. Preço e pagamento.** O preço total é de R$ {{ negocio.valor_total }} ({{ negocio.valor_total|extenso }}), pago da seguinte forma:
{% if pagamento.financiado %}Entrada de R$ {{ pagamento.entrada }} e saldo de R$ {{ pagamento.valor_financiado }} financiado junto a {{ pagamento.instituicao }}. A entrega do veículo fica condicionada à liberação do crédito pela instituição financeira.{% endif %}
{% if pagamento.parcelado_loja %}{{ pagamento.qtd_parcelas }} parcelas de R$ {{ pagamento.valor_parcela }}, com vencimento todo dia {{ pagamento.dia_vencimento }}, a primeira em {{ pagamento.primeiro_vencimento }}. Em caso de atraso incidirão multa de 2% (dois por cento) e juros de mora de 1% (um por cento) ao mês sobre a parcela em atraso. {{ pagamento.garantia_parcelamento }}{% endif %}
{% if pagamento.a_vista %}À vista, por {{ pagamento.meio }}, nesta data.{% endif %}

**Cláusula 3ª. Estado do veículo.** O(A) COMPRADOR(A) declara ter vistoriado o veículo{% if vistoria.test_drive %} e realizado teste de rodagem{% endif %}, tendo sido informado(a) das seguintes avarias e características: {{ v.avarias_declaradas|default:"nenhuma" }}.

**Cláusula 4ª. Garantia.** O veículo conta com a garantia legal prevista no Código de Defesa do Consumidor{% if garantia.contratual_dias %}, acrescida de garantia contratual de {{ garantia.contratual_dias }} dias para {{ garantia.cobertura }}{% endif %}. {{ garantia.exclusoes }}

> Nota para o advogado: não inserir cláusula de "venda no estado em que se encontra" que afaste a garantia legal. Avaliar redação das exclusões (desgaste natural de pneus, freios, embreagem, bateria etc.).

**Cláusula 5ª. Entrega e débitos.** [B6]
**Cláusula 6ª. Documentação.** [B7]
**Cláusula 7ª. Descumprimento.** [B9]
**Cláusula 8ª. Dados pessoais.** [B10]
[B11]

---

## C. Troca com a loja

Título: CONTRATO DE PERMUTA DE VEÍCULOS AUTOMOTORES COM COMPLEMENTAÇÃO DE PREÇO
Partes: **LOJA** = loja [B2]; **CLIENTE** = cliente [B3]

**Cláusula 1ª. Objeto.** As partes permutam entre si os veículos abaixo:
- Veículo entregue pela LOJA ao CLIENTE: [B4 do veículo de saída]
- Veículo(s) entregue(s) pelo CLIENTE à LOJA: [B4 de cada veículo de entrada]

**Cláusula 2ª. Valores e diferença.** O veículo entregue pela LOJA é avaliado em R$ {{ valor_saida }} e o(s) veículo(s) entregue(s) pelo CLIENTE em R$ {{ valor_entrada_total }}. {% if diferenca > 0 %}O CLIENTE pagará à LOJA a diferença de R$ {{ diferenca }} ({{ diferenca|extenso }}), da seguinte forma: {{ negocio.detalhes_pagamento }}.{% elif diferenca < 0 %}A LOJA pagará ao CLIENTE a diferença de R$ {{ diferenca_abs }} ({{ diferenca_abs|extenso }}), da seguinte forma: {{ negocio.detalhes_pagamento }}.{% else %}Os valores são equivalentes, sem complementação de preço.{% endif %}

**Cláusula 3ª. Financiamento.** Para cada veículo com alienação fiduciária: [B5]

**Cláusula 4ª. Declarações.** Cada parte, em relação ao veículo que entrega: [B8]

**Cláusula 5ª. Garantia.** Em relação ao veículo entregue pela LOJA, aplica-se a cláusula de garantia do modelo B. Em relação ao(s) veículo(s) entregue(s) pelo CLIENTE, o CLIENTE responde por vícios ocultos preexistentes não declarados, nos termos da lei civil.

**Cláusula 6ª. Entrega e débitos.** [B6], aplicado a cada veículo em relação a quem o entrega.
**Cláusula 7ª. Documentação.** [B7], aplicado a cada veículo.
**Cláusula 8ª. Descumprimento.** [B9]
**Cláusula 9ª. Dados pessoais.** [B10]
[B11]

---

## D. Consignação

Título: CONTRATO DE CONSIGNAÇÃO DE VEÍCULO PARA VENDA
Partes: **CONSIGNANTE** = proprietário(a) [B3]; **CONSIGNATÁRIA** = loja [B2]

**Cláusula 1ª. Objeto.** O(A) CONSIGNANTE entrega à CONSIGNATÁRIA, em consignação, o veículo abaixo identificado, para que esta o exponha e intermedeie sua venda a terceiros, em nome do(a) CONSIGNANTE. A propriedade permanece com o(a) CONSIGNANTE até a venda. [B4]

**Cláusula 2ª. Valor e remuneração.** O(A) CONSIGNANTE receberá, no mínimo, R$ {{ consignacao.valor_liquido_minimo }} ({{ consignacao.valor_liquido_minimo|extenso }}) líquidos pela venda. A remuneração da CONSIGNATÁRIA será {% if consignacao.comissao_tipo == "percentual" %}de {{ consignacao.comissao_valor }}% sobre o preço de venda{% elif consignacao.comissao_tipo == "fixa" %}de R$ {{ consignacao.comissao_valor }}{% else %}o valor que exceder o mínimo líquido acima{% endif %}. Venda por valor inferior ao mínimo depende de autorização escrita do(a) CONSIGNANTE, inclusive por mensagem eletrônica.

**Cláusula 3ª. Repasse.** A CONSIGNATÁRIA repassará ao(à) CONSIGNANTE o valor devido em até {{ consignacao.prazo_repasse_dias }} dias úteis após o recebimento integral do preço, por {{ consignacao.meio_repasse }}.

**Cláusula 4ª. Prazo.** A consignação vigora por {{ consignacao.prazo_dias }} dias a partir de {{ consignacao.data_entrada }}, renovando-se automaticamente por iguais períodos se nenhuma das partes se manifestar. Qualquer parte pode encerrá-la a qualquer tempo, com aviso de {{ consignacao.aviso_dias }} dias{% if consignacao.reembolso_despesas %}, devendo o(a) CONSIGNANTE, se a iniciativa for sua, reembolsar as despesas comprovadas com {{ consignacao.despesas_reembolsaveis }}{% endif %}.

**Cláusula 5ª. Guarda.** Enquanto o veículo estiver em seu poder, a CONSIGNATÁRIA responde por sua guarda e conservação{% if consignacao.seguro %}, mantendo seguro {{ consignacao.seguro_descricao }}{% endif %}. Fica autorizada a realizar testes de rodagem com interessados, acompanhados por seu preposto.

**Cláusula 6ª. Débitos.** Multas, tributos e encargos do veículo até a data da venda a terceiro são de responsabilidade do(a) CONSIGNANTE, exceto infrações cometidas durante a guarda da CONSIGNATÁRIA, que serão de responsabilidade desta.

**Cláusula 7ª. Financiamento.** {% if v.alienado %}[B5]. A venda a terceiro fica condicionada à quitação ou à anuência do credor, nos termos ajustados entre as partes.{% else %}O(A) CONSIGNANTE declara que o veículo não possui financiamento ativo.{% endif %}

**Cláusula 8ª. Declarações do(a) consignante.** [B8]

**Cláusula 9ª. Documentação.** O(A) CONSIGNANTE entrega nesta data: {{ consignacao.documentos_entregues }}. Concluída a venda, o(a) CONSIGNANTE se obriga a assinar a ATPV-e ou o documento equivalente em favor do comprador em até {{ prazo_assinatura }} dias úteis.

**Cláusula 10ª. Descumprimento.** [B9], calculado sobre o valor líquido mínimo.
**Cláusula 11ª. Dados pessoais.** [B10]
[B11]

---

## E. Intermediação (venda de consignado ou negócio entre particulares)

Título: CONTRATO DE {% if tipo == "troca" %}PERMUTA{% else %}COMPRA E VENDA{% endif %} DE VEÍCULO AUTOMOTOR COM INTERVENIÊNCIA DE INTERMEDIÁRIA
Partes: **VENDEDOR(A)** ou **PERMUTANTE 1** [B3]; **COMPRADOR(A)** ou **PERMUTANTE 2** [B3]; **INTERVENIENTE INTERMEDIÁRIA** = loja [B2]

**Cláusula 1ª. Objeto.** {% if tipo == "troca" %}As partes permutam entre si os veículos abaixo, cada um identificado com quem o entrega.{% else %}O(A) VENDEDOR(A) vende ao(à) COMPRADOR(A) o veículo abaixo.{% endif %} [B4 de cada veículo]

**Cláusula 2ª. Papel da intermediária.** A INTERVENIENTE INTERMEDIÁRIA atua na aproximação das partes e na organização documental do negócio, não sendo proprietária {% if tipo == "troca" %}dos veículos{% else %}do veículo{% endif %}. A INTERVENIENTE declara ter consultado, em {{ consulta.data }}, a situação do(s) veículo(s) junto a {{ consulta.fonte }}, cujo resultado segue anexo.

> Nota para o advogado: avaliar até onde a loja pode limitar sua responsabilidade como intermediária em relação ao consumidor. Não sabemos o entendimento atual dos tribunais sobre a responsabilidade da revenda em consignação.

**Cláusula 3ª. Preço, diferença e pagamento.** {% if tipo == "troca" %}Mesma estrutura da cláusula 2ª do modelo C, entre PERMUTANTE 1 e PERMUTANTE 2.{% else %}O preço total é de R$ {{ negocio.valor_total }} ({{ negocio.valor_total|extenso }}), pago {{ pagamento.destino }} da seguinte forma: {{ negocio.detalhes_pagamento }}.{% endif %}

`pagamento.destino`: "diretamente ao(à) VENDEDOR(A)" ou "à INTERVENIENTE INTERMEDIÁRIA, que repassará ao(à) VENDEDOR(A) conforme contrato de consignação nº {{ consignacao.contrato_numero }}".

**Cláusula 4ª. Remuneração da intermediária.** A remuneração da INTERVENIENTE é de R$ {{ comissao.valor }}, paga por {{ comissao.pagador }}{% if consignacao %}, conforme contrato de consignação nº {{ consignacao.contrato_numero }}{% endif %}.

**Cláusula 5ª. Financiamento.** Para cada veículo com alienação fiduciária: [B5]

**Cláusula 6ª. Proprietário registral diferente.** {% if algum_veiculo_com_terceiro %}O veículo {{ v.placa }} está registrado em nome de {{ v.proprietario_registral }}, que {% if terceiro_assina %}assina este contrato como anuente{% else %}autorizou a alienação por meio de {{ v.documento_autorizacao }}, anexo{% endif %}.{% endif %}

> Regra do sistema: se o proprietário registral não for parte e não houver documento de autorização anexado, bloquear a geração do contrato e explicar o motivo.

**Cláusula 7ª. Declarações.** Cada parte, em relação ao veículo que entrega: [B8]

**Cláusula 8ª. Vícios.** Cada parte responde perante a outra por vícios ocultos preexistentes e não declarados do veículo que entrega, nos termos da lei civil.

**Cláusula 9ª. Entrega e débitos.** [B6]
**Cláusula 10ª. Documentação.** [B7]
**Cláusula 11ª. Descumprimento.** [B9]
**Cláusula 12ª. Dados pessoais.** [B10]
[B11], com assinatura das partes, da INTERVENIENTE e do anuente, se houver.

---

## Anexos gerados pelo sistema

1. **Termo de vistoria e entrega**: data, hora, km, nível de combustível, itens entregues (chave reserva, manual, estepe, macaco, triângulo), avarias com fotos tiradas no momento da entrega. Assinado por quem entrega e por quem recebe.
2. **Recibo de pagamento**: para cada valor recebido.
3. **Consulta de situação do veículo**: arquivo anexado manualmente pelo usuário (o MVP não integra com órgãos de trânsito).

## Configurações da loja que o advogado precisa definir

- Percentual da multa por descumprimento (`multa_percentual`)
- Regra padrão de IPVA e licenciamento
- Prazos padrão de assinatura da ATPV-e e de repasse ao consignante
- Exclusões da garantia contratual
- Número de vias
- Texto final de cada cláusula