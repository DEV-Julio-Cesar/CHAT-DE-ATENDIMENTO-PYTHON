"""
Verificar status do serviço WhatsApp
"""
import requests
import json

def check_whatsapp_status():
    """Verificar status do WhatsApp"""
    print("=" * 60)
    print("📱 STATUS DO SERVIÇO WHATSAPP")
    print("=" * 60)
    
    try:
        # Verificar status geral
        r = requests.get('http://localhost:3001/status', timeout=5)
        if r.status_code == 200:
            data = r.json()
            print(f"\n✅ Serviço: {data.get('service')}")
            print(f"📊 Status: {data.get('status').upper()}")
            print(f"🔑 Versão: {data.get('version')}")
            print(f"📱 QR Code disponível: {'Sim' if data.get('hasQrCode') else 'Não'}")
            
            if data.get('clientInfo'):
                info = data['clientInfo']
                print(f"\n👤 Cliente conectado:")
                print(f"   • Número: {info.get('number')}")
                print(f"   • Nome: {info.get('name')}")
                print(f"   • Plataforma: {info.get('platform')}")
        
        # Verificar QR Code
        print("\n" + "-" * 60)
        r = requests.get('http://localhost:3001/qr-code', timeout=5)
        if r.status_code == 200:
            data = r.json()
            
            if data.get('connected'):
                print("✅ WhatsApp já está CONECTADO!")
                if data.get('clientInfo'):
                    info = data['clientInfo']
                    print(f"   • Conectado como: {info.get('name')} ({info.get('number')})")
            elif data.get('qr_code'):
                print("📱 QR CODE DISPONÍVEL!")
                print("   • Acesse: http://127.0.0.1:8000/whatsapp")
                print("   • Escaneie o QR Code com seu WhatsApp")
                print(f"   • Tamanho do QR: {len(data['qr_code'])} caracteres")
            else:
                print(f"⏳ {data.get('message', 'Aguardando...')}")
        
        print("\n" + "=" * 60)
        print("📌 PRÓXIMOS PASSOS:")
        print("=" * 60)
        print("1. Acesse: http://127.0.0.1:8000/whatsapp")
        print("2. Escaneie o QR Code com seu WhatsApp")
        print("3. Aguarde a mensagem 'WhatsApp conectado!'")
        print("4. Teste enviando uma mensagem")
        
    except requests.exceptions.ConnectionError:
        print("❌ ERRO: Serviço WhatsApp não está rodando!")
        print("\n📋 Para iniciar o serviço:")
        print("   cd whatsapp-service")
        print("   npm start")
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    check_whatsapp_status()
