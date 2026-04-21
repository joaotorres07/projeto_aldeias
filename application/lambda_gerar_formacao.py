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
        nucleo = body['nucleo']
        data_formacao = datetime.datetime.now().strftime('%Y-%m-%d')
        logger.info(f"Abrindo formação: Data: {data_formacao} - Núcleo: {nucleo}")
        insert_formacao(nucleo, body['tema'], data_formacao)

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Formação aberta com successo."
            })
        }

    except Exception as e:
        msg_error = f"Error in lambda_handler: {str(e)}"
        logger.error(msg_error)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": msg_error})
        }


def insert_formacao(nucleo, tema, data_formacao):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = " INSERT INTO db_aldeias.tb_formacao (tema, data_formacao, nucleo) VALUES (%s, %s, %s) "

            values = (
                tema,
                data_formacao,
                nucleo
            )
            cursor.execute(sql, values)
        connection.commit()

        logger.info("Formação aberta com sucesso.")
    except pymysql.err.IntegrityError as e:
        if e.args[0] == 1062:
            msg_error = "Já existe uma formação com esse tema nesse núcleo na data de hoje."
        else:
            msg_error = f"Erro ao abrir formação: {str(e)}"
        logger.error(msg_error)
        raise Exception(msg_error)
    except Exception as e:
        msg_error = f"Erro ao abrir formação: Data: {data_formacao} Nucleo: {nucleo} | Exception: {str(e)}"
        logger.error(msg_error)
        raise Exception(msg_error)
    finally:
        connection.close()


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