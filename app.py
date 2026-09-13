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
import io
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

# Distância máxima (face_distance) para considerar duas faces como
# pertencentes à mesma pessoa. Quanto menor, mais rigorosa a comparação.
LIMIAR_RECONHECIMENTO = 0.6

# ---------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
BI_DIR = os.path.join(UPLOADS_DIR, "bi")
FACIAL_DIR = os.path.join(UPLOADS_DIR, "facial")

os.makedirs(BI_DIR, exist_ok=True)
os.makedirs(FACIAL_DIR, exist_ok=True)

# Ligação ao servidor MySQL (porta por omissão 3306). Cada valor pode ser
# substituído por uma variável de ambiente — é assim que o docker-compose
# aponta o backend para o serviço "mysql" do próprio compose, sem precisar
# de alterar este ficheiro.
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "102.211.186.44"),
    "port": int(os.environ.get("DB_PORT", "3306")),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", "07123752136"),
    "database": os.environ.get("DB_NAME", "stemmoz_rh"),
}

app = Flask(__name__)
CORS(app)  # permite que o frontend React (noutra origem/porta) fale com este servidor


def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)


def inicializar_base_de_dados():
    """Garante que a base de dados e a tabela 'funcionarios' existem no
    servidor MySQL configurado (host/porta acima), criando-as
    automaticamente caso ainda não existam — não é preciso correr o
    schema.sql manualmente no phpMyAdmin."""
    config_sem_bd = {k: v for k, v in DB_CONFIG.items() if k != "database"}

    conexao = mysql.connector.connect(**config_sem_bd)
    cursor = conexao.cursor()
    cursor.execute(
        f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']} "
        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    cursor.close()
    conexao.close()

    conexao = get_db_connection()
    cursor = conexao.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS funcionarios (
          id INT AUTO_INCREMENT PRIMARY KEY,
          codigo VARCHAR(20) NOT NULL UNIQUE,
          nome VARCHAR(150) NOT NULL,
          departamento VARCHAR(100) NOT NULL,
          foto_bi_path VARCHAR(255) NOT NULL,
          foto_facial_path VARCHAR(255) NOT NULL,
          caracteristicas_faciais TEXT NOT NULL,
          data_cadastro DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conexao.commit()
    cursor.close()
    conexao.close()
    print(f"Base de dados '{DB_CONFIG['database']}' e tabela 'funcionarios' prontas em {DB_CONFIG['host']}:{DB_CONFIG['port']}.")


# Corre já ao importar o módulo (não só quando é executado directamente),
# para que também funcione quando o servidor é arrancado com gunicorn.
try:
    inicializar_base_de_dados()
except MySQLError as e:
    print(f"[aviso] Não foi possível preparar a base de dados no arranque: {e}")


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


def extrair_caracteristicas_de_imagem(imagem):
    """Recebe uma imagem já carregada (array numpy) e devolve o vector
    de 128 características extraído pelo modelo Dlib (através da
    biblioteca face_recognition), ou None caso não seja detectado
    nenhum rosto na imagem."""
    localizacoes = face_recognition.face_locations(imagem)

    if len(localizacoes) == 0:
        return None, "Não foi detectado nenhum rosto na imagem. Tente novamente com boa iluminação e o rosto de frente para a câmara."

    if len(localizacoes) > 1:
        return None, "Foi detectado mais do que um rosto na imagem. Certifica-te de que apenas uma pessoa aparece na captura."

    encodings = face_recognition.face_encodings(imagem, known_face_locations=localizacoes)
    vector = encodings[0]  # numpy array com 128 posições
    return vector.tolist(), None


def extrair_caracteristicas_faciais(caminho_absoluto_imagem):
    """Variante que recebe o caminho de um ficheiro em disco."""
    imagem = face_recognition.load_image_file(caminho_absoluto_imagem)
    return extrair_caracteristicas_de_imagem(imagem)


def carregar_imagem_de_data_url(data_url):
    """Descodifica uma dataURL base64 directamente em memória (sem
    gravar em disco), devolvendo uma imagem pronta para o
    face_recognition."""
    if "," in data_url:
        _, dados_b64 = data_url.split(",", 1)
    else:
        dados_b64 = data_url
    binario = base64.b64decode(dados_b64)
    return face_recognition.load_image_file(io.BytesIO(binario))


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


@app.route("/api/reconhecimento", methods=["POST"])
def pesquisar_funcionario_por_face():
    """Recebe uma foto (dataURL) captada ao vivo, extrai as suas
    características faciais e pesquisa, na base de dados, qual o
    funcionário já cadastrado cujo rosto mais se aproxima."""
    dados = request.get_json(silent=True) or {}
    foto = dados.get("foto")

    if not foto:
        return jsonify({"sucesso": False, "erro": "Falta a foto facial para a pesquisa."}), 400

    try:
        imagem = carregar_imagem_de_data_url(foto)
    except Exception:
        return jsonify({"sucesso": False, "erro": "Não foi possível ler a imagem enviada."}), 400

    vector, erro = extrair_caracteristicas_de_imagem(imagem)
    if erro:
        return jsonify({"sucesso": False, "erro": erro}), 422

    vector_pesquisado = np.array(vector)

    try:
        conexao = get_db_connection()
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT id, codigo, nome, departamento, foto_facial_path,
                   caracteristicas_faciais, data_cadastro
            FROM funcionarios
            """
        )
        linhas = cursor.fetchall()
        cursor.close()
        conexao.close()
    except MySQLError as e:
        return jsonify({"sucesso": False, "erro": f"Erro ao consultar a base de dados: {e}"}), 500

    if not linhas:
        return jsonify({
            "sucesso": True,
            "encontrado": False,
            "mensagem": "Ainda não há funcionários registados para comparar.",
        })

    vectores_conhecidos = [np.array(json.loads(linha["caracteristicas_faciais"])) for linha in linhas]
    distancias = face_recognition.face_distance(vectores_conhecidos, vector_pesquisado)
    indice_melhor = int(np.argmin(distancias))
    melhor_distancia = float(distancias[indice_melhor])
    melhor_linha = linhas[indice_melhor]

    if melhor_distancia > LIMIAR_RECONHECIMENTO:
        return jsonify({
            "sucesso": True,
            "encontrado": False,
            "distancia": round(melhor_distancia, 4),
            "mensagem": "Nenhum funcionário corresponde a este rosto.",
        })

    return jsonify({
        "sucesso": True,
        "encontrado": True,
        "distancia": round(melhor_distancia, 4),
        "funcionario": {
            "id": melhor_linha["id"],
            "codigo": melhor_linha["codigo"],
            "nome": melhor_linha["nome"],
            "departamento": melhor_linha["departamento"],
            "fotoFacialUrl": f"/uploads/{melhor_linha['foto_facial_path']}",
            "dataCadastro": melhor_linha["data_cadastro"].strftime("%d/%m/%Y %H:%M"),
        },
    })


@app.route("/uploads/<path:subcaminho>", methods=["GET"])
def servir_imagem(subcaminho):
    return send_from_directory(UPLOADS_DIR, subcaminho)


if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "true").lower() == "true"
    print(f"Servidor Stemmoz a correr em http://localhost:5000 (MySQL em {DB_CONFIG['host']}:{DB_CONFIG['port']})")
    app.run(host="0.0.0.0", port=5000, debug=debug_mode, use_reloader=False)
