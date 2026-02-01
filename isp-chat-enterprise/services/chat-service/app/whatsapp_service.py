#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WhatsApp Business API Integration
Serviço para integração com WhatsApp Business API
"""

import asyncio
import logging
import json
import aiohttp
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config.settings import settings
from .models import (
    ConversationCreate, MessageCreate, ConversationStatus, 
    MessageType, MessageDirection, QueuePriority
)
from .services import chat_service
from .websocket_manager import websocket_manager

logger = logging.getLogger(__name__)

class WhatsAppService:
    """
    Serviço de integração com WhatsApp Business API
    
    Funcionalidades:
    - Receber webhooks do WhatsApp
    - Enviar mensagens via API
    - Processar diferentes tipos de mídia
    - Gerenciar status de entrega
    - Criar conversas automaticamente
    """
    
    def __init__(self):
        self.api_url = "https://graph.facebook.com/v18.0"
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        self.access_token = settings.WHATSAPP_ACCESS_TOKEN
        self.verify_token = settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN
        
    async def verify_webhook(self, mode: str, token: str, challenge: str) -> Optional[str]:
        """
        Verificar webhook do WhatsApp
        
        Args:
            mode: Modo de verificação
            token: Token de verificação
            challenge: Challenge do WhatsApp
            
        Returns:
            Challenge se válido, None caso contrário
        """
        if mode == "subscribe" and token == self.verify_token:
            logger.info("✅ Webhook WhatsApp verificado com sucesso")
            return challenge
        
        logger.warning(f"❌ Falha na verificação do webhook: mode={mode}, token válido={token == self.verify_token}")
        return None
    
    async def process_webhook(self, webhook_data: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
        """
        Processar webhook recebido do WhatsApp
        
        Args:
            webhook_data: Dados do webhook
            db: Sessão do banco de dados
            
        Returns:
            Resultado do processamento
        """
        try:
            logger.info(f"📥 Processando webhook WhatsApp: {json.dumps(webhook_data, indent=2)}")
            
            # Extrair dados do webhook
            entry = webhook_data.get("entry", [])
            if not entry:
                return {"status": "no_entry", "message": "Nenhuma entrada encontrada"}
            
            results = []
            
            for entry_item in entry:
                changes = entry_item.get("changes", [])
                
                for change in changes:
                    field = change.get("field")
                    value = change.get("value", {})
                    
                    if field == "messages":
                        # Processar mensagens recebidas
                        result = await self._process_messages(value, db)
                        results.append(result)
                    
                    elif field == "message_status":
                        # Processar status de mensagens
                        result = await self._process_message_status(value, db)
                        results.append(result)
            
            return {
                "status": "processed",
                "results": results,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar webhook: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _process_messages(self, messages_data: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
        """Processar mensagens recebidas"""
        try:
            messages = messages_data.get("messages", [])
            contacts = messages_data.get("contacts", [])
            
            # Criar mapa de contatos
            contacts_map = {contact["wa_id"]: contact for contact in contacts}
            
            processed_messages = []
            
            for message in messages:
                try:
                    # Extrair dados da mensagem
                    from_number = message.get("from")
                    message_id = message.get("id")
                    timestamp = message.get("timestamp")
                    message_type = message.get("type", "text")
                    
                    # Obter dados do contato
                    contact = contacts_map.get(from_number, {})
                    contact_name = contact.get("profile", {}).get("name", from_number)
                    
                    # Extrair conteúdo da mensagem
                    content = await self._extract_message_content(message)
                    
                    # Buscar ou criar conversa
                    conversation = await self._get_or_create_conversation(
                        db, from_number, contact_name
                    )
                    
                    # Criar mensagem
                    message_data = MessageCreate(
                        conversation_id=str(conversation.id),
                        content=content["text"],
                        message_type=MessageType(content["type"]),
                        direction=MessageDirection.INBOUND,
                        sender_phone=from_number,
                        sender_name=contact_name,
                        media_url=content.get("media_url"),
                        metadata={
                            "whatsapp_message_id": message_id,
                            "whatsapp_timestamp": timestamp,
                            "original_message": message
                        }
                    )
                    
                    # Salvar mensagem
                    saved_message = await chat_service.create_message(db, message_data)
                    
                    # Notificar via WebSocket
                    await websocket_manager.broadcast_to_conversation(
                        str(conversation.id),
                        {
                            "type": "new_message",
                            "message": saved_message.model_dump(),
                            "conversation": conversation.model_dump()
                        }
                    )
                    
                    processed_messages.append({
                        "message_id": message_id,
                        "conversation_id": str(conversation.id),
                        "status": "processed"
                    })
                    
                    logger.info(f"✅ Mensagem processada: {message_id} -> conversa {conversation.id}")
                    
                except Exception as e:
                    logger.error(f"❌ Erro ao processar mensagem {message.get('id', 'unknown')}: {e}")
                    processed_messages.append({
                        "message_id": message.get("id"),
                        "status": "error",
                        "error": str(e)
                    })
            
            return {
                "type": "messages",
                "processed": len(processed_messages),
                "messages": processed_messages
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar mensagens: {e}")
            return {"type": "messages", "status": "error", "error": str(e)}
    
    async def _process_message_status(self, status_data: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
        """Processar status de mensagens"""
        try:
            statuses = status_data.get("statuses", [])
            processed_statuses = []
            
            for status in statuses:
                message_id = status.get("id")
                status_type = status.get("status")  # sent, delivered, read, failed
                timestamp = status.get("timestamp")
                
                # TODO: Atualizar status da mensagem no banco
                # Buscar mensagem pelo whatsapp_message_id e atualizar status
                
                processed_statuses.append({
                    "message_id": message_id,
                    "status": status_type,
                    "timestamp": timestamp
                })
                
                logger.info(f"📊 Status atualizado: {message_id} -> {status_type}")
            
            return {
                "type": "status",
                "processed": len(processed_statuses),
                "statuses": processed_statuses
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar status: {e}")
            return {"type": "status", "status": "error", "error": str(e)}
    
    async def _extract_message_content(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Extrair conteúdo da mensagem baseado no tipo"""
        message_type = message.get("type", "text")
        
        if message_type == "text":
            return {
                "type": "text",
                "text": message.get("text", {}).get("body", "")
            }
        
        elif message_type == "image":
            image_data = message.get("image", {})
            return {
                "type": "image",
                "text": image_data.get("caption", "[Imagem]"),
                "media_url": image_data.get("id"),  # ID da mídia para download
                "mime_type": image_data.get("mime_type")
            }
        
        elif message_type == "document":
            doc_data = message.get("document", {})
            return {
                "type": "document",
                "text": f"[Documento: {doc_data.get('filename', 'arquivo')}]",
                "media_url": doc_data.get("id"),
                "mime_type": doc_data.get("mime_type")
            }
        
        elif message_type == "audio":
            audio_data = message.get("audio", {})
            return {
                "type": "audio",
                "text": "[Áudio]",
                "media_url": audio_data.get("id"),
                "mime_type": audio_data.get("mime_type")
            }
        
        elif message_type == "video":
            video_data = message.get("video", {})
            return {
                "type": "video",
                "text": video_data.get("caption", "[Vídeo]"),
                "media_url": video_data.get("id"),
                "mime_type": video_data.get("mime_type")
            }
        
        elif message_type == "location":
            location_data = message.get("location", {})
            lat = location_data.get("latitude")
            lng = location_data.get("longitude")
            return {
                "type": "location",
                "text": f"[Localização: {lat}, {lng}]"
            }
        
        elif message_type == "contacts":
            contacts_data = message.get("contacts", [])
            contact_names = [c.get("name", {}).get("formatted_name", "Contato") for c in contacts_data]
            return {
                "type": "contact",
                "text": f"[Contato: {', '.join(contact_names)}]"
            }
        
        else:
            return {
                "type": "text",
                "text": f"[Mensagem não suportada: {message_type}]"
            }
    
    async def _get_or_create_conversation(
        self, 
        db: AsyncSession, 
        phone: str, 
        name: str
    ) -> Any:
        """Buscar conversa existente ou criar nova"""
        try:
            # Buscar conversa ativa existente
            existing_conversations = await chat_service.list_conversations(
                db, page=1, per_page=1, customer_phone=phone,
                status=ConversationStatus.WAITING
            )
            
            if existing_conversations["conversations"]:
                return existing_conversations["conversations"][0]
            
            # Criar nova conversa
            conversation_data = ConversationCreate(
                customer_phone=phone,
                customer_name=name,
                priority=QueuePriority.NORMAL,
                metadata={"source": "whatsapp", "auto_created": True}
            )
            
            return await chat_service.create_conversation(db, conversation_data)
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar/criar conversa para {phone}: {e}")
            raise
    
    async def send_message(
        self, 
        to_phone: str, 
        message: str, 
        message_type: str = "text",
        media_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enviar mensagem via WhatsApp Business API
        
        Args:
            to_phone: Número de destino
            message: Conteúdo da mensagem
            message_type: Tipo da mensagem (text, image, document, etc)
            media_url: URL da mídia (se aplicável)
            
        Returns:
            Resultado do envio
        """
        try:
            if not self.access_token or not self.phone_number_id:
                raise ValueError("WhatsApp API não configurada (token ou phone_number_id ausente)")
            
            url = f"{self.api_url}/{self.phone_number_id}/messages"
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            # Preparar payload baseado no tipo
            if message_type == "text":
                payload = {
                    "messaging_product": "whatsapp",
                    "to": to_phone,
                    "type": "text",
                    "text": {"body": message}
                }
            
            elif message_type == "image" and media_url:
                payload = {
                    "messaging_product": "whatsapp",
                    "to": to_phone,
                    "type": "image",
                    "image": {
                        "link": media_url,
                        "caption": message
                    }
                }
            
            else:
                # Fallback para texto
                payload = {
                    "messaging_product": "whatsapp",
                    "to": to_phone,
                    "type": "text",
                    "text": {"body": message}
                }
            
            # Enviar via API
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    result = await response.json()
                    
                    if response.status == 200:
                        logger.info(f"✅ Mensagem enviada para {to_phone}: {result}")
                        return {
                            "success": True,
                            "message_id": result.get("messages", [{}])[0].get("id"),
                            "status": "sent"
                        }
                    else:
                        logger.error(f"❌ Erro ao enviar mensagem: {result}")
                        return {
                            "success": False,
                            "error": result,
                            "status": "failed"
                        }
        
        except Exception as e:
            logger.error(f"❌ Erro ao enviar mensagem WhatsApp: {e}")
            return {
                "success": False,
                "error": str(e),
                "status": "error"
            }
    
    async def download_media(self, media_id: str) -> Optional[bytes]:
        """
        Baixar mídia do WhatsApp
        
        Args:
            media_id: ID da mídia no WhatsApp
            
        Returns:
            Bytes da mídia ou None se erro
        """
        try:
            if not self.access_token:
                return None
            
            # Primeiro, obter URL da mídia
            url = f"{self.api_url}/{media_id}"
            headers = {"Authorization": f"Bearer {self.access_token}"}
            
            async with aiohttp.ClientSession() as session:
                # Obter informações da mídia
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        return None
                    
                    media_info = await response.json()
                    media_url = media_info.get("url")
                    
                    if not media_url:
                        return None
                
                # Baixar mídia
                async with session.get(media_url, headers=headers) as response:
                    if response.status == 200:
                        return await response.read()
                    
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro ao baixar mídia {media_id}: {e}")
            return None

# Instância global do serviço WhatsApp
whatsapp_service = WhatsAppService()