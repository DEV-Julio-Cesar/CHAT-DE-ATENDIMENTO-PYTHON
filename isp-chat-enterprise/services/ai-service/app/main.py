#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Service - Microserviço de Inteligência Artificial
API FastAPI para IA, análise de sentimento e respostas automáticas
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from sqlalchemy.ext.asyncio import AsyncSession

# Imports locais
from shared.config.settings import settings
from shared.utils.database import get_db, init_db, close_db, get_database_info
from shared.utils.memory_cache import memory_cache
from shared.middleware.auth import (
    get_current_user, RequireAgentOrAbove, RequireSupervisorOrAdmin,
    CurrentUser
)
from shared.models.user import User

from .services import (
    ai_service, AIServiceError, ModelNotFoundError, 
    ProviderError, RateLimitError
)
from .models import (
    AIModelCreate, AIModelResponse, AIRequestCreate, AIRequestResponse,
    SentimentAnalysisCreate, SentimentAnalysisResponse, AutoResponseCreate, AutoResponseResponse,
    ChatCompletionRequest, ChatCompletionResponse, SuggestedResponse, AIStats,
    AIProvider, AIModelType, SentimentType, ResponseType
)

# Configurar logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = l