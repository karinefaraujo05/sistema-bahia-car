"""Cria o bucket de mídia no storage S3 LOCAL (s3mock) do docker-compose.

Só para o ambiente local: em produção o bucket do Cloudflare R2 é criado uma
única vez, à mão. Aqui garantimos que `docker compose up` já sobe com o bucket
pronto, igual à produção. Idempotente e com retry (o s3mock demora uns segundos
para responder depois de subir).
"""

import os
import time

import boto3
from botocore.exceptions import ClientError, EndpointConnectionError

bucket = os.environ["AWS_STORAGE_BUCKET_NAME"]
client = boto3.client(
    "s3",
    endpoint_url=os.environ["AWS_S3_ENDPOINT_URL"],
    aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
    region_name=os.environ.get("AWS_S3_REGION_NAME", "us-east-1"),
)

for _ in range(30):
    try:
        client.create_bucket(Bucket=bucket)
        print(f"Bucket '{bucket}' criado.")
        break
    except ClientError as e:
        codigo = e.response.get("Error", {}).get("Code", "")
        if codigo in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
            print(f"Bucket '{bucket}' já existe.")
            break
        print("Storage ainda não pronto, tentando de novo...", codigo)
        time.sleep(1)
    except EndpointConnectionError:
        print("Storage ainda não respondeu, tentando de novo...")
        time.sleep(1)
else:
    raise SystemExit("Não consegui criar o bucket no storage local.")
