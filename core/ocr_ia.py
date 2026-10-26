"""
Ler documento por FOTO com uma IA de visão (Claude), devolvendo os campos prontos.

Pensado pra quem tem dificuldade de digitar (o dono da loja, 60 anos): ele tira
uma foto do documento e o sistema preenche; depois ele CONFERE e corrige.

É um adapter plugável e DESLIGADO por padrão (OCR_IA_PROVIDER=none). Para ligar,
cadastre OCR_IA_PROVIDER=claude e a chave ANTHROPIC_API_KEY (ver .env.example).

Regra de ouro: NUNCA quebrar a tela. Qualquer falha (sem chave, API fora, foto
ruim) devolve None e o usuário segue preenchendo à mão.

LGPD: a foto vai pra API da Anthropic só pra leitura (a API não treina com os
dados). O arquivo em si continua indo pro bucket privado (R2) pelo fluxo normal.
"""

import base64
import io
import json

from django.conf import settings

# Campos extraídos do DOCUMENTO DO CARRO (CRLV/CRV).
CARRO_SCHEMA = {
    "type": "object",
    "properties": {
        "placa": {"type": "string"},
        "renavam": {"type": "string"},
        "chassi": {"type": "string"},
        "marca": {"type": "string"},
        "modelo": {"type": "string"},
        "ano_fabricacao": {"type": "string"},
        "ano_modelo": {"type": "string"},
        "cor": {"type": "string"},
    },
    "required": [
        "placa",
        "renavam",
        "chassi",
        "marca",
        "modelo",
        "ano_fabricacao",
        "ano_modelo",
        "cor",
    ],
    "additionalProperties": False,
}

# Campos extraídos do DOCUMENTO DA PESSOA (CNH/RG).
PESSOA_SCHEMA = {
    "type": "object",
    "properties": {
        "nome": {"type": "string"},
        "cpf_cnpj": {"type": "string"},
        "rg": {"type": "string"},
    },
    "required": ["nome", "cpf_cnpj", "rg"],
    "additionalProperties": False,
}

_PROMPT_COMUM = (
    "Leia a foto do documento brasileiro e extraia os campos pedidos. "
    "Se algum campo não aparecer ou você não tiver certeza, devolva string vazia — "
    "NUNCA invente nem chute. Devolva só os dados pedidos."
)

_CONFIG = {
    "carro": (
        CARRO_SCHEMA,
        _PROMPT_COMUM
        + " É um documento de veículo (CRLV/CRV). Placa sem hífen e em maiúsculas. "
        "Chassi em maiúsculas (17 caracteres). Renavam só números.",
    ),
    "pessoa": (
        PESSOA_SCHEMA,
        _PROMPT_COMUM
        + " É um documento pessoal (CNH ou RG). CPF/CNPJ só números. "
        "Nome completo como está no documento.",
    ),
}

LADO_MAXIMO = 1600


def provedor_ativo():
    return (getattr(settings, "OCR_IA_PROVIDER", "none") or "none").lower()


def _preparar_imagem(arquivo):
    """Redimensiona a foto (até 1600px), converte pra JPEG e devolve (base64, media_type)."""
    from PIL import Image, ImageOps

    arquivo.seek(0)
    imagem = Image.open(arquivo)
    imagem = ImageOps.exif_transpose(imagem)
    if imagem.mode != "RGB":
        imagem = imagem.convert("RGB")
    imagem.thumbnail((LADO_MAXIMO, LADO_MAXIMO))
    buffer = io.BytesIO()
    imagem.save(buffer, format="JPEG", quality=85)
    return base64.standard_b64encode(buffer.getvalue()).decode(), "image/jpeg"


def _ler_com_claude(b64, media_type, schema, prompt):
    import anthropic

    chave = getattr(settings, "ANTHROPIC_API_KEY", "") or None
    modelo = getattr(settings, "OCR_IA_MODELO", "claude-opus-4-8") or "claude-opus-4-8"
    cliente = anthropic.Anthropic(api_key=chave) if chave else anthropic.Anthropic()
    resposta = cliente.messages.create(
        model=modelo,
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": media_type, "data": b64},
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        output_config={"format": {"type": "json_schema", "schema": schema}},
    )
    texto = next((b.text for b in resposta.content if b.type == "text"), "")
    return json.loads(texto)


def ler_documento(arquivo, tipo):
    """
    Lê a foto do documento e devolve um dict com os campos (ou None se desligado/falhou).
    `tipo`: "carro" (CRLV) ou "pessoa" (CNH/RG).
    """
    if provedor_ativo() != "claude" or tipo not in _CONFIG:
        return None
    schema, prompt = _CONFIG[tipo]
    try:
        b64, media_type = _preparar_imagem(arquivo)
        dados = _ler_com_claude(b64, media_type, schema, prompt)
        if not isinstance(dados, dict):
            return None
        # Só devolve se veio pelo menos um campo preenchido.
        return dados if any((v or "").strip() for v in dados.values()) else None
    except Exception:
        return None
