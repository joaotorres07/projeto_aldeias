import json
import logging
from datetime import datetime
from database_function import verificar_presenca_existente, inserir_presenca

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def registrar_presenca(body):
    try:
        cpf = body['cpf']
        id_formacao = body['id_formacao']
        data_registro = datetime.now().strftime('%Y-%m-%d')

        logger.info(f"Registrando presença - CPF: {cpf} | Formação: {id_formacao} | Data: {data_registro}")

        if verificar_presenca_existente(cpf, id_formacao):
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Você já registrou presença nesta formação."})
            }

        inserir_presenca(cpf, id_formacao, data_registro)
        logger.info(f"Presença registrada com sucesso. CPF: {cpf}")

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Presença registrada com sucesso."})
        }
    except Exception as e:
        msg_error = f"Erro ao registrar presença: {str(e)}"
        logger.error(msg_error)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": msg_error})
        }

