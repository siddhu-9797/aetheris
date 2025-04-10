import os
import sys

# Setup Django context manually
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aetheris_core.settings")

from django.conf import settings
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import google.generativeai as genai

import django
django.setup()

GEMINI_API_KEY = settings.GEMINI_API_KEY

# Configure Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)

if not GEMINI_API_KEY:
    raise ValueError("Missing Google Gemini API key. Set it in environment or Django settings.")

# Configure the Gemini client
genai.configure(api_key=GEMINI_API_KEY)

# Retry on quota errors or rate limit issues
@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=2, max=10),
    retry=retry_if_exception_type(Exception)
)
def call_gemini(prompt: str, model_name: str = "gemini-2.0-flash") -> str:
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"[!] Gemini API call failed: {e}")
        raise
