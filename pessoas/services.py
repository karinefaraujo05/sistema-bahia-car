"""Lógica de negócio de pessoas: busca simples e cadastro rápido."""

from django.db.models import Q

from .models import Pessoa
from .validators import so_digitos


def buscar_pessoas(termo):
    """
    Busca por nome (ignorando maiúsculas) e, se o termo tiver dígitos, também por
    CPF/CNPJ e telefone (ignorando pontuação). A busca tolerante a acentos vem na Fase 6.
    """
    termo = (termo or "").strip()
    if not termo:
        return Pessoa.objetos.all()

    filtro = Q(nome__icontains=termo)
    digitos = so_digitos(termo)
    if digitos:
        filtro |= Q(cpf_cnpj__contains=digitos) | Q(telefone__contains=digitos)
    return Pessoa.objetos.filter(filtro)


def cadastrar_rapido(nome, telefone, *, tipo=None, usuario=None):
    """Cria uma pessoa só com o essencial (nome + telefone). O resto fica para depois."""
    pessoa = Pessoa(nome=nome, telefone=telefone, criado_por=usuario, atualizado_por=usuario)
    if tipo:
        pessoa.tipo = tipo
    pessoa.save()
    return pessoa


def arquivar_pessoa(pessoa, *, usuario=None):
    """Arquiva a pessoa (nunca apaga)."""
    pessoa.atualizado_por = usuario
    pessoa.arquivar()
