#!/usr/bin/env python3
"""
Script para iniciar a aplicação web
"""
import subprocess
import sys
import os

def check_dependencies():
    """Verificar se as dependências estão instaladas"""
    try:
        import fastapi
        import uvicorn
        print("✅ Dependências encontradas")
        return True
    except ImportError:
        print("❌ Dependências não encontradas")
        print("💡 Instalando dependências...")
        
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements_web.txt"])
            print("✅ Dependências instaladas com sucesso")
            return True
        except subprocess.CalledProcessError:
            print("❌ Erro ao instalar dependências")
            return False

def main():
    """Função principal"""
    print("🚀 ISP Customer Support - Iniciando Aplicação Web")
    print("=" * 60)
    
    # Verificar dependências
    if not check_dependencies():
        print("❌ Não foi possível instalar as dependências")
        sys.exit(1)
    
    print("\n📊 Informações da Aplicação:")
    print("   • Nome: ISP Customer Support")
    print("   • Versão: 2.0.0")
    print("   • Tecnologia: FastAPI + Python")
    print("   • Performance: Cache 1,280x + Compressão 98.2%")
    
    print("\n🌐 URLs Disponíveis:")
    print("   • Dashboard: http://localhost:8000")
    print("   • API Docs: http://localhost:8000/docs")
    print("   • Health Check: http://localhost:8000/health")
    print("   • Métricas: http://localhost:8000/metrics")
    print("   • Cache Stats: http://localhost:8000/cache/stats")
    
    print("\n🚀 Iniciando servidor...")
    print("=" * 60)
    
    try:
        # Importar e executar
        import uvicorn
        from main_web_ready import app
        
        uvicorn.run(
            "main_web_ready:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
        
    except KeyboardInterrupt:
        print("\n\n👋 Aplicação encerrada pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro ao iniciar aplicação: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()