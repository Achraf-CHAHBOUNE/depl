from dotenv import load_dotenv

load_dotenv()

class Config:
    SERVICE_NAME = "ocr-service"
    VERSION = "1.0.0"

config = Config()
