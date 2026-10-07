"""Filtros usados nos contratos: valor por extenso, sim/não e formatação do PDF."""

import re
from decimal import Decimal, InvalidOperation

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe
from num2words import num2words

register = template.Library()


@register.filter
def formatar_contrato(corpo):
    """
    Transforma o texto puro do contrato em HTML com cara de documento:
    título, cláusulas com cabeçalho em negrito, blocos de partes e assinaturas
    com o alinhamento preservado. Mantém o texto editável como está no banco.
    """
    if not corpo:
        return ""

    def realcar(linha):
        # Opera em texto JÁ escapado. Põe em negrito o que "salta aos olhos".
        # Valores em reais.
        linha = re.sub(r"(R\$\s?[\d.]+,\d{2})", r"<strong>\1</strong>", linha)
        # Marcadores de parágrafo.
        linha = re.sub(r"^(§\s*\d+º|Parágrafo único\.)", r"<strong>\1</strong>", linha)
        # Rótulo no começo da linha (dados do carro, pagamento etc.): "Placa:", "Marca/Modelo:".
        linha = re.sub(
            r"^([A-Za-zÀ-Úà-ú][\w/ ().-]{1,34}:)(\s)", r"<strong>\1</strong>\2", linha
        )
        return linha

    def por_linhas(texto):
        return "<br>".join(realcar(escape(l)) for l in texto.split("\n"))

    blocos = re.split(r"\n\s*\n", corpo.strip())
    partes = []
    for i, bloco in enumerate(blocos):
        bloco = bloco.strip("\n")
        if not bloco.strip():
            continue

        # Assinaturas e testemunhas: preservar o alinhamento.
        if "___" in bloco:
            partes.append('<pre class="assinaturas">%s</pre>' % escape(bloco))
            continue

        # Primeiro bloco: título do contrato + número.
        if i == 0:
            linhas = bloco.split("\n")
            html = '<h1 class="titulo">%s</h1>' % escape(linhas[0])
            resto = [l for l in linhas[1:] if l.strip()]
            if resto:
                html += '<p class="subtitulo">%s</p>' % "<br>".join(escape(l) for l in resto)
            partes.append(html)
            continue

        # Cláusulas: cabeçalho ("CLÁUSULA 1ª — OBJETO.") em negrito.
        m = re.match(r"(CL[ÁA]USULA[^.]*\.)(.*)", bloco, re.S)
        if m:
            partes.append(
                '<p class="clausula"><strong>%s</strong>%s</p>'
                % (escape(m.group(1)), por_linhas(m.group(2)))
            )
            continue

        # Blocos de parte (ex.: "VENDEDOR(A): ..."): rótulo em negrito.
        m = re.match(r"([A-ZÀ-Ú()/\s]{2,40}:)(.*)", bloco, re.S)
        if m:
            partes.append(
                '<p class="parte"><strong>%s</strong>%s</p>'
                % (escape(m.group(1)), por_linhas(m.group(2)))
            )
            continue

        partes.append("<p>%s</p>" % por_linhas(bloco))

    return mark_safe("\n".join(partes))


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


@register.filter
def numero_extenso(valor):
    """Número inteiro por extenso (ex.: 10 -> 'dez'). Usado na multa do contrato."""
    try:
        numero = int(Decimal(str(valor)))
    except (InvalidOperation, TypeError, ValueError):
        return ""
    return num2words(numero, lang="pt_BR")


@register.filter
def cep(valor):
    """Formata um CEP de 8 dígitos como 00000-000."""
    digitos = "".join(ch for ch in str(valor or "") if ch.isdigit())
    if len(digitos) == 8:
        return f"{digitos[:5]}-{digitos[5:]}"
    return valor or ""
