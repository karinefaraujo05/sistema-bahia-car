# Roteiro de teste no celular — Ondas 1 a 4

Checklist pra validar as mudanças **pelo celular** (é como o dono usa). Faça logado,
com calma, marcando cada item. Onde falar "deve", é o comportamento esperado.

> Dica: muita coisa é JavaScript no navegador do celular. Se algo não reagir, recarregue a página.

---

## Onda 1 — Cadastrar carro (Estoque → Cadastrar carro)

- [ ] **Placa primeiro.** Digite uma placa **que já existe** no estoque e toque em
      **"Buscar dados da placa"** → deve avisar *"Esse carro já está no sistema…"* com link **Abrir**.
- [ ] Digite uma **placa nova** e toque em "Buscar dados da placa" → deve dizer que a placa
      está livre (ou, se a consulta de placa paga estiver ligada, preencher os campos).
- [ ] **FIPE.** Escolha tipo → marca → modelo → ano. A cada passo, os campos lá embaixo
      (marca, modelo, ano, combustível, valor anunciado) devem **preencher sozinhos**.
- [ ] Repare que **marca e modelo aparecem travados** (fundo cinza). Toque em
      **"Não achei na FIPE — digitar na mão"** → eles **destravam** pra digitar.
- [ ] **Salvar só com o essencial:** preencha placa, marca, modelo, ano, cor, km e valor,
      **sem abrir** "Documentação e condição", e salve → o carro deve **entrar no estoque**.
- [ ] Abra a ficha desse carro (sem chassi/renavam) → deve aparecer o aviso
      **"Faltam dados pro contrato… Completar agora"**.
- [ ] Toque em **"Documentação e condição"** pra abrir. Marque **"tem financiamento"** →
      devem aparecer os campos de financiamento. Marque **"teve sinistro"** → deve aparecer
      a descrição do sinistro.

## Onda 2 — Negócios e pessoas

- [ ] **Cadastro rápido de pessoa** (Pessoas → cadastro rápido): tente salvar **sem CPF** →
      deve **barrar** pedindo o CPF.
- [ ] No cadastro rápido, digite um **CPF que já existe** → ao salvar deve **abrir a pessoa
      existente** (não cria duplicada) com o aviso de que já estava cadastrada.
- [ ] **Cadastro completo** de pessoa: salve **sem CEP** → deve **deixar salvar** (CEP agora é
      opcional). Digite um **CPF já cadastrado** e saia do campo → aviso *"Já existe … Abrir cadastro"*.
- [ ] **CEP:** digite um CEP **inexistente** → deve avisar *"CEP não encontrado, preencha o
      endereço à mão"* (antes ficava mudo).
- [ ] **Troca** (Novo negócio → Troca): no passo **"Quem"**, se faltarem dados do cliente pro
      contrato, deve aparecer **"Completar agora"** (abre, você completa e volta pro negócio).
- [ ] No passo do **carro do cliente**, deve ser o **mesmo formulário com FIPE** (não o paredão
      de campos antigo).
- [ ] No passo **"Valores"** da troca, os valores dos dois carros já devem vir **preenchidos**
      (dá pra conferir e ajustar) — é uma confirmação, não digitação do zero.
- [ ] **Compra** (Novo negócio → Compra): o passo do carro também deve ter **FIPE e seções**.

## Onda 3 — Contrato e WhatsApp

- [ ] Gere um contrato (precisa de loja configurada + chassi/renavam do carro + dados do cliente).
- [ ] **No celular**, toque em **WhatsApp** no contrato → deve abrir o compartilhamento do
      celular **já com o PDF anexado** (você escolhe o contato). *(Este é o item que mais
      precisa de teste real no aparelho.)*
- [ ] **No computador**, o botão WhatsApp deve abrir o **WhatsApp Web com a mensagem**
      (sem anexo) — é o comportamento de reserva, e está certo assim.
- [ ] Abra **"Abrir / editar"** o contrato → toque em **"Texto completo do contrato"** →
      o campo deve estar em **fonte normal** (não mais tipo máquina de escrever) e **crescer**
      conforme você digita.

## Onda 4 — Velocidade e robustez (menos visual)

- [ ] O **painel inicial** e o **estoque** devem abrir **mais rápidos** que antes.
- [ ] Ao adicionar foto no carro, tente enviar um arquivo **que não é imagem** (ex.: um PDF
      pela galeria, se der) → deve dar um **aviso amigável** e **não** quebrar a tela.
- [ ] O card **"carros parados"** no painel deve continuar mostrando os carros parados há mais
      de 90 dias (sem mudança visual — só ficou mais rápido por baixo).

---

## Se algo falhar

Anote **em qual item** e **o que apareceu** (print ajuda). Manda pra Karine que a gente corrige.
Nada do que está aqui apaga dados — pode testar à vontade.
