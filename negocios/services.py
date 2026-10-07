"""
Regras de negócio de compra, venda, troca e consignação.

Toda conclusão e todo cancelamento mexem no status de veículos (e de consignações)
dentro de uma transação, para nunca deixar o banco num estado pela metade.
Nada é apagado: cancelar reverte os status e marca o negócio como cancelado.
"""

from decimal import Decimal

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from core.tenancy import empresa_atual
from veiculos.models import Situacao, StatusVeiculo

from .models import (
    Consignacao,
    Modalidade,
    Negocio,
    PapelParte,
    StatusConsignacao,
    StatusNegocio,
    TipoNegocio,
)


class RegraNegocioError(Exception):
    """Erro de regra de negócio, com mensagem em linguagem simples para a tela."""


def _proximo_numero(modelo):
    # Numeração sequencial por empresa (cada loja começa do 1).
    qs = modelo.todos
    empresa = empresa_atual()
    if empresa is not None:
        qs = qs.filter(empresa=empresa)
    ultimo = qs.aggregate(maior=Max("numero_contrato"))["maior"] or 0
    return ultimo + 1


# ---------------------------------------------------------------------------
# Cálculos
# ---------------------------------------------------------------------------


def calcular_valor_total(negocio, itens):
    if not itens:
        return Decimal("0")
    if negocio.tipo == TipoNegocio.TROCA:
        if negocio.modalidade == Modalidade.PROPRIA:
            return sum((i.valor for i in itens if i.sai_da_loja), Decimal("0"))
        return max(i.valor for i in itens)
    return sum((i.valor for i in itens), Decimal("0"))


def diferenca_troca(negocio):
    """Positivo: o cliente paga a diferença. Negativo: a loja paga."""
    itens = list(negocio.itens.all())
    saida = sum((i.valor for i in itens if i.sai_da_loja), Decimal("0"))
    entrada = sum((i.valor for i in itens if i.entra_na_loja), Decimal("0"))
    return saida - entrada


# ---------------------------------------------------------------------------
# Validações
# ---------------------------------------------------------------------------


def _validar_estrutura(negocio, itens):
    for item in itens:
        if item.sai_da_loja and item.entra_na_loja:
            raise RegraNegocioError("Um carro não pode sair e entrar na loja ao mesmo tempo.")

    if negocio.modalidade == Modalidade.PROPRIA:
        _validar_propria(negocio, itens)
    else:
        _validar_intermediacao(negocio, itens)


def _validar_propria(negocio, itens):
    if negocio.tipo == TipoNegocio.COMPRA:
        if len(itens) != 1 or not itens[0].entra_na_loja or itens[0].sai_da_loja:
            raise RegraNegocioError("Na compra, um carro vem de um particular para a loja.")
    elif negocio.tipo == TipoNegocio.VENDA:
        if len(itens) != 1 or not itens[0].sai_da_loja or itens[0].entra_na_loja:
            raise RegraNegocioError("Na venda, um carro sai da loja para o cliente.")
        _exigir_carro_vendavel(itens[0].veiculo)
    elif negocio.tipo == TipoNegocio.TROCA:
        saidas = [i for i in itens if i.sai_da_loja]
        entradas = [i for i in itens if i.entra_na_loja]
        if len(saidas) != 1:
            raise RegraNegocioError("A troca deve ter exatamente um carro saindo da loja.")
        if not entradas:
            raise RegraNegocioError("A troca precisa de ao menos um carro entrando na loja.")
        _exigir_carro_vendavel(saidas[0].veiculo)


def _validar_intermediacao(negocio, itens):
    for item in itens:
        if item.sai_da_loja or item.entra_na_loja:
            raise RegraNegocioError(
                "Na intermediação a loja não é dona: todo carro vai de uma pessoa para outra."
            )
    if negocio.consignacao_id:
        if negocio.consignacao.status != StatusConsignacao.ATIVA:
            raise RegraNegocioError("A consignação precisa estar ativa para vender o carro.")
        consignado = negocio.consignacao.veiculo_id
        if not any(i.veiculo_id == consignado for i in itens):
            raise RegraNegocioError("O carro da consignação não está neste negócio.")


def _exigir_carro_vendavel(veiculo):
    if veiculo.situacao != Situacao.PROPRIO:
        raise RegraNegocioError(
            "Aqui só vende carro da loja. Para consignado, use a intermediação."
        )
    if veiculo.status not in (StatusVeiculo.EM_ESTOQUE, StatusVeiculo.RESERVADO):
        raise RegraNegocioError("O carro precisa estar na loja ou reservado para ser vendido.")


def _validar_alienacao(itens):
    for item in itens:
        if item.veiculo.alienado and not item.quitacao_opcao:
            raise RegraNegocioError(
                f"O carro {item.veiculo.placa_formatada} tem financiamento ativo. "
                "Escolha como fica a quitação."
            )


def _validar_autorizacao(negocio, itens):
    tem_anuente = negocio.partes.filter(papel=PapelParte.ANUENTE).exists()
    for item in itens:
        if item.de_pessoa_id is None:
            continue  # quem entrega é a loja
        registral = (item.veiculo.proprietario_registral or "").strip().lower()
        entregador = item.de_pessoa.nome.strip().lower()
        if registral and registral != entregador and not tem_anuente:
            # A checagem de documento_autorizacao anexado entra na Fase 5.
            raise RegraNegocioError(
                f"O carro {item.veiculo.placa_formatada} está em nome de "
                f"{item.veiculo.proprietario_registral}, diferente de quem está entregando. "
                "Inclua o proprietário como anuente ou anexe a autorização."
            )


# ---------------------------------------------------------------------------
# Conclusão
# ---------------------------------------------------------------------------


def _snapshot(item):
    item.status_anterior = item.veiculo.status
    item.situacao_anterior = item.veiculo.situacao
    item.valor_compra_anterior = item.veiculo.valor_compra
    item.save(update_fields=["status_anterior", "situacao_anterior", "valor_compra_anterior"])


def _virar_proprio_em_estoque(veiculo, valor, usuario):
    veiculo.situacao = Situacao.PROPRIO
    veiculo.proprietario = None
    veiculo.status = StatusVeiculo.EM_ESTOQUE
    veiculo.valor_compra = valor
    veiculo.atualizado_por = usuario
    veiculo.save()


def _vender(veiculo, usuario):
    veiculo.status = StatusVeiculo.VENDIDO
    veiculo.atualizado_por = usuario
    veiculo.save()


def _aplicar_transicoes(negocio, itens, usuario):
    for item in itens:
        _snapshot(item)

    if negocio.modalidade == Modalidade.PROPRIA:
        if negocio.tipo == TipoNegocio.COMPRA:
            item = itens[0]
            _virar_proprio_em_estoque(item.veiculo, item.valor, usuario)
        elif negocio.tipo == TipoNegocio.VENDA:
            _vender(itens[0].veiculo, usuario)
        elif negocio.tipo == TipoNegocio.TROCA:
            for item in itens:
                if item.sai_da_loja:
                    _vender(item.veiculo, usuario)
                else:
                    _virar_proprio_em_estoque(item.veiculo, item.valor, usuario)
    else:  # intermediação
        if negocio.consignacao_id:
            consignado = negocio.consignacao.veiculo
            _vender(consignado, usuario)
            negocio.consignacao.status = StatusConsignacao.VENDIDA
            negocio.consignacao.atualizado_por = usuario
            negocio.consignacao.save()
        # Entre particulares (carros de terceiro): não mexe no estoque.


@transaction.atomic
def concluir_negocio(negocio, *, usuario=None):
    if negocio.status == StatusNegocio.CONCLUIDO:
        raise RegraNegocioError("Este negócio já está concluído.")

    itens = list(negocio.itens.select_related("veiculo", "de_pessoa", "para_pessoa"))
    if not itens:
        raise RegraNegocioError("Adicione ao menos um carro ao negócio.")

    _validar_estrutura(negocio, itens)
    _validar_alienacao(itens)
    _validar_autorizacao(negocio, itens)

    _aplicar_transicoes(negocio, itens, usuario)

    negocio.numero_contrato = _proximo_numero(Negocio)
    negocio.valor_total = calcular_valor_total(negocio, itens)
    if not negocio.data:
        negocio.data = timezone.localdate()
    negocio.status = StatusNegocio.CONCLUIDO
    negocio.atualizado_por = usuario
    negocio.save()
    return negocio


@transaction.atomic
def cancelar_negocio(negocio, *, usuario=None):
    if negocio.status != StatusNegocio.CONCLUIDO:
        raise RegraNegocioError("Só dá para cancelar um negócio concluído.")

    for item in negocio.itens.select_related("veiculo"):
        veiculo = item.veiculo
        if item.status_anterior:
            veiculo.status = item.status_anterior
        if item.situacao_anterior:
            veiculo.situacao = item.situacao_anterior
        veiculo.valor_compra = item.valor_compra_anterior
        veiculo.atualizado_por = usuario
        veiculo.save()

    if negocio.consignacao_id:
        consignacao = negocio.consignacao
        consignacao.status = StatusConsignacao.ATIVA
        consignacao.repasse_feito_em = None
        consignacao.atualizado_por = usuario
        consignacao.save()

    negocio.status = StatusNegocio.CANCELADO
    negocio.atualizado_por = usuario
    negocio.save(update_fields=["status", "atualizado_por", "atualizado_em"])
    return negocio


# ---------------------------------------------------------------------------
# Consignação
# ---------------------------------------------------------------------------


@transaction.atomic
def criar_consignacao(
    *,
    veiculo,
    proprietario,
    valor_liquido_minimo,
    comissao_tipo,
    comissao_valor=None,
    prazo_dias=90,
    aviso_dias=15,
    prazo_repasse_dias=5,
    documentos_entregues="",
    data_entrada=None,
    usuario=None,
):
    from .models import ComissaoTipo

    if comissao_tipo != ComissaoTipo.SOBREPRECO and comissao_valor is None:
        raise RegraNegocioError("Informe o valor da comissão.")

    consignacao = Consignacao(
        veiculo=veiculo,
        proprietario=proprietario,
        valor_liquido_minimo=valor_liquido_minimo,
        comissao_tipo=comissao_tipo,
        comissao_valor=comissao_valor,
        prazo_dias=prazo_dias,
        aviso_dias=aviso_dias,
        prazo_repasse_dias=prazo_repasse_dias,
        documentos_entregues=documentos_entregues,
        data_entrada=data_entrada or timezone.localdate(),
        status=StatusConsignacao.ATIVA,
        criado_por=usuario,
        atualizado_por=usuario,
    )
    consignacao.numero_contrato = _proximo_numero(Consignacao)
    consignacao.save()

    veiculo.situacao = Situacao.CONSIGNADO
    veiculo.proprietario = proprietario
    veiculo.status = StatusVeiculo.EM_ESTOQUE
    veiculo.atualizado_por = usuario
    veiculo.save()
    return consignacao


@transaction.atomic
def registrar_repasse(consignacao, *, data=None, usuario=None):
    if consignacao.status != StatusConsignacao.VENDIDA:
        raise RegraNegocioError("O repasse ao dono é feito depois da venda do carro consignado.")
    consignacao.repasse_feito_em = data or timezone.localdate()
    consignacao.status = StatusConsignacao.ENCERRADA
    consignacao.atualizado_por = usuario
    consignacao.save()
    return consignacao


@transaction.atomic
def devolver_consignado(consignacao, *, usuario=None):
    """O dono retirou o carro antes de vender."""
    if consignacao.status == StatusConsignacao.VENDIDA:
        raise RegraNegocioError("Esse carro já foi vendido; não dá para devolver ao dono.")
    consignacao.status = StatusConsignacao.ENCERRADA
    consignacao.atualizado_por = usuario
    consignacao.save()

    veiculo = consignacao.veiculo
    veiculo.status = StatusVeiculo.DEVOLVIDO
    veiculo.atualizado_por = usuario
    veiculo.save()
    return consignacao


def repasses_pendentes():
    """Consignações vendidas cujo dono ainda não recebeu."""
    return Consignacao.objetos.filter(
        status=StatusConsignacao.VENDIDA, repasse_feito_em__isnull=True
    )


# ---------------------------------------------------------------------------
# Lucro e vendas (números sensíveis: só o administrador vê)
# ---------------------------------------------------------------------------


def lucro_bruto(negocio):
    """
    Lucro bruto de um negócio concluído:
    - venda própria: preço de venda menos valor de compra;
    - troca própria: preço do carro da loja menos o valor de compra dele;
    - intermediação: a comissão da loja;
    - compra: não há lucro (é aquisição).
    Devolve None quando não dá para calcular (ex.: falta o valor de compra).
    """
    if negocio.status != StatusNegocio.CONCLUIDO:
        return None
    if negocio.modalidade == Modalidade.INTERMEDIACAO:
        return negocio.comissao_valor or Decimal("0")

    itens = list(negocio.itens.select_related("veiculo"))
    if negocio.tipo == TipoNegocio.VENDA and itens:
        item = itens[0]
        if item.veiculo.valor_compra is None:
            return None
        return item.valor - item.veiculo.valor_compra
    if negocio.tipo == TipoNegocio.TROCA:
        saida = next((i for i in itens if i.sai_da_loja), None)
        if not saida or saida.veiculo.valor_compra is None:
            return None
        return saida.valor - saida.veiculo.valor_compra
    return None


def lucro_do_veiculo(veiculo):
    """Lucro do veículo quando já foi vendido pela loja (None caso contrário)."""
    item = (
        veiculo.itens_negocio.filter(
            de_pessoa__isnull=True,
            negocio__status=StatusNegocio.CONCLUIDO,
            negocio__tipo__in=[TipoNegocio.VENDA, TipoNegocio.TROCA],
        )
        .select_related("negocio")
        .order_by("-negocio__data")
        .first()
    )
    if not item or veiculo.valor_compra is None:
        return None
    return item.valor - veiculo.valor_compra


def resumo_de_vendas(ano, mes):
    """Total vendido e lucro bruto das vendas e trocas concluídas no mês."""
    vendas = Negocio.objetos.filter(
        status=StatusNegocio.CONCLUIDO,
        tipo__in=[TipoNegocio.VENDA, TipoNegocio.TROCA],
        data__year=ano,
        data__month=mes,
    )
    total = sum((n.valor_total or Decimal("0") for n in vendas), Decimal("0"))
    lucro = sum((lucro_bruto(n) or Decimal("0") for n in vendas), Decimal("0"))
    return {"total_vendido": total, "lucro_bruto": lucro, "quantidade": vendas.count()}
