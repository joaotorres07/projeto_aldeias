import json
import os
import logging
import pymysql
from decimal import Decimal

from application.lambda_get_dados import decimal_serializer

logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_format = logging.StreamHandler()
log_format.setFormatter(formatter)
logger.addHandler(log_format)


def lambda_handler(event, context):
    logger.info("Finding aldeiros...")
    try:
        filtros = event.get("body")
        data_result = select_aldeeiros_by(filtros)
        retorno_agrupado = agrupar_aldeeiros(data_result)
        retorno_lambda = {
            "statusCode": 200,
            "body": json.dumps(retorno_agrupado)

        }
    except Exception as e:
        msg_error = f"Error in lambda_handler: {str(e)}"
        logger.error(msg_error)
        retorno_lambda = {
            "statusCode": 500,
            "body": json.dumps({"error": msg_error})
        }

    return retorno_lambda


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


def select_aldeeiros_by(filtros):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = """SELECT a.nome as nome_aldeeiro, n.nome as nucleo, a.telefone as telefone_aldeeiro, e.nome as nome_equipe, 
                            ad.nome_aldeia as nome_aldeia_fez, ad2.nome_aldeia as aldeia_serviu 
                        FROM db_aldeias.tb_aldeeiro a
                        LEFT JOIN db_aldeias.tb_aldeeiro_aldeia_fez aaf ON aaf.cpf_aldeeiro = a.cpf
                        LEFT JOIN db_aldeias.tb_aldeeiro_aldeia_serviu aas ON aas.cpf_aldeeiro = a.cpf
                        LEFT JOIN db_aldeias.tb_aldeeiro_equipe ae ON ae.cpf_aldeeiro = a.cpf
                        INNER JOIN db_aldeias.tb_nucleo n ON n.id = a.nucleo
                        LEFT JOIN db_aldeias.tb_equipes e ON e.id = ae.id_equipe
                        LEFT JOIN db_aldeias.tb_aldeia ad ON ad.id = aaf.id_aldeia
                        LEFT JOIN db_aldeias.tb_aldeia ad2 ON ad2.id = aas.id_aldeia
                WHERE 1=1 
                  """
            params = []
            if filtros:
                if filtros.get("nome"):
                    sql += " AND a.nome LIKE %s "
                    params.append(f"%{filtros['nome']}%")

                if filtros.get("nucleo"):
                    sql += " AND n.id = %s"
                    params.append(filtros['nucleo'])

            cursor.execute(sql, params)
            return cursor.fetchall()
    except Exception as e:
        msg_error = f"Error querying aldeiros: {str(e)}"
        logger.error(msg_error)
        raise Exception(msg_error)
    finally:
        connection.close()


def agrupar_aldeeiros(rows):
    agrupado = {}
    for r in rows:
        nome = r["nome_aldeeiro"]

        if nome not in agrupado:
            agrupado[nome] = {
                "nome_aldeeiro": nome,
                "telefone": r["telefone_aldeeiro"],
                "nucleo": r["nucleo"],
                "equipes": set(),
                "aldeias_fez": set(),
                "aldeias_serviu": set()
            }

        # Equipes
        if r.get("nome_equipe"):
            agrupado[nome]["equipes"].add(r["nome_equipe"])

        # Aldeias que fez
        if r.get("nome_aldeia_fez"):
            agrupado[nome]["aldeias_fez"].add(r["nome_aldeia_fez"])

        # Aldeias que serviu
        if r.get("aldeia_serviu"):
            agrupado[nome]["aldeias_serviu"].add(r["aldeia_serviu"])

    # Converter sets para listas (JSON-friendly)
    resultado = []
    for a in agrupado.values():
        a["equipes"] = list(a["equipes"])
        a["aldeias_fez"] = list(a["aldeias_fez"])
        a["aldeias_serviu"] = list(a["aldeias_serviu"])
        resultado.append(a)

    return resultado
