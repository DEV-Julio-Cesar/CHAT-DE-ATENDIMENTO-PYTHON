"""
WhatsApp Business API Enterprise
Integração profissional para ISP com 10k+ clientes
"""
import asyncio
import aiohttp
import json
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import structlog
from urllib.parse import urljoin
import hashlib
import hmac
from app.core.config import settings
from app.core.redis_client import redis_manager
from app.core.monitoring import monitoring, WHATSAPP_MESSAGES

logger = structlog.get_logger(__name__)


@dataclass
class WhatsAppMessage:
    """Estrutura de mensagem WhatsApp"""
    id: str
    from_number: str
    to_number: str
    message_type: str
    content: str
    timestamp: datetime
    status: str
    metadata: Optional[Dict] = None


@dataclass
class WhatsAppTemplate:
    """Template de mensagem aprovado"""
    name: str
    language: str
    category: str
    components: List[Dict]
    status: str


@dataclass
class WhatsAppSession:
    """Sessão WhatsApp ativa"""
    session_id: str
    phone_number: str
    status: str
    webhook_url: str
    created_at: datetime
    last_activity: datetime
    message_count: int = 0
    error_count: int = 0


class WhatsAppEnterpriseAPI:
    """API Enterprise do WhatsApp Business"""
    
    def __init__(self):
        self.base_url = "https://graph.facebook.com/v19.0"
        self.access_token = settings.WHATSAPP_ACCESS_TOKEN
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        self.webhook_verify_token = settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN
        self.session = None
        self.active_sessions: Dict[str, WhatsAppSession] = {}
        self.message_queue = asyncio.Queue(maxsize=10000)
        self.rate_limiter = RateLimiter(1000, 60)  # 1000 msgs/min
        
    async def initialize(self):
        """Inicializa a API"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
        )
        
        # Inicia workers de processamento
        asyncio.create_task(self._message_processor())
        asyncio.create_task(self._health_monitor())
        
        logger.info("WhatsApp Enterprise API initialized")
        
    async def close(self):
        """Fecha conexões"""
        if self.session:
            await self.session.close()
            
    async def send_message(
        self,
        to_number: str,
        message: str,
        message_type: str = "text",
        media_url: Optional[str] = None,
        template_name: Optional[str] = None,
        template_params: Optional[List[str]] = None,
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """
        Envia mensagem via WhatsApp Business API
        
        Args:
            to_number: Número de destino (formato internacional)
            message: Conteúdo da mensagem
            message_type: Tipo (text, image, document, template)
            media_url: URL da mídia (se aplicável)
            template_name: Nome do template aprovado
            template_params: Parâmetros do template
            priority: Prioridade (normal, high, urgent)
        """
        try:
            # Validações
            if not self._validate_phone_number(to_number):
                return {
                    'success': False,
                    'error': 'Invalid phone number format',
                    'code': 'INVALID_PHONE'
                }
                
            # Rate limiting
            if not await self.rate_limiter.acquire():
                return {
                    'success': False,
                    'error': 'Rate limit exceeded',
                    'code': 'RATE_LIMIT'
                }
                
            # Constrói payload baseado no tipo
            payload = await self._build_message_payload(
                to_number, message, message_type, media_url,
                template_name, template_params
            )
            
            # Envia mensagem
            url = f"{self.base_url}/{self.phone_number_id}/messages"
            
            async with self.session.post(url, json=payload) as response:
                response_data = await response.json()
                
                if response.status == 200:
                    message_id = response_data.get('messages', [{}])[0].get('id')
                    
                    # Registra métricas
                    WHATSAPP_MESSAGES.labels(
                        direction='outbound',
                        type=message_type,
                        status='sent'
                    ).inc()
                    
                    # Cache da mensagem
                    await self._cache_message(
                        message_id, to_number, message, message_type, 'sent'
                    )
                    
                    logger.info(
                        "WhatsApp message sent",
                        message_id=message_id,
                        to_number=to_number,
                        type=message_type
                    )
                    
                    return {
                        'success': True,
                        'message_id': message_id,
                        'status': 'sent',
                        'timestamp': datetime.utcnow().isoformat()
                    }
                else:
                    error_info = response_data.get('error', {})
                    error_code = error_info.get('code', 'UNKNOWN')
                    error_message = error_info.get('message', 'Unknown error')
                    
                    WHATSAPP_MESSAGES.labels(
                        direction='outbound',
                        type=message_type,
                        status='failed'
                    ).inc()
                    
                    logger.error(
                        "WhatsApp message failed",
                        error_code=error_code,
                        error_message=error_message,
                        to_number=to_number
                    )
                    
                    return {
                        'success': False,
                        'error': error_message,
                        'code': error_code,
                        'status_code': response.status
                    }
                    
        except Exception as e:
            logger.error("Error sending WhatsApp message", error=str(e))
            return {
                'success': False,
                'error': str(e),
                'code': 'INTERNAL_ERROR'
            }
            
    async def send_bulk_messages(
        self,
        messages: List[Dict[str, Any]],
        batch_size: int = 100,
        delay_between_batches: float = 1.0
    ) -> Dict[str, Any]:
        """
        Envia mensagens em lote com controle de taxa
        
        Args:
            messages: Lista de mensagens para enviar
            batch_size: Tamanho do lote
            delay_between_batches: Delay entre lotes (segundos)
        """
        results = {
            'total': len(messages),
            'sent': 0,
            'failed': 0,
            'details': []
        }
        
        # Processa em lotes
        for i in range(0, len(messages), batch_size):
            batch = messages[i:i + batch_size]
            batch_results = await asyncio.gather(
                *[self.send_message(**msg) for msg in batch],
                return_exceptions=True
            )
            
            # Processa resultados do lote
            for msg, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    results['failed'] += 1
                    results['details'].append({
                        'to_number': msg.get('to_number'),
                        'success': False,
                        'error': str(result)
                    })
                elif result.get('success'):
                    results['sent'] += 1
                    results['details'].append({
                        'to_number': msg.get('to_number'),
                        'success': True,
                        'message_id': result.get('message_id')
                    })
                else:
                    results['failed'] += 1
                    results['details'].append({
                        'to_number': msg.get('to_number'),
                        'success': False,
                        'error': result.get('error')
                    })
                    
            # Delay entre lotes
            if i + batch_size < len(messages):
                await asyncio.sleep(delay_between_batches)
                
        logger.info(
            "Bulk WhatsApp messages completed",
            total=results['total'],
            sent=results['sent'],
            failed=results['failed']
        )
        
        return results
        
    async def get_message_status(self, message_id: str) -> Dict[str, Any]:
        """Obtém status de uma mensagem"""
        try:
            # Primeiro verifica cache
            cached = await redis_manager.get(f"whatsapp:message:{message_id}")
            if cached:
                return json.loads(cached)
                
            # Consulta API
            url = f"{self.base_url}/{message_id}"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Cache resultado
                    await redis_manager.setex(
                        f"whatsapp:message:{message_id}",
                        3600,  # 1 hora
                        json.dumps(data)
                    )
                    
                    return {
                        'success': True,
                        'status': data.get('status'),
                        'timestamp': data.get('timestamp')
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Message not found',
                        'code': 'NOT_FOUND'
                    }
                    
        except Exception as e:
            logger.error("Error getting message status", error=str(e))
            return {
                'success': False,
                'error': str(e),
                'code': 'INTERNAL_ERROR'
            }
            
    async def create_template(
        self,
        name: str,
        category: str,
        language: str,
        components: List[Dict]
    ) -> Dict[str, Any]:
        """Cria template de mensagem"""
        try:
            payload = {
                'name': name,
                'category': category,
                'language': language,
                'components': components
            }
            
            url = f"{self.base_url}/{settings.WHATSAPP_BUSINESS_ACCOUNT_ID}/message_templates"
            
            async with self.session.post(url, json=payload) as response:
                response_data = await response.json()
                
                if response.status == 200:
                    template_id = response_data.get('id')
                    
                    logger.info(
                        "WhatsApp template created",
                        template_id=template_id,
                        name=name
                    )
                    
                    return {
                        'success': True,
                        'template_id': template_id,
                        'status': 'pending_approval'
                    }
                else:
                    error_info = response_data.get('error', {})
                    return {
                        'success': False,
                        'error': error_info.get('message', 'Unknown error'),
                        'code': error_info.get('code', 'UNKNOWN')
                    }
                    
        except Exception as e:
            logger.error("Error creating template", error=str(e))
            return {
                'success': False,
                'error': str(e),
                'code': 'INTERNAL_ERROR'
            }
            
    async def list_templates(self) -> Dict[str, Any]:
        """Lista templates aprovados"""
        try:
            url = f"{self.base_url}/{settings.WHATSAPP_BUSINESS_ACCOUNT_ID}/message_templates"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    templates = data.get('data', [])
                    
                    # Filtra apenas aprovados
                    approved_templates = [
                        t for t in templates 
                        if t.get('status') == 'APPROVED'
                    ]
                    
                    return {
                        'success': True,
                        'templates': approved_templates,
                        'total': len(approved_templates)
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Failed to fetch templates',
                        'code': 'API_ERROR'
                    }
                    
        except Exception as e:
            logger.error("Error listing templates", error=str(e))
            return {
                'success': False,
                'error': str(e),
                'code': 'INTERNAL_ERROR'
            }
            
    async def get_connected_clients(self) -> List[Dict[str, Any]]:
        """Obtém lista de clientes conectados"""
        try:
            # Busca sessões ativas no Redis
            sessions = await redis_manager.hgetall('whatsapp:active_sessions')
            
            clients = []
            for session_id, session_data in sessions.items():
                session_info = json.loads(session_data)
                clients.append({
                    'id': session_id,
                    'phone': session_info.get('phone_number'),
                    'status': session_info.get('status', 'connected'),
                    'name': f"Cliente {session_info.get('phone_number', 'Unknown')}",
                    'last_activity': session_info.get('last_activity'),
                    'message_count': session_info.get('message_count', 0)
                })
                
            return clients
            
        except Exception as e:
            logger.error("Error getting connected clients", error=str(e))
            return []
            
    async def get_status(self) -> Dict[str, Any]:
        """Obtém status da integração WhatsApp"""
        try:
            # Verifica saúde da API
            health_status = await redis_manager.get('whatsapp:health')
            
            # Conta sessões ativas
            active_sessions = await redis_manager.hlen('whatsapp:active_sessions')
            
            # Métricas básicas
            return {
                'success': True,
                'status': health_status or 'unknown',
                'active_sessions': active_sessions,
                'api_configured': bool(self.access_token and self.phone_number_id),
                'webhook_configured': bool(self.webhook_verify_token),
                'rate_limit_status': 'normal',  # Placeholder
                'last_health_check': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Error getting WhatsApp status", error=str(e))
            return {
                'success': False,
                'error': str(e),
                'code': 'INTERNAL_ERROR'
            }
            
    async def configure(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Configura WhatsApp Business API"""
        try:
            # Atualiza configurações
            if 'access_token' in config_data:
                self.access_token = config_data['access_token']
                
            if 'phone_number_id' in config_data:
                self.phone_number_id = config_data['phone_number_id']
                
            if 'webhook_verify_token' in config_data:
                self.webhook_verify_token = config_data['webhook_verify_token']
                
            # Atualiza headers da sessão
            if self.session:
                self.session.headers.update({
                    'Authorization': f'Bearer {self.access_token}'
                })
                
            # Testa configuração
            test_result = await self._test_configuration()
            
            return {
                'success': True,
                'message': 'WhatsApp configurado com sucesso',
                'test_result': test_result
            }
            
        except Exception as e:
            logger.error("Error configuring WhatsApp", error=str(e))
            return {
                'success': False,
                'error': str(e),
                'code': 'INTERNAL_ERROR'
            }
            
    async def process_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """Processa webhook recebido"""
        return await self.handle_webhook(webhook_data)
        
    async def _test_configuration(self) -> Dict[str, Any]:
        """Testa configuração atual"""
        try:
            if not self.access_token or not self.phone_number_id:
                return {
                    'success': False,
                    'error': 'Missing required configuration'
                }
                
            # Testa acesso à API
            url = f"{self.base_url}/{self.phone_number_id}"
            async with self.session.get(url) as response:
                if response.status == 200:
                    return {
                        'success': True,
                        'message': 'Configuration test successful'
                    }
                else:
                    return {
                        'success': False,
                        'error': f'API test failed with status {response.status}'
                    }
                    
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
        """Processa webhook do WhatsApp"""
        try:
            # Verifica assinatura
            if not self._verify_webhook_signature(payload):
                return {
                    'success': False,
                    'error': 'Invalid signature',
                    'code': 'INVALID_SIGNATURE'
                }
                
            # Processa diferentes tipos de evento
            entry = payload.get('entry', [{}])[0]
            changes = entry.get('changes', [{}])[0]
            value = changes.get('value', {})
            
            # Mensagens recebidas
            if 'messages' in value:
                await self._process_incoming_messages(value['messages'])
                
            # Status de mensagens
            if 'statuses' in value:
                await self._process_message_statuses(value['statuses'])
                
            # Erros
            if 'errors' in value:
                await self._process_webhook_errors(value['errors'])
                
            return {'success': True}
            
        except Exception as e:
            logger.error("Error processing webhook", error=str(e))
            return {
                'success': False,
                'error': str(e),
                'code': 'INTERNAL_ERROR'
            }
            
    async def get_analytics(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Obtém analytics do WhatsApp"""
        try:
            # Métricas do Redis
            metrics = await redis_manager.hgetall('whatsapp:analytics:daily')
            
            # Calcula estatísticas
            total_sent = sum(int(v) for k, v in metrics.items() if k.startswith('sent:'))
            total_delivered = sum(int(v) for k, v in metrics.items() if k.startswith('delivered:'))
            total_read = sum(int(v) for k, v in metrics.items() if k.startswith('read:'))
            total_failed = sum(int(v) for k, v in metrics.items() if k.startswith('failed:'))
            
            delivery_rate = (total_delivered / total_sent * 100) if total_sent > 0 else 0
            read_rate = (total_read / total_delivered * 100) if total_delivered > 0 else 0
            failure_rate = (total_failed / total_sent * 100) if total_sent > 0 else 0
            
            return {
                'success': True,
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'metrics': {
                    'messages_sent': total_sent,
                    'messages_delivered': total_delivered,
                    'messages_read': total_read,
                    'messages_failed': total_failed,
                    'delivery_rate': round(delivery_rate, 2),
                    'read_rate': round(read_rate, 2),
                    'failure_rate': round(failure_rate, 2)
                },
                'trends': await self._calculate_trends(start_date, end_date)
            }
            
        except Exception as e:
            logger.error("Error getting analytics", error=str(e))
            return {
                'success': False,
                'error': str(e),
                'code': 'INTERNAL_ERROR'
            }
            
    # Métodos auxiliares
    def _validate_phone_number(self, phone: str) -> bool:
        """Valida formato do número de telefone"""
        # Remove caracteres não numéricos
        clean_phone = ''.join(filter(str.isdigit, phone))
        
        # Verifica se tem pelo menos 10 dígitos
        if len(clean_phone) < 10:
            return False
            
        # Verifica se começa com código do país
        if not clean_phone.startswith(('55', '1', '44', '49')):  # BR, US, UK, DE
            return False
            
        return True
        
    async def _build_message_payload(
        self,
        to_number: str,
        message: str,
        message_type: str,
        media_url: Optional[str] = None,
        template_name: Optional[str] = None,
        template_params: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Constrói payload da mensagem"""
        payload = {
            'messaging_product': 'whatsapp',
            'to': to_number
        }
        
        if message_type == 'text':
            payload['type'] = 'text'
            payload['text'] = {'body': message}
            
        elif message_type == 'template':
            payload['type'] = 'template'
            payload['template'] = {
                'name': template_name,
                'language': {'code': 'pt_BR'},
                'components': []
            }
            
            if template_params:
                payload['template']['components'].append({
                    'type': 'body',
                    'parameters': [
                        {'type': 'text', 'text': param}
                        for param in template_params
                    ]
                })
                
        elif message_type in ['image', 'document', 'audio', 'video']:
            payload['type'] = message_type
            payload[message_type] = {
                'link': media_url,
                'caption': message if message_type == 'image' else None
            }
            
        return payload
        
    async def _cache_message(
        self,
        message_id: str,
        to_number: str,
        content: str,
        message_type: str,
        status: str
    ):
        """Cache da mensagem enviada"""
        message_data = {
            'id': message_id,
            'to_number': to_number,
            'content': content,
            'type': message_type,
            'status': status,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        await redis_manager.setex(
            f"whatsapp:message:{message_id}",
            86400,  # 24 horas
            json.dumps(message_data)
        )
        
    def _verify_webhook_signature(self, payload: Dict[str, Any]) -> bool:
        """Verifica assinatura do webhook"""
        # Implementar verificação HMAC
        return True  # Placeholder
        
    async def _process_incoming_messages(self, messages: List[Dict]):
        """Processa mensagens recebidas"""
        for msg in messages:
            WHATSAPP_MESSAGES.labels(
                direction='inbound',
                type=msg.get('type', 'unknown'),
                status='received'
            ).inc()
            
            # Adiciona à fila de processamento
            await self.message_queue.put({
                'type': 'incoming_message',
                'data': msg,
                'timestamp': datetime.utcnow()
            })
            
    async def _process_message_statuses(self, statuses: List[Dict]):
        """Processa status de mensagens"""
        for status in statuses:
            message_id = status.get('id')
            status_type = status.get('status')
            
            # Atualiza cache
            await redis_manager.hset(
                f"whatsapp:message:{message_id}",
                'status',
                status_type
            )
            
            # Métricas
            WHATSAPP_MESSAGES.labels(
                direction='outbound',
                type='status_update',
                status=status_type
            ).inc()
            
    async def _process_webhook_errors(self, errors: List[Dict]):
        """Processa erros do webhook"""
        for error in errors:
            logger.error(
                "WhatsApp webhook error",
                error_code=error.get('code'),
                error_message=error.get('message')
            )
            
    async def _message_processor(self):
        """Worker para processar mensagens da fila"""
        while True:
            try:
                # Processa mensagens da fila
                message = await self.message_queue.get()
                
                # Aqui você pode implementar lógica de:
                # - Roteamento para atendentes
                # - Processamento por IA
                # - Respostas automáticas
                # - Integração com CRM
                
                logger.info("Processing message", message_type=message['type'])
                
            except Exception as e:
                logger.error("Error processing message", error=str(e))
                
    async def _health_monitor(self):
        """Monitor de saúde da API"""
        while True:
            try:
                # Verifica saúde da API
                url = f"{self.base_url}/{self.phone_number_id}"
                async with self.session.get(url) as response:
                    if response.status == 200:
                        await redis_manager.setex(
                            'whatsapp:health',
                            300,  # 5 minutos
                            'healthy'
                        )
                    else:
                        await redis_manager.setex(
                            'whatsapp:health',
                            300,
                            'unhealthy'
                        )
                        
            except Exception as e:
                logger.error("WhatsApp health check failed", error=str(e))
                await redis_manager.setex('whatsapp:health', 300, 'error')
                
            await asyncio.sleep(300)  # 5 minutos
            
    async def _calculate_trends(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Calcula tendências das métricas"""
        # Implementar cálculo de tendências
        return {
            'message_volume_trend': 'increasing',
            'delivery_rate_trend': 'stable',
            'response_time_trend': 'improving'
        }


class RateLimiter:
    """Rate limiter para API do WhatsApp"""
    
    def __init__(self, max_requests: int, time_window: int):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
        
    async def acquire(self) -> bool:
        """Adquire permissão para fazer request"""
        now = datetime.utcnow()
        
        # Remove requests antigos
        cutoff = now - timedelta(seconds=self.time_window)
        self.requests = [req_time for req_time in self.requests if req_time > cutoff]
        
        # Verifica se pode fazer novo request
        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True
            
        return False


# Instância global
whatsapp_api = WhatsAppEnterpriseAPI()