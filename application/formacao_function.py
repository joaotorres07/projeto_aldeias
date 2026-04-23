import json
import logging
import pymysql
from datetime import datetime
from database_function import insert_formacao_db

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def abrir_formacao(body):
    try:
        nucleo = body['nucleo']
        tema = body['tema']
        cpf_formador = body.get('cpf_formador')
        data_formacao = datetime.now().strftime('%Y-%m-%d')

        logger.info(f"Abrindo formação: Data: {data_formacao} - Núcleo: {nucleo}")
        insert_formacao_db(nucleo, tema, data_formacao, cpf_formador)
        logger.info("Formação aberta com sucesso.")

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Formação aberta com sucesso."})
        }
    except pymysql.err.IntegrityError as e:
        if e.args[0] == 1062:
            msg_error = "Já existe uma formação com esse tema nesse núcleo na data de hoje."
        else:
            msg_error = f"Erro ao abrir formação: {str(e)}"
        logger.error(msg_error)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": msg_error}, ensure_ascii=False)
        }
    except Exception as e:
        msg_error = f"Erro ao abrir formação: {str(e)}"
        logger.error(msg_error)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": msg_error}, ensure_ascii=False)
        }

