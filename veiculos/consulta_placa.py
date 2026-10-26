"""
Consulta de placa EXTERNA (opcional, desligada por padrão).

A integração com uma API paga de consulta veicular é um "adapter": o provedor é
escolhido por variável de ambiente (CONSULTA_PLACA_PROVIDER) e, por padrão, é
"none" — nada é consultado. Assim o cadastro de carro funciona sem nenhuma API;
quem quiser liga um provedor sem mexer no resto do código.

Regra de ouro: NUNCA quebrar o cadastro. Se a API falhar, der timeout ou vier
vazia, devolvemos None e a tela segue com preenchimento manual.

Provedores recomendados (ver PROMPTS-IMPLEMENTACAO.md):
- apibrasil  — ~R$ 0,10/consulta, traz FIPE junto
- simplesapi — ~R$ 0,10/consulta, dados básicos
- credify    — enterprise (inclui proprietário); exige CNPJ e contato comercial

ATENÇÃO: os nomes dos campos de resposta de cada API mudam e devem ser conferidos
na documentação do provedor no ato da contratação. O normalizador abaixo tenta
vários nomes comuns de propósito, para ser tolerante.
"""

import json
import urllib.request

from django.conf import settings

TIMEOUT = 12


def _pegar(dados, *chaves):
    """Primeiro valor não vazio entre várias chaves possíveis."""
    for chave in chaves:
        valor = dados.get(chave)
        if valor:
            return str(valor).strip()
    return ""


def _normalizar(dados):
    """Converte a resposta do provedor no formato que o formulário entende."""
    if not isinstance(dados, dict):
        return None
    # Alguns provedores embrulham o veículo em "response"/"data"/"dados".
    for embrulho in ("response", "data", "dados", "veiculo", "vehicle"):
        interno = dados.get(embrulho)
        if isinstance(interno, dict):
            dados = {**dados, **interno}
    return {
        "marca": _pegar(dados, "marca", "MARCA", "brand", "fabricante"),
        "modelo": _pegar(dados, "modelo", "MODELO", "model"),
        "cor": _pegar(dados, "cor", "COR", "color"),
        "ano_fabricacao": _pegar(dados, "ano", "anoFabricacao", "ano_fabricacao", "year"),
        "ano_modelo": _pegar(dados, "anoModelo", "ano_modelo", "modelYear"),
        "combustivel": _pegar(dados, "combustivel", "COMBUSTIVEL", "fuel"),
        "chassi": _pegar(dados, "chassi", "CHASSI", "chassis", "chassa"),
    }


def _get_json(url, headers):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:  # noqa: S310 (URL de provedor configurado)
        return json.loads(resp.read().decode("utf-8"))


def _post_json(url, corpo, headers):
    dados = json.dumps(corpo).encode("utf-8")
    cabecalhos = {"Content-Type": "application/json", **headers}
    req = urllib.request.Request(url, data=dados, headers=cabecalhos, method="POST")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:  # noqa: S310 (URL de provedor configurado)
        return json.loads(resp.read().decode("utf-8"))


# --- Provedores ------------------------------------------------------------
# Cada função recebe a placa (já normalizada) e devolve o JSON cru do provedor.
# A URL base pode ser sobrescrita por CONSULTA_PLACA_URL (útil se a API mudar).


def _apibrasil(placa, token, url):
    url = url or "https://gateway.apibrasil.io/api/v2/vehicles/dados"
    return _post_json(url, {"placa": placa}, {"Authorization": f"Bearer {token}"})


def _simplesapi(placa, token, url):
    url = url or "https://api.simplesapi.com.br/v1/vehicle/plate"
    return _post_json(url, {"placa": placa}, {"Authorization": f"Bearer {token}"})


def _credify(placa, token, url):
    url = url or "https://api.credify.com.br/v1/veiculosagregados"
    return _post_json(url, {"placa": placa}, {"Authorization": f"Bearer {token}"})


_PROVEDORES = {
    "apibrasil": _apibrasil,
    "simplesapi": _simplesapi,
    "credify": _credify,
}


def provedor_ativo():
    """Nome do provedor configurado, ou 'none' se a consulta externa está desligada."""
    return (getattr(settings, "CONSULTA_PLACA_PROVIDER", "none") or "none").lower()


def consultar_placa_externa(placa):
    """
    Consulta a placa no provedor configurado. Devolve um dict normalizado
    (marca, modelo, cor, ano_fabricacao, ano_modelo, combustivel, chassi) ou None.
    Nunca levanta exceção: qualquer falha vira None.
    """
    provedor = provedor_ativo()
    func = _PROVEDORES.get(provedor)
    if func is None:
        return None
    token = getattr(settings, "CONSULTA_PLACA_TOKEN", "") or ""
    url = getattr(settings, "CONSULTA_PLACA_URL", "") or ""
    try:
        bruto = func(placa, token, url)
        return _normalizar(bruto)
    except Exception:
        return None
