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


# --- Geração de contratos ---

from contratos.geracao import (  # noqa: E402
    ContratoError,
    escolher_modelo,
    gerar_contrato,
    gerar_contrato_consignacao,
    renderizar_docx,
    renderizar_pdf,
)
from contratos.models import ModeloContrato  # noqa: E402
from negocios.models import (  # noqa: E402
    ComissaoTipo,
    Consignacao,
    ItemNegocio,
    Modalidade,
    PapelParte,
    ParteNegocio,
    StatusConsignacao,
)
from pessoas.models import Pessoa, TipoPessoa  # noqa: E402
from veiculos.models import Situacao, Veiculo  # noqa: E402

CPF_A = "11144477735"
CPF_B = "52998224725"


def loja_completa():
    c = ConfiguracaoLoja.carregar()
    c.razao_social = "Bahia Car Veículos Ltda"
    c.cnpj = "11222333000181"
    c.endereco = "Rua das Flores, 1"
    c.cidade = "Salvador"
    c.uf = "BA"
    c.cep = "40000000"
    c.representante_nome = "Gerente da Loja"
    c.representante_cpf = CPF_A
    c.multa_percentual = Decimal("10")
    c.regra_ipva = "Proporcional até a entrega"
    c.numero_vias = 2
    c.save()
    return c


def pessoa_completa(nome, cpf):
    return Pessoa.objetos.create(
        nome=nome,
        tipo=TipoPessoa.FISICA,
        cpf_cnpj=cpf,
        endereco="Rua Y, 2",
        cidade="Salvador",
        uf="BA",
        cep="40000000",
        nacionalidade="brasileiro(a)",
        estado_civil="solteiro(a)",
        profissao="autônomo(a)",
    )


def veiculo_completo(placa, **kw):
    dados = {
        "placa": placa,
        "marca": "VW",
        "modelo": "Gol 1.0",
        "ano_fabricacao": 2015,
        "ano_modelo": 2016,
        "cor": "Prata",
        "chassi": "9BWZZZ377VT004251",
        "renavam": "12345678901",
    }
    dados.update(kw)
    return Veiculo.objetos.create(**dados)


def test_escolher_modelo():
    def n(tipo, modalidade):
        return Negocio.objetos.create(
            tipo=tipo, modalidade=modalidade, status=StatusNegocio.RASCUNHO
        )

    assert escolher_modelo(n(TipoNegocio.COMPRA, Modalidade.PROPRIA)) == ModeloContrato.A
    assert escolher_modelo(n(TipoNegocio.VENDA, Modalidade.PROPRIA)) == ModeloContrato.B
    assert escolher_modelo(n(TipoNegocio.TROCA, Modalidade.PROPRIA)) == ModeloContrato.C
    assert escolher_modelo(n(TipoNegocio.VENDA, Modalidade.INTERMEDIACAO)) == ModeloContrato.E


def test_gerar_bloqueia_sem_dados():
    comprador = Pessoa.objetos.create(nome="Sem dados")  # sem CPF/endereço
    carro = Veiculo.objetos.create(
        placa="AAA1234", marca="VW", modelo="Gol", ano_fabricacao=2015, ano_modelo=2016, cor="Prata"
    )
    negocio = Negocio.objetos.create(tipo=TipoNegocio.VENDA, status=StatusNegocio.RASCUNHO)
    ParteNegocio.objetos.create(negocio=negocio, pessoa=comprador, papel=PapelParte.COMPRADOR)
    ItemNegocio.objetos.create(
        negocio=negocio, veiculo=carro, para_pessoa=comprador, valor=Decimal("1")
    )
    with pytest.raises(ContratoError) as erro:
        gerar_contrato(negocio)
    assert erro.value.faltando  # tem lista do que falta


def test_gerar_venda_preenche_texto():
    loja_completa()
    comprador = pessoa_completa("João Silva", CPF_A)
    carro = veiculo_completo("ABC1D23")
    negocio = Negocio.objetos.create(
        tipo=TipoNegocio.VENDA, status=StatusNegocio.RASCUNHO, numero_contrato=1
    )
    ParteNegocio.objetos.create(negocio=negocio, pessoa=comprador, papel=PapelParte.COMPRADOR)
    ItemNegocio.objetos.create(
        negocio=negocio,
        veiculo=carro,
        para_pessoa=comprador,
        valor=Decimal("32000"),
        km_entrega=50000,
    )

    contrato = gerar_contrato(negocio)
    assert contrato.modelo == ModeloContrato.B
    assert "COMPRA E VENDA" in contrato.corpo
    assert "João Silva" in contrato.corpo
    assert "trinta e dois mil reais" in contrato.corpo

    # Regerar cria nova versão, mantém a anterior.
    contrato2 = gerar_contrato(negocio)
    assert contrato2.versao == 2
    assert negocio.contratos.count() == 2


def test_gerar_compra_troca_intermediacao():
    loja_completa()
    # Compra (A)
    vend = pessoa_completa("Vendedor", CPF_A)
    carro_a = veiculo_completo("AAA1111")
    na = Negocio.objetos.create(tipo=TipoNegocio.COMPRA, status=StatusNegocio.RASCUNHO)
    ParteNegocio.objetos.create(negocio=na, pessoa=vend, papel=PapelParte.VENDEDOR)
    ItemNegocio.objetos.create(negocio=na, veiculo=carro_a, de_pessoa=vend, valor=Decimal("20000"))
    assert gerar_contrato(na).modelo == ModeloContrato.A

    # Troca (C)
    cli = pessoa_completa("Cliente Troca", CPF_B)
    loja_carro = veiculo_completo("BBB2222")
    cli_carro = veiculo_completo("CCC3333", situacao=Situacao.TERCEIRO)
    nc = Negocio.objetos.create(tipo=TipoNegocio.TROCA, status=StatusNegocio.RASCUNHO)
    ParteNegocio.objetos.create(negocio=nc, pessoa=cli, papel=PapelParte.PERMUTANTE)
    ItemNegocio.objetos.create(
        negocio=nc, veiculo=loja_carro, para_pessoa=cli, valor=Decimal("40000")
    )
    ItemNegocio.objetos.create(negocio=nc, veiculo=cli_carro, de_pessoa=cli, valor=Decimal("15000"))
    contrato_c = gerar_contrato(nc)
    assert contrato_c.modelo == ModeloContrato.C
    assert "PERMUTA" in contrato_c.corpo


def test_gerar_consignacao_modelo_d():
    loja_completa()
    dono = pessoa_completa("Dona", CPF_A)
    carro = veiculo_completo("DDD4444")
    consignacao = Consignacao.objetos.create(
        veiculo=carro,
        proprietario=dono,
        numero_contrato=1,
        valor_liquido_minimo=Decimal("28000"),
        comissao_tipo=ComissaoTipo.PERCENTUAL,
        comissao_valor=Decimal("5"),
        status=StatusConsignacao.ATIVA,
    )
    contrato = gerar_contrato_consignacao(consignacao)
    assert contrato.modelo == ModeloContrato.D
    assert "CONSIGNAÇÃO" in contrato.corpo
    assert "Dona" in contrato.corpo


def test_pdf_e_docx(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    loja_completa()
    comprador = pessoa_completa("João Silva", CPF_A)
    carro = veiculo_completo("ABC1D23")
    negocio = Negocio.objetos.create(
        tipo=TipoNegocio.VENDA, status=StatusNegocio.RASCUNHO, numero_contrato=1
    )
    ParteNegocio.objetos.create(negocio=negocio, pessoa=comprador, papel=PapelParte.COMPRADOR)
    ItemNegocio.objetos.create(
        negocio=negocio, veiculo=carro, para_pessoa=comprador, valor=Decimal("32000")
    )
    contrato = gerar_contrato(negocio)

    pdf = renderizar_pdf(contrato)
    assert pdf[:4] == b"%PDF"
    docx = renderizar_docx(contrato)
    assert docx[:2] == b"PK"  # arquivo .docx é um zip


def _venda_completa():
    loja_completa()
    comprador = pessoa_completa("João Silva", CPF_A)
    carro = veiculo_completo("ABC1D23")
    negocio = Negocio.objetos.create(
        tipo=TipoNegocio.VENDA, status=StatusNegocio.RASCUNHO, numero_contrato=1
    )
    ParteNegocio.objetos.create(negocio=negocio, pessoa=comprador, papel=PapelParte.COMPRADOR)
    ItemNegocio.objetos.create(
        negocio=negocio, veiculo=carro, para_pessoa=comprador, valor=Decimal("32000")
    )
    return negocio


def test_fluxo_de_contrato_pelas_telas(client, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    Usuario.objects.create_user(username="karine", password="x-123456")
    client.login(username="karine", password="x-123456")
    negocio = _venda_completa()

    # Gerar → redireciona para a edição.
    resp = client.post(reverse("contratos:gerar", args=[negocio.pk]))
    assert resp.status_code == 302
    contrato = negocio.contratos.first()

    # Tela de edição abre; salvar altera o corpo.
    assert client.get(reverse("contratos:editar_contrato", args=[contrato.pk])).status_code == 200
    client.post(
        reverse("contratos:editar_contrato", args=[contrato.pk]),
        {"corpo": "Texto ajustado pelo usuário."},
    )
    contrato.refresh_from_db()
    assert contrato.corpo == "Texto ajustado pelo usuário."

    # Baixar PDF gera o arquivo e salva como documento do negócio.
    resp = client.get(reverse("contratos:baixar_pdf", args=[contrato.pk]))
    assert resp.status_code == 200
    assert resp["Content-Type"] == "application/pdf"
    assert Documento.objetos.filter(negocio=negocio, gerado_pelo_sistema=True).exists()

    # Baixar Word.
    resp = client.get(reverse("contratos:baixar_docx", args=[contrato.pk]))
    assert resp.status_code == 200


def test_gerar_sem_dados_mostra_faltando(client):
    Usuario.objects.create_user(username="k", password="x-123456")
    client.login(username="k", password="x-123456")
    comprador = Pessoa.objetos.create(nome="Sem dados")
    carro = Veiculo.objetos.create(
        placa="ZZZ9999", marca="VW", modelo="Gol", ano_fabricacao=2015, ano_modelo=2016, cor="Preto"
    )
    negocio = Negocio.objetos.create(tipo=TipoNegocio.VENDA, status=StatusNegocio.RASCUNHO)
    ParteNegocio.objetos.create(negocio=negocio, pessoa=comprador, papel=PapelParte.COMPRADOR)
    ItemNegocio.objetos.create(
        negocio=negocio, veiculo=carro, para_pessoa=comprador, valor=Decimal("1")
    )

    resp = client.post(reverse("contratos:gerar", args=[negocio.pk]))
    assert resp.status_code == 200
    assert b"Faltam dados" in resp.content
