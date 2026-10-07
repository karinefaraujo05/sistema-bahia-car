from django.db import models
from django.db.models import Q

from core.models import ModeloBase

# Dados de identidade da loja que o contrato precisa ter preenchidos.
# As regras do contrato (multa, IPVA, nº de vias, prazos) são definidas por contrato,
# ajustáveis no editor de cada contrato — por isso não entram aqui.
CAMPOS_OBRIGATORIOS_CONTRATO = [
    "razao_social",
    "cnpj",
    "endereco",
    "cidade",
    "uf",
    "representante_nome",
    "representante_cpf",
]


class ConfiguracaoLoja(ModeloBase):
    """Dados da loja usados nos contratos. Registro único (singleton)."""

    razao_social = models.CharField("razão social", max_length=160, blank=True)
    nome_fantasia = models.CharField("nome fantasia", max_length=120, blank=True)
    cnpj = models.CharField("CNPJ", max_length=14, blank=True)
    endereco = models.CharField("endereço", max_length=200, blank=True)
    cidade = models.CharField("cidade", max_length=100, blank=True)
    uf = models.CharField("UF", max_length=2, blank=True)
    cep = models.CharField("CEP", max_length=9, blank=True)
    representante_nome = models.CharField("representante", max_length=160, blank=True)
    representante_cpf = models.CharField("CPF do representante", max_length=11, blank=True)

    multa_percentual = models.DecimalField(
        "multa se não cumprir o combinado (%)",
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Porcentagem cobrada de quem desistir ou descumprir o contrato. "
        "Combine o valor com o seu advogado. Ex.: 10",
    )
    regra_ipva = models.CharField(
        "quem paga o IPVA e o licenciamento",
        max_length=200,
        blank=True,
        help_text="O que vale por padrão nos contratos. Ex.: até a entrega, por conta "
        "do vendedor; a partir da entrega, do comprador.",
    )
    prazo_assinatura_dias = models.PositiveSmallIntegerField(
        "prazo para assinar a ATPV-e (dias úteis)", default=5
    )
    prazo_repasse_dias = models.PositiveSmallIntegerField(
        "prazo de repasse ao consignante (dias úteis)", default=5
    )
    numero_vias = models.PositiveSmallIntegerField("número de vias", default=2)

    class Meta(ModeloBase.Meta):
        verbose_name = "configuração da loja"
        verbose_name_plural = "configuração da loja"

    def __str__(self):
        return self.razao_social or "Configuração da loja"

    def save(self, *args, **kwargs):
        self.pk = 1  # registro único
        super().save(*args, **kwargs)

    @classmethod
    def carregar(cls):
        obj, _ = cls.todos.get_or_create(pk=1)
        return obj

    def campos_faltando(self):
        """Lista os campos ainda não preenchidos que o contrato exige."""
        faltando = []
        for campo in CAMPOS_OBRIGATORIOS_CONTRATO:
            valor = getattr(self, campo)
            if valor in (None, ""):
                faltando.append(self._meta.get_field(campo).verbose_name)
        return faltando

    @property
    def completa_para_contrato(self):
        return not self.campos_faltando()


class TipoDocumento(models.TextChoices):
    CONTRATO = "contrato", "Contrato"
    TERMO_VISTORIA = "termo_vistoria", "Termo de vistoria e entrega"
    RECIBO = "recibo", "Recibo"
    CONSULTA = "consulta", "Consulta de situação do veículo"
    PROCURACAO = "procuracao", "Procuração/autorização"
    DOC_VEICULO = "doc_veiculo", "Documento do veículo (CRV/CRLV)"
    DOC_PESSOAL = "doc_pessoal", "Documento pessoal"
    OUTRO = "outro", "Outro"


def documento_upload_para(instance, filename):
    if instance.negocio_id:
        return f"documentos/negocio-{instance.negocio_id}/{filename}"
    if instance.consignacao_id:
        return f"documentos/consignacao-{instance.consignacao_id}/{filename}"
    return f"documentos/veiculo-{instance.veiculo_id}/{filename}"


class Documento(ModeloBase):
    negocio = models.ForeignKey(
        "negocios.Negocio",
        verbose_name="negócio",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="documentos",
    )
    consignacao = models.ForeignKey(
        "negocios.Consignacao",
        verbose_name="consignação",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="documentos",
    )
    veiculo = models.ForeignKey(
        "veiculos.Veiculo",
        verbose_name="veículo",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="documentos",
    )
    tipo = models.CharField("tipo", max_length=16, choices=TipoDocumento.choices)
    arquivo = models.FileField("arquivo", upload_to=documento_upload_para)
    gerado_pelo_sistema = models.BooleanField("gerado pelo sistema", default=False)
    descricao = models.CharField("descrição", max_length=200, blank=True)

    class Meta(ModeloBase.Meta):
        verbose_name = "documento"
        verbose_name_plural = "documentos"
        ordering = ["-criado_em"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(negocio__isnull=False)
                    | Q(consignacao__isnull=False)
                    | Q(veiculo__isnull=False)
                ),
                name="documento_pertence_a_negocio_ou_consignacao",
            )
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} ({self.arquivo.name})"

    @property
    def nome_arquivo(self):
        return self.arquivo.name.rsplit("/", 1)[-1]


class ModeloContrato(models.TextChoices):
    A = "A", "Compra pela loja"
    B = "B", "Venda pela loja"
    C = "C", "Troca com a loja"
    D = "D", "Consignação"
    E = "E", "Intermediação"


class Contrato(ModeloBase):
    """
    Contrato gerado a partir de um negócio (ou consignação). O corpo é texto editável:
    o usuário ajusta na tela e depois baixa em PDF ou Word. Regerar cria nova versão.
    """

    negocio = models.ForeignKey(
        "negocios.Negocio",
        verbose_name="negócio",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="contratos",
    )
    consignacao = models.ForeignKey(
        "negocios.Consignacao",
        verbose_name="consignação",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="contratos",
    )
    modelo = models.CharField("modelo", max_length=1, choices=ModeloContrato.choices)
    titulo = models.CharField("título", max_length=200)
    versao = models.PositiveSmallIntegerField("versão", default=1)
    corpo = models.TextField("texto do contrato")
    observacoes = models.TextField("observações", blank=True)
    num_testemunhas = models.PositiveSmallIntegerField("nº de testemunhas", default=2)

    class Meta(ModeloBase.Meta):
        verbose_name = "contrato"
        verbose_name_plural = "contratos"
        ordering = ["-versao", "-criado_em"]

    def __str__(self):
        return f"{self.titulo} (v{self.versao})"
