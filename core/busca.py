"""
Busca unificada, tolerante e ranqueada.

Ignora maiúsculas/minúsculas, acentos (nome, marca, modelo), pontuação/hífen
(placa, CPF/CNPJ, telefone) e tolera erros de digitação (pg_trgm). Resultados vêm
ordenados por relevância. Veículos de terceiro nunca aparecem.
"""

from django.contrib.postgres.search import TrigramWordSimilarity
from django.db.models import Q
from django.db.models.functions import Greatest

from negocios.models import Negocio, PapelParte, TipoNegocio
from pessoas.models import Pessoa
from pessoas.validators import so_digitos
from veiculos.models import Situacao, Veiculo
from veiculos.validators import normalizar_placa

LIMITE = 20
# Similaridade de palavra: tolera erro de digitação mesmo em campos longos
# (ex.: "renegde" acha "Renegade Sport 1.8"). 0 = nada, 1 = igual.
LIMIAR = 0.4

# Papel do cliente principal por tipo de negócio (espelha negocios.views.PAPEL_PRINCIPAL).
_PAPEL_CLIENTE = {
    TipoNegocio.VENDA: PapelParte.COMPRADOR,
    TipoNegocio.COMPRA: PapelParte.VENDEDOR,
    TipoNegocio.TROCA: PapelParte.PERMUTANTE,
}


def buscar(termo):
    termo = (termo or "").strip()
    if not termo:
        return {"termo": termo, "carros": [], "pessoas": [], "negocios": []}
    return {
        "termo": termo,
        "carros": _carros(termo),
        "pessoas": _pessoas(termo),
        "negocios": _negocios(termo),
    }


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


def _descrever_negocio(negocio):
    """Texto humano do negócio: "Venda do Gol prata pra João Silva" (data vai no template)."""
    texto = negocio.get_tipo_display()
    itens = list(negocio.itens.all())  # prefetched
    if itens:
        carro = itens[0].veiculo
        texto += f" do {carro.modelo}"
        if carro.cor:
            texto += f" {carro.cor.lower()}"
    papel = _PAPEL_CLIENTE.get(negocio.tipo)
    parte = next((p for p in negocio.partes.all() if p.papel == papel), None)
    if parte:
        texto += f" pra {parte.pessoa.nome}"
    return texto


def _negocios(termo):
    """Negócios/contratos por nome do cliente, placa ou carro (marca/modelo)."""
    consulta = (
        Q(partes__pessoa__nome__unaccent__icontains=termo)
        | Q(itens__veiculo__marca__unaccent__icontains=termo)
        | Q(itens__veiculo__modelo__unaccent__icontains=termo)
    )
    placa = normalizar_placa(termo)
    if placa:
        consulta |= Q(itens__veiculo__placa__icontains=placa)

    negocios = list(
        Negocio.objetos.filter(consulta)
        .distinct()
        .prefetch_related("partes__pessoa", "itens__veiculo", "contratos")
        .order_by("-data", "-criado_em")[:LIMITE]
    )
    for n in negocios:
        n.descricao_busca = _descrever_negocio(n)
        # contratos vêm ordenados por -versao (Meta); o primeiro é a versão mais nova.
        contratos = list(n.contratos.all())
        n.contrato_recente = contratos[0] if contratos else None
    return negocios
