from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from veiculos.models import Situacao, StatusVeiculo, Veiculo


@login_required
def inicio(request):
    """Tela inicial com um resumo simples e atalhos para as ações principais."""
    na_loja = (
        Veiculo.objetos.filter(status=StatusVeiculo.EM_ESTOQUE)
        .exclude(situacao=Situacao.TERCEIRO)
        .count()
    )
    contexto = {
        "carros_na_loja": na_loja,
    }
    return render(request, "inicio.html", contexto)
