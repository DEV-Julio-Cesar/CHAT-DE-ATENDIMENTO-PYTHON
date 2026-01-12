// src/infraestrutura/auditoria.js
// Registro de eventos de auditoria em arquivo texto estruturado JSON lines.

const fs = require('fs-extra');
const path = require('path');
const AUDIT_DIR = path.join(__dirname, '..', '..', 'dados');
const AUDIT_PATH = path.join(AUDIT_DIR, 'auditoria.log');

function logAudit(event, { user = null, details = null } = {}) {
  const registro = {
    timestamp: new Date().toISOString(),
    event,
    user: user || 'sistema',
    details: details || {}
  };
  try {
    // Cria diretório de forma síncrona
    fs.ensureDirSync(AUDIT_DIR);
    fs.appendFileSync(AUDIT_PATH, JSON.stringify(registro) + '\n');
  } catch (e) {
    // Falha silenciosa - não interrompe o fluxo
  }
}

module.exports = { logAudit };
