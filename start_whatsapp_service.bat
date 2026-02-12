@echo off
echo ========================================
echo  WhatsApp Service - CIANET
echo ========================================
echo.

cd whatsapp-service

echo Verificando Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo ERRO: Node.js nao esta instalado!
    echo Baixe em: https://nodejs.org/
    pause
    exit /b 1
)

echo Node.js encontrado!
echo.

if not exist node_modules (
    echo Instalando dependencias...
    call npm install
    echo.
)

echo Iniciando servico WhatsApp...
echo.
echo O servico estara disponivel em: http://localhost:3001
echo.
echo Pressione Ctrl+C para parar o servico
echo.

node server.js
