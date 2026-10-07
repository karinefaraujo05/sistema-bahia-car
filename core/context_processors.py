"""Deixa o número de pendências (lembretes) disponível em todas as telas (o sininho)."""

from django.utils import timezone

from .agenda import lembretes


def pendencias(request):
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {}
    try:
        total = len(lembretes(timezone.localdate()))
    except Exception:
        total = 0
    return {"n_lembretes": total}
