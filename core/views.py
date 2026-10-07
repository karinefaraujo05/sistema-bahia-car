import io
import zipfile

from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.core.management import call_command
from django.http import FileResponse, HttpResponseForbidden
from django.shortcuts import render
from django.utils import timezone

from negocios.models import Negocio, StatusNegocio, TipoNegocio
from negocios.services import repasses_pendentes
from veiculos.models import Situacao, StatusVeiculo, Veiculo

from .agenda import lembretes
from .busca import buscar as buscar_tudo
from .frases import frase_do_dia

MESES_ABREV = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def _vendas_por_mes(hoje):
    """Quantidade de vendas/trocas concluídas nos últimos 6 meses, para o gráfico."""
    pares = []
    ano, mes = hoje.year, hoje.month
    for _ in range(6):
        pares.append((ano, mes))
        mes -= 1
        if mes == 0:
            mes, ano = 12, ano - 1
    pares.reverse()

    dados = []
    for ano, mes in pares:
        quantidade = Negocio.objetos.filter(
            status=StatusNegocio.CONCLUIDO,
            tipo__in=[TipoNegocio.VENDA, TipoNegocio.TROCA],
            data__year=ano,
            data__month=mes,
        ).count()
        dados.append({"rotulo": MESES_ABREV[mes - 1], "valor": quantidade})

    maximo = max((d["valor"] for d in dados), default=0) or 1
    for d in dados:
        d["altura"] = round(d["valor"] / maximo * 100)
    return dados


@login_required
def inicio(request):
    """Painel inicial: indicadores, gráfico de vendas e atalhos."""
    hoje = timezone.localdate()

    na_loja = (
        Veiculo.objetos.filter(status=StatusVeiculo.EM_ESTOQUE)
        .exclude(situacao=Situacao.TERCEIRO)
        .count()
    )
    vendas_no_mes = Negocio.objetos.filter(
        status=StatusNegocio.CONCLUIDO,
        tipo=TipoNegocio.VENDA,
        data__year=hoje.year,
        data__month=hoje.month,
    ).count()

    # Onboarding: aparece sozinho toda segunda-feira (uma vez por semana).
    # "?onboarding=1" força a abrir (pra rever quando quiser).
    iso = hoje.isocalendar()
    ano_semana = f"{iso.year}-{iso.week:02d}"
    auto_segunda = hoje.weekday() == 0 and request.session.get("onboarding_semana") != ano_semana
    if auto_segunda:
        request.session["onboarding_semana"] = ano_semana
    mostrar_onboarding = auto_segunda or request.GET.get("onboarding") == "1"

    pendencias = lembretes(hoje)
    contexto = {
        "carros_na_loja": na_loja,
        "vendas_no_mes": vendas_no_mes,
        "repasses_pendentes": repasses_pendentes().count(),
        "ultimos_negocios": Negocio.objetos.filter(status=StatusNegocio.CONCLUIDO)[:5],
        "grafico_vendas": _vendas_por_mes(hoje),
        "alertas": pendencias[:4],
        "mais_alertas": max(len(pendencias) - 4, 0),
        "mostrar_onboarding": mostrar_onboarding,
        "frase_do_dia": frase_do_dia(hoje),
    }
    return render(request, "inicio.html", contexto)


@login_required
def agenda(request):
    """Agenda: todas as pendências, cada uma com link pro lugar certo."""
    return render(request, "agenda.html", {"itens": lembretes(timezone.localdate())})


@login_required
def buscar(request):
    resultado = buscar_tudo(request.GET.get("q", ""))
    if request.htmx:
        return render(request, "busca/resultados.html", resultado)
    return render(request, "busca/pagina.html", resultado)


@login_required
def ajuda(request):
    """Guia de uso passo a passo, em linguagem simples."""
    return render(request, "ajuda.html")


# --- App no celular (PWA) ---


def manifest(request):
    """Manifesto do app, pra poder instalar na tela inicial do celular."""
    return render(
        request, "pwa/manifest.webmanifest", content_type="application/manifest+json"
    )


def service_worker(request):
    """Service worker na raiz do site (escopo /), pra deixar o sistema instalável."""
    resposta = render(request, "pwa/sw.js", content_type="application/javascript")
    resposta["Service-Worker-Allowed"] = "/"
    resposta["Cache-Control"] = "no-cache"
    return resposta


# --- Backup para baixar na hora ---


def _arquivos_media(prefixo=""):
    """Lista todos os arquivos enviados (fotos/documentos), em dev ou no bucket."""
    try:
        pastas, arquivos = default_storage.listdir(prefixo)
    except Exception:
        return
    for nome in arquivos:
        yield f"{prefixo}/{nome}" if prefixo else nome
    for pasta in pastas:
        sub = f"{prefixo}/{pasta}" if prefixo else pasta
        yield from _arquivos_media(sub)


@login_required
def baixar_backup(request):
    """Gera um .zip com todos os dados (banco) e as fotos, pra guardar/salvar."""
    if not request.user.is_superuser:
        return HttpResponseForbidden("Só o responsável pode baixar o backup.")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        dados = io.StringIO()
        call_command(
            "dumpdata",
            natural_foreign=True,
            natural_primary=True,
            exclude=[
                "contenttypes",
                "auth.permission",
                "admin.logentry",
                "sessions.session",
            ],
            indent=2,
            stdout=dados,
        )
        zf.writestr("dados.json", dados.getvalue())

        for caminho in _arquivos_media():
            try:
                with default_storage.open(caminho, "rb") as fh:
                    zf.writestr(f"media/{caminho}", fh.read())
            except Exception:
                continue

        zf.writestr(
            "LEIA-ME.txt",
            "Backup do Sistema Bahia Car\n\n"
            "dados.json  -> todos os dados (pessoas, carros, vendas, contratos).\n"
            "media/      -> fotos e documentos enviados.\n\n"
            "Guarde este arquivo em um lugar seguro (pen drive, Google Drive).\n"
            "Para restaurar, procure o desenvolvedor do sistema.\n",
        )

    buffer.seek(0)
    nome = f"bahiacar-backup-{timezone.localdate():%Y-%m-%d}.zip"
    return FileResponse(
        buffer, as_attachment=True, filename=nome, content_type="application/zip"
    )
