#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Serviços de IA
Implementa integração com provedores de IA, análise de sentimento e respostas automáticas
"""

import asyncio
import logging
import time
import json
import re
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import selectinload

import aiohttp
from shared.config.settings import settings
from shared.utils.memory_cache import memory_cache

from .models import (
    AIModel, AIRequest, SentimentAnalysis, AutoResponse,
    AIProvider, AIModelType, SentimentType, ResponseType, AIRequestStatus,
    AIRequestCreate, AIRequestResponse, SentimentAnalysisCreate, SentimentAnalysisResponse,
    AutoResponseCreate, AutoResponseResponse, ChatCompletionRequest, ChatCompletionResponse,
    SuggestedResponse
)

logger = logging.getLogger(__name__)

class AIServiceError(Exception):
    """Erro base do AI Service"""
    pass

class ModelNotFoundError(AIServiceError):
    """Modelo não encontrado"""
    pass

class ProviderError(AIServiceError):
    """Erro do provedor de IA"""
    pass

class RateLimitError(AIServiceError):
    """Rate limit excedido"""
    pass

class AIService:
    """
    Serviço principal de IA
    Gerencia modelos, requisições e análises
    """
    
    def __init__(self):
        self.cache_ttl = 300  # 5 minutos
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Configurações dos provedores
        self.providers_config = {
            AIProvider.OPENAI: {
                "base_url": "https://api.openai.com/v1",
                "headers": {
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                }
            },
            AIProvider.GEMINI: {
                "base_url": "https://generativelanguage.googleapis.com/v1beta",
                "headers": {
                    "Content-Type": "application/json"
                }
            }
        }
    
    async def start(self):
        """Inicializar AI Service"""
        logger.info("🚀 Iniciando AI Service...")
        
        # Criar sessão HTTP
        connector = aiohttp.TCPConnector(limit=50, limit_per_host=20)
        timeout = aiohttp.ClientTimeout(total=60, connect=10)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout
        )
        
        logger.info("✅ AI Service iniciado")
    
    async def stop(self):
        """Parar AI Service"""
        if self.session:
            await self.session.close()
        logger.info("✅ AI Service parado")
    
    # === GERENCIAMENTO DE MODELOS ===
    
    async def create_model(self, db: AsyncSession, model_data: Dict[str, Any]) -> AIModel:
        """Criar novo modelo de IA"""
        try:
            # Verificar se já existe
            existing = await db.execute(
                select(AIModel).where(AIModel.name == model_data["name"])
            )
            if existing.scalar_one_or_none():
                raise AIServiceError(f"Modelo {model_data['name']} já existe")
            
            # Criar modelo
            model = AIModel(**model_data)
            db.add(model)
            await db.commit()
            await db.refresh(model)
            
            logger.info(f"Modelo de IA criado: {model.name}")
            return model
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Erro ao criar modelo: {e}")
            raise AIServiceError(f"Erro ao criar modelo: {e}")
    
    async def get_model_by_name(self, db: AsyncSession, name: str) -> Optional[AIModel]:
        """Obter modelo por nome"""
        try:
            result = await db.execute(
                select(AIModel).where(and_(
                    AIModel.name == name,
                    AIModel.is_active == True
                ))
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Erro ao obter modelo {name}: {e}")
            return None
    
    async def get_default_model(self, db: AsyncSession, model_type: AIModelType) -> Optional[AIModel]:
        """Obter modelo padrão por tipo"""
        try:
            result = await db.execute(
                select(AIModel).where(and_(
                    AIModel.model_type == model_type.value,
                    AIModel.is_active == True,
                    AIModel.is_default == True
                )).order_by(AIModel.priority.desc())
            )
            model = result.scalar_one_or_none()
            
            if not model:
                # Fallback: primeiro modelo ativo do tipo
                result = await db.execute(
                    select(AIModel).where(and_(
                        AIModel.model_type == model_type.value,
                        AIModel.is_active == True
                    )).order_by(AIModel.priority.desc())
                )
                model = result.scalar_one_or_none()
            
            return model
        except Exception as e:
            logger.error(f"Erro ao obter modelo padrão: {e}")
            return None
    
    # === CHAT COMPLETION ===
    
    async def chat_completion(
        self, 
        db: AsyncSession, 
        request: ChatCompletionRequest,
        user_id: Optional[str] = None
    ) -> ChatCompletionResponse:
        """Gerar resposta de chat usando IA"""
        start_time = time.time()
        
        try:
            # Obter modelo
            if request.model_name:
                model = await self.get_model_by_name(db, request.model_name)
            else:
                model = await self.get_default_model(db, AIModelType.CHAT)
            
            if not model:
                raise ModelNotFoundError("Nenhum modelo de chat disponível")
            
            # Verificar rate limit
            await self._check_rate_limit(db, model, user_id)
            
            # Preparar contexto
            context = await self._build_conversation_context(db, request.conversation_id)
            
            # Fazer requisição para o provedor
            response_text, tokens_used, cost = await self._call_provider(
                model, request, context
            )
            
            # Registrar requisição
            ai_request = await self._create_ai_request(
                db, model, request.message, response_text, 
                tokens_used, cost, time.time() - start_time,
                request.conversation_id, user_id
            )
            
            return ChatCompletionResponse(
                response=response_text,
                model_used=model.name,
                tokens_used=tokens_used,
                processing_time=time.time() - start_time,
                cost=cost,
                request_id=str(ai_request.id)
            )
            
        except (ModelNotFoundError, RateLimitError, ProviderError):
            raise
        except Exception as e:
            logger.error(f"Erro no chat completion: {e}")
            raise AIServiceError(f"Erro no chat completion: {e}")
    
    async def _call_provider(
        self, 
        model: AIModel, 
        request: ChatCompletionRequest, 
        context: Optional[str] = None
    ) -> Tuple[str, int, Optional[float]]:
        """Fazer chamada para o provedor de IA"""
        provider = AIProvider(model.provider)
        
        if provider == AIProvider.OPENAI:
            return await self._call_openai(model, request, context)
        elif provider == AIProvider.GEMINI:
            return await self._call_gemini(model, request, context)
        else:
            raise ProviderError(f"Provedor {provider} não suportado")
    
    async def _call_openai(
        self, 
        model: AIModel, 
        request: ChatCompletionRequest, 
        context: Optional[str] = None
    ) -> Tuple[str, int, Optional[float]]:
        """Chamada para OpenAI"""
        try:
            if not settings.OPENAI_API_KEY:
                raise ProviderError("OPENAI_API_KEY não configurada")
            
            # Preparar mensagens
            messages = []
            
            if request.system_prompt:
                messages.append({"role": "system", "content": request.system_prompt})
            elif context:
                messages.append({"role": "system", "content": f"Contexto da conversa: {context}"})
            
            messages.append({"role": "user", "content": request.message})
            
            # Preparar payload
            payload = {
                "model": model.model_id,
                "messages": messages,
                "max_tokens": request.max_tokens or model.max_tokens,
                "temperature": request.temperature or model.temperature,
                "top_p": model.top_p,
                "frequency_penalty": model.frequency_penalty,
                "presence_penalty": model.presence_penalty
            }
            
            # Fazer requisição
            config = self.providers_config[AIProvider.OPENAI]
            async with self.session.post(
                f"{config['base_url']}/chat/completions",
                headers=config["headers"],
                json=payload
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    raise ProviderError(f"OpenAI API error: {response.status} - {error_text}")
                
                data = await response.json()
                
                # Extrair resposta
                response_text = data["choices"][0]["message"]["content"]
                tokens_used = data["usage"]["total_tokens"]
                cost = None
                
                if model.cost_per_token:
                    cost = tokens_used * model.cost_per_token
                
                return response_text, tokens_used, cost
                
        except aiohttp.ClientError as e:
            raise ProviderError(f"Erro de conexão OpenAI: {e}")
        except Exception as e:
            raise ProviderError(f"Erro OpenAI: {e}")
    
    async def _call_gemini(
        self, 
        model: AIModel, 
        request: ChatCompletionRequest, 
        context: Optional[str] = None
    ) -> Tuple[str, int, Optional[float]]:
        """Chamada para Google Gemini"""
        try:
            if not settings.GEMINI_API_KEY:
                raise ProviderError("GEMINI_API_KEY não configurada")
            
            # Preparar prompt
            prompt = request.message
            if context:
                prompt = f"Contexto: {context}\n\nUsuário: {request.message}"
            
            # Preparar payload
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": request.temperature or model.temperature,
                    "topP": model.top_p,
                    "maxOutputTokens": request.max_tokens or model.max_tokens
                }
            }
            
            # Fazer requisição
            config = self.providers_config[AIProvider.GEMINI]
            url = f"{config['base_url']}/models/{model.model_id}:generateContent?key={settings.GEMINI_API_KEY}"
            
            async with self.session.post(
                url,
                headers=config["headers"],
                json=payload
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    raise ProviderError(f"Gemini API error: {response.status} - {error_text}")
                
                data = await response.json()
                
                # Extrair resposta
                response_text = data["candidates"][0]["content"]["parts"][0]["text"]
                tokens_used = data.get("usageMetadata", {}).get("totalTokenCount", 0)
                cost = None
                
                if model.cost_per_token:
                    cost = tokens_used * model.cost_per_token
                
                return response_text, tokens_used, cost
                
        except aiohttp.ClientError as e:
            raise ProviderError(f"Erro de conexão Gemini: {e}")
        except Exception as e:
            raise ProviderError(f"Erro Gemini: {e}")
    
    # === ANÁLISE DE SENTIMENTO ===
    
    async def analyze_sentiment(
        self, 
        db: AsyncSession, 
        request: SentimentAnalysisCreate
    ) -> SentimentAnalysisResponse:
        """Analisar sentimento de texto"""
        try:
            # Verificar cache
            cache_key = f"sentiment:{hash(request.text)}"
            cached = await memory_cache.get(cache_key)
            if cached:
                return SentimentAnalysisResponse.model_validate(cached)
            
            # Análise simples baseada em palavras-chave (pode ser substituída por IA)
            sentiment_result = await self._analyze_text_sentiment(request.text)
            
            # Salvar no banco
            analysis = SentimentAnalysis(
                conversation_id=request.conversation_id,
                message_id=request.message_id,
                text=request.text,
                sentiment=sentiment_result["sentiment"],
                confidence=sentiment_result["confidence"],
                positive_score=sentiment_result["positive_score"],
                negative_score=sentiment_result["negative_score"],
                neutral_score=sentiment_result["neutral_score"],
                language=sentiment_result.get("language"),
                keywords=sentiment_result.get("keywords"),
                emotions=sentiment_result.get("emotions")
            )
            
            db.add(analysis)
            await db.commit()
            await db.refresh(analysis)
            
            response = self._sentiment_to_response(analysis)
            
            # Cachear resultado
            await memory_cache.set(cache_key, response.model_dump(), ttl=self.cache_ttl)
            
            return response
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Erro na análise de sentimento: {e}")
            raise AIServiceError(f"Erro na análise de sentimento: {e}")
    
    async def _analyze_text_sentiment(self, text: str) -> Dict[str, Any]:
        """Análise de sentimento baseada em palavras-chave"""
        # Palavras-chave para sentimentos (versão simplificada)
        positive_words = [
            "obrigado", "obrigada", "excelente", "ótimo", "bom", "perfeito",
            "maravilhoso", "fantástico", "adorei", "amei", "satisfeito",
            "feliz", "contente", "grato", "grata", "parabéns"
        ]
        
        negative_words = [
            "ruim", "péssimo", "horrível", "terrível", "odiei", "detestei",
            "insatisfeito", "decepcionado", "frustrado", "irritado", "raiva",
            "problema", "erro", "falha", "defeito", "reclamação", "cancelar"
        ]
        
        neutral_words = [
            "ok", "normal", "regular", "comum", "padrão", "médio",
            "informação", "dúvida", "pergunta", "como", "quando", "onde"
        ]
        
        text_lower = text.lower()
        
        # Contar ocorrências
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        neutral_count = sum(1 for word in neutral_words if word in text_lower)
        
        total_count = positive_count + negative_count + neutral_count
        
        if total_count == 0:
            # Sem palavras-chave identificadas - assumir neutro
            return {
                "sentiment": SentimentType.NEUTRAL.value,
                "confidence": 0.5,
                "positive_score": 0.33,
                "negative_score": 0.33,
                "neutral_score": 0.34,
                "language": "pt",
                "keywords": [],
                "emotions": {}
            }
        
        # Calcular scores
        positive_score = positive_count / total_count
        negative_score = negative_count / total_count
        neutral_score = neutral_count / total_count
        
        # Determinar sentimento dominante
        if positive_score > negative_score and positive_score > neutral_score:
            sentiment = SentimentType.POSITIVE.value
            confidence = positive_score
        elif negative_score > positive_score and negative_score > neutral_score:
            sentiment = SentimentType.NEGATIVE.value
            confidence = negative_score
        else:
            sentiment = SentimentType.NEUTRAL.value
            confidence = neutral_score
        
        # Extrair palavras-chave encontradas
        found_keywords = []
        for word in positive_words + negative_words + neutral_words:
            if word in text_lower:
                found_keywords.append(word)
        
        return {
            "sentiment": sentiment,
            "confidence": min(confidence + 0.3, 1.0),  # Boost confidence
            "positive_score": positive_score,
            "negative_score": negative_score,
            "neutral_score": neutral_score,
            "language": "pt",
            "keywords": found_keywords[:10],  # Limitar a 10
            "emotions": {
                "joy": positive_score,
                "anger": negative_score * 0.7,
                "sadness": negative_score * 0.3,
                "neutral": neutral_score
            }
        }
    
    # === RESPOSTAS AUTOMÁTICAS ===
    
    async def suggest_response(
        self, 
        db: AsyncSession, 
        message: str, 
        conversation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[SuggestedResponse]:
        """Sugerir resposta automática"""
        try:
            # Buscar respostas automáticas ativas
            result = await db.execute(
                select(AutoResponse)
                .where(AutoResponse.is_active == True)
                .order_by(AutoResponse.priority.desc())
            )
            auto_responses = result.scalars().all()
            
            message_lower = message.lower()
            
            # Verificar triggers
            for auto_response in auto_responses:
                triggers = auto_response.triggers or []
                
                # Verificar se algum trigger está presente
                trigger_matches = 0
                for trigger in triggers:
                    if isinstance(trigger, str) and trigger.lower() in message_lower:
                        trigger_matches += 1
                
                if trigger_matches > 0:
                    # Calcular confiança baseada na quantidade de matches
                    confidence = min(trigger_matches / len(triggers), 1.0)
                    
                    # Selecionar texto da resposta
                    response_text = auto_response.response_text
                    
                    # Usar variação aleatória se disponível
                    if auto_response.response_variations:
                        import random
                        variations = [response_text] + auto_response.response_variations
                        response_text = random.choice(variations)
                    
                    # Melhorar com IA se configurado
                    if auto_response.use_ai_enhancement:
                        try:
                            enhanced_response = await self._enhance_response_with_ai(
                                db, response_text, message, context
                            )
                            if enhanced_response:
                                response_text = enhanced_response
                        except Exception as e:
                            logger.warning(f"Erro ao melhorar resposta com IA: {e}")
                    
                    # Atualizar estatísticas
                    auto_response.usage_count += 1
                    await db.commit()
                    
                    return SuggestedResponse(
                        text=response_text,
                        confidence=confidence,
                        type=ResponseType(auto_response.response_type),
                        reasoning=f"Matched triggers: {', '.join(triggers[:3])}",
                        alternatives=auto_response.response_variations[:3] if auto_response.response_variations else None
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao sugerir resposta: {e}")
            return None
    
    async def _enhance_response_with_ai(
        self, 
        db: AsyncSession, 
        base_response: str, 
        user_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Melhorar resposta usando IA"""
        try:
            model = await self.get_default_model(db, AIModelType.CHAT)
            if not model:
                return None
            
            system_prompt = f"""
            Você é um assistente que melhora respostas de atendimento ao cliente.
            
            Resposta base: "{base_response}"
            Mensagem do cliente: "{user_message}"
            
            Melhore a resposta base para ser mais personalizada e útil, mantendo o tom profissional e cordial.
            Responda apenas com a resposta melhorada, sem explicações adicionais.
            """
            
            request = ChatCompletionRequest(
                message=user_message,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=200
            )
            
            response_text, _, _ = await self._call_provider(model, request)
            return response_text.strip()
            
        except Exception as e:
            logger.error(f"Erro ao melhorar resposta com IA: {e}")
            return None
    
    # === MÉTODOS AUXILIARES ===
    
    async def _build_conversation_context(
        self, 
        db: AsyncSession, 
        conversation_id: Optional[str]
    ) -> Optional[str]:
        """Construir contexto da conversa"""
        if not conversation_id:
            return None
        
        try:
            # Buscar últimas mensagens da conversa (simulado)
            # Em produção, integraria com o Chat Service
            context = f"Conversa ID: {conversation_id}"
            return context
        except Exception as e:
            logger.warning(f"Erro ao construir contexto: {e}")
            return None
    
    async def _check_rate_limit(
        self, 
        db: AsyncSession, 
        model: AIModel, 
        user_id: Optional[str]
    ):
        """Verificar rate limit do modelo"""
        try:
            now = datetime.utcnow()
            
            # Verificar limite por minuto
            minute_ago = now - timedelta(minutes=1)
            result = await db.execute(
                select(func.count(AIRequest.id))
                .where(and_(
                    AIRequest.model_id == model.id,
                    AIRequest.created_at >= minute_ago,
                    AIRequest.user_id == user_id if user_id else True
                ))
            )
            requests_last_minute = result.scalar()
            
            if requests_last_minute >= model.rate_limit_per_minute:
                raise RateLimitError(f"Rate limit excedido: {requests_last_minute}/{model.rate_limit_per_minute} por minuto")
            
            # Verificar limite por dia
            day_ago = now - timedelta(days=1)
            result = await db.execute(
                select(func.count(AIRequest.id))
                .where(and_(
                    AIRequest.model_id == model.id,
                    AIRequest.created_at >= day_ago,
                    AIRequest.user_id == user_id if user_id else True
                ))
            )
            requests_last_day = result.scalar()
            
            if requests_last_day >= model.rate_limit_per_day:
                raise RateLimitError(f"Rate limit excedido: {requests_last_day}/{model.rate_limit_per_day} por dia")
                
        except RateLimitError:
            raise
        except Exception as e:
            logger.warning(f"Erro ao verificar rate limit: {e}")
    
    async def _create_ai_request(
        self,
        db: AsyncSession,
        model: AIModel,
        prompt: str,
        response: str,
        tokens_used: int,
        cost: Optional[float],
        processing_time: float,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> AIRequest:
        """Criar registro de requisição de IA"""
        try:
            ai_request = AIRequest(
                model_id=model.id,
                conversation_id=conversation_id,
                user_id=user_id,
                prompt=prompt,
                response=response,
                status=AIRequestStatus.COMPLETED.value,
                tokens_used=tokens_used,
                cost=cost,
                processing_time=processing_time,
                completed_at=datetime.utcnow()
            )
            
            db.add(ai_request)
            await db.commit()
            await db.refresh(ai_request)
            
            return ai_request
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Erro ao criar registro de requisição: {e}")
            raise
    
    def _sentiment_to_response(self, analysis: SentimentAnalysis) -> SentimentAnalysisResponse:
        """Converter análise para response"""
        return SentimentAnalysisResponse(
            id=str(analysis.id),
            conversation_id=str(analysis.conversation_id) if analysis.conversation_id else None,
            message_id=str(analysis.message_id) if analysis.message_id else None,
            text=analysis.text,
            sentiment=SentimentType(analysis.sentiment),
            confidence=analysis.confidence,
            positive_score=analysis.positive_score,
            negative_score=analysis.negative_score,
            neutral_score=analysis.neutral_score,
            language=analysis.language,
            keywords=analysis.keywords,
            emotions=analysis.emotions,
            created_at=analysis.created_at
        )
    
    async def get_ai_stats(self, db: AsyncSession) -> Dict[str, Any]:
        """Obter estatísticas de IA"""
        try:
            # Total de requisições
            total_result = await db.execute(select(func.count(AIRequest.id)))
            total_requests = total_result.scalar()
            
            # Requisições bem-sucedidas
            success_result = await db.execute(
                select(func.count(AIRequest.id))
                .where(AIRequest.status == AIRequestStatus.COMPLETED.value)
            )
            successful_requests = success_result.scalar()
            
            # Tempo médio de processamento
            avg_time_result = await db.execute(
                select(func.avg(AIRequest.processing_time))
                .where(AIRequest.processing_time.is_not(None))
            )
            avg_processing_time = avg_time_result.scalar() or 0
            
            # Total de tokens
            tokens_result = await db.execute(
                select(func.sum(AIRequest.tokens_used))
                .where(AIRequest.tokens_used.is_not(None))
            )
            total_tokens = tokens_result.scalar() or 0
            
            # Custo total
            cost_result = await db.execute(
                select(func.sum(AIRequest.cost))
                .where(AIRequest.cost.is_not(None))
            )
            total_cost = cost_result.scalar() or 0
            
            return {
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "failed_requests": total_requests - successful_requests,
                "avg_processing_time": float(avg_processing_time),
                "total_tokens_used": int(total_tokens),
                "total_cost": float(total_cost),
                "success_rate": successful_requests / total_requests if total_requests > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            raise AIServiceError(f"Erro ao obter estatísticas: {e}")

# Instância global do serviço
ai_service = AIService()