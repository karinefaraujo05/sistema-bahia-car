from django.contrib.auth.models import AbstractUser
from django.db import models


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

    class Meta(AbstractUser.Meta):
        verbose_name = "usuário"
        verbose_name_plural = "usuários"

    @property
    def eh_administrador(self):
        return self.is_superuser or self.papel == self.Papel.ADMINISTRADOR
