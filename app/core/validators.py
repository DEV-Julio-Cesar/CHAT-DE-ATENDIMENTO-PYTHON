"""
Validadores de dados sensíveis
"""
import re
from typing import Optional


def validar_cpf(cpf: str) -> bool:
    """
    Validar CPF com dígitos verificadores
    
    Args:
        cpf: CPF com ou sem formatação
        
    Returns:
        True se CPF válido
    """
    # Remover formatação
    cpf = re.sub(r'\D', '', cpf)
    
    # Verificar tamanho
    if len(cpf) != 11:
        return False
    
    # Verificar se todos os dígitos são iguais (CPF inválido)
    if cpf == cpf[0] * 11:
        return False
    
    # Calcular primeiro dígito verificador
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    digito1 = 11 - (soma % 11)
    if digito1 > 9:
        digito1 = 0
    
    if int(cpf[9]) != digito1:
        return False
    
    # Calcular segundo dígito verificador
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    digito2 = 11 - (soma % 11)
    if digito2 > 9:
        digito2 = 0
    
    return int(cpf[10]) == digito2


def formatar_cpf(cpf: str) -> Optional[str]:
    """
    Formatar CPF para padrão XXX.XXX.XXX-XX
    
    Args:
        cpf: CPF sem formatação
        
    Returns:
        CPF formatado ou None se inválido
    """
    cpf_limpo = re.sub(r'\D', '', cpf)
    
    if not validar_cpf(cpf_limpo):
        return None
    
    return f"{cpf_limpo[:3]}.{cpf_limpo[3:6]}.{cpf_limpo[6:9]}-{cpf_limpo[9:]}"


def sanitizar_cpf(cpf: str) -> Optional[str]:
    """
    Sanitizar e validar CPF
    
    Args:
        cpf: CPF com ou sem formatação
        
    Returns:
        CPF limpo (apenas números) ou None se inválido
    """
    cpf_limpo = re.sub(r'\D', '', cpf)
    
    if not validar_cpf(cpf_limpo):
        return None
    
    return cpf_limpo


def validar_cnpj(cnpj: str) -> bool:
    """
    Validar CNPJ com dígitos verificadores
    
    Args:
        cnpj: CNPJ com ou sem formatação
        
    Returns:
        True se CNPJ válido
    """
    # Remover formatação
    cnpj = re.sub(r'\D', '', cnpj)
    
    # Verificar tamanho
    if len(cnpj) != 14:
        return False
    
    # Verificar se todos os dígitos são iguais
    if cnpj == cnpj[0] * 14:
        return False
    
    # Calcular primeiro dígito verificador
    multiplicadores1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * multiplicadores1[i] for i in range(12))
    digito1 = 11 - (soma % 11)
    if digito1 > 9:
        digito1 = 0
    
    if int(cnpj[12]) != digito1:
        return False
    
    # Calcular segundo dígito verificador
    multiplicadores2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * multiplicadores2[i] for i in range(13))
    digito2 = 11 - (soma % 11)
    if digito2 > 9:
        digito2 = 0
    
    return int(cnpj[13]) == digito2


def validar_cpf_ou_cnpj(documento: str) -> bool:
    """
    Validar CPF ou CNPJ
    
    Args:
        documento: CPF ou CNPJ com ou sem formatação
        
    Returns:
        True se válido
    """
    documento_limpo = re.sub(r'\D', '', documento)
    
    if len(documento_limpo) == 11:
        return validar_cpf(documento_limpo)
    elif len(documento_limpo) == 14:
        return validar_cnpj(documento_limpo)
    else:
        return False
