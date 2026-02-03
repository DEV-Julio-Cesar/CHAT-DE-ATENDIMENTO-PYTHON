"""
Endpoints de Exportação de Relatórios PDF
CIANET PROVEDOR - v3.0

Endpoints para geração de relatórios:
- GET /reports/v2/daily - Relatório diário
- GET /reports/v2/conversation/{id} - Extrato de conversa
- GET /reports/v2/satisfaction - Relatório de satisfação
- GET /reports/v2/agent/{id} - Relatório individual do atendente
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, List
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.dependencies import get_current_user
from app.services.pdf_export import pdf_generator, REPORTLAB_AVAILABLE
from app.core.sqlserver_db import sqlserver_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports/v2", tags=["Relatórios PDF V2"])


# ============================================================================
# SCHEMAS
# ============================================================================

class DailyReportRequest(BaseModel):
    """Parâmetros para relatório diário"""
    date: Optional[str] = Field(None, description="Data no formato YYYY-MM-DD (padrão: hoje)")


class SatisfactionReportRequest(BaseModel):
    """Parâmetros para relatório de satisfação"""
    start_date: str = Field(..., description="Data inicial (YYYY-MM-DD)")
    end_date: str = Field(..., description="Data final (YYYY-MM-DD)")


class ReportResponse(BaseModel):
    """Resposta com informações do relatório"""
    success: bool
    filename: str
    size_bytes: int
    generated_at: datetime


# ============================================================================
# HELPERS
# ============================================================================

def check_reportlab():
    """Verificar se ReportLab está disponível"""
    if not REPORTLAB_AVAILABLE or not pdf_generator:
        raise HTTPException(
            status_code=503,
            detail="Serviço de geração de PDF não disponível. Instale ReportLab: pip install reportlab"
        )


def parse_date(date_str: str, default_delta: int = 0) -> datetime:
    """Converter string para datetime"""
    if not date_str:
        return datetime.now() + timedelta(days=default_delta)
    
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Data inválida: {date_str}. Use formato YYYY-MM-DD"
        )


# ============================================================================
# ENDPOINTS - RELATÓRIOS
# ============================================================================

@router.get(
    "/daily",
    summary="Relatório diário de atendimentos",
    description="Gera PDF com resumo de atendimentos do dia"
)
async def get_daily_report(
    date: Optional[str] = Query(None, description="Data (YYYY-MM-DD). Padrão: hoje"),
    current_user: dict = Depends(get_current_user)
):
    """
    Gerar relatório diário.
    
    Inclui:
    - Métricas de atendimento
    - Gráfico por hora
    - Categorias
    - Performance dos atendentes
    """
    check_reportlab()
    
    # Validar role (apenas supervisor/admin)
    if current_user.get('role') not in ['supervisor', 'admin']:
        raise HTTPException(
            status_code=403,
            detail="Apenas supervisores e administradores podem gerar este relatório"
        )
    
    report_date = parse_date(date)
    
    try:
        pdf_bytes = pdf_generator.generate_daily_report(date=report_date)
        
        filename = f"relatorio_diario_{report_date.strftime('%Y%m%d')}.pdf"
        
        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(pdf_bytes))
            }
        )
        
    except Exception as e:
        logger.error(f"Erro ao gerar relatório diário: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar relatório: {str(e)}"
        )


@router.get(
    "/conversation/{conversation_id}",
    summary="Extrato de conversa",
    description="Gera PDF com histórico completo da conversa"
)
async def get_conversation_report(
    conversation_id: int,
    current_user: dict = Depends(get_current_user)
):
    """
    Gerar extrato de conversa.
    
    Inclui:
    - Dados do cliente
    - Dados do atendente
    - Histórico de mensagens
    - Avaliação
    """
    check_reportlab()
    
    # Verificar se conversa existe
    conversation = sqlserver_manager.get_conversation(conversation_id)
    
    if not conversation:
        raise HTTPException(
            status_code=404,
            detail=f"Conversa {conversation_id} não encontrada"
        )
    
    # Verificar permissão (própria conversa ou supervisor)
    user_role = current_user.get('role')
    user_id = current_user.get('user_id')
    
    if user_role not in ['supervisor', 'admin']:
        if conversation.get('attendant_id') != user_id:
            raise HTTPException(
                status_code=403,
                detail="Sem permissão para acessar esta conversa"
            )
    
    try:
        pdf_bytes = pdf_generator.generate_conversation_report(
            conversation_id=conversation_id
        )
        
        filename = f"conversa_{conversation_id}.pdf"
        
        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(pdf_bytes))
            }
        )
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Erro ao gerar extrato: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar extrato: {str(e)}"
        )


@router.get(
    "/satisfaction",
    summary="Relatório de satisfação",
    description="Gera PDF com métricas de satisfação do cliente"
)
async def get_satisfaction_report(
    start_date: str = Query(..., description="Data inicial (YYYY-MM-DD)"),
    end_date: str = Query(..., description="Data final (YYYY-MM-DD)"),
    current_user: dict = Depends(get_current_user)
):
    """
    Gerar relatório de satisfação.
    
    Inclui:
    - Distribuição de avaliações
    - NPS
    - Métricas gerais
    """
    check_reportlab()
    
    # Validar role
    if current_user.get('role') not in ['supervisor', 'admin']:
        raise HTTPException(
            status_code=403,
            detail="Apenas supervisores e administradores podem gerar este relatório"
        )
    
    start = parse_date(start_date)
    end = parse_date(end_date)
    
    if start > end:
        raise HTTPException(
            status_code=400,
            detail="Data inicial deve ser anterior à data final"
        )
    
    try:
        pdf_bytes = pdf_generator.generate_satisfaction_report(
            start_date=start,
            end_date=end
        )
        
        filename = f"satisfacao_{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}.pdf"
        
        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(pdf_bytes))
            }
        )
        
    except Exception as e:
        logger.error(f"Erro ao gerar relatório: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar relatório: {str(e)}"
        )


@router.get(
    "/weekly",
    summary="Relatório semanal",
    description="Gera PDF com resumo semanal de atendimentos"
)
async def get_weekly_report(
    week_start: Optional[str] = Query(None, description="Início da semana (YYYY-MM-DD). Padrão: segunda passada"),
    current_user: dict = Depends(get_current_user)
):
    """
    Gerar relatório semanal.
    """
    check_reportlab()
    
    if current_user.get('role') not in ['supervisor', 'admin']:
        raise HTTPException(
            status_code=403,
            detail="Apenas supervisores e administradores podem gerar este relatório"
        )
    
    # Calcular início da semana
    if week_start:
        start = parse_date(week_start)
    else:
        today = datetime.now()
        start = today - timedelta(days=today.weekday())  # Segunda
    
    end = start + timedelta(days=6)  # Domingo
    
    try:
        pdf_bytes = pdf_generator.generate_satisfaction_report(
            start_date=start,
            end_date=end
        )
        
        filename = f"semanal_{start.strftime('%Y%m%d')}.pdf"
        
        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(pdf_bytes))
            }
        )
        
    except Exception as e:
        logger.error(f"Erro ao gerar relatório: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar relatório: {str(e)}"
        )


# ============================================================================
# ENDPOINTS - STATUS
# ============================================================================

@router.get(
    "/status",
    summary="Status do serviço de relatórios"
)
async def get_reports_status():
    """Verificar status do serviço de geração de PDF"""
    return {
        "service": "pdf_reports",
        "reportlab_available": REPORTLAB_AVAILABLE,
        "generator_ready": pdf_generator is not None,
        "available_reports": [
            "daily",
            "conversation",
            "satisfaction",
            "weekly"
        ]
    }


@router.get(
    "/templates",
    summary="Listar templates disponíveis"
)
async def list_report_templates(
    current_user: dict = Depends(get_current_user)
):
    """Listar templates de relatórios disponíveis"""
    return {
        "templates": [
            {
                "id": "daily",
                "name": "Relatório Diário",
                "description": "Resumo de atendimentos do dia com métricas e gráficos",
                "endpoint": "/reports/v2/daily",
                "required_role": ["supervisor", "admin"],
                "parameters": [
                    {"name": "date", "type": "string", "format": "YYYY-MM-DD", "required": False}
                ]
            },
            {
                "id": "conversation",
                "name": "Extrato de Conversa",
                "description": "Histórico completo de uma conversa específica",
                "endpoint": "/reports/v2/conversation/{id}",
                "required_role": ["atendente", "supervisor", "admin"],
                "parameters": [
                    {"name": "conversation_id", "type": "integer", "required": True}
                ]
            },
            {
                "id": "satisfaction",
                "name": "Relatório de Satisfação",
                "description": "Análise de avaliações e NPS",
                "endpoint": "/reports/v2/satisfaction",
                "required_role": ["supervisor", "admin"],
                "parameters": [
                    {"name": "start_date", "type": "string", "format": "YYYY-MM-DD", "required": True},
                    {"name": "end_date", "type": "string", "format": "YYYY-MM-DD", "required": True}
                ]
            },
            {
                "id": "weekly",
                "name": "Relatório Semanal",
                "description": "Resumo semanal de atendimentos",
                "endpoint": "/reports/v2/weekly",
                "required_role": ["supervisor", "admin"],
                "parameters": [
                    {"name": "week_start", "type": "string", "format": "YYYY-MM-DD", "required": False}
                ]
            }
        ]
    }
