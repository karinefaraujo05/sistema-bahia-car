# Tarefas que dependem de você (Karine)

Coisas que eu não consigo fazer daqui (precisam do seu login/acesso).
Vou acumulando aqui conforme avanço nos blocos.

---

## Bloco 1 — Hospedagem

### 1.3 — Confirmar que o plano virou Starter (cartão JÁ cadastrado ✅)
Você já pagou/cadastrou o cartão no Render — ótimo, isso destrava o Starter.
Falta só **confirmar que o plano trocou de fato**:

1. Entre em https://dashboard.render.com → serviço **bahia-car**.
2. No topo/Settings, veja o **plano**: tem que estar **Starter** (não "Free").
   - Se ainda estiver **Free**: vá no **Blueprint** e clique **Manual Sync**
     (ou em Settings → Plan, troque para **Starter**). Eu já deixei `plan: starter`
     no `render.yaml`, então o sync aplica sozinho.
3. Confira que o último deploy está **Live** (aba *Events/Logs*).
4. Me avise ("está Starter") que eu rodo o **teste de cold start** (deixo ~20 min
   parado e cronometro 3×) pra comprovar que o site não dorme mais.

> Domínio: a URL `https://bahia-car.onrender.com` continua a mesma após o upgrade
> (não muda nada no `manter-acordado.yml` nem nos acessos do seu pai). Só mexeremos
> em domínio próprio se você quiser um `bahiacar.com.br` depois.

---

## Bloco 2 — Painel

### 2.2 — ✅ RESOLVIDO: "valor em estoque" usa valor_anunciado
Você decidiu: o card mostra **quanto a loja receberia vendendo tudo** → passei a usar
**`valor_anunciado`** (preço de venda), em vez de valor_compra. Feito e publicado.

### ✅ Verificar o deploy que subiu (Bloco 2 + 3.1 + 3.2)
Empurrei tudo pro ar (commits 3644990..e44d971). O Render reconstrói e aplica a
migração nova (campo do contrato) no boot. **Confira no celular, logado:**
- Painel: cards novos (valor em estoque, lucro do mês, carros parados), números grandes.
- Busca: digite um nome/placa/modelo e veja a seção "Contratos e negócios" com botão PDF.
- Um contrato: a tela de edição agora tem o aviso sobre o texto × PDF.
Se algo parecer estranho, me diz que eu ajusto/reverto.

### 4.3 — Formas de pagamento mudaram (conferir negócios antigos)
As opções agora são **Dinheiro, Pix, Cartão, Financiamento, Troca + dinheiro**.
As antigas foram remapeadas automaticamente nos negócios já existentes:
- "À vista" → **Dinheiro**
- "Parcelado na loja" → **Financiamento**
- "Misto" → **Troca + dinheiro**
- "Financiado" → **Financiamento** (igual)

Esse remapeamento é um chute razoável. **Dê uma olhada em 2–3 contratos antigos**
pra ver se a forma de pagamento ficou coerente. Se algum ficou errado, me diga que
eu corrijo (dá pra reabrir o negócio ou ajustar direto).

### 2.4 — ✅ RESOLVIDO: painel e agenda unificados em 90 dias
Você decidiu: os dois a **90 dias**. O painel agora usa a mesma constante da agenda
(`DIAS_CARRO_PARADO = 90`), então nunca mais vão divergir. Feito e publicado.
