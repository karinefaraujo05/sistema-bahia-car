"""Filtros usados nos contratos: valor por extenso e sim/não."""

from decimal import Decimal, InvalidOperation

from django import template
from num2words import num2words

register = template.Library()


@register.filter
def extenso(valor):
    """Escreve um valor em reais por extenso (ex.: 'trinta e dois mil reais')."""
    if valor is None or valor == "":
        return ""
    try:
        numero = Decimal(valor)
    except (InvalidOperation, TypeError, ValueError):
        return ""
    # Arredonda para centavos antes de converter, para não distorcer o extenso.
    centavos = numero.quantize(Decimal("0.01"))
    return num2words(float(centavos), lang="pt_BR", to="currency")


@register.filter
def sim_nao(valor):
    if valor is None:
        return "—"
    return "Sim" if valor else "Não"
