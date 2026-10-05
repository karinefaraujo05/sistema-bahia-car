"""
Busca unificada e tolerante.

Ignora maiúsculas/minúsculas, acentos (nome, marca, modelo), e pontuação/hífen
(placa, CPF/CNPJ, telefone). Veículos de terceiro nunca aparecem.
"""

from django.db.models import Q

from pessoas.models import Pessoa
from pessoas.validators import so_digitos
from veiculos.models import Situacao, Veiculo
from veiculos.validators import normalizar_placa

LIMITE = 20


def buscar(termo):
    termo = (termo or "").strip()
    if not termo:
        return {"termo": termo, "carros": [], "pessoas": []}
    return {"termo": termo, "carros": _carros(termo), "pessoas": _pessoas(termo)}


def _carros(termo):
    consulta = Q(marca__unaccent__icontains=termo) | Q(modelo__unaccent__icontains=termo)
    placa = normalizar_placa(termo)
    if placa:
        consulta |= Q(placa__icontains=placa)
    return list(
        Veiculo.objetos.exclude(situacao=Situacao.TERCEIRO)
        .filter(consulta)
        .prefetch_related("fotos")[:LIMITE]
    )


def _pessoas(termo):
    consulta = Q(nome__unaccent__icontains=termo)
    digitos = so_digitos(termo)
    if digitos:
        consulta |= Q(cpf_cnpj__contains=digitos) | Q(telefone__contains=digitos)
    return list(Pessoa.objetos.filter(consulta)[:LIMITE])
