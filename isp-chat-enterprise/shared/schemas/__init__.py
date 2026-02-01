#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shared Schemas - Schemas compartilhados
Inicialização do módulo de schemas
"""

from .chat import (
    ConversationCreate, ConversationUpdate, ConversationResponse,
    MessageCreate, MessageResponse,
    ConversationListResponse, MessageListResponse
)

__all__ = [
    "ConversationCreate", "ConversationUpdate", "ConversationResponse",
    "MessageCreate", "MessageResponse", 
    "ConversationListResponse", "MessageListResponse"
]