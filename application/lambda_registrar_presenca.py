import datetime
import json
import os
import logging
import pymysql

logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_format = logging.StreamHandler()
log_format.setFormatter(formatter)
logger.addHandler(log_format)


def lambda_handler(event, context):
    try:
        logger.info(f"Event received: {json.dumps(event)}")
        body = event["body"]
        logger.info(f"Registrando presença do aldeeiro de CPF: {body['cpf']} | Data: {datetime.datetime.now().strftime('%Y-%m-%d')} | Núcleo: {body['nucleo']}")
        registrar_presenca(body)

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Presença registrada com successo."
            })
        }

    except Exception as e:
        msg_error = f"Error in lambda_handler: {str(e)}"
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
        msg_error = f"Error connecting to database: {str(e)}"
        logger.error(msg_error)
        raise Exception(msg_error)


def registrar_presenca(body):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM db_aldeias.tb_frequencia_aldeeiro WHERE cpf_aldeeiro = %s AND id_formacao = %s",
                (body['cpf'], body['id_formacao'])
            )
            if cursor.fetchone():
                raise Exception("Você já registrou presença nesta formação.")

            sql = " INSERT INTO db_aldeias.tb_frequencia_aldeeiro (cpf_aldeeiro, id_formacao, data_registro) VALUES (%s, %s, %s) "
            values = (
                body['cpf'],
                body['id_formacao'],
                datetime.datetime.now().strftime('%Y-%m-%d'),
            )
            cursor.execute(sql, values)
        connection.commit()

        logger.info(f"Presença registrada com sucesso. CPF: {body['cpf']} Data: {datetime.datetime.now().strftime('%Y-%m-%d')}")
    except Exception as e:
        msg_error = f"Error ao registrar presença: CPF: {body['cpf']} Data: {datetime.datetime.now().strftime('%Y-%m-%d')} Nucleo: {body['nucleo']} | Exception: {str(e)}"
        logger.error(msg_error)
        raise Exception(msg_error)
    finally:
        connection.close()