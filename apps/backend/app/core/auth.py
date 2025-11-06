"""
Sistema de autenticação JWT com access e refresh tokens.
Inclui hashing de senhas com bcrypt.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db, User

# Contexto para hashing de senhas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security scheme para FastAPI
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha corresponde ao hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Gera hash bcrypt da senha"""
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Cria um JWT access token.

    Args:
        data: Dados a serem encodados no token (ex: {"sub": user_id})
        expires_delta: Tempo de expiração customizado

    Returns:
        Token JWT assinado
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({
        "exp": expire,
        "type": "access"
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Cria um JWT refresh token com duração maior.

    Args:
        data: Dados a serem encodados no token

    Returns:
        Refresh token JWT assinado
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({
        "exp": expire,
        "type": "refresh"
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decodifica e valida um JWT token.

    Args:
        token: Token JWT a ser decodificado

    Returns:
        Payload do token decodificado

    Raises:
        HTTPException: Se o token for inválido ou expirado
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token inválido: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency para obter o usuário atual a partir do token JWT.

    Args:
        credentials: Credenciais HTTP Bearer extraídas do header
        db: Sessão do banco de dados

    Returns:
        Objeto User do usuário autenticado

    Raises:
        HTTPException: Se o token for inválido ou usuário não existir
    """
    token = credentials.credentials
    payload = decode_token(token)

    # Verificar tipo do token
    token_type = payload.get("type")
    if token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tipo de token inválido. Use um access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Obter user_id do payload (convertendo de string para int)
    user_id_str: Optional[str] = payload.get("sub")
    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token não contém identificador de usuário",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identificador de usuário inválido no token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Buscar usuário no banco
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verificar se usuário está ativo
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo"
        )

    return user


def verify_refresh_token(token: str) -> Dict[str, Any]:
    """
    Valida um refresh token e retorna seu payload.

    Args:
        token: Refresh token a ser validado

    Returns:
        Payload do token

    Raises:
        HTTPException: Se o token não for válido
    """
    payload = decode_token(token)

    # Verificar tipo do token
    token_type = payload.get("type")
    if token_type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tipo de token inválido. Use um refresh token.",
        )

    return payload


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """
    Autentica um usuário com email e senha.

    Args:
        db: Sessão do banco de dados
        email: Email do usuário
        password: Senha em texto plano

    Returns:
        Objeto User se autenticado, None caso contrário
    """
    user = db.query(User).filter(User.email == email).first()

    if not user:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    return user


def create_tokens_for_user(user: User) -> Dict[str, str]:
    """
    Cria access e refresh tokens para um usuário.

    Args:
        user: Objeto User

    Returns:
        Dict com access_token e refresh_token
    """
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }
