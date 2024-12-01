from typing import Optional
from datetime import date
from pydantic import BaseModel


class UserBase(BaseModel):
    email: str


class UserCreate(UserBase):
    password: str
    is_active: bool = True
    is_verified: bool = False


class User(UserBase):
    id: int
    is_active: bool = True
    is_verified: bool = False
    contacts: Optional[list] = []

    class Config:
        orm_mode = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


class ContactBase(BaseModel):
    name: str
    surname: str
    email: str
    phone: Optional[str] = None
    birthday: Optional[date] = None
    additional_data: Optional[str] = None


class ContactCreate(ContactBase):
    pass


class ContactUpdate(ContactBase):
    pass


class Contact(ContactBase):
    id: int

    class Config:
        orm_mode = True
