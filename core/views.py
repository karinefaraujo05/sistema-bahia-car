from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from negocios.models import Negocio, StatusNegocio, TipoNegocio
from negocios.services import repasses_pendentes
from veiculos.models import Situacao, StatusVeiculo, Veiculo


@login_required
def inicio(request):
    """Tela inicial com um resumo simples e atalhos para as ações principais."""
    hoje = timezone.localdate()

    na_loja = (
        Veiculo.objetos.filter(status=StatusVeiculo.EM_ESTOQUE)
        .exclude(situacao=Situacao.TERCEIRO)
        .count()
    )
    vendas_no_mes = Negocio.objetos.filter(
        status=StatusNegocio.CONCLUIDO,
        tipo=TipoNegocio.VENDA,
        data__year=hoje.year,
        data__month=hoje.month,
    ).count()
    ultimos = Negocio.objetos.filter(status=StatusNegocio.CONCLUIDO)[:5]

    contexto = {
        "carros_na_loja": na_loja,
        "vendas_no_mes": vendas_no_mes,
        "repasses_pendentes": repasses_pendentes().count(),
        "ultimos_negocios": ultimos,
    }
    return render(request, "inicio.html", contexto)
