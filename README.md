# Sistema de Cadastro e Reconhecimento Facial de Funcionários — Stemmoz

Este projecto implementa o **cadastro (registo)** e a **pesquisa/reconhecimento**
de funcionários por rosto, de acordo com a arquitectura cliente-servidor
descrita na monografia:

- **Cliente** → `frontend/` (aplicação **React**, corre no navegador, acede à câmara)
- **Servidor** → `app.py` (Python/Flask — processa o reconhecimento facial e fala com a base de dados)
- **Base de dados** → MySQL (as tabelas são **criadas automaticamente** pelo próprio backend ao arrancar)

> O antigo formulário estático `cadastro.html` foi substituído pela aplicação
> React em `frontend/`, que é mais interactiva (validação em tempo real,
> pesquisa/filtros na tabela, indicador de estado do servidor) e já inclui o
> ecrã de **Reconhecimento Facial** (pesquisa de um rosto captado ao vivo
> contra os funcionários já cadastrados).

---

## 1. Pré-requisitos

- **Node.js 18+** e **npm**, para correr o frontend React.
- **Python 3.10 ou 3.11** instalado (evita a versão 3.12+, por compatibilidade com o `dlib`).
- Acesso a um **servidor MySQL** (local ou remoto) na porta **3306**.
- **Visual Studio Code** (ou outro editor à tua escolha).

> ⚠️ **Nota importante sobre o `dlib`:** a biblioteca `face_recognition` depende do `dlib`,
> que precisa de ser compilado. No Windows, isto normalmente exige o **CMake** e as
> **Build Tools for Visual Studio (C++)**. Se o passo 3 (`pip install`) falhar com erros
> relacionados com o `dlib` ou `CMake`, a forma mais simples de resolver é instalar o
> [Anaconda](https://www.anaconda.com/) e correr:
> ```
> conda install -c conda-forge dlib
> ```
> antes de repetires o `pip install -r requirements.txt`.

---

## 2. Base de dados (criação automática)

Já **não é preciso** correr manualmente o `schema.sql` no phpMyAdmin: ao
arrancar, o `app.py` liga-se ao servidor MySQL configurado em `DB_CONFIG`
(dentro do próprio ficheiro), cria a base de dados `stemmoz_rh` (caso não
exista) e cria a tabela `funcionarios` (caso não exista).

```python
DB_CONFIG = {
    "host": "102.211.186.44",  # host do servidor MySQL
    "port": 3306,               # porta por omissão do MySQL
    "user": "root",
    "password": "...",
    "database": "stemmoz_rh",
}
```

Ajusta `host`, `port`, `user` e `password` conforme o teu servidor MySQL.
O ficheiro `schema.sql` fica apenas como referência do esquema criado.

---

## 3. Instalar e correr o backend (Flask)

No terminal, dentro da pasta deste projecto:

```bash
# 1. Criar e activar um ambiente virtual (recomendado)
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux/Mac

# 2. Instalar as dependências
pip install -r requirements.txt

# 3. Correr o servidor
python app.py
```

Se tudo correr bem, deverás ver:
```
Base de dados 'stemmoz_rh' e tabela 'funcionarios' prontas em <host>:3306.
Servidor Stemmoz a correr em http://localhost:5000 (MySQL em <host>:3306)
```

Deixa este terminal aberto — o servidor tem de ficar a correr enquanto usas o sistema.

---

## 4. Instalar e correr o frontend (React)

Num segundo terminal:

```bash
cd frontend
npm install
npm run dev
```

Abre o endereço apresentado (normalmente `http://localhost:5173`) no navegador.

Por omissão, o frontend fala com o backend em `http://localhost:5000`. Se o
backend estiver noutra máquina/porta, cria um ficheiro `frontend/.env`
(a partir de `frontend/.env.example`) com:

```
VITE_API_URL=http://<host-do-backend>:5000
```

Para gerar uma versão de produção do frontend: `npm run build` (gera a pasta `frontend/dist`, que pode ser servida por qualquer servidor estático).

---

## 5. Usar a aplicação

A aplicação React tem três separadores:

1. **Cadastro** — assistente em 4 passos: dados do funcionário → foto do
   documento (BI) → captura facial ao vivo → confirmação. Ao finalizar, o
   backend detecta o rosto, extrai as suas características (128 números) e
   grava o registo na base de dados.
2. **Reconhecimento Facial** — activa a câmara, captura um rosto e pesquisa,
   em tempo real, qual o funcionário já cadastrado (se algum) cujo rosto mais
   se aproxima, devolvendo o nome, departamento, código e a distância da
   comparação.
3. **Funcionários** — lista de todos os funcionários registados, com
   pesquisa por nome/código, filtro por departamento e ordenação por coluna.

---

## 6. Estrutura de ficheiros

```
stemmoz-cadastro/
├── app.py              → backend Flask (API + reconhecimento/pesquisa facial + criação automática da BD)
├── requirements.txt    → dependências Python
├── schema.sql          → esquema de referência da base de dados MySQL (criado automaticamente pelo app.py)
├── frontend/            → aplicação React (cliente)
│   ├── src/
│   │   ├── components/
│   │   │   ├── cadastro/        → assistente de cadastro em 4 passos
│   │   │   ├── reconhecimento/  → pesquisa de funcionário por rosto
│   │   │   ├── funcionarios/    → lista com pesquisa/filtros/ordenação
│   │   │   └── common/          → componentes partilhados (status, spinner)
│   │   ├── hooks/useCamera.js   → acesso à câmara, partilhado entre ecrãs
│   │   ├── api.js               → chamadas ao backend Flask
│   │   └── App.jsx              → navegação por separadores
│   └── package.json
├── cadastro.html        → formulário original (mantido como referência histórica)
├── README.md            → este ficheiro
└── uploads/
    ├── bi/              → fotos dos documentos de identificação, guardadas aqui
    └── facial/          → fotos faciais frontais, guardadas aqui
```

---

## 7. Sobre as características faciais

O sistema **não guarda a fotografia para depois comparar imagem contra
imagem**. Ao receber a foto facial, o backend usa o algoritmo do Dlib
(através da biblioteca `face_recognition`, já fundamentada no documento de
ferramentas da monografia) para extrair um vector de **128 características
numéricas**, exclusivo de cada rosto. É esse vector — guardado na coluna
`caracteristicas_faciais` da tabela `funcionarios`, em formato JSON — que é
usado no ecrã de **Reconhecimento Facial** para comparar (via
`face_recognition.face_distance`) um rosto captado ao vivo com todos os
rostos já cadastrados, e identificar a melhor correspondência.
