
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from datetime import datetime
from typing import List, Optional

app = FastAPI(title="Chat Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dados em memória
CONVERSATIONS = {
    "1": {
        "id": "1",
        "customer_phone": "5511999999999",
        "customer_name": "Cliente Teste",
        "status": "active",
        "created_at": datetime.now().isoformat(),
        "agent_id": "1"
    },
    "2": {
        "id": "2", 
        "customer_phone": "5511888888888",
        "customer_name": "Maria Silva",
        "status": "waiting",
        "created_at": datetime.now().isoformat(),
        "agent_id": None
    }
}

MESSAGES = {
    "1": [
        {"id": "1", "content": "Olá, preciso de ajuda", "sender": "customer", "timestamp": datetime.now().isoformat()},
        {"id": "2", "content": "Como posso ajudar?", "sender": "agent", "timestamp": datetime.now().isoformat()}
    ],
    "2": [
        {"id": "3", "content": "Internet lenta", "sender": "customer", "timestamp": datetime.now().isoformat()}
    ]
}

@app.get("/api/chat/conversations")
async def get_conversations():
    return {
        "conversations": list(CONVERSATIONS.values()),
        "total": len(CONVERSATIONS)
    }

@app.get("/api/chat/conversations/{conversation_id}/messages")
async def get_messages(conversation_id: str):
    messages = MESSAGES.get(conversation_id, [])
    return {
        "messages": messages,
        "total": len(messages)
    }

class MessageCreate(BaseModel):
    content: str
    sender: str = "agent"

@app.post("/api/chat/conversations/{conversation_id}/messages")
async def create_message(conversation_id: str, message: MessageCreate):
    if conversation_id not in MESSAGES:
        MESSAGES[conversation_id] = []
    
    new_message = {
        "id": str(len(MESSAGES[conversation_id]) + 1),
        "content": message.content,
        "sender": message.sender,
        "timestamp": datetime.now().isoformat()
    }
    
    MESSAGES[conversation_id].append(new_message)
    return new_message

@app.get("/api/chat/stats")
async def get_stats():
    return {
        "total_conversations": len(CONVERSATIONS),
        "active_conversations": len([c for c in CONVERSATIONS.values() if c["status"] == "active"]),
        "waiting_conversations": len([c for c in CONVERSATIONS.values() if c["status"] == "waiting"]),
        "total_messages": sum(len(msgs) for msgs in MESSAGES.values())
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "chat"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
