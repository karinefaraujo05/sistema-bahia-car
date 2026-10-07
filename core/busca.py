"""
Busca unificada, tolerante e ranqueada.

Ignora maiúsculas/minúsculas, acentos (nome, marca, modelo), pontuação/hífen
(placa, CPF/CNPJ, telefone) e tolera erros de digitação (pg_trgm). Resultados vêm
ordenados por relevância. Veículos de terceiro nunca aparecem.
"""

from django.contrib.postgres.search import TrigramWordSimilarity
from django.db.models import Q
from django.db.models.functions import Greatest

from pessoas.models import Pessoa
from pessoas.validators import so_digitos
from veiculos.models import Situacao, Veiculo
from veiculos.validators import normalizar_placa

LIMITE = 20
# Similaridade de palavra: tolera erro de digitação mesmo em campos longos
# (ex.: "renegde" acha "Renegade Sport 1.8"). 0 = nada, 1 = igual.
LIMIAR = 0.4


def buscar(termo):
    termo = (termo or "").strip()
    if not termo:
        return {"termo": termo, "carros": [], "pessoas": []}
    return {"termo": termo, "carros": _carros(termo), "pessoas": _pessoas(termo)}


def _carros(termo):
    consulta = (
        Q(marca__unaccent__icontains=termo)
        | Q(modelo__unaccent__icontains=termo)
        | Q(chassi__icontains=termo)
    )
    placa = normalizar_placa(termo)
    if placa:
        consulta |= Q(placa__icontains=placa)
    digitos = so_digitos(termo)
    if digitos and len(digitos) >= 4:
        consulta |= Q(renavam__icontains=digitos)

    return list(
        Veiculo.objetos.exclude(situacao=Situacao.TERCEIRO)
        .annotate(sim=Greatest(TrigramWordSimilarity(termo, "marca"), TrigramWordSimilarity(termo, "modelo")))
        .filter(consulta | Q(sim__gt=LIMIAR))
        .order_by("-sim", "-criado_em")
        .prefetch_related("fotos")[:LIMITE]
    )


def _pessoas(termo):
    consulta = Q(nome__unaccent__icontains=termo) | Q(email__unaccent__icontains=termo)
    digitos = so_digitos(termo)
    if digitos:
        consulta |= Q(cpf_cnpj__contains=digitos) | Q(telefone__contains=digitos)

    return list(
        Pessoa.objetos.annotate(sim=TrigramWordSimilarity(termo, "nome"))
        .filter(consulta | Q(sim__gt=LIMIAR))
        .order_by("-sim", "nome")[:LIMITE]
    )
