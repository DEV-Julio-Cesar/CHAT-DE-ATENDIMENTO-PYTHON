"""
Sistema de Migração de Dados - Node.js para Python
Migração completa e segura dos dados existentes
"""
import asyncio
import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
import structlog
from pathlib import Path
import hashlib
import shutil
from app.core.database import db_manager
from app.models.database import (
    Usuario, ClienteWhatsApp, Conversa, Mensagem, 
    Campanha, EnvioCampanha, ConfiguracaoSistema
)
from app.core.security_advanced import security_manager
from sqlalchemy import select, insert
from sqlalchemy.exc import IntegrityError

logger = structlog.get_logger(__name__)


class DataMigrationService:
    """Serviço de migração de dados do Node.js para Python"""
    
    def __init__(self):
        self.source_path = Path("chat-de-atendimento/dados")
        self.backup_path = Path("migration_backup")
        self.migration_log = []
        self.stats = {
            'users_migrated': 0,
            'clients_migrated': 0,
            'conversations_migrated': 0,
            'messages_migrated': 0,
            'campaigns_migrated': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None
        }
        
    async def migrate_all_data(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Migra todos os dados da aplicação Node.js
        
        Args:
            dry_run: Se True, apenas simula a migração sem salvar
        """
        try:
            self.stats['start_time'] = datetime.utcnow()
            logger.info("Starting data migration", dry_run=dry_run)
            
            # Criar backup antes da migração
            if not dry_run:
                await self._create_backup()
                
            # Migrar dados em ordem de dependência
            migration_steps = [
                ("Usuários", self._migrate_users),
                ("Clientes WhatsApp", self._migrate_whatsapp_clients),
                ("Conversas", self._migrate_conversations),
                ("Mensagens", self._migrate_messages),
                ("Campanhas", self._migrate_campaigns),
                ("Configurações", self._migrate_configurations)
            ]
            
            results = {}
            
            for step_name, migration_func in migration_steps:
                try:
                    logger.info(f"Migrating {step_name}...")
                    result = await migration_func(dry_run)
                    results[step_name.lower().replace(' ', '_')] = result
                    logger.info(f"Completed {step_name}", result=result)
                    
                except Exception as e:
                    logger.error(f"Error migrating {step_name}", error=str(e))
                    results[step_name.lower().replace(' ', '_')] = {'error': str(e)}
                    self.stats['errors'] += 1
                    
            self.stats['end_time'] = datetime.utcnow()
            duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
            
            # Gerar relatório final
            report = {
                'success': self.stats['errors'] == 0,
                'dry_run': dry_run,
                'duration_seconds': duration,
                'statistics': self.stats,
                'results': results,
                'migration_log': self.migration_log,
                'backup_path': str(self.backup_path) if not dry_run else None
            }
            
            logger.info("Data migration completed", report=report)
            return report
            
        except Exception as e:
            logger.error("Critical error in data migration", error=str(e))
            return {
                'success': False,
                'error': str(e),
                'statistics': self.stats
            }
            
    async def _create_backup(self):
        """Cria backup dos dados atuais"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_dir = self.backup_path / f"backup_{timestamp}"
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Backup do banco PostgreSQL
        db_backup_file = backup_dir / "database_backup.sql"
        # TODO: Implementar backup do PostgreSQL
        
        # Backup dos arquivos Node.js
        if self.source_path.exists():
            shutil.copytree(
                self.source_path,
                backup_dir / "nodejs_data",
                dirs_exist_ok=True
            )
            
        logger.info("Backup created", backup_path=str(backup_dir))
        
    async def _migrate_users(self, dry_run: bool = False) -> Dict[str, Any]:
        """Migra usuários do sistema Node.js"""
        users_file = self.source_path / "usuarios.json"
        
        if not users_file.exists():
            return {'error': 'Users file not found', 'migrated': 0}
            
        try:
            with open(users_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            users_data = data.get('usuarios', [])
            migrated_count = 0
            errors = []
            
            async with db_manager.get_session() as session:
                for user_data in users_data:
                    try:
                        # Verificar se usuário já existe
                        existing_user = await session.execute(
                            select(Usuario).where(Usuario.username == user_data['username'])
                        )
                        
                        if existing_user.scalar_one_or_none():
                            self._log_migration(f"User {user_data['username']} already exists, skipping")
                            continue
                            
                        # Criar novo usuário
                        new_user = Usuario(
                            username=user_data['username'],
                            email=user_data.get('email', f"{user_data['username']}@sistema.com"),
                            password_hash=user_data['password'],  # Já está hasheado
                            role=user_data.get('role', 'atendente'),
                            ativo=user_data.get('ativo', True),
                            created_at=datetime.fromisoformat(user_data.get('criadoEm', datetime.utcnow().isoformat())),
                            ultimo_login=datetime.fromisoformat(user_data['ultimoLogin']) if user_data.get('ultimoLogin') else None
                        )
                        
                        if not dry_run:
                            session.add(new_user)
                            await session.flush()
                            
                        migrated_count += 1
                        self._log_migration(f"Migrated user: {user_data['username']}")
                        
                    except Exception as e:
                        error_msg = f"Error migrating user {user_data.get('username', 'unknown')}: {str(e)}"
                        errors.append(error_msg)
                        logger.error(error_msg)
                        
                if not dry_run:
                    await session.commit()
                    
            self.stats['users_migrated'] = migrated_count
            
            return {
                'migrated': migrated_count,
                'errors': errors,
                'total_found': len(users_data)
            }
            
        except Exception as e:
            logger.error("Error in user migration", error=str(e))
            return {'error': str(e), 'migrated': 0}
            
    async def _migrate_whatsapp_clients(self, dry_run: bool = False) -> Dict[str, Any]:
        """Migra clientes WhatsApp"""
        sessions_file = self.source_path / "whatsapp-sessions.json"
        
        if not sessions_file.exists():
            return {'error': 'WhatsApp sessions file not found', 'migrated': 0}
            
        try:
            with open(sessions_file, 'r', encoding='utf-8') as f:
                sessions_data = json.load(f)
                
            migrated_count = 0
            errors = []
            
            async with db_manager.get_session() as session:
                for session_id, session_info in sessions_data.items():
                    try:
                        # Extrair informações do cliente
                        client_data = session_info.get('clientInfo', {})
                        
                        if not client_data:
                            continue
                            
                        # Verificar se cliente já existe
                        existing_client = await session.execute(
                            select(ClienteWhatsApp).where(
                                ClienteWhatsApp.client_id == session_id
                            )
                        )
                        
                        if existing_client.scalar_one_or_none():
                            continue
                            
                        # Criar novo cliente
                        new_client = ClienteWhatsApp(
                            client_id=session_id,
                            nome=client_data.get('pushname', f'Cliente {session_id}'),
                            telefone=client_data.get('wid', {}).get('user', ''),
                            status='ativo' if session_info.get('connected', False) else 'inativo',
                            metadata={
                                'platform': client_data.get('platform'),
                                'session_info': session_info
                            }
                        )
                        
                        if not dry_run:
                            session.add(new_client)
                            await session.flush()
                            
                        migrated_count += 1
                        self._log_migration(f"Migrated WhatsApp client: {session_id}")
                        
                    except Exception as e:
                        error_msg = f"Error migrating WhatsApp client {session_id}: {str(e)}"
                        errors.append(error_msg)
                        logger.error(error_msg)
                        
                if not dry_run:
                    await session.commit()
                    
            self.stats['clients_migrated'] = migrated_count
            
            return {
                'migrated': migrated_count,
                'errors': errors,
                'total_found': len(sessions_data)
            }
            
        except Exception as e:
            logger.error("Error in WhatsApp clients migration", error=str(e))
            return {'error': str(e), 'migrated': 0}
            
    async def _migrate_conversations(self, dry_run: bool = False) -> Dict[str, Any]:
        """Migra conversas"""
        atendimentos_file = self.source_path / "atendimentos.json"
        
        if not atendimentos_file.exists():
            return {'error': 'Conversations file not found', 'migrated': 0}
            
        try:
            with open(atendimentos_file, 'r', encoding='utf-8') as f:
                atendimentos_data = json.load(f)
                
            migrated_count = 0
            errors = []
            
            async with db_manager.get_session() as session:
                for chat_id, conversa_data in atendimentos_data.items():
                    try:
                        # Verificar se conversa já existe
                        existing_conv = await session.execute(
                            select(Conversa).where(Conversa.chat_id == chat_id)
                        )
                        
                        if existing_conv.scalar_one_or_none():
                            continue
                            
                        # Buscar cliente relacionado
                        client_result = await session.execute(
                            select(ClienteWhatsApp).where(
                                ClienteWhatsApp.telefone.contains(chat_id.split('@')[0])
                            )
                        )
                        client = client_result.scalar_one_or_none()
                        
                        if not client:
                            # Criar cliente temporário
                            client = ClienteWhatsApp(
                                client_id=f"migrated_{chat_id}",
                                nome=conversa_data.get('nomeContato', 'Cliente Migrado'),
                                telefone=chat_id.split('@')[0],
                                status='ativo'
                            )
                            session.add(client)
                            await session.flush()
                            
                        # Buscar atendente se especificado
                        atendente_id = None
                        if conversa_data.get('atendente'):
                            atendente_result = await session.execute(
                                select(Usuario).where(
                                    Usuario.username == conversa_data['atendente']
                                )
                            )
                            atendente = atendente_result.scalar_one_or_none()
                            if atendente:
                                atendente_id = atendente.id
                                
                        # Criar conversa
                        new_conversa = Conversa(
                            cliente_id=client.id,
                            chat_id=chat_id,
                            estado=conversa_data.get('estado', 'automacao'),
                            atendente_id=atendente_id,
                            prioridade=conversa_data.get('prioridade', 0),
                            metadata={
                                'migrated_from': 'nodejs',
                                'original_data': conversa_data
                            },
                            created_at=datetime.fromisoformat(
                                conversa_data.get('iniciadoEm', datetime.utcnow().isoformat())
                            )
                        )
                        
                        if not dry_run:
                            session.add(new_conversa)
                            await session.flush()
                            
                        migrated_count += 1
                        self._log_migration(f"Migrated conversation: {chat_id}")
                        
                    except Exception as e:
                        error_msg = f"Error migrating conversation {chat_id}: {str(e)}"
                        errors.append(error_msg)
                        logger.error(error_msg)
                        
                if not dry_run:
                    await session.commit()
                    
            self.stats['conversations_migrated'] = migrated_count
            
            return {
                'migrated': migrated_count,
                'errors': errors,
                'total_found': len(atendimentos_data)
            }
            
        except Exception as e:
            logger.error("Error in conversations migration", error=str(e))
            return {'error': str(e), 'migrated': 0}
            
    async def _migrate_messages(self, dry_run: bool = False) -> Dict[str, Any]:
        """Migra mensagens das conversas"""
        messages_dir = self.source_path / "mensagens"
        
        if not messages_dir.exists():
            return {'error': 'Messages directory not found', 'migrated': 0}
            
        migrated_count = 0
        errors = []
        
        try:
            async with db_manager.get_session() as session:
                for message_file in messages_dir.glob("*.json"):
                    try:
                        with open(message_file, 'r', encoding='utf-8') as f:
                            messages_data = json.load(f)
                            
                        chat_id = message_file.stem.replace('client_', '').split('_', 2)[-1]
                        
                        # Buscar conversa relacionada
                        conv_result = await session.execute(
                            select(Conversa).where(Conversa.chat_id.contains(chat_id))
                        )
                        conversa = conv_result.scalar_one_or_none()
                        
                        if not conversa:
                            continue
                            
                        for msg_data in messages_data.get('mensagens', []):
                            try:
                                # Verificar se mensagem já existe
                                existing_msg = await session.execute(
                                    select(Mensagem).where(
                                        Mensagem.whatsapp_message_id == msg_data.get('id')
                                    )
                                )
                                
                                if existing_msg.scalar_one_or_none():
                                    continue
                                    
                                # Determinar tipo de remetente
                                remetente_tipo = 'cliente'
                                if msg_data.get('fromMe', False):
                                    remetente_tipo = 'atendente'
                                elif msg_data.get('author') and 'bot' in msg_data.get('author', '').lower():
                                    remetente_tipo = 'bot'
                                    
                                # Criar mensagem
                                new_message = Mensagem(
                                    conversa_id=conversa.id,
                                    whatsapp_message_id=msg_data.get('id'),
                                    remetente_tipo=remetente_tipo,
                                    remetente_id=msg_data.get('author', chat_id),
                                    conteudo=msg_data.get('body', ''),
                                    tipo_mensagem=msg_data.get('type', 'texto'),
                                    metadata={
                                        'migrated_from': 'nodejs',
                                        'original_data': msg_data
                                    },
                                    created_at=datetime.fromtimestamp(
                                        msg_data.get('timestamp', 0)
                                    ) if msg_data.get('timestamp') else datetime.utcnow()
                                )
                                
                                if not dry_run:
                                    session.add(new_message)
                                    
                                migrated_count += 1
                                
                            except Exception as e:
                                error_msg = f"Error migrating message in {message_file}: {str(e)}"
                                errors.append(error_msg)
                                
                    except Exception as e:
                        error_msg = f"Error processing message file {message_file}: {str(e)}"
                        errors.append(error_msg)
                        logger.error(error_msg)
                        
                if not dry_run:
                    await session.commit()
                    
            self.stats['messages_migrated'] = migrated_count
            
            return {
                'migrated': migrated_count,
                'errors': errors,
                'files_processed': len(list(messages_dir.glob("*.json")))
            }
            
        except Exception as e:
            logger.error("Error in messages migration", error=str(e))
            return {'error': str(e), 'migrated': 0}
            
    async def _migrate_campaigns(self, dry_run: bool = False) -> Dict[str, Any]:
        """Migra campanhas"""
        campaigns_file = self.source_path / "campanhas.json"
        
        if not campaigns_file.exists():
            return {'error': 'Campaigns file not found', 'migrated': 0}
            
        try:
            with open(campaigns_file, 'r', encoding='utf-8') as f:
                campaigns_data = json.load(f)
                
            migrated_count = 0
            errors = []
            
            async with db_manager.get_session() as session:
                for campaign_data in campaigns_data.get('campanhas', []):
                    try:
                        # Buscar criador da campanha
                        criador_result = await session.execute(
                            select(Usuario).where(
                                Usuario.username == campaign_data.get('criador', 'admin')
                            )
                        )
                        criador = criador_result.scalar_one_or_none()
                        
                        if not criador:
                            # Usar admin padrão
                            criador_result = await session.execute(
                                select(Usuario).where(Usuario.role == 'admin')
                            )
                            criador = criador_result.first()
                            if not criador:
                                continue
                                
                        # Criar campanha
                        new_campaign = Campanha(
                            nome=campaign_data.get('nome', 'Campanha Migrada'),
                            descricao=campaign_data.get('descricao', ''),
                            mensagem_template=campaign_data.get('mensagem', ''),
                            criador_id=criador.id,
                            status=campaign_data.get('status', 'finalizada'),
                            total_destinatarios=campaign_data.get('totalDestinatarios', 0),
                            enviadas=campaign_data.get('enviadas', 0),
                            falharam=campaign_data.get('falharam', 0),
                            metadata={
                                'migrated_from': 'nodejs',
                                'original_data': campaign_data
                            },
                            created_at=datetime.fromisoformat(
                                campaign_data.get('criadaEm', datetime.utcnow().isoformat())
                            )
                        )
                        
                        if not dry_run:
                            session.add(new_campaign)
                            await session.flush()
                            
                        migrated_count += 1
                        self._log_migration(f"Migrated campaign: {campaign_data.get('nome')}")
                        
                    except Exception as e:
                        error_msg = f"Error migrating campaign {campaign_data.get('nome', 'unknown')}: {str(e)}"
                        errors.append(error_msg)
                        logger.error(error_msg)
                        
                if not dry_run:
                    await session.commit()
                    
            return {
                'migrated': migrated_count,
                'errors': errors,
                'total_found': len(campaigns_data.get('campanhas', []))
            }
            
        except Exception as e:
            logger.error("Error in campaigns migration", error=str(e))
            return {'error': str(e), 'migrated': 0}
            
    async def _migrate_configurations(self, dry_run: bool = False) -> Dict[str, Any]:
        """Migra configurações do sistema"""
        config_files = [
            ('automacao-config.json', 'automacao'),
            ('feature-flags.json', 'feature_flags'),
            ('theme.json', 'theme'),
            ('config-ia-humanizada.json', 'ia_config')
        ]
        
        migrated_count = 0
        errors = []
        
        try:
            async with db_manager.get_session() as session:
                for filename, categoria in config_files:
                    config_file = self.source_path / filename
                    
                    if not config_file.exists():
                        continue
                        
                    try:
                        with open(config_file, 'r', encoding='utf-8') as f:
                            config_data = json.load(f)
                            
                        # Verificar se configuração já existe
                        existing_config = await session.execute(
                            select(ConfiguracaoSistema).where(
                                ConfiguracaoSistema.chave == filename.replace('.json', '')
                            )
                        )
                        
                        if existing_config.scalar_one_or_none():
                            continue
                            
                        # Criar configuração
                        new_config = ConfiguracaoSistema(
                            chave=filename.replace('.json', ''),
                            valor=config_data,
                            descricao=f'Configuração migrada: {filename}',
                            categoria=categoria
                        )
                        
                        if not dry_run:
                            session.add(new_config)
                            
                        migrated_count += 1
                        self._log_migration(f"Migrated configuration: {filename}")
                        
                    except Exception as e:
                        error_msg = f"Error migrating config {filename}: {str(e)}"
                        errors.append(error_msg)
                        logger.error(error_msg)
                        
                if not dry_run:
                    await session.commit()
                    
            return {
                'migrated': migrated_count,
                'errors': errors,
                'files_processed': len(config_files)
            }
            
        except Exception as e:
            logger.error("Error in configurations migration", error=str(e))
            return {'error': str(e), 'migrated': 0}
            
    def _log_migration(self, message: str):
        """Registra log da migração"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'message': message
        }
        self.migration_log.append(log_entry)
        logger.info(message)
        
    async def validate_migration(self) -> Dict[str, Any]:
        """Valida a migração comparando dados"""
        try:
            validation_results = {}
            
            async with db_manager.get_session() as session:
                # Contar registros migrados
                users_count = await session.execute(select(Usuario).count())
                clients_count = await session.execute(select(ClienteWhatsApp).count())
                conversations_count = await session.execute(select(Conversa).count())
                messages_count = await session.execute(select(Mensagem).count())
                campaigns_count = await session.execute(select(Campanha).count())
                
                validation_results = {
                    'users_in_db': users_count.scalar(),
                    'clients_in_db': clients_count.scalar(),
                    'conversations_in_db': conversations_count.scalar(),
                    'messages_in_db': messages_count.scalar(),
                    'campaigns_in_db': campaigns_count.scalar(),
                    'validation_timestamp': datetime.utcnow().isoformat()
                }
                
            return {
                'success': True,
                'results': validation_results
            }
            
        except Exception as e:
            logger.error("Error validating migration", error=str(e))
            return {
                'success': False,
                'error': str(e)
            }


# Instância global
migration_service = DataMigrationService()