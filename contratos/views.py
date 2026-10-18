import unicodedata
from urllib.parse import quote

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from negocios.models import Consignacao, Negocio
from pessoas.validators import so_digitos

from .forms import ConfiguracaoLojaForm, DocumentoUploadForm
from .geracao import (
    ContratoError,
    gerar_contrato,
    gerar_contrato_consignacao,
    gerar_termo_vistoria,
    nome_arquivo_contrato,
    renderizar_docx,
    renderizar_pdf,
    salvar_pdf_como_documento,
)
from .models import ConfiguracaoLoja, Contrato
from .services import DocumentoError, adicionar_documentos

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _disposicao_download(contrato, ext):
    """Content-Disposition com o nome amigável do contrato (trata acentos)."""
    completo = f"{nome_arquivo_contrato(contrato)}.{ext}"
    ascii_fb = unicodedata.normalize("NFKD", completo).encode("ascii", "ignore").decode()
    ascii_fb = ascii_fb.replace('"', "") or f"contrato.{ext}"
    return "attachment; filename=\"%s\"; filename*=UTF-8''%s" % (ascii_fb, quote(completo))


@login_required
def configuracao(request):
    if not request.user.eh_administrador:
        messages.error(request, "Só o administrador acessa a configuração da loja.")
        return redirect("inicio")

    config = ConfiguracaoLoja.carregar()
    # Os dados da loja ficam travados por padrão (não mudam). Só edita com ?editar=1.
    editando = request.GET.get("editar") == "1"
    if request.method == "POST":
        form = ConfiguracaoLojaForm(request.POST, instance=config)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.atualizado_por = request.user
            obj.save()
            messages.success(request, "Configuração da loja salva.")
            return redirect("contratos:configuracao")
        editando = True  # com erro, continua no modo de edição
    else:
        form = ConfiguracaoLojaForm(instance=config)

    return render(
        request,
        "contratos/configuracao.html",
        {
            "form": form,
            "config": config,
            "faltando": config.campos_faltando(),
            "editando": editando,
        },
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
        erros = [e for lista in form.errors.values() for e in lista]
        messages.error(request, erros[0] if erros else "Escolha o tipo e ao menos um arquivo.")
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
@require_POST
def gerar_termo(request, negocio_pk):
    negocio = get_object_or_404(Negocio.objetos, pk=negocio_pk)
    if not negocio.itens.exists():
        messages.error(request, "Adicione o carro ao negócio antes de gerar o termo de vistoria.")
        return redirect("negocios:detalhe", pk=negocio.pk)
    gerar_termo_vistoria(negocio, usuario=request.user)
    messages.success(request, "Termo de vistoria gerado e anexado.")
    return redirect("negocios:detalhe", pk=negocio.pk)


@login_required
def editar_contrato(request, pk):
    contrato = get_object_or_404(Contrato.objetos, pk=pk)
    eh_admin = request.user.eh_administrador
    # Contrato assinado trava a edição; só o administrador pode mexer/destravar.
    travado = contrato.assinado and not eh_admin
    if request.method == "POST":
        if travado:
            messages.error(request, "Contrato assinado. Só o administrador pode alterar.")
            return redirect("contratos:editar_contrato", pk=contrato.pk)

        novo_corpo = request.POST.get("corpo", contrato.corpo)
        # Se o usuário mudou o texto, o PDF passa a sair desse texto (ver renderizar_pdf).
        if novo_corpo.strip() != (contrato.corpo or "").strip():
            contrato.corpo_editado = True
        contrato.corpo = novo_corpo
        contrato.observacoes = request.POST.get("observacoes", "").strip()
        try:
            n = int(request.POST.get("num_testemunhas", contrato.num_testemunhas))
        except (TypeError, ValueError):
            n = contrato.num_testemunhas
        contrato.num_testemunhas = n if n in (0, 1, 2) else 2

        # Assinatura: marcar trava o contrato. Desmarcar (destravar) só o admin pode.
        quer_assinado = bool(request.POST.get("assinado"))
        if contrato.assinado and not quer_assinado and not eh_admin:
            quer_assinado = True  # ignora tentativa de destravar de quem não é admin
        contrato.assinado = quer_assinado
        if quer_assinado:
            data = parse_date(request.POST.get("data_assinatura") or "")
            contrato.data_assinatura = data or contrato.data_assinatura or timezone.localdate()
        else:
            contrato.data_assinatura = None

        contrato.atualizado_por = request.user
        contrato.save()
        messages.success(request, "Contrato salvo.")
        return redirect("contratos:editar_contrato", pk=contrato.pk)
    return render(
        request,
        "contratos/editar.html",
        {"contrato": contrato, "travado": travado, "eh_admin": eh_admin},
    )


def _cliente_do_contrato(contrato):
    """Pessoa principal (cliente) do contrato — do negócio ou da consignação."""
    negocio = contrato.negocio
    if not negocio:
        return contrato.consignacao.proprietario if contrato.consignacao_id else None
    papel = {"venda": "comprador", "compra": "vendedor", "troca": "permutante"}.get(negocio.tipo)
    parte = negocio.partes.filter(papel=papel).first() if papel else None
    if parte is None:
        parte = negocio.partes.exclude(papel="anuente").first()
    return parte.pessoa if parte else None


def _voltar_do_contrato(contrato):
    if contrato.negocio_id:
        return redirect("negocios:detalhe", pk=contrato.negocio_id)
    if contrato.consignacao_id:
        return redirect("veiculos:detalhe", pk=contrato.consignacao.veiculo_id)
    return redirect("inicio")


@login_required
@require_POST
def enviar_whatsapp(request, pk):
    """Gera e salva o PDF do contrato e abre o WhatsApp do cliente com uma mensagem pronta."""
    contrato = get_object_or_404(Contrato.objetos, pk=pk)
    cliente = _cliente_do_contrato(contrato)
    telefone = so_digitos(cliente.telefone) if cliente and cliente.telefone else ""
    if not telefone:
        messages.error(request, "O cliente desse contrato não tem telefone cadastrado.")
        return _voltar_do_contrato(contrato)

    # Gera e salva o PDF: fica pronto como documento do negócio pra anexar no WhatsApp.
    salvar_pdf_como_documento(contrato, usuario=request.user)

    numero = telefone if telefone.startswith("55") else "55" + telefone
    primeiro_nome = cliente.nome.split()[0] if cliente.nome else ""
    loja = ConfiguracaoLoja.carregar()
    mensagem = f"Olá {primeiro_nome}! Segue o contrato ({contrato.titulo.lower()})."
    mensagem += " Qualquer dúvida, estou à disposição."
    assinatura = loja.nome_fantasia or loja.razao_social
    if assinatura:
        mensagem += f" — {assinatura}"
    return redirect(f"https://wa.me/{numero}?text={quote(mensagem)}")


@login_required
def baixar_pdf(request, pk):
    contrato = get_object_or_404(Contrato.objetos, pk=pk)
    pdf = renderizar_pdf(contrato)
    resp = HttpResponse(pdf, content_type="application/pdf")
    if request.GET.get("inline"):
        # Visualização/impressão: mostra na aba, sem salvar uma cópia nova a cada vez.
        resp["Content-Disposition"] = "inline"
        return resp
    # Download normal: o PDF gerado fica salvo como documento do negócio/consignação.
    salvar_pdf_como_documento(contrato, usuario=request.user)
    resp["Content-Disposition"] = _disposicao_download(contrato, "pdf")
    return resp


@login_required
def imprimir_contrato(request, pk):
    """Abre o PDF numa aba e dispara a impressão (window.print), para uso no computador."""
    contrato = get_object_or_404(Contrato.objetos, pk=pk)
    return render(request, "contratos/imprimir.html", {"contrato": contrato})


@login_required
def baixar_docx(request, pk):
    contrato = get_object_or_404(Contrato.objetos, pk=pk)
    conteudo = renderizar_docx(contrato)
    resp = HttpResponse(conteudo, content_type=DOCX_MIME)
    resp["Content-Disposition"] = _disposicao_download(contrato, "docx")
    return resp
