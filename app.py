# ============================================================
# Backend — Sistema de Cadastro de Funcionários com
# Reconhecimento Facial (Stemmoz)
#
# Responsabilidade deste servidor (o "computador/servidor" da
# arquitectura cliente-servidor descrita na monografia):
#   - Receber, através da API, os dados enviados pelo formulário
#     (nome, departamento, foto do BI e foto facial frontal);
#   - Detectar o rosto na foto facial e extrair as suas
#     características (vector de 128 dimensões), usando o
#     algoritmo do Dlib (biblioteca face_recognition);
#   - Guardar essas características — e não a fotografia em si —
#     na base de dados MySQL, juntamente com os dados do
#     funcionário;
#   - Disponibilizar a lista de funcionários já registados.
# ============================================================

import os
import json
import base64
import uuid
from datetime import datetime

import numpy as np
import face_recognition
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error as MySQLError

# ---------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
BI_DIR = os.path.join(UPLOADS_DIR, "bi")
FACIAL_DIR = os.path.join(UPLOADS_DIR, "facial")

os.makedirs(BI_DIR, exist_ok=True)
os.makedirs(FACIAL_DIR, exist_ok=True)

# Credenciais por omissão do XAMPP: utilizador "root", sem password.
# Ajusta aqui caso tenhas configurado uma password no teu MySQL.
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "stemmoz_rh",
}

app = Flask(__name__)
CORS(app)  # permite que o ficheiro cadastro.html (aberto localmente) fale com este servidor


def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)


def gerar_codigo_funcionario():
    ano = datetime.now().year
    return f"{ano}{uuid.uuid4().hex[:6].upper()}"


def guardar_imagem_base64(data_url, pasta, prefixo):
    """Recebe uma dataURL (ex: 'data:image/png;base64,....') e
    guarda-a em disco, devolvendo o caminho relativo do ficheiro."""
    if "," in data_url:
        cabecalho, dados_b64 = data_url.split(",", 1)
    else:
        dados_b64 = data_url

    extensao = "png"
    if "jpeg" in data_url or "jpg" in data_url:
        extensao = "jpg"

    nome_ficheiro = f"{prefixo}_{uuid.uuid4().hex}.{extensao}"
    caminho_absoluto = os.path.join(pasta, nome_ficheiro)

    with open(caminho_absoluto, "wb") as f:
        f.write(base64.b64decode(dados_b64))

    return nome_ficheiro


def extrair_caracteristicas_faciais(caminho_absoluto_imagem):
    """Recebe o caminho de uma imagem facial frontal e devolve o
    vector de 128 características extraído pelo modelo Dlib
    (através da biblioteca face_recognition), ou None caso não
    seja detectado nenhum rosto na imagem."""
    imagem = face_recognition.load_image_file(caminho_absoluto_imagem)
    localizacoes = face_recognition.face_locations(imagem)

    if len(localizacoes) == 0:
        return None, "Não foi detectado nenhum rosto na imagem. Tente novamente com boa iluminação e o rosto de frente para a câmara."

    if len(localizacoes) > 1:
        return None, "Foi detectado mais do que um rosto na imagem. Certifica-te de que apenas uma pessoa aparece na captura."

    encodings = face_recognition.face_encodings(imagem, known_face_locations=localizacoes)
    vector = encodings[0]  # numpy array com 128 posições
    return vector.tolist(), None


# ---------------------------------------------------------------
# Rotas
# ---------------------------------------------------------------

@app.route("/api/saude", methods=["GET"])
def saude():
    return jsonify({"status": "ok", "mensagem": "Servidor Stemmoz a correr."})


@app.route("/api/funcionarios", methods=["POST"])
def cadastrar_funcionario():
    dados = request.get_json(silent=True) or {}

    nome = (dados.get("nome") or "").strip()
    departamento = (dados.get("departamento") or "").strip()
    foto_bi = dados.get("fotoBI")
    foto_facial = dados.get("fotoFacial")

    if not nome or not departamento or not foto_bi or not foto_facial:
        return jsonify({"sucesso": False, "erro": "Faltam campos obrigatórios (nome, departamento, foto do BI ou foto facial)."}), 400

    # 1. Guardar as imagens em disco
    nome_ficheiro_bi = guardar_imagem_base64(foto_bi, BI_DIR, "bi")
    nome_ficheiro_facial = guardar_imagem_base64(foto_facial, FACIAL_DIR, "facial")
    caminho_absoluto_facial = os.path.join(FACIAL_DIR, nome_ficheiro_facial)

    # 2. Extrair as características faciais (vector de 128 dimensões)
    vector, erro = extrair_caracteristicas_faciais(caminho_absoluto_facial)
    if erro:
        # Remove os ficheiros guardados, já que o cadastro não será concluído
        os.remove(os.path.join(BI_DIR, nome_ficheiro_bi))
        os.remove(caminho_absoluto_facial)
        return jsonify({"sucesso": False, "erro": erro}), 422

    # 3. Guardar na base de dados
    codigo = gerar_codigo_funcionario()
    try:
        conexao = get_db_connection()
        cursor = conexao.cursor()
        cursor.execute(
            """
            INSERT INTO funcionarios
                (codigo, nome, departamento, foto_bi_path, foto_facial_path, caracteristicas_faciais)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                codigo,
                nome,
                departamento,
                f"bi/{nome_ficheiro_bi}",
                f"facial/{nome_ficheiro_facial}",
                json.dumps(vector),
            ),
        )
        conexao.commit()
        novo_id = cursor.lastrowid
        cursor.close()
        conexao.close()
    except MySQLError as e:
        return jsonify({"sucesso": False, "erro": f"Erro ao gravar na base de dados: {e}"}), 500

    return jsonify({
        "sucesso": True,
        "mensagem": f'Funcionário "{nome}" registado com sucesso.',
        "funcionario": {
            "id": novo_id,
            "codigo": codigo,
            "nome": nome,
            "departamento": departamento,
            "fotoFacialUrl": f"/uploads/facial/{nome_ficheiro_facial}",
        }
    }), 201


@app.route("/api/funcionarios", methods=["GET"])
def listar_funcionarios():
    try:
        conexao = get_db_connection()
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT id, codigo, nome, departamento, foto_facial_path, data_cadastro
            FROM funcionarios
            ORDER BY data_cadastro DESC
            """
        )
        linhas = cursor.fetchall()
        cursor.close()
        conexao.close()
    except MySQLError as e:
        return jsonify({"sucesso": False, "erro": f"Erro ao consultar a base de dados: {e}"}), 500

    funcionarios = []
    for linha in linhas:
        funcionarios.append({
            "id": linha["id"],
            "codigo": linha["codigo"],
            "nome": linha["nome"],
            "departamento": linha["departamento"],
            "fotoFacialUrl": f"/uploads/{linha['foto_facial_path']}",
            "dataCadastro": linha["data_cadastro"].strftime("%d/%m/%Y %H:%M"),
        })

    return jsonify({"sucesso": True, "funcionarios": funcionarios})


@app.route("/uploads/<path:subcaminho>", methods=["GET"])
def servir_imagem(subcaminho):
    return send_from_directory(UPLOADS_DIR, subcaminho)


if __name__ == "__main__":
    print("Servidor Stemmoz a correr em http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
