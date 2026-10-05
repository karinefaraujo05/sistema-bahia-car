from decimal import Decimal

import pytest

from negocios import services
from negocios.models import (
    ComissaoTipo,
    ItemNegocio,
    Modalidade,
    Negocio,
    PapelParte,
    ParteNegocio,
    QuitacaoOpcao,
    StatusConsignacao,
    StatusNegocio,
    TipoNegocio,
)
from negocios.services import RegraNegocioError
from pessoas.models import Pessoa
from veiculos.models import Situacao, StatusVeiculo, Veiculo

pytestmark = pytest.mark.django_db


# --- Fábricas simples ---


def pessoa(nome):
    return Pessoa.objetos.create(nome=nome)


def veiculo(placa, **kw):
    dados = {
        "placa": placa,
        "marca": "VW",
        "modelo": "Gol",
        "ano_fabricacao": 2015,
        "ano_modelo": 2016,
        "cor": "Prata",
    }
    dados.update(kw)
    return Veiculo.objetos.create(**dados)


def rascunho(tipo, modalidade=Modalidade.PROPRIA, **kw):
    return Negocio.objetos.create(
        tipo=tipo, modalidade=modalidade, status=StatusNegocio.RASCUNHO, **kw
    )


def item(negocio, v, valor, *, de=None, para=None, **kw):
    return ItemNegocio.objetos.create(
        negocio=negocio, veiculo=v, valor=Decimal(valor), de_pessoa=de, para_pessoa=para, **kw
    )


# --- Compra própria ---


def test_compra_poe_carro_no_estoque_com_valor_de_compra():
    vendedor = pessoa("João Vendedor")
    carro = veiculo("AAA1111")
    negocio = rascunho(TipoNegocio.COMPRA)
    item(negocio, carro, "20000", de=vendedor)

    services.concluir_negocio(negocio)
    carro.refresh_from_db()
    negocio.refresh_from_db()

    assert carro.situacao == Situacao.PROPRIO
    assert carro.status == StatusVeiculo.EM_ESTOQUE
    assert carro.valor_compra == Decimal("20000")
    assert negocio.numero_contrato == 1
    assert negocio.status == StatusNegocio.CONCLUIDO


# --- Venda própria ---


def test_venda_marca_carro_como_vendido():
    comprador = pessoa("Maria Compradora")
    carro = veiculo("BBB2222", valor_compra=Decimal("18000"))
    negocio = rascunho(TipoNegocio.VENDA)
    item(negocio, carro, "25000", para=comprador)

    services.concluir_negocio(negocio)
    carro.refresh_from_db()
    assert carro.status == StatusVeiculo.VENDIDO


def test_venda_bloqueia_carro_que_nao_e_proprio():
    comprador = pessoa("Maria")
    carro = veiculo("BBB2223", situacao=Situacao.CONSIGNADO)
    negocio = rascunho(TipoNegocio.VENDA)
    item(negocio, carro, "25000", para=comprador)
    with pytest.raises(RegraNegocioError):
        services.concluir_negocio(negocio)


# --- Troca própria ---


def test_troca_propria_vende_o_da_loja_e_poe_o_do_cliente_no_estoque():
    cliente = pessoa("Carlos Cliente")
    da_loja = veiculo("CCC3333")
    do_cliente = veiculo("DDD4444", situacao=Situacao.TERCEIRO)
    negocio = rascunho(TipoNegocio.TROCA)
    item(negocio, da_loja, "40000", para=cliente)
    item(negocio, do_cliente, "15000", de=cliente)

    services.concluir_negocio(negocio)
    da_loja.refresh_from_db()
    do_cliente.refresh_from_db()
    negocio.refresh_from_db()

    assert da_loja.status == StatusVeiculo.VENDIDO
    assert do_cliente.situacao == Situacao.PROPRIO
    assert do_cliente.status == StatusVeiculo.EM_ESTOQUE
    assert do_cliente.valor_compra == Decimal("15000")
    assert negocio.valor_total == Decimal("40000")
    assert services.diferenca_troca(negocio) == Decimal("25000")  # cliente paga


# --- Venda de consignado (intermediação) ---


def consignar(placa="EEE5555"):
    dono = pessoa("Dona do Carro")
    carro = veiculo(placa)
    consignacao = services.criar_consignacao(
        veiculo=carro,
        proprietario=dono,
        valor_liquido_minimo=Decimal("28000"),
        comissao_tipo=ComissaoTipo.PERCENTUAL,
        comissao_valor=Decimal("5"),
    )
    return consignacao, carro, dono


def test_venda_de_consignado_gera_pendencia_de_repasse():
    consignacao, carro, dono = consignar()
    carro.refresh_from_db()
    assert carro.situacao == Situacao.CONSIGNADO

    comprador = pessoa("Comprador")
    negocio = rascunho(
        TipoNegocio.VENDA, modalidade=Modalidade.INTERMEDIACAO, consignacao=consignacao
    )
    item(negocio, carro, "30000", de=dono, para=comprador)

    services.concluir_negocio(negocio)
    carro.refresh_from_db()
    consignacao.refresh_from_db()

    assert carro.status == StatusVeiculo.VENDIDO
    assert consignacao.status == StatusConsignacao.VENDIDA
    assert services.repasses_pendentes().filter(pk=consignacao.pk).exists()


def test_repasse_so_depois_da_venda_e_encerra():
    consignacao, carro, dono = consignar("EEE5556")
    with pytest.raises(RegraNegocioError):
        services.registrar_repasse(consignacao)  # ainda está ativa

    comprador = pessoa("Comprador")
    negocio = rascunho(
        TipoNegocio.VENDA, modalidade=Modalidade.INTERMEDIACAO, consignacao=consignacao
    )
    item(negocio, carro, "30000", de=dono, para=comprador)
    services.concluir_negocio(negocio)

    services.registrar_repasse(consignacao)
    consignacao.refresh_from_db()
    assert consignacao.status == StatusConsignacao.ENCERRADA
    assert consignacao.repasse_feito_em is not None
    assert not services.repasses_pendentes().filter(pk=consignacao.pk).exists()


def test_dono_retira_consignado():
    consignacao, carro, dono = consignar("EEE5557")
    services.devolver_consignado(consignacao)
    carro.refresh_from_db()
    consignacao.refresh_from_db()
    assert carro.status == StatusVeiculo.DEVOLVIDO
    assert consignacao.status == StatusConsignacao.ENCERRADA


# --- Troca entre particulares (intermediação) ---


def test_troca_entre_particulares_nao_mexe_no_estoque():
    p1 = pessoa("Particular 1")
    p2 = pessoa("Particular 2")
    carro1 = veiculo("FFF6666", situacao=Situacao.TERCEIRO, proprietario=p1)
    carro2 = veiculo("GGG7777", situacao=Situacao.TERCEIRO, proprietario=p2)
    negocio = rascunho(TipoNegocio.TROCA, modalidade=Modalidade.INTERMEDIACAO)
    item(negocio, carro1, "20000", de=p1, para=p2)
    item(negocio, carro2, "18000", de=p2, para=p1)

    services.concluir_negocio(negocio)
    carro1.refresh_from_db()
    carro2.refresh_from_db()
    assert carro1.situacao == Situacao.TERCEIRO
    assert carro2.situacao == Situacao.TERCEIRO
    assert carro1.status != StatusVeiculo.VENDIDO


# --- Carro alienado ---


def test_carro_alienado_bloqueia_sem_escolha_de_quitacao():
    comprador = pessoa("Comprador")
    carro = veiculo("HHH8888", alienado=True, credor_alienacao="Banco X")
    negocio = rascunho(TipoNegocio.VENDA)
    it = item(negocio, carro, "25000", para=comprador)

    with pytest.raises(RegraNegocioError):
        services.concluir_negocio(negocio)

    it.quitacao_opcao = QuitacaoOpcao.DESCONTA_PRECO
    it.save()
    services.concluir_negocio(negocio)  # agora passa
    carro.refresh_from_db()
    assert carro.status == StatusVeiculo.VENDIDO


# --- Proprietário registral diferente ---


def test_proprietario_registral_diferente_bloqueia_sem_anuente():
    vendedor = pessoa("João Vendedor")
    carro = veiculo("III9999", proprietario_registral="Pedro Dono Antigo")
    negocio = rascunho(TipoNegocio.COMPRA)
    item(negocio, carro, "20000", de=vendedor)

    with pytest.raises(RegraNegocioError):
        services.concluir_negocio(negocio)

    ParteNegocio.objetos.create(
        negocio=negocio, pessoa=pessoa("Pedro Dono Antigo"), papel=PapelParte.ANUENTE
    )
    services.concluir_negocio(negocio)  # com anuente, passa
    negocio.refresh_from_db()
    assert negocio.numero_contrato == 1


# --- Numeração sequencial ---


def test_numero_contrato_e_sequencial():
    v1 = veiculo("JJJ1010")
    v2 = veiculo("KKK1111")
    n1 = rascunho(TipoNegocio.COMPRA)
    item(n1, v1, "10000", de=pessoa("A"))
    n2 = rascunho(TipoNegocio.COMPRA)
    item(n2, v2, "12000", de=pessoa("B"))

    services.concluir_negocio(n1)
    services.concluir_negocio(n2)
    n1.refresh_from_db()
    n2.refresh_from_db()
    assert {n1.numero_contrato, n2.numero_contrato} == {1, 2}


# --- Cancelamento ---


def test_cancelar_venda_devolve_carro_ao_estoque():
    comprador = pessoa("Maria")
    carro = veiculo("LLL1212")
    negocio = rascunho(TipoNegocio.VENDA)
    item(negocio, carro, "25000", para=comprador)
    services.concluir_negocio(negocio)

    services.cancelar_negocio(negocio)
    carro.refresh_from_db()
    negocio.refresh_from_db()
    assert carro.status == StatusVeiculo.EM_ESTOQUE
    assert negocio.status == StatusNegocio.CANCELADO


def test_cancelar_compra_reverte_valor_de_compra():
    carro = veiculo("MMM1313")  # valor_compra começa None
    negocio = rascunho(TipoNegocio.COMPRA)
    item(negocio, carro, "20000", de=pessoa("Vendedor"))
    services.concluir_negocio(negocio)
    carro.refresh_from_db()
    assert carro.valor_compra == Decimal("20000")

    services.cancelar_negocio(negocio)
    carro.refresh_from_db()
    assert carro.valor_compra is None


def test_cancelar_troca_reverte_os_dois_carros():
    cliente = pessoa("Carlos")
    da_loja = veiculo("NNN1414")
    do_cliente = veiculo("OOO1515", situacao=Situacao.TERCEIRO)
    negocio = rascunho(TipoNegocio.TROCA)
    item(negocio, da_loja, "40000", para=cliente)
    item(negocio, do_cliente, "15000", de=cliente)
    services.concluir_negocio(negocio)

    services.cancelar_negocio(negocio)
    da_loja.refresh_from_db()
    do_cliente.refresh_from_db()
    assert da_loja.status == StatusVeiculo.EM_ESTOQUE
    assert do_cliente.situacao == Situacao.TERCEIRO
    assert do_cliente.valor_compra is None


def test_cancelar_venda_de_consignado_volta_consignacao_para_ativa():
    consignacao, carro, dono = consignar("PPP1616")
    comprador = pessoa("Comprador")
    negocio = rascunho(
        TipoNegocio.VENDA, modalidade=Modalidade.INTERMEDIACAO, consignacao=consignacao
    )
    item(negocio, carro, "30000", de=dono, para=comprador)
    services.concluir_negocio(negocio)

    services.cancelar_negocio(negocio)
    carro.refresh_from_db()
    consignacao.refresh_from_db()
    assert consignacao.status == StatusConsignacao.ATIVA
    assert carro.status == StatusVeiculo.EM_ESTOQUE
    assert not services.repasses_pendentes().filter(pk=consignacao.pk).exists()


def test_nao_cancela_rascunho():
    negocio = rascunho(TipoNegocio.COMPRA)
    with pytest.raises(RegraNegocioError):
        services.cancelar_negocio(negocio)
