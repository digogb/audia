"""
Rotas de autenticação: registro, login e refresh de tokens.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from loguru import logger

from app.core.database import get_db, User
from app.core.auth import (
    get_password_hash,
    authenticate_user,
    create_tokens_for_user,
    verify_refresh_token,
    create_access_token,
    get_current_user
)
from app.models.schemas import (
    UserRegister,
    UserLogin,
    TokenResponse,
    RefreshTokenRequest,
    UserResponse
)

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Registra um novo usuário.

    Args:
        user_data: Dados do usuário (email, username, password)
        db: Sessão do banco de dados

    Returns:
        Tokens de acesso (access_token e refresh_token)

    Raises:
        HTTPException 400: Se email ou username já existir
    """
    logger.info(f"Tentativa de registro: {user_data.email}")

    # Verificar se email já existe
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        logger.warning(f"Email já existe: {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já está em uso"
        )

    # Verificar se username já existe
    existing_username = db.query(User).filter(
        User.username == user_data.username
    ).first()
    if existing_username:
        logger.warning(f"Username já existe: {user_data.username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username já está em uso"
        )

    # Criar novo usuário
    hashed_password = get_password_hash(user_data.password)

    new_user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password,
        is_active=True
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info(f"Usuário criado com sucesso: {new_user.email} (ID: {new_user.id})")

    # Gerar tokens
    tokens = create_tokens_for_user(new_user)

    return TokenResponse(**tokens)


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Autentica um usuário e retorna tokens.

    Args:
        credentials: Email e senha
        db: Sessão do banco de dados

    Returns:
        Tokens de acesso (access_token e refresh_token)

    Raises:
        HTTPException 401: Se credenciais forem inválidas
    """
    logger.info(f"Tentativa de login: {credentials.email}")

    # Autenticar usuário
    user = authenticate_user(db, credentials.email, credentials.password)

    if not user:
        logger.warning(f"Falha no login: {credentials.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.info(f"Login bem-sucedido: {user.email} (ID: {user.id})")

    # Gerar tokens
    tokens = create_tokens_for_user(user)

    return TokenResponse(**tokens)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Renova o access token usando um refresh token válido.

    Args:
        refresh_data: Refresh token
        db: Sessão do banco de dados

    Returns:
        Novo access_token (mantém o mesmo refresh_token)

    Raises:
        HTTPException 401: Se refresh token for inválido
    """
    logger.info("Tentativa de refresh de token")

    # Validar refresh token
    payload = verify_refresh_token(refresh_data.refresh_token)

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido"
        )

    # Buscar usuário
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo"
        )

    logger.info(f"Token renovado para usuário: {user.email}")

    # Criar novo access token
    new_access_token = create_access_token(data={"sub": user.id})

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=refresh_data.refresh_token,  # Mantém o mesmo refresh token
        token_type="bearer"
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Retorna informações do usuário autenticado.

    Args:
        current_user: Usuário atual (injetado via dependency)

    Returns:
        Dados do usuário
    """
    return UserResponse.from_orm(current_user)
