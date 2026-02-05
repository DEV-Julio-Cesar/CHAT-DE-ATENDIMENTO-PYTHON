"""
Exportação de Relatórios em PDF
CIANET PROVEDOR - v3.0

Geração de relatórios profissionais:
- Relatório diário de atendimentos
- Relatório de performance por atendente
- Relatório de satisfação do cliente
- Extrato de conversa individual
"""
import logging
import io
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

# ReportLab para geração de PDF
from reportlab.graphics.shapes import Drawing

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm, cm, inch
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
        Image, PageBreak, HRFlowable
    )
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.charts.piecharts import Pie
    from reportlab.graphics.charts.lineplots import LinePlot
    from reportlab.graphics.widgets.markers import makeMarker
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

from app.core.config import settings
from app.core.database import db_manager
from app.models.database import Conversa, Mensagem
from sqlalchemy import select
import asyncio

logger = logging.getLogger(__name__)


# ============================================================================
# ESTILOS
# ============================================================================

def get_styles():
    """Obter estilos para o PDF"""
    styles = getSampleStyleSheet()
    
    # Título principal
    styles.add(ParagraphStyle(
        name='MainTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#22c55e'),  # Verde CIANET
        alignment=TA_CENTER,
        spaceAfter=20
    ))
    
    # Subtítulo
    styles.add(ParagraphStyle(
        name='SubTitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#374151'),
        alignment=TA_CENTER,
        spaceAfter=10
    ))
    
    # Seção
    styles.add(ParagraphStyle(
        name='SectionTitle',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#f97316'),  # Laranja CIANET
        spaceBefore=20,
        spaceAfter=10
    ))
    
    # Texto normal customizado (evita conflito com BodyText existente)
    styles.add(ParagraphStyle(
        name='CustomBodyText',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#374151'),
        spaceAfter=6
    ))
    
    # Texto destacado
    styles.add(ParagraphStyle(
        name='Highlight',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#22c55e'),
        fontName='Helvetica-Bold'
    ))
    
    # Rodapé
    styles.add(ParagraphStyle(
        name='FooterText',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#9ca3af'),
        alignment=TA_CENTER
    ))
    
    return styles


# ============================================================================
# COMPONENTES DE GRÁFICOS
# ============================================================================

def create_bar_chart(data: List[tuple], width: float = 400, height: float = 200) -> Drawing:
    """Criar gráfico de barras"""
    drawing = Drawing(width, height)
    
    chart = VerticalBarChart()
    chart.x = 50
    chart.y = 30
    chart.width = width - 80
    chart.height = height - 60
    
    # Dados
    values = [d[1] for d in data]
    chart.data = [values]
    
    # Categorias
    chart.categoryAxis.categoryNames = [d[0] for d in data]
    chart.categoryAxis.labels.angle = 45
    chart.categoryAxis.labels.boxAnchor = 'e'
    
    # Estilo
    chart.bars[0].fillColor = colors.HexColor('#22c55e')
    chart.valueAxis.valueMin = 0
    
    drawing.add(chart)
    return drawing


def create_pie_chart(data: List[tuple], width: float = 250, height: float = 200) -> Drawing:
    """Criar gráfico de pizza"""
    drawing = Drawing(width, height)
    
    pie = Pie()
    pie.x = width / 2 - 60
    pie.y = height / 2 - 60
    pie.width = 120
    pie.height = 120
    
    # Dados
    pie.data = [d[1] for d in data]
    pie.labels = [f"{d[0]}: {d[1]}" for d in data]
    
    # Cores
    pie.slices.strokeWidth = 0.5
    pie_colors = [
        colors.HexColor('#22c55e'),
        colors.HexColor('#f97316'),
        colors.HexColor('#3b82f6'),
        colors.HexColor('#8b5cf6'),
        colors.HexColor('#ef4444')
    ]
    
    for i, _ in enumerate(data):
        pie.slices[i].fillColor = pie_colors[i % len(pie_colors)]
    
    drawing.add(pie)
    return drawing


# ============================================================================
# GERADOR DE RELATÓRIOS
# ============================================================================

class PDFReportGenerator:
    """Gerador de relatórios PDF"""
    
    def __init__(self):
        if not REPORTLAB_AVAILABLE:
            raise ImportError("ReportLab não está instalado. Execute: pip install reportlab")
        
        self.styles = get_styles()
        self.company_name = getattr(settings, 'CHATBOT_COMPANY_NAME', 'CIANET PROVEDOR')
    
    def _create_header(self, title: str, subtitle: str = None) -> List:
        """Criar cabeçalho do relatório"""
        elements = []
        
        # Logo (se existir)
        # logo_path = "app/static/logo.png"
        # if os.path.exists(logo_path):
        #     elements.append(Image(logo_path, width=100, height=50))
        
        # Título
        elements.append(Paragraph(self.company_name, self.styles['MainTitle']))
        elements.append(Paragraph(title, self.styles['SubTitle']))
        
        if subtitle:
            elements.append(Paragraph(subtitle, self.styles['CustomBodyText']))
        
        # Data de geração
        elements.append(Paragraph(
            f"Gerado em: {datetime.now().strftime('%d/%m/%Y às %H:%M')}",
            self.styles['FooterText']
        ))
        
        elements.append(Spacer(1, 20))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e5e7eb')))
        elements.append(Spacer(1, 20))
        
        return elements
    
    def _create_table(
        self, 
        data: List[List], 
        col_widths: List[float] = None,
        header_color: str = '#22c55e'
    ) -> Table:
        """Criar tabela estilizada"""
        table = Table(data, colWidths=col_widths)
        
        style = TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(header_color)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            
            # Body
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            
            # Alternating rows
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
        ])
        
        table.setStyle(style)
        return table
    
    def generate_daily_report(
        self, 
        date: datetime = None,
        output_path: str = None
    ) -> bytes:
        """
        Gerar relatório diário de atendimentos.
        
        Inclui:
        - Resumo de métricas
        - Gráfico de atendimentos por hora
        - Top categorias
        - Performance por atendente
        """
        if date is None:
            date = datetime.now()
        
        date_str = date.strftime('%Y-%m-%d')
        
        # Buscar dados
        metrics = self._get_daily_metrics(date_str)
        hourly = self._get_hourly_data(date_str)
        categories = self._get_category_data(date_str)
        agents = self._get_agent_performance(date_str)
        
        # Criar PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        elements = []
        
        # Header
        elements.extend(self._create_header(
            "Relatório Diário de Atendimentos",
            date.strftime('%d/%m/%Y')
        ))
        
        # Resumo de métricas
        elements.append(Paragraph("📊 Resumo do Dia", self.styles['SectionTitle']))
        
        metrics_data = [
            ['Métrica', 'Valor'],
            ['Total de Atendimentos', str(metrics.get('total', 0))],
            ['Atendimentos Resolvidos', str(metrics.get('resolved', 0))],
            ['Em Fila', str(metrics.get('waiting', 0))],
            ['Em Andamento', str(metrics.get('in_progress', 0))],
            ['Tempo Médio de Resposta', f"{metrics.get('avg_response', 0):.1f} min"],
            ['Tempo Médio de Resolução', f"{metrics.get('avg_resolution', 0):.1f} min"],
            ['Satisfação Média', f"{metrics.get('avg_rating', 0):.1f} ⭐"],
        ]
        
        elements.append(self._create_table(metrics_data, col_widths=[200, 200]))
        elements.append(Spacer(1, 20))
        
        # Gráfico por hora
        if hourly:
            elements.append(Paragraph("📈 Atendimentos por Hora", self.styles['SectionTitle']))
            elements.append(create_bar_chart(hourly))
            elements.append(Spacer(1, 20))
        
        # Categorias
        if categories:
            elements.append(Paragraph("📁 Por Categoria", self.styles['SectionTitle']))
            elements.append(create_pie_chart(categories))
            elements.append(Spacer(1, 20))
        
        # Performance dos atendentes
        if agents:
            elements.append(Paragraph("👥 Performance dos Atendentes", self.styles['SectionTitle']))
            
            agent_data = [['Atendente', 'Total', 'Resolvidos', 'Média Rating']]
            for agent in agents:
                agent_data.append([
                    agent.get('name', 'N/A'),
                    str(agent.get('total', 0)),
                    str(agent.get('resolved', 0)),
                    f"{agent.get('avg_rating', 0):.1f}" if agent.get('avg_rating') else '-'
                ])
            
            elements.append(self._create_table(agent_data, col_widths=[150, 80, 80, 90]))
        
        # Gerar
        doc.build(elements)
        
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        # Salvar em arquivo se especificado
        if output_path:
            with open(output_path, 'wb') as f:
                f.write(pdf_bytes)
        
        return pdf_bytes
    
    def generate_conversation_report(
        self, 
        conversation_id: int,
        output_path: str = None
    ) -> bytes:
        """
        Gerar extrato de conversa individual.
        
        Inclui:
        - Dados do cliente
        - Dados do atendente
        - Histórico de mensagens
        - Avaliação
        """
        # Buscar conversa
        conversation = asyncio.run(get_conversation_by_id(conversation_id))
        
        if not conversation:
            raise ValueError(f"Conversa {conversation_id} não encontrada")
        
        # Buscar mensagens
        messages = asyncio.run(list_messages(conversation_id, limit=500))
        
        # Criar PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        elements = []
        
        # Header
        elements.extend(self._create_header(
            f"Extrato de Atendimento #{conversation_id}",
            f"Protocolo: CIANET-{conversation_id:06d}"
        ))
        
        # Dados da conversa
        elements.append(Paragraph("📋 Informações do Atendimento", self.styles['SectionTitle']))
        
        info_data = [
            ['Campo', 'Valor'],
            ['Cliente', conversation.client_name or 'N/A'],
            ['Telefone', conversation.client_phone or 'N/A'],
            ['Atendente', conversation.attendant_name or 'Bot/Fila'],
            ['Status', conversation.status or 'N/A'],
            ['Prioridade', conversation.priority or 'normal'],
            ['Categoria', conversation.category or 'N/A'],
            ['Início', str(conversation.started_at or 'N/A')],
            ['Resolução', str(conversation.resolved_at or 'N/A') if conversation.resolved_at else 'Não resolvido'],
            ['Avaliação', f"{conversation.rating or '-'} ⭐" if conversation.rating else 'Não avaliado'],
        ]
        
        elements.append(self._create_table(info_data, col_widths=[150, 250]))
        elements.append(Spacer(1, 20))
        
        # Histórico de mensagens
        elements.append(Paragraph("💬 Histórico de Mensagens", self.styles['SectionTitle']))
        
        for msg in messages:
            sender = "👤 Cliente" if msg.sender_type == 'client' else "🤖 Bot" if msg.sender_type == 'bot' else "👨‍💼 Atendente"
            timestamp = msg.created_at
            content = msg.content
            
            # Estilo diferente para cliente vs sistema
            if msg.sender_type == 'client':
                style = ParagraphStyle(
                    'ClientMsg',
                    parent=self.styles['CustomBodyText'],
                    leftIndent=0,
                    backgroundColor=colors.HexColor('#f3f4f6'),
                    borderPadding=5
                )
            else:
                style = ParagraphStyle(
                    'SystemMsg',
                    parent=self.styles['CustomBodyText'],
                    leftIndent=30,
                    backgroundColor=colors.HexColor('#dcfce7'),
                    borderPadding=5
                )
            
            elements.append(Paragraph(f"<b>{sender}</b> - {timestamp}", self.styles['FooterText']))
            elements.append(Paragraph(content, style))
            elements.append(Spacer(1, 5))
        
        # Gerar
        doc.build(elements)
        
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        if output_path:
            with open(output_path, 'wb') as f:
                f.write(pdf_bytes)
        
        return pdf_bytes
    
    def generate_satisfaction_report(
        self, 
        start_date: datetime,
        end_date: datetime,
        output_path: str = None
    ) -> bytes:
        """
        Gerar relatório de satisfação do cliente.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        
        elements = []
        
        # Header
        elements.extend(self._create_header(
            "Relatório de Satisfação do Cliente",
            f"{start_date.strftime('%d/%m/%Y')} a {end_date.strftime('%d/%m/%Y')}"
        ))
        
        # Métricas de satisfação
        satisfaction = self._get_satisfaction_data(start_date, end_date)
        
        elements.append(Paragraph("⭐ Distribuição de Avaliações", self.styles['SectionTitle']))
        
        if satisfaction.get('distribution'):
            dist_data = [
                (f"{k} estrela(s)", v) 
                for k, v in satisfaction['distribution'].items()
            ]
            elements.append(create_pie_chart(dist_data))
        
        elements.append(Spacer(1, 20))
        
        # Métricas gerais
        elements.append(Paragraph("📊 Métricas", self.styles['SectionTitle']))
        
        metrics_data = [
            ['Métrica', 'Valor'],
            ['Total de Avaliações', str(satisfaction.get('total', 0))],
            ['Média Geral', f"{satisfaction.get('avg', 0):.2f} ⭐"],
            ['NPS (Net Promoter Score)', f"{satisfaction.get('nps', 0):.0f}"],
            ['% Promotores (4-5)', f"{satisfaction.get('promoters_pct', 0):.1f}%"],
            ['% Detratores (1-2)', f"{satisfaction.get('detractors_pct', 0):.1f}%"],
        ]
        
        elements.append(self._create_table(metrics_data))
        
        # Gerar
        doc.build(elements)
        
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        if output_path:
            with open(output_path, 'wb') as f:
                f.write(pdf_bytes)
        
        return pdf_bytes
    
    # =========================================================================
    # DATA FETCHING
    # =========================================================================
    
    async def _get_daily_metrics_async(self, date_str: str) -> Dict[str, Any]:
        """Buscar métricas do dia (MariaDB/MySQL)"""
        try:
            async with db_manager.session_factory() as session:
                from sqlalchemy import func, cast, Date
                from app.models.database import Conversa
                date = datetime.strptime(date_str, "%Y-%m-%d").date()
                total = await session.execute(
                    select(func.count()).select_from(Conversa).where(cast(Conversa.created_at, Date) == date)
                )
                resolved = await session.execute(
                    select(func.count()).select_from(Conversa).where(cast(Conversa.created_at, Date) == date, Conversa.estado == 'encerrado')
                )
                waiting = await session.execute(
                    select(func.count()).select_from(Conversa).where(cast(Conversa.created_at, Date) == date, Conversa.estado == 'espera')
                )
                in_progress = await session.execute(
                    select(func.count()).select_from(Conversa).where(cast(Conversa.created_at, Date) == date, Conversa.estado == 'atendimento')
                )
                # As médias podem ser adaptadas conforme os campos disponíveis
                return {
                    'total': total.scalar() or 0,
                    'resolved': resolved.scalar() or 0,
                    'waiting': waiting.scalar() or 0,
                    'in_progress': in_progress.scalar() or 0,
                    'avg_response': 0.0,  # Adapte se houver campos de tempo
                    'avg_resolution': 0.0,
                    'avg_rating': 0.0
                }
        except Exception as e:
            logger.error(f"Erro ao buscar métricas: {e}")
            return {}
    
    def _get_daily_metrics(self, date_str: str) -> Dict[str, Any]:
        """Buscar métricas do dia (MariaDB/MySQL)"""
        return asyncio.run(self._get_daily_metrics_async(date_str))

    def _get_hourly_data(self, date_str: str) -> List[tuple]:
        """Buscar dados por hora (MariaDB/MySQL)"""
        # Implemente consulta async semelhante usando SQLAlchemy
        return []

    def _get_category_data(self, date_str: str) -> List[tuple]:
        """Buscar dados por categoria (MariaDB/MySQL)"""
        # Implemente consulta async semelhante usando SQLAlchemy
        return []

    def _get_agent_performance(self, date_str: str) -> List[Dict]:
        """Buscar performance dos atendentes (MariaDB/MySQL)"""
        # Implemente consulta async semelhante usando SQLAlchemy
        return []

    def _get_satisfaction_data(self, start_date: datetime, end_date: datetime) -> Dict:
        """Buscar dados de satisfação (MariaDB/MySQL)"""
        # Implemente consulta async semelhante usando SQLAlchemy
        return {}


# Helper para buscar conversa por ID
async def get_conversation_by_id(conversation_id):
    async with db_manager.session_factory() as session:
        result = await session.execute(select(Conversa).where(Conversa.id == conversation_id))
        return result.scalar_one_or_none()

# Helper para listar mensagens de uma conversa
async def list_messages(conversation_id, limit=500):
    async with db_manager.session_factory() as session:
        result = await session.execute(
            select(Mensagem).where(Mensagem.conversa_id == conversation_id).limit(limit)
        )
        return result.scalars().all()


# Instância singleton
pdf_generator = PDFReportGenerator() if REPORTLAB_AVAILABLE else None
