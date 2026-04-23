import json
import logging
from decimal import Decimal
from datetime import datetime, date
from database_function import select_equipes, select_aldeias, select_nucleos

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def decimal_serializer(obj):
    if isinstance(obj, Decimal):
        return int(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Tipo não serializável: {type(obj)}")


def get_dados_aldeias():
    try:
        logger.info("Buscando dados das aldeias.")
        equipes = select_equipes()
        aldeias_fez = select_aldeias()
        aldeias_serviu = aldeias_fez
        nucleos = select_nucleos()

        response_body = {
            "equipes": equipes,
            "aldeias_fez": aldeias_fez,
            "aldeias_serviu": aldeias_serviu,
            "nucleos": nucleos
        }

        return {
            "statusCode": 200,
            "body": json.dumps(response_body, default=decimal_serializer, ensure_ascii=False)
        }
    except Exception as e:
        msg_error = f"Erro ao buscar dados: {str(e)}"
        logger.error(msg_error)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": msg_error})
        }

