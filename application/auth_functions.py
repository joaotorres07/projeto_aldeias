import json
import os
import logging
import random
import string
import boto3
from werkzeug.security import generate_password_hash, check_password_hash
from database_function import (
    buscar_usuario_por_email, email_ja_cadastrado, inserir_usuario,
    buscar_usuario_id_por_email, invalidar_codigos_recuperacao,
    inserir_codigo_recuperacao, validar_codigo_recuperacao,
    marcar_codigo_usado, atualizar_senha_usuario
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def gerar_codigo(tamanho=6):
    return ''.join(random.choices(string.digits, k=tamanho))


def enviar_email_codigo(email, codigo):
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


def cadastrar_usuario_fn(body):
    try:
        if email_ja_cadastrado(body['email']):
            return {
                "statusCode": 403,
                "body": json.dumps({"error": "Este email já está cadastrado."})
            }

        senha_hash = generate_password_hash(body['senha'])
        inserir_usuario(body['nome'], body['email'], senha_hash)
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


def login(body):
    try:
        usuario = buscar_usuario_por_email(body['email'])

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


def solicitar_recuperacao(body):
    try:
        usuario_id = buscar_usuario_id_por_email(body['email'])
        if not usuario_id:
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "Email não encontrado."})
            }

        invalidar_codigos_recuperacao(usuario_id)
        codigo = gerar_codigo()
        inserir_codigo_recuperacao(usuario_id, codigo)
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


def confirmar_recuperacao(body):
    try:
        usuario_id = buscar_usuario_id_por_email(body['email'])
        if not usuario_id:
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "Email não encontrado."})
            }

        token = validar_codigo_recuperacao(usuario_id, body['codigo'])
        if not token:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Código inválido ou expirado."})
            }

        marcar_codigo_usado(token['id'])
        nova_senha_hash = generate_password_hash(body['nova_senha'])
        atualizar_senha_usuario(usuario_id, nova_senha_hash)

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

