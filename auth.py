from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext
from pydantic import BaseModel,EmailStr, Field

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker,Session
from sqlalchemy import Column, Integer, String, Boolean
from dotenv import load_dotenv
import os
from sqlalchemy.exc import IntegrityError

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# --- SQLAlchemy setup ---
# Create database engine and session maker for PostgreSQL connection
Base = declarative_base()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- User model for SQLAlchemy ---
# Define User table schema for database
class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True,autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String(100), nullable=True)
    disabled = Column(Boolean, default=False)

# Create the table if it doesn't exist
Base.metadata.create_all(bind=engine)


load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not set in environment variables")

# --- JWT configuration ---
# Secret key, algorithm, and token expiration settings for JWT
SECRET_KEY = SECRET_KEY # to get a string like this run: openssl rand -hex 32
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Token expires in 30 minutes


# --- Pydantic models ---
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class User(BaseModel):
    username: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = None


class UserInDB(User):
    hashed_password: str
    
class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str | None = None


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for extracting the "Authorization: Bearer <token>" header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# --- Database dependency ---
def get_db():
    """Provide a database session/connection 
    for each request and ensure proper cleanup"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        
# --- Authentication functions ---

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against the stored hashed password"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def get_user(db: Session, username: str):
    """Retrieve a user from the PostgreSQL database."""
    user = db.query(UserDB).filter(UserDB.username == username).first()
    if user:
        return UserInDB(
            username=user.username,
            email=user.email,
            hashed_password=user.hashed_password,
            full_name=user.full_name,
            disabled=user.disabled
        )
    return None


def authenticate_user(db: Session, username: str, password: str):
    """Authenticate user by username and password"""
    user = get_user(db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """
    Create a JWT access token.
    `data` should include the user identifier (usually `sub`).
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# --- Dependency functions ---
# --- Database functions ---
def create_user(db: Session, user_create: UserCreate):
    """Create a new user in the PostgreSQL database."""
    hashed_password = get_password_hash(user_create.password)
    new_user = UserDB(
        username = user_create.username,
        email = user_create.email,
        hashed_password=hashed_password,
        full_name = user_create.full_name,
        disabled=False
    )
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user.username
    
    except IntegrityError as e:
        db.rollback()
        if "users_email_key" in str(e):
            raise HTTPException(status_code=400, detail="Email already exists")
        raise HTTPException(status_code=400, detail="Username already exists")
            
    
async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: Annotated[Session, Depends(get_db)]) -> UserInDB:
    """
    Extract the current user from the JWT token.
    Raises 401 if the token is invalid or user does not exist.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except InvalidTokenError:
        raise credentials_exception
    user = get_user(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    Ensure the current user is active.
    Raises 400 if the account is disabled.
    """
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user