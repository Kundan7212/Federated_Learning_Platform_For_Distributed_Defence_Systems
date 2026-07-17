from __future__ import annotations
from typing import Optional
from sqlalchemy.orm import Session
from app.core.security import hash_password, verify_password
from app.models.user import User


class AuthService:

    @staticmethod
    def register_user(db: Session, email: str, username: str, password: str) -> User:
        existing = db.query(User).filter(User.email == email.lower()).first()
        if existing:
            raise ValueError(f"Email '{email}' is already registered")

        user = User(
            email=email.lower(),
            username=username,
            hashed_password=hash_password(password),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
        user = db.query(User).filter(User.email == email.lower()).first()
        if user is None:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email.lower()).first()
