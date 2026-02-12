"""
Serviço WhatsApp usando biblioteca Python (pywhatkit)
Integração simples com WhatsApp Web
"""
import pywhatkit as kit
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import asyncio
from pathlib import Path

logger = logging.getLogger(__name__)


class WhatsAppPythonService:
    """Serviço para enviar mensagens via WhatsApp Web usando Python"""
    
    def __init__(self):
        self.initialized = False
        logger.info("WhatsApp Python Service initialized")
    
    async def send_message(
        self,
        phone_number: str,
        message: str,
        wait_time: int = 15,
        close_tab: bool = True
    ) -> Dict[str, Any]:
        """
        Enviar mensagem via WhatsApp Web
        
        Args:
            phone_number: Número com código do país (ex: +5511999999999)
            message: Mensagem a ser enviada
            wait_time: Tempo de espera em segundos antes de enviar
            close_tab: Fechar aba após enviar
            
        Returns:
            Dict com status do envio
        """
        try:
            # Calcular horário de envio (agora + wait_time)
            now = datetime.now() + timedelta(seconds=wait_time)
            hour = now.hour
            minute = now.minute
            
            # Enviar mensagem instantaneamente
            await asyncio.to_thread(
                kit.sendwhatmsg_instantly,
                phone_number,
                message,
                wait_time,
                close_tab
            )
            
            logger.info(f"Mensagem enviada para {phone_number}")
            
            return {
                "success": True,
                "phone_number": phone_number,
                "message": message,
                "sent_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "phone_number": phone_number
            }
    
    async def send_message_scheduled(
        self,
        phone_number: str,
        message: str,
        hour: int,
        minute: int,
        close_tab: bool = True
    ) -> Dict[str, Any]:
        """
        Agendar mensagem para horário específico
        
        Args:
            phone_number: Número com código do país
            message: Mensagem a ser enviada
            hour: Hora do envio (0-23)
            minute: Minuto do envio (0-59)
            close_tab: Fechar aba após enviar
        """
        try:
            await asyncio.to_thread(
                kit.sendwhatmsg,
                phone_number,
                message,
                hour,
                minute,
                close_tab=close_tab
            )
            
            logger.info(f"Mensagem agendada para {phone_number} às {hour}:{minute}")
            
            return {
                "success": True,
                "phone_number": phone_number,
                "scheduled_time": f"{hour:02d}:{minute:02d}",
                "message": message
            }
            
        except Exception as e:
            logger.error(f"Erro ao agendar mensagem: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "phone_number": phone_number
            }
    
    async def send_image(
        self,
        phone_number: str,
        image_path: str,
        caption: Optional[str] = None,
        wait_time: int = 15
    ) -> Dict[str, Any]:
        """
        Enviar imagem via WhatsApp Web
        
        Args:
            phone_number: Número com código do país
            image_path: Caminho da imagem
            caption: Legenda da imagem (opcional)
            wait_time: Tempo de espera em segundos
        """
        try:
            # Verificar se arquivo existe
            if not Path(image_path).exists():
                raise FileNotFoundError(f"Imagem não encontrada: {image_path}")
            
            await asyncio.to_thread(
                kit.sendwhats_image,
                phone_number,
                image_path,
                caption or "",
                wait_time
            )
            
            logger.info(f"Imagem enviada para {phone_number}")
            
            return {
                "success": True,
                "phone_number": phone_number,
                "image_path": image_path,
                "caption": caption,
                "sent_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erro ao enviar imagem: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "phone_number": phone_number
            }
    
    async def send_bulk_messages(
        self,
        contacts: list[Dict[str, str]],
        wait_time: int = 15
    ) -> Dict[str, Any]:
        """
        Enviar mensagens em massa
        
        Args:
            contacts: Lista de dicts com 'phone' e 'message'
            wait_time: Tempo de espera entre mensagens
            
        Returns:
            Dict com estatísticas do envio
        """
        results = {
            "total": len(contacts),
            "success": 0,
            "failed": 0,
            "errors": []
        }
        
        for contact in contacts:
            phone = contact.get("phone")
            message = contact.get("message")
            
            if not phone or not message:
                results["failed"] += 1
                results["errors"].append({
                    "phone": phone,
                    "error": "Phone or message missing"
                })
                continue
            
            result = await self.send_message(phone, message, wait_time)
            
            if result["success"]:
                results["success"] += 1
            else:
                results["failed"] += 1
                results["errors"].append({
                    "phone": phone,
                    "error": result.get("error")
                })
            
            # Aguardar entre mensagens para evitar bloqueio
            await asyncio.sleep(5)
        
        logger.info(f"Envio em massa concluído: {results['success']}/{results['total']} sucesso")
        
        return results
    
    def get_status(self) -> Dict[str, Any]:
        """Retornar status do serviço"""
        return {
            "service": "WhatsApp Python (pywhatkit)",
            "status": "active",
            "type": "whatsapp_web",
            "features": [
                "send_message",
                "send_scheduled",
                "send_image",
                "send_bulk"
            ],
            "requirements": [
                "WhatsApp Web deve estar logado no navegador",
                "Navegador Chrome deve estar instalado"
            ]
        }


# Instância global
whatsapp_service = WhatsAppPythonService()
