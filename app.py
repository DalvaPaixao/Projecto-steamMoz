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
#   - Verificar que o rosto da foto do BI é da mesma pessoa que
#     fez a captura facial (caso contrário, o cadastro é recusado);
#   - Verificar que o funcionário ainda não está cadastrado
#     (caso contrário, o cadastro é recusado);
#   - Guardar os dados do funcionário na base de dados MySQL;
#   - Disponibilizar a lista de funcionários já registados;
#   - Registar a PRESENÇA (entrada e saída) de cada funcionário,
#     identificado pelo rosto, e disponibilizar o histórico;
#   - Exigir LOGIN: só utilizadores autenticados podem usar a API
#     (cadastrar, listar, marcar presença, histórico e ver fotos).
#
# Que dados ficam guardados (política actual do sistema):
#   - Na base de dados: nome, departamento, código, o vector facial
#     (128 números — é ele que se usa nas comparações), os caminhos das
#     fotografias e os registos de presença.
#   - No disco (pasta uploads/): a foto do BI e a foto facial de cada
#     funcionário. Servem de comprovativo e para mostrar o funcionário
#     nos ecrãs. Se a política da instituição for NÃO guardar fotografias,
#     é nesta parte (passo 6 do cadastro) que isso se altera.
# ============================================================

import os
import io
import json
import math
import time
import base64
import secrets
import threading
import unicodedata
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps

import numpy as np
import face_recognition
from PIL import Image, ImageOps
from flask import Flask, request, jsonify, send_from_directory, g
from flask_cors import CORS
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from mysql.connector import Error as MySQLError

# Distância máxima (face_distance) para considerar duas faces como
# pertencentes à mesma pessoa. Quanto menor, mais rigorosa a comparação.
LIMIAR_RECONHECIMENTO = 0.6

# Distância máxima entre o rosto da foto do BI e o rosto da captura para
# aceitar que são a mesma pessoa. As fotos de BI costumam ser antigas e de
# pior qualidade, por isso o limiar é o valor padrão do Dlib (0.6).
# Se o sistema estiver a recusar pessoas certas, aumenta (ex: 0.65);
# se estiver a aceitar pessoas erradas, diminui (ex: 0.55).
LIMIAR_BI_CAPTURA = 0.6

# Distância máxima entre a captura e os funcionários já cadastrados para
# considerar que é a MESMA pessoa a tentar cadastrar-se outra vez. Aqui as
# duas imagens vêm da câmara, por isso o limiar é mais rigoroso, para não
# bloquear por engano uma pessoa diferente.
LIMIAR_DUPLICADO = 0.5

# Distância máxima para aceitar que o rosto diante da câmara é o de um
# funcionário ao MARCAR PRESENÇA. É rigoroso de propósito: é preferível
# pedir para repetir do que registar a presença na pessoa errada.
LIMIAR_PRESENCA = 0.5

# Minutos que têm de passar entre a entrada e a saída (evita registar a
# saída por engano logo a seguir à entrada, ex: se a pessoa passar duas vezes).
MIN_MINUTOS_ENTRE_MARCACOES = 5

# Limites das imagens recebidas (protegem o servidor de ficheiros enormes
# ou inválidos). O pedido todo também tem um tamanho máximo.
MAX_BYTES_IMAGEM = 8 * 1024 * 1024        # 8 MB por imagem (já descodificada)
MAX_PIXELS_IMAGEM = 40_000_000            # 40 megapixels
MAX_LADO_IMAGEM = 1280                    # a imagem é reduzida a isto antes da análise
MAX_TAMANHO_PEDIDO = 24 * 1024 * 1024     # 24 MB (cobre BI + captura em base64)
# (MPO é o formato de muitas fotos JPG tiradas com telemóveis)
FORMATOS_IMAGEM = {"JPEG": "jpg", "MPO": "jpg", "PNG": "png", "WEBP": "webp"}

# Nome do "cadeado" do MySQL que garante que dois cadastros em simultâneo
# não passam ao mesmo tempo pela verificação de duplicados.
NOME_TRAVA_CADASTRO = "stemmoz_cadastro"

# Intervalo máximo (em dias) que o histórico de presenças pode abranger.
MAX_DIAS_HISTORICO = 366

# ---------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
BI_DIR = os.path.join(UPLOADS_DIR, "bi")
FACIAL_DIR = os.path.join(UPLOADS_DIR, "facial")

os.makedirs(BI_DIR, exist_ok=True)
os.makedirs(FACIAL_DIR, exist_ok=True)


def carregar_ficheiro_env():
    """Lê o ficheiro .env (na mesma pasta deste app.py), se existir, e coloca
    os valores nas variáveis de ambiente. Variáveis já definidas no sistema
    (ex: pelo docker-compose) não são substituídas. É no .env que se escrevem
    ADMIN_USER, ADMIN_PASSWORD e (opcionalmente) SECRET_KEY e DB_PASSWORD."""
    caminho = os.path.join(BASE_DIR, ".env")
    if not os.path.isfile(caminho):
        return
    with open(caminho, encoding="utf-8-sig") as f:
        for linha in f:
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue
            chave, valor = linha.split("=", 1)
            chave = chave.strip()
            valor = valor.strip()
            if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
                valor = valor[1:-1]
            os.environ.setdefault(chave, valor)


carregar_ficheiro_env()


def obter_fuso_horario():
    """Fuso horário usado nas datas e horas das presenças. Por omissão,
    Moçambique (UTC+2, sem hora de verão). Pode mudar-se com a variável
    FUSO_HORARIO no .env (ex: Africa/Maputo)."""
    nome = os.environ.get("FUSO_HORARIO", "Africa/Maputo")
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(nome)
    except Exception:
        print(f"[aviso] Fuso horário '{nome}' indisponível neste computador; a usar UTC+02:00 (hora de Moçambique).")
        return timezone(timedelta(hours=2), "CAT")


FUSO_HORARIO = obter_fuso_horario()


def agora_local():
    """Data e hora actuais no fuso horário configurado (sem informação de fuso)."""
    return datetime.now(FUSO_HORARIO).replace(tzinfo=None)


# ---------------------------------------------------------------
# Login (autenticação)
# ---------------------------------------------------------------
# Conta de administrador criada/actualizada automaticamente ao arrancar,
# a partir do .env (ADMIN_USER e ADMIN_PASSWORD). A senha nunca é guardada
# em texto: na base de dados fica apenas o seu "hash".
ADMIN_USER = os.environ.get("ADMIN_USER", "").strip()
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

# Durante quanto tempo uma sessão (token) é válida depois do login.
TOKEN_VALIDADE_SEGUNDOS = int(os.environ.get("TOKEN_VALIDADE_HORAS", "8")) * 3600

# Protecção contra tentativas de adivinhar a senha: depois de
# MAX_TENTATIVAS_LOGIN falhas seguidas, o login fica bloqueado durante
# JANELA_TENTATIVAS_SEGUNDOS para esse utilizador a partir desse computador.
# (Os registos ficam na memória deste processo: reiniciar o servidor apaga-os.
# Para o servidor actual — 1 processo — é suficiente.)
MAX_TENTATIVAS_LOGIN = 5
JANELA_TENTATIVAS_SEGUNDOS = 300


def obter_chave_secreta():
    """Chave usada para assinar os tokens de sessão. Vem da variável
    SECRET_KEY. Se não existir, gera-se uma aleatória e grava-se no .env
    para que as sessões sobrevivam a um reinício do servidor."""
    chave = os.environ.get("SECRET_KEY", "").strip()
    if chave:
        return chave

    chave = secrets.token_hex(32)
    try:
        caminho = os.path.join(BASE_DIR, ".env")
        existe_conteudo = os.path.isfile(caminho) and os.path.getsize(caminho) > 0
        with open(caminho, "a", encoding="utf-8") as f:
            f.write(("\n" if existe_conteudo else "") + f"SECRET_KEY={chave}\n")
    except OSError:
        print("[aviso] Não foi possível gravar SECRET_KEY no .env; as sessões serão terminadas quando o servidor reiniciar.")
    os.environ["SECRET_KEY"] = chave
    return chave


SECRET_KEY = obter_chave_secreta()
_serializador = URLSafeTimedSerializer(SECRET_KEY, salt="stemmoz-sessao")
_HASH_FALSO = generate_password_hash("senha-falsa-para-igualar-tempos", method="pbkdf2:sha256")
_tentativas_falhadas = {}  # "ip|utilizador" -> lista de instantes (time.time()) das falhas


def normalizar_utilizador(texto):
    """'Dalva Paixão', 'dalva paixao' e 'DALVA  PAIXAO' contam como o mesmo
    nome de utilizador (sem maiúsculas, acentos nem espaços a mais)."""
    texto = unicodedata.normalize("NFKD", texto.strip())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.casefold().split())


def criar_token(utilizador_id, nome_exibicao):
    return _serializador.dumps({"id": utilizador_id, "nome": nome_exibicao})


def validar_token(token):
    """Devolve os dados da sessão se o token for válido e não tiver
    expirado; caso contrário devolve None."""
    if not token:
        return None
    try:
        return _serializador.loads(token, max_age=TOKEN_VALIDADE_SEGUNDOS)
    except (BadSignature, SignatureExpired):
        return None


def requer_login():
    """Decorador que só deixa passar pedidos com uma sessão válida. O token vai
    sempre no cabeçalho 'Authorization: Bearer <token>' (nunca no endereço, para
    não ficar nos registos do servidor nem no histórico do navegador)."""
    def decorador(funcao):
        @wraps(funcao)
        def envolvido(*args, **kwargs):
            cabecalho = request.headers.get("Authorization", "")
            token = cabecalho[7:].strip() if cabecalho.startswith("Bearer ") else None

            sessao = validar_token(token)
            if sessao is None:
                return jsonify({"sucesso": False, "erro": "Sessão inválida ou expirada. Faz login novamente."}), 401
            g.sessao = sessao
            return funcao(*args, **kwargs)
        return envolvido
    return decorador


def _chave_tentativas(utilizador_normalizado):
    return f"{request.remote_addr}|{utilizador_normalizado}"


def login_bloqueado(chave):
    agora = time.time()
    recentes = [t for t in _tentativas_falhadas.get(chave, []) if agora - t < JANELA_TENTATIVAS_SEGUNDOS]
    _tentativas_falhadas[chave] = recentes
    return len(recentes) >= MAX_TENTATIVAS_LOGIN


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
    "connection_timeout": 10,
}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_TAMANHO_PEDIDO
CORS(app)  # permite que o frontend React (noutra origem/porta) fale com este servidor


@app.errorhandler(413)
def pedido_demasiado_grande(_erro):
    return jsonify({"sucesso": False, "erro": "O pedido é demasiado grande. Usa imagens mais pequenas (máximo 8 MB cada)."}), 413


def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)


def inicializar_base_de_dados():
    """Garante que a base de dados e as tabelas ('funcionarios', 'utilizadores'
    e 'presencas') existem no servidor MySQL configurado (host/porta acima),
    criando-as automaticamente caso ainda não existam — não é preciso correr
    o schema.sql manualmente no phpMyAdmin."""
    # Passo 1: criar a base de dados. Se o utilizador MySQL não tiver permissão
    # para isso (ou se a base já existir), não é um erro: segue-se para o passo 2.
    try:
        config_sem_bd = {k: v for k, v in DB_CONFIG.items() if k != "database"}
        conexao = mysql.connector.connect(**config_sem_bd)
        cursor = conexao.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']} "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        cursor.close()
        conexao.close()
    except MySQLError as e:
        print(f"[aviso] Não foi possível criar a base de dados '{DB_CONFIG['database']}' ({e}). A tentar usar a que já existe.")

    # Passo 2: ligar à base de dados e criar as tabelas. Se isto falhar, o
    # erro sobe para quem chamou (ver garantir_base_de_dados).
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
    # Tabela dos utilizadores que podem entrar no sistema (login).
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS utilizadores (
          id INT AUTO_INCREMENT PRIMARY KEY,
          nome_utilizador VARCHAR(100) NOT NULL UNIQUE,
          nome_exibicao VARCHAR(150) NOT NULL,
          password_hash VARCHAR(255) NOT NULL,
          data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    # Tabela das presenças: no máximo UMA entrada e UMA saída por funcionário
    # por dia (garantido pela chave única, mesmo com pedidos em simultâneo).
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS presencas (
          id INT AUTO_INCREMENT PRIMARY KEY,
          funcionario_id INT NOT NULL,
          tipo VARCHAR(10) NOT NULL,
          data_hora DATETIME NOT NULL,
          data_dia DATE NOT NULL,
          distancia FLOAT NULL,
          UNIQUE KEY uq_funcionario_dia_tipo (funcionario_id, data_dia, tipo),
          INDEX idx_data_dia (data_dia),
          FOREIGN KEY (funcionario_id) REFERENCES funcionarios(id) ON DELETE CASCADE
        )
        """
    )
    conexao.commit()

    # Cria (ou actualiza a senha de) o administrador definido no .env.
    if ADMIN_USER and ADMIN_PASSWORD:
        nome_normalizado = normalizar_utilizador(ADMIN_USER)
        hash_senha = generate_password_hash(ADMIN_PASSWORD, method="pbkdf2:sha256")
        cursor.execute("SELECT id FROM utilizadores WHERE nome_utilizador = %s", (nome_normalizado,))
        if cursor.fetchone():
            cursor.execute(
                "UPDATE utilizadores SET nome_exibicao = %s, password_hash = %s WHERE nome_utilizador = %s",
                (ADMIN_USER, hash_senha, nome_normalizado),
            )
        else:
            cursor.execute(
                "INSERT INTO utilizadores (nome_utilizador, nome_exibicao, password_hash) VALUES (%s, %s, %s)",
                (nome_normalizado, ADMIN_USER, hash_senha),
            )
        conexao.commit()
        print(f"[login] Utilizador administrador '{ADMIN_USER}' pronto.")
    else:
        print("[aviso] ADMIN_USER / ADMIN_PASSWORD não definidos no .env: se ainda não existir nenhum utilizador, ninguém consegue entrar no sistema.")

    cursor.close()
    conexao.close()
    print(f"Base de dados '{DB_CONFIG['database']}' e tabelas 'funcionarios', 'utilizadores' e 'presencas' prontas em {DB_CONFIG['host']}:{DB_CONFIG['port']}.")


_bd_pronta = False
_ultima_tentativa_bd = 0.0
_trava_inicializacao = threading.Lock()
SEGUNDOS_ENTRE_TENTATIVAS_BD = 5


def garantir_base_de_dados():
    """Devolve True se a base de dados está pronta. Se ainda não estiver (por
    exemplo, porque o MySQL estava desligado quando o servidor arrancou),
    tenta prepará-la outra vez — é chamada em cada pedido até conseguir (com
    uma pausa de alguns segundos entre tentativas)."""
    global _bd_pronta, _ultima_tentativa_bd
    if _bd_pronta:
        return True
    with _trava_inicializacao:
        if _bd_pronta:
            return True
        if time.time() - _ultima_tentativa_bd < SEGUNDOS_ENTRE_TENTATIVAS_BD:
            return False
        _ultima_tentativa_bd = time.time()
        try:
            inicializar_base_de_dados()
            _bd_pronta = True
        except MySQLError as e:
            print(f"[aviso] A base de dados ainda não está pronta: {e}")
    return _bd_pronta


# Corre já ao importar o módulo (não só quando é executado directamente),
# para que também funcione quando o servidor é arrancado com gunicorn.
garantir_base_de_dados()


@app.before_request
def verificar_base_de_dados():
    """Antes de cada pedido à API (menos /api/saude), confirma que a base de
    dados está pronta; se não estiver, responde com um erro claro em vez de
    deixar rebentar com erros de tabelas inexistentes."""
    if request.method == "OPTIONS" or not request.path.startswith("/api/") or request.path == "/api/saude":
        return None
    if not garantir_base_de_dados():
        return jsonify({
            "sucesso": False,
            "erro": "A base de dados não está disponível neste momento. Confirma que o servidor MySQL está ligado e tenta novamente.",
        }), 503
    return None


def gerar_codigo_funcionario():
    ano = datetime.now().year
    return f"{ano}{uuid.uuid4().hex[:6].upper()}"


def decodificar_imagem_data_url(data_url, descricao):
    """Valida e descodifica uma dataURL base64 ('data:image/png;base64,....').
    Confirma o tamanho, que é mesmo uma imagem JPG/PNG/WEBP legível (e não
    apenas um ficheiro com extensão de imagem), corrige a rotação guardada
    pelo telemóvel (EXIF) e reduz imagens muito grandes.
    Devolve (bytes originais, imagem como array numpy RGB, extensão real).
    Em caso de problema levanta ValueError com uma mensagem em português."""
    if not isinstance(data_url, str) or not data_url:
        raise ValueError(f"{descricao}: falta a imagem.")

    dados_b64 = data_url.split(",", 1)[1] if "," in data_url else data_url

    # Verifica o tamanho ANTES de descodificar, para não gastar memória à toa.
    if len(dados_b64) > (MAX_BYTES_IMAGEM * 4) // 3 + 16:
        raise ValueError(f"{descricao}: imagem demasiado grande (máximo {MAX_BYTES_IMAGEM // (1024 * 1024)} MB).")

    try:
        binario = base64.b64decode(dados_b64, validate=True)
    except ValueError:
        raise ValueError(f"{descricao}: o ficheiro enviado não é uma imagem válida.") from None

    if len(binario) > MAX_BYTES_IMAGEM:
        raise ValueError(f"{descricao}: imagem demasiado grande (máximo {MAX_BYTES_IMAGEM // (1024 * 1024)} MB).")

    try:
        imagem = Image.open(io.BytesIO(binario))
        formato = imagem.format
        if formato not in FORMATOS_IMAGEM:
            raise ValueError(f"{descricao}: formato de imagem não suportado. Usa JPG ou PNG.")
        if imagem.width * imagem.height > MAX_PIXELS_IMAGEM:
            raise ValueError(f"{descricao}: a resolução da imagem é demasiado alta. Usa uma foto mais pequena.")
        imagem.load()  # força a leitura completa: apanha ficheiros truncados ou corrompidos
    except ValueError:
        raise
    except Exception:
        raise ValueError(f"{descricao}: a imagem está corrompida ou não é válida.") from None

    imagem = ImageOps.exif_transpose(imagem).convert("RGB")
    if max(imagem.size) > MAX_LADO_IMAGEM:
        imagem.thumbnail((MAX_LADO_IMAGEM, MAX_LADO_IMAGEM))
    return binario, np.array(imagem), FORMATOS_IMAGEM[formato]


def guardar_bytes_imagem(binario, extensao, pasta, prefixo):
    """Guarda em disco os bytes de uma imagem já validada, devolvendo o nome
    do ficheiro criado (nome aleatório; a extensão é a do formato real)."""
    nome_ficheiro = f"{prefixo}_{uuid.uuid4().hex}.{extensao}"
    with open(os.path.join(pasta, nome_ficheiro), "wb") as f:
        f.write(binario)
    return nome_ficheiro


def guardar_imagem_base64(data_url, pasta, prefixo):
    """Recebe uma dataURL (ex: 'data:image/png;base64,....'), valida-a e
    guarda-a em disco, devolvendo o nome do ficheiro."""
    binario, _, extensao = decodificar_imagem_data_url(data_url, "Imagem")
    return guardar_bytes_imagem(binario, extensao, pasta, prefixo)


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
    """Descodifica e valida uma dataURL base64 directamente em memória (sem
    gravar em disco), devolvendo uma imagem pronta para o face_recognition.
    Levanta ValueError se a imagem não for válida."""
    _, imagem, _ = decodificar_imagem_data_url(data_url, "Foto facial")
    return imagem


def carregar_imagem_bi_de_data_url(data_url):
    """Igual à anterior, para a foto do BI (normalmente tirada com o
    telemóvel). Levanta ValueError se a imagem não for válida."""
    _, imagem, _ = decodificar_imagem_data_url(data_url, "Foto do BI")
    return imagem


def extrair_caracteristicas_do_bi(imagem):
    """Devolve o vector facial da foto do BI. Um BI pode ter mais do que um
    rosto (foto principal + marca de segurança), por isso, se houver vários,
    usa-se o maior, que é a foto principal do titular."""
    localizacoes = []
    for ampliacoes in (1, 2):
        localizacoes = face_recognition.face_locations(imagem, number_of_times_to_upsample=ampliacoes)
        if localizacoes:
            break

    if not localizacoes:
        return None, "Não foi detectado nenhum rosto na foto do BI. Carrega uma foto nítida, bem iluminada e com o documento inteiro visível, sem reflexos."

    # localizacao = (topo, direita, fundo, esquerda)
    principal = max(localizacoes, key=lambda l: (l[2] - l[0]) * (l[1] - l[3]))
    encodings = face_recognition.face_encodings(imagem, known_face_locations=[principal])
    return encodings[0].tolist(), None


def distancia_entre_rostos(vector_a, vector_b):
    """Distância entre dois vectores faciais (0 = iguais; quanto maior, mais
    diferentes)."""
    return float(face_recognition.face_distance([np.array(vector_b)], np.array(vector_a))[0])


def remover_ficheiro_silenciosamente(caminho):
    try:
        os.remove(caminho)
    except OSError:
        pass


def formatar_hora(data_hora):
    return data_hora.strftime("%H:%M")


# ---------------------------------------------------------------
# Rotas
# ---------------------------------------------------------------

@app.route("/api/saude", methods=["GET"])
def saude():
    return jsonify({"status": "ok", "mensagem": "Servidor Stemmoz a correr.", "baseDeDados": _bd_pronta})


@app.route("/api/login", methods=["POST"])
def login():
    """Recebe {utilizador, senha}. Se estiverem certos, devolve um token de
    sessão que o frontend envia em todos os pedidos seguintes."""
    dados = request.get_json(silent=True) or {}
    utilizador = dados.get("utilizador")
    senha = dados.get("senha")

    if not isinstance(utilizador, str) or not isinstance(senha, str) or not utilizador.strip() or not senha:
        return jsonify({"sucesso": False, "erro": "Preenche o nome de utilizador e a senha."}), 400

    nome_normalizado = normalizar_utilizador(utilizador)
    chave = _chave_tentativas(nome_normalizado)

    if login_bloqueado(chave):
        return jsonify({
            "sucesso": False,
            "erro": f"Demasiadas tentativas falhadas. Aguarda {JANELA_TENTATIVAS_SEGUNDOS // 60} minutos e tenta novamente.",
        }), 429

    try:
        conexao = get_db_connection()
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, nome_exibicao, password_hash FROM utilizadores WHERE nome_utilizador = %s",
            (nome_normalizado,),
        )
        linha = cursor.fetchone()
        cursor.close()
        conexao.close()
    except MySQLError as e:
        return jsonify({"sucesso": False, "erro": f"Erro ao consultar a base de dados: {e}"}), 500

    # Mesmo que o utilizador não exista, faz-se uma verificação de senha
    # "falsa" para que a resposta demore o mesmo tempo nos dois casos.
    senha_certa = check_password_hash(linha["password_hash"] if linha else _HASH_FALSO, senha)

    if not linha or not senha_certa:
        _tentativas_falhadas.setdefault(chave, []).append(time.time())
        return jsonify({"sucesso": False, "erro": "Nome de utilizador ou senha incorrectos."}), 401

    _tentativas_falhadas.pop(chave, None)
    return jsonify({
        "sucesso": True,
        "token": criar_token(linha["id"], linha["nome_exibicao"]),
        "utilizador": linha["nome_exibicao"],
        "expiraEmSegundos": TOKEN_VALIDADE_SEGUNDOS,
    })


@app.route("/api/sessao", methods=["GET"])
@requer_login()
def sessao_actual():
    """Permite ao frontend confirmar se o token guardado ainda é válido."""
    return jsonify({"sucesso": True, "utilizador": g.sessao["nome"]})


@app.route("/api/funcionarios", methods=["POST"])
@requer_login()
def cadastrar_funcionario():
    dados = request.get_json(silent=True) or {}

    nome = (dados.get("nome") or "").strip()
    departamento = (dados.get("departamento") or "").strip()
    foto_bi = dados.get("fotoBI")
    foto_facial = dados.get("fotoFacial")

    if not nome or not departamento or not foto_bi or not foto_facial:
        return jsonify({"sucesso": False, "erro": "Faltam campos obrigatórios (nome, departamento, foto do BI ou foto facial)."}), 400

    # 1. Validar e ler as duas imagens em memória (tamanho, formato real,
    #    rotação). Nada é gravado em disco enquanto todas as validações
    #    abaixo não passarem.
    try:
        bytes_facial, imagem_facial, extensao_facial = decodificar_imagem_data_url(foto_facial, "Foto facial")
        bytes_bi, imagem_bi, extensao_bi = decodificar_imagem_data_url(foto_bi, "Foto do BI")
    except ValueError as e:
        return jsonify({"sucesso": False, "erro": str(e)}), 400

    # 2. Extrair as características faciais da captura (vector de 128 dimensões)
    vector, erro = extrair_caracteristicas_de_imagem(imagem_facial)
    if erro:
        return jsonify({"sucesso": False, "erro": erro}), 422

    # 3. Extrair as características do rosto que aparece na foto do BI
    vector_bi, erro_bi = extrair_caracteristicas_do_bi(imagem_bi)
    if erro_bi:
        return jsonify({"sucesso": False, "erro": erro_bi}), 422

    # 4. VALIDAÇÃO: o rosto do BI tem de ser da mesma pessoa que fez a captura
    distancia_bi = distancia_entre_rostos(vector, vector_bi)
    print(f"[cadastro] distância BI vs captura = {distancia_bi:.4f} (limiar {LIMIAR_BI_CAPTURA})")
    if distancia_bi > LIMIAR_BI_CAPTURA:
        return jsonify({
            "sucesso": False,
            "motivo": "bi_nao_corresponde",
            "distancia": round(distancia_bi, 4),
            "erro": "O rosto da captura não corresponde à foto do documento de identificação (BI). O cadastro não foi efectuado.",
        }), 422

    # 5 a 7. Verificar duplicados, guardar as fotos e gravar na base de dados,
    #    tudo dentro de um "cadeado" do MySQL: se dois cadastros chegarem ao
    #    mesmo tempo, o segundo espera pelo primeiro, e assim vê o funcionário
    #    que acabou de ser registado (evita cadastros duplicados em simultâneo).
    conexao = None
    cursor = None
    trava_obtida = False
    ficheiros_gravados = []
    try:
        conexao = get_db_connection()
        cursor = conexao.cursor(dictionary=True)

        cursor.execute("SELECT GET_LOCK(%s, %s) AS obtido", (NOME_TRAVA_CADASTRO, 15))
        resultado_trava = cursor.fetchone()
        trava_obtida = bool(resultado_trava and resultado_trava["obtido"] == 1)
        if not trava_obtida:
            return jsonify({"sucesso": False, "erro": "O servidor está a processar outro cadastro. Tenta novamente dentro de alguns segundos."}), 503

        # 5. VALIDAÇÃO: o funcionário não pode estar cadastrado mais do que uma vez
        cursor.execute("SELECT id, codigo, nome, caracteristicas_faciais FROM funcionarios")
        existentes = cursor.fetchall()

        if existentes:
            vectores_conhecidos = [np.array(json.loads(linha["caracteristicas_faciais"])) for linha in existentes]
            distancias = face_recognition.face_distance(vectores_conhecidos, np.array(vector))
            indice_mais_proximo = int(np.argmin(distancias))
            distancia_mais_proxima = float(distancias[indice_mais_proximo])
            print(f"[cadastro] distância mínima aos já cadastrados = {distancia_mais_proxima:.4f} (limiar {LIMIAR_DUPLICADO})")

            if distancia_mais_proxima <= LIMIAR_DUPLICADO:
                ja_cadastrado = existentes[indice_mais_proximo]
                return jsonify({
                    "sucesso": False,
                    "motivo": "duplicado",
                    "distancia": round(distancia_mais_proxima, 4),
                    "erro": f'Funcionário já cadastrado: {ja_cadastrado["nome"]} (código {ja_cadastrado["codigo"]}). O cadastro não foi efectuado.',
                }), 409

        # 6. Tudo validado: guardar as imagens em disco
        nome_ficheiro_bi = guardar_bytes_imagem(bytes_bi, extensao_bi, BI_DIR, "bi")
        ficheiros_gravados.append(os.path.join(BI_DIR, nome_ficheiro_bi))
        nome_ficheiro_facial = guardar_bytes_imagem(bytes_facial, extensao_facial, FACIAL_DIR, "facial")
        ficheiros_gravados.append(os.path.join(FACIAL_DIR, nome_ficheiro_facial))

        # 7. Guardar na base de dados
        codigo = gerar_codigo_funcionario()
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
        ficheiros_gravados = []  # cadastro concluído: as fotos ficam
    except MySQLError as e:
        return jsonify({"sucesso": False, "erro": f"Erro ao gravar na base de dados: {e}"}), 500
    finally:
        # Se o cadastro não foi concluído, remove as fotos que chegaram a ser gravadas.
        for caminho in ficheiros_gravados:
            remover_ficheiro_silenciosamente(caminho)
        if conexao is not None:
            try:
                if trava_obtida:
                    cursor.execute("SELECT RELEASE_LOCK(%s) AS libertado", (NOME_TRAVA_CADASTRO,))
                    cursor.fetchone()
                cursor.close()
                conexao.close()
            except MySQLError:
                pass

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
@requer_login()
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
@requer_login()
def pesquisar_funcionario_por_face():
    """Recebe uma foto (dataURL) captada ao vivo, extrai as suas
    características faciais e pesquisa, na base de dados, qual o
    funcionário já cadastrado cujo rosto mais se aproxima.
    (Só identifica; para REGISTAR a presença usa-se /api/presencas/marcar.)"""
    dados = request.get_json(silent=True) or {}
    foto = dados.get("foto")

    if not foto:
        return jsonify({"sucesso": False, "erro": "Falta a foto facial para a pesquisa."}), 400

    try:
        imagem = carregar_imagem_de_data_url(foto)
    except ValueError as e:
        return jsonify({"sucesso": False, "erro": str(e)}), 400

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


@app.route("/api/presencas/marcar", methods=["POST"])
@requer_login()
def marcar_presenca():
    """Recebe uma foto (dataURL) captada ao vivo, identifica o funcionário pelo
    rosto e regista a presença:
      - 1.ª marcação do dia  -> ENTRADA
      - 2.ª marcação do dia  -> SAÍDA (depois de MIN_MINUTOS_ENTRE_MARCACOES)
      - a partir daí         -> avisa que a presença de hoje já está completa.
    O frontend envia só a foto: quem é o funcionário é sempre decidido aqui,
    pelo rosto, para ninguém poder marcar presença em nome de outra pessoa."""
    dados = request.get_json(silent=True) or {}
    foto = dados.get("foto")

    if not foto:
        return jsonify({"sucesso": False, "erro": "Falta a foto facial para marcar a presença."}), 400

    try:
        imagem = carregar_imagem_de_data_url(foto)
    except ValueError as e:
        return jsonify({"sucesso": False, "erro": str(e)}), 400

    vector, erro = extrair_caracteristicas_de_imagem(imagem)
    if erro:
        return jsonify({"sucesso": False, "erro": erro}), 422

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

        if not linhas:
            cursor.close()
            conexao.close()
            return jsonify({"sucesso": False, "erro": "Ainda não há funcionários registados. Faz primeiro o cadastro."}), 404

        vectores_conhecidos = [np.array(json.loads(linha["caracteristicas_faciais"])) for linha in linhas]
        distancias = face_recognition.face_distance(vectores_conhecidos, np.array(vector))
        indice_melhor = int(np.argmin(distancias))
        melhor_distancia = float(distancias[indice_melhor])
        funcionario = linhas[indice_melhor]
        print(f"[presença] distância ao funcionário mais parecido = {melhor_distancia:.4f} (limiar {LIMIAR_PRESENCA})")

        if melhor_distancia > LIMIAR_PRESENCA:
            cursor.close()
            conexao.close()
            return jsonify({
                "sucesso": False,
                "encontrado": False,
                "erro": "Rosto não reconhecido. Nenhuma presença foi registada. Tenta novamente com boa iluminação e o rosto de frente para a câmara.",
            }), 404

        agora = agora_local()
        hoje = agora.date()

        cursor.execute(
            "SELECT tipo, data_hora FROM presencas WHERE funcionario_id = %s AND data_dia = %s ORDER BY data_hora",
            (funcionario["id"], hoje),
        )
        registos_de_hoje = {linha["tipo"]: linha["data_hora"] for linha in cursor.fetchall()}

        dados_funcionario = {
            "id": funcionario["id"],
            "codigo": funcionario["codigo"],
            "nome": funcionario["nome"],
            "departamento": funcionario["departamento"],
            "fotoFacialUrl": f"/uploads/{funcionario['foto_facial_path']}",
        }

        # Decide se esta marcação é entrada ou saída (ou se não há nada a registar)
        if "entrada" not in registos_de_hoje:
            tipo = "entrada"
        elif "saida" not in registos_de_hoje:
            minutos_decorridos = (agora - registos_de_hoje["entrada"]).total_seconds() / 60
            if minutos_decorridos < MIN_MINUTOS_ENTRE_MARCACOES:
                faltam = max(1, math.ceil(MIN_MINUTOS_ENTRE_MARCACOES - minutos_decorridos))
                cursor.close()
                conexao.close()
                return jsonify({
                    "sucesso": True,
                    "registado": False,
                    "motivo": "entrada_recente",
                    "mensagem": f"{funcionario['nome']}: a entrada já foi registada às {formatar_hora(registos_de_hoje['entrada'])}. Para marcar a saída, aguarda cerca de {faltam} minuto(s).",
                    "funcionario": dados_funcionario,
                })
            tipo = "saida"
        else:
            cursor.close()
            conexao.close()
            return jsonify({
                "sucesso": True,
                "registado": False,
                "motivo": "dia_completo",
                "mensagem": f"{funcionario['nome']}: a presença de hoje já está completa (entrada às {formatar_hora(registos_de_hoje['entrada'])} e saída às {formatar_hora(registos_de_hoje['saida'])}).",
                "funcionario": dados_funcionario,
            })

        try:
            cursor.execute(
                "INSERT INTO presencas (funcionario_id, tipo, data_hora, data_dia, distancia) VALUES (%s, %s, %s, %s, %s)",
                (funcionario["id"], tipo, agora, hoje, round(melhor_distancia, 4)),
            )
            conexao.commit()
        except MySQLError as e:
            cursor.close()
            conexao.close()
            if getattr(e, "errno", None) == 1062:
                # Chave única: outra marcação igual acabou de ser registada (ex: duplo clique)
                return jsonify({"sucesso": False, "erro": "Esta marcação acabou de ser registada. Actualiza o histórico para a ver."}), 409
            return jsonify({"sucesso": False, "erro": f"Erro ao gravar na base de dados: {e}"}), 500

        cursor.close()
        conexao.close()
    except MySQLError as e:
        return jsonify({"sucesso": False, "erro": f"Erro ao consultar a base de dados: {e}"}), 500

    rotulo = "Entrada" if tipo == "entrada" else "Saída"
    return jsonify({
        "sucesso": True,
        "registado": True,
        "tipo": tipo,
        "hora": formatar_hora(agora),
        "dataHora": agora.strftime("%d/%m/%Y %H:%M"),
        "distancia": round(melhor_distancia, 4),
        "mensagem": f"{rotulo} registada às {formatar_hora(agora)}: {funcionario['nome']}.",
        "funcionario": dados_funcionario,
    }), 201


@app.route("/api/presencas", methods=["GET"])
@requer_login()
def listar_presencas():
    """Histórico de presenças, agrupado por funcionário e por dia.
    Parâmetros opcionais (AAAA-MM-DD): de, ate. Por omissão, só o dia de hoje."""
    hoje = agora_local().date()
    try:
        de = datetime.strptime(request.args["de"], "%Y-%m-%d").date() if request.args.get("de") else hoje
        ate = datetime.strptime(request.args["ate"], "%Y-%m-%d").date() if request.args.get("ate") else de
    except ValueError:
        return jsonify({"sucesso": False, "erro": "Datas inválidas. Usa o formato AAAA-MM-DD."}), 400

    if ate < de:
        return jsonify({"sucesso": False, "erro": "A data final não pode ser anterior à data inicial."}), 400
    if (ate - de).days > MAX_DIAS_HISTORICO:
        return jsonify({"sucesso": False, "erro": f"O intervalo máximo é de {MAX_DIAS_HISTORICO} dias."}), 400

    try:
        conexao = get_db_connection()
        cursor = conexao.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT p.data_dia, p.tipo, p.data_hora,
                   f.id AS funcionario_id, f.codigo, f.nome, f.departamento
            FROM presencas p
            JOIN funcionarios f ON f.id = p.funcionario_id
            WHERE p.data_dia BETWEEN %s AND %s
            ORDER BY p.data_dia DESC, f.nome, p.data_hora
            """,
            (de, ate),
        )
        linhas = cursor.fetchall()
        cursor.close()
        conexao.close()
    except MySQLError as e:
        return jsonify({"sucesso": False, "erro": f"Erro ao consultar a base de dados: {e}"}), 500

    # Junta a entrada e a saída de cada funcionário em cada dia numa só linha
    agrupado = {}
    for linha in linhas:
        chave = (linha["data_dia"], linha["funcionario_id"])
        if chave not in agrupado:
            agrupado[chave] = {
                "data": linha["data_dia"],
                "funcionarioId": linha["funcionario_id"],
                "codigo": linha["codigo"],
                "nome": linha["nome"],
                "departamento": linha["departamento"],
                "entrada": None,
                "saida": None,
            }
        agrupado[chave][linha["tipo"]] = linha["data_hora"]

    presencas = []
    for item in agrupado.values():
        horas_trabalhadas = None
        if item["entrada"] and item["saida"]:
            minutos = int((item["saida"] - item["entrada"]).total_seconds() // 60)
            horas_trabalhadas = f"{minutos // 60}h{minutos % 60:02d}"
        presencas.append({
            "data": item["data"].strftime("%d/%m/%Y"),
            "funcionarioId": item["funcionarioId"],
            "codigo": item["codigo"],
            "nome": item["nome"],
            "departamento": item["departamento"],
            "entrada": formatar_hora(item["entrada"]) if item["entrada"] else None,
            "saida": formatar_hora(item["saida"]) if item["saida"] else None,
            "horasTrabalhadas": horas_trabalhadas,
        })

    return jsonify({
        "sucesso": True,
        "de": de.isoformat(),
        "ate": ate.isoformat(),
        "presencas": presencas,
    })


@app.route("/uploads/<path:subcaminho>", methods=["GET"])
@requer_login()
def servir_imagem(subcaminho):
    return send_from_directory(UPLOADS_DIR, subcaminho)


if __name__ == "__main__":
    # Por segurança, o modo debug fica DESLIGADO por omissão (o modo debug do
    # Flask permite executar código no servidor a quem lhe aceda). Para o
    # ligar só no teu computador, define FLASK_DEBUG=true no .env.
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    print(f"Servidor Stemmoz a correr em http://localhost:5000 (MySQL em {DB_CONFIG['host']}:{DB_CONFIG['port']})")
    app.run(host="0.0.0.0", port=5000, debug=debug_mode, use_reloader=False)