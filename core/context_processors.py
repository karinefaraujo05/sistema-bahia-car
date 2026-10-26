"""Deixa o número de pendências (lembretes) disponível em todas as telas (o sininho)."""

from django.conf import settings

from .agenda import lembretes_do_request


def recursos(request):
    """Flags de recursos opcionais, pra mostrar/esconder botões (ex.: ler documento por foto)."""
    ocr = (getattr(settings, "OCR_IA_PROVIDER", "none") or "none").lower()
    return {"ocr_ia_ativo": ocr == "claude"}


def pendencias(request):
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {}
    try:
        total = len(lembretes_do_request(request))
    except Exception:
        total = 0
    return {"n_lembretes": total}
