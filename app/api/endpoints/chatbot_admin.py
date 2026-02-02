"""
API de Administração do Chatbot Treinável
Endpoints para gerenciar intents, FAQ e configurações
"""
from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.services.chatbot_trainable import get_chatbot, TrainableChatbot
# from app.core.security import get_current_admin_user  # TODO: Habilitar autenticação

router = APIRouter(prefix="/chatbot", tags=["Chatbot Admin"])


# =============================================================================
# SCHEMAS
# =============================================================================

class IntentCreate(BaseModel):
    """Schema para criar novo intent"""
    intent_id: str = Field(..., description="ID único do intent (ex: 'promocao_verao')")
    name: str = Field(..., description="Nome amigável (ex: 'Promoção de Verão')")
    patterns: List[str] = Field(..., description="Lista de frases que ativam este intent")
    responses: List[str] = Field(..., description="Lista de respostas possíveis")
    category: str = Field(default="geral", description="Categoria: geral, suporte_tecnico, financeiro, comercial")
    tags: Optional[List[str]] = Field(default=None, description="Tags para organização")
    
    class Config:
        json_schema_extra = {
            "example": {
                "intent_id": "promocao_verao",
                "name": "Promoção de Verão",
                "patterns": ["promoção", "desconto", "oferta especial", "promoção de verão"],
                "responses": ["🌞 Aproveite nossa promoção de verão! 50% de desconto nos 3 primeiros meses. Quer saber mais?"],
                "category": "comercial",
                "tags": ["promocao", "vendas", "verao"]
            }
        }


class PatternAdd(BaseModel):
    """Schema para adicionar padrão"""
    pattern: str = Field(..., description="Nova frase para reconhecimento")
    
    class Config:
        json_schema_extra = {
            "example": {
                "pattern": "tem alguma promoção?"
            }
        }


class ResponseAdd(BaseModel):
    """Schema para adicionar resposta"""
    response: str = Field(..., description="Nova resposta para o intent")
    
    class Config:
        json_schema_extra = {
            "example": {
                "response": "Sim! Temos várias promoções. Qual plano você gostaria de conhecer?"
            }
        }


class FAQCreate(BaseModel):
    """Schema para criar FAQ"""
    question: str = Field(..., description="Pergunta frequente")
    answer: str = Field(..., description="Resposta para a pergunta")
    category: str = Field(default="geral", description="Categoria da FAQ")
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "Como faço para ver meu consumo de dados?",
                "answer": "Você pode verificar seu consumo no app ou acessando portal.empresa.com.br com seu CPF.",
                "category": "suporte_tecnico"
            }
        }


class ConfigUpdate(BaseModel):
    """Schema para atualizar configuração"""
    key: str = Field(..., description="Nome da configuração")
    value: str = Field(..., description="Novo valor")
    
    class Config:
        json_schema_extra = {
            "example": {
                "key": "company_name",
                "value": "MinhaEmpresaTelecom"
            }
        }


class ChatMessage(BaseModel):
    """Schema para testar mensagem"""
    message: str = Field(..., description="Mensagem para testar")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "minha internet está muito lenta"
            }
        }


class QuickReplyUpdate(BaseModel):
    """Schema para atualizar quick replies"""
    category: str = Field(..., description="Categoria do quick reply")
    replies: List[str] = Field(..., description="Lista de respostas rápidas")
    
    class Config:
        json_schema_extra = {
            "example": {
                "category": "menu_principal",
                "replies": ["💰 Boleto", "🔧 Suporte", "📦 Planos", "🙋 Atendente"]
            }
        }


# =============================================================================
# ENDPOINTS - INTENTS
# =============================================================================

@router.get("/intents", summary="Listar todos os intents")
async def list_intents(chatbot: TrainableChatbot = Depends(get_chatbot)):
    """
    Lista todos os intents cadastrados no chatbot.
    Útil para visualizar o que o bot reconhece.
    """
    intents = chatbot.get_all_intents()
    return {
        "total": len(intents),
        "intents": intents
    }


@router.get("/intents/{intent_id}", summary="Obter intent específico")
async def get_intent(intent_id: str, chatbot: TrainableChatbot = Depends(get_chatbot)):
    """Obter detalhes de um intent específico"""
    for intent in chatbot.get_all_intents():
        if intent["id"] == intent_id:
            return intent
    raise HTTPException(status_code=404, detail=f"Intent '{intent_id}' não encontrado")


@router.post("/intents", summary="Criar novo intent")
async def create_intent(
    data: IntentCreate,
    chatbot: TrainableChatbot = Depends(get_chatbot)
):
    """
    Criar novo intent (intenção) para o chatbot reconhecer.
    
    - **intent_id**: Identificador único (snake_case recomendado)
    - **patterns**: Frases que ativam este intent
    - **responses**: Respostas que o bot pode dar
    """
    result = chatbot.add_intent(
        intent_id=data.intent_id,
        name=data.name,
        patterns=data.patterns,
        responses=data.responses,
        category=data.category,
        tags=data.tags
    )
    return result


@router.post("/intents/{intent_id}/patterns", summary="Adicionar padrão ao intent")
async def add_pattern_to_intent(
    intent_id: str,
    data: PatternAdd,
    chatbot: TrainableChatbot = Depends(get_chatbot)
):
    """Adicionar nova frase de reconhecimento a um intent existente"""
    result = chatbot.add_pattern(intent_id, data.pattern)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])
    return result


@router.post("/intents/{intent_id}/responses", summary="Adicionar resposta ao intent")
async def add_response_to_intent(
    intent_id: str,
    data: ResponseAdd,
    chatbot: TrainableChatbot = Depends(get_chatbot)
):
    """Adicionar nova resposta a um intent existente"""
    result = chatbot.add_response(intent_id, data.response)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])
    return result


@router.delete("/intents/{intent_id}", summary="Remover intent")
async def delete_intent(
    intent_id: str,
    chatbot: TrainableChatbot = Depends(get_chatbot)
):
    """Remover um intent da base de conhecimento"""
    result = chatbot.remove_intent(intent_id)
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])
    return result


# =============================================================================
# ENDPOINTS - FAQ
# =============================================================================

@router.get("/faq", summary="Listar todas as FAQs")
async def list_faq(chatbot: TrainableChatbot = Depends(get_chatbot)):
    """Lista todas as perguntas frequentes"""
    faqs = chatbot.get_all_faq()
    return {
        "total": len(faqs),
        "faq": faqs
    }


@router.post("/faq", summary="Adicionar FAQ")
async def create_faq(
    data: FAQCreate,
    chatbot: TrainableChatbot = Depends(get_chatbot)
):
    """Adicionar nova pergunta frequente"""
    result = chatbot.add_faq(
        question=data.question,
        answer=data.answer,
        category=data.category
    )
    return result


# =============================================================================
# ENDPOINTS - CONFIGURAÇÃO
# =============================================================================

@router.get("/config", summary="Obter configurações")
async def get_config(chatbot: TrainableChatbot = Depends(get_chatbot)):
    """Obter configurações do chatbot"""
    return chatbot.get_config()


@router.put("/config", summary="Atualizar configuração")
async def update_config(
    data: ConfigUpdate,
    chatbot: TrainableChatbot = Depends(get_chatbot)
):
    """
    Atualizar configuração do chatbot.
    
    Configurações disponíveis:
    - company_name: Nome da empresa
    - welcome_message: Mensagem de boas-vindas
    - fallback_message: Mensagem quando não entende
    - transfer_message: Mensagem ao transferir
    - goodbye_message: Mensagem de despedida
    - business_hours: Horário de funcionamento
    """
    result = chatbot.update_config(data.key, data.value)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.put("/quick-replies", summary="Atualizar quick replies")
async def update_quick_replies(
    data: QuickReplyUpdate,
    chatbot: TrainableChatbot = Depends(get_chatbot)
):
    """Atualizar botões de resposta rápida"""
    chatbot.knowledge_base["quick_replies"][data.category] = data.replies
    chatbot._save_knowledge()
    return {"success": True, "message": f"Quick replies '{data.category}' atualizados"}


# =============================================================================
# ENDPOINTS - TESTE E ESTATÍSTICAS
# =============================================================================

@router.post("/test", summary="Testar resposta do chatbot")
async def test_chatbot(
    data: ChatMessage,
    chatbot: TrainableChatbot = Depends(get_chatbot)
):
    """
    Testar como o chatbot responderia a uma mensagem.
    Útil para verificar se os intents estão funcionando corretamente.
    """
    response = chatbot.get_response(data.message)
    return {
        "input": data.message,
        "output": response
    }


@router.get("/stats", summary="Estatísticas de uso")
async def get_stats(chatbot: TrainableChatbot = Depends(get_chatbot)):
    """
    Obter estatísticas de uso do chatbot.
    Inclui taxa de acerto e perguntas não respondidas.
    """
    return chatbot.get_stats()


@router.get("/unmatched", summary="Perguntas não respondidas")
async def get_unmatched(chatbot: TrainableChatbot = Depends(get_chatbot)):
    """
    Obter lista de perguntas que o chatbot não conseguiu responder.
    Use para identificar novos intents que precisam ser criados.
    """
    unmatched = chatbot.get_unmatched_queries()
    return {
        "total": len(unmatched),
        "queries": unmatched
    }


# =============================================================================
# ENDPOINTS - IMPORT/EXPORT
# =============================================================================

@router.get("/export", summary="Exportar base de conhecimento")
async def export_knowledge(chatbot: TrainableChatbot = Depends(get_chatbot)):
    """Exportar toda a base de conhecimento em JSON"""
    return chatbot.export_knowledge()


@router.post("/import", summary="Importar base de conhecimento")
async def import_knowledge(
    data: Dict[str, Any] = Body(...),
    chatbot: TrainableChatbot = Depends(get_chatbot)
):
    """Importar base de conhecimento de JSON"""
    result = chatbot.import_knowledge(data)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


# =============================================================================
# ENDPOINT - CATEGORIAS
# =============================================================================

@router.get("/categories", summary="Listar categorias")
async def get_categories(chatbot: TrainableChatbot = Depends(get_chatbot)):
    """Obter lista de categorias utilizadas"""
    categories = set()
    for intent in chatbot.get_all_intents():
        categories.add(intent.get("category", "geral"))
    for faq in chatbot.get_all_faq():
        categories.add(faq.get("category", "geral"))
    
    return {
        "categories": sorted(list(categories)),
        "suggested": ["geral", "suporte_tecnico", "financeiro", "comercial", "reclamacao"]
    }
