from django.db import models
from django.utils import timezone

from core.models import ModeloBase


class TipoNegocio(models.TextChoices):
    COMPRA = "compra", "Compra"
    VENDA = "venda", "Venda"
    TROCA = "troca", "Troca"


class Modalidade(models.TextChoices):
    PROPRIA = "propria", "A loja é dona do carro"
    INTERMEDIACAO = "intermediacao", "A loja só intermedia"


class StatusNegocio(models.TextChoices):
    RASCUNHO = "rascunho", "Rascunho"
    CONCLUIDO = "concluido", "Concluído"
    CANCELADO = "cancelado", "Cancelado"


class FormaPagamento(models.TextChoices):
    A_VISTA = "a_vista", "À vista"
    FINANCIADO = "financiado", "Financiado"
    PARCELADO_LOJA = "parcelado_loja", "Parcelado na loja"
    MISTO = "misto", "Misto"


class PapelParte(models.TextChoices):
    VENDEDOR = "vendedor", "Vendedor"
    COMPRADOR = "comprador", "Comprador"
    PERMUTANTE = "permutante", "Permutante"
    ANUENTE = "anuente", "Anuente"


class QuitacaoOpcao(models.TextChoices):
    RESPONSAVEL = "responsavel", "Alguém quita o saldo até uma data"
    DESCONTA_PRECO = "desconta_preco", "Saldo descontado do preço e pago ao credor"
    ANUENCIA_CREDOR = "anuencia_credor", "Depende da anuência do credor"


class ComissaoTipo(models.TextChoices):
    PERCENTUAL = "percentual", "Percentual sobre a venda"
    FIXA = "fixa", "Valor fixo"
    SOBREPRECO = "sobrepreco", "O que exceder o mínimo"


class StatusConsignacao(models.TextChoices):
    ATIVA = "ativa", "Ativa"
    VENDIDA = "vendida", "Vendida"
    ENCERRADA = "encerrada", "Encerrada"


class Consignacao(ModeloBase):
    veiculo = models.ForeignKey(
        "veiculos.Veiculo",
        verbose_name="veículo",
        on_delete=models.PROTECT,
        related_name="consignacoes",
    )
    proprietario = models.ForeignKey(
        "pessoas.Pessoa",
        verbose_name="proprietário",
        on_delete=models.PROTECT,
        related_name="consignacoes_como_dono",
    )
    numero_contrato = models.PositiveIntegerField("número do contrato", null=True, blank=True)
    data_entrada = models.DateField("data de entrada", default=timezone.localdate)
    valor_liquido_minimo = models.DecimalField(
        "valor líquido mínimo ao dono", max_digits=10, decimal_places=2
    )
    comissao_tipo = models.CharField(
        "tipo de comissão", max_length=12, choices=ComissaoTipo.choices
    )
    comissao_valor = models.DecimalField(
        "valor da comissão", max_digits=10, decimal_places=2, null=True, blank=True
    )
    prazo_dias = models.PositiveSmallIntegerField("prazo (dias)", default=90)
    aviso_dias = models.PositiveSmallIntegerField("aviso de encerramento (dias)", default=15)
    prazo_repasse_dias = models.PositiveSmallIntegerField("prazo de repasse (dias)", default=5)
    documentos_entregues = models.TextField("documentos entregues pelo dono", blank=True)
    status = models.CharField(
        "status", max_length=10, choices=StatusConsignacao.choices, default=StatusConsignacao.ATIVA
    )
    repasse_feito_em = models.DateField("repasse feito em", null=True, blank=True)

    class Meta(ModeloBase.Meta):
        verbose_name = "consignação"
        verbose_name_plural = "consignações"
        ordering = ["-data_entrada"]

    def __str__(self):
        return f"Consignação {self.numero_contrato or '(rascunho)'} — {self.veiculo}"


class Negocio(ModeloBase):
    tipo = models.CharField("tipo", max_length=10, choices=TipoNegocio.choices)
    modalidade = models.CharField(
        "modalidade", max_length=14, choices=Modalidade.choices, default=Modalidade.PROPRIA
    )
    numero_contrato = models.PositiveIntegerField("número do contrato", null=True, blank=True)
    data = models.DateField("data", default=timezone.localdate)
    data_hora_entrega = models.DateTimeField("data e hora da entrega", null=True, blank=True)
    local_entrega = models.CharField("local da entrega", max_length=200, blank=True)
    valor_total = models.DecimalField(
        "valor total", max_digits=10, decimal_places=2, null=True, blank=True
    )
    forma_pagamento = models.CharField(
        "forma de pagamento", max_length=16, choices=FormaPagamento.choices, blank=True
    )
    detalhes_pagamento = models.TextField("detalhes do pagamento", blank=True)
    comissao_valor = models.DecimalField(
        "valor da comissão", max_digits=10, decimal_places=2, null=True, blank=True
    )
    comissao_pagador = models.ForeignKey(
        "pessoas.Pessoa",
        verbose_name="quem paga a comissão",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="comissoes_a_pagar",
    )
    consignacao = models.ForeignKey(
        Consignacao,
        verbose_name="consignação",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="negocios",
    )
    negocio_relacionado = models.ForeignKey(
        "self",
        verbose_name="negócio relacionado",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="relacionados",
    )
    observacoes = models.TextField("observações", blank=True)
    status = models.CharField(
        "status", max_length=10, choices=StatusNegocio.choices, default=StatusNegocio.CONCLUIDO
    )

    class Meta(ModeloBase.Meta):
        verbose_name = "negócio"
        verbose_name_plural = "negócios"
        ordering = ["-data", "-criado_em"]

    def __str__(self):
        return f"{self.get_tipo_display()} {self.numero_contrato or '(rascunho)'}"

    @property
    def eh_intermediacao(self):
        return self.modalidade == Modalidade.INTERMEDIACAO


class ParteNegocio(ModeloBase):
    negocio = models.ForeignKey(
        Negocio, verbose_name="negócio", on_delete=models.CASCADE, related_name="partes"
    )
    pessoa = models.ForeignKey(
        "pessoas.Pessoa",
        verbose_name="pessoa",
        on_delete=models.PROTECT,
        related_name="participacoes",
    )
    papel = models.CharField("papel", max_length=12, choices=PapelParte.choices)

    class Meta(ModeloBase.Meta):
        verbose_name = "parte do negócio"
        verbose_name_plural = "partes do negócio"

    def __str__(self):
        return f"{self.get_papel_display()}: {self.pessoa}"


class ItemNegocio(ModeloBase):
    negocio = models.ForeignKey(
        Negocio, verbose_name="negócio", on_delete=models.CASCADE, related_name="itens"
    )
    veiculo = models.ForeignKey(
        "veiculos.Veiculo",
        verbose_name="veículo",
        on_delete=models.PROTECT,
        related_name="itens_negocio",
    )
    # Quem entrega e quem recebe. Vazio = a loja (só na modalidade própria).
    de_pessoa = models.ForeignKey(
        "pessoas.Pessoa",
        verbose_name="quem entrega",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="itens_entregues",
    )
    para_pessoa = models.ForeignKey(
        "pessoas.Pessoa",
        verbose_name="quem recebe",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="itens_recebidos",
    )
    valor = models.DecimalField("valor", max_digits=10, decimal_places=2)
    km_entrega = models.PositiveIntegerField("km na entrega", null=True, blank=True)

    # Escolha de quitação quando o carro é alienado (ver CONTRATOS.md, bloco B5).
    quitacao_opcao = models.CharField(
        "como fica a quitação", max_length=16, choices=QuitacaoOpcao.choices, blank=True
    )
    quitacao_responsavel = models.CharField("quem quita", max_length=120, blank=True)

    # Estado do veículo antes de concluir este negócio, para desfazer no cancelamento.
    status_anterior = models.CharField("status anterior do veículo", max_length=12, blank=True)
    situacao_anterior = models.CharField("situação anterior do veículo", max_length=12, blank=True)
    valor_compra_anterior = models.DecimalField(
        "valor de compra anterior", max_digits=10, decimal_places=2, null=True, blank=True
    )

    class Meta(ModeloBase.Meta):
        verbose_name = "carro do negócio"
        verbose_name_plural = "carros do negócio"

    def __str__(self):
        return f"{self.veiculo} em {self.negocio}"

    @property
    def entra_na_loja(self):
        """O carro vai para a loja (quem recebe é a loja)."""
        return self.para_pessoa_id is None

    @property
    def sai_da_loja(self):
        """O carro sai da loja (quem entrega é a loja)."""
        return self.de_pessoa_id is None
