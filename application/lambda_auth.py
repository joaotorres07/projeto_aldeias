import json
import os
import logging
import pymysql
from werkzeug.security import generate_password_hash, check_password_hash

logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_format = logging.StreamHandler()
log_format.setFormatter(formatter)
logger.addHandler(log_format)


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


def cadastrar_usuario(body):
    """Cadastra um novo usuário. Permite apenas 1 usuário no sistema."""
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            # Verifica se já existe algum usuário cadastrado
            cursor.execute("SELECT COUNT(*) as total FROM db_aldeias.tb_usuario")
            result = cursor.fetchone()
            if result['total'] >= 1:
                return {
                    "statusCode": 403,
                    "body": json.dumps({"error": "Já existe um usuário cadastrado. Apenas 1 acesso é permitido."})
                }

            senha_hash = generate_password_hash(body['senha'])
            sql = """INSERT INTO db_aldeias.tb_usuario (nome, email, senha_hash) VALUES (%s, %s, %s)"""
            cursor.execute(sql, (body['nome'], body['email'], senha_hash))
        connection.commit()
        logger.info(f"Usuário cadastrado com sucesso: {body['email']}")
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Usuário cadastrado com sucesso."})
        }
    except Exception as e:
        msg_error = f"Erro ao cadastrar usuário: {str(e)}"
        logger.error(msg_error)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": msg_error})
        }
    finally:
        connection.close()


def login(body):
    """Valida login do usuário."""
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM db_aldeias.tb_usuario WHERE email = %s AND ativo = 1"
            cursor.execute(sql, (body['email'],))
            usuario = cursor.fetchone()

            if usuario and check_password_hash(usuario['senha_hash'], body['senha']):
                logger.info(f"Login bem-sucedido: {body['email']}")
                return {
                    "statusCode": 200,
                    "body": json.dumps({"message": "Login bem-sucedido."}),
                    "usuario": usuario
                }
            else:
                logger.warning(f"Tentativa de login inválida: {body['email']}")
                return {
                    "statusCode": 401,
                    "body": json.dumps({"error": "Email ou senha inválidos."})
                }
    except Exception as e:
        msg_error = f"Erro no login: {str(e)}"
        logger.error(msg_error)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": msg_error})
        }
    finally:
        connection.close()


def recuperar_senha(body):
    """Reseta a senha do usuário pelo email."""
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT id FROM db_aldeias.tb_usuario WHERE email = %s AND ativo = 1"
            cursor.execute(sql, (body['email'],))
            usuario = cursor.fetchone()

            if not usuario:
                return {
                    "statusCode": 404,
                    "body": json.dumps({"error": "Email não encontrado."})
                }

            nova_senha_hash = generate_password_hash(body['nova_senha'])
            sql_update = "UPDATE db_aldeias.tb_usuario SET senha_hash = %s WHERE id = %s"
            cursor.execute(sql_update, (nova_senha_hash, usuario['id']))
        connection.commit()
        logger.info(f"Senha recuperada com sucesso para: {body['email']}")
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Senha alterada com sucesso."})
        }
    except Exception as e:
        msg_error = f"Erro ao recuperar senha: {str(e)}"
        logger.error(msg_error)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": msg_error})
        }
    finally:
        connection.close()

