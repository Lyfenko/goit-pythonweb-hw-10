from sqlalchemy import Column, Integer, String, Date
from database import Base
from passlib.hash import bcrypt


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), index=True)
    surname = Column(String(50), index=True)
    email = Column(String(50), unique=True, index=True)
    phone = Column(String(20))
    birthday = Column(Date)
    additional_data = Column(String(200))


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(50), unique=True, index=True)
    password_hash = Column(String(128))

    def set_password(self, password: str):
        self.password_hash = bcrypt.hash(password)

    def check_password(self, password: str):
        return bcrypt.verify(password, self.password_hash)
