import uuid
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from backend.config import settings
from backend.db.database import get_db
from backend.db.models import User, EmergencyContact
from backend.models.schemas import (
    UserCreate, UserResponse, TokenData, GuestLoginResponse,
    LoginResponse, EmergencyContact as EmergencySchema, EmergencyResponse
)

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=7)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


async def get_current_user(
    token: str = Depends(lambda: None),
    db: Session = Depends(get_db)
) -> Optional[User]:
    if not token:
        return None
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            return None
        token_data = TokenData(user_id=user_id)
    except JWTError:
        return None
    
    user = db.query(User).filter(User.id == token_data.user_id).first()
    return user


@router.post("/guest", response_model=GuestLoginResponse)
async def guest_login():
    device_id = "guest_" + str(uuid.uuid4())
    return {"device_id": device_id, "mode": "guest"}


@router.post("/register", response_model=LoginResponse)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    db_user = get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user.password)
    new_user = User(
        email=user.email,
        password_hash=hashed_password,
        nickname=user.nickname or user.email.split("@")[0]
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    token = create_access_token(data={"sub": new_user.id})
    
    return {"token": token, "user_id": new_user.id, "nickname": new_user.nickname}


@router.post("/login", response_model=LoginResponse)
async def login(user: UserCreate, db: Session = Depends(get_db)):
    db_user = get_user_by_email(db, email=user.email)
    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    token = create_access_token(data={"sub": db_user.id})
    
    return {"token": token, "user_id": db_user.id, "nickname": db_user.nickname}


@router.get("/user/me", response_model=UserResponse)
async def get_user_info(current_user: User = Depends(get_current_user)):
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return current_user


@router.put("/user/emergency", response_model=EmergencyResponse)
async def update_emergency_contact(
    contact: EmergencySchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    existing = db.query(EmergencyContact).filter(
        EmergencyContact.user_id == current_user.id
    ).first()
    
    if existing:
        existing.name = contact.name
        existing.phone = contact.phone
    else:
        new_contact = EmergencyContact(
            user_id=current_user.id,
            name=contact.name,
            phone=contact.phone
        )
        db.add(new_contact)
    
    db.commit()
    
    return {"success": True}