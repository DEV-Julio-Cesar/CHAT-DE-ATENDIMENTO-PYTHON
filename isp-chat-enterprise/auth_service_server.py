
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from datetime import datetime, timedelta
import jwt

app = FastAPI(title="Auth Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dados em memória
USERS = {
    "admin": {
        "id": "1",
        "username": "admin", 
        "password": "admin123",
        "email": "admin@ispchatsystem.com",
        "role": "admin"
    }
}

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/api/auth/login")
async def login(request: LoginRequest):
    user = USERS.get(request.username)
    if not user or user["password"] != request.password:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    
    # Criar token simples (em produção usar JWT real)
    token = f"token_{user['id']}_{datetime.now().timestamp()}"
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "role": user["role"]
        }
    }

@app.get("/api/auth/verify")
async def verify():
    return {"valid": True}

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "auth"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
