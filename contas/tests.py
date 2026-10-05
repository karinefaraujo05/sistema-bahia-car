import pytest
from django.urls import reverse

from contas.models import Usuario


@pytest.mark.django_db
def test_pagina_de_login_abre(client):
    resp = client.get(reverse("contas:entrar"))
    assert resp.status_code == 200
    assert "Entrar" in resp.content.decode()


@pytest.mark.django_db
def test_inicio_exige_login(client):
    resp = client.get(reverse("inicio"))
    assert resp.status_code == 302
    assert reverse("contas:entrar") in resp.url


@pytest.mark.django_db
def test_inicio_abre_quando_logado(client):
    Usuario.objects.create_user(username="karine", password="senha-forte-123")
    client.login(username="karine", password="senha-forte-123")
    resp = client.get(reverse("inicio"))
    assert resp.status_code == 200


@pytest.mark.django_db
def test_papel_define_administrador():
    chefe = Usuario.objects.create_user(
        username="chefe", password="x", papel=Usuario.Papel.ADMINISTRADOR
    )
    vendedor = Usuario.objects.create_user(username="vendedor", password="x")
    assert chefe.eh_administrador is True
    assert vendedor.eh_administrador is False


@pytest.mark.django_db
def test_superusuario_e_sempre_administrador():
    adm = Usuario.objects.create_superuser(username="dev", password="x")
    assert adm.eh_administrador is True
