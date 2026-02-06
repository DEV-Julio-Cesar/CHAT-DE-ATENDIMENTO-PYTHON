#!/usr/bin/env python
"""
Demo interativo do Chatbot AI
Execute este script para testar o chatbot localmente

Uso:
    python demo_chatbot.py
"""

import asyncio
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.chatbot_ai import chatbot_ai, IntentType, SentimentType


# Cores para terminal
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header():
    """Imprimir cabeçalho do demo"""
    print(f"""
{Colors.CYAN}╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     🤖 ARIA - Chatbot AI Enterprise Demo                    ║
║     Sistema de Atendimento para Telecomunicações            ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝{Colors.ENDC}

{Colors.YELLOW}Comandos especiais:{Colors.ENDC}
  /sair    - Encerra o chat
  /limpar  - Limpa o histórico da conversa
  /metricas - Mostra métricas do chatbot
  /ajuda   - Mostra esta mensagem

{Colors.GREEN}Digite sua mensagem para começar!{Colors.ENDC}
""")


def print_response(response):
    """Imprimir resposta do chatbot formatada"""
    # Cor baseada no sentimento
    sentiment_color = {
        SentimentType.MUITO_POSITIVO: Colors.GREEN,
        SentimentType.POSITIVO: Colors.GREEN,
        SentimentType.NEUTRO: Colors.BLUE,
        SentimentType.NEGATIVO: Colors.YELLOW,
        SentimentType.MUITO_NEGATIVO: Colors.RED,
    }
    
    color = sentiment_color.get(response.sentiment, Colors.BLUE)
    
    print(f"\n{Colors.CYAN}┌─ ARIA {Colors.ENDC}")
    print(f"{Colors.CYAN}│{Colors.ENDC}")
    
    # Resposta
    for line in response.message.split('\n'):
        print(f"{Colors.CYAN}│{Colors.ENDC} {line}")
    
    print(f"{Colors.CYAN}│{Colors.ENDC}")
    print(f"{Colors.CYAN}└─────────────────────────────────────{Colors.ENDC}")
    
    # Metadados
    print(f"\n{Colors.YELLOW}📊 Análise:{Colors.ENDC}")
    print(f"   • Intenção: {response.intent.value}")
    print(f"   • Sentimento: {color}{response.sentiment.value}{Colors.ENDC}")
    print(f"   • Confiança: {response.confidence:.0%}")
    print(f"   • Tempo: {response.metadata.get('response_time_ms', 0)}ms")
    
    if response.should_escalate:
        print(f"\n{Colors.RED}⚠️ ESCALAÇÃO NECESSÁRIA:{Colors.ENDC} {response.escalation_reason}")
    
    if response.quick_replies:
        print(f"\n{Colors.GREEN}💬 Sugestões de resposta:{Colors.ENDC}")
        for i, reply in enumerate(response.quick_replies, 1):
            print(f"   {i}. {reply}")


async def print_metrics():
    """Imprimir métricas do chatbot"""
    metrics = await chatbot_ai.get_metrics()
    
    print(f"\n{Colors.CYAN}═══════════════════════════════════════{Colors.ENDC}")
    print(f"{Colors.BOLD}📈 MÉTRICAS DO CHATBOT{Colors.ENDC}")
    print(f"{Colors.CYAN}═══════════════════════════════════════{Colors.ENDC}")
    print(f"Total de mensagens: {metrics['total_messages']}")
    print(f"Resoluções bem-sucedidas: {metrics['successful_resolutions']}")
    print(f"Taxa de resolução: {metrics['resolution_rate']:.1f}%")
    print(f"Escalações: {metrics['escalations']}")
    print(f"Taxa de escalação: {metrics['escalation_rate']:.1f}%")
    print(f"Tempo médio de resposta: {metrics['avg_response_time_ms']}ms")
    
    if metrics['top_intents']:
        print(f"\n{Colors.BOLD}Top Intenções:{Colors.ENDC}")
        for intent, count in list(metrics['top_intents'].items())[:5]:
            print(f"   • {intent}: {count}")
    
    print(f"{Colors.CYAN}═══════════════════════════════════════{Colors.ENDC}\n")


async def main():
    """Função principal do demo"""
    print_header()
    
    # Inicializar chatbot
    print(f"{Colors.YELLOW}Inicializando chatbot...{Colors.ENDC}")
    await chatbot_ai.initialize()
    print(f"{Colors.GREEN}Chatbot pronto!{Colors.ENDC}\n")
    
    conversation_id = "demo:terminal:001"
    
    # Informações do cliente simulado
    cliente_info = {
        "nome": "Cliente Demo",
        "telefone": "5511999999999",
        "plano": "Plus 200MB"
    }
    
    while True:
        try:
            # Input do usuário
            user_input = input(f"\n{Colors.GREEN}Você:{Colors.ENDC} ").strip()
            
            if not user_input:
                continue
            
            # Comandos especiais
            if user_input.lower() == '/sair':
                print(f"\n{Colors.CYAN}Até logo! 👋{Colors.ENDC}\n")
                break
            
            if user_input.lower() == '/limpar':
                await chatbot_ai.clear_conversation(conversation_id)
                print(f"{Colors.GREEN}Histórico limpo!{Colors.ENDC}")
                continue
            
            if user_input.lower() == '/metricas':
                await print_metrics()
                continue
            
            if user_input.lower() == '/ajuda':
                print_header()
                continue
            
            # Processar mensagem
            response = await chatbot_ai.generate_response(
                conversation_id=conversation_id,
                user_message=user_input,
                cliente_info=cliente_info
            )
            
            # Mostrar resposta
            print_response(response)
            
        except KeyboardInterrupt:
            print(f"\n\n{Colors.CYAN}Até logo! 👋{Colors.ENDC}\n")
            break
        except Exception as e:
            print(f"\n{Colors.RED}Erro: {e}{Colors.ENDC}")


if __name__ == "__main__":
    # Verificar se colorama está disponível (para Windows)
    try:
        import colorama
        colorama.init()
    except ImportError:
        pass
    
    # Executar demo
    asyncio.run(main())
