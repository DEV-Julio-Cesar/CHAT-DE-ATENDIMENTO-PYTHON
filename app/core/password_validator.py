"""
Validador de Senha Forte
Implementa política de segurança de senhas conforme NIST e OWASP
"""
import re
from typing import List, Tuple
from app.core.config import settings


class PasswordValidator:
    """
    Validador de senha com políticas de segurança
    
    Regras:
    - Mínimo 12 caracteres
    - Pelo menos 1 letra maiúscula
    - Pelo menos 1 letra minúscula
    - Pelo menos 1 número
    - Pelo menos 1 caractere especial
    - Não pode conter senhas comuns
    - Não pode conter informações pessoais
    """
    
    # Lista de senhas comuns (top 100 mais usadas)
    COMMON_PASSWORDS = {
        "password", "123456", "123456789", "12345678", "12345", "1234567",
        "password1", "password123", "admin", "admin123", "root", "root123",
        "qwerty", "abc123", "letmein", "welcome", "monkey", "dragon",
        "master", "sunshine", "princess", "football", "shadow", "michael",
        "jennifer", "computer", "trustno1", "superman", "batman", "iloveyou",
        "Password1!", "Admin123!", "Welcome1!", "Qwerty123!", "Password@123",
        "Admin@123", "Welcome@123", "P@ssw0rd", "P@ssword1", "Passw0rd!",
        # Adicione mais conforme necessário
    }
    
    @staticmethod
    def validate(password: str, user_info: dict = None) -> Tuple[bool, List[str]]:
        """
        Validar senha contra política de segurança
        
        Args:
            password: Senha a validar
            user_info: Informações do usuário (nome, email, etc) para evitar uso
        
        Returns:
            (is_valid: bool, errors: List[str])
        """
        errors = []
        
        # 1. Comprimento mínimo
        if len(password) < settings.PASSWORD_MIN_LENGTH:
            errors.append(
                f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters long"
            )
        
        # 2. Letra maiúscula
        if settings.PASSWORD_REQUIRE_UPPERCASE and not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least one uppercase letter")
        
        # 3. Letra minúscula
        if settings.PASSWORD_REQUIRE_LOWERCASE and not re.search(r"[a-z]", password):
            errors.append("Password must contain at least one lowercase letter")
        
        # 4. Número
        if settings.PASSWORD_REQUIRE_NUMBERS and not re.search(r"\d", password):
            errors.append("Password must contain at least one number")
        
        # 5. Caractere especial
        if settings.PASSWORD_REQUIRE_SPECIAL and not re.search(
            r"[!@#$%^&*(),.?\":{}|<>_\-+=\[\]\\\/;'`~]", password
        ):
            errors.append("Password must contain at least one special character")
        
        # 6. Senhas comuns
        if password.lower() in PasswordValidator.COMMON_PASSWORDS:
            errors.append("Password is too common. Please choose a stronger password")
        
        # 7. Não pode conter informações pessoais
        if user_info:
            personal_info = [
                user_info.get("nome", "").lower(),
                user_info.get("email", "").split("@")[0].lower(),
                user_info.get("username", "").lower(),
            ]
            
            for info in personal_info:
                if info and len(info) > 3 and info in password.lower():
                    errors.append(
                        "Password cannot contain your personal information"
                    )
                    break
        
        # 8. Não pode ser sequencial
        if PasswordValidator._is_sequential(password):
            errors.append("Password cannot contain sequential characters")
        
        # 9. Não pode ter caracteres repetidos demais
        if PasswordValidator._has_too_many_repeats(password):
            errors.append("Password has too many repeated characters")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def _is_sequential(password: str) -> bool:
        """Verificar se senha contém sequências óbvias"""
        sequences = [
            "abcdefghijklmnopqrstuvwxyz",
            "0123456789",
            "qwertyuiop",
            "asdfghjkl",
            "zxcvbnm"
        ]
        
        password_lower = password.lower()
        
        for seq in sequences:
            # Verificar sequências de 4+ caracteres
            for i in range(len(seq) - 3):
                if seq[i:i+4] in password_lower or seq[i:i+4][::-1] in password_lower:
                    return True
        
        return False
    
    @staticmethod
    def _has_too_many_repeats(password: str) -> bool:
        """Verificar se tem muitos caracteres repetidos"""
        # Não permitir mais de 3 caracteres iguais consecutivos
        for i in range(len(password) - 3):
            if password[i] == password[i+1] == password[i+2] == password[i+3]:
                return True
        
        return False
    
    @staticmethod
    def generate_strong_password(length: int = 16) -> str:
        """
        Gerar senha forte aleatória
        
        Args:
            length: Comprimento da senha (mínimo 12)
        
        Returns:
            Senha forte gerada
        """
        import secrets
        import string
        
        if length < 12:
            length = 12
        
        # Garantir pelo menos um de cada tipo
        password = [
            secrets.choice(string.ascii_uppercase),
            secrets.choice(string.ascii_lowercase),
            secrets.choice(string.digits),
            secrets.choice("!@#$%^&*()_+-=[]{}|;:,.<>?")
        ]
        
        # Preencher o resto
        all_chars = string.ascii_letters + string.digits + "!@#$%^&*()_+-=[]{}|;:,.<>?"
        password.extend(secrets.choice(all_chars) for _ in range(length - 4))
        
        # Embaralhar
        secrets.SystemRandom().shuffle(password)
        
        return ''.join(password)
    
    @staticmethod
    def calculate_strength(password: str) -> Tuple[int, str]:
        """
        Calcular força da senha (0-100)
        
        Returns:
            (score: int, level: str)
        """
        score = 0
        
        # Comprimento (até 30 pontos)
        score += min(len(password) * 2, 30)
        
        # Variedade de caracteres (até 40 pontos)
        if re.search(r"[a-z]", password):
            score += 10
        if re.search(r"[A-Z]", password):
            score += 10
        if re.search(r"\d", password):
            score += 10
        if re.search(r"[!@#$%^&*(),.?\":{}|<>_\-+=\[\]\\\/;'`~]", password):
            score += 10
        
        # Complexidade (até 30 pontos)
        unique_chars = len(set(password))
        score += min(unique_chars * 2, 30)
        
        # Penalidades
        if PasswordValidator._is_sequential(password):
            score -= 20
        if PasswordValidator._has_too_many_repeats(password):
            score -= 20
        if password.lower() in PasswordValidator.COMMON_PASSWORDS:
            score -= 30
        
        score = max(0, min(100, score))
        
        # Classificar
        if score >= 80:
            level = "Very Strong"
        elif score >= 60:
            level = "Strong"
        elif score >= 40:
            level = "Medium"
        elif score >= 20:
            level = "Weak"
        else:
            level = "Very Weak"
        
        return score, level


# Instância global
password_validator = PasswordValidator()
