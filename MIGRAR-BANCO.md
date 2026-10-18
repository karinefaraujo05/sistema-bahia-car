# Mover o banco pra perto do site (acabar com a lentidão das páginas)

**Por quê:** hoje o site (Render, EUA) e o banco (Neon, São Paulo) estão longe um do
outro, e cada página faz várias viagens entre eles → lento em toda troca de página.
A cura é pôr os dois no **mesmo lugar**. Aqui a gente move o **banco** pra junto do site.

**Regras de ouro:** backup antes, fazer com a **loja fechada**, e **guardar o banco
velho alguns dias** antes de apagar.

---

## Passo 0 — ✅ região do Render confirmada: OREGON
O site está em **Oregon** (AWS us-west-2). Então o banco novo vai na mesma: **US West (Oregon)**.

## Passo 1 — criar o banco novo no Neon, em US West (Oregon)
Em **console.neon.tech**: crie um **projeto novo** e, na criação, escolha a região
**AWS → US West (Oregon)** / `aws-us-west-2` (a MESMA do Render; não dá pra mudar a
região depois — por isso é projeto novo). Copie a **connection string** dele
(começa com `postgres://...`).

## Passo 2 — cadastrar o endereço do banco novo como "secret" no GitHub
No GitHub do projeto: **Settings → Secrets and variables → Actions → New repository
secret**:
- **Name:** `NOVO_DATABASE_URL`
- **Secret:** a connection string do Passo 1

## Passo 3 — rodar o botão de migração (LOJA FECHADA)
Em **Actions → "Migrar banco (uma vez)" → Run workflow**, digite **MIGRAR** e confirme.
Ele faz o backup/cópia e, no fim, mostra as **contagens** (veículos, pessoas, negócios,
contratos). **Confira se batem** com o que o sistema mostra.

## Passo 4 — apontar o site pro banco novo
No **Render → `bahia-car` → Environment**: troque o valor de **`DATABASE_URL`** pela
connection string do banco novo. Salve (o Render republica sozinho).

## Passo 5 — manter o backup funcionando
No **GitHub → Secrets → Actions**: troque também o secret **`DATABASE_URL`** pelo
endereço do banco novo (pra os backups diários passarem a copiar o banco novo).

## Passo 6 — me avisa
Eu meço a velocidade de novo (deve cair de ~1,5s pra ~0,3s por página) e confiro os dados.

## Passo 7 — depois de 2–3 dias OK
Apague o projeto **antigo** no Neon (São Paulo). Pronto.

---

### Observações
- A cópia é rápida; a "loja fechada" é só pra nenhum registro novo escapar entre a
  cópia e a troca do endereço.
- Se algo der errado, **nada é perdido**: o banco velho continua intacto até o Passo 7,
  e é só voltar o `DATABASE_URL` pra ele.
- Seu `.env` local também aponta pro banco de produção — quando a poeira baixar, vale
  trocar pra apontar pro banco local (docker), por segurança. Me lembra depois.
