import os
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig

load_dotenv()

class Settings:
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_FROM = os.getenv("MAIL_FROM")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
    MAIL_SERVER = os.getenv("MAIL_SERVER")
    MAIL_STARTTLS = os.getenv("MAIL_STARTTLS", "True") == "True"
    MAIL_SSL_TLS = os.getenv("MAIL_SSL_TLS", "False") == "True"
    USE_CREDENTIALS = os.getenv("USE_CREDENTIALS", "True") == "True"

conf = ConnectionConfig(
    MAIL_USERNAME=Settings.MAIL_USERNAME,
    MAIL_PASSWORD=Settings.MAIL_PASSWORD,
    MAIL_FROM=Settings.MAIL_FROM,
    MAIL_PORT=Settings.MAIL_PORT,
    MAIL_SERVER=Settings.MAIL_SERVER,
    MAIL_STARTTLS=Settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=Settings.MAIL_SSL_TLS,
    USE_CREDENTIALS=Settings.USE_CREDENTIALS
)

fm = FastMail(conf)

async def send_email_to_user(email: str, code: str, username: str = None, template_name: str = "email-template.html"):

    if not username:
        username = email.split('@')[0]
        
    templates_path = os.path.join(os.path.dirname(__file__), "../../templates")
    
    env = Environment(loader=FileSystemLoader(templates_path))

    try:
        template = env.get_template(template_name)
    except Exception as e:
        raise FileNotFoundError(f"Template {template_name} không tồn tại tại {templates_path}") from e
    
    html_content = template.render(username=username, code=code)
    
    message = MessageSchema(
        subject="Thông tin xác thực tài khoản CodeMate của bạn",
        recipients=[email],  
        body=html_content,  
        subtype="html"   
    )

    await fm.send_message(message)
