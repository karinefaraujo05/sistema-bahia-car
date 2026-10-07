import io
import zipfile

import pytest
from django.urls import reverse

from contas.models import Usuario
from core.busca import buscar
from pessoas.models import Pessoa
from veiculos.models import Situacao, Veiculo

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
