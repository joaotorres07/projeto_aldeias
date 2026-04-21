import json
import os
import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_format = logging.StreamHandler()
log_format.setFormatter(formatter)
logger.addHandler(log_format)


def lambda_handler(event, context):
    """Gera uma URL pré-assinada para download de arquivo no S3."""
    try:
        body = event.get("body", {})
        if isinstance(body, str):
            body = json.loads(body)

        bucket = os.environ.get('S3_BUCKET_NAME', 'aldeias-arquivos')
        s3_key = body.get('s3_key')

        if not s3_key:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Chave do arquivo (s3_key) não informada."})
            }

        logger.info(f"Gerando URL de download para: {s3_key}")

        s3_client = boto3.client(
            's3',
            region_name=os.environ.get('AWS_REGION', 'us-east-1')
        )

        # Verifica se o arquivo existe
        try:
            s3_client.head_object(Bucket=bucket, Key=s3_key)
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return {
                    "statusCode": 404,
                    "body": json.dumps({"error": f"Arquivo não encontrado: {s3_key}"})
                }
            raise

        # Gera URL pré-assinada válida por 5 minutos
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket,
                'Key': s3_key
            },
            ExpiresIn=300
        )

        logger.info(f"URL gerada com sucesso para: {s3_key}")
        return {
            "statusCode": 200,
            "body": json.dumps({"url": url, "arquivo": s3_key.split('/')[-1]})
        }

    except Exception as e:
        msg_error = f"Erro ao gerar URL de download: {str(e)}"
        logger.error(msg_error)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": msg_error})
        }


def listar_arquivos(equipe):
    """Lista arquivos de uma equipe no S3."""
    try:
        bucket = os.environ.get('S3_BUCKET_NAME', 'aldeias-arquivos')
        prefix = f"equipes/{equipe}/"

        s3_client = boto3.client(
            's3',
            region_name=os.environ.get('AWS_REGION', 'us-east-1')
        )

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

