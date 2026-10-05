from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from contas.models import Usuario
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


# --- Fluxos pelas telas (wizard) ---


def logar(client):
    Usuario.objects.create_user(username="karine", password="segredo-123")
    client.login(username="karine", password="segredo-123")


def ultimo_negocio():
    return Negocio.todos.latest("criado_em")


def test_fluxo_de_venda_pelas_telas(client):
    logar(client)
    comprador_existente = pessoa("Maria Compradora")
    carro = veiculo("QQQ1717")

    client.get(reverse("negocios:iniciar", args=["venda"]))
    negocio = ultimo_negocio()

    client.post(
        reverse("negocios:passo_pessoa", args=[negocio.pk]), {"pessoa": comprador_existente.pk}
    )
    client.post(reverse("negocios:passo_carro", args=[negocio.pk]), {"veiculo": carro.pk})
    client.post(
        reverse("negocios:passo_pagamento", args=[negocio.pk]),
        {"valor": "32000", "data": "2026-10-05"},
    )
    resp = client.post(reverse("negocios:revisao", args=[negocio.pk]))
    assert resp.status_code == 302

    negocio.refresh_from_db()
    carro.refresh_from_db()
    assert negocio.status == StatusNegocio.CONCLUIDO
    assert negocio.valor_total == Decimal("32000")
    assert carro.status == StatusVeiculo.VENDIDO


def test_fluxo_de_compra_cadastrando_carro_e_pessoa(client):
    logar(client)

    client.get(reverse("negocios:iniciar", args=["compra"]))
    negocio = ultimo_negocio()

    client.post(
        reverse("negocios:passo_pessoa", args=[negocio.pk]),
        {"nome_novo": "Vendedor Novo", "telefone_novo": "71999990000"},
    )
    client.post(
        reverse("negocios:passo_carro", args=[negocio.pk]),
        {
            "placa": "RRR1818",
            "marca": "Fiat",
            "modelo": "Uno",
            "ano_fabricacao": "2012",
            "ano_modelo": "2013",
            "cor": "Branco",
            "situacao": Situacao.PROPRIO,
            "status": StatusVeiculo.EM_ESTOQUE,
        },
    )
    client.post(
        reverse("negocios:passo_pagamento", args=[negocio.pk]),
        {"valor": "20000", "data": "2026-10-05"},
    )
    client.post(reverse("negocios:revisao", args=[negocio.pk]))

    negocio.refresh_from_db()
    assert negocio.status == StatusNegocio.CONCLUIDO
    carro = Veiculo.objetos.get(placa="RRR1818")
    assert carro.situacao == Situacao.PROPRIO
    assert carro.valor_compra == Decimal("20000")


def test_cancelar_pela_tela(client):
    logar(client)
    comprador = pessoa("Maria")
    carro = veiculo("SSS1919")
    negocio = rascunho(TipoNegocio.VENDA)
    item(negocio, carro, "25000", para=comprador)
    services.concluir_negocio(negocio)

    # Página de confirmação abre e o POST cancela.
    assert (
        client.get(reverse("negocios:confirmar_cancelamento", args=[negocio.pk])).status_code == 200
    )
    resp = client.post(reverse("negocios:cancelar", args=[negocio.pk]))
    assert resp.status_code == 302
    negocio.refresh_from_db()
    carro.refresh_from_db()
    assert negocio.status == StatusNegocio.CANCELADO
    assert carro.status == StatusVeiculo.EM_ESTOQUE


def test_detalhe_do_negocio_abre(client):
    logar(client)
    comprador = pessoa("Maria")
    carro = veiculo("TTT2020")
    negocio = rascunho(TipoNegocio.VENDA)
    item(negocio, carro, "25000", para=comprador)
    services.concluir_negocio(negocio)
    assert client.get(reverse("negocios:detalhe", args=[negocio.pk])).status_code == 200


def _dados_veiculo(placa, **extra):
    dados = {
        "placa": placa,
        "marca": "Fiat",
        "modelo": "Uno",
        "ano_fabricacao": "2012",
        "ano_modelo": "2013",
        "cor": "Branco",
        "situacao": Situacao.PROPRIO,
        "status": StatusVeiculo.EM_ESTOQUE,
    }
    dados.update(extra)
    return dados


def test_fluxo_de_troca_pelas_telas(client):
    logar(client)
    da_loja = veiculo("UUU2121")

    client.get(reverse("negocios:iniciar", args=["troca"]))
    negocio = ultimo_negocio()

    client.post(
        reverse("negocios:passo_pessoa", args=[negocio.pk]),
        {"nome_novo": "Cliente Troca", "telefone_novo": ""},
    )
    client.post(reverse("negocios:troca_carro_loja", args=[negocio.pk]), {"veiculo": da_loja.pk})
    client.post(
        reverse("negocios:troca_carro_cliente", args=[negocio.pk]), _dados_veiculo("VVV2222")
    )
    client.post(
        reverse("negocios:troca_valores", args=[negocio.pk]),
        {"valor_loja": "40000", "valor_cliente": "15000", "data": "2026-10-05"},
    )
    client.post(reverse("negocios:revisao", args=[negocio.pk]))

    negocio.refresh_from_db()
    da_loja.refresh_from_db()
    do_cliente = Veiculo.objetos.get(placa="VVV2222")
    assert negocio.status == StatusNegocio.CONCLUIDO
    assert da_loja.status == StatusVeiculo.VENDIDO
    assert do_cliente.situacao == Situacao.PROPRIO
    assert do_cliente.valor_compra == Decimal("15000")


def test_consignacao_pela_tela(client):
    logar(client)
    dados = {
        "nome_novo": "Dono Consignante",
        "telefone_novo": "71988887777",
        **_dados_veiculo("WWW2323"),
        "valor_liquido_minimo": "28000",
        "comissao_tipo": ComissaoTipo.PERCENTUAL,
        "comissao_valor": "5",
        "prazo_dias": "90",
        "aviso_dias": "15",
        "prazo_repasse_dias": "5",
        "documentos_entregues": "CRLV e chave reserva",
    }
    resp = client.post(reverse("negocios:consignar"), dados)
    assert resp.status_code == 302
    carro = Veiculo.objetos.get(placa="WWW2323")
    assert carro.situacao == Situacao.CONSIGNADO
    assert carro.consignacoes.first().status == StatusConsignacao.ATIVA


def test_venda_de_consignado_e_repasse_pelas_telas(client):
    logar(client)
    consignacao, carro, dono = consignar("XXX2424")

    client.get(reverse("negocios:iniciar_consignado", args=[consignacao.pk]))
    negocio = ultimo_negocio()
    client.post(
        reverse("negocios:consignado_comprador", args=[negocio.pk]),
        {"nome_novo": "Comprador Final", "telefone_novo": ""},
    )
    client.post(
        reverse("negocios:consignado_valores", args=[negocio.pk]),
        {"valor": "30000", "data": "2026-10-05"},
    )
    client.post(reverse("negocios:revisao", args=[negocio.pk]))

    carro.refresh_from_db()
    consignacao.refresh_from_db()
    assert carro.status == StatusVeiculo.VENDIDO
    assert consignacao.status == StatusConsignacao.VENDIDA

    # Repasse ao dono pela tela.
    client.post(reverse("negocios:repasse", args=[consignacao.pk]))
    consignacao.refresh_from_db()
    assert consignacao.status == StatusConsignacao.ENCERRADA
    assert consignacao.repasse_feito_em is not None


def test_devolver_consignado_pela_tela(client):
    logar(client)
    consignacao, carro, dono = consignar("YYY2525")
    client.post(reverse("negocios:devolver", args=[consignacao.pk]))
    carro.refresh_from_db()
    consignacao.refresh_from_db()
    assert carro.status == StatusVeiculo.DEVOLVIDO
    assert consignacao.status == StatusConsignacao.ENCERRADA


def test_paginas_novas_renderizam_em_get(client):
    logar(client)
    # Página de consignação (três formulários).
    assert client.get(reverse("negocios:consignar")).status_code == 200

    # Passo de valores da troca precisa dos dois carros no rascunho.
    cliente = pessoa("Cliente")
    negocio = rascunho(TipoNegocio.TROCA)
    ParteNegocio.objetos.create(negocio=negocio, pessoa=cliente, papel=PapelParte.PERMUTANTE)
    item(negocio, veiculo("ZZZ2626"), "40000", para=cliente)
    item(negocio, veiculo("ZZZ2627", situacao=Situacao.TERCEIRO), "15000", de=cliente)
    assert client.get(reverse("negocios:troca_valores", args=[negocio.pk])).status_code == 200
    assert client.get(reverse("negocios:revisao", args=[negocio.pk])).status_code == 200


# --- Lucro, vendas e papéis (Fase 7) ---


def _venda_concluida(placa="LLL3030", compra="18000", venda="25000"):
    carro = veiculo(placa, valor_compra=Decimal(compra))
    comprador = pessoa("Comprador Lucro")
    negocio = rascunho(TipoNegocio.VENDA)
    item(negocio, carro, venda, para=comprador)
    services.concluir_negocio(negocio)
    return negocio, carro


def test_lucro_bruto_da_venda():
    negocio, _ = _venda_concluida()
    assert services.lucro_bruto(negocio) == Decimal("7000")


def test_lucro_do_veiculo():
    _, carro = _venda_concluida("LLL3031")
    carro.refresh_from_db()
    assert services.lucro_do_veiculo(carro) == Decimal("7000")


def test_resumo_de_vendas_do_mes():
    _venda_concluida("LLL3032")
    hoje = timezone.localdate()
    resumo = services.resumo_de_vendas(hoje.year, hoje.month)
    assert resumo["total_vendido"] == Decimal("25000")
    assert resumo["lucro_bruto"] == Decimal("7000")
    assert resumo["quantidade"] == 1


def test_vendas_lucro_so_para_admin(client):
    _venda_concluida("LLL3033")

    Usuario.objects.create_user(username="vend", password="x-123456", papel=Usuario.Papel.VENDEDOR)
    client.login(username="vend", password="x-123456")
    conteudo_vendedor = client.get(reverse("negocios:vendas")).content.decode().lower()
    assert "lucro" not in conteudo_vendedor

    client.logout()
    Usuario.objects.create_user(
        username="chefe", password="x-123456", papel=Usuario.Papel.ADMINISTRADOR
    )
    client.login(username="chefe", password="x-123456")
    conteudo_admin = client.get(reverse("negocios:vendas")).content.decode().lower()
    assert "lucro" in conteudo_admin


def test_exportar_bloqueia_vendedor(client):
    Usuario.objects.create_user(username="vend", password="x-123456", papel=Usuario.Papel.VENDEDOR)
    client.login(username="vend", password="x-123456")
    resp = client.get(reverse("negocios:exportar_excel"))
    assert resp.status_code == 302  # redirecionado


def test_exportar_admin_gera_xlsx(client):
    _venda_concluida("LLL3034")
    Usuario.objects.create_user(
        username="chefe", password="x-123456", papel=Usuario.Papel.ADMINISTRADOR
    )
    client.login(username="chefe", password="x-123456")
    resp = client.get(reverse("negocios:exportar_excel"))
    assert resp.status_code == 200
    assert resp.content[:2] == b"PK"  # xlsx é um zip
