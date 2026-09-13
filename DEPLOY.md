# Deploy no Ubuntu Server (Docker Compose)

Este guia cobre a instalação completa do sistema Stemmoz (frontend React +
backend Flask/reconhecimento facial + MySQL) num Ubuntu Server, usando
Docker Compose. Os três serviços correm em containers:

| Serviço    | Container         | Porta exposta |
|------------|--------------------|---------------|
| `mysql`    | `stemmoz_mysql`    | 3306          |
| `backend`  | `stemmoz_backend`  | 5000          |
| `frontend` | `stemmoz_frontend` | 80            |

As tabelas da base de dados são criadas **automaticamente** pelo backend
assim que este arranca — não é preciso correr `schema.sql` manualmente.

---

## 1. Pré-requisitos no servidor

Liga-te ao servidor por SSH e instala o Docker Engine + plugin do Compose:

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg

sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# permite correr "docker" sem sudo (é preciso voltar a entrar na sessão SSH depois disto)
sudo usermod -aG docker $USER
```

Confirma a instalação:

```bash
docker --version
docker compose version
```

---

## 2. Copiar o projecto para o servidor

A partir da tua máquina (onde tens o código), envia a pasta do projecto
para o servidor (ajusta utilizador/IP):

```bash
rsync -avz --exclude node_modules --exclude venv --exclude .git \
  ./Projecto-steamMoz/ utilizador@IP_DO_SERVIDOR:~/stemmoz/
```

Ou, se o projecto estiver num repositório Git, clona-o directamente no
servidor:

```bash
git clone <url-do-repositorio> ~/stemmoz
```

---

## 3. Configurar as variáveis de ambiente

No servidor, dentro da pasta do projecto:

```bash
cd ~/stemmoz
cp .env.example .env
nano .env
```

Ajusta:

```
MYSQL_ROOT_PASSWORD=<escolhe uma password forte>
DB_NAME=stemmoz_rh
VITE_API_URL=http://IP_OU_DOMINIO_DO_SERVIDOR:5000
```

> `VITE_API_URL` é o endereço pelo qual o **navegador** (não o container) vai
> contactar o backend — usa o IP público/domínio do servidor, não `localhost`
> nem o nome interno do serviço Docker.

---

## 4. Construir e arrancar os containers

```bash
docker compose build
docker compose up -d
```

A primeira build do backend demora alguns minutos (instala o `dlib` via
conda-forge). Acompanha o arranque:

```bash
docker compose ps
docker compose logs -f backend
```

Deves ver uma linha como:

```
Base de dados 'stemmoz_rh' e tabela 'funcionarios' prontas em mysql:3306.
```

---

## 5. Abrir as portas na firewall

```bash
sudo ufw allow 80/tcp     # frontend
sudo ufw allow 5000/tcp   # backend (API)
sudo ufw enable
```

> A porta 3306 (MySQL) só precisa de ficar acessível **de fora** do servidor
> se quiseres ligar-te à base de dados remotamente (ex: com o MySQL
> Workbench). Se não precisares disso, não a abras na firewall — o backend
> já lhe acede internamente através da rede do Docker Compose, mesmo sem
> essa porta estar aberta ao exterior.

---

## 6. Aceder à aplicação

Abre no navegador:

```
http://IP_OU_DOMINIO_DO_SERVIDOR
```

A câmara só funciona em contexto seguro (HTTPS) ou em `localhost` — se
acederes por HTTP a partir de outro computador, a maior parte dos
navegadores vai bloquear o acesso à câmara. Para uso em produção fora da
rede local, configura HTTPS (ver secção 8).

---

## 7. Operações do dia-a-dia

```bash
# ver logs de um serviço
docker compose logs -f backend
docker compose logs -f frontend

# reiniciar um serviço
docker compose restart backend

# actualizar depois de alterares código
docker compose build backend
docker compose up -d backend

# parar tudo (mantém os dados)
docker compose down

# parar tudo e apagar também os dados (MySQL e uploads) — cuidado!
docker compose down -v
```

Os dados persistem em dois volumes Docker nomeados:
- `mysql_data` — base de dados MySQL
- `uploads_data` — fotos do BI e fotos faciais gravadas pelo backend

Backup da base de dados:

```bash
docker compose exec mysql sh -c 'mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" stemmoz_rh' > backup_stemmoz_rh.sql
```

---

## 8. HTTPS (recomendado para acesso fora da rede local)

Como a câmara exige contexto seguro, para acesso a partir de outra rede o
mais simples é colocar um domínio a apontar para o servidor e usar o Caddy
ou Nginx + Certbot à frente do container `frontend` (porta 80) para emitir
um certificado TLS automático. Depois disso, actualiza `VITE_API_URL` no
`.env` para `https://...` e faz `docker compose build frontend && docker
compose up -d frontend` novamente.

---

## 9. Notas de segurança

- Troca sempre `MYSQL_ROOT_PASSWORD` no `.env` — nunca uses o valor de
  exemplo em produção.
- O `.env` **não** deve ser commitado no Git (já está no `.gitignore`).
- `FLASK_DEBUG` está definido como `false` no `docker-compose.yml` — mantém
  assim em produção (o modo debug do Flask expõe um interpretador de
  código no navegador em caso de erro).
