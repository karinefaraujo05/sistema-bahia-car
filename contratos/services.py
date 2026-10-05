"""Lógica de documentos: upload de uma ou várias imagens, opcionalmente juntas num PDF."""

import io

from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image

from .models import Documento


class DocumentoError(Exception):
    """Erro de upload de documento, com mensagem em linguagem simples."""


def _eh_imagem(arquivo):
    return (getattr(arquivo, "content_type", "") or "").startswith("image/")


def _validar_tamanho(arquivo):
    limite = settings.TAMANHO_MAXIMO_UPLOAD_MB * 1024 * 1024
    if arquivo.size > limite:
        raise DocumentoError(
            f"O arquivo {arquivo.name} passa de {settings.TAMANHO_MAXIMO_UPLOAD_MB} MB."
        )


def _imagens_em_pdf(arquivos):
    imagens = []
    for arquivo in arquivos:
        arquivo.seek(0)
        imagens.append(Image.open(arquivo).convert("RGB"))
    buffer = io.BytesIO()
    imagens[0].save(buffer, format="PDF", save_all=True, append_images=imagens[1:])
    return ContentFile(buffer.getvalue())


def adicionar_documentos(
    *, negocio=None, consignacao=None, tipo, arquivos, descricao="", juntar_pdf=False, usuario=None
):
    """
    Cria documentos a partir dos arquivos enviados. Se `juntar_pdf` e todos forem imagens,
    gera um único PDF (útil para um contrato fotografado em várias páginas).
    """
    if not arquivos:
        raise DocumentoError("Nenhum arquivo foi enviado.")
    for arquivo in arquivos:
        _validar_tamanho(arquivo)

    def _novo(nome, conteudo):
        doc = Documento(
            negocio=negocio,
            consignacao=consignacao,
            tipo=tipo,
            descricao=descricao,
            criado_por=usuario,
            atualizado_por=usuario,
        )
        doc.arquivo.save(nome, conteudo, save=False)
        doc.save()
        return doc

    if juntar_pdf and len(arquivos) > 1 and all(_eh_imagem(a) for a in arquivos):
        return [_novo(f"{tipo}.pdf", _imagens_em_pdf(arquivos))]

    return [_novo(a.name, a) for a in arquivos]
