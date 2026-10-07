from django.db import models
from django.db.models import Q

from core.models import ModeloBase

from .validators import (
    formatar_cpf_cnpj,
    formatar_telefone,
    so_digitos,
    validar_cpf_cnpj,
)


class TipoPessoa(models.TextChoices):
    FISICA = "fisica", "Pessoa física"
    JURIDICA = "juridica", "Pessoa jurídica"


class Pessoa(ModeloBase):
    tipo = models.CharField(
        "tipo", max_length=10, choices=TipoPessoa.choices, default=TipoPessoa.FISICA
    )
    nome = models.CharField("nome", max_length=160)
    cpf_cnpj = models.CharField(
        "CPF/CNPJ", max_length=14, blank=True, validators=[validar_cpf_cnpj]
    )
    telefone = models.CharField("telefone", max_length=11, blank=True)
    email = models.EmailField("e-mail", blank=True)

    endereco = models.CharField("endereço", max_length=200, blank=True)
    cidade = models.CharField("cidade", max_length=100, blank=True)
    uf = models.CharField("UF", max_length=2, blank=True)
    cep = models.CharField("CEP", max_length=9, blank=True)

    rg = models.CharField("RG", max_length=20, blank=True)
    rg_orgao_emissor = models.CharField("órgão emissor do RG", max_length=20, blank=True)
    nacionalidade = models.CharField("nacionalidade", max_length=40, blank=True)
    estado_civil = models.CharField("estado civil", max_length=40, blank=True)
    profissao = models.CharField("profissão", max_length=60, blank=True)

    representante_nome = models.CharField("nome do representante", max_length=160, blank=True)
    representante_cpf = models.CharField("CPF do representante", max_length=11, blank=True)

    observacoes = models.TextField("observações", blank=True)

    class Meta(ModeloBase.Meta):
        verbose_name = "pessoa"
        verbose_name_plural = "pessoas"
        ordering = ["nome"]
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "cpf_cnpj"],
                condition=Q(arquivado=False) & ~Q(cpf_cnpj=""),
                name="cpf_cnpj_unico_entre_nao_arquivados",
                nulls_distinct=False,
            )
        ]

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        self.cpf_cnpj = so_digitos(self.cpf_cnpj)
        self.telefone = so_digitos(self.telefone)
        self.representante_cpf = so_digitos(self.representante_cpf)
        super().save(*args, **kwargs)

    @property
    def eh_fisica(self):
        return self.tipo == TipoPessoa.FISICA

    @property
    def cpf_cnpj_formatado(self):
        return formatar_cpf_cnpj(self.cpf_cnpj)

    @property
    def telefone_formatado(self):
        return formatar_telefone(self.telefone)
