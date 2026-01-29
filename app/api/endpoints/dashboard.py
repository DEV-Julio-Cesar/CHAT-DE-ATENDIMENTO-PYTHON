"""
Dashboard API para ISP - Métricas em tempo real
Dashboard executivo para provedores de internet
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import asyncio
from app.core.monitoring import monitoring
from app.services.whatsapp_enterprise import whatsapp_api
from app.core.redis_client import redis_manager
from app.core.database import db_manager
from app.api.endpoints.auth import get_current_user
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview")
async def get_dashboard_overview(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Visão geral do dashboard em tempo real
    Métricas principais para ISP com 10k clientes
    """
    try:
        # Dados do monitoramento
        dashboard_data = await monitoring.get_real_time_dashboard()
        
        # Métricas de WhatsApp
        whatsapp_analytics = await whatsapp_api.get_analytics(
            start_date=datetime.utcnow() - timedelta(days=1),
            end_date=datetime.utcnow()
        )
        
        # Métricas de atendimento
        support_metrics = await _get_support_metrics()
        
        # Métricas financeiras
        financial_metrics = await _get_financial_metrics()
        
        # KPIs principais
        kpis = {
            'total_customers': 10000,  # Configurável
            'active_conversations': dashboard_data.get('summary', {}).get('active_conversations', 0),
            'agents_online': dashboard_data.get('summary', {}).get('agents_online', 0),
            'system_uptime': dashboard_data.get('summary', {}).get('system_uptime', '99.9%'),
            'response_time_avg': support_metrics.get('avg_response_time', 0),
            'resolution_rate': support_metrics.get('resolution_rate', 0),
            'customer_satisfaction': support_metrics.get('satisfaction_score', 0),
            'revenue_today': financial_metrics.get('revenue_today', 0),
            'churn_rate': financial_metrics.get('churn_rate', 0)
        }
        
        # Alertas ativos
        active_alerts = dashboard_data.get('active_alerts', [])
        
        # Tendências
        trends = await _calculate_business_trends()
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'kpis': kpis,
            'system_health': dashboard_data.get('health_status', {}),
            'whatsapp_metrics': whatsapp_analytics.get('metrics', {}),
            'support_metrics': support_metrics,
            'financial_metrics': financial_metrics,
            'active_alerts': active_alerts,
            'trends': trends,
            'performance': {
                'cpu_usage': dashboard_data.get('system_metrics', {}).get('cpu_percent', 0),
                'memory_usage': dashboard_data.get('system_metrics', {}).get('memory_percent', 0),
                'disk_usage': dashboard_data.get('system_metrics', {}).get('disk_percent', 0),
                'active_connections': dashboard_data.get('system_metrics', {}).get('active_connections', 0)
            }
        }
        
    except Exception as e:
        logger.error("Error getting dashboard overview", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/real-time")
async def get_real_time_metrics(
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Métricas em tempo real para gráficos"""
    try:
        # Últimas métricas do sistema
        system_metrics = await redis_manager.get('system_metrics:latest')
        business_metrics = await redis_manager.get('business_metrics:latest')
        
        # Métricas de WhatsApp em tempo real
        whatsapp_health = await redis_manager.get('whatsapp:health')
        
        # Conversas ativas por canal
        active_conversations = await _get_active_conversations_by_channel()
        
        # Fila de atendimento
        queue_metrics = await _get_queue_metrics()
        
        # Performance da aplicação
        app_performance = await _get_app_performance()
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'system': json.loads(system_metrics) if system_metrics else {},
            'business': json.loads(business_metrics) if business_metrics else {},
            'whatsapp_health': whatsapp_health,
            'conversations': active_conversations,
            'queue': queue_metrics,
            'performance': app_performance
        }
        
    except Exception as e:
        logger.error("Error getting real-time metrics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/support")
async def get_support_analytics(
    period: str = Query("24h", description="Período: 1h, 24h, 7d, 30d"),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Analytics detalhado de suporte"""
    try:
        # Calcula período
        end_date = datetime.utcnow()
        if period == "1h":
            start_date = end_date - timedelta(hours=1)
        elif period == "24h":
            start_date = end_date - timedelta(days=1)
        elif period == "7d":
            start_date = end_date - timedelta(days=7)
        elif period == "30d":
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=1)
            
        # Métricas de tickets
        ticket_metrics = await _get_ticket_analytics(start_date, end_date)
        
        # Métricas de agentes
        agent_metrics = await _get_agent_analytics(start_date, end_date)
        
        # Métricas de canais
        channel_metrics = await _get_channel_analytics(start_date, end_date)
        
        # Satisfação do cliente
        satisfaction_metrics = await _get_satisfaction_analytics(start_date, end_date)
        
        # Análise de sentimento
        sentiment_analysis = await _get_sentiment_analysis(start_date, end_date)
        
        return {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'duration': period
            },
            'tickets': ticket_metrics,
            'agents': agent_metrics,
            'channels': channel_metrics,
            'satisfaction': satisfaction_metrics,
            'sentiment': sentiment_analysis,
            'summary': {
                'total_interactions': ticket_metrics.get('total_created', 0),
                'resolution_rate': ticket_metrics.get('resolution_rate', 0),
                'avg_response_time': ticket_metrics.get('avg_response_time', 0),
                'customer_satisfaction': satisfaction_metrics.get('average_score', 0),
                'agent_productivity': agent_metrics.get('avg_productivity', 0)
            }
        }
        
    except Exception as e:
        logger.error("Error getting support analytics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/whatsapp")
async def get_whatsapp_analytics(
    period: str = Query("24h", description="Período: 1h, 24h, 7d, 30d"),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Analytics detalhado do WhatsApp"""
    try:
        # Calcula período
        end_date = datetime.utcnow()
        if period == "1h":
            start_date = end_date - timedelta(hours=1)
        elif period == "24h":
            start_date = end_date - timedelta(days=1)
        elif period == "7d":
            start_date = end_date - timedelta(days=7)
        elif period == "30d":
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=1)
            
        # Analytics da API WhatsApp
        whatsapp_analytics = await whatsapp_api.get_analytics(start_date, end_date)
        
        # Métricas de sessões
        session_metrics = await _get_whatsapp_session_metrics(start_date, end_date)
        
        # Análise de conteúdo
        content_analysis = await _get_whatsapp_content_analysis(start_date, end_date)
        
        # Performance por horário
        hourly_performance = await _get_whatsapp_hourly_performance(start_date, end_date)
        
        # Top conversas
        top_conversations = await _get_top_whatsapp_conversations(start_date, end_date)
        
        return {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'duration': period
            },
            'api_metrics': whatsapp_analytics.get('metrics', {}),
            'sessions': session_metrics,
            'content': content_analysis,
            'hourly_performance': hourly_performance,
            'top_conversations': top_conversations,
            'trends': whatsapp_analytics.get('trends', {}),
            'summary': {
                'total_messages': whatsapp_analytics.get('metrics', {}).get('messages_sent', 0),
                'delivery_rate': whatsapp_analytics.get('metrics', {}).get('delivery_rate', 0),
                'read_rate': whatsapp_analytics.get('metrics', {}).get('read_rate', 0),
                'active_sessions': session_metrics.get('active_count', 0),
                'avg_response_time': session_metrics.get('avg_response_time', 0)
            }
        }
        
    except Exception as e:
        logger.error("Error getting WhatsApp analytics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analytics/financial")
async def get_financial_analytics(
    period: str = Query("30d", description="Período: 7d, 30d, 90d, 1y"),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Analytics financeiro do ISP"""
    try:
        # Calcula período
        end_date = datetime.utcnow()
        if period == "7d":
            start_date = end_date - timedelta(days=7)
        elif period == "30d":
            start_date = end_date - timedelta(days=30)
        elif period == "90d":
            start_date = end_date - timedelta(days=90)
        elif period == "1y":
            start_date = end_date - timedelta(days=365)
        else:
            start_date = end_date - timedelta(days=30)
            
        # Métricas de receita
        revenue_metrics = await _get_revenue_metrics(start_date, end_date)
        
        # Análise de churn
        churn_analysis = await _get_churn_analysis(start_date, end_date)
        
        # Customer Lifetime Value
        clv_metrics = await _get_clv_metrics(start_date, end_date)
        
        # ROI do suporte
        support_roi = await _get_support_roi(start_date, end_date)
        
        # Previsões
        forecasts = await _get_financial_forecasts()
        
        return {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'duration': period
            },
            'revenue': revenue_metrics,
            'churn': churn_analysis,
            'clv': clv_metrics,
            'support_roi': support_roi,
            'forecasts': forecasts,
            'summary': {
                'total_revenue': revenue_metrics.get('total', 0),
                'revenue_growth': revenue_metrics.get('growth_rate', 0),
                'churn_rate': churn_analysis.get('rate', 0),
                'avg_clv': clv_metrics.get('average', 0),
                'support_cost_per_ticket': support_roi.get('cost_per_ticket', 0)
            }
        }
        
    except Exception as e:
        logger.error("Error getting financial analytics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stream/metrics")
async def stream_real_time_metrics(
    current_user: dict = Depends(get_current_user)
):
    """Stream de métricas em tempo real via Server-Sent Events"""
    
    async def generate_metrics():
        """Gerador de métricas em tempo real"""
        while True:
            try:
                # Obtém métricas atuais
                metrics = await get_real_time_metrics(current_user)
                
                # Formata como Server-Sent Event
                yield f"data: {json.dumps(metrics)}\n\n"
                
                # Aguarda 5 segundos
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error("Error streaming metrics", error=str(e))
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                break
                
    return StreamingResponse(
        generate_metrics(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )


@router.get("/alerts")
async def get_active_alerts(
    severity: Optional[str] = Query(None, description="Filtrar por severidade"),
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Lista alertas ativos do sistema"""
    try:
        # Obtém alertas do Redis
        alerts_data = await redis_manager.get('system:alerts:active')
        alerts = json.loads(alerts_data) if alerts_data else []
        
        # Filtra por severidade se especificado
        if severity:
            alerts = [alert for alert in alerts if alert.get('severity') == severity]
            
        # Ordena por timestamp (mais recentes primeiro)
        alerts.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # Estatísticas
        stats = {
            'total': len(alerts),
            'critical': len([a for a in alerts if a.get('severity') == 'critical']),
            'warning': len([a for a in alerts if a.get('severity') == 'warning']),
            'info': len([a for a in alerts if a.get('severity') == 'info'])
        }
        
        return {
            'alerts': alerts,
            'statistics': stats,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Error getting alerts", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Reconhece um alerta"""
    try:
        # Obtém alertas atuais
        alerts_data = await redis_manager.get('system:alerts:active')
        alerts = json.loads(alerts_data) if alerts_data else []
        
        # Encontra e atualiza o alerta
        alert_found = False
        for alert in alerts:
            if alert.get('id') == alert_id:
                alert['acknowledged'] = True
                alert['acknowledged_by'] = current_user.get('username')
                alert['acknowledged_at'] = datetime.utcnow().isoformat()
                alert_found = True
                break
                
        if not alert_found:
            raise HTTPException(status_code=404, detail="Alert not found")
            
        # Salva alertas atualizados
        await redis_manager.set('system:alerts:active', json.dumps(alerts))
        
        logger.info(
            "Alert acknowledged",
            alert_id=alert_id,
            user=current_user.get('username')
        )
        
        return {
            'success': True,
            'message': 'Alert acknowledged successfully'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error acknowledging alert", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Funções auxiliares
async def _get_support_metrics() -> Dict[str, Any]:
    """Obtém métricas de suporte"""
    # Implementar queries no banco de dados
    return {
        'avg_response_time': 125.5,  # segundos
        'resolution_rate': 87.3,    # percentual
        'satisfaction_score': 4.2,  # 1-5
        'tickets_open': 45,
        'tickets_resolved_today': 38,
        'agents_active': 8
    }


async def _get_financial_metrics() -> Dict[str, Any]:
    """Obtém métricas financeiras"""
    return {
        'revenue_today': 25000.00,
        'revenue_month': 750000.00,
        'churn_rate': 2.1,  # percentual
        'avg_clv': 1200.00,  # Customer Lifetime Value
        'cost_per_acquisition': 150.00
    }


async def _calculate_business_trends() -> Dict[str, Any]:
    """Calcula tendências de negócio"""
    return {
        'customer_growth': 'increasing',
        'satisfaction_trend': 'stable',
        'revenue_trend': 'increasing',
        'churn_trend': 'decreasing',
        'support_efficiency': 'improving'
    }


async def _get_active_conversations_by_channel() -> Dict[str, int]:
    """Conversas ativas por canal"""
    return {
        'whatsapp': 125,
        'email': 45,
        'phone': 23,
        'chat': 67,
        'social': 12
    }


async def _get_queue_metrics() -> Dict[str, Any]:
    """Métricas da fila de atendimento"""
    return {
        'waiting_count': 15,
        'avg_wait_time': 180,  # segundos
        'longest_wait': 450,   # segundos
        'queue_trend': 'decreasing'
    }


async def _get_app_performance() -> Dict[str, Any]:
    """Performance da aplicação"""
    return {
        'response_time_p95': 0.25,  # segundos
        'error_rate': 0.1,          # percentual
        'throughput': 1250,         # requests/min
        'database_query_time': 0.05 # segundos
    }


# Implementar outras funções auxiliares conforme necessário
async def _get_ticket_analytics(start_date: datetime, end_date: datetime) -> Dict[str, Any]:
    """Analytics de tickets"""
    return {'total_created': 150, 'resolution_rate': 85.5, 'avg_response_time': 120}


async def _get_agent_analytics(start_date: datetime, end_date: datetime) -> Dict[str, Any]:
    """Analytics de agentes"""
    return {'avg_productivity': 25.5, 'total_agents': 10, 'active_agents': 8}


async def _get_channel_analytics(start_date: datetime, end_date: datetime) -> Dict[str, Any]:
    """Analytics por canal"""
    return {'whatsapp': 60, 'email': 25, 'phone': 10, 'chat': 5}


async def _get_satisfaction_analytics(start_date: datetime, end_date: datetime) -> Dict[str, Any]:
    """Analytics de satisfação"""
    return {'average_score': 4.2, 'total_responses': 85, 'nps': 45}


async def _get_sentiment_analysis(start_date: datetime, end_date: datetime) -> Dict[str, Any]:
    """Análise de sentimento"""
    return {'positive': 65, 'neutral': 25, 'negative': 10}


async def _get_whatsapp_session_metrics(start_date: datetime, end_date: datetime) -> Dict[str, Any]:
    """Métricas de sessões WhatsApp"""
    return {'active_count': 3, 'avg_response_time': 95.5}


async def _get_whatsapp_content_analysis(start_date: datetime, end_date: datetime) -> Dict[str, Any]:
    """Análise de conteúdo WhatsApp"""
    return {'text': 80, 'image': 15, 'document': 3, 'audio': 2}


async def _get_whatsapp_hourly_performance(start_date: datetime, end_date: datetime) -> List[Dict]:
    """Performance por hora"""
    return [{'hour': i, 'messages': 50 + i * 5} for i in range(24)]


async def _get_top_whatsapp_conversations(start_date: datetime, end_date: datetime) -> List[Dict]:
    """Top conversas"""
    return [{'contact': f'Contact {i}', 'messages': 100 - i * 10} for i in range(5)]


async def _get_revenue_metrics(start_date: datetime, end_date: datetime) -> Dict[str, Any]:
    """Métricas de receita"""
    return {'total': 750000, 'growth_rate': 5.2}


async def _get_churn_analysis(start_date: datetime, end_date: datetime) -> Dict[str, Any]:
    """Análise de churn"""
    return {'rate': 2.1, 'trend': 'decreasing'}


async def _get_clv_metrics(start_date: datetime, end_date: datetime) -> Dict[str, Any]:
    """Métricas de CLV"""
    return {'average': 1200, 'median': 950}


async def _get_support_roi(start_date: datetime, end_date: datetime) -> Dict[str, Any]:
    """ROI do suporte"""
    return {'cost_per_ticket': 25.50, 'roi': 450}


async def _get_financial_forecasts() -> Dict[str, Any]:
    """Previsões financeiras"""
    return {'revenue_next_month': 800000, 'churn_forecast': 1.8}