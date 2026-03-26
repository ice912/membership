from fastapi import FastAPI, HTTPException, BackgroundTasks, Form
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr, validator
from datetime import date
import sqlite3
import re
from typing import Optional

app = FastAPI()

# In-memory store (replace with DB for production)
users_db = {}
login_attempts = {}


class UserSignUp(BaseModel):
    email: EmailStr
    password: str
    nickname: str
    birth_date: date
    gender: str
    phone: str
    agreed: bool

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8 or not re.search(r'[@_!#$%^&*()<>?/|}{~:]', v):
            raise ValueError('Password should be at least 8 letters long, including special characters.')
        return v

    @validator('birth_date')
    def check_adult(cls, v):
        today = date.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age < 19:
            raise ValueError('Those under age of 19 cannot be a member.')
        return v

    @validator('agreed')
    def must_agree(cls, v):
        if not v:
            raise ValueError('You must agree to the terms.')
        return v


class UserWithdraw(BaseModel):
    email: EmailStr
    password: str


# --- Routes ---

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("membership.html", "r", encoding="utf-8") as f:
        return f.read()


@app.post("/signup")
async def signup(user: UserSignUp):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    try:
        # 1. 데이터 삽입
        cursor.execute("""
            INSERT INTO users (email, password, nickname, birth_date, gender, phone, agreed)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user.email, user.password, user.nickname, str(user.birth_date), user.gender, user.phone, int(user.agreed)))
        
        # 2. ★매우 중요★ 이 줄이 없으면 파일에 저장되지 않습니다!
        conn.commit() 
        
        print(f"User {user.email} saved successfully!") # 로그 확인용
    except Exception as e:
        print(f"Database Error: {e}")
        conn.rollback() # 에러 시 취소
    finally:
        conn.close()
        
    return {"message": "Thank you for joining! Your data is saved."}


@app.post("/withdraw") # 또는 @app.post("/withdraw")
async def withdraw(email: str = Form(...), password: str = Form(...)):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    
    # 1. 해당 이메일과 비밀번호가 일치하는 사용자 확인
    cursor.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        # 여기서 에러가 발생한다면 입력값과 DB 값이 다른 것입니다.
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    
    # 2. 사용자 삭제
    cursor.execute("DELETE FROM users WHERE email = ?", (email,))
    conn.commit()
    conn.close()
    
    return {"message": "Your account has been successfully deleted."}


@app.post("/login")
async def login(email: str = Form(...), password: str = Form(...)):
    attempts = login_attempts.get(email, 0)
    if attempts >= 5:
        raise HTTPException(
            status_code=403,
            detail="The account is locked for 10 minutes. Renew your password through e-mail."
        )

    user = users_db.get(email)
    if not user or user['password'] != password:
        login_attempts[email] = attempts + 1
        raise HTTPException(status_code=401, detail="There is a mismatch.")

    login_attempts[email] = 0  # Reset on success
    return {"message": f"Welcome {user['nickname']}.", "token": "access_token"}