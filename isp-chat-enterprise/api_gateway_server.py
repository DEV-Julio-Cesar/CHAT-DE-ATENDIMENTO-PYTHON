
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import httpx
from fastapi.responses import JSONResponse

app = FastAPI(title="API Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_request(request: Request, path: str):
    # Determinar serviço baseado no path
    if path.startswith("auth/"):
        target_url = f"http://localhost:8001/api/{path}"
    elif path.startswith("chat/"):
        target_url = f"http://localhost:8002/api/{path}"
    else:
        return JSONResponse({"error": "Service not found"}, status_code=404)
    
    # Fazer proxy da requisição
    async with httpx.AsyncClient() as client:
        try:
            # Obter dados da requisição
            body = await request.body()
            headers = dict(request.headers)
            
            # Fazer requisição para o serviço
            response = await client.request(
                method=request.method,
                url=target_url,
                content=body,
                headers=headers,
                params=request.query_params
            )
            
            return JSONResponse(
                content=response.json() if response.content else {},
                status_code=response.status_code
            )
            
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "gateway"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
