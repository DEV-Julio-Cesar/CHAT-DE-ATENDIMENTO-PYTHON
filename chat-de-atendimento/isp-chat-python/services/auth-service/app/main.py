from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta
from pydantic import BaseModel
import sys
import os

# Adicionar path para shared
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# Configuração
DATABASE_URL = "postgresql+asyncpg://postgres:postgres123@localhost:5432/isp_chat"
JWT_SECRET = "your-super-secret-jwt-key"
JWT_ALGORITHM = "HS256"

# FastAPI app
app = FastAPI(
    title="Auth Service", 
    version="1.0.0",
    description="Serviço de autenticação migrado do sistema Node.js"
)

# Database
engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Security
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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

# Dependency
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# Routes
@app.post("/login", response_model=LoginResponse)
async def login(credentials: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login compatível com o sistema atual"""
    
    # Buscar usuário no PostgreSQL
    result = await db.execute(
        text("SELECT id, username, email, password_hash, role, is_active FROM users WHERE username = :username"),
        {"username": credentials.username}
    )
    user = result.fetchone()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Verificar senha (compatível com bcrypt do Node.js)
    if not pwd_context.verify(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Atualizar último login
    await db.execute(
        text("UPDATE users SET last_login = NOW() WHERE id = :user_id"),
        {"user_id": user.id}
    )
    await db.commit()
    
    # Criar token JWT
    token_data = {
        "sub": user.username,
        "user_id": str(user.id),
        "role": user.role,
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    token = jwt.encode(token_data, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user_id=str(user.id),
        username=user.username,
        role=user.role,
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
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Obter dados do usuário atual"""
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("user_id")
        
        result = await db.execute(
            text("SELECT id, username, email, role, is_active, last_login FROM users WHERE id = :user_id"),
            {"user_id": user_id}
        )
        user = result.fetchone()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return UserResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            last_login=user.last_login.isoformat() if user.last_login else None
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
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001, reload=True)