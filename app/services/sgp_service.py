import requests
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class SGPService:
    def __init__(self):
        self.base_url = settings.SGP_BASE_URL 
        self.token = settings.SGP_TOKEN
        self.app = settings.SGP_APP_NAME
        self.username = settings.SGP_USERNAME
        self.password = settings.SGP_PASSWORD
        self.headers = {
            "Content-Type": "application/json"
        }

    def buscar_cliente_por_cpf(self, cpf):
        """Identifica o cliente e retorna seu status e ID"""
        from app.core.validators import validar_cpf, formatar_cpf
        
        try:
            # Validar CPF
            if not validar_cpf(cpf):
                logger.warning(f"CPF inválido fornecido")
                return None
            
            # Formatar CPF
            cpf_formatado = formatar_cpf(cpf)
            if not cpf_formatado:
                return None
            
            # Payload JSON com usuário e senha
            # IMPORTANTE: Nunca logar credenciais
            payload = {
                "app": self.app,
                "token": self.token,
                "usuario": self.username,
                "senha": self.password,
                "cpfcnpj": cpf_formatado
            }
            
            logger.info(f"Buscando cliente no SGP: CPF={cpf_formatado[:7]}***")
            
            # POST request com timeout
            response = requests.post(
                self.base_url, 
                json=payload, 
                headers=self.headers,
                timeout=30  # Timeout de 30 segundos
            )
            data = response.json()

            # A resposta vem em formato: {"clientes": [...]}
            if data and "clientes" in data and len(data["clientes"]) > 0:
                cliente = data["clientes"][0]
                
                # Pegar status do primeiro contrato
                status = "Desconhecido"
                if cliente.get("contratos") and len(cliente["contratos"]) > 0:
                    status = cliente["contratos"][0].get("status", "Desconhecido")
                
                return {
                    "id": cliente.get("id"),
                    "nome": cliente.get("nome"),
                    "cpf_cnpj": cliente.get("cpfcnpj"),
                    "status": status,  # Ativo, Bloqueado, Suspenso, etc
                    "situacao": cliente.get("tipo"),  # Pessoa Física/Jurídica
                    "contratos": cliente.get("contratos", []),
                    "titulos": cliente.get("titulos", []),
                    "contatos": cliente.get("contatos", {})
                }
            return None
        except Exception as e:
            logger.error(f"Erro ao buscar cliente no SGP: {e}")
            return None

    def obter_faturas_abertas(self, cliente_id):
        """Puxa boletos pendentes - já vem na busca do cliente"""
        try:
            # Na API do SGP, os títulos já vêm junto com o cliente
            # Então vamos buscar o cliente novamente para pegar os títulos atualizados
            # Ou você pode passar os títulos diretamente do contexto
            
            # Por enquanto, retorna vazio pois os títulos já vêm na busca
            # Você pode implementar uma busca específica se a API tiver endpoint separado
            logger.info(f"Faturas já vêm na busca do cliente. Use os dados do contexto.")
            return []
        except Exception as e:
            logger.error(f"Erro ao buscar faturas: {e}")
            return []

    def realizar_promessa_pagamento(self, cliente_id):
        """Libera a internet por confiança"""
        try:
            # NUNCA colocar token na URL (fica em logs)
            # Usar header Authorization
            url = f"{self.base_url}/{cliente_id}/liberar_confianca"
            headers = {
                **self.headers,
                "Authorization": f"Bearer {self.token}"
            }
            
            response = requests.post(
                url, 
                headers=headers,
                timeout=30
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Erro na promessa de pagamento: {e}")
            return False