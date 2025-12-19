import datetime
import json
import os
import logging
import pymysql

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    try:
        logger.info(f"Event received: {json.dumps(event)}")
        body = event["body"]
        logger.info(f"Start insert/update aldeeiro. CPF: {body['cpf']}")
        insert_update_user(body)

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Aldeeiro inserted/updated successfully."
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


def insert_update_user(body):
    connection = get_db_connection()
    try:
        ja_serviu = body["serviu"][0]
        with connection.cursor() as cursor:
            sql = """
                  INSERT INTO db_aldeias.tb_aldeeiro
                    (nome, cpf, data_nascimento, telefone, email, nucleo, ja_serviu, data_insert, ativo)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    telefone = VALUES(telefone),
                    email = VALUES(email),
                    nucleo = VALUES(nucleo),
                    data_update = %s
            """
            now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            values = (
                body["nome"],
                body["cpf"],
                body["data_nascimento"],  # formato YYYY-MM-DD
                body["telefone"],
                body["email"],
                body["nucleo"],
                1 if ja_serviu == 'true' else 0,
                now,  # data_insert
                1,  # ativo
                now # data_update (somente no update)
            )
            cursor.execute(sql, values)
        connection.commit()

        if body.get("aldeias_fez") is not None and body.get("aldeias_fez") != []:
            insert_aldeias_fez(connection, connection.cursor(), body["cpf"], body.get("aldeias_fez"))
        if ja_serviu == 'true':
            if body.get("aldeias_serviu") is not None and body.get("aldeias_serviu") != []:
                insert_aldeias_serviu(connection, connection.cursor(), body["cpf"], body.get("aldeias_serviu"))

            if body.get("equipes") is not None and body.get("equipes") != []:
                insert_equipes(connection, connection.cursor(), body["cpf"], body.get("equipes"))

        logger.info("User inserted/updated successfully.")
    except Exception as e:
        msg_error = f"Error inserting/updating aldeeiro cpf: {body["cpf"]} | Exception: {str(e)}"
        logger.error(msg_error)
        raise Exception(msg_error)
    finally:
        connection.close()


def insert_aldeias_fez(connection, cursor, aldeeiro_cpf, aldeias_fez):
    try:
        sql_delete = """ DELETE FROM db_aldeias.tb_aldeeiro_aldeia_fez WHERE cpf_aldeeiro = %s"""
        cursor.execute(sql_delete, aldeeiro_cpf)
        sql_insert = """
            INSERT INTO db_aldeias.tb_aldeeiro_aldeia_fez (cpf_aldeeiro, id_aldeia)
            VALUES (%s, %s)
        """
        for id_aldeia in aldeias_fez:
            cursor.execute(sql_insert, (aldeeiro_cpf, id_aldeia))
        connection.commit()
        logger.info("Aldeias fez inserted successfully.")
    except Exception as e:
        msg_error = f"Error inserting aldeias fez for aldeeiro cpf: {aldeeiro_cpf} | Exception: {str(e)}"
        logger.error(msg_error)
        raise Exception(msg_error)


def insert_aldeias_serviu(connection, cursor, aldeeiro_cpf, aldeias_serviu):
    try:
        sql_delete = """ DELETE FROM db_aldeias.tb_aldeeiro_aldeia_serviu WHERE cpf_aldeeiro = %s"""
        cursor.execute(sql_delete, aldeeiro_cpf)
        sql_insert = """
            INSERT INTO db_aldeias.tb_aldeeiro_aldeia_serviu (cpf_aldeeiro, id_aldeia)
            VALUES (%s, %s)
        """
        for id_aldeia in aldeias_serviu:
            cursor.execute(sql_insert, (aldeeiro_cpf, id_aldeia))
        connection.commit()
        logger.info("Aldeias serviu inserted successfully.")
    except Exception as e:
        msg_error = f"Error inserting aldeias serviu for aldeeiro cpf: {aldeeiro_cpf} | Exception: {str(e)}"
        logger.error(msg_error)
        raise Exception(msg_error)


def insert_equipes(connection, cursor, aldeeiro_cpf, equipes):
    try:
        sql_delete = """ DELETE FROM db_aldeias.tb_aldeeiro_equipe WHERE cpf_aldeeiro = %s """
        cursor.execute(sql_delete, aldeeiro_cpf)

        sql_insert = """
            INSERT INTO db_aldeias.tb_aldeeiro_equipe (cpf_aldeeiro, id_equipe)
            VALUES (%s, %s)
        """
        for id_equipe in equipes:
            cursor.execute(sql_insert, (aldeeiro_cpf, id_equipe))
        connection.commit()
        logger.info("Equipes inserted successfully.")
    except Exception as e:
        msg_error = f"Error inserting equipes for aldeeiro cpf: {aldeeiro_cpf} | Exception: {str(e)}"
        logger.error(msg_error)
        raise Exception(msg_error)

#EVENTO TESTE LOCAL
'''
event = {
  "resource": "/aldeeiro",
  "path": "/aldeeiro",
  "httpMethod": "POST",
  "headers": {
    "Content-Type": "application/json"
  },
  "requestContext": {
    "resourcePath": "/aldeeiro",
    "httpMethod": "POST",
    "stage": "prod",
    "identity": {
      "sourceIp": "187.10.20.30",
      "userAgent": "PostmanRuntime/7.36.0"
    }
  },
  "body": "{\n    \"nome\": \"João da Silva\",\n    \"cpf\": \"12345678900\",\n    \"data_nascimento\": \"1990-05-20\",\n    \"telefone\": \"11999998887\",\n    \"email\": \"joao.silva@emailteste.com\",\n    \"nucleo\": 2,\n    \"ativo\": true\n  }",
  "isBase64Encoded": False
}
lambda_handler(event, None)
'''