import json
import os
import pymysql
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, render_template, request, session, redirect, url_for, flash
from lambda_get_dados import lambda_handler
from lambda_cadastro import lambda_handler as lambda_handler_cadastro
from lambda_get_aldeeiros import lambda_handler as lambda_handler_aldeeiros
from lambda_gerar_formacao import lambda_handler as lambda_handler_formacao
from lambda_registrar_presenca import lambda_handler as lambda_handler_presenca
from lambda_envia_alerta_wpp_meta import lambda_handler as lambda_handler_whatsapp
from lambda_auth import login as auth_login, cadastrar_usuario, solicitar_recuperacao, confirmar_recuperacao
from lambda_download_s3 import lambda_handler as lambda_handler_download, listar_arquivos

template_path = "C:/Users/joao-/Documents/GitHub/projeto_aldeias/templates"
application = Flask(__name__, template_folder=template_path)
application.secret_key = os.environ.get('SECRET_KEY', 'aldeias-secret-key-2026')
application.permanent_session_lifetime = timedelta(minutes=5)

NUCLEOS_CACHE = None


@application.before_request
def check_session_timeout():
    rotas_publicas = ['login_page', 'cadastro_page', 'recuperar_senha_page', 'confirmar_codigo_page', 'static']
    if request.endpoint in rotas_publicas:
        return

    if session.get('usuario_id'):
        last_activity = session.get('last_activity')
        now = datetime.utcnow()
        if last_activity:
            elapsed = (now - datetime.fromisoformat(last_activity)).total_seconds()
            if elapsed > 300:
                session.clear()
                flash('Sessão expirada por inatividade. Faça login novamente.', 'error')
                return redirect(url_for('login_page'))
        session['last_activity'] = now.isoformat()


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('usuario_id'):
            flash('Faça login para acessar o sistema.', 'error')
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function


def perfil_required(*perfis_permitidos):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            perfil = session.get('perfil', [])
            if not any(p in perfil for p in perfis_permitidos):
                flash('Você não tem permissão para acessar esta página.', 'error')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


@application.route("/")
def root():
    if session.get('usuario_id'):
        return redirect(url_for('index'))
    return redirect(url_for('login_page'))


# ==================== AUTH ====================

@application.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "POST":
        body = {
            "email": request.form.get("email"),
            "senha": request.form.get("senha")
        }
        result = auth_login(body)
        if result["statusCode"] == 200:
            usuario = result["usuario"]
            session.permanent = True
            session['usuario_id'] = usuario['id']
            session['usuario_nome'] = usuario['nome']
            session['usuario_email'] = usuario['email']
            session['perfil'] = get_perfil_usuario(usuario['email'])
            session['last_activity'] = datetime.utcnow().isoformat()
            return redirect(url_for('index'))
        else:
            flash(json.loads(result["body"]).get("error", "Erro no login."), 'error')
    return render_template("login.html")


@application.route("/cadastro", methods=["GET", "POST"])
def cadastro_page():
    if request.method == "POST":
        senha = request.form.get("senha")
        confirmar = request.form.get("confirmar_senha")
        if senha != confirmar:
            flash("As senhas não coincidem.", "error")
            return render_template("cadastro_usuario.html")

        body = {
            "nome": request.form.get("nome"),
            "email": request.form.get("email"),
            "senha": senha
        }
        result = cadastrar_usuario(body)
        if result["statusCode"] == 200:
            flash("Conta criada com sucesso! Faça login.", "success")
            return redirect(url_for('login_page'))
        else:
            flash(json.loads(result["body"]).get("error", "Erro ao cadastrar."), "error")
    return render_template("cadastro_usuario.html")


@application.route("/recuperar-senha", methods=["GET", "POST"])
def recuperar_senha_page():
    if request.method == "POST":
        body = {"email": request.form.get("email")}
        result = solicitar_recuperacao(body)
        if result["statusCode"] == 200:
            flash("Código enviado para o seu email. Válido por 10 minutos.", "success")
            return redirect(url_for('confirmar_codigo_page', email=body['email']))
        else:
            flash(json.loads(result["body"]).get("error", "Erro ao solicitar recuperação."), "error")
    return render_template("recuperar_senha.html")


@application.route("/confirmar-codigo", methods=["GET", "POST"])
def confirmar_codigo_page():
    email = request.args.get("email") or request.form.get("email", "")

    if request.method == "POST":
        nova_senha = request.form.get("nova_senha")
        confirmar = request.form.get("confirmar_senha")
        if nova_senha != confirmar:
            flash("As senhas não coincidem.", "error")
            return render_template("confirmar_codigo.html", email=email)

        body = {
            "email": email,
            "codigo": request.form.get("codigo"),
            "nova_senha": nova_senha
        }
        result = confirmar_recuperacao(body)
        if result["statusCode"] == 200:
            flash("Senha alterada com sucesso! Faça login.", "success")
            return redirect(url_for('login_page'))
        else:
            flash(json.loads(result["body"]).get("error", "Erro ao confirmar código."), "error")

    return render_template("confirmar_codigo.html", email=email)


@application.route("/logout")
def logout():
    session.clear()
    flash("Você saiu do sistema.", "success")
    return redirect(url_for('login_page'))

# ==================== PAGES ====================

@application.route("/init-aldeias", methods=["GET", "POST"])
@login_required
def index():
    perfil = session.get('perfil', [])
    return render_template("index.html", perfil=perfil)


@application.route("/aldeeiro/form", methods=["GET", "POST"])
@login_required
def form_aldeeiro():
    response = lambda_handler({}, None)
    data = json.loads(response["body"])
    aldeeiro = get_aldeeiro_por_email(session.get('usuario_email'))

    aldeeiro_equipes_ids = []
    aldeeiro_aldeias_fez_ids = []
    aldeeiro_aldeias_serviu_ids = []

    if aldeeiro:
        rel = get_aldeeiro_relacoes(aldeeiro['cpf'])
        aldeeiro_equipes_ids = rel['equipes']
        aldeeiro_aldeias_fez_ids = rel['aldeias_fez']
        aldeeiro_aldeias_serviu_ids = rel['aldeias_serviu']

    return render_template(
        "criar_atualizar_aldeeiro.html",
        equipes=data.get("equipes"),
        aldeias_serviu=data.get("aldeias_serviu"),
        aldeias_fez=data.get("aldeias_fez"),
        nucleos=data.get("nucleos"),
        aldeeiro=aldeeiro,
        aldeeiro_equipes_ids=aldeeiro_equipes_ids,
        aldeeiro_aldeias_fez_ids=aldeeiro_aldeias_fez_ids,
        aldeeiro_aldeias_serviu_ids=aldeeiro_aldeias_serviu_ids
    )


@application.route("/salvar_atualizar_aldeeiro", methods=["POST"])
@login_required
def salvar_atualizar_aldeeiro():
    form_data = request.form.to_dict(flat=False)
    form_data['email'] = [session.get('usuario_email')]
    result = lambda_handler_cadastro({"body": form_data}, None)

    status_code = result.get("statusCode")
    if status_code == 200:
        session['perfil'] = get_perfil_usuario(session.get('usuario_email'))
        status = "success"
        message = "Cadastro realizado com sucesso!"
    else:
        status = "error"
        message = f"Erro ao realizar cadastro: {result.get('body')}"

    return render_template(
        "result-cadastro.html",
        status=status,
        message=message,
        status_code=status_code
    )


@application.route("/aldeeiro/listar", methods=["GET", "POST"])
@login_required
@perfil_required('Coordenador')
def listar_aldeeiros():
    nucleos = get_nucleos()
    response = lambda_handler({}, None)
    dados = json.loads(response["body"])
    return render_template(
        "listar-aldeeiros.html",
        nucleos=nucleos,
        aldeias=dados.get("aldeias_fez", []),
        equipes_lista=dados.get("equipes", [])
    )


@application.route("/pesquisarAldeeiros", methods=["GET", "POST"])
@login_required
@perfil_required('Coordenador')
def pesquisar_aldeeeiros():
    nome = request.args.get("nome") or request.form.get("nome")
    nucleo = request.args.get("nucleo") or request.form.get("nucleo")
    filtros = {"body": {
        "nome": nome,
        "nucleo": nucleo
    }}

    result = lambda_handler_aldeeiros(filtros, None)
    aldeeiros = json.loads(result["body"])

    # Filtrar por aldeias_fez, aldeias_serviu, equipes no lado do app
    sel_aldeias_fez = request.form.getlist("aldeias_fez")
    sel_aldeias_serviu = request.form.getlist("aldeias_serviu")
    sel_equipes = request.form.getlist("equipes")

    if sel_aldeias_fez or sel_aldeias_serviu or sel_equipes:
        filtered = []
        for a in aldeeiros:
            rel = get_aldeeiro_relacoes(a.get('cpf', ''))
            rel_fez = [str(x) for x in rel['aldeias_fez']]
            rel_serviu = [str(x) for x in rel['aldeias_serviu']]
            rel_equipes = [str(x) for x in rel['equipes']]

            if sel_aldeias_fez and not any(af in rel_fez for af in sel_aldeias_fez):
                continue
            if sel_aldeias_serviu and not any(asv in rel_serviu for asv in sel_aldeias_serviu):
                continue
            if sel_equipes and not any(eq in rel_equipes for eq in sel_equipes):
                continue
            filtered.append(a)
        aldeeiros = filtered

    response = lambda_handler({}, None)
    dados = json.loads(response["body"])

    return render_template(
        "listar-aldeeiros.html",
        aldeeiros=aldeeiros,
        nucleos=get_nucleos(),
        aldeias=dados.get("aldeias_fez", []),
        equipes_lista=dados.get("equipes", []),
        sel_aldeias_fez=sel_aldeias_fez,
        sel_aldeias_serviu=sel_aldeias_serviu,
        sel_equipes=sel_equipes,
        filtro_nome=nome or '',
        filtro_nucleo=nucleo or ''
    )


# ==================== FORMAÇÃO ====================

@application.route("/formacao/abrir", methods=["GET", "POST"])
@login_required
@perfil_required('Formador')
def abrir_formacao():
    if request.method == "POST":
        aldeeiro = get_aldeeiro_por_email(session.get('usuario_email'))
        body = {
            "nucleo": request.form.get("nucleo"),
            "tema": request.form.get("tema"),
            "cpf_formador": aldeeiro['cpf'] if aldeeiro else None
        }
        result = lambda_handler_formacao({"body": body}, None)
        if result["statusCode"] == 200:
            flash("Formação aberta com sucesso!", "success")
        else:
            flash(json.loads(result.get('body')).get('error', 'Erro ao abrir formação.'), "error")
        return redirect(url_for('abrir_formacao'))

    nucleos = get_nucleos()
    return render_template("abrir_formacao.html", nucleos=nucleos)


@application.route("/formacao/presenca", methods=["GET", "POST"])
@login_required
def registrar_presenca():
    aldeeiro = get_aldeeiro_por_email(session.get('usuario_email'))

    if request.method == "POST":
        cpf = aldeeiro['cpf'] if aldeeiro else request.form.get("cpf")
        body = {
            "cpf": cpf,
            "id_formacao": request.form.get("id_formacao"),
            "nucleo": request.form.get("nucleo")
        }
        result = lambda_handler_presenca({"body": body}, None)
        if result["statusCode"] == 200:
            flash("Presença registrada com sucesso!", "success")
        else:
            flash(json.loads(result.get('body')).get('error', 'Erro ao registrar presença.'), "error")
        return redirect(url_for('registrar_presenca'))

    nucleos = get_nucleos()
    nucleo_aldeeiro = aldeeiro['nucleo'] if aldeeiro else None
    formacoes = get_formacoes_por_nucleo(nucleo_aldeeiro) if nucleo_aldeeiro else get_formacoes()
    return render_template(
        "registrar_presenca.html",
        nucleos=nucleos,
        formacoes=formacoes,
        aldeeiro=aldeeiro,
        nucleo_aldeeiro=nucleo_aldeeiro
    )


@application.route("/api/formacoes", methods=["GET"])
@login_required
def api_formacoes_por_nucleo():
    nucleo = request.args.get("nucleo")
    if not nucleo:
        return json.dumps([]), 200, {"Content-Type": "application/json"}
    formacoes = get_formacoes_por_nucleo(nucleo)
    resultado = []
    for f in formacoes:
        resultado.append({
            "id": f['id'],
            "tema": f['tema'],
            "data_formacao": str(f['data_formacao']) if f['data_formacao'] else ''
        })
    return json.dumps(resultado, ensure_ascii=False), 200, {"Content-Type": "application/json"}


# ==================== ARQUIVOS E INFORMATIVOS ====================

@application.route("/arquivos", methods=["GET"])
@login_required
def arquivos_informativos():
    equipes_config = [
        {"nome": "Banda", "pasta": "banda"},
        {"nome": "Cozinha", "pasta": "cozinha"},
        {"nome": "Liderança / Mediadores", "pasta": "lideranca-mediadores"},
    ]

    equipes = []
    ''' for eq in equipes_config:
        arquivos = listar_arquivos(eq["pasta"])
        for arq in arquivos:
            tamanho = arq.get("tamanho", 0)
            if tamanho >= 1048576:
                arq["tamanho_formatado"] = f"{tamanho / 1048576:.1f} MB"
            elif tamanho >= 1024:
                arq["tamanho_formatado"] = f"{tamanho / 1024:.1f} KB"
            else:
                arq["tamanho_formatado"] = f"{tamanho} B"
        equipes.append({"nome": eq["nome"], "arquivos": arquivos})
    '''
    return render_template("arquivos_informativos.html", equipes=equipes)


@application.route("/arquivos/download", methods=["GET"])
@login_required
def download_arquivo():
    s3_key = request.args.get("s3_key")
    if not s3_key:
        flash("Arquivo não informado.", "error")
        return redirect(url_for('arquivos_informativos'))

    result = lambda_handler_download({"body": {"s3_key": s3_key}}, None)
    if result["statusCode"] == 200:
        data = json.loads(result["body"])
        return redirect(data["url"])
    else:
        erro = json.loads(result["body"]).get("error", "Erro ao baixar arquivo.")
        flash(erro, "error")
        return redirect(url_for('arquivos_informativos'))


# ==================== WHATSAPP ====================

@application.route("/whatsapp/enviar", methods=["GET", "POST"])
@login_required
@perfil_required('Coordenador')
def enviar_whatsapp():
    if request.method == "POST":
        tipo_envio = request.form.get("tipo_envio")
        if tipo_envio == "template":
            parametros_str = request.form.get("parametros", "")
            parametros = [p.strip() for p in parametros_str.split(",") if p.strip()]
            body = {
                "template_name": request.form.get("template_name"),
                "parametros": parametros
            }
        else:
            body = {
                "mensagem": request.form.get("mensagem")
            }

        result = lambda_handler_whatsapp({"body": body}, None)
        if result["statusCode"] == 200:
            data = json.loads(result["body"])
            flash(f"Mensagens enviadas! Total: {data.get('total')}, Sucesso: {data.get('enviadas')}, Falhas: {data.get('falhas')}", "success")
        else:
            flash(f"Erro ao enviar mensagens: {result.get('body')}", "error")
        return redirect(url_for('enviar_whatsapp'))

    return render_template("enviar_whatsapp.html")


# ==================== INFORMAÇÕES GERAIS ====================

@application.route("/informacoes", methods=["GET"])
@login_required
def informacoes_gerais():
    nucleos = get_nucleos()
    return render_template("informacoes_gerais.html", nucleos=nucleos)


@application.route("/api/info-nucleo", methods=["GET"])
@login_required
def api_info_nucleo():
    nucleo_id = request.args.get("id", "")
    connection = None
    try:
        connection = pymysql.connect(
            host=os.environ['DB_HOST'],
            user=os.environ['DB_USER'],
            password=os.environ['DB_PASSWORD'],
            database=os.environ['DB_NAME'],
            cursorclass=pymysql.cursors.DictCursor
        )
        with connection.cursor() as cursor:
            # Dados do núcleo
            cursor.execute(
                "SELECT endereco, dias_reuniao FROM db_aldeias.tb_nucleo WHERE id = %s", (nucleo_id,)
            )
            nucleo = cursor.fetchone() or {}

            # Coordenadores do núcleo
            cursor.execute("""
                SELECT a.nome, a.telefone
                FROM db_aldeias.tb_aldeeiro a
                JOIN db_aldeias.tb_aldeeiro_perfil ap ON ap.cpf_aldeeiro = a.cpf
                JOIN db_aldeias.tb_perfil p ON p.id = ap.id_perfil
                WHERE a.nucleo = %s AND p.descricao = 'Coordenador' AND a.ativo = 1
                ORDER BY a.nome
            """, (nucleo_id,))
            coordenadores = cursor.fetchall()

        resultado = {
            "endereco": nucleo.get("endereco", ""),
            "dias_reuniao": nucleo.get("dias_reuniao", ""),
            "coordenadores": coordenadores
        }
        return json.dumps(resultado, ensure_ascii=False), 200, {"Content-Type": "application/json"}
    except Exception as e:
        return json.dumps({"error": str(e)}), 500, {"Content-Type": "application/json"}
    finally:
        if connection:
            connection.close()


# ==================== CONSULTAR FORMAÇÕES ====================

@application.route("/formacao/consultar", methods=["GET", "POST"])
@login_required
@perfil_required('Coordenador')
def consultar_formacoes():
    nucleos = get_nucleos()
    resultados = None

    if request.method == "POST":
        nucleo = request.form.get("nucleo")
        data_inicio = request.form.get("data_inicio") or None
        data_fim = request.form.get("data_fim") or None

        connection = None
        try:
            connection = pymysql.connect(
                host=os.environ['DB_HOST'],
                user=os.environ['DB_USER'],
                password=os.environ['DB_PASSWORD'],
                database=os.environ['DB_NAME'],
                cursorclass=pymysql.cursors.DictCursor
            )
            with connection.cursor() as cursor:
                sql = """
                    SELECT f.data_formacao, f.tema, n.nome AS nucleo,
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
                resultados = cursor.fetchall()
        except Exception as e:
            flash(f"Erro ao consultar formações: {str(e)}", "error")
            resultados = []
        finally:
            if connection:
                connection.close()

    filtros = {}
    if request.method == "POST":
        filtros = {
            'nucleo': request.form.get('nucleo', ''),
            'data_inicio': request.form.get('data_inicio', ''),
            'data_fim': request.form.get('data_fim', '')
        }

    return render_template(
        "consultar_formacoes.html",
        nucleos=nucleos,
        resultados=resultados,
        filtros=filtros
    )


# ==================== RELATÓRIOS ====================

@application.route("/relatorio/presenca", methods=["GET", "POST"])
@login_required
@perfil_required('Coordenador')
def relatorio_presenca():
    nucleos = get_nucleos()
    resultados = None
    total_formacoes_nucleo = 0

    if request.method == "POST":
        nucleo = request.form.get("nucleo")
        data_inicio = request.form.get("data_inicio") or None
        data_fim = request.form.get("data_fim") or None

        connection = None
        try:
            connection = pymysql.connect(
                host=os.environ['DB_HOST'],
                user=os.environ['DB_USER'],
                password=os.environ['DB_PASSWORD'],
                database=os.environ['DB_NAME'],
                cursorclass=pymysql.cursors.DictCursor
            )
            with connection.cursor() as cursor:
                # Contar formações do núcleo no período
                sql_count = """
                    SELECT COUNT(*) AS total
                    FROM db_aldeias.tb_formacao
                    WHERE nucleo = %s
                """
                params_count = [nucleo]
                if data_inicio:
                    sql_count += " AND data_formacao >= %s"
                    params_count.append(data_inicio)
                if data_fim:
                    sql_count += " AND data_formacao <= %s"
                    params_count.append(data_fim)
                cursor.execute(sql_count, params_count)
                total_formacoes_nucleo = cursor.fetchone()['total']

                sql = """
                    SELECT a.nome, n.nome AS nucleo,
                           COUNT(DISTINCT fa.id) AS total_formacoes,
                           MAX(f.data_formacao) AS ultima_presenca
                    FROM db_aldeias.tb_aldeeiro a
                    JOIN db_aldeias.tb_nucleo n ON n.id = a.nucleo
                    LEFT JOIN db_aldeias.tb_frequencia_aldeeiro fa ON fa.cpf_aldeeiro = a.cpf
                    LEFT JOIN db_aldeias.tb_formacao f ON f.id = fa.id_formacao
                    WHERE a.nucleo = %s and a.ativo = 1 
                """
                params = [nucleo]

                if data_inicio:
                    sql += " AND f.data_formacao >= %s"
                    params.append(data_inicio)
                if data_fim:
                    sql += " AND f.data_formacao <= %s"
                    params.append(data_fim)

                sql += " GROUP BY a.cpf, a.nome, n.nome ORDER BY total_formacoes DESC, a.nome"

                cursor.execute(sql, params)
                resultados = cursor.fetchall()
        except Exception as e:
            flash(f"Erro ao consultar relatório: {str(e)}", "error")
            resultados = []
        finally:
            if connection:
                connection.close()

    filtros = {}
    if request.method == "POST":
        filtros = {
            'nucleo': request.form.get('nucleo', ''),
            'data_inicio': request.form.get('data_inicio', ''),
            'data_fim': request.form.get('data_fim', '')
        }

    return render_template(
        "relatorio_presenca.html",
        nucleos=nucleos,
        resultados=resultados,
        filtros=filtros,
        total_formacoes_nucleo=total_formacoes_nucleo
    )


# ==================== ADMIN ====================

@application.route("/admin/perfis", methods=["GET", "POST"])
@login_required
@perfil_required('Administrador')
def gerenciar_perfis():
    if request.method == "POST":
        cpf = request.form.get("cpf_aldeeiro")
        perfis_ids = request.form.getlist("id_perfil")
        acao = request.form.get("acao")

        connection = None
        try:
            connection = pymysql.connect(
                host=os.environ['DB_HOST'],
                user=os.environ['DB_USER'],
                password=os.environ['DB_PASSWORD'],
                database=os.environ['DB_NAME'],
                cursorclass=pymysql.cursors.DictCursor
            )
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
                flash(f"Perfil(is) {'adicionado(s)' if acao == 'adicionar' else 'removido(s)'} com sucesso!", "success")
        except Exception as e:
            flash(f"Erro: {str(e)}", "error")
        finally:
            if connection:
                connection.close()
        return redirect(url_for('gerenciar_perfis'))

    connection = None
    perfis = []
    try:
        connection = pymysql.connect(
            host=os.environ['DB_HOST'],
            user=os.environ['DB_USER'],
            password=os.environ['DB_PASSWORD'],
            database=os.environ['DB_NAME'],
            cursorclass=pymysql.cursors.DictCursor
        )
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, descricao FROM db_aldeias.tb_perfil ORDER BY descricao")
            perfis = cursor.fetchall()
    except Exception:
        pass
    finally:
        if connection:
            connection.close()

    return render_template("gerenciar_perfis.html", perfis=perfis, nucleos=get_nucleos())


@application.route("/admin/buscar-aldeeiro", methods=["GET"])
@login_required
@perfil_required('Administrador')
def buscar_aldeeiro_por_cpf():
    cpf = request.args.get("cpf", "")
    connection = None
    try:
        connection = pymysql.connect(
            host=os.environ['DB_HOST'],
            user=os.environ['DB_USER'],
            password=os.environ['DB_PASSWORD'],
            database=os.environ['DB_NAME'],
            cursorclass=pymysql.cursors.DictCursor
        )
        with connection.cursor() as cursor:
            cursor.execute("SELECT nome FROM db_aldeias.tb_aldeeiro WHERE cpf = %s", (cpf,))
            row = cursor.fetchone()
            if row:
                return json.dumps({"nome": row['nome']}), 200, {"Content-Type": "application/json"}
            else:
                return json.dumps({"nome": ""}), 404, {"Content-Type": "application/json"}
    except Exception:
        return json.dumps({"nome": ""}), 500, {"Content-Type": "application/json"}
    finally:
        if connection:
            connection.close()


@application.route("/admin/buscar-aldeeiro-status", methods=["GET"])
@login_required
@perfil_required('Administrador')
def buscar_aldeeiro_status():
    cpf = request.args.get("cpf", "")
    connection = None
    try:
        connection = pymysql.connect(
            host=os.environ['DB_HOST'],
            user=os.environ['DB_USER'],
            password=os.environ['DB_PASSWORD'],
            database=os.environ['DB_NAME'],
            cursorclass=pymysql.cursors.DictCursor
        )
        with connection.cursor() as cursor:
            cursor.execute("SELECT nome, ativo FROM db_aldeias.tb_aldeeiro WHERE cpf = %s", (cpf,))
            row = cursor.fetchone()
            if row:
                return json.dumps({"nome": row['nome'], "ativo": bool(row['ativo'])}), 200, {"Content-Type": "application/json"}
            else:
                return json.dumps({"nome": ""}), 404, {"Content-Type": "application/json"}
    except Exception:
        return json.dumps({"nome": ""}), 500, {"Content-Type": "application/json"}
    finally:
        if connection:
            connection.close()


@application.route("/admin/buscar-nucleo", methods=["GET"])
@login_required
@perfil_required('Administrador')
def buscar_nucleo():
    nucleo_id = request.args.get("id", "")
    connection = None
    try:
        connection = pymysql.connect(
            host=os.environ['DB_HOST'],
            user=os.environ['DB_USER'],
            password=os.environ['DB_PASSWORD'],
            database=os.environ['DB_NAME'],
            cursorclass=pymysql.cursors.DictCursor
        )
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id, nome, endereco, dias_reuniao, ativo FROM db_aldeias.tb_nucleo WHERE id = %s",
                (nucleo_id,)
            )
            row = cursor.fetchone()
            if row:
                return json.dumps(row, ensure_ascii=False), 200, {"Content-Type": "application/json"}
            else:
                return json.dumps({}), 404, {"Content-Type": "application/json"}
    except Exception:
        return json.dumps({}), 500, {"Content-Type": "application/json"}
    finally:
        if connection:
            connection.close()


@application.route("/admin/ativar-desativar", methods=["POST"])
@login_required
@perfil_required('Administrador')
def ativar_desativar_aldeeiro():
    cpf = request.form.get("cpf_aldeeiro")
    acao = request.form.get("acao")
    novo_status = 1 if acao == "ativar" else 0

    connection = None
    try:
        connection = pymysql.connect(
            host=os.environ['DB_HOST'],
            user=os.environ['DB_USER'],
            password=os.environ['DB_PASSWORD'],
            database=os.environ['DB_NAME'],
            cursorclass=pymysql.cursors.DictCursor
        )
        with connection.cursor() as cursor:
            cursor.execute("UPDATE db_aldeias.tb_aldeeiro SET ativo = %s WHERE cpf = %s", (novo_status, cpf))
            connection.commit()
            flash(f"Aldeeiro {'ativado' if novo_status == 1 else 'desativado'} com sucesso!", "success")
    except Exception as e:
        flash(f"Erro ao alterar status: {str(e)}", "error")
    finally:
        if connection:
            connection.close()

    return redirect(url_for('gerenciar_perfis'))


@application.route("/admin/cadastrar-nucleo", methods=["POST"])
@login_required
@perfil_required('Administrador')
def cadastrar_nucleo():
    acao_nucleo = request.form.get("acao_nucleo")
    nome = request.form.get("nome_nucleo", "").strip()
    endereco = request.form.get("endereco_nucleo", "").strip() or None
    dias_reuniao = request.form.get("dias_reuniao", "").strip() or None
    ativo = 1 if request.form.get("ativo_nucleo") == "1" else 0
    motivo = request.form.get("motivo_alteracao", "").strip() or None

    if not nome:
        flash("Nome do núcleo é obrigatório.", "error")
        return redirect(url_for('gerenciar_perfis'))

    aldeeiro = get_aldeeiro_por_email(session.get('usuario_email'))
    cpf_alterou = aldeeiro['cpf'] if aldeeiro else None
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    global NUCLEOS_CACHE
    connection = None
    try:
        connection = pymysql.connect(
            host=os.environ['DB_HOST'],
            user=os.environ['DB_USER'],
            password=os.environ['DB_PASSWORD'],
            database=os.environ['DB_NAME'],
            cursorclass=pymysql.cursors.DictCursor
        )
        with connection.cursor() as cursor:
            if acao_nucleo == "cadastrar":
                sql = """
                    INSERT INTO db_aldeias.tb_nucleo
                        (nome, endereco, dias_reuniao, ativo, motivo_alteracao, data_criacao, cpf_alterou)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (nome, endereco, dias_reuniao, ativo, motivo, now, cpf_alterou))
                flash(f"Núcleo '{nome}' cadastrado com sucesso!", "success")
            else:
                nucleo_id = request.form.get("nucleo_id")
                sql = """
                    UPDATE db_aldeias.tb_nucleo
                    SET nome = %s, endereco = %s, dias_reuniao = %s, ativo = %s,
                        motivo_alteracao = %s, data_update = %s, cpf_alterou = %s
                    WHERE id = %s
                """
                cursor.execute(sql, (nome, endereco, dias_reuniao, ativo, motivo, now, cpf_alterou, nucleo_id))
                flash(f"Núcleo '{nome}' atualizado com sucesso!", "success")
            connection.commit()
            NUCLEOS_CACHE = None
    except pymysql.err.IntegrityError:
        flash(f"Já existe um núcleo com o nome '{nome}'.", "error")
    except Exception as e:
        flash(f"Erro ao salvar núcleo: {str(e)}", "error")
    finally:
        if connection:
            connection.close()

    return redirect(url_for('gerenciar_perfis'))


# ==================== HELPERS ====================

def get_nucleos():
    global NUCLEOS_CACHE
    if NUCLEOS_CACHE is None:
        response = lambda_handler({}, None)
        data = json.loads(response["body"])
        NUCLEOS_CACHE = data.get("nucleos", [])
    return NUCLEOS_CACHE


def get_formacoes():
    connection = None
    try:
        connection = pymysql.connect(
            host=os.environ['DB_HOST'],
            user=os.environ['DB_USER'],
            password=os.environ['DB_PASSWORD'],
            database=os.environ['DB_NAME'],
            cursorclass=pymysql.cursors.DictCursor
        )
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, tema, data_formacao, nucleo FROM db_aldeias.tb_formacao WHERE data_formacao = CURDATE() ORDER BY data_formacao DESC")
            return cursor.fetchall()
    except Exception:
        return []
    finally:
        if connection:
            connection.close()


def get_formacoes_por_nucleo(nucleo_id):
    connection = None
    try:
        connection = pymysql.connect(
            host=os.environ['DB_HOST'],
            user=os.environ['DB_USER'],
            password=os.environ['DB_PASSWORD'],
            database=os.environ['DB_NAME'],
            cursorclass=pymysql.cursors.DictCursor
        )
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


def get_perfil_usuario(email):
    connection = None
    try:
        connection = pymysql.connect(
            host=os.environ['DB_HOST'],
            user=os.environ['DB_USER'],
            password=os.environ['DB_PASSWORD'],
            database=os.environ['DB_NAME'],
            cursorclass=pymysql.cursors.DictCursor
        )
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


def get_aldeeiro_por_email(email):
    connection = None
    try:
        connection = pymysql.connect(
            host=os.environ['DB_HOST'],
            user=os.environ['DB_USER'],
            password=os.environ['DB_PASSWORD'],
            database=os.environ['DB_NAME'],
            cursorclass=pymysql.cursors.DictCursor
        )
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
    result = {'equipes': [], 'aldeias_fez': [], 'aldeias_serviu': []}
    try:
        connection = pymysql.connect(
            host=os.environ['DB_HOST'],
            user=os.environ['DB_USER'],
            password=os.environ['DB_PASSWORD'],
            database=os.environ['DB_NAME'],
            cursorclass=pymysql.cursors.DictCursor
        )
        with connection.cursor() as cursor:
            cursor.execute("SELECT id_equipe FROM db_aldeias.tb_aldeeiro_equipe WHERE cpf_aldeeiro = %s", (cpf,))
            result['equipes'] = [r['id_equipe'] for r in cursor.fetchall()]

            cursor.execute("SELECT id_aldeia FROM db_aldeias.tb_aldeeiro_aldeia_fez WHERE cpf_aldeeiro = %s", (cpf,))
            result['aldeias_fez'] = [r['id_aldeia'] for r in cursor.fetchall()]

            cursor.execute("SELECT id_aldeia FROM db_aldeias.tb_aldeeiro_aldeia_serviu WHERE cpf_aldeeiro = %s", (cpf,))
            result['aldeias_serviu'] = [r['id_aldeia'] for r in cursor.fetchall()]
    except Exception:
        pass
    finally:
        if connection:
            connection.close()
    return result


application.run(debug=True)
