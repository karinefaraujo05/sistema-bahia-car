from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from veiculos.forms import VeiculoForm
from veiculos.models import Situacao, StatusVeiculo, Veiculo

from .forms import EscolherCarroForm, EscolherPessoaForm, PagamentoEntregaForm
from .models import (
    ItemNegocio,
    Modalidade,
    Negocio,
    PapelParte,
    ParteNegocio,
    StatusNegocio,
    TipoNegocio,
)
from .services import RegraNegocioError, cancelar_negocio, concluir_negocio, diferenca_troca

# Papel da pessoa principal em cada tipo de negócio próprio.
PAPEL_PRINCIPAL = {
    TipoNegocio.VENDA: PapelParte.COMPRADOR,
    TipoNegocio.COMPRA: PapelParte.VENDEDOR,
}


def _rascunho(pk):
    return get_object_or_404(Negocio.objetos, pk=pk, status=StatusNegocio.RASCUNHO)


def _parte_principal(negocio):
    papel = PAPEL_PRINCIPAL[negocio.tipo]
    return negocio.partes.filter(papel=papel).first()


def _item_unico(negocio):
    return negocio.itens.first()


@login_required
def iniciar(request, tipo):
    if tipo not in (TipoNegocio.COMPRA, TipoNegocio.VENDA):
        messages.info(request, "Esse tipo de negócio chega na próxima parte da Fase 4.")
        return redirect("inicio")
    negocio = Negocio.objetos.create(
        tipo=tipo,
        modalidade=Modalidade.PROPRIA,
        status=StatusNegocio.RASCUNHO,
        criado_por=request.user,
        atualizado_por=request.user,
    )
    return redirect("negocios:passo_pessoa", pk=negocio.pk)


@login_required
def passo_pessoa(request, pk):
    negocio = _rascunho(pk)
    papel = PAPEL_PRINCIPAL[negocio.tipo]
    parte = _parte_principal(negocio)

    if request.method == "POST":
        form = EscolherPessoaForm(request.POST)
        if form.is_valid():
            pessoa = form.resolver(usuario=request.user)
            ParteNegocio.objetos.update_or_create(
                negocio=negocio, papel=papel, defaults={"pessoa": pessoa}
            )
            if "rascunho" in request.POST:
                return redirect("negocios:detalhe", pk=negocio.pk)
            return redirect("negocios:passo_carro", pk=negocio.pk)
    else:
        form = EscolherPessoaForm(initial={"pessoa": parte.pessoa if parte else None})

    titulo = "Quem está comprando?" if negocio.tipo == TipoNegocio.VENDA else "De quem é o carro?"
    return render(
        request,
        "negocios/passo_pessoa.html",
        {"negocio": negocio, "form": form, "titulo": titulo, "passo": 1},
    )


@login_required
def passo_carro(request, pk):
    negocio = _rascunho(pk)
    item = _item_unico(negocio)

    if negocio.tipo == TipoNegocio.VENDA:
        return _carro_do_estoque(request, negocio, item)
    return _carro_novo(request, negocio, item)


def _carro_do_estoque(request, negocio, item):
    vendaveis = Veiculo.objetos.filter(
        situacao=Situacao.PROPRIO,
        status__in=[StatusVeiculo.EM_ESTOQUE, StatusVeiculo.RESERVADO],
    )
    comprador = _parte_principal(negocio)
    if request.method == "POST":
        form = EscolherCarroForm(request.POST, queryset=vendaveis)
        if form.is_valid():
            veiculo = form.cleaned_data["veiculo"]
            ItemNegocio.objetos.update_or_create(
                negocio=negocio,
                defaults={
                    "veiculo": veiculo,
                    "de_pessoa": None,
                    "para_pessoa": comprador.pessoa if comprador else None,
                    "valor": item.valor if item else (veiculo.valor_anunciado or 0),
                },
            )
            if "rascunho" in request.POST:
                return redirect("negocios:detalhe", pk=negocio.pk)
            return redirect("negocios:passo_pagamento", pk=negocio.pk)
    else:
        form = EscolherCarroForm(
            queryset=vendaveis, initial={"veiculo": item.veiculo if item else None}
        )
    return render(
        request,
        "negocios/passo_carro_estoque.html",
        {"negocio": negocio, "form": form, "titulo": "Qual carro?", "passo": 2},
    )


def _carro_novo(request, negocio, item):
    vendedor = _parte_principal(negocio)
    instancia = item.veiculo if item else None
    if request.method == "POST":
        form = VeiculoForm(request.POST, instance=instancia)
        if form.is_valid():
            veiculo = form.save(commit=False)
            if not instancia:
                veiculo.criado_por = request.user
            veiculo.atualizado_por = request.user
            veiculo.save()
            ItemNegocio.objetos.update_or_create(
                negocio=negocio,
                defaults={
                    "veiculo": veiculo,
                    "de_pessoa": vendedor.pessoa if vendedor else None,
                    "para_pessoa": None,
                    "valor": item.valor if item else 0,
                },
            )
            if "rascunho" in request.POST:
                return redirect("negocios:detalhe", pk=negocio.pk)
            return redirect("negocios:passo_pagamento", pk=negocio.pk)
    else:
        form = VeiculoForm(instance=instancia)
    return render(
        request,
        "negocios/passo_carro_novo.html",
        {"negocio": negocio, "form": form, "titulo": "Qual carro entrou?", "passo": 2},
    )


@login_required
def passo_pagamento(request, pk):
    negocio = _rascunho(pk)
    item = _item_unico(negocio)
    if not item:
        return redirect("negocios:passo_carro", pk=negocio.pk)

    exige_quitacao = item.veiculo.alienado
    if request.method == "POST":
        form = PagamentoEntregaForm(request.POST, exige_quitacao=exige_quitacao)
        if form.is_valid():
            d = form.cleaned_data
            item.valor = d["valor"]
            item.km_entrega = d.get("km_entrega")
            if exige_quitacao:
                item.quitacao_opcao = d["quitacao_opcao"]
            item.atualizado_por = request.user
            item.save()

            negocio.forma_pagamento = d.get("forma_pagamento", "")
            negocio.detalhes_pagamento = d.get("detalhes_pagamento", "")
            negocio.data = d["data"]
            negocio.data_hora_entrega = d.get("data_hora_entrega")
            negocio.local_entrega = d.get("local_entrega", "")
            negocio.atualizado_por = request.user
            negocio.save()

            if "rascunho" in request.POST:
                return redirect("negocios:detalhe", pk=negocio.pk)
            return redirect("negocios:revisao", pk=negocio.pk)
    else:
        form = PagamentoEntregaForm(
            exige_quitacao=exige_quitacao,
            initial={
                "valor": item.valor or None,
                "km_entrega": item.km_entrega,
                "forma_pagamento": negocio.forma_pagamento,
                "detalhes_pagamento": negocio.detalhes_pagamento,
                "data": negocio.data,
                "data_hora_entrega": negocio.data_hora_entrega,
                "local_entrega": negocio.local_entrega,
                "quitacao_opcao": item.quitacao_opcao,
            },
        )
    return render(
        request,
        "negocios/passo_pagamento.html",
        {"negocio": negocio, "form": form, "titulo": "Valores, pagamento e entrega", "passo": 3},
    )


@login_required
def revisao(request, pk):
    negocio = _rascunho(pk)
    if request.method == "POST":
        try:
            concluir_negocio(negocio, usuario=request.user)
        except RegraNegocioError as erro:
            messages.error(request, str(erro))
            return redirect("negocios:revisao", pk=negocio.pk)
        rotulo = "Venda salva." if negocio.tipo == TipoNegocio.VENDA else "Compra salva."
        messages.success(request, rotulo)
        return redirect("negocios:detalhe", pk=negocio.pk)

    return render(
        request,
        "negocios/revisao.html",
        {
            "negocio": negocio,
            "item": _item_unico(negocio),
            "parte": _parte_principal(negocio),
            "passo": 4,
        },
    )


@login_required
def detalhe(request, pk):
    negocio = get_object_or_404(Negocio.objetos, pk=pk)
    return render(
        request,
        "negocios/detalhe.html",
        {
            "negocio": negocio,
            "itens": negocio.itens.select_related("veiculo", "de_pessoa", "para_pessoa"),
            "partes": negocio.partes.select_related("pessoa"),
            "diferenca": diferenca_troca(negocio) if negocio.tipo == TipoNegocio.TROCA else None,
        },
    )


@login_required
def confirmar_cancelamento(request, pk):
    negocio = get_object_or_404(Negocio.objetos, pk=pk, status=StatusNegocio.CONCLUIDO)
    return render(request, "negocios/confirmar_cancelamento.html", {"negocio": negocio})


@login_required
@require_POST
def cancelar(request, pk):
    negocio = get_object_or_404(Negocio.objetos, pk=pk, status=StatusNegocio.CONCLUIDO)
    try:
        cancelar_negocio(negocio, usuario=request.user)
    except RegraNegocioError as erro:
        messages.error(request, str(erro))
        return redirect("negocios:detalhe", pk=negocio.pk)
    messages.success(request, "Negócio cancelado. Os carros voltaram ao estado anterior.")
    return redirect("negocios:detalhe", pk=negocio.pk)
