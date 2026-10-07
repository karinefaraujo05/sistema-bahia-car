from django.db import models
from django.db.models import Q
from django.utils import timezone

from core.models import ModeloBase

from .validators import (
    normalizar_placa,
    placa_formatada,
    validar_chassi,
    validar_placa,
    validar_renavam,
)


def foto_upload_para(instance, filename):
    return f"veiculos/{instance.veiculo_id}/{filename}"


def miniatura_upload_para(instance, filename):
    return f"veiculos/{instance.veiculo_id}/miniaturas/{filename}"


class Combustivel(models.TextChoices):
    FLEX = "flex", "Flex"
    GASOLINA = "gasolina", "Gasolina"
    ETANOL = "etanol", "Etanol"
    DIESEL = "diesel", "Diesel"
    ELETRICO = "eletrico", "Elétrico"
    HIBRIDO = "hibrido", "Híbrido"
    GNV = "gnv", "GNV"


class Cambio(models.TextChoices):
    MANUAL = "manual", "Manual"
    AUTOMATICO = "automatico", "Automático"


class Situacao(models.TextChoices):
    PROPRIO = "proprio", "Da loja"
    CONSIGNADO = "consignado", "Consignado"
    TERCEIRO = "terceiro", "De terceiro"


class StatusVeiculo(models.TextChoices):
    EM_ESTOQUE = "em_estoque", "Na loja"
    RESERVADO = "reservado", "Reservado"
    VENDIDO = "vendido", "Vendido"
    DEVOLVIDO = "devolvido", "Devolvido"


class Veiculo(ModeloBase):
    placa = models.CharField("placa", max_length=7, validators=[validar_placa])
    marca = models.CharField("marca", max_length=60)
    modelo = models.CharField("modelo", max_length=120)
    ano_fabricacao = models.PositiveSmallIntegerField("ano de fabricação")
    ano_modelo = models.PositiveSmallIntegerField("ano do modelo")
    cor = models.CharField("cor", max_length=40)
    km = models.PositiveIntegerField("quilometragem", null=True, blank=True)
    combustivel = models.CharField(
        "combustível", max_length=10, choices=Combustivel.choices, blank=True
    )
    cambio = models.CharField("câmbio", max_length=10, choices=Cambio.choices, blank=True)
    chassi = models.CharField("chassi", max_length=17, blank=True, validators=[validar_chassi])
    renavam = models.CharField("renavam", max_length=11, blank=True, validators=[validar_renavam])

    situacao = models.CharField(
        "situação", max_length=12, choices=Situacao.choices, default=Situacao.PROPRIO
    )
    # Dono do carro quando é consignado ou de terceiro (vazio quando é da loja).
    # A obrigatoriedade (consignado/terceiro exigem dono) é aplicada na Fase 4.
    proprietario = models.ForeignKey(
        "pessoas.Pessoa",
        verbose_name="proprietário",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="veiculos",
    )
    proprietario_registral = models.CharField(
        "proprietário no documento", max_length=120, blank=True
    )
    # documento_autorizacao (FK Documento) entra na Fase 5.

    alienado = models.BooleanField("tem financiamento ativo", default=False)
    credor_alienacao = models.CharField("credor da alienação", max_length=120, blank=True)
    saldo_devedor = models.DecimalField(
        "saldo devedor", max_digits=10, decimal_places=2, null=True, blank=True
    )
    parcelas_restantes = models.PositiveSmallIntegerField(
        "parcelas restantes", null=True, blank=True
    )
    valor_parcela = models.DecimalField(
        "valor da parcela", max_digits=10, decimal_places=2, null=True, blank=True
    )
    dia_vencimento = models.PositiveSmallIntegerField("dia de vencimento", null=True, blank=True)
    parcelas_vencidas = models.PositiveSmallIntegerField("parcelas vencidas", null=True, blank=True)

    tem_chave_reserva = models.BooleanField("tem chave reserva", null=True, blank=True)
    avarias_declaradas = models.TextField("avarias declaradas", blank=True)
    sinistro_declarado = models.BooleanField("teve sinistro", default=False)
    sinistro_descricao = models.TextField("descrição do sinistro", blank=True)

    valor_compra = models.DecimalField(
        "valor de compra", max_digits=10, decimal_places=2, null=True, blank=True
    )
    valor_anunciado = models.DecimalField(
        "valor anunciado", max_digits=10, decimal_places=2, null=True, blank=True
    )
    status = models.CharField(
        "status", max_length=12, choices=StatusVeiculo.choices, default=StatusVeiculo.EM_ESTOQUE
    )
    observacoes = models.TextField("observações", blank=True)

    class Meta(ModeloBase.Meta):
        verbose_name = "veículo"
        verbose_name_plural = "veículos"
        ordering = ["-criado_em"]
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "placa"],
                condition=Q(arquivado=False),
                name="placa_unica_entre_nao_arquivados",
                nulls_distinct=False,
            )
        ]

    def __str__(self):
        return f"{self.marca} {self.modelo} — {self.placa_formatada}"

    def save(self, *args, **kwargs):
        self.placa = normalizar_placa(self.placa)
        if self.chassi:
            self.chassi = self.chassi.strip().upper()
        super().save(*args, **kwargs)

    @property
    def placa_formatada(self):
        return placa_formatada(self.placa)

    @property
    def eh_consignado(self):
        return self.situacao == Situacao.CONSIGNADO

    @property
    def foto_capa(self):
        return self.fotos.filter(capa=True).first() or self.fotos.first()

    @property
    def dias_na_loja(self):
        # Até a Fase 4 (negócios), contamos a partir do cadastro do veículo.
        return (timezone.now().date() - self.criado_em.date()).days


class FotoVeiculo(ModeloBase):
    veiculo = models.ForeignKey(
        Veiculo, verbose_name="veículo", on_delete=models.CASCADE, related_name="fotos"
    )
    imagem = models.ImageField("imagem", upload_to=foto_upload_para)
    miniatura = models.ImageField(
        "miniatura", upload_to=miniatura_upload_para, null=True, blank=True
    )
    ordem = models.PositiveSmallIntegerField("ordem", default=0)
    capa = models.BooleanField("é a foto de capa", default=False)

    class Meta(ModeloBase.Meta):
        verbose_name = "foto do veículo"
        verbose_name_plural = "fotos do veículo"
        ordering = ["ordem", "criado_em"]
        constraints = [
            models.UniqueConstraint(
                fields=["veiculo"],
                condition=Q(capa=True, arquivado=False),
                name="uma_capa_por_veiculo",
            )
        ]

    def __str__(self):
        return f"Foto de {self.veiculo_id}"
