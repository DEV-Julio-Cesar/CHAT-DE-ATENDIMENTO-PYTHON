#!/usr/bin/env python3
"""
Script interativo para configurar WhatsApp Business API
"""
import os
import re
import requests
from pathlib import Path

def print_header():
    print("=" * 60)
    print("🚀 CONFIGURAÇÃO WHATSAPP BUSINESS API")
    print("=" * 60)
    print()

def print_step(step, title):
    print(f"📋 PASSO {step}: {title}")
    print("-" * 40)

def validate_access_token(token):
    """Validar formato do access token"""
    if not token:
        return False
    # Access tokens do Meta geralmente começam com EAA
    return token.startswith("EAA") and len(token) > 50

def validate_phone_number_id(phone_id):
    """Validar formato do phone number ID"""
    if not phone_id:
        return False
    # Phone number IDs são números longos
    return phone_id.isdigit() and len(phone_id) >= 10

def test_whatsapp_connection(access_token, phone_number_id):
    """Testar conexão com WhatsApp Business API"""
    try:
        url = f"https://graph.facebook.com/v18.0/{phone_number_id}"
        headers = {"Authorization": f"Bearer {access_token}"}
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            return True, data
        else:
            return False, response.text
            
    except Exception as e:
        return False, str(e)

def update_env_file(access_token, phone_number_id, webhook_token):
    """Atualizar arquivo .env com as credenciais"""
    env_path = Path(".env")
    
    # Ler arquivo atual
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            content = f.read()
    else:
        content = ""
    
    # Atualizar ou adicionar variáveis
    def update_or_add_var(content, var_name, var_value):
        pattern = f'^{var_name}=.*$'
        replacement = f'{var_name}="{var_value}"'
        
        if re.search(pattern, content, re.MULTILINE):
            return re.sub(pattern, replacement, content, flags=re.MULTILINE)
        else:
            return content + f'\n{replacement}'
    
    content = update_or_add_var(content, "WHATSAPP_ACCESS_TOKEN", access_token)
    content = update_or_add_var(content, "WHATSAPP_PHONE_NUMBER_ID", phone_number_id)
    content = update_or_add_var(content, "WHATSAPP_WEBHOOK_VERIFY_TOKEN", webhook_token)
    
    # Salvar arquivo
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Arquivo .env atualizado com sucesso!")

def main():
    print_header()
    
    print("Este script vai te ajudar a configurar o WhatsApp Business API.")
    print("Você precisará das credenciais do Meta for Developers.")
    print()
    
    # Passo 1: Verificar se já tem credenciais
    print_step(1, "VERIFICAR CONFIGURAÇÃO ATUAL")
    
    current_token = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    current_phone = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    
    if current_token and current_phone:
        print(f"✅ Access Token: {current_token[:20]}...")
        print(f"✅ Phone Number ID: {current_phone}")
        
        test_current = input("\n🔍 Testar configuração atual? (s/n): ").lower().strip()
        if test_current == 's':
            print("🔄 Testando conexão...")
            success, result = test_whatsapp_connection(current_token, current_phone)
            
            if success:
                print("✅ Conexão funcionando!")
                print(f"   Nome: {result.get('name', 'N/A')}")
                print(f"   Status: {result.get('status', 'N/A')}")
                
                if input("\n✨ Configuração atual está funcionando. Continuar mesmo assim? (s/n): ").lower().strip() != 's':
                    print("👋 Configuração mantida. Até logo!")
                    return
            else:
                print(f"❌ Erro na conexão: {result}")
                print("🔧 Vamos reconfigurar...")
    else:
        print("⚠️  Nenhuma configuração encontrada.")
    
    print()
    
    # Passo 2: Obter credenciais
    print_step(2, "CONFIGURAR CREDENCIAIS")
    
    print("📱 Para obter as credenciais:")
    print("1. Acesse: https://developers.facebook.com/")
    print("2. Crie um App Business")
    print("3. Adicione WhatsApp Business API")
    print("4. Copie as credenciais")
    print()
    
    # Access Token
    while True:
        access_token = input("🔑 Access Token (EAAxxxxx...): ").strip()
        
        if not access_token:
            print("❌ Access Token é obrigatório!")
            continue
            
        if not validate_access_token(access_token):
            print("❌ Formato inválido! Access Token deve começar com 'EAA' e ter mais de 50 caracteres.")
            continue
            
        break
    
    # Phone Number ID
    while True:
        phone_number_id = input("📱 Phone Number ID (números apenas): ").strip()
        
        if not phone_number_id:
            print("❌ Phone Number ID é obrigatório!")
            continue
            
        if not validate_phone_number_id(phone_number_id):
            print("❌ Formato inválido! Phone Number ID deve conter apenas números e ter pelo menos 10 dígitos.")
            continue
            
        break
    
    # Webhook Token
    webhook_token = input("🔐 Webhook Verify Token (ou Enter para usar padrão): ").strip()
    if not webhook_token:
        webhook_token = "webhook_verify_token_123"
    
    print()
    
    # Passo 3: Testar credenciais
    print_step(3, "TESTAR CREDENCIAIS")
    
    print("🔄 Testando conexão com WhatsApp Business API...")
    success, result = test_whatsapp_connection(access_token, phone_number_id)
    
    if success:
        print("✅ Conexão bem-sucedida!")
        print(f"   Nome do Negócio: {result.get('name', 'N/A')}")
        print(f"   Status: {result.get('status', 'N/A')}")
        print(f"   Phone Number ID: {phone_number_id}")
    else:
        print(f"❌ Erro na conexão: {result}")
        print("\n🔧 Possíveis problemas:")
        print("- Access Token inválido ou expirado")
        print("- Phone Number ID incorreto")
        print("- Permissões insuficientes")
        print("- Problema de rede")
        
        if input("\n❓ Salvar mesmo assim? (s/n): ").lower().strip() != 's':
            print("❌ Configuração cancelada.")
            return
    
    print()
    
    # Passo 4: Salvar configuração
    print_step(4, "SALVAR CONFIGURAÇÃO")
    
    try:
        update_env_file(access_token, phone_number_id, webhook_token)
        
        print("✅ Configuração salva com sucesso!")
        print()
        print("🔄 Para aplicar as mudanças:")
        print("   docker-compose -f docker-compose.dev.yml restart api")
        print()
        print("🧪 Para testar:")
        print("   curl http://localhost:8000/api/v1/whatsapp/status")
        print()
        print("📚 Documentação:")
        print("   http://localhost:8000/docs")
        
    except Exception as e:
        print(f"❌ Erro ao salvar: {e}")
        return
    
    print()
    print("🎉 CONFIGURAÇÃO CONCLUÍDA!")
    print("=" * 60)
    print("Sua aplicação agora está integrada com WhatsApp Business API!")
    print("Você pode enviar e receber mensagens via WhatsApp.")
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Configuração cancelada pelo usuário.")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        print("Por favor, configure manualmente o arquivo .env")