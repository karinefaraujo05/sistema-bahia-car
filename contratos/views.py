from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from negocios.models import Consignacao, Negocio

from .forms import ConfiguracaoLojaForm, DocumentoUploadForm
from .geracao import (
    ContratoError,
    gerar_contrato,
    gerar_contrato_consignacao,
    renderizar_docx,
    renderizar_pdf,
    salvar_pdf_como_documento,
)
from .models import ConfiguracaoLoja, Contrato
from .services import DocumentoError, adicionar_documentos

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@login_required
def configuracao(request):
    if not request.user.eh_administrador:
        messages.error(request, "Só o administrador acessa a configuração da loja.")
        return redirect("inicio")

    config = ConfiguracaoLoja.carregar()
    if request.method == "POST":
        form = ConfiguracaoLojaForm(request.POST, instance=config)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.atualizado_por = request.user
            obj.save()
            messages.success(request, "Configuração da loja salva.")
            return redirect("contratos:configuracao")
    else:
        form = ConfiguracaoLojaForm(instance=config)

    return render(
        request,
        "contratos/configuracao.html",
        {"form": form, "faltando": config.campos_faltando()},
    )


@login_required
@require_POST
def upload_documentos(request, negocio_pk):
    negocio = get_object_or_404(Negocio.objetos, pk=negocio_pk)
    form = DocumentoUploadForm(request.POST)
    arquivos = request.FILES.getlist("arquivos")
    if form.is_valid():
        try:
            criados = adicionar_documentos(
                negocio=negocio,
                tipo=form.cleaned_data["tipo"],
                arquivos=arquivos,
                descricao=form.cleaned_data["descricao"],
                juntar_pdf=form.cleaned_data["juntar_pdf"],
                usuario=request.user,
            )
        except DocumentoError as erro:
            messages.error(request, str(erro))
            return redirect("negocios:detalhe", pk=negocio.pk)
        messages.success(request, f"{len(criados)} documento(s) anexado(s).")
    else:
        messages.error(request, "Escolha o tipo e ao menos um arquivo.")
    return redirect("negocios:detalhe", pk=negocio.pk)


# --- Contratos ---


@login_required
@require_POST
def gerar(request, negocio_pk):
    negocio = get_object_or_404(Negocio.objetos, pk=negocio_pk)
    try:
        contrato = gerar_contrato(negocio, usuario=request.user)
    except ContratoError as erro:
        return render(request, "contratos/faltando.html", {"faltando": erro.faltando})
    return redirect("contratos:editar_contrato", pk=contrato.pk)


@login_required
@require_POST
def gerar_consignacao(request, consignacao_pk):
    consignacao = get_object_or_404(Consignacao.objetos, pk=consignacao_pk)
    try:
        contrato = gerar_contrato_consignacao(consignacao, usuario=request.user)
    except ContratoError as erro:
        return render(request, "contratos/faltando.html", {"faltando": erro.faltando})
    return redirect("contratos:editar_contrato", pk=contrato.pk)


@login_required
def editar_contrato(request, pk):
    contrato = get_object_or_404(Contrato.objetos, pk=pk)
    if request.method == "POST":
        contrato.corpo = request.POST.get("corpo", contrato.corpo)
        contrato.atualizado_por = request.user
        contrato.save()
        messages.success(request, "Contrato salvo.")
        return redirect("contratos:editar_contrato", pk=contrato.pk)
    return render(request, "contratos/editar.html", {"contrato": contrato})


@login_required
def baixar_pdf(request, pk):
    contrato = get_object_or_404(Contrato.objetos, pk=pk)
    pdf = renderizar_pdf(contrato)
    # O PDF gerado fica salvo como documento do negócio/consignação.
    salvar_pdf_como_documento(contrato, usuario=request.user)
    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="contrato-{contrato.pk}.pdf"'
    return resp


@login_required
def baixar_docx(request, pk):
    contrato = get_object_or_404(Contrato.objetos, pk=pk)
    conteudo = renderizar_docx(contrato)
    resp = HttpResponse(conteudo, content_type=DOCX_MIME)
    resp["Content-Disposition"] = f'attachment; filename="contrato-{contrato.pk}.docx"'
    return resp
