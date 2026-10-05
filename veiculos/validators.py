"""Validação e normalização de placa, chassi e renavam."""

import re

from django.core.exceptions import ValidationError

# Placa formato antigo: ABC1234. Mercosul: ABC1D23.
_PLACA_ANTIGA = re.compile(r"^[A-Z]{3}[0-9]{4}$")
_PLACA_MERCOSUL = re.compile(r"^[A-Z]{3}[0-9][A-Z][0-9]{2}$")

# Chassi: 17 caracteres, sem as letras I, O e Q.
_CHASSI = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$")

_RENAVAM = re.compile(r"^[0-9]{11}$")


def normalizar_placa(valor):
    """Deixa a placa em maiúsculas e sem hífen, espaços ou pontuação."""
    if not valor:
        return valor
    return re.sub(r"[^A-Za-z0-9]", "", valor).upper()


def validar_placa(valor):
    placa = normalizar_placa(valor)
    if not (_PLACA_ANTIGA.match(placa) or _PLACA_MERCOSUL.match(placa)):
        raise ValidationError(
            "Placa inválida. Use o formato antigo (ABC1234) ou Mercosul (ABC1D23).",
            code="placa_invalida",
        )


def validar_chassi(valor):
    if not valor:
        return
    chassi = valor.strip().upper()
    if not _CHASSI.match(chassi):
        raise ValidationError(
            "Chassi inválido. Deve ter 17 caracteres e não pode conter as letras I, O ou Q.",
            code="chassi_invalido",
        )


def validar_renavam(valor):
    if not valor:
        return
    if not _RENAVAM.match(valor.strip()):
        raise ValidationError(
            "Renavam inválido. Deve ter 11 dígitos.",
            code="renavam_invalido",
        )


def placa_formatada(placa):
    """Devolve a placa pronta para exibição (ABC-1234 no formato antigo)."""
    placa = normalizar_placa(placa) or ""
    if _PLACA_ANTIGA.match(placa):
        return f"{placa[:3]}-{placa[3:]}"
    return placa
