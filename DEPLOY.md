# 📖 Guia Completo de Deploy - Sistema de Gestão Integrado

> Documentação profissional para deployment em todos ambientes

---

## 📑 Índice

1. [Pré-requisitos](#1️⃣-pré-requisitos)
2. [Execução Local](#2️⃣-execução-local)
3. [Docker (Recomendado)](#3️⃣-execução-com-docker)
4. [Deploy em Nuvem](#4️⃣-deploy-em-nuvem)
5. [Termux (Android)](#5️⃣-execução-em-termux-android)
6. [Troubleshooting](#6️⃣-troubleshooting)

---

## 1️⃣ Pré-requisitos

### Obter Credenciais Telegram

#### Token do Bot
1. Abra Telegram
2. Procure por `@BotFather`
3. Envie `/newbot`
4. Siga as instruções
5. Copie o token (formato: `123456:ABC-DEF1234ghIkl...`)

#### Seu ID de Usuário
1. Procure por `@userinfobot`
2. Envie `/start`
3. Copie seu ID (número inteiro)

### Requisitos de Sistema

**Mínimo:**
- Python 3.9+
- 256MB RAM
- 100MB Disco
- Conexão Internet

**Recomendado:**
- Python 3.11+
- 512MB RAM
- 500MB Disco
- Conexão rápida

---

## 2️⃣ Execução Local

### 🐧 Linux / macOS

```bash
# 1. Clonar repositório
git clone https://github.com/duzzx22/Telegram_bot_administra-o-.git
cd Telegram_bot_administra-o-
git checkout development/core-system

# 2. Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate  # Linux/macOS

# 3. Configurar credenciais
cp .env.example .env
nano .env  # Editar com suas credenciais

# 4. Instalar dependências
pip install --upgrade pip
pip install -r requirements.txt

# 5. Executar
python main.py
```

### 🪟 Windows (CMD)

```cmd
REM 1. Clonar repositório
git clone https://github.com/duzzx22/Telegram_bot_administra-o-.git
cd Telegram_bot_administra-o-
git checkout development/core-system

REM 2. Criar ambiente virtual
python -m venv venv
venv\Scripts\activate

REM 3. Configurar credenciais
copy .env.example .env
REM Editar .env com Notepad++

REM 4. Instalar dependências
pip install --upgrade pip
pip install -r requirements.txt

REM 5. Executar
python main.py
```

### 🪟 Windows (PowerShell)

```powershell
# 1. Clonar repositório
git clone https://github.com/duzzx22/Telegram_bot_administra-o-.git
cd Telegram_bot_administra-o-
git checkout development/core-system

# 2. Criar ambiente virtual
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Configurar credenciais
Copy-Item .env.example .env
# Editar .env

# 4. Instalar dependências
pip install --upgrade pip
pip install -r requirements.txt

# 5. Executar
python main.py
```

---

## 3️⃣ Execução com Docker

### ✅ Quick Start (Recomendado)

```bash
# 1. Clonar repositório
git clone https://github.com/duzzx22/Telegram_bot_administra-o-.git
cd Telegram_bot_administra-o-

# 2. Configurar ambiente
cp .env.example .env
# Editar .env

# 3. Iniciar com Docker Compose
docker-compose up -d

# 4. Ver logs
docker-compose logs -f

# 5. Parar
docker-compose down
```

### Docker Manual

```bash
# Build da imagem
docker build -t sistema-gestao-telegram:1.0 .

# Executar container
docker run -d \
  --name bot-telegram \
  --restart unless-stopped \
  -e TELEGRAM_BOT_TOKEN=seu_token \
  -e ADMIN_IDS=seu_id \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  sistema-gestao-telegram:1.0

# Ver logs
docker logs -f bot-telegram

# Parar
docker stop bot-telegram
docker rm bot-telegram
```

---

## 4️⃣ Deploy em Nuvem

### ☁️ Azure Container Instances

```bash
# 1. Login
az login

# 2. Criar resource group
az group create --name myResourceGroup --location eastus

# 3. Criar container
az container create \
  --resource-group myResourceGroup \
  --name telegram-bot \
  --image sistema-gestao-telegram:1.0 \
  --environment-variables \
    TELEGRAM_BOT_TOKEN=seu_token \
    ADMIN_IDS=seu_id \
  --restart-policy Always

# 4. Ver status
az container show --resource-group myResourceGroup --name telegram-bot
```

### 🟨 AWS (Lambda + ECR)

```bash
# 1. Build e push para ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin 123456.dkr.ecr.us-east-1.amazonaws.com

docker build -t telegram-bot:1.0 .
docker tag telegram-bot:1.0 123456.dkr.ecr.us-east-1.amazonaws.com/telegram-bot:latest
docker push 123456.dkr.ecr.us-east-1.amazonaws.com/telegram-bot:latest

# 2. Deploy Lambda (via AWS Console)
# - Criar função Lambda
# - Usar imagem ECR
# - Configurar variáveis de ambiente
```

### 🌐 DigitalOcean

```bash
# 1. Criar App via GitHub
# - Conectar repositório GitHub
# - Selecionar branch 'development/core-system'
# - Configurar ambiente: .env

# 2. Via CLI
doctl apps create --spec app.yaml
```

### 🔴 Heroku

```bash
# 1. Login
heroku login

# 2. Criar app
heroku create meu-telegram-bot

# 3. Configurar variáveis
heroku config:set TELEGRAM_BOT_TOKEN=seu_token
heroku config:set ADMIN_IDS=seu_id

# 4. Deploy
git push heroku development/core-system:main

# 5. Ver logs
heroku logs --tail
```

### 🚀 Render

```bash
# 1. Criar em https://render.com
# - New > Web Service
# - Conectar GitHub
# - Build Command: pip install -r requirements.txt
# - Start Command: python main.py
# - Adicionar variáveis de ambiente
```

---

## 5️⃣ Execução em Termux (Android)

### Setup Termux

```bash
# 1. Instalar Termux (Play Store)
# - App: "Termux"

# 2. Atualizar pacotes
apt update && apt upgrade -y

# 3. Instalar Python
apt install -y python3 python3-pip git

# 4. Clonar repositório
git clone https://github.com/duzzx22/Telegram_bot_administra-o-.git
cd Telegram_bot_administra-o-

# 5. Configurar
cp .env.example .env
# Editar com nano ou vim

# 6. Instalar dependências
pip install -r requirements.txt

# 7. Executar
python main.py
```

### Executar em Background

```bash
# Instalar tmux
apt install tmux

# Criar sessão
tmux new-session -d -s bot "python /path/to/main.py"

# Ver logs
tmux attach-session -t bot

# Desanexar: Ctrl+B, D

# Listar sessões
tmux list-sessions

# Matar sessão
tmux kill-session -t bot
```

---

## 6️⃣ Troubleshooting

### ❌ Erro: "Token inválido"

**Causa:** Token incorreto ou com espaços

**Solução:**
```bash
# Verificar .env
cat .env

# Sem espaços extras!
# CORRETO: TELEGRAM_BOT_TOKEN=123456:ABC
# ERRADO: TELEGRAM_BOT_TOKEN = 123456:ABC
```

### ❌ Erro: "Bot não é administrador"

**Causa:** Bot sem permissões no grupo

**Solução:**
1. Adicione o bot ao grupo
2. Abra Configurações do Grupo
3. Membros > Seu Bot
4. Promova a Administrador
5. Ative: Banir usuários, Deletar msgs, Restringir

### ❌ Erro: "Banco de dados bloqueado"

**Causa:** Múltiplas instâncias acessando DB

**Solução:**
```bash
# Parar todas as instâncias
# Deletar banco
rm -f data/management.db
# Iniciar novamente
python main.py
```

### ❌ Erro: "ModuleNotFoundError"

**Causa:** Dependências não instaladas

**Solução:**
```bash
# Verificar ambiente virtual
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Reinstalar
pip install --force-reinstall -r requirements.txt
```

### ❌ Erro: "Port already in use" (Docker)

**Causa:** Porta já em uso

**Solução:**
```bash
# Parar container existente
docker-compose down

# OU mudar porta em docker-compose.yml
```

### ✅ Health Check

```bash
# Verificar se bot está respondendo
curl -X GET https://api.telegram.org/bot<TOKEN>/getMe

# Se retornar JSON com ok:true, tudo funciona!
```

---

## 📊 Monitoramento

### Ver Logs

**Local:**
```bash
tail -f logs/sistema_*.log
```

**Docker:**
```bash
docker-compose logs -f
```

### Métricas

```bash
# Memória
free -h

# CPU
top -b -n1 | head -n 5

# Disco
du -sh data/
```

---

## 🔐 Segurança

✅ **Boas Práticas:**
- Nunca compartilhe `.env`
- Use variáveis de ambiente em nuvem
- Ative 2FA em @BotFather
- Revise logs regularmente
- Faça backup do banco periodicamente
- Use HTTPS em APIs
- Mantenha dependências atualizadas

---

## 🆘 Suporte

Se tiver dúvidas:
1. 📖 Revise [README.md](README.md)
2. 🐛 Abra [Issue no GitHub](https://github.com/duzzx22/Telegram_bot_administra-o-/issues)
3. 💬 Acesse [Discussions](https://github.com/duzzx22/Telegram_bot_administra-o-/discussions)

---

**Status:** ✅ Deploy Guide Completo | 🚀 Pronto para Produção
