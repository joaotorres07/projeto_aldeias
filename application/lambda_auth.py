import json
import os
import logging
import random
import string
import pymysql
import boto3
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


def gerar_codigo(tamanho=6):
    """Gera código numérico aleatório de 6 dígitos."""
    return ''.join(random.choices(string.digits, k=tamanho))


def enviar_email_codigo(email, codigo):
    """Envia o código de recuperação via AWS SES."""
    ses = boto3.client('ses', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
    ses.send_email(
        Source=os.environ['EMAIL_REMETENTE'],
        Destination={'ToAddresses': [email]},
        Message={
            'Subject': {'Data': 'Código de recuperação de senha - Sistema Aldeias', 'Charset': 'UTF-8'},
            'Body': {
                'Html': {
                    'Data': f"""
                        <h2>Recuperação de Senha</h2>
                        <p>Seu código de verificação é:</p>
                        <h1 style="letter-spacing: 8px; color: #5a67d8;">{codigo}</h1>
                        <p>Este código expira em <strong>10 minutos</strong>.</p>
                        <p>Se você não solicitou a recuperação de senha, ignore este email.</p>
                    """,
                    'Charset': 'UTF-8'
                }
            }
        }
    )


def cadastrar_usuario(body):
    """Cadastra um novo usuário. Impede email duplicado."""
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM db_aldeias.tb_usuario WHERE email = %s", (body['email'],))
            if cursor.fetchone() is not None:
                return {
                    "statusCode": 403,
                    "body": json.dumps({"error": "Este email já está cadastrado."})
                }

            senha_hash = generate_password_hash(body['senha'])
            sql = "INSERT INTO db_aldeias.tb_usuario (nome, email, senha_hash) VALUES (%s, %s, %s)"
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


def solicitar_recuperacao(body):
    """Etapa 1: gera código de 6 dígitos, salva no banco e envia por email."""
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM db_aldeias.tb_usuario WHERE email = %s AND ativo = 1",
                (body['email'],)
            )
            usuario = cursor.fetchone()
            if not usuario:
                return {
                    "statusCode": 404,
                    "body": json.dumps({"error": "Email não encontrado."})
                }

            # Invalida códigos anteriores não usados
            cursor.execute(
                "UPDATE db_aldeias.tb_recuperacao_senha SET usado = 1 WHERE usuario_id = %s AND usado = 0",
                (usuario['id'],)
            )

            codigo = gerar_codigo()
            cursor.execute(
                "INSERT INTO db_aldeias.tb_recuperacao_senha (usuario_id, codigo) VALUES (%s, %s)",
                (usuario['id'], codigo)
            )
        connection.commit()

        enviar_email_codigo(body['email'], codigo)
        logger.info(f"Código de recuperação enviado para: {body['email']}")

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Código enviado para o email informado."})
        }
    except Exception as e:
        msg_error = f"Erro ao solicitar recuperação: {str(e)}"
        logger.error(msg_error)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": msg_error})
        }
    finally:
        connection.close()


def confirmar_recuperacao(body):
    """Etapa 2: valida código (10 min) e altera a senha."""
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM db_aldeias.tb_usuario WHERE email = %s AND ativo = 1",
                (body['email'],)
            )
            usuario = cursor.fetchone()
            if not usuario:
                return {
                    "statusCode": 404,
                    "body": json.dumps({"error": "Email não encontrado."})
                }

            # Busca código válido: não usado e criado há no máximo 10 minutos
            cursor.execute(
                """SELECT id FROM db_aldeias.tb_recuperacao_senha
                   WHERE usuario_id = %s AND codigo = %s AND usado = 0
                   AND criado_em >= NOW() - INTERVAL 10 MINUTE""",
                (usuario['id'], body['codigo'])
            )
            token = cursor.fetchone()

            if not token:
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "Código inválido ou expirado."})
                }

            # Marca código como usado
            cursor.execute(
                "UPDATE db_aldeias.tb_recuperacao_senha SET usado = 1 WHERE id = %s",
                (token['id'],)
            )

            # Atualiza senha
            nova_senha_hash = generate_password_hash(body['nova_senha'])
            cursor.execute(
                "UPDATE db_aldeias.tb_usuario SET senha_hash = %s WHERE id = %s",
                (nova_senha_hash, usuario['id'])
            )
        connection.commit()
        logger.info(f"Senha alterada com sucesso para: {body['email']}")
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Senha alterada com sucesso."})
        }
    except Exception as e:
        msg_error = f"Erro ao confirmar recuperação: {str(e)}"
        logger.error(msg_error)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": msg_error})
        }
    finally:
        connection.close()
