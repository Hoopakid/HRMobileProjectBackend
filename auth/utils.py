import os
import smtplib
from email.message import EmailMessage
from sqlalchemy import select

import jwt
import secrets
import starlette.status as status
import random

from datetime import *
from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from models.models import Users
from settings import (
    mail_username,
    mail_server,
    mail_port,
    mail_password,
)

load_dotenv()
secret_key = os.environ.get("SECRET_KEY")
algorithm = "HS256"
security = HTTPBearer()


def generate_token(user_id: int):
    jti_access = str(secrets.token_urlsafe(32))
    jti_refresh = str(secrets.token_urlsafe(32))
    data_access_token = {
        "token_type": "access",
        "exp": datetime.utcnow() + timedelta(days=7),
        "user_id": user_id,
        "jti": jti_access,
    }
    data_refresh_token = {
        "token_type": "refresh",
        "exp": datetime.utcnow() + timedelta(days=30),
        "user_id": user_id,
        "jti": jti_refresh,
    }
    access_token = jwt.encode(data_access_token, secret_key, algorithm)
    refresh_token = jwt.encode(data_refresh_token, secret_key, algorithm)

    return {"access_token": access_token, "refresh_token": refresh_token}


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
        )

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )


def get_email_objects(user_email, password: str):
    email = EmailMessage()
    email["Subject"] = f"Introducing"
    email["From"] = mail_username
    email["To"] = user_email

    email.set_content(
        f"""
        <html>
        <head>
            <style>
                .email-body {{
                    font-family: Arial, sans-serif;
                    font-size: 16px;
                    line-height: 1.6;
                    padding: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="email-body">
                <p>Assalomu alaykum,</p>

                <p>Tabriklaymiz! Siz The Wolf ilovasiga muvaffaqiyatli ro'yxatdan o'tdingiz!</p>

                <p>The Wolf ilovasi sizga o'z ta'lim va o'quv jarayonlaringizni boshlashda va barcha o'quv materiallariga kirishda yordam beradi.</p>

                <p>Boshlash uchun, quyidagi havolani bosing va dasturni yuklab oling</p>

                <p><a href="https://play.google.com/store/apps/details?id=com.tencent.ig">App Store</a> | <a href="https://play.google.com/store/apps/details?id=com.tencent.ig">Google Play</a></p>
                    
                <p>Va ro'yxatdan o'ting</p>
                <p>🔑 Login: {user_email}</p>
                <p>🔒 Parol: {password}</p>
                
                <p>Omad !</p>

                <p>Hasan<br>SEO<br>The Wolf (Miilliard)</p>
            </div>
        </body>
        </html>
        """,
        subtype="html",
    )
    return email


def send_mail(email: str, password: str):
    email = get_email_objects(email, password)
    with smtplib.SMTP_SSL(mail_server, mail_port) as server:
        server.login(mail_username, mail_password)
        server.send_message(email)


def generate_six_numbers_code():
    code = ""
    for _ in range(6):
        code += str(random.randint(0, 9))
    return int(code)


def get_email_objects_for_forget_password(user_email: str, code: int, first_name: str):
    email = EmailMessage()
    email["Subject"] = f"Change Password"
    email["From"] = mail_username
    email["To"] = user_email

    email.set_content(
        f"""
            <html>
<head>
    <style>
        body {{
            font-family: Arial, sans-serif;
            background-color: #f4f4f4;
            color: #333;
            margin: 0;
            padding: 0;
        }}
        .container {{
            max-width: 600px;
            margin: 20px auto;
            padding: 20px;
            background-color: #fff;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}
        h1 {{
            color: #333;
            text-align: center;
        }}
        p {{
            margin-bottom: 20px;
            line-height: 1.6;
        }}
        .code {{
            background-color: #f0f0f0;
            padding: 10px 20px;
            border-radius: 6px;
            text-align: center;
            font-size: 24px;
            margin: 20px 0;
        }}
        .footer {{
            text-align: center;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Salom {first_name}</h1>
        <p>Parolingizni tiklash uchun quyidagi kodni kiriting:</p>
        <div class="code">{code}</div>
        <div class="footer">
            <p>Rahmat,</p>
            <p>The Wolf Jamoasi</p>
        </div>

        <p align='center'><a href="https://play.google.com/store/apps/details?id=com.tencent.ig">App Store</a> | <a href="https://play.google.com/store/apps/details?id=com.tencent.ig">Google Play</a></p>
    </div>
</body>
</html>

        """,
        subtype="html",
    )
    return email


def send_mail_for_forget_password(email: str, first_name: str):
    code = generate_six_numbers_code()
    email = get_email_objects_for_forget_password(email, code, first_name)
    with smtplib.SMTP_SSL(mail_server, mail_port) as server:
        server.login(mail_username, mail_password)
        server.send_message(email)
    return code


async def get_user_data(session, user_id):
    user_query = select(Users).where(Users.id == user_id)
    user__data = await session.execute(user_query)
    user_data = user__data.scalars().one()
    return user_data
