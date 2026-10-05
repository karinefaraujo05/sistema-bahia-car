from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def inicio(request):
    """Tela inicial. Por enquanto é o esqueleto do layout (sem dados)."""
    return render(request, "inicio.html")
