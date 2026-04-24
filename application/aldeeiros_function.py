import json
import logging
from decimal import Decimal
from datetime import datetime, date
from database_function import select_aldeeiros_by

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def decimal_serializer(obj):
    if isinstance(obj, Decimal):
        return int(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Tipo não serializável: {type(obj)}")


def pesquisar_aldeeiros(filtros):
    try:
        logger.info("Buscando aldeeiros...")
        data_result = select_aldeeiros_by(filtros)
        retorno_agrupado = agrupar_aldeeiros(data_result)
        return {
            "statusCode": 200,
            "body": json.dumps(retorno_agrupado, default=decimal_serializer, ensure_ascii=False)
        }
    except Exception as e:
        msg_error = f"Erro ao buscar aldeeiros: {str(e)}"
        logger.error(msg_error)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": msg_error})
        }


def agrupar_aldeeiros(rows):
    from collections import Counter
    agrupado = {}
    for r in rows:
        cpf = r["cpf"]

        if cpf not in agrupado:
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
                "aldeias_fez": set(),
                "aldeias_serviu_counter": Counter(),
                "equipes_counter": Counter(),
                "aldeeiro_desde": None
            }

        if r.get("nome_aldeia_fez"):
            agrupado[cpf]["aldeias_fez"].add(r["nome_aldeia_fez"])
        if r.get("data_aldeia_fez"):
            dt = r["data_aldeia_fez"]
            atual = agrupado[cpf]["aldeeiro_desde"]
            if atual is None or dt < atual:
                agrupado[cpf]["aldeeiro_desde"] = dt
        if r.get("aldeia_serviu"):
            agrupado[cpf]["aldeias_serviu_counter"][r["aldeia_serviu"]] += 1
        if r.get("nome_equipe"):
            agrupado[cpf]["equipes_counter"][r["nome_equipe"]] += 1

    resultado = []
    for a in agrupado.values():
        a["aldeias_fez"] = list(a["aldeias_fez"])
        # Format with count: "Aldeia X 2x" or just "Aldeia X" if 1x
        a["aldeias_serviu"] = [
            f"{nome} {count}x" if count > 1 else nome
            for nome, count in a["aldeias_serviu_counter"].items()
        ]
        a["equipes"] = [
            f"{nome} {count}x" if count > 1 else nome
            for nome, count in a["equipes_counter"].items()
        ]
        del a["aldeias_serviu_counter"]
        del a["equipes_counter"]
        resultado.append(a)

    return resultado

