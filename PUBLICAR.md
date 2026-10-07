# Como publicar o Bahia Car na internet

Guia passo a passo pra colocar o sistema no ar e passar pro seu pai.
Não precisa programar nada — é só criar umas contas e preencher campos.

Como vai ficar:
- **Render** hospeda o site → vira um endereço tipo `https://bahia-car.onrender.com`
- **Neon** guarda os dados (o banco que já usamos)
- **Cloudflare R2** guarda as fotos dos carros e documentos (grátis até 10 GB)

> ⏱️ Dá pra fazer tudo em uns 30–40 minutos. Faça com calma, um passo de cada vez.

---

## Antes de começar

Você vai precisar de 2 contas novas (as duas **grátis**):
- **Cloudflare** → https://dash.cloudflare.com/sign-up
- **Render** → https://render.com (dá pra entrar com o GitHub)

E de uma coisa que você já tem:
- O **DATABASE_URL** do Neon. Está no arquivo `.env` do projeto, na linha que começa com `DATABASE_URL=postgres://...`. Deixe essa linha à mão (vamos copiar depois).

> ⚠️ Nunca cole o `DATABASE_URL`, senhas ou chaves em lugar público (mensagem, print, etc.). Só nos campos do Render.

---

## Passo 1 — Guardar as fotos (Cloudflare R2)

1. Entre no Cloudflare → menu lateral **R2**.
2. Clique em **Create bucket**. Dê um nome, ex.: `bahia-car-arquivos`. Deixe o resto no padrão → **Create**.
3. Ainda em R2, abra **Manage R2 API Tokens** (ou "API Tokens") → **Create API Token**.
   - Permissão: **Object Read & Write**.
   - Clique em criar e **copie estes 3 valores** (eles só aparecem uma vez):
     - **Access Key ID**
     - **Secret Access Key**
     - **Endpoint** — é a "S3 API URL", algo como `https://XXXXXXXX.r2.cloudflarestorage.com`
4. Guarde esses 3 valores + o nome do bucket (`bahia-car-arquivos`). Vamos usar no Passo 3.

---

## Passo 2 — Criar o serviço no Render

1. Entre no Render e clique em **New +** → **Blueprint**.
2. Conecte sua conta do **GitHub** e escolha o repositório **`sistema-bahia-car`**.
3. O Render vai ler o arquivo `render.yaml` sozinho e mostrar o serviço **bahia-car**.
4. Ele vai pedir pra preencher as variáveis. Preencha assim:

| Variável | O que colocar |
|---|---|
| `DATABASE_URL` | O endereço do Neon (do seu `.env`) |
| `AWS_STORAGE_BUCKET_NAME` | `bahia-car-arquivos` |
| `AWS_ACCESS_KEY_ID` | Access Key ID do R2 (Passo 1) |
| `AWS_SECRET_ACCESS_KEY` | Secret Access Key do R2 (Passo 1) |
| `AWS_S3_ENDPOINT_URL` | O Endpoint do R2 (Passo 1) |
| `AWS_S3_REGION_NAME` | `auto` |
| `ALLOWED_HOSTS` | *(deixe em branco por enquanto)* |
| `CSRF_TRUSTED_ORIGINS` | *(deixe em branco por enquanto)* |
| `ADMIN_URL` | `painel-interno/` |
| `RESP_USUARIO` | `nelson` |
| `RESP_SENHA` | *(a senha do seu pai)* |
| `RESP_NOME` | `Nelson` |
| `RESP_EMPRESA` | `Bahia Car` |

5. Clique em **Apply** / **Create**. O Render vai montar o site (demora alguns minutos — é normal).

> No primeiro deploy o sistema já cria sozinho a loja **Bahia Car** e o login do **nelson** com a senha que você pôs em `RESP_SENHA`.

---

## Passo 3 — Ajustar o endereço (depois que subir)

1. Quando terminar, o Render mostra a URL do site, ex.: `https://bahia-car.onrender.com`.
2. Vá em **Environment** (variáveis) e preencha:
   - `CSRF_TRUSTED_ORIGINS` = `https://bahia-car.onrender.com` (troque pelo seu endereço real)
3. Salve. O Render reinicia sozinho (1–2 min).

> O `ALLOWED_HOSTS` pode continuar em branco — o Render já libera o próprio endereço automaticamente.

---

## Passo 4 — Entrar e configurar

1. Abra a URL do site.
2. Entre com **nelson** e a senha que você definiu.
3. No menu do nome (canto de cima) → **Configuração** → preencha os dados reais da loja (nome, CNPJ, endereço). Isso é o que sai nos contratos.
4. Pronto! É só começar a cadastrar os carros. 🎉

---

## Coisas boas de saber

- **Plano grátis:** o site "dorme" depois de 15 min sem uso. Na primeira visita do dia ele demora uns **40 segundos** pra acordar — depois fica rápido. Se quiser tirar essa demora, dá pra mudar pro plano **Starter (US$7/mês)** no Render, em **Settings → Instance Type**.
- **Seus dados não somem:** ficam no Neon (dados) e no R2 (fotos). Atualizar o site não apaga nada.
- **Trocar a senha do seu pai depois:** no Render → **Environment**, mude `RESP_SENHA` para a nova e adicione `RESP_RESET_SENHA` = `1`. Salve (ele reinicia e troca a senha). Depois **apague** o `RESP_RESET_SENHA`.
- **Atualizar o sistema:** toda vez que você subir algo novo pro GitHub (branch `main`), o Render publica sozinho.
- **Domínio próprio (ex.: `bahiacar.com.br`):** depois dá pra ligar no Render em **Settings → Custom Domains**.
