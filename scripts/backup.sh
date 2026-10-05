#!/usr/bin/env bash
#
# Backup do banco: dump compactado enviado para o bucket de backup (S3/R2/B2).
# Mantém 30 cópias diárias e 12 mensais.
#
# Variáveis de ambiente esperadas:
#   DATABASE_URL          conexão do banco de origem
#   BACKUP_BUCKET         nome do bucket de backup (diferente do bucket de mídia)
#   AWS_S3_ENDPOINT_URL   endpoint S3 (ex.: https://<conta>.r2.cloudflarestorage.com)
#   AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY  credenciais do bucket
#
# Requer: pg_dump e aws cli.
set -euo pipefail

: "${DATABASE_URL:?defina DATABASE_URL}"
: "${BACKUP_BUCKET:?defina BACKUP_BUCKET}"
: "${AWS_S3_ENDPOINT_URL:?defina AWS_S3_ENDPOINT_URL}"

stamp="$(date +%Y%m%d-%H%M%S)"
arquivo="bahiacar-${stamp}.sql.gz"
destino="/tmp/${arquivo}"

echo "Gerando dump..."
pg_dump "${DATABASE_URL}" --no-owner --no-privileges | gzip -9 >"${destino}"

echo "Enviando diário..."
aws s3 cp "${destino}" "s3://${BACKUP_BUCKET}/diarios/${arquivo}" \
    --endpoint-url "${AWS_S3_ENDPOINT_URL}"

# No primeiro dia do mês, guarda também uma cópia mensal.
if [ "$(date +%d)" = "01" ]; then
    echo "Enviando mensal..."
    aws s3 cp "${destino}" "s3://${BACKUP_BUCKET}/mensais/${arquivo}" \
        --endpoint-url "${AWS_S3_ENDPOINT_URL}"
fi

rm -f "${destino}"

# Retenção: mantém apenas as N cópias mais recentes de cada pasta.
podar() {
    local pasta="$1" manter="$2"
    local nomes total remover
    mapfile -t nomes < <(
        aws s3 ls "s3://${BACKUP_BUCKET}/${pasta}/" --endpoint-url "${AWS_S3_ENDPOINT_URL}" \
            | awk '{print $4}' | grep -v '^$' | sort
    )
    total=${#nomes[@]}
    remover=$((total - manter))
    for ((i = 0; i < remover; i++)); do
        echo "Removendo antigo: ${pasta}/${nomes[$i]}"
        aws s3 rm "s3://${BACKUP_BUCKET}/${pasta}/${nomes[$i]}" \
            --endpoint-url "${AWS_S3_ENDPOINT_URL}"
    done
}

podar diarios 30
podar mensais 12

echo "Backup concluído: ${arquivo}"
