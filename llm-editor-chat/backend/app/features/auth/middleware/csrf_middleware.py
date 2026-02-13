from fastapi_csrf_protect import CsrfProtect
from pydantic import BaseModel

class CsrfSettings(BaseModel):
    secret_key: str = "your_super_secret_csrf_key_change_this" # IMPORTANT: Change this in production!

@CsrfProtect.load_config
def get_csrf_config():
    return CsrfSettings()

# The 'csrf_protect' instance that will be imported in main.py
# This is the name 'csrf_protection' that main.py is trying to import
csrf_protection = CsrfProtect()