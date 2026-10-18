import io
import zipfile

import pytest
from django.urls import reverse

from contas.models import Usuario
from core.busca import buscar
from pessoas.models import Pessoa
from veiculos.models import Situacao, StatusVeiculo, Veiculo

pytestmark = pytest.mark.django_db


def _carro(placa, **kw):
    dados = {
        "placa": placa,
        "marca": "Volkswagen",
        "modelo": "Gol 1.0",
        "ano_fabricacao": 2015,
        "ano_modelo": 2016,
        "cor": "Prata",
    }
    dados.update(kw)
    return Veiculo.objetos.create(**dados)


def test_busca_placa_ignora_hifen_e_caixa():
    carro = _carro("ABC1D23")
    assert carro in buscar("abc1d23")["carros"]
    assert carro in buscar("ABC-1D23")["carros"]
    assert carro in buscar("abc 1d23")["carros"]


def test_busca_nome_ignora_acento():
    joao = Pessoa.objetos.create(nome="João Silva")
    assert joao in buscar("joao")["pessoas"]
    assert joao in buscar("JOAO")["pessoas"]


def test_busca_cpf_ignora_pontuacao():
    pessoa = Pessoa.objetos.create(nome="Carlos", cpf_cnpj="12345678909")
    assert pessoa in buscar("123.456")["pessoas"]


def test_busca_marca_e_modelo():
    carro = _carro("XYZ4321")
    assert carro in buscar("gol")["carros"]
    assert carro in buscar("volksw")["carros"]


def test_busca_esconde_terceiro():
    carro = _carro("TTT0000", situacao=Situacao.TERCEIRO)
    assert carro not in buscar("TTT0000")["carros"]


def test_busca_vazia_nao_quebra():
    resultado = buscar("")
    assert resultado["carros"] == []
    assert resultado["pessoas"] == []


def test_view_de_busca(client):
    Usuario.objects.create_user(username="karine", password="segredo-123")
    client.login(username="karine", password="segredo-123")
    _carro("ABC1D23")
    resp = client.get(reverse("buscar"), {"q": "abc1d23"})
    assert resp.status_code == 200
    assert "ABC1D23" in resp.content.decode()


# --- App no celular (PWA) ---


def test_manifest_abre_com_icone():
    from django.test import Client

    resp = Client().get(reverse("manifest"))
    assert resp.status_code == 200
    assert "icon-192" in resp.content.decode()


def test_service_worker_abre():
    from django.test import Client

    resp = Client().get(reverse("service_worker"))
    assert resp.status_code == 200
    assert resp["Content-Type"].startswith("application/javascript")


# --- Backup ---


def test_backup_so_para_superusuario(client):
    Usuario.objects.create_user(username="vendedor", password="x-123456")
    client.login(username="vendedor", password="x-123456")
    assert client.get(reverse("backup")).status_code == 403


def test_backup_gera_zip_com_dados(client):
    Usuario.objects.create_superuser(username="dono", password="x-123456")
    client.login(username="dono", password="x-123456")
    resp = client.get(reverse("backup"))
    assert resp.status_code == 200
    assert resp["Content-Type"] == "application/zip"
    dados = b"".join(resp.streaming_content)
    zf = zipfile.ZipFile(io.BytesIO(dados))
    assert "dados.json" in zf.namelist()


# --- Multi-empresa: isolamento de dados ---


def test_dados_sao_separados_por_empresa():
    from contas.models import Empresa
    from core.tenancy import limpar_empresa_atual, set_empresa_atual
    from veiculos.models import Veiculo

    a = Empresa.objects.create(nome="Empresa A")
    b = Empresa.objects.create(nome="Empresa B")

    set_empresa_atual(a)
    try:
        Veiculo.objetos.create(
            placa="AAA1A11", marca="X", modelo="Y",
            ano_fabricacao=2020, ano_modelo=2021, cor="Preto",
        )
        assert Veiculo.objetos.count() == 1  # a empresa A vê o próprio carro
    finally:
        limpar_empresa_atual()

    set_empresa_atual(b)
    try:
        assert Veiculo.objetos.count() == 0  # a empresa B NÃO vê o carro da A
    finally:
        limpar_empresa_atual()


# --- Consulta FIPE ---


def test_fipe_exige_login(client):
    assert client.get(reverse("fipe") + "?q=marcas&tipo=carros").status_code == 302


def test_fipe_rejeita_tipo_invalido(client):
    Usuario.objects.create_user(username="k", password="x-123456")
    client.login(username="k", password="x-123456")
    resp = client.get(reverse("fipe") + "?q=marcas&tipo=aviao")
    assert resp.status_code == 400


def test_pagina_consulta_abre(client):
    Usuario.objects.create_user(username="k", password="x-123456")
    client.login(username="k", password="x-123456")
    assert client.get(reverse("consulta")).status_code == 200


def test_cnpj_rejeita_numero_invalido(client):
    Usuario.objects.create_user(username="k2", password="x-123456")
    client.login(username="k2", password="x-123456")
    assert client.get(reverse("cnpj") + "?cnpj=123").status_code == 400


# --- Painel inicial (indicadores) ---


def _entrar_como_dono(client):
    Usuario.objects.create_superuser(username="dono", password="x-123456")
    client.login(username="dono", password="x-123456")


def test_painel_vendas_no_mes_conta_venda_e_troca(client):
    # Item 2.1: o número de "vendas no mês" conta VENDA e TROCA (igual ao gráfico).
    from negocios.models import Negocio, StatusNegocio, TipoNegocio

    Negocio.objetos.create(tipo=TipoNegocio.VENDA, status=StatusNegocio.CONCLUIDO)
    Negocio.objetos.create(tipo=TipoNegocio.TROCA, status=StatusNegocio.CONCLUIDO)
    Negocio.objetos.create(tipo=TipoNegocio.COMPRA, status=StatusNegocio.CONCLUIDO)
    _entrar_como_dono(client)
    resp = client.get(reverse("inicio"))
    assert resp.context["vendas_no_mes"] == 2  # venda + troca; compra não entra


def test_painel_valor_estoque_soma_so_proprios_em_estoque(client):
    # Item 2.2: valor em estoque soma valor_compra só dos carros PRÓPRIOS em estoque.
    _carro("AAA1A11", situacao=Situacao.PROPRIO, valor_compra=30000)
    _carro("BBB2B22", situacao=Situacao.PROPRIO, valor_compra=20000)
    _carro("CCC3C33", situacao=Situacao.CONSIGNADO, valor_compra=50000)  # não é da loja
    _carro("DDD4D44", situacao=Situacao.PROPRIO, valor_compra=99000,
           status=StatusVeiculo.VENDIDO)  # já saiu do estoque
    _entrar_como_dono(client)
    resp = client.get(reverse("inicio"))
    assert resp.context["valor_estoque"] == 50000  # 30000 + 20000


def test_painel_conta_carros_de_terceiros(client):
    # Item 2.2: consignados e de terceiros contam como "carros de terceiros na loja".
    _carro("EEE5E55", situacao=Situacao.PROPRIO)
    _carro("FFF6F66", situacao=Situacao.CONSIGNADO)
    _carro("GGG7G77", situacao=Situacao.TERCEIRO)
    _entrar_como_dono(client)
    resp = client.get(reverse("inicio"))
    assert resp.context["carros_terceiros"] == 2  # consignado + terceiro


def test_painel_lucro_do_mes_escondido_do_vendedor(client):
    # Item 2.3: lucro do mês é número sensível; vendedor não vê.
    Usuario.objects.create_user(username="vend", password="x-123456")  # papel padrão: vendedor
    client.login(username="vend", password="x-123456")
    resp = client.get(reverse("inicio"))
    assert resp.context["eh_admin"] is False
    assert resp.context["lucro_do_mes"] is None
    assert "lucro do mês" not in resp.content.decode().lower()


def test_painel_lucro_do_mes_visivel_para_admin(client):
    # Item 2.3: administrador vê o lucro do mês no painel.
    _entrar_como_dono(client)
    resp = client.get(reverse("inicio"))
    assert resp.context["eh_admin"] is True
    assert resp.context["lucro_do_mes"] is not None
    assert "lucro do mês" in resp.content.decode().lower()


def _carro_parado(placa, dias):
    # criado_em é auto_now_add; update() escreve o valor direto (não dispara auto_now).
    from datetime import timedelta

    from django.utils import timezone

    v = _carro(placa)
    Veiculo.objetos.filter(pk=v.pk).update(criado_em=timezone.now() - timedelta(days=dias))
    return v


def test_painel_carros_parados_mostra_3_mais_antigos(client):
    # Item 2.4: card lista os 3 carros parados há mais de 60 dias, do mais antigo pro menos.
    _carro_parado("AAA1111", 70)
    _carro_parado("BBB2222", 120)
    _carro_parado("CCC3333", 90)
    _carro_parado("DDD4444", 65)
    _carro("EEE5555")  # recém-chegado: não está parado
    _entrar_como_dono(client)
    resp = client.get(reverse("inicio"))
    assert resp.context["total_parados"] == 4
    placas = [v.placa for v in resp.context["carros_parados"]]
    assert placas == ["BBB2222", "CCC3333", "AAA1111"]  # 120, 90, 70 dias


def test_painel_carros_parados_ignora_menos_de_60_dias(client):
    # Carro com 60 dias exatos não entra (regra é "mais de 60").
    _carro_parado("FFF6666", 60)
    _entrar_como_dono(client)
    resp = client.get(reverse("inicio"))
    assert resp.context["total_parados"] == 0
