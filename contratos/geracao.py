"""
Geração de contratos.

O texto é renderizado de um template por modelo (A–E) e guardado como corpo editável
de um `Contrato`. A partir dele o usuário baixa em PDF (WeasyPrint) ou Word (python-docx).
Antes de gerar, conferimos os dados obrigatórios e, se faltar algo, dizemos exatamente o
que falta, com link para preencher.
"""

import io

from django.db.models import Max
from django.template.loader import render_to_string
from django.urls import reverse

from negocios.models import Modalidade, PapelParte, TipoNegocio
from negocios.services import diferenca_troca
from pessoas.models import TipoPessoa

from .models import ConfiguracaoLoja, Contrato, Documento, ModeloContrato, TipoDocumento


class ContratoError(Exception):
    def __init__(self, mensagem, faltando=None):
        super().__init__(mensagem)
        self.faltando = faltando or []


TITULOS = {
    ModeloContrato.A: "CONTRATO DE COMPRA E VENDA DE VEÍCULO AUTOMOTOR",
    ModeloContrato.B: "CONTRATO DE COMPRA E VENDA DE VEÍCULO AUTOMOTOR",
    ModeloContrato.C: "CONTRATO DE PERMUTA DE VEÍCULOS COM COMPLEMENTAÇÃO DE PREÇO",
    ModeloContrato.D: "CONTRATO DE CONSIGNAÇÃO DE VEÍCULO PARA VENDA",
    ModeloContrato.E: "CONTRATO DE COMPRA E VENDA COM INTERVENIÊNCIA DE INTERMEDIÁRIA",
}


def escolher_modelo(negocio):
    if negocio.modalidade == Modalidade.INTERMEDIACAO:
        return ModeloContrato.E
    return {
        TipoNegocio.COMPRA: ModeloContrato.A,
        TipoNegocio.VENDA: ModeloContrato.B,
        TipoNegocio.TROCA: ModeloContrato.C,
    }[negocio.tipo]


def _faltando_pessoa(pessoa):
    itens = []
    obrigatorios = {
        "cpf_cnpj": "CPF/CNPJ",
        "endereco": "endereço",
        "cidade": "cidade",
        "uf": "UF",
    }
    if pessoa.tipo == TipoPessoa.FISICA:
        obrigatorios |= {"nacionalidade": "nacionalidade", "estado_civil": "estado civil"}
    for campo, rotulo in obrigatorios.items():
        if not getattr(pessoa, campo):
            itens.append(f"{pessoa.nome}: {rotulo}")
    return itens


def campos_faltando_contrato(negocio):
    """Lista de dicts {texto, url} com o que falta preencher para gerar o contrato."""
    faltando = []

    loja = ConfiguracaoLoja.carregar()
    for rotulo in loja.campos_faltando():
        faltando.append({"texto": f"Loja: {rotulo}", "url": reverse("contratos:configuracao")})

    for parte in negocio.partes.select_related("pessoa"):
        for item in _faltando_pessoa(parte.pessoa):
            faltando.append(
                {"texto": item, "url": reverse("pessoas:editar", args=[parte.pessoa_id])}
            )

    for it in negocio.itens.select_related("veiculo"):
        v = it.veiculo
        if not v.chassi:
            faltando.append(
                {
                    "texto": f"{v.placa_formatada}: chassi",
                    "url": reverse("veiculos:editar", args=[v.pk]),
                }
            )
        if not v.renavam:
            faltando.append(
                {
                    "texto": f"{v.placa_formatada}: renavam",
                    "url": reverse("veiculos:editar", args=[v.pk]),
                }
            )
    return faltando


def _contexto(negocio):
    partes = list(negocio.partes.select_related("pessoa"))

    def parte(papel):
        return next((p.pessoa for p in partes if p.papel == papel), None)

    itens = list(negocio.itens.select_related("veiculo", "de_pessoa", "para_pessoa"))
    return {
        "loja": ConfiguracaoLoja.carregar(),
        "negocio": negocio,
        "itens": itens,
        "item": itens[0] if itens else None,
        "saida": next((i for i in itens if i.sai_da_loja), None),
        "entradas": [i for i in itens if i.entra_na_loja],
        "vendedor": parte(PapelParte.VENDEDOR),
        "comprador": parte(PapelParte.COMPRADOR),
        "permutante": parte(PapelParte.PERMUTANTE),
        "anuente": parte(PapelParte.ANUENTE),
        "diferenca": diferenca_troca(negocio) if negocio.tipo == TipoNegocio.TROCA else None,
    }


def _proxima_versao(negocio):
    atual = negocio.contratos.aggregate(maior=Max("versao"))["maior"] or 0
    return atual + 1


def gerar_contrato(negocio, *, usuario=None):
    faltando = campos_faltando_contrato(negocio)
    if faltando:
        raise ContratoError("Faltam dados para gerar o contrato.", faltando=faltando)

    modelo = escolher_modelo(negocio)
    contexto = _contexto(negocio)
    corpo = render_to_string(f"contratos/modelos/{modelo}.txt", contexto).strip()

    return Contrato.objetos.create(
        negocio=negocio,
        modelo=modelo,
        titulo=TITULOS[modelo],
        versao=_proxima_versao(negocio),
        corpo=corpo,
        criado_por=usuario,
        atualizado_por=usuario,
    )


def campos_faltando_consignacao(consignacao):
    faltando = []
    loja = ConfiguracaoLoja.carregar()
    for rotulo in loja.campos_faltando():
        faltando.append({"texto": f"Loja: {rotulo}", "url": reverse("contratos:configuracao")})
    for item in _faltando_pessoa(consignacao.proprietario):
        faltando.append(
            {"texto": item, "url": reverse("pessoas:editar", args=[consignacao.proprietario_id])}
        )
    v = consignacao.veiculo
    for campo, rotulo in (("chassi", "chassi"), ("renavam", "renavam")):
        if not getattr(v, campo):
            faltando.append(
                {
                    "texto": f"{v.placa_formatada}: {rotulo}",
                    "url": reverse("veiculos:editar", args=[v.pk]),
                }
            )
    return faltando


def gerar_contrato_consignacao(consignacao, *, usuario=None):
    faltando = campos_faltando_consignacao(consignacao)
    if faltando:
        raise ContratoError("Faltam dados para gerar o contrato.", faltando=faltando)

    contexto = {
        "loja": ConfiguracaoLoja.carregar(),
        "consignacao": consignacao,
        "proprietario": consignacao.proprietario,
        "v": consignacao.veiculo,
    }
    corpo = render_to_string("contratos/modelos/D.txt", contexto).strip()
    atual = consignacao.contratos.aggregate(maior=Max("versao"))["maior"] or 0
    return Contrato.objetos.create(
        consignacao=consignacao,
        modelo=ModeloContrato.D,
        titulo=TITULOS[ModeloContrato.D],
        versao=atual + 1,
        corpo=corpo,
        criado_por=usuario,
        atualizado_por=usuario,
    )


def _nome_carro(veiculo):
    return f"{veiculo.marca} {veiculo.modelo}".strip() if veiculo else ""


def _cliente_do_negocio(negocio):
    papel = {"venda": "comprador", "compra": "vendedor", "troca": "permutante"}.get(negocio.tipo)
    parte = negocio.partes.filter(papel=papel).first() if papel else None
    if parte is None:
        parte = negocio.partes.exclude(papel="anuente").first()
    return parte.pessoa.nome if parte else ""


def nome_arquivo_contrato(contrato):
    """
    Nome amigável do arquivo, no padrão:
    "[nº] Venda <carro> - <cliente>" ou "[nº] Troca <carro1> por <carro2> - <cliente>".
    """
    import re

    negocio = contrato.negocio
    if negocio:
        numero = negocio.numero_contrato or "rascunho"
        itens = list(negocio.itens.select_related("veiculo"))
        if negocio.tipo == "troca":
            saida = next((i for i in itens if i.de_pessoa_id is None), None)
            entradas = [i for i in itens if i.de_pessoa_id is not None]
            carro = _nome_carro(saida.veiculo) if saida else ""
            if entradas:
                carro += " por " + ", ".join(_nome_carro(e.veiculo) for e in entradas)
        else:
            carro = ", ".join(_nome_carro(i.veiculo) for i in itens)
        nome = f"[{numero}] {negocio.get_tipo_display()}"
        if carro.strip():
            nome += f" {carro.strip()}"
        cliente = _cliente_do_negocio(negocio)
        if cliente:
            nome += f" - {cliente}"
    elif contrato.consignacao:
        cons = contrato.consignacao
        numero = cons.numero_contrato or "rascunho"
        nome = f"[{numero}] Consignação {_nome_carro(cons.veiculo)} - {cons.proprietario.nome}"
    else:
        nome = f"contrato-{contrato.pk}"
    nome = re.sub(r'[\\/:*?"<>|\n\r\t]+', "", nome)
    nome = re.sub(r"\s+", " ", nome).strip()
    return nome or f"contrato-{contrato.pk}"


def renderizar_pdf(contrato):
    from weasyprint import HTML  # importado aqui porque depende das libs de sistema

    # Todos os contratos usam o layout bonito (MARA), montado a partir dos dados.
    if contrato.negocio_id or contrato.consignacao_id:
        from .mara import contexto_mara

        template = (
            "contratos/mara/consignacao.html"
            if contrato.consignacao_id
            else "contratos/mara/contrato.html"
        )
        html = render_to_string(template, contexto_mara(contrato))
    else:
        html = render_to_string(
            "contratos/pdf_base.html",
            {"contrato": contrato, "loja": ConfiguracaoLoja.carregar()},
        )
    return HTML(string=html).write_pdf()


def _foto_datauri(foto):
    import base64

    arquivo = foto.miniatura if foto.miniatura else foto.imagem
    arquivo.open("rb")
    try:
        dados = arquivo.read()
    finally:
        arquivo.close()
    return "data:image/jpeg;base64," + base64.b64encode(dados).decode()


def gerar_termo_vistoria(negocio, *, usuario=None):
    """
    Gera o termo de vistoria e entrega (checklist + fotos do carro) em PDF e salva
    como documento do negócio. Não é texto editável: é um documento para imprimir e assinar.
    """
    from django.core.files.base import ContentFile
    from weasyprint import HTML

    blocos = []
    for item in negocio.itens.select_related("veiculo", "de_pessoa", "para_pessoa"):
        fotos = [_foto_datauri(ft) for ft in item.veiculo.fotos.all()[:6]]
        blocos.append({"item": item, "veiculo": item.veiculo, "fotos": fotos})

    html = render_to_string(
        "contratos/termo_vistoria.html",
        {"loja": ConfiguracaoLoja.carregar(), "negocio": negocio, "blocos": blocos},
    )
    pdf = HTML(string=html).write_pdf()

    doc = Documento(
        negocio=negocio,
        tipo=TipoDocumento.TERMO_VISTORIA,
        gerado_pelo_sistema=True,
        descricao="Termo de vistoria e entrega",
        criado_por=usuario,
        atualizado_por=usuario,
    )
    doc.arquivo.save("termo-vistoria.pdf", ContentFile(pdf), save=False)
    doc.save()
    return doc


def renderizar_docx(contrato):
    from docx import Document as Docx

    documento = Docx()
    for bloco in contrato.corpo.split("\n\n"):
        texto = bloco.replace("\n", " ").strip()
        if texto:
            documento.add_paragraph(texto)
    buffer = io.BytesIO()
    documento.save(buffer)
    return buffer.getvalue()


def salvar_pdf_como_documento(contrato, *, usuario=None):
    from django.core.files.base import ContentFile

    pdf = renderizar_pdf(contrato)
    doc = Documento(
        negocio=contrato.negocio,
        consignacao=contrato.consignacao,
        tipo=TipoDocumento.CONTRATO,
        gerado_pelo_sistema=True,
        descricao=f"{contrato.titulo} (v{contrato.versao})",
        criado_por=usuario,
        atualizado_por=usuario,
    )
    doc.arquivo.save(f"contrato-v{contrato.versao}.pdf", ContentFile(pdf), save=False)
    doc.save()
    return doc
