import json
import logging
from database_function import inserir_atualizar_aldeeiro

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def salvar_aldeeiro(body):
    try:
        logger.info(f"Start insert/update aldeeiro. CPF: {body['cpf']}")
        inserir_atualizar_aldeeiro(body)
        logger.info("Aldeeiro inserted/updated successfully.")
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Aldeeiro inserted/updated successfully."})
        }
    except Exception as e:
        msg_error = f"Error in salvar_aldeeiro: {str(e)}"
        logger.error(msg_error)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": msg_error})
        }

