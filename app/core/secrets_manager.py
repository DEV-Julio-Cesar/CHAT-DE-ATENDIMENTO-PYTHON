"""
Gerenciador de Secrets - Abstração para múltiplos provedores
Suporta: AWS Secrets Manager, HashiCorp Vault, Azure Key Vault, Arquivo Local
"""
import os
import json
from typing import Optional, Dict, Any
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class SecretProvider(str, Enum):
    """Provedores de secrets suportados"""
    LOCAL = "local"  # Arquivo .env (desenvolvimento)
    AWS = "aws"  # AWS Secrets Manager
    VAULT = "vault"  # HashiCorp Vault
    AZURE = "azure"  # Azure Key Vault


class SecretsManager:
    """
    Gerenciador centralizado de secrets
    
    Uso:
        secrets = SecretsManager()
        db_password = secrets.get_secret("DATABASE_PASSWORD")
        sgp_token = secrets.get_secret("SGP_TOKEN")
    """
    
    def __init__(self, provider: SecretProvider = SecretProvider.LOCAL):
        self.provider = provider
        self._cache: Dict[str, Any] = {}
        logger.info(f"SecretsManager initialized with provider: {provider}")
    
    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Buscar secret por chave
        
        Args:
            key: Nome do secret
            default: Valor padrão se não encontrado
            
        Returns:
            Valor do secret ou default
        """
        # Verificar cache
        if key in self._cache:
            return self._cache[key]
        
        # Buscar no provedor
        value = None
        
        if self.provider == SecretProvider.LOCAL:
            value = self._get_from_env(key)
        elif self.provider == SecretProvider.AWS:
            value = self._get_from_aws(key)
        elif self.provider == SecretProvider.VAULT:
            value = self._get_from_vault(key)
        elif self.provider == SecretProvider.AZURE:
            value = self._get_from_azure(key)
        
        # Usar default se não encontrado
        if value is None:
            value = default
        
        # Cachear
        if value is not None:
            self._cache[key] = value
        
        return value
    
    def _get_from_env(self, key: str) -> Optional[str]:
        """Buscar em variável de ambiente (.env)"""
        return os.getenv(key)
    
    def _get_from_aws(self, key: str) -> Optional[str]:
        """
        Buscar no AWS Secrets Manager
        
        Requer: boto3
        pip install boto3
        """
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            session = boto3.session.Session()
            client = session.client(
                service_name='secretsmanager',
                region_name=os.getenv('AWS_REGION', 'us-east-1')
            )
            
            try:
                response = client.get_secret_value(SecretId=key)
                
                # Secret pode ser string ou JSON
                if 'SecretString' in response:
                    secret = response['SecretString']
                    try:
                        # Tentar parsear como JSON
                        secret_dict = json.loads(secret)
                        return secret_dict.get(key)
                    except json.JSONDecodeError:
                        # É string simples
                        return secret
                else:
                    # Secret binário
                    return response['SecretBinary'].decode('utf-8')
                    
            except ClientError as e:
                logger.error(f"AWS Secrets Manager error: {e}")
                return None
                
        except ImportError:
            logger.warning("boto3 not installed. Install with: pip install boto3")
            return None
    
    def _get_from_vault(self, key: str) -> Optional[str]:
        """
        Buscar no HashiCorp Vault
        
        Requer: hvac
        pip install hvac
        """
        try:
            import hvac
            
            vault_url = os.getenv('VAULT_ADDR', 'http://localhost:8200')
            vault_token = os.getenv('VAULT_TOKEN')
            
            if not vault_token:
                logger.warning("VAULT_TOKEN not set")
                return None
            
            client = hvac.Client(url=vault_url, token=vault_token)
            
            if not client.is_authenticated():
                logger.error("Vault authentication failed")
                return None
            
            # Buscar secret no path kv/data/app
            secret_path = os.getenv('VAULT_SECRET_PATH', 'kv/data/app')
            response = client.secrets.kv.v2.read_secret_version(path=secret_path)
            
            return response['data']['data'].get(key)
            
        except ImportError:
            logger.warning("hvac not installed. Install with: pip install hvac")
            return None
        except Exception as e:
            logger.error(f"Vault error: {e}")
            return None
    
    def _get_from_azure(self, key: str) -> Optional[str]:
        """
        Buscar no Azure Key Vault
        
        Requer: azure-keyvault-secrets, azure-identity
        pip install azure-keyvault-secrets azure-identity
        """
        try:
            from azure.keyvault.secrets import SecretClient
            from azure.identity import DefaultAzureCredential
            
            vault_url = os.getenv('AZURE_KEYVAULT_URL')
            
            if not vault_url:
                logger.warning("AZURE_KEYVAULT_URL not set")
                return None
            
            credential = DefaultAzureCredential()
            client = SecretClient(vault_url=vault_url, credential=credential)
            
            secret = client.get_secret(key)
            return secret.value
            
        except ImportError:
            logger.warning("Azure SDK not installed. Install with: pip install azure-keyvault-secrets azure-identity")
            return None
        except Exception as e:
            logger.error(f"Azure Key Vault error: {e}")
            return None
    
    def set_secret(self, key: str, value: str) -> bool:
        """
        Definir secret (apenas para desenvolvimento local)
        
        Em produção, use o console do provedor
        """
        if self.provider != SecretProvider.LOCAL:
            logger.warning(f"set_secret not supported for provider: {self.provider}")
            return False
        
        # Atualizar cache
        self._cache[key] = value
        
        # Atualizar .env (apenas desenvolvimento)
        logger.info(f"Secret '{key}' updated in cache (not persisted to .env)")
        return True
    
    def clear_cache(self):
        """Limpar cache de secrets"""
        self._cache.clear()
        logger.info("Secrets cache cleared")


# Instância global
_secrets_manager: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    """
    Obter instância global do SecretsManager
    
    Uso:
        from app.core.secrets_manager import get_secrets_manager
        
        secrets = get_secrets_manager()
        token = secrets.get_secret("SGP_TOKEN")
    """
    global _secrets_manager
    
    if _secrets_manager is None:
        # Determinar provedor baseado em variável de ambiente
        provider_name = os.getenv('SECRETS_PROVIDER', 'local').lower()
        
        try:
            provider = SecretProvider(provider_name)
        except ValueError:
            logger.warning(f"Invalid SECRETS_PROVIDER: {provider_name}, using LOCAL")
            provider = SecretProvider.LOCAL
        
        _secrets_manager = SecretsManager(provider=provider)
    
    return _secrets_manager


# Funções de conveniência
def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """Atalho para buscar secret"""
    return get_secrets_manager().get_secret(key, default)


def set_secret(key: str, value: str) -> bool:
    """Atalho para definir secret (apenas local)"""
    return get_secrets_manager().set_secret(key, value)
