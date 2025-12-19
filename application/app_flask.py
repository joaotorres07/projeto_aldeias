import json

from flask import Flask, render_template, request
from lambda_get_dados import lambda_handler
from lambda_cadastro import lambda_handler as lambda_handler_cadastro
from lambda_get_aldeeiros import lambda_handler as lambda_handler_aldeeiros

template_path = "C:/Users/UserForce/Documents/GitHub/projeto aldeias/templates"
#application = Flask(__name__, template_folder=os.environ['TEMPLATE_PATH'])
application = Flask(__name__, template_folder=template_path)

NUCLEOS_CACHE = None

@application.route("/init-aldeias", methods=["GET", "POST"])
def index():
    return render_template("index.html")


@application.route("/aldeeiro/form", methods=["GET", "POST"])
def form_aldeeiro():
    response = lambda_handler({}, None)
    data = json.loads(response["body"])
    return render_template(
        "criar_atualizar_aldeeiro.html",
        equipes=data.get("equipes"),
        aldeias_serviu=data.get("aldeias_serviu"),
        aldeias_fez=data.get("aldeias_fez"),
        nucleos=data.get("nucleos")
    )

@application.route("/salvar_atualizar_aldeeiro", methods=["POST"])
def salvar_atualizar_aldeeiro():
    form_data = request.form.to_dict(flat=False)
    result = lambda_handler_cadastro({"body": form_data }, None)

    status_code = result.get("statusCode")
    if status_code == 200:
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
def listar_aldeeiros():
    nucleos = get_nucleos()

    return render_template("listar-aldeeiros.html", nucleos=nucleos)


@application.route("/pesquisarAldeeiros", methods=["GET", "POST"])
def pesquisar_aldeeeiros():
    nome = request.args.get("nome") or request.form.get("nome")
    nucleo = request.args.get("nucleo") or request.form.get("nucleo")
    filtros = {"body": {
        "nome": nome,
        "nucleo": nucleo
        }
    }

    result = lambda_handler_aldeeiros(filtros, None)
    aldeeiros = json.loads(result["body"])
    return render_template("listar-aldeeiros.html", aldeeiros=aldeeiros, nucleos=get_nucleos())


def get_nucleos():
    global NUCLEOS_CACHE
    if NUCLEOS_CACHE is None:
        response = lambda_handler({}, None)
        data = json.loads(response["body"])
        NUCLEOS_CACHE = data.get("nucleos", [])
    return NUCLEOS_CACHE

application.run(debug=True)