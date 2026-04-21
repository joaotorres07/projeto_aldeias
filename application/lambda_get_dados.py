import json
import os
import logging
import pymysql
from decimal import Decimal

logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_format = logging.StreamHandler()
log_format.setFormatter(formatter)
logger.addHandler(log_format)


def lambda_handler(event, context):
    logger.info("Finding dados das aldeias.")
    equipes = select_equipes()
    logger.info("Equipes recuperadas com sucesso.")
    aldeias_fez = select_aldeias()
    aldeias_serviu = aldeias_fez
    logger.info("Aldeias recuperadas com sucesso.")
    nucleos = select_nucleos()
    logger.info("Nucleos recuperados com sucesso.")

    response_body = {
        "equipes": equipes,
        "aldeias_fez": aldeias_fez,
        "aldeias_serviu": aldeias_serviu,
        "nucleos": nucleos
    }

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(
            response_body,
            default=decimal_serializer,
            ensure_ascii=False
        )
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


def select_equipes():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = """ SELECT id, nome FROM db_aldeias.tb_equipes """
            cursor.execute(sql)
            resultados = cursor.fetchall()
    except Exception as e:
        msg_error = f"Error get equipes in database | Exception: {str(e)}"
        logger.error(msg_error)
        raise Exception(msg_error)
    finally:
        connection.close()

    return resultados


def select_aldeias():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = """ SELECT * FROM db_aldeias.tb_aldeia """
            cursor.execute(sql)
            resultados = cursor.fetchall()
    except Exception as e:
        msg_error = f"Error get aldeias in database | Exception: {str(e)}"
        logger.error(msg_error)
        raise Exception(msg_error)
    finally:
        connection.close()

    return resultados


def select_nucleos():
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = """ SELECT * FROM db_aldeias.tb_nucleo """
            cursor.execute(sql)
            resultados = cursor.fetchall()
    except Exception as e:
        msg_error = f"Error get nucleos in database | Exception: {str(e)}"
        logger.error(msg_error)
        raise Exception(msg_error)
    finally:
        connection.close()

    return resultados


def decimal_serializer(obj):
    if isinstance(obj, Decimal):
        return int(obj)
    raise TypeError(f"Tipo não serializável: {type(obj)}")

#lambda_handler('', '')