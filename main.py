import uuid
from typing import List
from fastapi import FastAPI, Depends, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi_limiter.depends import RateLimiter
from sqlalchemy.orm import Session
from database import SessionLocal, engine, redis_client
import models
import crud
import schemas

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# CORS (Cross-Origin Resource Sharing) middleware to allow requests from any origin
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


# Dependency to get a database session for each request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/users/", response_model=schemas.User, tags=["Користувачі"])
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=409, detail="User already registered")
    return crud.create_user(db=db, user=user)


@app.post("/token/", tags=["Користувачі"])
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    user = crud.authenticate_user(
        db, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    access_token = crud.create_access_token(email=user.email)
    refresh_token = crud.create_refresh_token(email=user.email)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@app.post("/refresh/", tags=["Користувачі"])
async def refresh_token(access_token: str, db: Session = Depends(get_db)):
    email = crud.verify_token(access_token)
    if not email:
        raise HTTPException(status_code=401, detail="Invalid access token")
    new_access_token = crud.get_current_user_token(access_token)
    if not new_access_token:
        raise HTTPException(status_code=401, detail="Invalid access token")
    return {"access_token": new_access_token, "token_type": "bearer"}


@app.get("/verify/{token}", tags=["Користувачі"])
async def verify_email(token: str, db: Session = Depends(get_db)):
    email = crud.verify_token(token)
    if not email:
        raise HTTPException(status_code=401, detail="Invalid verification token")

    user = crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_verified = True
    db.commit()

    return {"message": "Email verified successfully"}


@app.post("/reset-password/", tags=["Користувачі"])
async def reset_password(
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    user = crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Generate a password reset token
    reset_token = str(uuid.uuid4())

    # Send the password reset email
    crud.send_password_reset_email(user.email, reset_token)

    return {"message": "Password reset email sent successfully"}


@app.post("/reset-password/{reset_token}/", tags=["Користувачі"])
async def update_password(
    reset_token: str,
    new_password: str = Form(...),
    db: Session = Depends(get_db)
):
    email = crud.verify_token(reset_token)
    if not email:
        raise HTTPException(status_code=401, detail="Invalid reset token")

    user = crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update the user's password
    user.set_password(new_password)
    db.commit()

    # Remove the cached user details
    redis_client.delete(email)

    return {"message": "Password updated successfully"}


@app.get("/contacts/", response_model=List[schemas.Contact], tags=["Контакти"])
def read_contacts_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    user = crud.get_current_user(token=token, db=db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid access token")
    contacts = crud.get_user_contacts(db, user_id=user.id, skip=skip, limit=limit)
    return contacts


@app.post(
    "/contacts/", response_model=schemas.Contact, status_code=201, tags=["Контакти"]
)
def create_contact(
    contact: schemas.ContactCreate,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    user = crud.get_current_user(token=token, db=db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid access token")
    return crud.create_contact(db=db, contact=contact)


@app.get(
    "/contacts/",
    response_model=List[schemas.Contact],
    tags=["Контакти"],
    dependencies=[Depends(RateLimiter(times=10, minutes=1))],
)
def read_contacts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    contacts = crud.get_contacts(db, skip=skip, limit=limit)
    return contacts


@app.get("/contacts/{contact_id}", response_model=schemas.Contact, tags=["Контакти"])
def read_contact(contact_id: int, db: Session = Depends(get_db)):
    db_contact = crud.get_contact(db, contact_id=contact_id)
    if db_contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return db_contact


@app.put("/contacts/{contact_id}", response_model=schemas.Contact, tags=["Контакти"])
def update_contact(
    contact_id: int, contact: schemas.ContactUpdate, db: Session = Depends(get_db)
):
    db_contact = crud.get_contact(db, contact_id=contact_id)
    if db_contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return crud.update_contact(db=db, db_contact=db_contact, contact=contact)


@app.delete("/contacts/{contact_id}", response_model=schemas.Contact, tags=["Контакти"])
def delete_contact(contact_id: int, db: Session = Depends(get_db)):
    db_contact = crud.get_contact(db, contact_id=contact_id)
    if db_contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return crud.delete_contact(db=db, db_contact=db_contact)


@app.get("/contacts/search/", response_model=List[schemas.Contact], tags=["Контакти"])
def search_contacts(query: str, db: Session = Depends(get_db)):
    contacts = crud.search_contacts(db, query=query)
    return contacts


@app.get("/contacts/birthday/", response_model=List[schemas.Contact], tags=["Контакти"])
def birthday_contacts(db: Session = Depends(get_db)):
    contacts = crud.birthday_contacts(db)
    return contacts
