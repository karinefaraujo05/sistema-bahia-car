"""
Lógica de negócio de veículos (fica aqui, não nas views nem nos templates).

Fotos de celular são pesadas: ao enviar, geramos uma versão grande (máx. 1600px no
maior lado) e uma miniatura, sempre corrigindo a orientação da câmera.
"""

import io
import uuid

from django.core.files.base import ContentFile
from django.db import transaction
from PIL import Image, ImageOps

from .models import FotoVeiculo, Situacao, StatusVeiculo, Veiculo

LADO_MAXIMO = 1600
LADO_MINIATURA = 400


def _redimensionar(arquivo, lado_maximo):
    """Devolve um ContentFile JPEG com no máximo `lado_maximo` px no maior lado."""
    arquivo.seek(0)
    imagem = Image.open(arquivo)
    imagem = ImageOps.exif_transpose(imagem)  # respeita a orientação da foto do celular
    if imagem.mode != "RGB":
        imagem = imagem.convert("RGB")
    imagem.thumbnail((lado_maximo, lado_maximo))
    buffer = io.BytesIO()
    imagem.save(buffer, format="JPEG", quality=85, optimize=True)
    return ContentFile(buffer.getvalue())


@transaction.atomic
def adicionar_foto(veiculo, arquivo, *, usuario=None):
    """Adiciona uma foto ao veículo, gerando versão grande e miniatura."""
    nome = f"{veiculo.placa or 'foto'}-{uuid.uuid4().hex[:8]}.jpg"

    foto = FotoVeiculo(veiculo=veiculo, criado_por=usuario, atualizado_por=usuario)
    foto.ordem = veiculo.fotos.count()
    foto.imagem.save(nome, _redimensionar(arquivo, LADO_MAXIMO), save=False)
    foto.miniatura.save(nome, _redimensionar(arquivo, LADO_MINIATURA), save=False)
    foto.save()

    # A primeira foto do veículo vira capa automaticamente.
    if not veiculo.fotos.filter(capa=True).exists():
        definir_capa(foto, usuario=usuario)
    return foto


@transaction.atomic
def definir_capa(foto, *, usuario=None):
    """Marca `foto` como capa e desmarca as demais do mesmo veículo."""
    FotoVeiculo.objetos.filter(veiculo=foto.veiculo, capa=True).exclude(pk=foto.pk).update(
        capa=False
    )
    if not foto.capa:
        foto.capa = True
        foto.atualizado_por = usuario
        foto.save(update_fields=["capa", "atualizado_por", "atualizado_em"])


@transaction.atomic
def remover_foto(foto, *, usuario=None):
    """Arquiva a foto (nunca apaga). Se era a capa, promove outra foto a capa."""
    era_capa = foto.capa
    foto.capa = False
    foto.atualizado_por = usuario
    foto.save(update_fields=["capa", "atualizado_por", "atualizado_em"])
    foto.arquivar()

    if era_capa:
        proxima = foto.veiculo.fotos.first()
        if proxima:
            definir_capa(proxima, usuario=usuario)


def arquivar_veiculo(veiculo, *, usuario=None):
    """Arquiva o veículo (some do estoque). Não apaga."""
    veiculo.atualizado_por = usuario
    veiculo.arquivar()


def consultar_estoque(*, status=None, origem="todos", ordem="recentes"):
    """
    Monta a consulta do estoque.

    - status: valor de StatusVeiculo (None = todos os status visíveis);
    - origem: "todos", "loja" (próprios) ou "consignados";
    - ordem: "recentes" ou "antigos" (há mais tempo na loja).

    Veículos de terceiro nunca aparecem no estoque.
    """
    qs = Veiculo.objetos.exclude(situacao=Situacao.TERCEIRO)

    if status:
        qs = qs.filter(status=status)

    if origem == "loja":
        qs = qs.filter(situacao=Situacao.PROPRIO)
    elif origem == "consignados":
        qs = qs.filter(situacao=Situacao.CONSIGNADO)

    if ordem == "antigos":
        qs = qs.order_by("criado_em")
    else:
        qs = qs.order_by("-criado_em")

    return qs.prefetch_related("fotos")


# Abas de status do estoque (rótulo curto exibido na tela).
ABAS_ESTOQUE = [
    (StatusVeiculo.EM_ESTOQUE, "Na loja"),
    (StatusVeiculo.RESERVADO, "Reservados"),
    (StatusVeiculo.VENDIDO, "Vendidos"),
]

# Filtro secundário por origem do carro.
ORIGENS_ESTOQUE = [
    ("todos", "Todos"),
    ("loja", "Da loja"),
    ("consignados", "Consignados"),
]
