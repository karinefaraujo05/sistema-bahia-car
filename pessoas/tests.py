import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse

from contas.models import Usuario
from pessoas import services
from pessoas.forms import PessoaForm, PessoaRapidaForm
from pessoas.models import Pessoa, TipoPessoa
from pessoas.validators import (
    cnpj_valido,
    cpf_valido,
    formatar_cpf_cnpj,
    formatar_telefone,
    so_digitos,
)

CPF_VALIDO = "11144477735"
CNPJ_VALIDO = "11222333000181"


def logar(client):
    Usuario.objects.create_user(username="karine", password="segredo-123")
    client.login(username="karine", password="segredo-123")


# --- Validação de CPF/CNPJ ---


def test_cpf_valido_e_invalido():
    assert cpf_valido(CPF_VALIDO)
    assert cpf_valido("111.444.777-35")  # com pontuação
    assert not cpf_valido("11111111111")  # todos iguais
    assert not cpf_valido("12345678900")
    assert not cpf_valido("123")


def test_cnpj_valido_e_invalido():
    assert cnpj_valido(CNPJ_VALIDO)
    assert not cnpj_valido("00000000000000")
    assert not cnpj_valido("11222333000180")


def test_so_digitos_e_formatacao():
    assert so_digitos("111.444.777-35") == "11144477735"
    assert formatar_cpf_cnpj("11144477735") == "111.444.777-35"
    assert formatar_cpf_cnpj("11222333000181") == "11.222.333/0001-81"
    assert formatar_telefone("71999998888") == "(71) 99999-8888"
    assert formatar_telefone("7133334444") == "(71) 3333-4444"


# --- Modelo Pessoa ---


@pytest.mark.django_db
def test_cpf_e_telefone_salvos_so_com_digitos():
    pessoa = Pessoa.objetos.create(
        nome="João Silva", cpf_cnpj="111.444.777-35", telefone="(71) 99999-8888"
    )
    assert pessoa.cpf_cnpj == "11144477735"
    assert pessoa.telefone == "71999998888"
    assert pessoa.cpf_cnpj_formatado == "111.444.777-35"


@pytest.mark.django_db
def test_cpf_cnpj_unico_entre_nao_arquivados():
    Pessoa.objetos.create(nome="João", cpf_cnpj=CPF_VALIDO)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Pessoa.objetos.create(nome="Outro João", cpf_cnpj=CPF_VALIDO)


@pytest.mark.django_db
def test_varias_pessoas_sem_documento_sao_permitidas():
    # A restrição de unicidade não vale para quem está sem CPF/CNPJ.
    Pessoa.objetos.create(nome="Sem doc 1")
    Pessoa.objetos.create(nome="Sem doc 2")
    assert Pessoa.objetos.count() == 2


@pytest.mark.django_db
def test_arquivar_libera_o_documento():
    primeira = Pessoa.objetos.create(nome="João", cpf_cnpj=CPF_VALIDO)
    primeira.arquivar()
    segunda = Pessoa.objetos.create(nome="João de novo", cpf_cnpj=CPF_VALIDO)
    assert segunda.pk != primeira.pk


# --- Services ---


@pytest.mark.django_db
def test_cadastro_rapido_cria_com_nome_e_telefone():
    pessoa = services.cadastrar_rapido("Maria", "71988887777")
    assert pessoa.pk
    assert pessoa.nome == "Maria"
    assert pessoa.telefone == "71988887777"


@pytest.mark.django_db
def test_busca_por_nome_cpf_e_telefone():
    services.cadastrar_rapido("Maria Souza", "71988887777")
    Pessoa.objetos.create(nome="Carlos", cpf_cnpj=CPF_VALIDO, telefone="71911112222")

    assert services.buscar_pessoas("maria").count() == 1
    assert services.buscar_pessoas("111.444.777-35").count() == 1  # por CPF com pontuação
    assert services.buscar_pessoas("988887777").count() == 1  # por telefone
    assert services.buscar_pessoas("ninguém").count() == 0


# --- Form ---


@pytest.mark.django_db
def test_form_rejeita_cpf_duplicado():
    Pessoa.objetos.create(nome="João", cpf_cnpj=CPF_VALIDO)
    form = PessoaForm(data={"tipo": TipoPessoa.FISICA, "nome": "Outro", "cpf_cnpj": CPF_VALIDO})
    assert not form.is_valid()
    assert "cpf_cnpj" in form.errors


@pytest.mark.django_db
def test_form_rejeita_pf_com_cnpj():
    form = PessoaForm(data={"tipo": TipoPessoa.FISICA, "nome": "Fulano", "cpf_cnpj": CNPJ_VALIDO})
    assert not form.is_valid()
    assert "cpf_cnpj" in form.errors


# --- Views ---


@pytest.mark.django_db
def test_lista_exige_login(client):
    assert client.get(reverse("pessoas:lista")).status_code == 302


@pytest.mark.django_db
def test_cadastro_pelo_formulario(client):
    logar(client)
    # Regra nova (Onda 2): obrigatórios são nome e CPF; CEP não é mais obrigatório.
    dados = {
        "tipo": TipoPessoa.FISICA,
        "nome": "José Pereira",
        "cpf_cnpj": CPF_VALIDO,
        "telefone": "71999990000",
    }
    resp = client.post(reverse("pessoas:novo"), dados)
    assert resp.status_code == 302
    assert Pessoa.objetos.filter(nome="José Pereira").exists()


# --- Onda 2: CPF obrigatório no rápido, dedupe e completude ---


@pytest.mark.django_db
def test_form_rapido_exige_cpf():
    sem_cpf = PessoaRapidaForm(data={"tipo": TipoPessoa.FISICA, "nome": "Maria", "telefone": "71"})
    assert not sem_cpf.is_valid()
    assert "cpf_cnpj" in sem_cpf.errors
    com_cpf = PessoaRapidaForm(
        data={"tipo": TipoPessoa.FISICA, "nome": "Maria", "cpf_cnpj": CPF_VALIDO}
    )
    assert com_cpf.is_valid()


@pytest.mark.django_db
def test_cadastro_rapido_pela_tela_deduplica(client):
    logar(client)
    existente = Pessoa.objetos.create(nome="João Antigo", cpf_cnpj=CPF_VALIDO)
    resp = client.post(
        reverse("pessoas:novo_rapido"),
        {"tipo": TipoPessoa.FISICA, "nome": "João Novo", "cpf_cnpj": "111.444.777-35"},
    )
    assert resp.status_code == 302
    # Não criou duplicata: continua tendo só uma pessoa com esse CPF.
    assert Pessoa.objetos.filter(cpf_cnpj=CPF_VALIDO).count() == 1
    assert resp.url == reverse("pessoas:detalhe", args=[existente.pk])


@pytest.mark.django_db
def test_form_pessoa_uf_e_estado_civil_viram_selecao(client):
    logar(client)
    html = client.get(reverse("pessoas:novo")).content.decode()
    assert 'id="nacionalidades"' in html  # datalist de nacionalidade
    assert "Bahia" in html and "São Paulo" in html  # opções de UF no select
    assert "Casado(a)" in html and "União estável" in html  # opções de estado civil
    # Salvar com UF e estado civil escolhidos da lista funciona.
    resp = client.post(
        reverse("pessoas:novo"),
        {
            "tipo": TipoPessoa.FISICA,
            "nome": "Fulana da Lista",
            "cpf_cnpj": CPF_VALIDO,
            "uf": "BA",
            "estado_civil": "Casado(a)",
            "nacionalidade": "Brasileira",
        },
    )
    assert resp.status_code == 302
    p = Pessoa.objetos.get(nome="Fulana da Lista")
    assert p.uf == "BA"
    assert p.estado_civil == "Casado(a)"


@pytest.mark.django_db
def test_buscar_cpf_encontra(client):
    logar(client)
    p = Pessoa.objetos.create(nome="Carla", cpf_cnpj=CPF_VALIDO)
    resp = client.get(reverse("pessoas:buscar_cpf"), {"cpf": "111.444.777-35"})
    dados = resp.json()
    assert dados["encontrado"] is True
    assert dados["nome"] == "Carla"
    assert dados["url"] == reverse("pessoas:detalhe", args=[p.pk])


@pytest.mark.django_db
def test_campos_faltando_contrato_pessoa():
    p = Pessoa.objetos.create(nome="Sem Dados", cpf_cnpj=CPF_VALIDO)
    faltando = p.campos_faltando_contrato()
    assert "endereço" in faltando and "cidade" in faltando
    assert "nacionalidade" in faltando  # pessoa física exige
    assert "CPF/CNPJ" not in faltando  # esse já está preenchido


@pytest.mark.django_db
def test_telas_abrem(client):
    logar(client)
    pessoa = Pessoa.objetos.create(nome="Ana", cpf_cnpj=CPF_VALIDO)
    assert client.get(reverse("pessoas:lista")).status_code == 200
    assert client.get(reverse("pessoas:novo")).status_code == 200
    assert client.get(reverse("pessoas:novo_rapido")).status_code == 200
    assert client.get(reverse("pessoas:detalhe", args=[pessoa.pk])).status_code == 200


# --- Integração com veículos: FK proprietario ---


@pytest.mark.django_db
def test_veiculo_consignado_aponta_para_dono():
    from veiculos.models import Situacao, Veiculo

    dono = Pessoa.objetos.create(nome="Dono do carro", cpf_cnpj=CPF_VALIDO)
    veiculo = Veiculo.objetos.create(
        placa="XYZ1A23",
        marca="Fiat",
        modelo="Uno",
        ano_fabricacao=2012,
        ano_modelo=2013,
        cor="Branco",
        situacao=Situacao.CONSIGNADO,
        proprietario=dono,
    )
    assert veiculo.proprietario == dono
    assert dono.veiculos.count() == 1


# --- Item 6.5: paginação (50 por página) ---


@pytest.mark.django_db
def test_lista_de_pessoas_pagina_50_por_pagina(client):
    Usuario.objects.create_user(username="k", password="x-123456")
    client.login(username="k", password="x-123456")
    for i in range(55):
        Pessoa.objetos.create(nome=f"Pessoa {i:03d}")
    resp = client.get(reverse("pessoas:lista"))
    page = resp.context["page_obj"]
    assert page.paginator.count == 55
    assert page.paginator.num_pages == 2
    assert len(page.object_list) == 50
    resp2 = client.get(reverse("pessoas:lista"), {"page": 2})
    assert len(resp2.context["page_obj"].object_list) == 5
