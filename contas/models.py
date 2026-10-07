from django.contrib.auth.models import AbstractUser
from django.db import models


class Empresa(models.Model):
    """Uma loja/empresa. Cada usuário pertence a uma e os dados são separados por ela."""

    nome = models.CharField("nome", max_length=120)
    criado_em = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        verbose_name = "empresa"
        verbose_name_plural = "empresas"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Usuario(AbstractUser):
    """
    Usuário do sistema. Dois papéis:

    - administrador: vê tudo, inclusive valor de compra e lucro;
    - vendedor: não vê valor de compra nem lucro.

    O superusuário (o desenvolvedor) é sempre tratado como administrador.
    """

    class Papel(models.TextChoices):
        ADMINISTRADOR = "administrador", "Administrador"
        VENDEDOR = "vendedor", "Vendedor"

    papel = models.CharField(
        "papel",
        max_length=20,
        choices=Papel.choices,
        default=Papel.VENDEDOR,
    )
    empresa = models.ForeignKey(
        "contas.Empresa",
        verbose_name="empresa",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="usuarios",
    )

    class Meta(AbstractUser.Meta):
        verbose_name = "usuário"
        verbose_name_plural = "usuários"

    @property
    def eh_administrador(self):
        return self.is_superuser or self.papel == self.Papel.ADMINISTRADOR
