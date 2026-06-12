import json
import os
import logging
import boto3
from io import BytesIO
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def _get_s3_client():
    return boto3.client(
        's3',
        region_name=os.environ.get('AWS_REGION', 'us-east-1'),
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY')
    )


def download_arquivo_s3(s3_key):
    try:
        bucket = os.environ.get('S3_BUCKET_NAME', 'aldeias-arquivos')
        if not s3_key:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Chave do arquivo (s3_key) não informada."})
            }

        logger.info(f"Baixando arquivo do S3: {s3_key}")
        s3_client = _get_s3_client()
        try:
            response = s3_client.get_object(Bucket=bucket, Key=s3_key)
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return {
                    "statusCode": 404,
                    "body": json.dumps({"error": f"Arquivo não encontrado: {s3_key}"})
                }
            raise

        file_content = response['Body'].read()
        content_type = response.get('ContentType', 'application/octet-stream')
        nome_arquivo = s3_key.split('/')[-1]

        logger.info(f"Arquivo baixado com sucesso: {nome_arquivo} ({len(file_content)} bytes)")
        buffer = BytesIO(file_content)
        buffer.seek(0)
        return {
            "statusCode": 200,
            "buffer": buffer,
            "nome_arquivo": nome_arquivo,
            "content_type": content_type
        }
    except Exception as e:
        msg_error = f"Erro ao baixar arquivo do S3: {str(e)}"
        logger.error(msg_error)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": msg_error})
        }


def listar_arquivos(equipe):
    try:
        bucket = os.environ.get('S3_BUCKET_NAME', 'aldeias-arquivos')
        prefix = f"Equipes/{equipe}/"

        s3_client = _get_s3_client()

        response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
        arquivos = []

        for obj in response.get('Contents', []):
            key = obj['Key']
            if key == prefix:
                continue
            nome = key.split('/')[-1]
            if nome:
                arquivos.append({
                    "nome": nome,
                    "s3_key": key,
                    "tamanho": obj['Size'],
                    "ultima_modificacao": obj['LastModified'].strftime('%d/%m/%Y %H:%M')
                })

        logger.info(f"Listados {len(arquivos)} arquivos para equipe: {equipe}")
        return arquivos
    except Exception as e:
        logger.error(f"Erro ao listar arquivos da equipe {equipe}: {str(e)}")
        return []
