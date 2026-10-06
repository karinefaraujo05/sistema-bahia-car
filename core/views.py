from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from negocios.models import Negocio, StatusNegocio, TipoNegocio
from negocios.services import repasses_pendentes
from veiculos.models import Situacao, StatusVeiculo, Veiculo

from .busca import buscar as buscar_tudo

MESES_ABREV = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def _vendas_por_mes(hoje):
    """Quantidade de vendas/trocas concluídas nos últimos 6 meses, para o gráfico."""
    pares = []
    ano, mes = hoje.year, hoje.month
    for _ in range(6):
        pares.append((ano, mes))
        mes -= 1
        if mes == 0:
            mes, ano = 12, ano - 1
    pares.reverse()

    dados = []
    for ano, mes in pares:
        quantidade = Negocio.objetos.filter(
            status=StatusNegocio.CONCLUIDO,
            tipo__in=[TipoNegocio.VENDA, TipoNegocio.TROCA],
            data__year=ano,
            data__month=mes,
        ).count()
        dados.append({"rotulo": MESES_ABREV[mes - 1], "valor": quantidade})

    maximo = max((d["valor"] for d in dados), default=0) or 1
    for d in dados:
        d["altura"] = round(d["valor"] / maximo * 100)
    return dados


@login_required
def inicio(request):
    """Painel inicial: indicadores, gráfico de vendas e atalhos."""
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

    contexto = {
        "carros_na_loja": na_loja,
        "vendas_no_mes": vendas_no_mes,
        "repasses_pendentes": repasses_pendentes().count(),
        "ultimos_negocios": Negocio.objetos.filter(status=StatusNegocio.CONCLUIDO)[:5],
        "grafico_vendas": _vendas_por_mes(hoje),
    }
    return render(request, "inicio.html", contexto)


@login_required
def buscar(request):
    resultado = buscar_tudo(request.GET.get("q", ""))
    if request.htmx:
        return render(request, "busca/resultados.html", resultado)
    return render(request, "busca/pagina.html", resultado)
