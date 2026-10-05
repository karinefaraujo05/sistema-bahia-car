from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import VeiculoForm
from .models import FotoVeiculo, StatusVeiculo, Veiculo
from .services import (
    ABAS_ESTOQUE,
    ORIGENS_ESTOQUE,
    adicionar_foto,
    arquivar_veiculo,
    consultar_estoque,
    definir_capa,
    remover_foto,
)


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
def detalhe(request, pk):
    from negocios.services import lucro_do_veiculo

    veiculo = get_object_or_404(Veiculo.objetos, pk=pk)
    lucro = None
    if request.user.eh_administrador and veiculo.status == StatusVeiculo.VENDIDO:
        lucro = lucro_do_veiculo(veiculo)
    return render(request, "veiculos/detalhe.html", {"veiculo": veiculo, "lucro": lucro})


@login_required
def novo(request):
    if request.method == "POST":
        form = VeiculoForm(request.POST)
        if form.is_valid():
            veiculo = form.save(commit=False)
            veiculo.criado_por = request.user
            veiculo.atualizado_por = request.user
            veiculo.save()
            for arquivo in request.FILES.getlist("fotos"):
                adicionar_foto(veiculo, arquivo, usuario=request.user)
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
            for arquivo in request.FILES.getlist("fotos"):
                adicionar_foto(veiculo, arquivo, usuario=request.user)
            messages.success(request, "Carro atualizado.")
            return redirect("veiculos:detalhe", pk=veiculo.pk)
    else:
        form = VeiculoForm(instance=veiculo)
    return render(request, "veiculos/form.html", {"form": form, "veiculo": veiculo})


@login_required
@require_POST
def arquivar(request, pk):
    veiculo = get_object_or_404(Veiculo.objetos, pk=pk)
    arquivar_veiculo(veiculo, usuario=request.user)
    messages.success(request, "Carro arquivado. Ele sai do estoque, mas nada é apagado.")
    return redirect("veiculos:estoque")


def _galeria(request, veiculo):
    """Devolve a galeria renderizada (parcial), para respostas HTMX."""
    return render(request, "veiculos/partials/galeria.html", {"veiculo": veiculo})


@login_required
@require_POST
def adicionar_fotos(request, pk):
    veiculo = get_object_or_404(Veiculo.objetos, pk=pk)
    enviadas = request.FILES.getlist("fotos")
    for arquivo in enviadas:
        adicionar_foto(veiculo, arquivo, usuario=request.user)
    if request.htmx:
        return _galeria(request, veiculo)
    messages.success(request, f"{len(enviadas)} foto(s) adicionada(s).")
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
