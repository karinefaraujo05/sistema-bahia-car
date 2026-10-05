from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from negocios.models import Negocio

from .forms import ConfiguracaoLojaForm, DocumentoUploadForm
from .models import ConfiguracaoLoja
from .services import DocumentoError, adicionar_documentos


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
