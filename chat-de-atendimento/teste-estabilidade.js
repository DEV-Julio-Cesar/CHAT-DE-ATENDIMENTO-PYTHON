#!/usr/bin/env node

/**
 * 🧪 TESTE DE ESTABILIDADE DO SISTEMA
 * 
 * Monitora a execução do sistema por 10 minutos e registra:
 * - Erros não esperados
 * - Desconexões
 * - Comportamentos anormais
 */

const fs = require('fs-extra');
const path = require('path');
const readline = require('readline');

const DURACAO_TESTE = 10 * 60 * 1000; // 10 minutos
const INTERVALO_VERIFICACAO = 30 * 1000; // 30 segundos
const ARQUIVO_LOG = path.join(__dirname, 'dados/teste-estabilidade.log');

class MonitorEstabilidade {
    constructor() {
        this.dataInicio = new Date();
        this.erros = [];
        this.desconexoes = [];
        this.eventos = [];
    }

    async iniciar() {
        console.log('\n' + '='.repeat(70));
        console.log('🧪 TESTE DE ESTABILIDADE DO SISTEMA');
        console.log('='.repeat(70));
        console.log(`⏱️  Duração: ${DURACAO_TESTE / 1000 / 60} minutos`);
        console.log(`📊 Intervalo de verificação: ${INTERVALO_VERIFICACAO / 1000}s`);
        console.log(`📝 Log: ${ARQUIVO_LOG}`);
        console.log('='.repeat(70) + '\n');

        // Limpar log anterior
        await fs.writeFile(ARQUIVO_LOG, `TESTE INICIADO: ${this.dataInicio.toISOString()}\n\n`, 'utf8');

        // Monitorar stderr/stdout
        this.monitorarConsole();

        // Executar verificações periódicas
        const timeoutVerificacao = setInterval(() => this.verificar(), INTERVALO_VERIFICACAO);

        // Parar após duração do teste
        setTimeout(async () => {
            clearInterval(timeoutVerificacao);
            await this.finalizar();
        }, DURACAO_TESTE);
    }

    monitorarConsole() {
        const original_log = console.log;
        const original_error = console.error;
        const self = this;

        console.log = function(...args) {
            const msg = args.join(' ');
            original_log(...args);

            // Detectar erros
            if (msg.toLowerCase().includes('[erro]') || msg.toLowerCase().includes('[erroão]')) {
                self.erros.push({
                    timestamp: new Date(),
                    mensagem: msg
                });
            }

            // Detectar desconexões
            if (msg.toLowerCase().includes('desconectado') || msg.toLowerCase().includes('logout')) {
                self.desconexoes.push({
                    timestamp: new Date(),
                    mensagem: msg
                });
            }

            // Registrar evento importante
            if (msg.includes('[SUCESSO]') || msg.includes('[INFO]')) {
                self.eventos.push({
                    timestamp: new Date(),
                    mensagem: msg
                });
            }
        };

        console.error = function(...args) {
            const msg = args.join(' ');
            original_error(...args);
            self.erros.push({
                timestamp: new Date(),
                mensagem: msg,
                tipo: 'stderr'
            });
        };
    }

    async verificar() {
        const tempoDecorrido = new Date() - this.dataInicio;
        const minutos = Math.floor(tempoDecorrido / 1000 / 60);
        const segundos = Math.floor((tempoDecorrido / 1000) % 60);

        const status = `
⏱️  ${minutos}m ${segundos}s decorridos
📊 Erros detectados: ${this.erros.length}
🔄 Desconexões: ${this.desconexoes.length}
📝 Eventos: ${this.eventos.length}
        `;

        console.log(status);

        // Registrar no arquivo
        let logContent = `\n[${new Date().toISOString()}] ${minutos}m ${segundos}s\n`;
        logContent += `Erros: ${this.erros.length} | Desconexões: ${this.desconexoes.length} | Eventos: ${this.eventos.length}\n`;

        if (this.erros.length > 0) {
            logContent += '\n⚠️  ERROS RECENTES:\n';
            this.erros.slice(-3).forEach(e => {
                logContent += `  - ${e.mensagem.substring(0, 100)}...\n`;
            });
        }

        await fs.appendFile(ARQUIVO_LOG, logContent, 'utf8');
    }

    async finalizar() {
        const tempoTotal = new Date() - this.dataInicio;
        const minutos = tempoTotal / 1000 / 60;

        console.log('\n' + '='.repeat(70));
        console.log('✅ TESTE DE ESTABILIDADE FINALIZADO');
        console.log('='.repeat(70));
        console.log(`⏱️  Tempo total: ${minutos.toFixed(1)} minutos`);
        console.log(`📊 Erros: ${this.erros.length}`);
        console.log(`🔄 Desconexões: ${this.desconexoes.length}`);
        console.log(`📝 Eventos: ${this.eventos.length}`);

        // Análise
        if (this.desconexoes.length === 0) {
            console.log('\n✅ RESULTADO: SISTEMA ESTÁVEL (Nenhuma desconexão detectada)');
        } else if (this.desconexoes.length <= 2) {
            console.log('\n⚠️  RESULTADO: SISTEMA RAZOÁVEL (Poucas desconexões)');
        } else {
            console.log('\n❌ RESULTADO: SISTEMA INSTÁVEL (Muitas desconexões)');
        }

        // Salvar relatório
        let relatorio = `
RELATÓRIO FINAL DO TESTE DE ESTABILIDADE
=====================================

Data: ${this.dataInicio.toISOString()}
Duração: ${minutos.toFixed(1)} minutos

MÉTRICAS:
- Erros detectados: ${this.erros.length}
- Desconexões: ${this.desconexoes.length}
- Eventos registrados: ${this.eventos.length}

ANÁLISE:
${this.desconexoes.length === 0 ? '✅ Sistema manteve conexão estável durante todo o teste' : `❌ ${this.desconexoes.length} desconexões detectadas`}
${this.erros.length === 0 ? '✅ Nenhum erro registrado' : `⚠️  ${this.erros.length} erros registrados`}

DETALHES:
`;

        if (this.desconexoes.length > 0) {
            relatorio += '\nDESCONEXÕES:\n';
            this.desconexoes.forEach((d, i) => {
                relatorio += `${i + 1}. ${d.timestamp.toISOString()} - ${d.mensagem.substring(0, 80)}\n`;
            });
        }

        if (this.erros.length > 0) {
            relatorio += '\nERROS:\n';
            this.erros.forEach((e, i) => {
                relatorio += `${i + 1}. ${e.timestamp.toISOString()} - ${e.mensagem.substring(0, 80)}\n`;
            });
        }

        await fs.appendFile(ARQUIVO_LOG, '\n' + relatorio, 'utf8');

        console.log('\n📝 Relatório salvo em:', ARQUIVO_LOG);
        console.log('='.repeat(70) + '\n');

        process.exit(this.desconexoes.length === 0 ? 0 : 1);
    }
}

// Iniciar teste
const monitor = new MonitorEstabilidade();
monitor.iniciar();
