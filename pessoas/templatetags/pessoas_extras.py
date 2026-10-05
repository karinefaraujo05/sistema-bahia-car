"""Filtros de exibição de documento e telefone no padrão brasileiro."""

from django import template

from pessoas.validators import formatar_cpf_cnpj, formatar_telefone

register = template.Library()


@register.filter(name="cpf_cnpj")
def cpf_cnpj(valor):
    return formatar_cpf_cnpj(valor) or "—"


@register.filter(name="telefone")
def telefone(valor):
    return formatar_telefone(valor) or "—"
