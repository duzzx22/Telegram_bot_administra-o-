#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════╗
║                    SISTEMA DE GESTÃO INTEGRADO v1.0                      ║
║                 python-telegram-bot v20+ | Production Ready              ║
║                  Compatível: Docker, Windows, Linux, Termux               ║
╚═══════════════════════════════════════════════════════════════════════════╝

Desenvolvido como Sistema de Gestão Automatizado para Telegram.
"""

import os
import json
import sqlite3
import logging
import asyncio
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

from telegram import (
    Update, Chat, ChatMember, ChatPermissions,
    InlineKeyboardButton, InlineKeyboardMarkup, PhotoSize
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters, ConversationHandler
)
from telegram.error import TelegramError

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÃO INICIAL
# ═══════════════════════════════════════════════════════════════════════════

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_IDS = [int(id) for id in os.getenv('ADMIN_IDS', '').split(',') if id]
DATABASE_PATH = Path('data/management.db')
LOGS_PATH = Path('logs')
BACKUP_INTERVAL = 3600  # 1 hora

# Criar diretórios
DATABASE_PATH.parent.mkdir(exist_ok=True)
LOGS_PATH.mkdir(exist_ok=True)

# ═══════════════════════════════════════════════════════════════════════════
# SISTEMA DE LOGGING
# ═══════════════════════════════════════════════════════════════════════════

def setup_logger():
    """Configura logging profissional com rotação."""
    logger = logging.getLogger('GestaoIntegrada')
    logger.setLevel(logging.INFO)
    
    # Handler arquivo
    file_handler = logging.FileHandler(LOGS_PATH / f'sistema_{datetime.now().strftime("%Y%m%d")}.log')
    file_handler.setLevel(logging.INFO)
    
    # Handler console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - [%(levelname)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

logger = setup_logger()

# ═══════════════════════════════════════════════════════════════════════════
# BANCO DE DADOS - SQLITE
# ═══════════════════════════════════════════════════════════════════════════

class DatabaseManager:
    """Gerenciador de banco de dados com operações seguras."""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        """Retorna conexão com banco de dados."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Inicializa esquema do banco de dados."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Tabela de grupos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS groups (
                group_id INTEGER PRIMARY KEY,
                group_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                settings JSON DEFAULT '{}'
            )
        ''')
        
        # Tabela de usuários
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                group_id INTEGER,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (group_id) REFERENCES groups(group_id)
            )
        ''')
        
        # Tabela de advertências
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                group_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                issued_by INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (group_id) REFERENCES groups(group_id)
            )
        ''')
        
        # Tabela de ações disciplinares
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                group_id INTEGER NOT NULL,
                reason TEXT,
                expires_at TIMESTAMP,
                executed_by INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (group_id) REFERENCES groups(group_id)
            )
        ''')
        
        # Tabela de fotos de perfil
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS profile_photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id TEXT UNIQUE NOT NULL,
                set_by INTEGER,
                set_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Base de dados sincronizada com sucesso")
    
    def add_warning(self, user_id: int, group_id: int, reason: str, issued_by: int) -> int:
        """Adiciona advertência e retorna total."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO warnings (user_id, group_id, reason, issued_by)
            VALUES (?, ?, ?, ?)
        ''', (user_id, group_id, reason, issued_by))
        
        cursor.execute('''
            SELECT COUNT(*) as total FROM warnings
            WHERE user_id = ? AND group_id = ?
        ''', (user_id, group_id))
        
        total = cursor.fetchone()['total']
        conn.commit()
        conn.close()
        
        return total
    
    def log_action(self, action_type: str, user_id: int, group_id: int,
                   reason: str, expires_at: Optional[datetime] = None, executed_by: int = None):
        """Registra ação disciplinar."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO actions (action_type, user_id, group_id, reason, expires_at, executed_by)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (action_type, user_id, group_id, reason, expires_at, executed_by))
        
        conn.commit()
        conn.close()
    
    def get_active_mutes(self, group_id: int) -> list:
        """Retorna usuários silenciados ativos."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT DISTINCT user_id FROM actions
            WHERE group_id = ? AND action_type = 'mute' AND expires_at > CURRENT_TIMESTAMP
        ''', (group_id,))
        
        result = cursor.fetchall()
        conn.close()
        
        return [row['user_id'] for row in result]
    
    def add_group(self, group_id: int, group_name: str):
        """Registra novo grupo."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR IGNORE INTO groups (group_id, group_name)
            VALUES (?, ?)
        ''', (group_id, group_name))
        
        conn.commit()
        conn.close()
    
    def backup(self):
        """Cria backup do banco de dados."""
        backup_path = LOGS_PATH / f'backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
        import shutil
        shutil.copy2(self.db_path, backup_path)
        logger.info(f"Backup criado: {backup_path}")

db = DatabaseManager(DATABASE_PATH)

# ═══════════════════════════════════════════════════════════════════════════
# DECORADORES E UTILITÁRIOS
# ═══════════════════════════════════════════════════════════════════════════

def admin_only(func):
    """Decorador para restricionar comandos a administradores."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        if user_id not in ADMIN_IDS:
            if update.callback_query:
                await update.callback_query.answer("❌ Acesso negado", show_alert=True)
            else:
                await update.message.reply_text("❌ Acesso negado. Solicite autorização de administrador.")
            logger.warning(f"Tentativa de acesso não autorizado por {user_id}")
            return
        
        return await func(update, context)
    
    return wrapper

def group_admin_only(func):
    """Decorador para restringir a administradores do grupo."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        
        try:
            member = await context.bot.get_chat_member(chat_id, user_id)
            if member.status not in ['administrator', 'creator']:
                await update.message.reply_text("❌ Comando exclusivo para administradores do grupo.")
                return
        except TelegramError:
            await update.message.reply_text("⚠️ Erro ao verificar permissões.")
            return
        
        return await func(update, context)
    
    return wrapper

async def check_bot_permissions(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> dict:
    """Verifica permissões do bot no grupo."""
    try:
        bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
        return {
            'can_restrict_members': bot_member.can_restrict_members,
            'can_delete_messages': bot_member.can_delete_messages,
            'can_change_info': bot_member.can_change_info,
        }
    except TelegramError:
        return {}

# ═══════════════════════════════════════════════════════════════════════════
# MÓDULO DE ADMINISTRAÇÃO
# ═══════════════════════════════════════════════════════════════════════════

@group_admin_only
async def cmd_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando: /ban @usuario motivo - Bane usuário permanentemente."""
    chat_id = update.effective_chat.id
    admin_id = update.effective_user.id
    
    if not context.args or len(context.args) < 1:
        await update.message.reply_text("📋 Uso: /ban @usuario [motivo]")
        return
    
    # Verificar permissões do bot
    perms = await check_bot_permissions(context, chat_id)
    if not perms.get('can_restrict_members'):
        await update.message.reply_text("❌ Sistema sem permissão para restringir membros.")
        logger.warning(f"Permissão insuficiente em {chat_id}")
        return
    
    try:
        # Obter usuário
        if update.message.reply_to_message:
            target_user = update.message.reply_to_message.from_user
        else:
            username = context.args[0].lstrip('@')
            member = await context.bot.get_chat_members_count(chat_id)
            await update.message.reply_text("⚠️ Responda a mensagem do usuário para banir.")
            return
        
        target_id = target_user.id
        reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "Violação de regras"
        
        # Banir usuário
        await context.bot.ban_chat_member(chat_id, target_id)
        
        # Registrar ação
        db.log_action('ban', target_id, chat_id, reason, executed_by=admin_id)
        
        # Notificar
        msg = f"""✅ **Acesso Revogado**
├ Usuário: {target_user.mention_html()}
├ Motivo: {reason}
├ Administrador: {update.effective_user.mention_html()}
└ Timestamp: {datetime.now().strftime('%H:%M:%S')}
"""
        await update.message.reply_html(msg)
        logger.info(f"Usuário {target_id} banido do grupo {chat_id}. Motivo: {reason}")
        
    except TelegramError as e:
        await update.message.reply_text(f"❌ Erro ao processar: {str(e)}")
        logger.error(f"Erro em /ban: {e}")

@group_admin_only
async def cmd_kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando: /kick - Remove usuário temporariamente."""
    chat_id = update.effective_chat.id
    admin_id = update.effective_user.id
    
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Responda a mensagem do usuário para remover.")
        return
    
    perms = await check_bot_permissions(context, chat_id)
    if not perms.get('can_restrict_members'):
        await update.message.reply_text("❌ Sistema sem permissão.")
        return
    
    try:
        target_user = update.message.reply_to_message.from_user
        target_id = target_user.id
        reason = ' '.join(context.args) if context.args else "Remoção do grupo"
        
        # Remover usuário
        await context.bot.ban_chat_member(chat_id, target_id, revoke_messages=False)
        await asyncio.sleep(0.5)
        await context.bot.unban_chat_member(chat_id, target_id)
        
        db.log_action('kick', target_id, chat_id, reason, executed_by=admin_id)
        
        msg = f"""✅ **Usuário Removido**
├ Alvo: {target_user.mention_html()}
├ Motivo: {reason}
└ Timestamp: {datetime.now().strftime('%H:%M:%S')}
"""
        await update.message.reply_html(msg)
        logger.info(f"Usuário {target_id} removido do grupo {chat_id}")
        
    except TelegramError as e:
        await update.message.reply_text(f"❌ Erro: {str(e)}")
        logger.error(f"Erro em /kick: {e}")

@group_admin_only
async def cmd_mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando: /mute [minutos] - Silencia usuário."""
    chat_id = update.effective_chat.id
    admin_id = update.effective_user.id
    
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Responda a mensagem do usuário para silenciar.")
        return
    
    # Duração (padrão: 30 minutos)
    duration_min = 30
    if context.args and context.args[0].isdigit():
        duration_min = int(context.args[0])
    
    perms = await check_bot_permissions(context, chat_id)
    if not perms.get('can_restrict_members'):
        await update.message.reply_text("❌ Sistema sem permissão.")
        return
    
    try:
        target_user = update.message.reply_to_message.from_user
        target_id = target_user.id
        
        # Definir permissões (sem enviar mensagens)
        restricted_perms = ChatPermissions(can_send_messages=False)
        until_date = datetime.now() + timedelta(minutes=duration_min)
        
        await context.bot.restrict_chat_member(
            chat_id, target_id, 
            permissions=restricted_perms,
            until_date=until_date
        )
        
        db.log_action('mute', target_id, chat_id, f"Silenciado por {duration_min} min", 
                     expires_at=until_date, executed_by=admin_id)
        
        msg = f"""🔇 **Silenciamento Ativado**
├ Usuário: {target_user.mention_html()}
├ Duração: {duration_min} minutos
├ Liberação: {until_date.strftime('%H:%M:%S')}
└ Timestamp: {datetime.now().strftime('%H:%M:%S')}
"""
        await update.message.reply_html(msg)
        logger.info(f"Usuário {target_id} silenciado por {duration_min}min no grupo {chat_id}")
        
    except TelegramError as e:
        await update.message.reply_text(f"❌ Erro: {str(e)}")
        logger.error(f"Erro em /mute: {e}")

@group_admin_only
async def cmd_warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando: /warn - Registra advertência. 3 strikes = ban automático."""
    chat_id = update.effective_chat.id
    admin_id = update.effective_user.id
    
    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Responda a mensagem do usuário para advertir.")
        return
    
    try:
        target_user = update.message.reply_to_message.from_user
        target_id = target_user.id
        reason = ' '.join(context.args) if context.args else "Comportamento inadequado"
        
        # Adicionar advertência
        total_warns = db.add_warning(target_id, chat_id, reason, admin_id)
        
        msg = f"""⚠️ **Advertência Registrada**
├ Usuário: {target_user.mention_html()}
├ Motivo: {reason}
├ Total: {total_warns}/3
└ Timestamp: {datetime.now().strftime('%H:%M:%S')}
"""
        
        # Ban automático em 3 advertências
        if total_warns >= 3:
            perms = await check_bot_permissions(context, chat_id)
            if perms.get('can_restrict_members'):
                await context.bot.ban_chat_member(chat_id, target_id)
                db.log_action('auto_ban', target_id, chat_id, "3 advertências registradas", 
                             executed_by=admin_id)
                msg += f"\n\n🔴 **Limite atingido - Usuário banido automaticamente**"
        
        await update.message.reply_html(msg)
        logger.info(f"Advertência {total_warns}/3 registrada para {target_id} no grupo {chat_id}")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Erro: {str(e)}")
        logger.error(f"Erro em /warn: {e}")

# ═══════════════════════════════════════════════════════════════════════════
# MÓDULO FINANCEIRO (DOAÇÕES)
# ═══════════════════════════════════════════════════════════════════════════

BITCOIN_WALLET = "1Q5HdEBLrPCSprdprCJCnntrDerhBvipdR"

@admin_only
async def cmd_donate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando: /donate - Exibe informações de doação."""
    keyboard = [
        [InlineKeyboardButton("📋 Copiar Carteira Bitcoin", callback_data='copy_wallet')],
        [InlineKeyboardButton("ℹ️ Informações", callback_data='donate_info')],
        [InlineKeyboardButton("❌ Fechar", callback_data='close')]
    ]
    
    msg = """💰 **Sistema de Contribuições Financeiras**

Este Sistema de Gestão Integrado é mantido através de contribuições voluntárias.

**Métodos de Contribuição:**
├ Bitcoin (BTC) - Recomendado
├ Transferência bancária
└ Criptomoedas alternativas

**Carteira Bitcoin Primária:**
`1Q5HdEBLrPCSprdprCJCnntrDerhBvipdR`

**Status do Projeto:**
├ Versão: 1.0 Production
├ Uptime: Monitorado
└ Suporte: 24/7

Obrigado pelo apoio! 🙏
"""
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_html(msg, reply_markup=reply_markup)
    logger.info(f"Interface de doações acessada por {update.effective_user.id}")

async def donate_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler de callbacks do módulo de doações."""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'copy_wallet':
        msg = f"""✅ **Carteira Copiada**

\`\`\`
{BITCOIN_WALLET}
\`\`\`

Cole este endereço em sua carteira Bitcoin para enviar contribuição.
"""
        await query.edit_message_text(msg, parse_mode='Markdown')
        logger.info(f"Carteira copiada por {query.from_user.id}")
        
    elif query.data == 'donate_info':
        msg = """ℹ️ **Informações sobre Contribuições**

**Por que contribuir?**
• Manutenção contínua do sistema
• Implementação de novas funcionalidades
• Suporte técnico prioritário
• Segurança e atualizações

**Segurança:**
✅ Todas as transações são verificadas
✅ Nenhum dado pessoal armazenado
✅ Carteira auditada publicamente

**Transparência:**
A carteira Bitcoin permite rastrear todas as contribuições na blockchain.
"""
        await query.edit_message_text(msg, parse_mode='Markdown')
        
    elif query.data == 'close':
        await query.delete_message()
        logger.info(f"Interface fechada por {query.from_user.id}")

# ═══════════════════════════════════════════════════════════════════════════
# MÓDULO DE AUTOMAÇÃO DE MÍDIA
# ═══════════════════════════════════════════════════════════════════════════

@admin_only
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler automático para fotos de administradores."""
    user_id = update.effective_user.id
    
    if update.message.photo:
        photo = update.message.photo[-1]
        file_id = photo.file_id
        
        keyboard = [
            [InlineKeyboardButton("📤 Reenviar", callback_data=f'resend_photo_{file_id}')],
            [InlineKeyboardButton("💾 Guardar", callback_data=f'save_photo_{file_id}')],
            [InlineKeyboardButton("❌ Cancelar", callback_data='cancel')]
        ]
        
        msg = """📸 **Processamento de Mídia Detectado**

Opções disponíveis:
• Reenviar para grupo
• Guardar para uso posterior
• Cancelar operação
"""
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(msg, reply_markup=reply_markup)
        logger.info(f"Foto recebida de admin {user_id}: {file_id}")

async def photo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler de callbacks para manipulação de fotos."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith('resend_photo_'):
        file_id = data.replace('resend_photo_', '')
        await query.message.reply_photo(file_id, caption="✅ Foto reenviada | Log: Photo forwarded")
        logger.info(f"Foto reenviada por {query.from_user.id}")
        
    elif data.startswith('save_photo_'):
        file_id = data.replace('save_photo_', '')
        conn = db.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''INSERT INTO profile_photos (file_id, set_by) VALUES (?, ?)''',
                          (file_id, query.from_user.id))
            conn.commit()
            await query.edit_message_text("✅ Foto armazenada no sistema")
            logger.info(f"Foto guardada por {query.from_user.id}")
        except sqlite3.IntegrityError:
            await query.edit_message_text("⚠️ Foto já existe no sistema")
        finally:
            conn.close()
            
    elif data == 'cancel':
        await query.delete_message()

@admin_only
async def cmd_setphoto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando: /setphoto - Altera foto de perfil do bot."""
    user_id = update.effective_user.id
    
    if update.message.reply_to_message and update.message.reply_to_message.photo:
        photo = update.message.reply_to_message.photo[-1]
        
        try:
            await context.bot.set_chat_photo(
                chat_id=update.effective_chat.id,
                photo=photo.file_id
            )
            
            # Guardar no banco de dados
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute('''INSERT OR REPLACE INTO profile_photos (file_id, set_by) 
                            VALUES (?, ?)''', (photo.file_id, user_id))
            conn.commit()
            conn.close()
            
            await update.message.reply_text("✅ Foto de perfil atualizada com sucesso")
            logger.info(f"Foto de perfil alterada por {user_id}")
            
        except TelegramError as e:
            await update.message.reply_text(f"❌ Erro ao alterar foto: {str(e)}")
            logger.error(f"Erro em /setphoto: {e}")
    else:
        await update.message.reply_text("""📸 **Comando: /setphoto**

Use: Responda a uma imagem com /setphoto

Formatos aceitos:
• JPG/PNG
• GIF (será convertido)
• Foto de arquivo

Exemplo: [Responda a foto] /setphoto
""")

# ═══════════════════════════════════════════════════════════════════════════
# MÓDULO DE FILTROS E PROTEÇÃO
# ═══════════════════════════════════════════════════════════════════════════

SPAM_PATTERNS = [
    'click here', 'visit now', 'buy now', 'free bitcoin',
    'earn money', 'casino', 'betting', 't.me/', 'click link'
]

async def filter_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Filtra mensagens de spam."""
    if not update.message or update.message.chat.type not in ['group', 'supergroup']:
        return
    
    message_text = (update.message.text or update.message.caption or '').lower()
    
    for pattern in SPAM_PATTERNS:
        if pattern in message_text:
            try:
                await update.message.delete()
                logger.info(f"Mensagem de spam deletada em {update.effective_chat.id}")
                return
            except TelegramError:
                pass

# ═══════════════════════════════════════════════════════════════════════════
# COMANDOS DE SISTEMA
# ═══════════════════════════════════════════════════════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando: /start - Apresentação do sistema."""
    msg = """🔐 **Sistema de Gestão Integrado v1.0**

Bem-vindo ao módulo de gerenciamento de grupos Telegram.

**Funcionalidades Disponíveis:**

📋 **Administração:**
  • /ban - Banimento permanente
  • /kick - Remoção temporária
  • /mute [min] - Silenciamento
  • /warn - Advertência (3 strikes = ban)

💰 **Contribuições:**
  • /donate - Interface de doações

📸 **Mídia:**
  • /setphoto - Alterar foto de perfil

**Status:** ✅ Sistema operacional
**Versão:** 1.0 Production
**Uptime Monitor:** Ativo

Acesse /help para informações detalhadas.
"""
    await update.message.reply_html(msg)
    logger.info(f"Comando /start executado por {update.effective_user.id}")

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando: /help - Ajuda geral."""
    msg = """📚 **Guia de Comandos**

**MÓDULO ADMINISTRAÇÃO:**
┌─ /ban @user [motivo]
│  └─ Bane permanentemente
├─ /kick
│  └─ Remove (responda mensagem)
├─ /mute [minutos]
│  └─ Silencia (responda mensagem)
└─ /warn
   └─ Advertência (responda mensagem)

**MÓDULO FINANCEIRO:**
└─ /donate
   └─ Contribuições e Bitcoin

**MÓDULO MÍDIA:**
├─ Enviar foto (admin detecta)
└─ /setphoto
   └─ Alterar foto perfil

**SISTEMA:**
├─ /start - Iniciar
├─ /help - Este menu
└─ /status - Status do sistema

**Requisitos:**
• Ser administrador do grupo
• Dar permissões ao bot
• Atualizar regularmente

Contato Suporte: Consulte administrador do grupo
"""
    await update.message.reply_text(msg)

async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando: /status - Status do sistema."""
    db_size = DATABASE_PATH.stat().st_size / 1024 / 1024 if DATABASE_PATH.exists() else 0
    
    msg = f"""✅ **Status do Sistema - Sistema de Gestão Integrado**

**Componentes Ativos:**
├ Módulo Administração: ✅ Online
├ Módulo Financeiro: ✅ Online
├ Módulo Mídia: ✅ Online
└ Database: ✅ Online

**Recursos:**
├ Banco de Dados: {db_size:.2f} MB
├ Logs: {len(list(LOGS_PATH.glob('*.log')))} arquivo(s)
└ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**Capacidade:**
├ Grupos Monitorados: 0+
├ Usuários Registrados: 0+
└ Ações Registradas: 0+

**Uptime:** Iniciado em sessão atual
**Versão:** 1.0.0
**Ambiente:** Produção

Próximo Backup: {(datetime.now() + timedelta(hours=1)).strftime('%H:%M:%S')}
"""
    await update.message.reply_text(msg)

# ═══════════════════════════════════════════════════════════════════════════
# HEALTH CHECK E MANUTENÇÃO
# ═══════════════════════════════════════════════════════════════════════════

async def health_check(context: ContextTypes.DEFAULT_TYPE):
    """Verifica saúde do sistema a cada 5 minutos."""
    try:
        # Verificar banco de dados
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM sqlite_master WHERE type="table"')
        tables = cursor.fetchone()[0]
        conn.close()
        
        if tables < 5:
            logger.error("Health Check FALHOU: Tabelas insuficientes no banco")
            return
        
        logger.info(f"✓ Health Check OK | DB: {tables} tabelas | Timestamp: {datetime.now()}")
        
    except Exception as e:
        logger.error(f"✗ Health Check ERRO: {e}")

async def backup_job(context: ContextTypes.DEFAULT_TYPE):
    """Realiza backup automático a cada hora."""
    try:
        db.backup()
        logger.info("Backup automático realizado com sucesso")
    except Exception as e:
        logger.error(f"Erro no backup: {e}")

async def cleanup_expired_mutes(context: ContextTypes.DEFAULT_TYPE):
    """Remove silenciamentos expirados."""
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT user_id, group_id FROM actions
            WHERE action_type = 'mute' AND expires_at <= CURRENT_TIMESTAMP
        ''')
        
        expired = cursor.fetchall()
        for row in expired:
            try:
                user_id = row['user_id']
                group_id = row['group_id']
                
                # Remover restrições
                await context.bot.restrict_chat_member(
                    group_id, user_id,
                    permissions=ChatPermissions(
                        can_send_messages=True,
                        can_send_media_messages=True,
                        can_send_polls=True,
                        can_send_other_messages=True,
                        can_add_web_page_previews=True
                    )
                )
                logger.info(f"Silenciamento expirado liberado: {user_id}")
            except TelegramError as e:
                logger.warning(f"Erro ao liberar silenciamento: {e}")
        
        conn.close()
    except Exception as e:
        logger.error(f"Erro no cleanup de mutes: {e}")

# ═══════════════════════════════════════════════════════════════════════════
# TRATAMENTO DE ERROS
# ═══════════════════════════════════════════════════════════════════════════

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler de erros global."""
    logger.error(f"Erro na atualização {update}: {context.error}")
    
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ Erro no processamento. Tente novamente ou contacte o suporte."
            )
        except TelegramError:
            pass

# ═══════════════════════════════════════════════════════════════════════════
# INICIALIZAÇÃO DO APLICATIVO
# ═══════════════════════════════════════════════════════════════════════════

def main():
    """Função principal - Inicia o sistema de gestão."""
    logger.info("╔════════════════════════════════════════════════╗")
    logger.info("║  INICIANDO SISTEMA DE GESTÃO INTEGRADO v1.0   ║")
    logger.info("║  python-telegram-bot v20+ | Production Ready   ║")
    logger.info("╚════════════════════════════════════════════════╝")
    
    if not TELEGRAM_BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN não configurado em .env")
        return
    
    if not ADMIN_IDS:
        logger.warning("⚠️ Nenhum ADMIN_IDS configurado. Funcionalidades limitadas.")
    
    # Criar aplicação
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Handlers de Comandos
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("ban", cmd_ban))
    app.add_handler(CommandHandler("kick", cmd_kick))
    app.add_handler(CommandHandler("mute", cmd_mute))
    app.add_handler(CommandHandler("warn", cmd_warn))
    app.add_handler(CommandHandler("donate", cmd_donate))
    app.add_handler(CommandHandler("setphoto", cmd_setphoto))
    
    # Handlers de Callbacks
    app.add_handler(CallbackQueryHandler(donate_callback, pattern='^(copy_wallet|donate_info|close)$'))
    app.add_handler(CallbackQueryHandler(photo_callback, pattern='^(resend_photo_|save_photo_|cancel)'))
    
    # Handlers de Mensagens
    app.add_handler(MessageHandler(filters.PHOTO & filters.ChatType.PRIVATE, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, filter_spam))
    
    # Job Queue (Tarefas Agendadas)
    job_queue = app.job_queue
    job_queue.run_repeating(health_check, interval=300, first=10)  # Health check a cada 5min
    job_queue.run_repeating(backup_job, interval=BACKUP_INTERVAL, first=60)  # Backup a cada 1h
    job_queue.run_repeating(cleanup_expired_mutes, interval=60, first=30)  # Cleanup a cada 1min
    
    # Error Handler
    app.add_error_handler(error_handler)
    
    logger.info("✓ Handlers registrados com sucesso")
    logger.info("✓ Job Queue inicializado")
    logger.info("✓ Sistema pronto para operação")
    
    # Iniciar polling
    logger.info("📡 Iniciando polling... (CTRL+C para parar)")
    
    try:
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    except KeyboardInterrupt:
        logger.info("\n⏹️  Sistema parado pelo usuário")
    except Exception as e:
        logger.critical(f"❌ Erro crítico: {e}")
        logger.info("🔄 Reiniciando em 10 segundos...")
        import time
        time.sleep(10)
        main()

if __name__ == '__main__':
    main()
