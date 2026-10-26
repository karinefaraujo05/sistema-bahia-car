from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from contratos.models import Documento, TipoDocumento
from core.tenancy import empresa_atual

from .consulta_placa import consultar_placa_externa, provedor_ativo
from .forms import GastoVeiculoForm, VeiculoForm
from .models import FotoVeiculo, GastoVeiculo, StatusVeiculo, Veiculo
from .services import (
    ABAS_ESTOQUE,
    ORIGENS_ESTOQUE,
    FotoError,
    adicionar_foto,
    arquivar_veiculo,
    consultar_estoque,
    definir_capa,
    remover_foto,
)
from .validators import normalizar_placa


def _salvar_fotos(veiculo, arquivos, usuario):
    """Salva as fotos enviadas, pulando as que derem problema. Devolve (ok, erros)."""
    ok, erros = 0, []
    for arquivo in arquivos:
        try:
            adicionar_foto(veiculo, arquivo, usuario=usuario)
            ok += 1
        except FotoError as erro:
            erros.append(str(erro))
    return ok, erros


@login_required
def estoque(request):
    status = request.GET.get("status", StatusVeiculo.EM_ESTOQUE)
    origem = request.GET.get("origem", "todos")
    ordem = request.GET.get("ordem", "recentes")

    carros = consultar_estoque(status=status, origem=origem, ordem=ordem)

    contexto = {
        "carros": carros,
        "abas": ABAS_ESTOQUE,
        "origens": ORIGENS_ESTOQUE,
        "status_atual": status,
        "origem_atual": origem,
        "ordem_atual": ordem,
    }
    return render(request, "veiculos/estoque.html", contexto)


@login_required
def patio(request):
    """Modo pátio: lista grande e simples dos carros à venda, pra usar no celular."""
    from contratos.models import ConfiguracaoLoja

    carros = consultar_estoque(
        status=StatusVeiculo.EM_ESTOQUE, origem="todos", ordem="recentes"
    )
    return render(
        request,
        "veiculos/patio.html",
        {"carros": carros, "loja": ConfiguracaoLoja.carregar()},
    )


@login_required
def detalhe(request, pk):
    from negocios.services import lucro_do_veiculo

    veiculo = get_object_or_404(Veiculo.objetos, pk=pk)
    eh_admin = request.user.eh_administrador
    lucro = None
    if eh_admin and veiculo.status == StatusVeiculo.VENDIDO:
        lucro = lucro_do_veiculo(veiculo)
    return render(
        request,
        "veiculos/detalhe.html",
        {
            "veiculo": veiculo,
            "lucro": lucro,
            # Avisa, na ficha, o que falta pro contrato (chassi/renavam).
            "faltando_contrato": veiculo.campos_faltando_contrato(),
            # Gastos do carro (só o administrador vê/lança — é número financeiro).
            "gastos": veiculo.gastos.all() if eh_admin else None,
            "gasto_form": GastoVeiculoForm() if eh_admin else None,
        },
    )


@login_required
@require_POST
def adicionar_gasto(request, pk):
    if not request.user.eh_administrador:
        messages.error(request, "Só o administrador lança gastos.")
        return redirect("veiculos:detalhe", pk=pk)
    veiculo = get_object_or_404(Veiculo.objetos, pk=pk)
    form = GastoVeiculoForm(request.POST)
    if form.is_valid():
        gasto = form.save(commit=False)
        gasto.veiculo = veiculo
        gasto.criado_por = request.user
        gasto.atualizado_por = request.user
        gasto.save()
        messages.success(request, "Gasto lançado.")
    else:
        messages.error(request, "Confira a descrição e o valor do gasto.")
    return redirect("veiculos:detalhe", pk=veiculo.pk)


@login_required
@require_POST
def remover_gasto(request, gasto_pk):
    gasto = get_object_or_404(GastoVeiculo.objetos, pk=gasto_pk)
    if not request.user.eh_administrador:
        messages.error(request, "Só o administrador remove gastos.")
        return redirect("veiculos:detalhe", pk=gasto.veiculo_id)
    veiculo_id = gasto.veiculo_id
    gasto.atualizado_por = request.user
    gasto.arquivar()
    messages.success(request, "Gasto removido.")
    return redirect("veiculos:detalhe", pk=veiculo_id)


@login_required
def buscar_placa(request):
    """
    Busca a placa no PRÓPRIO banco (inclusive carros arquivados), na empresa atual.
    Usado no cadastro: carro que já passou pela loja volta preenchido, sem digitar tudo.
    """
    placa = normalizar_placa(request.GET.get("placa", ""))
    if len(placa) < 7:
        return JsonResponse({"encontrado": False})
    qs = Veiculo.todos.filter(placa=placa)
    empresa = empresa_atual()
    if empresa is not None:
        qs = qs.filter(empresa=empresa)
    veiculo = qs.order_by("-criado_em").first()
    if veiculo is None:
        return JsonResponse({"encontrado": False})
    return JsonResponse(
        {
            "encontrado": True,
            "arquivado": veiculo.arquivado,
            "pk": veiculo.pk,
            "url": reverse("veiculos:detalhe", args=[veiculo.pk]),
            "resumo": f"{veiculo.marca} {veiculo.modelo}".strip(),
        }
    )


@login_required
def consultar_placa(request):
    """Consulta a placa numa API externa (se um provedor estiver configurado)."""
    if provedor_ativo() == "none":
        return JsonResponse({"ativo": False})
    placa = normalizar_placa(request.GET.get("placa", ""))
    dados = consultar_placa_externa(placa) if len(placa) >= 7 else None
    if not dados:
        return JsonResponse({"ativo": True, "ok": False})
    return JsonResponse({"ativo": True, "ok": True, "dados": dados})


@login_required
def novo(request):
    if request.method == "POST":
        form = VeiculoForm(request.POST)
        if form.is_valid():
            veiculo = form.save(commit=False)
            veiculo.criado_por = request.user
            veiculo.atualizado_por = request.user
            veiculo.save()
            _, erros = _salvar_fotos(veiculo, request.FILES.getlist("fotos"), request.user)
            for erro in erros:
                messages.warning(request, erro)
            messages.success(request, "Carro cadastrado.")
            return redirect("veiculos:detalhe", pk=veiculo.pk)
    else:
        form = VeiculoForm()
    return render(request, "veiculos/form.html", {"form": form, "veiculo": None})


@login_required
def editar(request, pk):
    veiculo = get_object_or_404(Veiculo.objetos, pk=pk)
    if request.method == "POST":
        form = VeiculoForm(request.POST, instance=veiculo)
        if form.is_valid():
            veiculo = form.save(commit=False)
            veiculo.atualizado_por = request.user
            veiculo.save()
            _, erros = _salvar_fotos(veiculo, request.FILES.getlist("fotos"), request.user)
            for erro in erros:
                messages.warning(request, erro)
            messages.success(request, "Carro atualizado.")
            return redirect("veiculos:detalhe", pk=veiculo.pk)
    else:
        form = VeiculoForm(instance=veiculo)
    return render(request, "veiculos/form.html", {"form": form, "veiculo": veiculo})


@login_required
@require_POST
def arquivar(request, pk):
    # Só o responsável (superusuário) pode arquivar carros.
    if not request.user.is_superuser:
        messages.error(request, "Só o responsável pode arquivar um carro.")
        return redirect("veiculos:detalhe", pk=pk)
    veiculo = get_object_or_404(Veiculo.objetos, pk=pk)
    arquivar_veiculo(veiculo, usuario=request.user)
    messages.success(request, "Carro arquivado. Ele sai do estoque, mas nada é apagado.")
    return redirect("veiculos:estoque")


@login_required
@require_POST
def adicionar_documento(request, pk):
    """Guarda uma foto/PDF do documento direto na ficha do carro."""
    veiculo = get_object_or_404(Veiculo.objetos, pk=pk)
    arquivo = request.FILES.get("arquivo")
    if not arquivo:
        messages.error(request, "Escolha uma foto ou um PDF para guardar.")
        return redirect("veiculos:detalhe", pk=pk)
    limite = settings.TAMANHO_MAXIMO_UPLOAD_MB * 1024 * 1024
    if arquivo.size > limite:
        messages.error(request, f"O arquivo passa de {settings.TAMANHO_MAXIMO_UPLOAD_MB} MB.")
        return redirect("veiculos:detalhe", pk=pk)
    tipo = request.POST.get("tipo") or TipoDocumento.DOC_VEICULO
    Documento._default_manager.create(
        veiculo=veiculo,
        tipo=tipo,
        arquivo=arquivo,
        descricao=request.POST.get("descricao", ""),
        criado_por=request.user,
        atualizado_por=request.user,
    )
    messages.success(request, "Documento guardado na ficha do carro.")
    return redirect("veiculos:detalhe", pk=pk)


def _galeria(request, veiculo):
    """Devolve a galeria renderizada (parcial), para respostas HTMX."""
    return render(request, "veiculos/partials/galeria.html", {"veiculo": veiculo})


@login_required
@require_POST
def adicionar_fotos(request, pk):
    veiculo = get_object_or_404(Veiculo.objetos, pk=pk)
    ok, erros = _salvar_fotos(veiculo, request.FILES.getlist("fotos"), request.user)
    if request.htmx:
        return _galeria(request, veiculo)
    for erro in erros:
        messages.warning(request, erro)
    messages.success(request, f"{ok} foto(s) adicionada(s).")
    return redirect("veiculos:detalhe", pk=veiculo.pk)


@login_required
@require_POST
def remover_foto_view(request, foto_pk):
    foto = get_object_or_404(FotoVeiculo.objetos, pk=foto_pk)
    veiculo = foto.veiculo
    remover_foto(foto, usuario=request.user)
    if request.htmx:
        return _galeria(request, veiculo)
    return redirect("veiculos:detalhe", pk=veiculo.pk)


@login_required
@require_POST
def definir_capa_view(request, foto_pk):
    foto = get_object_or_404(FotoVeiculo.objetos, pk=foto_pk)
    definir_capa(foto, usuario=request.user)
    if request.htmx:
        return _galeria(request, foto.veiculo)
    return redirect("veiculos:detalhe", pk=foto.veiculo_id)
