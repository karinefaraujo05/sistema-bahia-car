from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import PessoaForm, PessoaRapidaForm
from .models import Pessoa
from .services import arquivar_pessoa, buscar_pessoas
from .validators import so_digitos

POR_PAGINA = 50


def _querystring_sem_pagina(request):
    """Querystring atual sem 'page', pronta pra concatenar page=N (termina em '&' ou vazia)."""
    params = request.GET.copy()
    params.pop("page", None)
    qs = params.urlencode()
    return f"{qs}&" if qs else ""


def _redirecionar_com_pessoa(request, pessoa, proximo):
    """Volta pro negócio (com a pessoa já selecionada) ou pro detalhe dela."""
    if proximo and url_has_allowed_host_and_scheme(proximo, allowed_hosts={request.get_host()}):
        separador = "&" if "?" in proximo else "?"
        return redirect(f"{proximo}{separador}selecionar={pessoa.pk}")
    return redirect("pessoas:detalhe", pk=pessoa.pk)


@login_required
def lista(request):
    termo = request.GET.get("q", "")
    paginador = Paginator(buscar_pessoas(termo), POR_PAGINA)
    page_obj = paginador.get_page(request.GET.get("page"))
    return render(
        request,
        "pessoas/lista.html",
        {
            "pessoas": page_obj,
            "page_obj": page_obj,
            "querystring": _querystring_sem_pagina(request),
            "termo": termo,
        },
    )


@login_required
def detalhe(request, pk):
    pessoa = get_object_or_404(Pessoa.objetos, pk=pk)
    return render(request, "pessoas/detalhe.html", {"pessoa": pessoa})


@login_required
def novo(request):
    # "next" (quando veio de um negócio): ao salvar, volta pra lá já com a pessoa escolhida.
    proximo = request.GET.get("next", "")
    if request.method == "POST":
        form = PessoaForm(request.POST)
        if form.is_valid():
            pessoa = form.save(commit=False)
            pessoa.criado_por = request.user
            pessoa.atualizado_por = request.user
            pessoa.save()
            messages.success(request, "Pessoa cadastrada.")
            return _redirecionar_com_pessoa(request, pessoa, proximo)
    else:
        form = PessoaForm()
    return render(
        request, "pessoas/form.html", {"form": form, "pessoa": None, "proximo": proximo}
    )


@login_required
def novo_rapido(request):
    proximo = request.GET.get("next", "")
    if request.method == "POST":
        form = PessoaRapidaForm(request.POST)
        if form.is_valid():
            documento = form.cleaned_data["cpf_cnpj"]
            # Já existe alguém com esse CPF/CNPJ? Em vez de duplicar, abre a pessoa existente.
            existente = Pessoa.objetos.filter(cpf_cnpj=documento).first() if documento else None
            if existente:
                messages.info(request, "Essa pessoa já estava cadastrada. Abrimos o cadastro dela.")
                return _redirecionar_com_pessoa(request, existente, proximo)
            pessoa = form.save(commit=False)
            pessoa.criado_por = request.user
            pessoa.atualizado_por = request.user
            pessoa.save()
            messages.success(request, "Pessoa cadastrada. Você pode completar os dados depois.")
            return _redirecionar_com_pessoa(request, pessoa, proximo)
    else:
        form = PessoaRapidaForm()
    return render(request, "pessoas/form_rapido.html", {"form": form, "proximo": proximo})


@login_required
def editar(request, pk):
    # "next": permite "completar agora" dentro do negócio e voltar pra ele já com a pessoa.
    proximo = request.GET.get("next", "")
    pessoa = get_object_or_404(Pessoa.objetos, pk=pk)
    if request.method == "POST":
        form = PessoaForm(request.POST, instance=pessoa)
        if form.is_valid():
            pessoa = form.save(commit=False)
            pessoa.atualizado_por = request.user
            pessoa.save()
            messages.success(request, "Dados atualizados.")
            return _redirecionar_com_pessoa(request, pessoa, proximo)
    else:
        form = PessoaForm(instance=pessoa)
    return render(
        request, "pessoas/form.html", {"form": form, "pessoa": pessoa, "proximo": proximo}
    )


@login_required
@require_POST
def ler_documento(request):
    """Lê a foto do documento da pessoa (CNH/RG) com IA e devolve os campos."""
    from core.ocr_ia import ler_documento as ler
    from core.ocr_ia import provedor_ativo

    if provedor_ativo() != "claude":
        return JsonResponse({"ativo": False})
    arquivo = request.FILES.get("documento")
    dados = ler(arquivo, "pessoa") if arquivo else None
    if not dados:
        return JsonResponse({"ativo": True, "ok": False})
    return JsonResponse({"ativo": True, "ok": True, "dados": dados})


@login_required
def buscar_cpf(request):
    """Procura uma pessoa pelo CPF/CNPJ (usado no cadastro, pra não duplicar)."""
    documento = so_digitos(request.GET.get("cpf", ""))
    if len(documento) not in (11, 14):
        return JsonResponse({"encontrado": False})
    pessoa = Pessoa.objetos.filter(cpf_cnpj=documento).first()
    if pessoa is None:
        return JsonResponse({"encontrado": False})
    return JsonResponse(
        {
            "encontrado": True,
            "nome": pessoa.nome,
            "url": reverse("pessoas:detalhe", args=[pessoa.pk]),
        }
    )


@login_required
@require_POST
def arquivar(request, pk):
    # Só o responsável (superusuário) pode arquivar pessoas.
    if not request.user.is_superuser:
        messages.error(request, "Só o responsável pode arquivar uma pessoa.")
        return redirect("pessoas:detalhe", pk=pk)
    pessoa = get_object_or_404(Pessoa.objetos, pk=pk)
    arquivar_pessoa(pessoa, usuario=request.user)
    messages.success(request, "Pessoa arquivada. Nada é apagado.")
    return redirect("pessoas:lista")
