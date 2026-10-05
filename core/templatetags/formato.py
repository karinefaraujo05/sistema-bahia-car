"""Filtros de formatação no padrão brasileiro."""

from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def reais(valor):
    """Formata um valor como moeda brasileira: R$ 32.000,00. Vazio vira travessão."""
    if valor is None or valor == "":
        return "—"
    try:
        numero = Decimal(valor)
    except (InvalidOperation, TypeError, ValueError):
        return valor
    inteiro_decimal = f"{numero:,.2f}"  # ex.: 32,000.00
    # Troca separadores para o padrão brasileiro (ponto para milhar, vírgula para decimal).
    brasileiro = inteiro_decimal.replace(",", "@").replace(".", ",").replace("@", ".")
    return f"R$ {brasileiro}"
