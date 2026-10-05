from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import PessoaForm, PessoaRapidaForm
from .models import Pessoa
from .services import arquivar_pessoa, buscar_pessoas


@login_required
def lista(request):
    termo = request.GET.get("q", "")
    pessoas = buscar_pessoas(termo)
    return render(request, "pessoas/lista.html", {"pessoas": pessoas, "termo": termo})


@login_required
def detalhe(request, pk):
    pessoa = get_object_or_404(Pessoa.objetos, pk=pk)
    return render(request, "pessoas/detalhe.html", {"pessoa": pessoa})


@login_required
def novo(request):
    if request.method == "POST":
        form = PessoaForm(request.POST)
        if form.is_valid():
            pessoa = form.save(commit=False)
            pessoa.criado_por = request.user
            pessoa.atualizado_por = request.user
            pessoa.save()
            messages.success(request, "Pessoa cadastrada.")
            return redirect("pessoas:detalhe", pk=pessoa.pk)
    else:
        form = PessoaForm()
    return render(request, "pessoas/form.html", {"form": form, "pessoa": None})


@login_required
def novo_rapido(request):
    if request.method == "POST":
        form = PessoaRapidaForm(request.POST)
        if form.is_valid():
            pessoa = form.save(commit=False)
            pessoa.criado_por = request.user
            pessoa.atualizado_por = request.user
            pessoa.save()
            messages.success(request, "Pessoa cadastrada. Você pode completar os dados depois.")
            return redirect("pessoas:detalhe", pk=pessoa.pk)
    else:
        form = PessoaRapidaForm()
    return render(request, "pessoas/form_rapido.html", {"form": form})


@login_required
def editar(request, pk):
    pessoa = get_object_or_404(Pessoa.objetos, pk=pk)
    if request.method == "POST":
        form = PessoaForm(request.POST, instance=pessoa)
        if form.is_valid():
            pessoa = form.save(commit=False)
            pessoa.atualizado_por = request.user
            pessoa.save()
            messages.success(request, "Dados atualizados.")
            return redirect("pessoas:detalhe", pk=pessoa.pk)
    else:
        form = PessoaForm(instance=pessoa)
    return render(request, "pessoas/form.html", {"form": form, "pessoa": pessoa})


@login_required
@require_POST
def arquivar(request, pk):
    pessoa = get_object_or_404(Pessoa.objetos, pk=pk)
    arquivar_pessoa(pessoa, usuario=request.user)
    messages.success(request, "Pessoa arquivada. Nada é apagado.")
    return redirect("pessoas:lista")
