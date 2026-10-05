#!/usr/bin/env bash
#
# Restaura um backup num banco de destino.
# Uso: scripts/restore.sh caminho/para/backup.sql.gz "postgres://usuario:senha@host/banco"
#
# ATENÇÃO: restaure sempre primeiro num banco DESCARTÁVEL para conferir, nunca
# direto em produção. O destino deve estar vazio.
set -euo pipefail

arquivo="${1:?informe o arquivo .sql.gz}"
destino="${2:?informe a URL do banco de destino}"

echo "Restaurando ${arquivo} em ${destino} ..."
gunzip -c "${arquivo}" | psql "${destino}" -v ON_ERROR_STOP=1
echo "Restauração concluída."
