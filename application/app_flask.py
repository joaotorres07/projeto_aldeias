import json
import os
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, render_template, request, session, redirect, url_for, flash
from dados_function import get_dados_aldeias, decimal_serializer
from cadastro_function import salvar_aldeeiro
from aldeeiros_function import pesquisar_aldeeiros
from formacao_function import abrir_formacao as abrir_formacao_fn
from presenca_function import registrar_presenca as registrar_presenca_fn
from whatsapp_function import enviar_whatsapp as enviar_whatsapp_fn
from auth_functions import login as auth_login, cadastrar_usuario_fn as cadastrar_usuario, solicitar_recuperacao, confirmar_recuperacao
from download_s3_function import gerar_url_download, listar_arquivos

from database_function import (
    get_aldeeiro_por_email, get_aldeeiro_relacoes, buscar_aldeeiro_por_cpf_db,
    buscar_aldeeiro_status_por_cpf, ativar_desativar_aldeeiro_db,
    get_perfil_usuario, get_perfis, adicionar_remover_perfis,
    get_formacoes, get_formacoes_por_nucleo, consultar_formacoes_db,
    get_formacao_por_id, get_presentes_por_formacao,
    contar_formacoes_nucleo, relatorio_presenca_db,
    get_info_nucleo, buscar_nucleo_por_id, cadastrar_atualizar_nucleo,
    invalidar_cache, select_nucleos
)

template_path = "C:/Users/joao-/Documents/GitHub/projeto_aldeias/templates"
static_path = os.path.join(os.path.dirname(template_path), "templates", "img")
application = Flask(__name__, template_folder=template_path, static_folder=static_path, static_url_path='/img')
application.secret_key = os.environ.get('SECRET_KEY', 'aldeias-secret-key-2026')
application.permanent_session_lifetime = timedelta(minutes=5)



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
    response = get_dados_aldeias()
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
    result = salvar_aldeeiro(form_data)

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
    response = get_dados_aldeias()
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
    filtros = {
        "nome": nome,
        "nucleo": nucleo
    }

    result = pesquisar_aldeeiros(filtros)
    aldeeiros = json.loads(result["body"])

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

    response = get_dados_aldeias()
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
        result = abrir_formacao_fn(body)
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
        result = registrar_presenca_fn(body)
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
    return render_template("arquivos_informativos.html", equipes=equipes)


@application.route("/arquivos/download", methods=["GET"])
@login_required
def download_arquivo():
    s3_key = request.args.get("s3_key")
    if not s3_key:
        flash("Arquivo não informado.", "error")
        return redirect(url_for('arquivos_informativos'))

    result = gerar_url_download(s3_key)
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

        result = enviar_whatsapp_fn(body)
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
    try:
        resultado = get_info_nucleo(nucleo_id)
        return json.dumps(resultado, ensure_ascii=False), 200, {"Content-Type": "application/json"}
    except Exception as e:
        return json.dumps({"error": str(e)}), 500, {"Content-Type": "application/json"}


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

        try:
            resultados = consultar_formacoes_db(nucleo, data_inicio, data_fim)
        except Exception as e:
            flash(f"Erro ao consultar formações: {str(e)}", "error")
            resultados = []

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

@application.route("/formacao/<int:id_formacao>/presentes", methods=["GET"])
@login_required
@perfil_required('Coordenador')
def lista_presentes_formacao(id_formacao):
    formacao = get_formacao_por_id(id_formacao)
    presentes = get_presentes_por_formacao(id_formacao)

    return render_template(
        "lista_presentes.html",
        formacao=formacao,
        presentes=presentes
    )


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
        zero_presenca = request.form.get("zero_presenca")
        min_presenca = request.form.get("min_presenca")

        try:
            total_formacoes_nucleo = contar_formacoes_nucleo(nucleo, data_inicio, data_fim)
            resultados = relatorio_presenca_db(
                nucleo, data_inicio, data_fim,
                zero_presenca=bool(zero_presenca),
                min_presenca=min_presenca
            )
        except Exception as e:
            flash(f"Erro ao consultar relatório: {str(e)}", "error")
            resultados = []

    filtros = {}
    if request.method == "POST":
        filtros = {
            'nucleo': request.form.get('nucleo', ''),
            'data_inicio': request.form.get('data_inicio', ''),
            'data_fim': request.form.get('data_fim', ''),
            'zero_presenca': request.form.get('zero_presenca', ''),
            'min_presenca': request.form.get('min_presenca', '')
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

        try:
            adicionar_remover_perfis(cpf, perfis_ids, acao)
            flash(f"Perfil(is) {'adicionado(s)' if acao == 'adicionar' else 'removido(s)'} com sucesso!", "success")
        except Exception as e:
            flash(f"Erro: {str(e)}", "error")
        return redirect(url_for('gerenciar_perfis'))

    perfis = get_perfis()
    return render_template("gerenciar_perfis.html", perfis=perfis, nucleos=get_nucleos())


@application.route("/admin/buscar-aldeeiro", methods=["GET"])
@login_required
@perfil_required('Administrador')
def buscar_aldeeiro_por_cpf():
    cpf = request.args.get("cpf", "")
    row = buscar_aldeeiro_por_cpf_db(cpf)
    if row:
        return json.dumps({"nome": row['nome']}), 200, {"Content-Type": "application/json"}
    else:
        return json.dumps({"nome": ""}), 404, {"Content-Type": "application/json"}


@application.route("/admin/buscar-aldeeiro-status", methods=["GET"])
@login_required
@perfil_required('Administrador')
def buscar_aldeeiro_status():
    cpf = request.args.get("cpf", "")
    row = buscar_aldeeiro_status_por_cpf(cpf)
    if row:
        return json.dumps({"nome": row['nome'], "ativo": bool(row['ativo'])}), 200, {"Content-Type": "application/json"}
    else:
        return json.dumps({"nome": ""}), 404, {"Content-Type": "application/json"}


@application.route("/admin/buscar-nucleo", methods=["GET"])
@login_required
@perfil_required('Administrador')
def buscar_nucleo():
    nucleo_id = request.args.get("id", "")
    row = buscar_nucleo_por_id(nucleo_id)
    if row:
        return json.dumps(row, ensure_ascii=False), 200, {"Content-Type": "application/json"}
    else:
        return json.dumps({}), 404, {"Content-Type": "application/json"}


@application.route("/admin/ativar-desativar", methods=["POST"])
@login_required
@perfil_required('Administrador')
def ativar_desativar_aldeeiro():
    cpf = request.form.get("cpf_aldeeiro")
    acao = request.form.get("acao")
    novo_status = 1 if acao == "ativar" else 0

    try:
        ativar_desativar_aldeeiro_db(cpf, novo_status)
        flash(f"Aldeeiro {'ativado' if novo_status == 1 else 'desativado'} com sucesso!", "success")
    except Exception as e:
        flash(f"Erro ao alterar status: {str(e)}", "error")

    return redirect(url_for('gerenciar_perfis'))


@application.route("/admin/cadastrar-nucleo", methods=["POST"])
@login_required
@perfil_required('Administrador')
def cadastrar_nucleo_route():
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
    nucleo_id = request.form.get("nucleo_id") if acao_nucleo != "cadastrar" else None

    try:
        cadastrar_atualizar_nucleo(acao_nucleo, nome, endereco, dias_reuniao, ativo, motivo, cpf_alterou, nucleo_id)
        invalidar_cache('nucleos')
        if acao_nucleo == "cadastrar":
            flash(f"Núcleo '{nome}' cadastrado com sucesso!", "success")
        else:
            flash(f"Núcleo '{nome}' atualizado com sucesso!", "success")
    except Exception as e:
        if "Duplicate" in str(e) or "IntegrityError" in str(type(e).__name__):
            flash(f"Já existe um núcleo com o nome '{nome}'.", "error")
        else:
            flash(f"Erro ao salvar núcleo: {str(e)}", "error")

    return redirect(url_for('gerenciar_perfis'))


# ==================== HELPERS ====================

def get_nucleos():
    return select_nucleos()


application.run(debug=True)
