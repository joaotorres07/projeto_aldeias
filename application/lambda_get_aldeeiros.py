import json
import os
import logging
import pymysql
from decimal import Decimal

try:
    from application.lambda_get_dados import decimal_serializer
except ImportError:
    from lambda_get_dados import decimal_serializer

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
            "body": json.dumps(retorno_agrupado, default=decimal_serializer, ensure_ascii=False)

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
            sql = """SELECT a.cpf as cpf, a.nome as nome_aldeeiro, n.nome as nucleo, a.telefone as telefone_aldeeiro, e.nome as nome_equipe, 
                            ad.nome_aldeia as nome_aldeia_fez, ad2.nome_aldeia as aldeia_serviu,
                            a.logradouro, a.numero, a.complemento, a.bairro, a.cidade, a.uf 
                        FROM db_aldeias.tb_aldeeiro a
                        LEFT JOIN db_aldeias.tb_aldeeiro_aldeia_fez aaf ON aaf.cpf_aldeeiro = a.cpf
                        LEFT JOIN db_aldeias.tb_aldeeiro_aldeia_serviu aas ON aas.cpf_aldeeiro = a.cpf
                        LEFT JOIN db_aldeias.tb_aldeeiro_equipe ae ON ae.cpf_aldeeiro = a.cpf
                        INNER JOIN db_aldeias.tb_nucleo n ON n.id = a.nucleo
                        LEFT JOIN db_aldeias.tb_equipes e ON e.id = ae.id_equipe
                        LEFT JOIN db_aldeias.tb_aldeia ad ON ad.id = aaf.id_aldeia
                        LEFT JOIN db_aldeias.tb_aldeia ad2 ON ad2.id = aas.id_aldeia
                WHERE a.ativo = 1
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
        cpf = r["cpf"]

        if cpf not in agrupado:
            # Montar endereço concatenado
            partes_endereco = []
            if r.get("logradouro"):
                partes_endereco.append(r["logradouro"])
            if r.get("numero"):
                partes_endereco.append(r["numero"])
            if r.get("complemento"):
                partes_endereco.append(r["complemento"])
            if r.get("bairro"):
                partes_endereco.append(r["bairro"])
            if r.get("cidade"):
                partes_endereco.append(r["cidade"])
            if r.get("uf"):
                partes_endereco.append(r["uf"])
            endereco = ", ".join(partes_endereco) if partes_endereco else ""

            agrupado[cpf] = {
                "cpf": cpf,
                "nome_aldeeiro": r["nome_aldeeiro"],
                "telefone": r["telefone_aldeeiro"],
                "nucleo": r["nucleo"],
                "endereco": endereco,
                "equipes": set(),
                "aldeias_fez": set(),
                "aldeias_serviu": set()
            }

        if r.get("nome_equipe"):
            agrupado[cpf]["equipes"].add(r["nome_equipe"])

        if r.get("nome_aldeia_fez"):
            agrupado[cpf]["aldeias_fez"].add(r["nome_aldeia_fez"])

        if r.get("aldeia_serviu"):
            agrupado[cpf]["aldeias_serviu"].add(r["aldeia_serviu"])

    resultado = []
    for a in agrupado.values():
        a["equipes"] = list(a["equipes"])
        a["aldeias_fez"] = list(a["aldeias_fez"])
        a["aldeias_serviu"] = list(a["aldeias_serviu"])
        resultado.append(a)

    return resultado
