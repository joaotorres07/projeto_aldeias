import json
import os
import logging
import pymysql
import requests

logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(levelname)s - %(asctime)s - %(message)s')
log_format = logging.StreamHandler()
log_format.setFormatter(formatter)
logger.addHandler(log_format)


def lambda_handler(event, context):
    try:
        logger.info("Iniciando envio de mensagens WhatsApp via Meta")
        body = event.get("body", {})

        if isinstance(body, str):
            body = json.loads(body)

        mensagem = body.get('mensagem', '')
        template_name = body.get('template_name', None)

        if not mensagem and not template_name:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Mensagem ou template não fornecido"})
            }

        numeros = obter_numeros_telefone()
        if template_name:
            resultados = enviar_via_template(numeros, template_name, body.get('parametros', []))
        else:
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
    phone_number_id = os.environ['META_PHONE_NUMBER_ID']
    access_token = os.environ['META_ACCESS_TOKEN']
    url = f"https://graph.instagram.com/v18.0/{phone_number_id}/messages"

    resultados = {'sucesso': 0, 'falha': 0}

    for numero in numeros:
        try:
            payload = {
                "messaging_product": "whatsapp",
                "to": numero,
                "type": "text",
                "text": {
                    "body": mensagem
                }
            }

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()

            message_id = response.json().get('messages', [{}])[0].get('id')
            logger.info(f"Mensagem enviada para {numero} - Message ID: {message_id}")
            resultados['sucesso'] += 1

        except requests.exceptions.HTTPError as e:
            msg_error = f"Erro HTTP ao enviar para {numero}: {e.response.status_code} - {e.response.text}"
            logger.error(msg_error)
            resultados['falha'] += 1
        except Exception as e:
            msg_error = f"Erro ao enviar para {numero}: {str(e)}"
            logger.error(msg_error)
            resultados['falha'] += 1

    return resultados


def enviar_via_template(numeros, template_name, parametros):
    phone_number_id = os.environ['META_PHONE_NUMBER_ID']
    access_token = os.environ['META_ACCESS_TOKEN']
    url = f"https://graph.instagram.com/v18.0/{phone_number_id}/messages"

    resultados = {'sucesso': 0, 'falha': 0}

    for numero in numeros:
        try:
            payload = {
                "messaging_product": "whatsapp",
                "to": numero,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {
                        "code": "pt_BR"
                    }
                }
            }

            if parametros:
                payload["template"]["components"] = [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": param} for param in parametros
                        ]
                    }
                ]

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()

            message_id = response.json().get('messages', [{}])[0].get('id')
            logger.info(f"Template enviado para {numero} - Message ID: {message_id}")
            resultados['sucesso'] += 1

        except requests.exceptions.HTTPError as e:
            msg_error = f"Erro HTTP ao enviar para {numero}: {e.response.status_code} - {e.response.text}"
            logger.error(msg_error)
            resultados['falha'] += 1
        except Exception as e:
            msg_error = f"Erro ao enviar para {numero}: {str(e)}"
            logger.error(msg_error)
            resultados['falha'] += 1

    return resultados
