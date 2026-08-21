# Sistema de Cadastro de Funcionários com Reconhecimento Facial — Stemmoz

Este projecto implementa a parte de **cadastro (registo)** de funcionários,
com captura da foto facial frontal e extracção automática das
características faciais (vector de 128 dimensões), de acordo com a
arquitectura cliente-servidor descrita na monografia:

- **Cliente** → `cadastro.html` (corre no navegador, acede à câmara)
- **Servidor** → `app.py` (Python/Flask — processa o reconhecimento facial e fala com a base de dados)
- **Base de dados** → MySQL, gerido pelo XAMPP/phpMyAdmin

Este projecto cobre **apenas o cadastro**. A verificação diária de presença
(comparar um rosto novo com os já registados) é a fase seguinte, a construir
depois de o cadastro estar validado.

---

## 1. Pré-requisitos

- **XAMPP** instalado, com o **Apache** e o **MySQL** ligados (no painel de controlo do XAMPP).
- **Python 3.10 ou 3.11** instalado (evita a versão 3.12+, por compatibilidade com o `dlib`).
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

## 2. Configurar a base de dados

1. Abre o **XAMPP Control Panel** e liga o **Apache** e o **MySQL**.
2. Abre o navegador em `http://localhost/phpmyadmin`.
3. Clica no separador **SQL**.
4. Copia todo o conteúdo do ficheiro `schema.sql` (deste projecto) e cola na caixa.
5. Clica em **Executar**.

Isto cria a base de dados `stemmoz_rh` e a tabela `funcionarios`.

> Se o teu MySQL tiver uma password definida para o utilizador `root`
> (por defeito no XAMPP não tem), abre o `app.py` e ajusta o valor
> `"password": ""` em `DB_CONFIG`.

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
Servidor Stemmoz a correr em http://localhost:5000
```

Deixa este terminal aberto — o servidor tem de ficar a correr enquanto usas o sistema.

---

## 4. Abrir o formulário de cadastro

Com o servidor Flask a correr, abre o ficheiro `cadastro.html` directamente
no navegador (duplo clique, ou clique direito → "Abrir com" → o teu navegador).

O formulário vai:
1. Pedir o nome e o departamento do funcionário;
2. Pedir a foto do documento de identificação (BI);
3. Activar a câmara e captar **apenas uma foto facial frontal**;
4. Mostrar um resumo para confirmação;
5. Ao clicares em "Finalizar Cadastro", enviar os dados ao servidor Flask, que:
   - detecta o rosto na foto e extrai as suas características (128 números);
   - se não conseguir detectar nenhum rosto, devolve uma mensagem de erro
     (pede para repetir a captura, com melhor iluminação);
   - se tudo correr bem, guarda o registo na base de dados MySQL.

A tabela "Funcionários Registados", no fundo da página, é carregada
directamente a partir da base de dados.

---

## 5. Estrutura de ficheiros

```
stemmoz-cadastro/
├── app.py              → backend Flask (API + reconhecimento facial)
├── requirements.txt    → dependências Python
├── schema.sql          → script de criação da base de dados MySQL
├── cadastro.html       → formulário (cliente), a correr no navegador
├── README.md           → este ficheiro
└── uploads/
    ├── bi/              → fotos dos documentos de identificação, guardadas aqui
    └── facial/          → fotos faciais frontais, guardadas aqui
```

---

## 6. Sobre as características faciais

O sistema **não guarda a fotografia para depois comparar imagem contra
imagem**. Ao receber a foto facial, o backend usa o algoritmo do Dlib
(através da biblioteca `face_recognition`, já fundamentada no documento de
ferramentas da monografia) para extrair um vector de **128 características
numéricas**, exclusivo de cada rosto. É esse vector — guardado na coluna
`caracteristicas_faciais` da tabela `funcionarios`, em formato JSON — que
será usado, na fase seguinte do projecto, para comparar e reconhecer os
funcionários no momento da marcação de presença.
