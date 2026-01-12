@echo off
echo.
echo ================================================
echo  REINICIO LIMPO - Sistema de Atendimento
echo ================================================
echo.

echo [1/4] Fechando processos Electron...
taskkill /F /IM electron.exe >nul 2>&1
timeout /t 2 >nul

echo [2/4] Limpando cache...
if exist "%APPDATA%\chat-de-atendimento" (
    rmdir /S /Q "%APPDATA%\chat-de-atendimento" >nul 2>&1
)

echo [3/4] Usuário admin já foi resetado
echo       Credenciais: admin / admin

echo [4/4] Iniciando aplicação...
echo.
echo ================================================
echo  PRONTO! Aguarde o aplicativo abrir...
echo ================================================
echo.
echo Tente logar com:
echo   Usuario: admin
echo   Senha: admin
echo.

start /B npm start
