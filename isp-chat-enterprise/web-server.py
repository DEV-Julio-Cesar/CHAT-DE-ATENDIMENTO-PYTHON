#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ISP Chat Enterprise - Servidor Web
Servidor para interface web estática
"""

import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Criar aplicação FastAPI
app = FastAPI(
    title="ISP Chat Enterprise - Web Interface",
    description="Interface web para o sistema de chat",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Diretório da interface web
web_dir = Path(__file__).parent / "web-interface"

# Servir arquivos estáticos
app.mount("/static", StaticFiles(directory=web_dir), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Servir página principal"""
    index_file = web_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return HTMLResponse("<h1>Interface Web não encontrada</h1>", status_code=404)

@app.get("/app.js")
async def serve_app_js():
    """Servir JavaScript principal"""
    js_file = web_dir / "app.js"
    if js_file.exists():
        return FileResponse(js_file, media_type="application/javascript")
    return HTMLResponse("// JavaScript não encontrado", status_code=404)

@app.get("/health")
async def health_check():
    """Health check"""
    return {
        "status": "healthy",
        "service": "web-interface",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    uvicorn.run(
        "web-server:app",
        host="0.0.0.0",
        port=3000,
        reload=False,
        log_level="info"
    )