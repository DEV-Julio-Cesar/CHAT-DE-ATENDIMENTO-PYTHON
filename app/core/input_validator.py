"""
Validador de Input e Sanitização
Proteção contra XSS, SQL Injection, Path Traversal, etc.
"""
import re
import html
from typing import Optional, List, Tuple
from urllib.parse import urlparse
import phonenumbers
from email_validator import validate_email, EmailNotValidError


class InputValidator:
    """
    Validador e sanitizador de entrada de dados
    Proteção contra ataques comuns
    """
    
    # Padrões perigosos
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
        r"(--|;|\/\*|\*\/|xp_|sp_)",
        r"(\bOR\b.*=.*|1=1|'=')",
    ]
    
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe",
        r"<object",
        r"<embed",
    ]
    
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",
        r"\.\.",
        r"%2e%2e",
        r"\.\.\\",
    ]
    
    @staticmethod
    def sanitize_string(
        text: str,
        max_length: int = 1000,
        allow_html: bool = False
    ) -> str:
        """
        Sanitizar string removendo caracteres perigosos
        
        Args:
            text: Texto a sanitizar
            max_length: Comprimento máximo
            allow_html: Se permite HTML (será escapado)
        
        Returns:
            Texto sanitizado
        """
        if not text:
            return ""
        
        # Remover caracteres de controle (exceto \n, \r, \t)
        sanitized = ''.join(
            char for char in text
            if ord(char) >= 32 or char in '\n\r\t'
        )
        
        # Escapar HTML se não permitido
        if not allow_html:
            sanitized = html.escape(sanitized)
        
        # Limitar tamanho
        return sanitized[:max_length]
    
    @staticmethod
    def validate_email(email: str) -> Tuple[bool, Optional[str]]:
        """
        Validar formato de email
        
        Returns:
            (is_valid: bool, normalized_email: Optional[str])
        """
        try:
            validation = validate_email(email, check_deliverability=False)
            return True, validation.normalized
        except EmailNotValidError as e:
            return False, None
    
    @staticmethod
    def validate_phone(phone: str, region: str = "BR") -> Tuple[bool, Optional[str]]:
        """
        Validar e normalizar número de telefone
        
        Args:
            phone: Número de telefone
            region: Código do país (BR, US, etc)
        
        Returns:
            (is_valid: bool, normalized_phone: Optional[str])
        """
        try:
            parsed = phonenumbers.parse(phone, region)
            if phonenumbers.is_valid_number(parsed):
                normalized = phonenumbers.format_number(
                    parsed,
                    phonenumbers.PhoneNumberFormat.E164
                )
                return True, normalized
            return False, None
        except phonenumbers.NumberParseException:
            return False, None
    
    @staticmethod
    def validate_url(url: str, allowed_schemes: List[str] = None) -> Tuple[bool, str]:
        """
        Validar URL
        
        Args:
            url: URL a validar
            allowed_schemes: Esquemas permitidos (http, https, etc)
        
        Returns:
            (is_valid: bool, error_message: str)
        """
        if not url:
            return False, "URL is empty"
        
        if allowed_schemes is None:
            allowed_schemes = ["http", "https"]
        
        try:
            parsed = urlparse(url)
            
            # Verificar esquema
            if parsed.scheme not in allowed_schemes:
                return False, f"URL scheme must be one of: {', '.join(allowed_schemes)}"
            
            # Verificar domínio
            if not parsed.netloc:
                return False, "URL must have a valid domain"
            
            # Verificar caracteres perigosos
            dangerous_chars = ["<", ">", '"', "'", "`"]
            if any(char in url for char in dangerous_chars):
                return False, "URL contains dangerous characters"
            
            return True, ""
            
        except Exception as e:
            return False, f"Invalid URL: {str(e)}"
    
    @staticmethod
    def validate_filename(filename: str) -> Tuple[bool, str]:
        """
        Validar nome de arquivo
        
        Returns:
            (is_valid: bool, error_message: str)
        """
        if not filename:
            return False, "Filename is empty"
        
        # Caracteres perigosos
        dangerous_chars = ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|', '\0']
        if any(char in filename for char in dangerous_chars):
            return False, "Filename contains dangerous characters"
        
        # Verificar extensão
        if '.' not in filename:
            return False, "Filename must have an extension"
        
        # Verificar comprimento
        if len(filename) > 255:
            return False, "Filename is too long"
        
        return True, ""
    
    @staticmethod
    def detect_sql_injection(text: str) -> bool:
        """
        Detectar tentativa de SQL injection
        
        Returns:
            True se detectado padrão suspeito
        """
        text_upper = text.upper()
        
        for pattern in InputValidator.SQL_INJECTION_PATTERNS:
            if re.search(pattern, text_upper, re.IGNORECASE):
                return True
        
        return False
    
    @staticmethod
    def detect_xss(text: str) -> bool:
        """
        Detectar tentativa de XSS
        
        Returns:
            True se detectado padrão suspeito
        """
        for pattern in InputValidator.XSS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    @staticmethod
    def detect_path_traversal(path: str) -> bool:
        """
        Detectar tentativa de path traversal
        
        Returns:
            True se detectado padrão suspeito
        """
        for pattern in InputValidator.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, path, re.IGNORECASE):
                return True
        
        return False
    
    @staticmethod
    def sanitize_sql_input(text: str) -> str:
        """
        Sanitizar input para SQL (use sempre parametrização!)
        Esta é uma camada extra de proteção
        """
        # Remover caracteres perigosos
        dangerous = ["'", '"', ";", "--", "/*", "*/", "xp_", "sp_"]
        sanitized = text
        
        for char in dangerous:
            sanitized = sanitized.replace(char, "")
        
        return sanitized
    
    @staticmethod
    def validate_uuid(uuid_string: str) -> bool:
        """Validar formato UUID"""
        pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        return bool(re.match(pattern, uuid_string.lower()))
    
    @staticmethod
    def validate_integer(value: str, min_val: int = None, max_val: int = None) -> Tuple[bool, Optional[int]]:
        """
        Validar e converter para inteiro
        
        Returns:
            (is_valid: bool, value: Optional[int])
        """
        try:
            int_value = int(value)
            
            if min_val is not None and int_value < min_val:
                return False, None
            
            if max_val is not None and int_value > max_val:
                return False, None
            
            return True, int_value
            
        except (ValueError, TypeError):
            return False, None
    
    @staticmethod
    def sanitize_html(html_content: str, allowed_tags: List[str] = None) -> str:
        """
        Sanitizar HTML permitindo apenas tags seguras
        
        Args:
            html_content: Conteúdo HTML
            allowed_tags: Tags permitidas (padrão: nenhuma)
        
        Returns:
            HTML sanitizado
        """
        try:
            import bleach
            
            if allowed_tags is None:
                # Sem tags por padrão (apenas texto)
                allowed_tags = []
            
            # Atributos permitidos por tag
            allowed_attributes = {
                'a': ['href', 'title'],
                'img': ['src', 'alt'],
            }
            
            # Protocolos permitidos
            allowed_protocols = ['http', 'https', 'mailto']
            
            cleaned = bleach.clean(
                html_content,
                tags=allowed_tags,
                attributes=allowed_attributes,
                protocols=allowed_protocols,
                strip=True
            )
            
            return cleaned
            
        except ImportError:
            # Fallback: remover todas as tags
            return re.sub(r'<[^>]+>', '', html_content)


# Instância global
input_validator = InputValidator()
