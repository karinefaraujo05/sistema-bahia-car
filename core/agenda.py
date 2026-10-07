"""
Agenda de pendências: cada lembrete já aponta pro lugar exato de resolver
(a ficha daquele carro, aquele negócio). Usado na tela inicial e na Agenda.
"""

from datetime import timedelta

from django.urls import reverse

from negocios.models import (
    Consignacao,
    Negocio,
    StatusConsignacao,
    StatusNegocio,
)
from negocios.services import repasses_pendentes
from veiculos.models import Situacao, StatusVeiculo, Veiculo

DIAS_CARRO_PARADO = 90
RASCUNHO_ANTIGO_DIAS = 2

PESO_NIVEL = {"atrasado": 0, "atencao": 1, "neutro": 2}


def _nome_carro(veiculo):
    nome = f"{veiculo.marca} {veiculo.modelo}".strip()
    return nome or veiculo.placa


def _vence_em(dias):
    if dias <= 0:
        return "Vence hoje"
    if dias == 1:
        return "Vence amanhã"
    return f"Vence em {dias} dias"


def lembretes(hoje):
    """Lista de pendências ordenada por urgência; cada item leva pro lugar certo."""
    itens = []

    # Repasses a pagar: dinheiro do dono de um consignado já vendido.
    for c in repasses_pendentes().select_related("veiculo", "proprietario"):
        itens.append(
            {
                "nivel": "atrasado",
                "categoria": "repasse",
                "titulo": f"Repassar ao dono: {_nome_carro(c.veiculo)}",
                "detalhe": f"{c.proprietario.nome} está esperando o repasse da venda.",
                "url": reverse("veiculos:detalhe", args=[c.veiculo_id]),
                "ordem": -100,
            }
        )

    # Consignações ativas: vencidas ou perto do prazo.
    ativas = Consignacao.objetos.filter(status=StatusConsignacao.ATIVA).select_related(
        "veiculo", "proprietario"
    )
    for c in ativas:
        vence = c.data_entrada + timedelta(days=c.prazo_dias)
        dias = (vence - hoje).days
        if dias < 0:
            itens.append(
                {
                    "nivel": "atrasado",
                    "categoria": "consignacao",
                    "titulo": f"Consignação vencida: {_nome_carro(c.veiculo)}",
                    "detalhe": f"O prazo com {c.proprietario.nome} acabou. Renovar ou devolver.",
                    "url": reverse("veiculos:detalhe", args=[c.veiculo_id]),
                    "ordem": dias,
                }
            )
        elif dias <= c.aviso_dias:
            itens.append(
                {
                    "nivel": "atencao",
                    "categoria": "consignacao",
                    "titulo": f"Consignação perto do prazo: {_nome_carro(c.veiculo)}",
                    "detalhe": f"{_vence_em(dias)} · dono: {c.proprietario.nome}.",
                    "url": reverse("veiculos:detalhe", args=[c.veiculo_id]),
                    "ordem": dias,
                }
            )

    # Carros próprios parados há muito tempo.
    proprios = Veiculo.objetos.filter(status=StatusVeiculo.EM_ESTOQUE).exclude(
        situacao=Situacao.TERCEIRO
    )
    for v in proprios:
        if v.dias_na_loja > DIAS_CARRO_PARADO:
            itens.append(
                {
                    "nivel": "neutro",
                    "categoria": "parado",
                    "titulo": f"{_nome_carro(v)} parado há {v.dias_na_loja} dias",
                    "detalhe": "Pensar em baixar o preço ou anunciar de novo.",
                    "url": reverse("veiculos:detalhe", args=[v.pk]),
                    "ordem": 1000 - v.dias_na_loja,
                }
            )

    # Negócios começados e não terminados.
    limite = hoje - timedelta(days=RASCUNHO_ANTIGO_DIAS)
    rascunhos = Negocio.objetos.filter(
        status=StatusNegocio.RASCUNHO, criado_em__date__lte=limite
    )
    for n in rascunhos:
        itens.append(
            {
                "nivel": "neutro",
                "categoria": "rascunho",
                "titulo": f"Negócio não terminado: {n.get_tipo_display()}",
                "detalhe": "Você começou e não concluiu. Terminar ou cancelar.",
                "url": reverse("negocios:detalhe", args=[n.pk]),
                "ordem": 2000,
            }
        )

    itens.sort(key=lambda i: (PESO_NIVEL[i["nivel"]], i["ordem"]))
    return itens
