"""
Schemas base para padronização de respostas
"""
from pydantic import BaseModel, Field
from typing import Optional, Generic, TypeVar, Any, Dict, List
from datetime import datetime

T = TypeVar('T')


class ResponseModel(BaseModel, Generic[T]):
    """Modelo padrão de resposta da API"""
    success: bool = Field(..., description="Indica se a operação foi bem-sucedida")
    data: Optional[T] = Field(None, description="Dados da resposta")
    message: Optional[str] = Field(None, description="Mensagem descritiva")
    errors: Optional[List[str]] = Field(None, description="Lista de erros, se houver")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp da resposta")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PaginatedResponse(BaseModel, Generic[T]):
    """Modelo para respostas paginadas"""
    items: List[T] = Field(..., description="Lista de itens")
    total: int = Field(..., description="Total de itens")
    page: int = Field(..., description="Página atual")
    per_page: int = Field(..., description="Itens por página")
    pages: int = Field(..., description="Total de páginas")
    has_prev: bool = Field(..., description="Tem página anterior")
    has_next: bool = Field(..., description="Tem próxima página")


class ErrorResponse(BaseModel):
    """Modelo para respostas de erro"""
    error: Dict[str, Any] = Field(..., description="Detalhes do erro")
    
    class Config:
        schema_extra = {
            "example": {
                "error": {
                    "code": 400,
                    "message": "Bad Request",
                    "details": "Invalid input data",
                    "timestamp": "2024-01-01T00:00:00Z"
                }
            }
        }


class HealthCheckResponse(BaseModel):
    """Modelo para health check"""
    status: str = Field(..., description="Status da aplicação")
    version: str = Field(..., description="Versão da aplicação")
    checks: Dict[str, bool] = Field(..., description="Status dos serviços")
    timestamp: float = Field(..., description="Timestamp do check")


class MetricsResponse(BaseModel):
    """Modelo para métricas"""
    metric_name: str = Field(..., description="Nome da métrica")
    value: float = Field(..., description="Valor da métrica")
    unit: Optional[str] = Field(None, description="Unidade da métrica")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    labels: Optional[Dict[str, str]] = Field(None, description="Labels da métrica")


# Schemas para filtros e ordenação
class FilterBase(BaseModel):
    """Base para filtros de consulta"""
    search: Optional[str] = Field(None, description="Termo de busca")
    date_from: Optional[datetime] = Field(None, description="Data inicial")
    date_to: Optional[datetime] = Field(None, description="Data final")


class SortOrder(str):
    """Enum para ordenação"""
    ASC = "asc"
    DESC = "desc"


class PaginationParams(BaseModel):
    """Parâmetros de paginação"""
    page: int = Field(1, ge=1, description="Número da página")
    per_page: int = Field(20, ge=1, le=100, description="Itens por página")
    sort_by: Optional[str] = Field(None, description="Campo para ordenação")
    sort_order: Optional[SortOrder] = Field(SortOrder.ASC, description="Ordem de classificação")


# Schemas para operações em lote
class BulkOperationRequest(BaseModel):
    """Request para operações em lote"""
    ids: List[str] = Field(..., description="Lista de IDs para operação")
    action: str = Field(..., description="Ação a ser executada")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Parâmetros adicionais")


class BulkOperationResponse(BaseModel):
    """Response para operações em lote"""
    total_requested: int = Field(..., description="Total de itens solicitados")
    successful: int = Field(..., description="Itens processados com sucesso")
    failed: int = Field(..., description="Itens que falharam")
    errors: Optional[List[Dict[str, str]]] = Field(None, description="Detalhes dos erros")


# Schemas para upload de arquivos
class FileUploadResponse(BaseModel):
    """Response para upload de arquivo"""
    filename: str = Field(..., description="Nome do arquivo")
    file_path: str = Field(..., description="Caminho do arquivo")
    file_size: int = Field(..., description="Tamanho do arquivo em bytes")
    content_type: str = Field(..., description="Tipo de conteúdo")
    upload_timestamp: datetime = Field(default_factory=datetime.utcnow)


# Schemas para configurações
class ConfigurationItem(BaseModel):
    """Item de configuração"""
    key: str = Field(..., description="Chave da configuração")
    value: Any = Field(..., description="Valor da configuração")
    description: Optional[str] = Field(None, description="Descrição da configuração")
    category: str = Field("general", description="Categoria da configuração")
    is_sensitive: bool = Field(False, description="Se é um valor sensível")


class ConfigurationUpdate(BaseModel):
    """Atualização de configuração"""
    configurations: List[ConfigurationItem] = Field(..., description="Lista de configurações")


# Schemas para auditoria
class AuditLogEntry(BaseModel):
    """Entrada de log de auditoria"""
    id: str = Field(..., description="ID do log")
    user_id: Optional[str] = Field(None, description="ID do usuário")
    action: str = Field(..., description="Ação executada")
    resource: str = Field(..., description="Recurso afetado")
    resource_id: Optional[str] = Field(None, description="ID do recurso")
    details: Optional[Dict[str, Any]] = Field(None, description="Detalhes da ação")
    ip_address: Optional[str] = Field(None, description="Endereço IP")
    user_agent: Optional[str] = Field(None, description="User agent")
    timestamp: datetime = Field(..., description="Timestamp da ação")


# Schemas para notificações
class NotificationBase(BaseModel):
    """Base para notificações"""
    title: str = Field(..., description="Título da notificação")
    message: str = Field(..., description="Mensagem da notificação")
    type: str = Field("info", description="Tipo da notificação")
    priority: str = Field("normal", description="Prioridade da notificação")


class NotificationCreate(NotificationBase):
    """Criação de notificação"""
    user_ids: Optional[List[str]] = Field(None, description="IDs dos usuários destinatários")
    roles: Optional[List[str]] = Field(None, description="Roles dos destinatários")
    send_email: bool = Field(False, description="Enviar por email")


class NotificationResponse(NotificationBase):
    """Response de notificação"""
    id: str = Field(..., description="ID da notificação")
    read: bool = Field(False, description="Se foi lida")
    created_at: datetime = Field(..., description="Data de criação")
    read_at: Optional[datetime] = Field(None, description="Data de leitura")