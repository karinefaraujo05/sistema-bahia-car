from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from veiculos.forms import VeiculoForm
from veiculos.models import Situacao, StatusVeiculo, Veiculo

from .forms import (
    ConsignacaoTermosForm,
    EscolherCarroForm,
    EscolherPessoaForm,
    PagamentoEntregaForm,
    TrocaValoresForm,
)
from .models import (
    Consignacao,
    ItemNegocio,
    Modalidade,
    Negocio,
    PapelParte,
    ParteNegocio,
    StatusConsignacao,
    StatusNegocio,
    TipoNegocio,
)
from .services import (
    RegraNegocioError,
    cancelar_negocio,
    concluir_negocio,
    criar_consignacao,
    devolver_consignado,
    diferenca_troca,
    registrar_repasse,
)

# Papel da pessoa principal (o cliente) em cada tipo de negócio próprio.
PAPEL_PRINCIPAL = {
    TipoNegocio.VENDA: PapelParte.COMPRADOR,
    TipoNegocio.COMPRA: PapelParte.VENDEDOR,
    TipoNegocio.TROCA: PapelParte.PERMUTANTE,
}


def _rascunho(pk):
    return get_object_or_404(Negocio.objetos, pk=pk, status=StatusNegocio.RASCUNHO)


def _parte_principal(negocio):
    return negocio.partes.filter(papel=PAPEL_PRINCIPAL[negocio.tipo]).first()


def _item_unico(negocio):
    return negocio.itens.first()


def _item_saida(negocio):
    return negocio.itens.filter(de_pessoa__isnull=True).first()


def _item_entrada(negocio):
    return negocio.itens.filter(para_pessoa__isnull=True).first()


@login_required
def iniciar(request, tipo):
    if tipo not in (TipoNegocio.COMPRA, TipoNegocio.VENDA, TipoNegocio.TROCA):
        messages.info(request, "Esse tipo de negócio ainda não está disponível.")
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
            if negocio.tipo == TipoNegocio.TROCA:
                return redirect("negocios:troca_carro_loja", pk=negocio.pk)
            return redirect("negocios:passo_carro", pk=negocio.pk)
    else:
        form = EscolherPessoaForm(initial={"pessoa": parte.pessoa if parte else None})

    titulos = {
        TipoNegocio.VENDA: "Quem está comprando?",
        TipoNegocio.COMPRA: "De quem é o carro?",
        TipoNegocio.TROCA: "Quem é o cliente da troca?",
    }
    return render(
        request,
        "negocios/passo_pessoa.html",
        {"negocio": negocio, "form": form, "titulo": titulos[negocio.tipo], "passo": 1},
    )


@login_required
def passo_carro(request, pk):
    negocio = _rascunho(pk)
    item = _item_unico(negocio)
    if negocio.tipo == TipoNegocio.VENDA:
        return _carro_do_estoque(request, negocio, item)
    return _carro_novo(request, negocio, item)


def _vendaveis():
    return Veiculo.objetos.filter(
        situacao=Situacao.PROPRIO,
        status__in=[StatusVeiculo.EM_ESTOQUE, StatusVeiculo.RESERVADO],
    )


def _carro_do_estoque(request, negocio, item):
    comprador = _parte_principal(negocio)
    if request.method == "POST":
        form = EscolherCarroForm(request.POST, queryset=_vendaveis())
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
            queryset=_vendaveis(), initial={"veiculo": item.veiculo if item else None}
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
            _salvar_pagamento_item(negocio, item, form.cleaned_data, request.user, exige_quitacao)
            if "rascunho" in request.POST:
                return redirect("negocios:detalhe", pk=negocio.pk)
            return redirect("negocios:revisao", pk=negocio.pk)
    else:
        form = PagamentoEntregaForm(
            exige_quitacao=exige_quitacao, initial=_inicial_pagamento(negocio, item)
        )
    return render(
        request,
        "negocios/passo_pagamento.html",
        {"negocio": negocio, "form": form, "titulo": "Valores, pagamento e entrega", "passo": 3},
    )


def _inicial_pagamento(negocio, item):
    return {
        "valor": item.valor or None,
        "km_entrega": item.km_entrega,
        "forma_pagamento": negocio.forma_pagamento,
        "detalhes_pagamento": negocio.detalhes_pagamento,
        "data": negocio.data,
        "data_hora_entrega": negocio.data_hora_entrega,
        "local_entrega": negocio.local_entrega,
        "quitacao_opcao": item.quitacao_opcao,
    }


def _salvar_pagamento_item(negocio, item, dados, usuario, exige_quitacao):
    item.valor = dados["valor"]
    item.km_entrega = dados.get("km_entrega")
    if exige_quitacao:
        item.quitacao_opcao = dados["quitacao_opcao"]
    item.atualizado_por = usuario
    item.save()
    _salvar_pagamento_negocio(negocio, dados, usuario)


def _salvar_pagamento_negocio(negocio, dados, usuario):
    negocio.forma_pagamento = dados.get("forma_pagamento", "")
    negocio.detalhes_pagamento = dados.get("detalhes_pagamento", "")
    negocio.data = dados["data"]
    negocio.data_hora_entrega = dados.get("data_hora_entrega")
    negocio.local_entrega = dados.get("local_entrega", "")
    negocio.atualizado_por = usuario
    negocio.save()


# --- Troca ---


@login_required
def troca_carro_loja(request, pk):
    negocio = _rascunho(pk)
    cliente = _parte_principal(negocio)
    item = _item_saida(negocio)
    if request.method == "POST":
        form = EscolherCarroForm(request.POST, queryset=_vendaveis())
        if form.is_valid():
            veiculo = form.cleaned_data["veiculo"]
            if item:
                item.veiculo = veiculo
                item.para_pessoa = cliente.pessoa if cliente else None
                item.save()
            else:
                ItemNegocio.objetos.create(
                    negocio=negocio,
                    veiculo=veiculo,
                    de_pessoa=None,
                    para_pessoa=cliente.pessoa if cliente else None,
                    valor=veiculo.valor_anunciado or 0,
                )
            if "rascunho" in request.POST:
                return redirect("negocios:detalhe", pk=negocio.pk)
            return redirect("negocios:troca_carro_cliente", pk=negocio.pk)
    else:
        form = EscolherCarroForm(
            queryset=_vendaveis(), initial={"veiculo": item.veiculo if item else None}
        )
    return render(
        request,
        "negocios/passo_carro_estoque.html",
        {"negocio": negocio, "form": form, "titulo": "Qual carro da loja sai?", "passo": 2},
    )


@login_required
def troca_carro_cliente(request, pk):
    negocio = _rascunho(pk)
    cliente = _parte_principal(negocio)
    item = _item_entrada(negocio)
    instancia = item.veiculo if item else None
    if request.method == "POST":
        form = VeiculoForm(request.POST, instance=instancia)
        if form.is_valid():
            veiculo = form.save(commit=False)
            if not instancia:
                veiculo.criado_por = request.user
                veiculo.situacao = Situacao.TERCEIRO
                veiculo.proprietario = cliente.pessoa if cliente else None
            veiculo.atualizado_por = request.user
            veiculo.save()
            if item:
                item.veiculo = veiculo
                item.save()
            else:
                ItemNegocio.objetos.create(
                    negocio=negocio,
                    veiculo=veiculo,
                    de_pessoa=cliente.pessoa if cliente else None,
                    para_pessoa=None,
                    valor=0,
                )
            if "rascunho" in request.POST:
                return redirect("negocios:detalhe", pk=negocio.pk)
            return redirect("negocios:troca_valores", pk=negocio.pk)
    else:
        form = VeiculoForm(instance=instancia)
    return render(
        request,
        "negocios/passo_carro_novo.html",
        {"negocio": negocio, "form": form, "titulo": "Qual carro o cliente deu?", "passo": 3},
    )


@login_required
def troca_valores(request, pk):
    negocio = _rascunho(pk)
    saida = _item_saida(negocio)
    entrada = _item_entrada(negocio)
    if not saida or not entrada:
        return redirect("negocios:troca_carro_loja", pk=negocio.pk)

    if request.method == "POST":
        form = TrocaValoresForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            saida.valor = d["valor_loja"]
            saida.km_entrega = d.get("km_loja")
            saida.save()
            entrada.valor = d["valor_cliente"]
            entrada.km_entrega = d.get("km_cliente")
            entrada.save()
            _salvar_pagamento_negocio(negocio, d, request.user)
            if "rascunho" in request.POST:
                return redirect("negocios:detalhe", pk=negocio.pk)
            return redirect("negocios:revisao", pk=negocio.pk)
    else:
        form = TrocaValoresForm(
            initial={
                "valor_loja": saida.valor or None,
                "valor_cliente": entrada.valor or None,
                "km_loja": saida.km_entrega,
                "km_cliente": entrada.km_entrega,
                "forma_pagamento": negocio.forma_pagamento,
                "detalhes_pagamento": negocio.detalhes_pagamento,
                "data": negocio.data,
                "data_hora_entrega": negocio.data_hora_entrega,
                "local_entrega": negocio.local_entrega,
            }
        )
    return render(
        request,
        "negocios/troca_valores.html",
        {"negocio": negocio, "form": form, "titulo": "Valores e pagamento", "passo": 4},
    )


# --- Revisão e conclusão ---


@login_required
def revisao(request, pk):
    negocio = _rascunho(pk)
    if request.method == "POST":
        try:
            concluir_negocio(negocio, usuario=request.user)
        except RegraNegocioError as erro:
            messages.error(request, str(erro))
            return redirect("negocios:revisao", pk=negocio.pk)
        rotulos = {
            TipoNegocio.VENDA: "Venda salva.",
            TipoNegocio.COMPRA: "Compra salva.",
            TipoNegocio.TROCA: "Troca salva.",
        }
        messages.success(request, rotulos[negocio.tipo])
        return redirect("negocios:detalhe", pk=negocio.pk)

    return render(
        request,
        "negocios/revisao.html",
        {
            "negocio": negocio,
            "itens": list(negocio.itens.select_related("veiculo", "de_pessoa", "para_pessoa")),
            "parte": _parte_principal(negocio),
            "diferenca": diferenca_troca(negocio) if negocio.tipo == TipoNegocio.TROCA else None,
            "passo": 5 if negocio.tipo == TipoNegocio.TROCA else 4,
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


# --- Consignação ---


@login_required
def consignar(request):
    if request.method == "POST":
        pessoa_form = EscolherPessoaForm(request.POST)
        veiculo_form = VeiculoForm(request.POST)
        termos_form = ConsignacaoTermosForm(request.POST)
        if pessoa_form.is_valid() and veiculo_form.is_valid() and termos_form.is_valid():
            dono = pessoa_form.resolver(usuario=request.user)
            veiculo = veiculo_form.save(commit=False)
            veiculo.criado_por = request.user
            veiculo.atualizado_por = request.user
            veiculo.save()
            t = termos_form.cleaned_data
            criar_consignacao(
                veiculo=veiculo,
                proprietario=dono,
                valor_liquido_minimo=t["valor_liquido_minimo"],
                comissao_tipo=t["comissao_tipo"],
                comissao_valor=t.get("comissao_valor"),
                prazo_dias=t["prazo_dias"],
                aviso_dias=t["aviso_dias"],
                prazo_repasse_dias=t["prazo_repasse_dias"],
                documentos_entregues=t.get("documentos_entregues", ""),
                usuario=request.user,
            )
            messages.success(request, "Carro recebido em consignação.")
            return redirect("veiculos:detalhe", pk=veiculo.pk)
    else:
        pessoa_form = EscolherPessoaForm()
        veiculo_form = VeiculoForm()
        termos_form = ConsignacaoTermosForm()
    return render(
        request,
        "negocios/consignar.html",
        {"pessoa_form": pessoa_form, "veiculo_form": veiculo_form, "termos_form": termos_form},
    )


# --- Venda de consignado (intermediação) ---


@login_required
def iniciar_consignado(request, consignacao_pk):
    consignacao = get_object_or_404(Consignacao.objetos, pk=consignacao_pk)
    if consignacao.status != StatusConsignacao.ATIVA:
        messages.error(request, "Essa consignação não está ativa.")
        return redirect("veiculos:detalhe", pk=consignacao.veiculo_id)

    negocio = Negocio.objetos.create(
        tipo=TipoNegocio.VENDA,
        modalidade=Modalidade.INTERMEDIACAO,
        consignacao=consignacao,
        status=StatusNegocio.RASCUNHO,
        criado_por=request.user,
        atualizado_por=request.user,
    )
    ParteNegocio.objetos.create(
        negocio=negocio, pessoa=consignacao.proprietario, papel=PapelParte.VENDEDOR
    )
    ItemNegocio.objetos.create(
        negocio=negocio,
        veiculo=consignacao.veiculo,
        de_pessoa=consignacao.proprietario,
        para_pessoa=None,
        valor=consignacao.veiculo.valor_anunciado or 0,
    )
    return redirect("negocios:consignado_comprador", pk=negocio.pk)


@login_required
def consignado_comprador(request, pk):
    negocio = _rascunho(pk)
    comprador = negocio.partes.filter(papel=PapelParte.COMPRADOR).first()
    item = _item_unico(negocio)
    if request.method == "POST":
        form = EscolherPessoaForm(request.POST)
        if form.is_valid():
            pessoa = form.resolver(usuario=request.user)
            ParteNegocio.objetos.update_or_create(
                negocio=negocio, papel=PapelParte.COMPRADOR, defaults={"pessoa": pessoa}
            )
            if item:
                item.para_pessoa = pessoa
                item.save()
            if "rascunho" in request.POST:
                return redirect("negocios:detalhe", pk=negocio.pk)
            return redirect("negocios:consignado_valores", pk=negocio.pk)
    else:
        form = EscolherPessoaForm(initial={"pessoa": comprador.pessoa if comprador else None})
    return render(
        request,
        "negocios/passo_pessoa.html",
        {"negocio": negocio, "form": form, "titulo": "Quem está comprando?", "passo": 1},
    )


@login_required
def consignado_valores(request, pk):
    negocio = _rascunho(pk)
    item = _item_unico(negocio)
    if not item:
        return redirect("negocios:detalhe", pk=negocio.pk)
    exige_quitacao = item.veiculo.alienado
    if request.method == "POST":
        form = PagamentoEntregaForm(request.POST, exige_quitacao=exige_quitacao)
        if form.is_valid():
            _salvar_pagamento_item(negocio, item, form.cleaned_data, request.user, exige_quitacao)
            if "rascunho" in request.POST:
                return redirect("negocios:detalhe", pk=negocio.pk)
            return redirect("negocios:revisao", pk=negocio.pk)
    else:
        form = PagamentoEntregaForm(
            exige_quitacao=exige_quitacao, initial=_inicial_pagamento(negocio, item)
        )
    return render(
        request,
        "negocios/passo_pagamento.html",
        {"negocio": negocio, "form": form, "titulo": "Valores, pagamento e entrega", "passo": 2},
    )


@login_required
@require_POST
def repasse(request, consignacao_pk):
    consignacao = get_object_or_404(Consignacao.objetos, pk=consignacao_pk)
    try:
        registrar_repasse(consignacao, usuario=request.user)
    except RegraNegocioError as erro:
        messages.error(request, str(erro))
        return redirect("veiculos:detalhe", pk=consignacao.veiculo_id)
    messages.success(request, "Repasse ao dono registrado.")
    return redirect("veiculos:detalhe", pk=consignacao.veiculo_id)


@login_required
@require_POST
def devolver(request, consignacao_pk):
    consignacao = get_object_or_404(Consignacao.objetos, pk=consignacao_pk)
    try:
        devolver_consignado(consignacao, usuario=request.user)
    except RegraNegocioError as erro:
        messages.error(request, str(erro))
        return redirect("veiculos:detalhe", pk=consignacao.veiculo_id)
    messages.success(request, "Carro devolvido ao dono.")
    return redirect("veiculos:detalhe", pk=consignacao.veiculo_id)
