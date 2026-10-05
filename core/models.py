"""
Modelo base de todo o sistema.

Regra central do projeto: NADA é apagado de verdade. "Excluir" na interface
significa arquivar. Por isso:

- o manager padrão (`objetos`) esconde os registros arquivados;
- o manager `todos` enxerga tudo, inclusive arquivados;
- o manager "base" do Django (usado para relações) também enxerga tudo, para
  não quebrar chaves estrangeiras apontando para algo arquivado.

Todo modelo concreto do sistema deve herdar de `ModeloBase`. Se precisar de uma
classe Meta própria, herde a desta base para manter os managers:

    class Meta(ModeloBase.Meta):
        verbose_name = "..."
"""

from django.conf import settings
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords


class NaoArquivadosManager(models.Manager):
    """Manager padrão: devolve apenas os registros não arquivados."""

    def get_queryset(self):
        return super().get_queryset().filter(arquivado=False)


class ModeloBase(models.Model):
    criado_em = models.DateTimeField("criado em", auto_now_add=True)
    atualizado_em = models.DateTimeField("atualizado em", auto_now=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="criado por",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    atualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="atualizado por",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    arquivado = models.BooleanField("arquivado", default=False)
    arquivado_em = models.DateTimeField("arquivado em", null=True, blank=True)

    # Histórico automático (quem mudou o quê e quando) para todo modelo filho.
    historico = HistoricalRecords(inherit=True)

    objetos = NaoArquivadosManager()
    todos = models.Manager()

    class Meta:
        abstract = True
        # `objetos` é o padrão (esconde arquivados); `todos` é a base (vê tudo).
        default_manager_name = "objetos"
        base_manager_name = "todos"

    def arquivar(self, salvar=True):
        """Arquiva o registro em vez de apagá-lo."""
        if not self.arquivado:
            self.arquivado = True
            self.arquivado_em = timezone.now()
            if salvar:
                self.save(update_fields=["arquivado", "arquivado_em"])

    def desarquivar(self, salvar=True):
        """Desfaz o arquivamento."""
        if self.arquivado:
            self.arquivado = False
            self.arquivado_em = None
            if salvar:
                self.save(update_fields=["arquivado", "arquivado_em"])
