"""Deixa o número de pendências (lembretes) disponível em todas as telas (o sininho)."""

from .agenda import lembretes_do_request


def pendencias(request):
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {}
    try:
        total = len(lembretes_do_request(request))
    except Exception:
        total = 0
    return {"n_lembretes": total}
