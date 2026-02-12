"""
Serviço para gerar QR Code do WhatsApp Web
Integração com serviço Node.js (whatsapp-web.js)
"""
import httpx
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# URL do serviço Node.js
WHATSAPP_SERVICE_URL = "http://localhost:3001"


class WhatsAppWebQRService:
    """Serviço para gerar QR Code do WhatsApp Web via Node.js"""
    
    def __init__(self, service_url: str = WHATSAPP_SERVICE_URL):
        self.service_url = service_url
        self.timeout = 30.0
    
    async def check_service_status(self) -> Dict[str, Any]:
        """Verificar se o serviço Node.js está rodando"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.service_url}/status")
                return response.json()
        except httpx.ConnectError:
            logger.error("Serviço WhatsApp não está rodando")
            return {
                "success": False,
                "error": "Serviço WhatsApp não está rodando. Execute 'npm start' na pasta whatsapp-service"
            }
        except Exception as e:
            logger.error(f"Erro ao verificar status: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def generate_qr_code(self, session_id: str = None) -> Dict[str, Any]:
        """
        Gerar QR Code para WhatsApp Web
        
        Args:
            session_id: ID da sessão (não usado, mantido para compatibilidade)
            
        Returns:
            Dict com QR Code em base64 e informações da sessão
        """
        try:
            # Verificar se o serviço está rodando
            status = await self.check_service_status()
            if not status.get("success"):
                return status
            
            # Obter QR Code do serviço Node.js
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.service_url}/qr-code")
                data = response.json()
                
                if not data.get("success"):
                    return data
                
                # Se já está conectado
                if data.get("connected"):
                    return {
                        "success": True,
                        "connected": True,
                        "message": data.get("message"),
                        "client_info": data.get("clientInfo")
                    }
                
                # Retornar QR Code
                return {
                    "success": True,
                    "qr_code": data.get("qr_code"),
                    "message": data.get("message", "Escaneie o QR Code com seu WhatsApp"),
                    "session_id": "whatsapp-web-session"
                }
                
        except httpx.ConnectError:
            logger.error("Serviço WhatsApp não está rodando")
            return {
                "success": False,
                "error": "Serviço WhatsApp não está rodando. Execute 'npm start' na pasta whatsapp-service"
            }
        except Exception as e:
            logger.error(f"Erro ao gerar QR Code: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_session_status(self, session_id: str = None) -> Dict[str, Any]:
        """Verificar status da sessão WhatsApp"""
        return await self.check_service_status()
    
    async def send_message(self, phone: str, message: str) -> Dict[str, Any]:
        """
        Enviar mensagem via WhatsApp
        
        Args:
            phone: Número com código do país (ex: 5511999999999)
            message: Mensagem a ser enviada
            
        Returns:
            Dict com resultado do envio
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.service_url}/send-message",
                    json={"phone": phone, "message": message}
                )
                return response.json()
                
        except httpx.ConnectError:
            return {
                "success": False,
                "error": "Serviço WhatsApp não está rodando"
            }
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def disconnect(self) -> Dict[str, Any]:
        """Desconectar WhatsApp"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.service_url}/disconnect")
                return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def reconnect(self) -> Dict[str, Any]:
        """Reconectar WhatsApp (gera novo QR Code)"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.service_url}/reconnect")
                return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}


# Instância global
whatsapp_qr_service = WhatsAppWebQRService()
