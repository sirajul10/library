from fastapi import FastAPI, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from typing import Annotated, Optional
import models
from models import Users, Books, Reservations, IssueRecords
from database import SessionLocal, engine
from fastapi.responses import JSONResponse
from router import admin, auth
from router.auth import get_current_user
from fastapi.middleware.cors import CORSMiddleware

# Initialize database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Configure CORS Middleware to allow requests from any application/domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all websites, mobile apps, and clients
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, DELETE, etc.)
    allow_headers=["*"],  # Allows all headers
)

# Include Routers
app.include_router(auth.router)
app.include_router(admin.router)

# Database Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]

# Helper to handle both object models and dictionary payloads from auth
def get_user_id(user):
    if hasattr(user, "id"):
        return user.id
    if isinstance(user, dict):
        return user.get("id")
    return None


@app.get("/books/all")
def get_all_books(db: db_dependency):
    books = db.query(Books).all()
    return books


@app.get("/books/{book_id}")
def get_specific(user: user_dependency, db: db_dependency, book_id: int):
    if user is None:
        raise HTTPException(status_code=401, detail="Failed Authentication")
    
    book = db.query(Books).filter(Books.id == book_id).first()
    if book is None:
        raise HTTPException(status_code=404, detail="Book Not Found")
    return book


@app.post("/reserve/{book_id}")
def book_reservation(user: user_dependency, db: db_dependency, book_id: int):
    if user is None:
        raise HTTPException(status_code=401, detail="Failed Authentication")
    
    book = db.query(Books).filter(Books.id == book_id).first()
    if book is None:
        raise HTTPException(status_code=404, detail="Book Not Found")
    
    user_id = get_user_id(user)
    
    reservation_model = Reservations(
        book_id=book_id,
        user_id=user_id,
        status="pending"
    )
    db.add(reservation_model)
    db.commit()
    
    return JSONResponse(status_code=201, content={"message": "Reservation Added Successfully"})


@app.delete("/reserve/cancel/{reservation_id}")
def cancel_reservation(user: user_dependency, db: db_dependency, reservation_id: int):
    if user is None:
        raise HTTPException(status_code=401, detail="Failed Authentication")

    reservation = db.query(Reservations).filter(Reservations.id == reservation_id).first()
    if reservation is None:
        raise HTTPException(status_code=404, detail="Reservation Not Found")

    reservation.status = "cancelled"
    db.commit()

    return JSONResponse(status_code=200, content={"message": "Reservation cancelled successfully"})


@app.get("/reserve/my")
def my_reservations(user: user_dependency, db: db_dependency):
    if user is None:
        raise HTTPException(status_code=401, detail="Failed Authentication")

    user_id = get_user_id(user)
    reservations = db.query(Reservations).filter(
        Reservations.user_id == user_id, 
        Reservations.status != "cancelled"
    ).all()

    return reservations


@app.get("/issue/my")
def get_my_issues(user: user_dependency, db: db_dependency):
    if user is None:
        raise HTTPException(status_code=401, detail="Failed Authentication")
    
    user_id = get_user_id(user)
    issues = db.query(IssueRecords).filter(
        IssueRecords.user_id == user_id,
        IssueRecords.status == "issued"
    ).all()

    return issues