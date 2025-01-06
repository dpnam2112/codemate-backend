import os
from fastapi_mail import ConnectionConfig
from dotenv import load_dotenv

# Load .env file
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
