from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import bcrypt
import jwt
from datetime import datetime, timedelta
from pydantic import BaseModel

# FastAPI app
app = FastAPI(
    title="Auth Service", 
    version="1.0.0",
    description="Serviço de autenticação - versão simplificada para teste"
)

# Configuração
JWT_SECRET = "your-super-secret-jwt-key"
JWT_ALGORITHM = "HS256"

# Security
security = HTTPBearer()

# Usuários em memória (migrados do sistema Node.js)
USERS_DB = {
    "admin": {
        "id": "admin-id",
        "username": "admin",
        "email": "admin@sistema.com",
        "password_hash": "$2a$10$Cmu1DBIKIwpBB29IJMfN1uXu3QalrDOq7.j4mV.XzrKU/N0Nh7nam",
        "role": "admin",
        "is_active": True
    }
}

# Schemas
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    username: str
    role: str
    expires_in: int

class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    role: str
    is_active: bool

# Routes
@app.post("/login", response_model=LoginResponse)
async def login(credentials: LoginRequest):
    """Login compatível com o sistema atual"""
    
    # Buscar usuário
    user = USERS_DB.get(credentials.username)
    
    if not user or not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Verificar senha (compatível com bcrypt do Node.js)
    if not bcrypt.checkpw(credentials.password.encode('utf-8'), user["password_hash"].encode('utf-8')):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Criar token JWT
    token_data = {
        "sub": user["username"],
        "user_id": user["id"],
        "role": user["role"],
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    token = jwt.encode(token_data, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user_id=user["id"],
        username=user["username"],
        role=user["role"],
        expires_in=24 * 3600
    )

@app.post("/verify")
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verificar token JWT"""
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return {"valid": True, "user": payload}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/users/me", response_model=UserResponse)
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Obter dados do usuário atual"""
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username = payload.get("sub")
        
        user = USERS_DB.get(username)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return UserResponse(
            id=user["id"],
            username=user["username"],
            email=user["email"],
            role=user["role"],
            is_active=user["is_active"]
        )
        
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/health")
async def health_check():
    """Health check"""
    return {
        "status": "healthy", 
        "service": "auth-service",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "message": "🚀 Auth Service Python funcionando!"
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "🎉 ISP Chat System - Auth Service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "login": "POST /login",
            "verify": "POST /verify", 
            "me": "GET /users/me",
            "health": "GET /health",
            "docs": "GET /docs"
        }
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Iniciando Auth Service Python...")
    print("📍 Acesse: http://localhost:8001")
    print("📖 Documentação: http://localhost:8001/docs")
    uvicorn.run("main_simple:app", host="0.0.0.0", port=8001, reload=False)