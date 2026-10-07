"""
Consulta à Tabela FIPE (preço de referência) — grátis, sem chave.
Fonte: parallelum.com.br/fipe. Guarda em cache (a FIPE muda ~1x por mês),
pra responder rápido e bater pouco na API.
"""

import json
import re
import urllib.request

from django.core.cache import cache

BASE = "https://parallelum.com.br/fipe/api/v1"
TIPOS = {"carros", "motos", "caminhoes"}
_SEGURO = re.compile(r"^[\w-]+$")


def _ok(valor):
    return bool(valor) and bool(_SEGURO.match(str(valor)))


def _buscar(caminho, ttl):
    url = f"{BASE}/{caminho}"
    chave = "fipe:" + url
    dados = cache.get(chave)
    if dados is None:
        req = urllib.request.Request(url, headers={"User-Agent": "BahiaCar"})
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310 (URL fixa, só FIPE)
            dados = json.loads(resp.read().decode("utf-8"))
        cache.set(chave, dados, ttl)
    return dados


def marcas(tipo):
    return _buscar(f"{tipo}/marcas", 86400)


def modelos(tipo, marca):
    if not _ok(marca):
        return []
    dados = _buscar(f"{tipo}/marcas/{marca}/modelos", 86400)
    return dados.get("modelos", [])


def anos(tipo, marca, modelo):
    if not (_ok(marca) and _ok(modelo)):
        return []
    return _buscar(f"{tipo}/marcas/{marca}/modelos/{modelo}/anos", 86400)


def preco(tipo, marca, modelo, ano):
    if not (_ok(marca) and _ok(modelo) and _ok(ano)):
        return {}
    return _buscar(f"{tipo}/marcas/{marca}/modelos/{modelo}/anos/{ano}", 43200)
