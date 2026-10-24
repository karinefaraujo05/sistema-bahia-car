"""
Anexa o ARQUIVO ORIGINAL de cada contrato antigo (.docx/.odt) ao negócio
correspondente no sistema, como Documento do tipo "Contrato".

Casa pelo NÚMERO do contrato (prefixo do nome do arquivo). Quando o mesmo número
tem dois negócios (ex.: 1128), desempata pelo nome da pessoa no arquivo.

O arquivo vai pro armazenamento padrão do Django — então rode com as settings de
produção (R2) pra ele cair no bucket real:

    DJANGO_SETTINGS_MODULE=config.settings.prod \
        python manage.py anexar_contratos --dry-run
    DJANGO_SETTINGS_MODULE=config.settings.prod python manage.py anexar_contratos

É idempotente: se o negócio já tem um contrato anexado com o mesmo nome, pula.
"""

import os
import re
import unicodedata

from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction

from contas.models import Empresa, Usuario
from contratos.models import Documento, TipoDocumento
from core.tenancy import limpar_empresa_atual, set_empresa_atual
from negocios.models import Negocio

PASTA_PADRAO = os.path.expanduser("~/Downloads/anexos")
EMPRESA_NOME = "Bahia Car"
USUARIO_LOGIN = "nelson"
MARCA_IMPORT = "[IMPORTADO DO CONTRATO ANTIGO]"


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s or "")
                   if unicodedata.category(c) != "Mn").upper()


class Command(BaseCommand):
    help = "Anexa os .docx/.odt dos contratos antigos aos negócios como Documento (Contrato)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--dir", default=PASTA_PADRAO)
        parser.add_argument("--numeros", nargs="*", type=int)

    def handle(self, *args, **opts):
        pasta = opts["dir"]
        if not os.path.isdir(pasta):
            self.stderr.write(f"Pasta não encontrada: {pasta}")
            return
        arquivos = [f for f in os.listdir(pasta)
                    if f.lower().endswith((".docx", ".odt"))
                    and "MODELO NOVO" not in f.upper()
                    and not f.endswith(" (1).docx")]
        # índice número -> [arquivos]
        por_numero = {}
        for f in arquivos:
            m = re.match(r"\s*(\d+)", f)
            if m:
                por_numero.setdefault(int(m.group(1)), []).append(f)

        dry = opts["dry_run"]
        empresa = Empresa.objects.get(nome=EMPRESA_NOME)
        usuario = Usuario.objects.get(username=USUARIO_LOGIN)
        set_empresa_atual(empresa)
        self.stdout.write(self.style.WARNING(
            f"\n{'MODO TESTE' if dry else 'ANEXANDO'} — negócios importados da Bahia Car\n"))
        anexados = pulados = sem_arquivo = 0
        try:
            negs = Negocio.objetos.filter(
                empresa=empresa, observacoes__contains=MARCA_IMPORT
            ).exclude(numero_contrato__isnull=True)
            if opts.get("numeros"):
                negs = negs.filter(numero_contrato__in=opts["numeros"])
            for neg in negs.order_by("numero_contrato"):
                num = neg.numero_contrato
                candidatos = por_numero.get(num, [])
                arq = self._escolher(neg, candidatos)
                if not arq:
                    sem_arquivo += 1
                    self.stdout.write(self.style.ERROR(
                        f"  #{num}: sem arquivo correspondente (candidatos: {candidatos})"))
                    continue
                nome_arq = os.path.basename(arq)
                # Um negócio importado tem um contrato. Se já tem, não anexa de novo.
                ja = neg.documentos.filter(tipo=TipoDocumento.CONTRATO).exists()
                if ja:
                    pulados += 1
                    self.stdout.write(f"  #{num}: já anexado ({nome_arq}), pulei")
                    continue
                self.stdout.write(self.style.HTTP_INFO(f"  #{num}: {nome_arq}"))
                if dry:
                    continue
                with transaction.atomic():
                    caminho = os.path.join(pasta, arq)
                    with open(caminho, "rb") as fh:
                        doc = Documento(
                            negocio=neg,
                            tipo=TipoDocumento.CONTRATO,
                            descricao=f"Contrato {num} (original)",
                            criado_por=usuario,
                            empresa=empresa,
                        )
                        doc.arquivo.save(nome_arq, File(fh), save=True)
                anexados += 1
                self.stdout.write(self.style.SUCCESS("     → anexado"))
        finally:
            limpar_empresa_atual()

        self.stdout.write(self.style.WARNING(
            f"\nResumo: {anexados} anexados, {pulados} já existiam, {sem_arquivo} sem arquivo."))
        if dry:
            self.stdout.write("Rode sem --dry-run (com settings de produção) para anexar de verdade.")

    def _escolher(self, neg, candidatos):
        """Escolhe o arquivo certo. Com mais de um (número repetido), desempata pelo nome."""
        if not candidatos:
            return None
        if len(candidatos) == 1:
            return candidatos[0]
        nomes = [sem_acento(p.pessoa.nome) for p in neg.partes.all()]
        primeiros = {n.split()[0] for n in nomes if n.split()}
        for arq in candidatos:
            alvo = sem_acento(arq)
            if any(pn in alvo for pn in primeiros):
                return arq
        return candidatos[0]
