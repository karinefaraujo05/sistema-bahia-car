import io

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.urls import reverse
from PIL import Image

from contas.models import Usuario
from veiculos import services
from veiculos.models import FotoVeiculo, Situacao, StatusVeiculo, Veiculo
from veiculos.validators import (
    normalizar_placa,
    placa_formatada,
    validar_chassi,
    validar_placa,
    validar_renavam,
)

CAMPOS_MINIMOS = {
    "placa": "ABC1234",
    "marca": "VW",
    "modelo": "Gol 1.0",
    "ano_fabricacao": 2015,
    "ano_modelo": 2016,
    "cor": "Prata",
}


def criar_veiculo(**kwargs):
    dados = {**CAMPOS_MINIMOS, **kwargs}
    return Veiculo.objetos.create(**dados)


def imagem_em_memoria(nome="foto.jpg", tamanho=(3000, 2000)):
    buffer = io.BytesIO()
    Image.new("RGB", tamanho, (20, 100, 120)).save(buffer, format="JPEG")
    buffer.seek(0)
    return SimpleUploadedFile(nome, buffer.read(), content_type="image/jpeg")


# --- Validação e normalização de placa ---


def test_normalizar_placa_tira_hifen_e_maiuscula():
    assert normalizar_placa("abc-1d23") == "ABC1D23"
    assert normalizar_placa(" abc 1234 ") == "ABC1234"


def test_validar_placa_aceita_antiga_e_mercosul():
    validar_placa("ABC1234")
    validar_placa("abc1d23")  # normaliza antes de validar


def test_validar_placa_rejeita_invalida():
    with pytest.raises(ValidationError):
        validar_placa("12345")


def test_placa_formatada_coloca_hifen_na_antiga():
    assert placa_formatada("ABC1234") == "ABC-1234"
    assert placa_formatada("ABC1D23") == "ABC1D23"


# --- Validação de chassi e renavam ---


def test_chassi_valido_e_invalido():
    validar_chassi("9BWZZZ377VT004251")  # 17 caracteres, sem I/O/Q
    with pytest.raises(ValidationError):
        validar_chassi("9BWZZZ377VT00425I")  # contém I
    with pytest.raises(ValidationError):
        validar_chassi("123")  # curto demais


def test_renavam_valido_e_invalido():
    validar_renavam("12345678901")
    with pytest.raises(ValidationError):
        validar_renavam("123")


# --- Modelo Veiculo ---


@pytest.mark.django_db
def test_placa_e_salva_normalizada():
    veiculo = criar_veiculo(placa="abc-1234")
    assert veiculo.placa == "ABC1234"
    assert veiculo.placa_formatada == "ABC-1234"


@pytest.mark.django_db
def test_placa_unica_entre_nao_arquivados():
    criar_veiculo(placa="ABC1234")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            criar_veiculo(placa="ABC1234")


@pytest.mark.django_db
def test_arquivar_libera_a_placa():
    primeiro = criar_veiculo(placa="ABC1234")
    primeiro.arquivar()
    # Agora a mesma placa pode ser cadastrada de novo.
    segundo = criar_veiculo(placa="ABC1234")
    assert segundo.pk != primeiro.pk


# --- Fotos: capa e redimensionamento ---


@pytest.mark.django_db
def test_primeira_foto_vira_capa(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    veiculo = criar_veiculo()
    foto1 = services.adicionar_foto(veiculo, imagem_em_memoria("1.jpg"))
    foto2 = services.adicionar_foto(veiculo, imagem_em_memoria("2.jpg"))
    foto1.refresh_from_db()
    foto2.refresh_from_db()
    assert foto1.capa is True
    assert foto2.capa is False


@pytest.mark.django_db
def test_definir_capa_troca_a_capa(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    veiculo = criar_veiculo()
    foto1 = services.adicionar_foto(veiculo, imagem_em_memoria("1.jpg"))
    foto2 = services.adicionar_foto(veiculo, imagem_em_memoria("2.jpg"))
    services.definir_capa(foto2)
    foto1.refresh_from_db()
    foto2.refresh_from_db()
    assert foto2.capa is True
    assert foto1.capa is False
    # Só uma capa entre as não arquivadas.
    assert FotoVeiculo.objetos.filter(veiculo=veiculo, capa=True).count() == 1


@pytest.mark.django_db
def test_foto_e_redimensionada(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    veiculo = criar_veiculo()
    foto = services.adicionar_foto(veiculo, imagem_em_memoria("grande.jpg", tamanho=(3000, 2000)))
    grande = Image.open(foto.imagem.path)
    mini = Image.open(foto.miniatura.path)
    assert max(grande.size) <= services.LADO_MAXIMO
    assert max(mini.size) <= services.LADO_MINIATURA


@pytest.mark.django_db
def test_remover_foto_promove_outra_a_capa(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    veiculo = criar_veiculo()
    foto1 = services.adicionar_foto(veiculo, imagem_em_memoria("1.jpg"))
    foto2 = services.adicionar_foto(veiculo, imagem_em_memoria("2.jpg"))
    services.remover_foto(foto1)
    foto2.refresh_from_db()
    assert foto2.capa is True
    # A foto removida está arquivada, não apagada.
    assert FotoVeiculo.todos.filter(pk=foto1.pk, arquivado=True).exists()


# --- Consulta de estoque ---


@pytest.mark.django_db
def test_estoque_filtra_por_origem_e_esconde_terceiro():
    criar_veiculo(placa="AAA1111", situacao=Situacao.PROPRIO)
    criar_veiculo(placa="BBB2222", situacao=Situacao.CONSIGNADO)
    criar_veiculo(placa="CCC3333", situacao=Situacao.TERCEIRO)

    todos = services.consultar_estoque(status=StatusVeiculo.EM_ESTOQUE, origem="todos")
    assert todos.count() == 2  # terceiro nunca aparece

    loja = services.consultar_estoque(status=StatusVeiculo.EM_ESTOQUE, origem="loja")
    assert [v.placa for v in loja] == ["AAA1111"]

    consignados = services.consultar_estoque(status=StatusVeiculo.EM_ESTOQUE, origem="consignados")
    assert [v.placa for v in consignados] == ["BBB2222"]


@pytest.mark.django_db
def test_arquivar_veiculo_tira_do_estoque():
    veiculo = criar_veiculo()
    services.arquivar_veiculo(veiculo)
    assert services.consultar_estoque(status=StatusVeiculo.EM_ESTOQUE).count() == 0


# --- Views ---


@pytest.mark.django_db
def test_estoque_exige_login(client):
    resp = client.get(reverse("veiculos:estoque"))
    assert resp.status_code == 302


@pytest.mark.django_db
def test_cadastro_pelo_formulario_aparece_no_estoque(client, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    Usuario.objects.create_user(username="karine", password="segredo-123")
    client.login(username="karine", password="segredo-123")

    dados = {
        **CAMPOS_MINIMOS,
        "situacao": Situacao.PROPRIO,
        "status": StatusVeiculo.EM_ESTOQUE,
        "valor_anunciado": "32000.00",
        "fotos": imagem_em_memoria("carro.jpg"),
    }
    resp = client.post(reverse("veiculos:novo"), dados)
    assert resp.status_code == 302

    veiculo = Veiculo.objetos.get(placa="ABC1234")
    assert veiculo.fotos.count() == 1

    estoque = client.get(reverse("veiculos:estoque"))
    assert "Gol" in estoque.content.decode()


@pytest.mark.django_db
def test_tela_de_cadastro_abre(client):
    Usuario.objects.create_user(username="karine", password="segredo-123")
    client.login(username="karine", password="segredo-123")
    assert client.get(reverse("veiculos:novo")).status_code == 200


@pytest.mark.django_db
def test_tela_de_detalhe_abre(client, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    Usuario.objects.create_user(username="karine", password="segredo-123")
    client.login(username="karine", password="segredo-123")
    veiculo = criar_veiculo()
    services.adicionar_foto(veiculo, imagem_em_memoria("1.jpg"))
    resp = client.get(reverse("veiculos:detalhe", args=[veiculo.pk]))
    assert resp.status_code == 200
    assert "Gol" in resp.content.decode()
