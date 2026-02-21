import json
import os
import logging
import pymysql
from twilio.rest import Client

logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(levelname)s - %(asctime)s - %(message)s')
log_format = logging.StreamHandler()
log_format.setFormatter(formatter)
logger.addHandler(log_format)


def lambda_handler(event, context):
    try:
        logger.info("Iniciando envio de mensagens WhatsApp")
        body = event.get("body", {})

        if isinstance(body, str):
            body = json.loads(body)

        mensagem = body.get('mensagem', '')

        if not mensagem:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Mensagem não fornecida"})
            }

        # Busca todos os números de telefone
        numeros = obter_numeros_telefone()

        # Envia mensagem para cada número
        resultados = enviar_whatsapp_em_massa(numeros, mensagem)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Mensagens enviadas com sucesso",
                "total": len(numeros),
                "enviadas": resultados['sucesso'],
                "falhas": resultados['falha']
            })
        }

    except Exception as e:
        msg_error = f"Erro ao enviar mensagens: {str(e)}"
        logger.error(msg_error)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": msg_error})
        }


def get_db_connection():
    try:
        connection = pymysql.connect(
            host=os.environ['DB_HOST'],
            user=os.environ['DB_USER'],
            password=os.environ['DB_PASSWORD'],
            database=os.environ['DB_NAME'],
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except Exception as e:
        msg_error = f"Erro ao conectar ao banco: {str(e)}"
        logger.error(msg_error)
        raise Exception(msg_error)


def obter_numeros_telefone():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT DISTINCT numero_telefone FROM db_aldeias.tb_aldeeiro WHERE numero_telefone IS NOT NULL"
            cursor.execute(sql)
            rows = cursor.fetchall()

            numeros = [row['numero_telefone'] for row in rows]
            logger.info(f"Total de números encontrados: {len(numeros)}")

            return numeros
    except Exception as e:
        msg_error = f"Erro ao buscar números de telefone: {str(e)}"
        logger.error(msg_error)
        raise Exception(msg_error)
    finally:
        connection.close()


def enviar_whatsapp_em_massa(numeros, mensagem):
    account_sid = os.environ['TWILIO_ACCOUNT_SID']
    auth_token = os.environ['TWILIO_AUTH_TOKEN']
    numero_origem = os.environ['TWILIO_WHATSAPP_NUMBER']

    client = Client(account_sid, auth_token)

    resultados = {'sucesso': 0, 'falha': 0}

    for numero in numeros:
        try:
            message = client.messages.create(
                from_=f'whatsapp:{numero_origem}',
                body=mensagem,
                to=f'whatsapp:{numero}'
            )

            logger.info(f"Mensagem enviada para {numero} - SID: {message.sid}")
            resultados['sucesso'] += 1

        except Exception as e:
            msg_error = f"Erro ao enviar para {numero}: {str(e)}"
            logger.error(msg_error)
            resultados['falha'] += 1

    return resultados
