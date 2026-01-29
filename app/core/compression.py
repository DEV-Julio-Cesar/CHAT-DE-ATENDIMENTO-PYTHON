"""
Sistema de Compressão de Resposta para Otimização de Performance
"""
import gzip
import brotli
import zlib
from typing import Union, Dict, Any, Optional
from fastapi import Request, Response
from fastapi.responses import JSONResponse
import json
import structlog

logger = structlog.get_logger(__name__)


class CompressionManager:
    """Gerenciador de compressão de resposta"""
    
    def __init__(self):
        self.compression_stats = {
            "gzip": {"requests": 0, "bytes_saved": 0},
            "brotli": {"requests": 0, "bytes_saved": 0},
            "deflate": {"requests": 0, "bytes_saved": 0},
            "none": {"requests": 0}
        }
        
        # Configurações de compressão
        self.min_size = 1024  # Comprimir apenas respostas > 1KB
        self.compression_level = {
            "gzip": 6,     # Balanceado
            "brotli": 4,   # Balanceado
            "deflate": 6   # Balanceado
        }
    
    def should_compress(self, content: bytes, content_type: str) -> bool:
        """Verificar se deve comprimir a resposta"""
        # Não comprimir se muito pequeno
        if len(content) < self.min_size:
            return False
        
        # Tipos de conteúdo que devem ser comprimidos
        compressible_types = [
            "application/json",
            "text/html",
            "text/css",
            "text/javascript",
            "application/javascript",
            "text/xml",
            "application/xml",
            "text/plain"
        ]
        
        return any(ct in content_type for ct in compressible_types)
    
    def get_best_encoding(self, accept_encoding: str) -> Optional[str]:
        """Determinar melhor encoding baseado no Accept-Encoding"""
        if not accept_encoding:
            return None
        
        accept_encoding = accept_encoding.lower()
        
        # Prioridade: brotli > gzip > deflate
        if "br" in accept_encoding:
            return "brotli"
        elif "gzip" in accept_encoding:
            return "gzip"
        elif "deflate" in accept_encoding:
            return "deflate"
        
        return None
    
    def compress_content(self, content: bytes, encoding: str) -> bytes:
        """Comprimir conteúdo com o encoding especificado"""
        try:
            original_size = len(content)
            
            if encoding == "gzip":
                compressed = gzip.compress(content, compresslevel=self.compression_level["gzip"])
                self.compression_stats["gzip"]["requests"] += 1
                self.compression_stats["gzip"]["bytes_saved"] += original_size - len(compressed)
                
            elif encoding == "brotli":
                compressed = brotli.compress(content, quality=self.compression_level["brotli"])
                self.compression_stats["brotli"]["requests"] += 1
                self.compression_stats["brotli"]["bytes_saved"] += original_size - len(compressed)
                
            elif encoding == "deflate":
                compressed = zlib.compress(content, level=self.compression_level["deflate"])
                self.compression_stats["deflate"]["requests"] += 1
                self.compression_stats["deflate"]["bytes_saved"] += original_size - len(compressed)
                
            else:
                return content
            
            compression_ratio = (1 - len(compressed) / original_size) * 100
            logger.debug("Content compressed", 
                        encoding=encoding,
                        original_size=original_size,
                        compressed_size=len(compressed),
                        ratio=f"{compression_ratio:.1f}%")
            
            return compressed
            
        except Exception as e:
            logger.error("Compression failed", encoding=encoding, error=str(e))
            return content
    
    def get_stats(self) -> Dict[str, Any]:
        """Obter estatísticas de compressão"""
        total_requests = sum(stats.get("requests", 0) for stats in self.compression_stats.values())
        total_bytes_saved = sum(stats.get("bytes_saved", 0) for stats in self.compression_stats.values())
        
        return {
            "total_requests": total_requests,
            "total_bytes_saved": total_bytes_saved,
            "total_bytes_saved_mb": round(total_bytes_saved / 1024 / 1024, 2),
            "by_encoding": self.compression_stats,
            "compression_ratio": {
                encoding: {
                    "requests": stats["requests"],
                    "avg_bytes_saved": round(stats["bytes_saved"] / max(stats["requests"], 1), 2)
                }
                for encoding, stats in self.compression_stats.items()
                if "bytes_saved" in stats
            }
        }


# Instância global
compression_manager = CompressionManager()


class CompressedJSONResponse(JSONResponse):
    """JSONResponse com compressão automática"""
    
    def __init__(
        self,
        content: Any,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        media_type: Optional[str] = None,
        background = None,
        request: Optional[Request] = None
    ):
        super().__init__(content, status_code, headers, media_type, background)
        self.request = request
    
    def render(self, content: Any) -> bytes:
        """Renderizar conteúdo com compressão"""
        # Renderizar JSON normalmente
        json_content = json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
            default=str
        ).encode("utf-8")
        
        # Se não há request, retornar sem compressão
        if not self.request:
            compression_manager.compression_stats["none"]["requests"] += 1
            return json_content
        
        # Verificar se deve comprimir
        content_type = self.media_type or "application/json"
        if not compression_manager.should_compress(json_content, content_type):
            compression_manager.compression_stats["none"]["requests"] += 1
            return json_content
        
        # Determinar melhor encoding
        accept_encoding = self.request.headers.get("accept-encoding", "")
        encoding = compression_manager.get_best_encoding(accept_encoding)
        
        if not encoding:
            compression_manager.compression_stats["none"]["requests"] += 1
            return json_content
        
        # Comprimir conteúdo
        compressed_content = compression_manager.compress_content(json_content, encoding)
        
        # Adicionar headers de compressão
        if compressed_content != json_content:
            self.headers["content-encoding"] = encoding
            self.headers["vary"] = "Accept-Encoding"
        
        return compressed_content


def create_compressed_response(
    content: Any,
    request: Request,
    status_code: int = 200,
    headers: Optional[Dict[str, str]] = None
) -> Response:
    """Criar resposta comprimida"""
    return CompressedJSONResponse(
        content=content,
        status_code=status_code,
        headers=headers,
        request=request
    )


# Middleware de compressão
class CompressionMiddleware:
    """Middleware para compressão automática"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        
        # Wrapper para interceptar resposta
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                # Adicionar headers de compressão se necessário
                headers = dict(message.get("headers", []))
                
                # Verificar se já tem content-encoding
                if b"content-encoding" not in [h[0] for h in message.get("headers", [])]:
                    accept_encoding = request.headers.get("accept-encoding", "")
                    encoding = compression_manager.get_best_encoding(accept_encoding)
                    
                    if encoding:
                        message["headers"] = [
                            *message.get("headers", []),
                            (b"vary", b"Accept-Encoding")
                        ]
                
                await send(message)
                
            elif message["type"] == "http.response.body":
                body = message.get("body", b"")
                
                if body:
                    content_type = ""
                    # Extrair content-type dos headers (implementação simplificada)
                    
                    if compression_manager.should_compress(body, content_type):
                        accept_encoding = request.headers.get("accept-encoding", "")
                        encoding = compression_manager.get_best_encoding(accept_encoding)
                        
                        if encoding:
                            compressed_body = compression_manager.compress_content(body, encoding)
                            message["body"] = compressed_body
                
                await send(message)
            else:
                await send(message)
        
        await self.app(scope, receive, send_wrapper)