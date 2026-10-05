import io
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from contas.models import Usuario
from contratos.models import ConfiguracaoLoja, Documento
from contratos.services import DocumentoError, adicionar_documentos
from contratos.templatetags.contratos_extras import extenso, sim_nao
from negocios.models import Negocio, StatusNegocio, TipoNegocio

pytestmark = pytest.mark.django_db


def imagem(nome):
    buffer = io.BytesIO()
    Image.new("RGB", (400, 300), (10, 100, 120)).save(buffer, format="JPEG")
    buffer.seek(0)
    return SimpleUploadedFile(nome, buffer.read(), content_type="image/jpeg")


# --- Filtros ---


def test_extenso_reais():
    texto = extenso(Decimal("32000"))
    assert "trinta e dois mil" in texto
    assert "reais" in texto


def test_extenso_com_centavos():
    texto = extenso(Decimal("1234.56"))
    assert "cinquenta e seis centavos" in texto


def test_extenso_vazio():
    assert extenso(None) == ""


def test_sim_nao():
    assert sim_nao(True) == "Sim"
    assert sim_nao(False) == "Não"
    assert sim_nao(None) == "—"


# --- ConfiguracaoLoja ---


def test_configuracao_e_singleton():
    a = ConfiguracaoLoja.carregar()
    b = ConfiguracaoLoja.carregar()
    assert a.pk == 1 and b.pk == 1
    assert ConfiguracaoLoja.todos.count() == 1


def test_campos_faltando_quando_vazia():
    config = ConfiguracaoLoja.carregar()
    assert config.campos_faltando()  # lista não vazia
    assert not config.completa_para_contrato


def test_configuracao_completa():
    config = ConfiguracaoLoja.carregar()
    config.razao_social = "Bahia Car Veículos Ltda"
    config.cnpj = "11222333000181"
    config.endereco = "Rua X, 100"
    config.cidade = "Salvador"
    config.uf = "BA"
    config.representante_nome = "Fulano"
    config.representante_cpf = "11144477735"
    config.multa_percentual = Decimal("10")
    config.regra_ipva = "Proporcional até a entrega"
    config.numero_vias = 2
    config.save()
    assert config.completa_para_contrato


# --- Tela de configuração (só admin) ---


def test_config_bloqueia_vendedor(client):
    Usuario.objects.create_user(username="vend", password="x-123456", papel=Usuario.Papel.VENDEDOR)
    client.login(username="vend", password="x-123456")
    resp = client.get(reverse("contratos:configuracao"))
    assert resp.status_code == 302  # redirecionado para o início


def test_config_abre_para_admin(client):
    Usuario.objects.create_user(
        username="chefe", password="x-123456", papel=Usuario.Papel.ADMINISTRADOR
    )
    client.login(username="chefe", password="x-123456")
    assert client.get(reverse("contratos:configuracao")).status_code == 200


# --- Documentos ---


def _negocio():
    return Negocio.objetos.create(tipo=TipoNegocio.VENDA, status=StatusNegocio.RASCUNHO)


def test_varias_imagens_viram_um_pdf(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    negocio = _negocio()
    docs = adicionar_documentos(
        negocio=negocio,
        tipo="contrato",
        arquivos=[imagem("1.jpg"), imagem("2.jpg")],
        juntar_pdf=True,
    )
    assert len(docs) == 1
    assert docs[0].arquivo.name.endswith(".pdf")


def test_sem_juntar_gera_um_por_arquivo(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    negocio = _negocio()
    docs = adicionar_documentos(
        negocio=negocio,
        tipo="contrato",
        arquivos=[imagem("1.jpg"), imagem("2.jpg")],
        juntar_pdf=False,
    )
    assert len(docs) == 2


def test_upload_grande_demais(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    settings.TAMANHO_MAXIMO_UPLOAD_MB = 0  # força o limite
    negocio = _negocio()
    with pytest.raises(DocumentoError):
        adicionar_documentos(negocio=negocio, tipo="contrato", arquivos=[imagem("1.jpg")])


def test_upload_pela_tela(client, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    Usuario.objects.create_user(username="karine", password="x-123456")
    client.login(username="karine", password="x-123456")
    negocio = _negocio()

    resp = client.post(
        reverse("contratos:upload_documentos", args=[negocio.pk]),
        {"tipo": "contrato", "juntar_pdf": "on", "arquivos": [imagem("c.jpg")]},
    )
    assert resp.status_code == 302
    assert Documento.objetos.filter(negocio=negocio).count() == 1
