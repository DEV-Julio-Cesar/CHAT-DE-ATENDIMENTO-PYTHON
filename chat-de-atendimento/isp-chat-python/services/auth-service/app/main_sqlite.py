from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import bcrypt
import jwt
import sqlite3
from datetime import datetime, timedelta
from pydantic import BaseModel
import os

# FastAPI app
app = FastAPI(
    title="Auth Service", 
    version="1.0.0",
    description="Serviço de autenticação com SQLite"
)

# Configuração
JWT_SECRET = "your-super-secret-jwt-key"
JWT_ALGORITHM = "HS256"
DB_PATH = "isp_chat.db"

# Security
security = HTTPBearer()

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
    last_login: str = None

# Database functions
def get_db_connection():
    """Obter conexão com SQLite"""
    # Caminho relativo ao diretório do projeto
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    db_path = os.path.join(project_root, DB_PATH)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Para acessar colunas por nome
    return conn

def get_user_by_username(username: str):
    """Buscar usuário por username"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, email, password_hash, role, is_active, last_login FROM users WHERE username = ?",
            (username,)
        )
        user = cursor.fetchone()
        return dict(user) if user else None
    finally:
        conn.close()

def update_last_login(user_id: str):
    """Atualizar último login do usuário"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET last_login = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), user_id)
        )
        conn.commit()
    finally:
        conn.close()

# Routes
@app.post("/login", response_model=LoginResponse)
async def login(credentials: LoginRequest):
    """Login com banco SQLite"""
    
    # Buscar usuário no SQLite
    user = get_user_by_username(credentials.username)
    
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
    
    # Atualizar último login
    update_last_login(user["id"])
    
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
        
        user = get_user_by_username(username)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return UserResponse(
            id=user["id"],
            username=user["username"],
            email=user["email"],
            role=user["role"],
            is_active=bool(user["is_active"]),
            last_login=user["last_login"]
        )
        
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/health")
async def health_check():
    """Health check com informações do banco"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        users_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM conversations")
        conversations_count = cursor.fetchone()[0]
        conn.close()
        
        return {
            "status": "healthy", 
            "service": "auth-service",
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat(),
            "database": {
                "type": "SQLite",
                "users": users_count,
                "conversations": conversations_count
            },
            "message": "🚀 Auth Service Python com SQLite funcionando!"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "🎉 ISP Chat System - Auth Service",
        "version": "1.0.0",
        "status": "running",
        "database": "SQLite",
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
    print("🚀 Iniciando Auth Service Python com SQLite...")
    print("📍 Acesse: http://localhost:8002")
    print("📖 Documentação: http://localhost:8002/docs")
    print("🗄️ Banco: SQLite (isp_chat.db)")
    uvicorn.run("main_sqlite:app", host="0.0.0.0", port=8002, reload=False)