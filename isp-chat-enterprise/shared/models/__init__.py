#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shared Models - Modelos compartilhados
Inicialização do módulo de modelos
"""

from .user import User, UserRole
from .conversation import Conversation, ConversationStatus, ConversationPriority
from .message import Message, MessageSenderType, MessageType

__all__ = [
    "User", "UserRole",
    "Conversation", "ConversationStatus", "ConversationPriority", 
    "Message", "MessageSenderType", "MessageType"
]