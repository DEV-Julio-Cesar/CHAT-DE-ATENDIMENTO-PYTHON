/**
 * =========================================================================
 * GERENCIADOR DE USUÁRIOS - SISTEMA DE CADASTRO DINÂMICO
 * =========================================================================
 * 
 * Este módulo gerencia usuários cadastrados dinamicamente no sistema.
 * Funcionalidades principais:
 * - Cadastro de novos usuários
 * - Validação de dados de usuário
 * - Armazenamento em arquivo JSON
 * - Cache em memória para performance
 * - Operações CRUD completas
 * 
 * Os usuários são armazenados tanto em memória (array) quanto em arquivo
 * para garantir persistência e performance.
 * 
 * @author Sistema Chat Atendimento
 * @version 2.0.0
 * @since 2024
 */

const fs = require('fs-extra');
const path = require('path');
const crypto = require('crypto');

// =========================================================================
// CONFIGURAÇÕES E CONSTANTES
// =========================================================================

/**
 * Caminho do arquivo de usuários
 */
const CAMINHO_ARQUIVO_USUARIOS = path.join(__dirname, '../../dados/usuarios-cadastrados.json');

/**
 * Cache em memória para melhor performance
 * @type {Array<Object>}
 */
let usuariosEmMemoria = [];

/**
 * Indica se o sistema foi inicializado
 */
let sistemaInicializado = false;

// =========================================================================
// FUNÇÕES DE INICIALIZAÇÃO
// =========================================================================

/**
 * Inicializa o sistema de gerenciamento de usuários
 * Carrega dados do arquivo e sincroniza com memória
 * 
 * @returns {Promise<void>}
 */
async function inicializarSistema() {
    try {
        console.log('[GerenciadorUsuarios] Inicializando sistema...');
        
        // Garante que o diretório existe
        await fs.ensureDir(path.dirname(CAMINHO_ARQUIVO_USUARIOS));
        
        // Verifica se o arquivo existe
        if (await fs.pathExists(CAMINHO_ARQUIVO_USUARIOS)) {
            console.log('[GerenciadorUsuarios] Carregando usuários do arquivo...');
            
            const dadosArquivo = await fs.readFile(CAMINHO_ARQUIVO_USUARIOS, 'utf8');
            usuariosEmMemoria = JSON.parse(dadosArquivo) || [];
            
            console.log(`[GerenciadorUsuarios] ✅ ${usuariosEmMemoria.length} usuários carregados`);
        } else {
            console.log('[GerenciadorUsuarios] Arquivo não existe, criando novo...');
            
            usuariosEmMemoria = [];
            await salvarUsuariosNoArquivo();
            
            console.log('[GerenciadorUsuarios] ✅ Sistema inicializado com array vazio');
        }
        
        sistemaInicializado = true;
        
    } catch (erro) {
        console.error('[GerenciadorUsuarios] ❌ Erro na inicialização:', erro);
        usuariosEmMemoria = []; // Fallback para array vazio
        sistemaInicializado = true;
    }
}

/**
 * Salva o array de usuários no arquivo JSON
 * 
 * @returns {Promise<boolean>} true se salvou com sucesso
 */
async function salvarUsuariosNoArquivo() {
    try {
        const dadosJson = JSON.stringify(usuariosEmMemoria, null, 2);
        await fs.writeFile(CAMINHO_ARQUIVO_USUARIOS, dadosJson, 'utf8');
        
        console.log(`[GerenciadorUsuarios] 💾 ${usuariosEmMemoria.length} usuários salvos no arquivo`);
        return true;
        
    } catch (erro) {
        console.error('[GerenciadorUsuarios] ❌ Erro ao salvar arquivo:', erro);
        return false;
    }
}

// =========================================================================
// FUNÇÕES UTILITÁRIAS
// =========================================================================

/**
 * Gera um hash seguro da senha usando crypto
 * 
 * @param {string} senha - Senha em texto puro
 * @returns {string} Hash da senha
 */
function gerarHashSenha(senha) {
    return crypto.createHash('sha256').update(senha).digest('hex');
}

/**
 * Gera um ID único baseado em timestamp
 * 
 * @returns {string} ID único
 */
function gerarIdUnico() {
    return `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Valida formato de email
 * 
 * @param {string} email - Email a ser validado
 * @returns {boolean} true se for válido
 */
function validarFormatoEmail(email) {
    const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return regex.test(email);
}

/**
 * Garante que o sistema está inicializado
 */
async function garantirInicializacao() {
    if (!sistemaInicializado) {
        await inicializarSistema();
    }
}

// =========================================================================
// OPERAÇÕES CRUD DE USUÁRIOS
// =========================================================================

/**
 * Cria um novo usuário no sistema
 * 
 * @param {string} nomeUsuario - Nome de usuário único
 * @param {string} senha - Senha do usuário
 * @param {string} email - Email do usuário
 * @param {string} nomeCompleto - Nome completo do usuário
 * @returns {Promise<Object>} Resultado da operação
 * 
 * @example
 * const resultado = await criarUsuario('joao123', 'minhasenha', 'joao@email.com', 'João Silva');
 * if (resultado.sucesso) {
 *   console.log('Usuário criado!');
 * }
 */
async function criarUsuario(nomeUsuario, senha, email, nomeCompleto) {
    try {
        await garantirInicializacao();
        
        console.log(`[GerenciadorUsuarios] Criando usuário: ${nomeUsuario}`);
        
        // Validações básicas
        if (!nomeUsuario || !senha || !email || !nomeCompleto) {
            return { 
                sucesso: false, 
                mensagem: 'Todos os campos são obrigatórios.' 
            };
        }
        
        if (nomeUsuario.length < 3) {
            return { 
                sucesso: false, 
                mensagem: 'Nome de usuário deve ter pelo menos 3 caracteres.' 
            };
        }
        
        if (senha.length < 4) {
            return { 
                sucesso: false, 
                mensagem: 'Senha deve ter pelo menos 4 caracteres.' 
            };
        }
        
        if (!validarFormatoEmail(email)) {
            return { 
                sucesso: false, 
                mensagem: 'Formato de email inválido.' 
            };
        }
        
        // Verifica se usuário já existe
        const usuarioExistente = usuariosEmMemoria.find(
            u => u.nomeUsuario.toLowerCase() === nomeUsuario.toLowerCase()
        );
        
        if (usuarioExistente) {
            console.log(`[GerenciadorUsuarios] ❌ Usuário já existe: ${nomeUsuario}`);
            return { 
                sucesso: false, 
                mensagem: 'Nome de usuário já está em uso.' 
            };
        }
        
        // Verifica se email já existe
        const emailExistente = usuariosEmMemoria.find(
            u => u.email.toLowerCase() === email.toLowerCase()
        );
        
        if (emailExistente) {
            console.log(`[GerenciadorUsuarios] ❌ Email já cadastrado: ${email}`);
            return { 
                sucesso: false, 
                mensagem: 'Email já está em uso.' 
            };
        }
        
        // Cria o novo usuário
        const novoUsuario = {
            id: gerarIdUnico(),
            nomeUsuario: nomeUsuario.trim(),
            senha: gerarHashSenha(senha),
            email: email.trim().toLowerCase(),
            nomeCompleto: nomeCompleto.trim(),
            dataCriacao: new Date().toISOString(),
            ultimoLogin: null,
            ativo: true
        };
        
        // Adiciona ao array em memória
        usuariosEmMemoria.push(novoUsuario);
        
        // Salva no arquivo
        const salvouArquivo = await salvarUsuariosNoArquivo();
        
        if (salvouArquivo) {
            console.log(`[GerenciadorUsuarios] ✅ Usuário criado: ${nomeUsuario} (ID: ${novoUsuario.id})`);
            return { 
                sucesso: true, 
                mensagem: 'Usuário cadastrado com sucesso!',
                usuario: {
                    id: novoUsuario.id,
                    nomeUsuario: novoUsuario.nomeUsuario,
                    email: novoUsuario.email,
                    nomeCompleto: novoUsuario.nomeCompleto,
                    dataCriacao: novoUsuario.dataCriacao
                }
            };
        } else {
            // Remove do array se não conseguiu salvar
            usuariosEmMemoria.pop();
            return { 
                sucesso: false, 
                mensagem: 'Erro ao salvar usuário no arquivo.' 
            };
        }
        
    } catch (erro) {
        console.error('[GerenciadorUsuarios] ❌ Erro ao criar usuário:', erro);
        return { 
            sucesso: false, 
            mensagem: 'Erro interno do sistema.' 
        };
    }
}

/**
 * Lista todos os usuários cadastrados (sem senhas)
 * 
 * @returns {Promise<Array<Object>>} Array com usuários
 */
async function listarUsuarios() {
    try {
        await garantirInicializacao();
        
        // Retorna usuários sem a senha por segurança
        return usuariosEmMemoria.map(usuario => ({
            id: usuario.id,
            nomeUsuario: usuario.nomeUsuario,
            email: usuario.email,
            nomeCompleto: usuario.nomeCompleto,
            dataCriacao: usuario.dataCriacao,
            ultimoLogin: usuario.ultimoLogin,
            ativo: usuario.ativo
        }));
        
    } catch (erro) {
        console.error('[GerenciadorUsuarios] ❌ Erro ao listar usuários:', erro);
        return [];
    }
}

/**
 * Busca usuário por nome de usuário
 * 
 * @param {string} nomeUsuario - Nome do usuário
 * @returns {Promise<Object|null>} Usuário encontrado ou null
 */
async function buscarUsuarioPorNome(nomeUsuario) {
    try {
        await garantirInicializacao();
        
        const usuario = usuariosEmMemoria.find(
            u => u.nomeUsuario.toLowerCase() === nomeUsuario.toLowerCase()
        );
        
        if (usuario) {
            // Retorna sem a senha
            return {
                id: usuario.id,
                nomeUsuario: usuario.nomeUsuario,
                email: usuario.email,
                nomeCompleto: usuario.nomeCompleto,
                dataCriacao: usuario.dataCriacao,
                ultimoLogin: usuario.ultimoLogin,
                ativo: usuario.ativo
            };
        }
        
        return null;
        
    } catch (erro) {
        console.error('[GerenciadorUsuarios] ❌ Erro ao buscar usuário:', erro);
        return null;
    }
}

/**
 * Valida a senha de um usuário
 * 
 * @param {string} nomeUsuario - Nome do usuário
 * @param {string} senha - Senha a ser validada
 * @returns {Promise<boolean>} true se a senha estiver correta
 */
async function validarSenhaUsuario(nomeUsuario, senha) {
    try {
        await garantirInicializacao();
        
        const usuario = usuariosEmMemoria.find(
            u => u.nomeUsuario.toLowerCase() === nomeUsuario.toLowerCase()
        );
        
        if (usuario && usuario.ativo) {
            const hashSenha = gerarHashSenha(senha);
            
            if (hashSenha === usuario.senha) {
                // Atualiza último login
                usuario.ultimoLogin = new Date().toISOString();
                await salvarUsuariosNoArquivo();
                
                return true;
            }
        }
        
        return false;
        
    } catch (erro) {
        console.error('[GerenciadorUsuarios] ❌ Erro ao validar senha:', erro);
        return false;
    }
}

/**
 * Remove um usuário do sistema
 * 
 * @param {string} nomeUsuario - Nome do usuário a ser removido
 * @returns {Promise<Object>} Resultado da operação
 */
async function removerUsuario(nomeUsuario) {
    try {
        await garantirInicializacao();
        
        const indiceUsuario = usuariosEmMemoria.findIndex(
            u => u.nomeUsuario.toLowerCase() === nomeUsuario.toLowerCase()
        );
        
        if (indiceUsuario === -1) {
            return { 
                sucesso: false, 
                mensagem: 'Usuário não encontrado.' 
            };
        }
        
        // Remove do array
        const usuarioRemovido = usuariosEmMemoria.splice(indiceUsuario, 1)[0];
        
        // Salva no arquivo
        const salvouArquivo = await salvarUsuariosNoArquivo();
        
        if (salvouArquivo) {
            console.log(`[GerenciadorUsuarios] 🗑️ Usuário removido: ${nomeUsuario}`);
            return { 
                sucesso: true, 
                mensagem: 'Usuário removido com sucesso!' 
            };
        } else {
            // Restaura usuário se não conseguiu salvar
            usuariosEmMemoria.splice(indiceUsuario, 0, usuarioRemovido);
            return { 
                sucesso: false, 
                mensagem: 'Erro ao salvar alterações.' 
            };
        }
        
    } catch (erro) {
        console.error('[GerenciadorUsuarios] ❌ Erro ao remover usuário:', erro);
        return { 
            sucesso: false, 
            mensagem: 'Erro interno do sistema.' 
        };
    }
}

/**
 * Obtém estatísticas dos usuários
 * 
 * @returns {Promise<Object>} Estatísticas do sistema
 */
async function obterEstatisticasUsuarios() {
    try {
        await garantirInicializacao();
        
        const total = usuariosEmMemoria.length;
        const ativos = usuariosEmMemoria.filter(u => u.ativo).length;
        const inativos = total - ativos;
        
        // Usuário mais recente
        const maisRecente = usuariosEmMemoria.reduce((anterior, atual) => {
            return new Date(atual.dataCriacao) > new Date(anterior?.dataCriacao || 0) 
                ? atual 
                : anterior;
        }, null);
        
        return {
            totalUsuarios: total,
            usuariosAtivos: ativos,
            usuariosInativos: inativos,
            usuarioMaisRecente: maisRecente?.nomeUsuario || 'Nenhum',
            ultimaAtualizacao: new Date().toISOString()
        };
        
    } catch (erro) {
        console.error('[GerenciadorUsuarios] ❌ Erro ao obter estatísticas:', erro);
        return {
            totalUsuarios: 0,
            usuariosAtivos: 0,
            usuariosInativos: 0,
            usuarioMaisRecente: 'Erro',
            erro: erro.message
        };
    }
}

// =========================================================================
// INICIALIZAÇÃO AUTOMÁTICA
// =========================================================================

// Inicializa o sistema automaticamente quando o módulo for carregado
inicializarSistema();

// =========================================================================
// EXPORTAÇÕES
// =========================================================================

module.exports = {
    criarUsuario,
    listarUsuarios,
    buscarUsuarioPorNome,
    validarSenhaUsuario,
    removerUsuario,
    obterEstatisticasUsuarios,
    inicializarSistema
};

console.log('[GerenciadorUsuarios] Módulo de gerenciamento de usuários carregado');
