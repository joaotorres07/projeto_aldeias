import json
import os
import logging
import requests
from database_function import obter_numeros_telefone

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def enviar_whatsapp(body):
    try:
        logger.info("Iniciando envio de mensagens WhatsApp via Meta")

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


def enviar_whatsapp_em_massa(numeros, mensagem):
    phone_number_id = os.environ['META_PHONE_NUMBER_ID']
    access_token = os.environ['META_ACCESS_TOKEN']
    url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"

    resultados = {'sucesso': 0, 'falha': 0}

    for numero in numeros:
        try:
            payload = {
                "messaging_product": "whatsapp",
                "to": numero,
                "type": "text",
                "text": {"body": mensagem}
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
            logger.error(f"Erro HTTP ao enviar para {numero}: {e.response.status_code} - {e.response.text}")
            resultados['falha'] += 1
        except Exception as e:
            logger.error(f"Erro ao enviar para {numero}: {str(e)}")
            resultados['falha'] += 1

    return resultados


def enviar_via_template(numeros, template_name, parametros):
    phone_number_id = os.environ['META_PHONE_NUMBER_ID']
    access_token = os.environ['META_ACCESS_TOKEN']
    url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"

    resultados = {'sucesso': 0, 'falha': 0}

    for numero in numeros:
        try:
            payload = {
                "messaging_product": "whatsapp",
                "to": numero,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": "pt_BR"}
                }
            }

            if parametros:
                payload["template"]["components"] = [
                    {
                        "type": "body",
                        "parameters": [{"type": "text", "text": param} for param in parametros]
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
            logger.error(f"Erro HTTP ao enviar para {numero}: {e.response.status_code} - {e.response.text}")
            resultados['falha'] += 1
        except Exception as e:
            logger.error(f"Erro ao enviar para {numero}: {str(e)}")
            resultados['falha'] += 1

    return resultados

