import os
import logging
import pymysql
from datetime import datetime
from time import time
from dbutils.pooled_db import PooledDB

logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_format = logging.StreamHandler()
log_format.setFormatter(formatter)
logger.addHandler(log_format)

# ==================== CONNECTION POOL ====================

_pool = None


def _get_pool():
    global _pool
    if _pool is None:
        _pool = PooledDB(
            creator=pymysql,
            maxconnections=10,
            mincached=2,
            maxcached=5,
            blocking=True,
            host=os.environ['DB_HOST'],
            user=os.environ['DB_USER'],
            password=os.environ['DB_PASSWORD'],
            database=os.environ['DB_NAME'],
            cursorclass=pymysql.cursors.DictCursor
        )
        logger.info("Database connection pool initialized.")
    return _pool


def get_db_connection():
    try:
        return _get_pool().connection()
    except Exception as e:
        msg_error = f"Error connecting to database: {str(e)}"
        logger.error(msg_error)
        raise Exception(msg_error)


# ==================== CACHE ====================

_cache = {}
CACHE_TTL = 300  # 5 minutos


def _cache_get(key):
    if key in _cache and (time() - _cache[key]['ts']) < CACHE_TTL:
        return _cache[key]['data']
    return None


def _cache_set(key, data):
    _cache[key] = {'data': data, 'ts': time()}


def invalidar_cache(key=None):
    global _cache
    if key:
        _cache.pop(key, None)
    else:
        _cache = {}


# ==================== ALDEEIRO ====================

def get_aldeeiro_por_email(email):
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM db_aldeias.tb_aldeeiro WHERE email = %s", (email,))
            return cursor.fetchone()
    except Exception:
        return None
    finally:
        if connection:
            connection.close()


def get_aldeeiro_relacoes(cpf):
    connection = None
    result = {'aldeias_fez': [], 'aldeias_serviu': []}
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT aaf.id, aaf.id_aldeia, ad.nome_aldeia, aaf.data_aldeia, aaf.id_nucleo, n.nome as nome_nucleo
                FROM db_aldeias.tb_aldeeiro_aldeia_fez aaf
                LEFT JOIN db_aldeias.tb_aldeia ad ON ad.id = aaf.id_aldeia
                LEFT JOIN db_aldeias.tb_nucleo n ON n.id = aaf.id_nucleo
                WHERE aaf.cpf_aldeeiro = %s
            """, (cpf,))
            for r in cursor.fetchall():
                r['id_aldeia'] = int(r['id_aldeia']) if r['id_aldeia'] else r['id_aldeia']
                if r.get('data_aldeia'):
                    r['data_aldeia'] = r['data_aldeia'].isoformat() if hasattr(r['data_aldeia'], 'isoformat') else str(r['data_aldeia'])
                result['aldeias_fez'].append(r)

            cursor.execute("""
                SELECT aas.id, aas.id_aldeia, ad.nome_aldeia, aas.data_aldeia, aas.id_equipe, e.nome as nome_equipe, aas.id_nucleo, n.nome as nome_nucleo
                FROM db_aldeias.tb_aldeeiro_aldeia_serviu aas
                LEFT JOIN db_aldeias.tb_aldeia ad ON ad.id = aas.id_aldeia
                LEFT JOIN db_aldeias.tb_equipes e ON e.id = aas.id_equipe
                LEFT JOIN db_aldeias.tb_nucleo n ON n.id = aas.id_nucleo
                WHERE aas.cpf_aldeeiro = %s
            """, (cpf,))
            for r in cursor.fetchall():
                r['id_aldeia'] = int(r['id_aldeia']) if r['id_aldeia'] else r['id_aldeia']
                if r.get('data_aldeia'):
                    r['data_aldeia'] = r['data_aldeia'].isoformat() if hasattr(r['data_aldeia'], 'isoformat') else str(r['data_aldeia'])
                result['aldeias_serviu'].append(r)
    except Exception:
        pass
    finally:
        if connection:
            connection.close()
    return result


def buscar_aldeeiro_por_cpf_db(cpf):
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT nome FROM db_aldeias.tb_aldeeiro WHERE cpf = %s", (cpf,))
            return cursor.fetchone()
    except Exception:
        return None
    finally:
        if connection:
            connection.close()


def buscar_aldeeiro_status_por_cpf(cpf):
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT nome, ativo FROM db_aldeias.tb_aldeeiro WHERE cpf = %s", (cpf,))
            return cursor.fetchone()
    except Exception:
        return None
    finally:
        if connection:
            connection.close()


def ativar_desativar_aldeeiro_db(cpf, novo_status):
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("UPDATE db_aldeias.tb_aldeeiro SET ativo = %s WHERE cpf = %s", (novo_status, cpf))
            connection.commit()
    except Exception as e:
        raise e
    finally:
        if connection:
            connection.close()


# ==================== PERFIL ====================

def get_perfil_usuario(email):
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT p.descricao
                FROM db_aldeias.tb_aldeeiro_perfil ap
                JOIN db_aldeias.tb_aldeeiro a ON a.cpf = ap.cpf_aldeeiro
                JOIN db_aldeias.tb_perfil p ON p.id = ap.id_perfil
                WHERE a.email = %s
            """, (email,))
            rows = cursor.fetchall()
            return [r['descricao'] for r in rows]
    except Exception:
        return []
    finally:
        if connection:
            connection.close()


def get_perfis():
    cached = _cache_get('perfis')
    if cached is not None:
        return cached
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, descricao FROM db_aldeias.tb_perfil ORDER BY descricao")
            resultado = cursor.fetchall()
            _cache_set('perfis', resultado)
            return resultado
    except Exception:
        return []
    finally:
        if connection:
            connection.close()


def adicionar_remover_perfis(cpf, perfis_ids, acao):
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            for id_perfil in perfis_ids:
                if acao == "adicionar":
                    cursor.execute(
                        "INSERT IGNORE INTO db_aldeias.tb_aldeeiro_perfil (cpf_aldeeiro, id_perfil) VALUES (%s, %s)",
                        (cpf, id_perfil)
                    )
                elif acao == "remover":
                    cursor.execute(
                        "DELETE FROM db_aldeias.tb_aldeeiro_perfil WHERE cpf_aldeeiro = %s AND id_perfil = %s",
                        (cpf, id_perfil)
                    )
            connection.commit()
    except Exception as e:
        raise e
    finally:
        if connection:
            connection.close()


# ==================== FORMAÇÀO ====================

def get_formacoes():
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, tema, data_formacao, nucleo FROM db_aldeias.tb_formacao WHERE data_formacao = CURDATE() ORDER BY data_formacao DESC"
            )
            return cursor.fetchall()
    except Exception:
        return []
    finally:
        if connection:
            connection.close()


def get_formacoes_por_nucleo(nucleo_id):
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, tema, data_formacao, nucleo FROM db_aldeias.tb_formacao WHERE nucleo = %s AND data_formacao = CURDATE() ORDER BY data_formacao DESC",
                (nucleo_id,)
            )
            return cursor.fetchall()
    except Exception:
        return []
    finally:
        if connection:
            connection.close()


def consultar_formacoes_db(nucleo, data_inicio=None, data_fim=None):
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = """
                SELECT f.id, f.data_formacao, f.tema, n.nome AS nucleo,
                       COALESCE(a.nome, 'Não informado') AS formador
                FROM db_aldeias.tb_formacao f
                JOIN db_aldeias.tb_nucleo n ON n.id = f.nucleo
                LEFT JOIN db_aldeias.tb_aldeeiro a ON a.cpf = f.cpf_formador
                WHERE f.nucleo = %s
            """
            params = [nucleo]

            if data_inicio:
                sql += " AND f.data_formacao >= %s"
                params.append(data_inicio)
            if data_fim:
                sql += " AND f.data_formacao <= %s"
                params.append(data_fim)

            sql += " ORDER BY f.data_formacao DESC, f.tema"
            cursor.execute(sql, params)
            return cursor.fetchall()
    except Exception as e:
        raise e
    finally:
        if connection:
            connection.close()


def get_formacao_por_id(id_formacao):
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT f.tema, f.data_formacao FROM db_aldeias.tb_formacao f WHERE f.id = %s",
                (id_formacao,)
            )
            return cursor.fetchone()
    except Exception:
        return None
    finally:
        if connection:
            connection.close()


def get_presentes_por_formacao(id_formacao):
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT a.nome
                FROM db_aldeias.tb_frequencia_aldeeiro fa
                JOIN db_aldeias.tb_aldeeiro a ON a.cpf = fa.cpf_aldeeiro
                WHERE fa.id_formacao = %s
                ORDER BY a.nome
            """, (id_formacao,))
            return cursor.fetchall()
    except Exception:
        return []
    finally:
        if connection:
            connection.close()


# ==================== RELATÓRIO DE PRESENÇA ====================

def contar_formacoes_nucleo(nucleo, data_inicio=None, data_fim=None):
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = """
                SELECT COUNT(*) AS total
                FROM db_aldeias.tb_formacao
                WHERE nucleo = %s
            """
            params = [nucleo]
            if data_inicio:
                sql += " AND data_formacao >= %s"
                params.append(data_inicio)
            if data_fim:
                sql += " AND data_formacao <= %s"
                params.append(data_fim)
            cursor.execute(sql, params)
            return cursor.fetchone()['total']
    except Exception:
        return 0
    finally:
        if connection:
            connection.close()


def relatorio_presenca_db(nucleo, data_inicio=None, data_fim=None, zero_presenca=False, min_presenca=None):
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            join_extra = ""
            join_params = []
            if data_inicio:
                join_extra += " AND f.data_formacao >= %s"
                join_params.append(data_inicio)
            if data_fim:
                join_extra += " AND f.data_formacao <= %s"
                join_params.append(data_fim)

            sql = f"""
                SELECT a.nome, n.nome AS nucleo,
                       COUNT(DISTINCT fa.id) AS total_formacoes,
                       MAX(f.data_formacao) AS ultima_presenca
                FROM db_aldeias.tb_aldeeiro a
                JOIN db_aldeias.tb_nucleo n ON n.id = a.nucleo
                LEFT JOIN db_aldeias.tb_frequencia_aldeeiro fa ON fa.cpf_aldeeiro = a.cpf
                LEFT JOIN db_aldeias.tb_formacao f ON f.id = fa.id_formacao{join_extra}
                WHERE a.nucleo = %s AND a.ativo = 1
            """
            params = join_params + [nucleo]

            sql += " GROUP BY a.cpf, a.nome, n.nome"

            if zero_presenca:
                sql += " HAVING total_formacoes = 0"
            elif min_presenca:
                sql += " HAVING total_formacoes >= %s"
                params.append(int(min_presenca))

            sql += " ORDER BY total_formacoes DESC, a.nome"

            cursor.execute(sql, params)
            return cursor.fetchall()
    except Exception as e:
        raise e
    finally:
        if connection:
            connection.close()


# ==================== NÚCLEO ====================

def get_info_nucleo(nucleo_id):
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT endereco, dias_reuniao FROM db_aldeias.tb_nucleo WHERE id = %s", (nucleo_id,)
            )
            nucleo = cursor.fetchone() or {}

            cursor.execute("""
                SELECT a.nome, a.telefone
                FROM db_aldeias.tb_aldeeiro a
                JOIN db_aldeias.tb_aldeeiro_perfil ap ON ap.cpf_aldeeiro = a.cpf
                JOIN db_aldeias.tb_perfil p ON p.id = ap.id_perfil
                WHERE a.nucleo = %s AND p.descricao = 'Coordenador' AND a.ativo = 1
                ORDER BY a.nome
            """, (nucleo_id,))
            coordenadores = cursor.fetchall()

            return {
                "endereco": nucleo.get("endereco", ""),
                "dias_reuniao": nucleo.get("dias_reuniao", ""),
                "coordenadores": coordenadores
            }
    except Exception as e:
        raise e
    finally:
        if connection:
            connection.close()


def buscar_nucleo_por_id(nucleo_id):
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, nome, endereco, dias_reuniao, ativo_relatorio FROM db_aldeias.tb_nucleo WHERE id = %s",
                (nucleo_id,)
            )
            return cursor.fetchone()
    except Exception:
        return None
    finally:
        if connection:
            connection.close()


def cadastrar_atualizar_nucleo(acao, nome, endereco, dias_reuniao, ativo_relatorio, motivo, cpf_alterou, nucleo_id=None):
    connection = None
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            if acao == "cadastrar":
                sql = """
                    INSERT INTO db_aldeias.tb_nucleo
                        (nome, endereco, dias_reuniao, ativo_relatorio, motivo_alteracao, data_criacao, cpf_alterou)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (nome, endereco, dias_reuniao, ativo_relatorio, motivo, now, cpf_alterou))
            else:
                sql = """
                    UPDATE db_aldeias.tb_nucleo
                    SET nome = %s, endereco = %s, dias_reuniao = %s, ativo_relatorio = %s,
                        motivo_alteracao = %s, data_update = %s, cpf_alterou = %s
                    WHERE id = %s
                """
                cursor.execute(sql, (nome, endereco, dias_reuniao, ativo_relatorio, motivo, now, cpf_alterou, nucleo_id))
            connection.commit()
    except Exception as e:
        raise e
    finally:
        if connection:
            connection.close()


# ==================== AUTENTICAÇÀO ====================

def buscar_usuario_por_email(email):
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM db_aldeias.tb_usuario WHERE email = %s AND ativo = 1", (email,))
            return cursor.fetchone()
    except Exception:
        return None
    finally:
        if connection:
            connection.close()


def email_ja_cadastrado(email):
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM db_aldeias.tb_usuario WHERE email = %s", (email,))
            return cursor.fetchone() is not None
    except Exception:
        return False
    finally:
        if connection:
            connection.close()


def inserir_usuario(nome, email, senha_hash):
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO db_aldeias.tb_usuario (nome, email, senha_hash) VALUES (%s, %s, %s)",
                (nome, email, senha_hash)
            )
        connection.commit()
    except Exception as e:
        raise e
    finally:
        if connection:
            connection.close()


def buscar_usuario_id_por_email(email):
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM db_aldeias.tb_usuario WHERE email = %s AND ativo = 1", (email,))
            row = cursor.fetchone()
            return row['id'] if row else None
    except Exception:
        return None
    finally:
        if connection:
            connection.close()


def invalidar_codigos_recuperacao(usuario_id):
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE db_aldeias.tb_recuperacao_senha SET usado = 1 WHERE usuario_id = %s AND usado = 0",
                (usuario_id,)
            )
        connection.commit()
    except Exception:
        pass
    finally:
        if connection:
            connection.close()


def inserir_codigo_recuperacao(usuario_id, codigo):
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO db_aldeias.tb_recuperacao_senha (usuario_id, codigo) VALUES (%s, %s)",
                (usuario_id, codigo)
            )
        connection.commit()
    except Exception as e:
        raise e
    finally:
        if connection:
            connection.close()


def validar_codigo_recuperacao(usuario_id, codigo):
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT id FROM db_aldeias.tb_recuperacao_senha
                   WHERE usuario_id = %s AND codigo = %s AND usado = 0
                   AND criado_em >= NOW() - INTERVAL 10 MINUTE""",
                (usuario_id, codigo)
            )
            return cursor.fetchone()
    except Exception:
        return None
    finally:
        if connection:
            connection.close()


def marcar_codigo_usado(token_id):
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE db_aldeias.tb_recuperacao_senha SET usado = 1 WHERE id = %s",
                (token_id,)
            )
        connection.commit()
    except Exception:
        pass
    finally:
        if connection:
            connection.close()


def atualizar_senha_usuario(usuario_id, nova_senha_hash):
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE db_aldeias.tb_usuario SET senha_hash = %s WHERE id = %s",
                (nova_senha_hash, usuario_id)
            )
        connection.commit()
    except Exception as e:
        raise e
    finally:
        if connection:
            connection.close()


# ==================== CADASTRO ALDEEIRO ====================

def inserir_atualizar_aldeeiro(body):
    connection = None
    try:
        connection = get_db_connection()
        ja_serviu = body["serviu"][0]
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        with connection.cursor() as cursor:
            sql = """
                  INSERT INTO db_aldeias.tb_aldeeiro
                    (nome, cpf, data_nascimento, sexo, telefone, email, nucleo, ja_serviu, data_insert, ativo,
                     logradouro, numero, complemento, bairro, cidade, uf)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    nome = VALUES(nome),
                    telefone = VALUES(telefone),
                    email = VALUES(email),
                    nucleo = VALUES(nucleo),
                    ja_serviu = VALUES(ja_serviu),
                    logradouro = VALUES(logradouro),
                    numero = VALUES(numero),
                    complemento = VALUES(complemento),
                    bairro = VALUES(bairro),
                    cidade = VALUES(cidade),
                    uf = VALUES(uf),
                    data_update = %s
            """
            values = (
                body["nome"],
                body["cpf"],
                body["data_nascimento"],
                body["sexo"],
                body["telefone"],
                body["email"],
                body["nucleo"],
                1 if ja_serviu == 'true' else 0,
                now,
                1,
                body.get("logradouro", [None])[0] if isinstance(body.get("logradouro"), list) else body.get("logradouro"),
                body.get("numero", [None])[0] if isinstance(body.get("numero"), list) else body.get("numero"),
                body.get("complemento", [None])[0] if isinstance(body.get("complemento"), list) else body.get("complemento"),
                body.get("bairro", [None])[0] if isinstance(body.get("bairro"), list) else body.get("bairro"),
                body.get("cidade", [None])[0] if isinstance(body.get("cidade"), list) else body.get("cidade"),
                body.get("uf", [None])[0] if isinstance(body.get("uf"), list) else body.get("uf"),
                now
            )
            cursor.execute(sql, values)
        connection.commit()

        cpf = body["cpf"]
        import json as _json
        # aldeias_fez comes as JSON string
        aldeias_fez_json = body.get("aldeias_fez_json")
        if isinstance(aldeias_fez_json, list):
            aldeias_fez_json = aldeias_fez_json[0] if aldeias_fez_json else '[]'
        aldeias_fez_list = _json.loads(aldeias_fez_json) if aldeias_fez_json else []
        _replace_aldeias_fez(connection, cpf, aldeias_fez_list)

        if ja_serviu == 'true':
            aldeias_serviu_json = body.get("aldeias_serviu_json")
            if isinstance(aldeias_serviu_json, list):
                aldeias_serviu_json = aldeias_serviu_json[0] if aldeias_serviu_json else '[]'
            aldeias_serviu_list = _json.loads(aldeias_serviu_json) if aldeias_serviu_json else []
            _replace_aldeias_serviu(connection, cpf, aldeias_serviu_list)

    except Exception as e:
        raise e
    finally:
        if connection:
            connection.close()


def _replace_aldeias_fez(connection, cpf, aldeias_fez):
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM db_aldeias.tb_aldeeiro_aldeia_fez WHERE cpf_aldeeiro = %s", (cpf,))
        for item in aldeias_fez:
            cursor.execute(
                "INSERT INTO db_aldeias.tb_aldeeiro_aldeia_fez (cpf_aldeeiro, id_aldeia, data_aldeia, id_nucleo) VALUES (%s, %s, %s, %s)",
                (cpf, item['id_aldeia'], item.get('data_aldeia') or None, item.get('id_nucleo') or None)
            )
    connection.commit()


def _replace_aldeias_serviu(connection, cpf, aldeias_serviu):
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM db_aldeias.tb_aldeeiro_aldeia_serviu WHERE cpf_aldeeiro = %s", (cpf,))
        for item in aldeias_serviu:
            cursor.execute(
                "INSERT INTO db_aldeias.tb_aldeeiro_aldeia_serviu (cpf_aldeeiro, id_aldeia, data_aldeia, id_equipe, id_nucleo) VALUES (%s, %s, %s, %s, %s)",
                (cpf, item['id_aldeia'], item.get('data_aldeia') or None, item.get('id_equipe') or None, item.get('id_nucleo') or None)
            )
    connection.commit()


# ==================== DADOS GERAIS ====================

def select_equipes():
    cached = _cache_get('equipes')
    if cached is not None:
        return cached
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, nome FROM db_aldeias.tb_equipes")
            resultado = cursor.fetchall()
            _cache_set('equipes', resultado)
            return resultado
    except Exception as e:
        raise e
    finally:
        if connection:
            connection.close()


def select_aldeias():
    cached = _cache_get('aldeias')
    if cached is not None:
        return cached
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM db_aldeias.tb_aldeia")
            resultado = cursor.fetchall()
            _cache_set('aldeias', resultado)
            return resultado
    except Exception as e:
        raise e
    finally:
        if connection:
            connection.close()


def select_nucleos():
    cached = _cache_get('nucleos')
    if cached is not None:
        return cached
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, nome FROM db_aldeias.tb_nucleo")
            resultado = cursor.fetchall()
            _cache_set('nucleos', resultado)
            return resultado
    except Exception as e:
        raise e
    finally:
        if connection:
            connection.close()


def select_nucleos_ativos():
    cached = _cache_get('nucleos_ativos')
    if cached is not None:
        return cached
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, nome FROM db_aldeias.tb_nucleo WHERE ativo_relatorio = 1")
            resultado = cursor.fetchall()
            _cache_set('nucleos_ativos', resultado)
            return resultado
    except Exception as e:
        raise e
    finally:
        if connection:
            connection.close()


# ==================== CONSULTAR ALDEEIROS ====================

def select_aldeeiros_by(filtros):
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = """SELECT a.cpf as cpf, a.nome as nome_aldeeiro, n.nome as nucleo, a.telefone as telefone_aldeeiro,
                            ad.nome_aldeia as nome_aldeia_fez,
                            aaf.data_aldeia as data_aldeia_fez,
                            ad2.nome_aldeia as aldeia_serviu,
                            e.nome as nome_equipe,
                            a.logradouro, a.numero, a.complemento, a.bairro, a.cidade, a.uf 
                        FROM db_aldeias.tb_aldeeiro a
                        LEFT JOIN db_aldeias.tb_aldeeiro_aldeia_fez aaf ON aaf.cpf_aldeeiro = a.cpf
                        LEFT JOIN db_aldeias.tb_aldeeiro_aldeia_serviu aas ON aas.cpf_aldeeiro = a.cpf
                        INNER JOIN db_aldeias.tb_nucleo n ON n.id = a.nucleo
                        LEFT JOIN db_aldeias.tb_aldeia ad ON ad.id = aaf.id_aldeia
                        LEFT JOIN db_aldeias.tb_aldeia ad2 ON ad2.id = aas.id_aldeia
                        LEFT JOIN db_aldeias.tb_equipes e ON e.id = aas.id_equipe
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
        raise e
    finally:
        if connection:
            connection.close()


# ==================== FORMAÇÃO (INSERT) ====================

def insert_formacao_db(nucleo, tema, data_formacao, cpf_formador=None):
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = "INSERT INTO db_aldeias.tb_formacao (tema, data_formacao, nucleo, cpf_formador) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql, (tema, data_formacao, nucleo, cpf_formador))
        connection.commit()
    except Exception as e:
        raise e
    finally:
        if connection:
            connection.close()


# ==================== CONSULTAR ALDEIAS ====================

def consultar_aldeias_db(id_aldeia=None, data_inicio=None, data_fim=None, id_nucleo=None):
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = """
                SELECT DISTINCT aas.id_aldeia, ad.nome_aldeia, aas.data_aldeia, aas.id_nucleo, n.nome AS nome_nucleo
                FROM db_aldeias.tb_aldeeiro_aldeia_serviu aas
                JOIN db_aldeias.tb_aldeia ad ON ad.id = aas.id_aldeia
                LEFT JOIN db_aldeias.tb_nucleo n ON n.id = aas.id_nucleo
                WHERE 1=1
            """
            params = []
            if id_aldeia:
                sql += " AND aas.id_aldeia = %s"
                params.append(id_aldeia)
            if data_inicio:
                sql += " AND aas.data_aldeia >= %s"
                params.append(data_inicio)
            if data_fim:
                sql += " AND aas.data_aldeia <= %s"
                params.append(data_fim)
            if id_nucleo:
                sql += " AND aas.id_nucleo = %s"
                params.append(id_nucleo)

            sql += " ORDER BY aas.data_aldeia DESC, ad.nome_aldeia"
            cursor.execute(sql, params)
            return cursor.fetchall()
    except Exception as e:
        raise e
    finally:
        if connection:
            connection.close()


def get_serventes_aldeia(id_aldeia, data_aldeia, id_nucleo):
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            sql = """
                SELECT a.nome, e.nome AS equipe
                FROM db_aldeias.tb_aldeeiro_aldeia_serviu aas
                JOIN db_aldeias.tb_aldeeiro a ON a.cpf = aas.cpf_aldeeiro
                LEFT JOIN db_aldeias.tb_equipes e ON e.id = aas.id_equipe
                WHERE aas.id_aldeia = %s
            """
            params = [id_aldeia]
            if data_aldeia:
                sql += " AND aas.data_aldeia = %s"
                params.append(data_aldeia)
            if id_nucleo:
                sql += " AND aas.id_nucleo = %s"
                params.append(id_nucleo)
            sql += " ORDER BY a.nome"
            cursor.execute(sql, params)
            return cursor.fetchall()
    except Exception as e:
        raise e
    finally:
        if connection:
            connection.close()


# ==================== PRESENÇA ====================

def verificar_presenca_existente(cpf, id_formacao):
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM db_aldeias.tb_frequencia_aldeeiro WHERE cpf_aldeeiro = %s AND id_formacao = %s",
                (cpf, id_formacao)
            )
            return cursor.fetchone() is not None
    except Exception:
        return False
    finally:
        if connection:
            connection.close()


def inserir_presenca(cpf, id_formacao, data_registro):
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO db_aldeias.tb_frequencia_aldeeiro (cpf_aldeeiro, id_formacao, data_registro) VALUES (%s, %s, %s)",
                (cpf, id_formacao, data_registro)
            )
        connection.commit()
    except Exception as e:
        raise e
    finally:
        if connection:
            connection.close()


# ==================== WHATSAPP ====================

def obter_numeros_telefone():
    connection = None
    try:
        connection = get_db_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT DISTINCT telefone FROM db_aldeias.tb_aldeeiro WHERE telefone IS NOT NULL AND ativo = 1")
            rows = cursor.fetchall()
            return [row['telefone'] for row in rows]
    except Exception as e:
        raise e
    finally:
        if connection:
            connection.close()

