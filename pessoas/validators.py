"""Validação de CPF/CNPJ (dígitos verificadores) e normalização de documentos e telefone."""

import re

from django.core.exceptions import ValidationError


def so_digitos(valor):
    """Devolve apenas os dígitos de um texto."""
    if not valor:
        return ""
    return re.sub(r"\D", "", valor)


def _digito(digitos, pesos):
    soma = sum(int(d) * p for d, p in zip(digitos, pesos, strict=True))
    resto = soma % 11
    return "0" if resto < 2 else str(11 - resto)


def cpf_valido(valor):
    cpf = so_digitos(valor)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    d1 = _digito(cpf[:9], range(10, 1, -1))
    d2 = _digito(cpf[:10], range(11, 1, -1))
    return cpf[9:] == d1 + d2


def cnpj_valido(valor):
    cnpj = so_digitos(valor)
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    d1 = _digito(cnpj[:12], pesos1)
    d2 = _digito(cnpj[:13], pesos2)
    return cnpj[12:] == d1 + d2


def validar_cpf_cnpj(valor):
    """Valida como CPF (11 dígitos) ou CNPJ (14 dígitos), conforme o tamanho."""
    documento = so_digitos(valor)
    if not documento:
        return
    if len(documento) == 11:
        if not cpf_valido(documento):
            raise ValidationError("CPF inválido. Confira os números.", code="cpf_invalido")
    elif len(documento) == 14:
        if not cnpj_valido(documento):
            raise ValidationError("CNPJ inválido. Confira os números.", code="cnpj_invalido")
    else:
        raise ValidationError(
            "Documento inválido. Informe um CPF (11 dígitos) ou CNPJ (14 dígitos).",
            code="documento_invalido",
        )


def formatar_cpf_cnpj(valor):
    documento = so_digitos(valor)
    if len(documento) == 11:
        return f"{documento[:3]}.{documento[3:6]}.{documento[6:9]}-{documento[9:]}"
    if len(documento) == 14:
        return (
            f"{documento[:2]}.{documento[2:5]}.{documento[5:8]}/{documento[8:12]}-{documento[12:]}"
        )
    return valor or ""


def formatar_telefone(valor):
    numero = so_digitos(valor)
    if len(numero) == 11:
        return f"({numero[:2]}) {numero[2:7]}-{numero[7:]}"
    if len(numero) == 10:
        return f"({numero[:2]}) {numero[2:6]}-{numero[6:]}"
    return valor or ""
