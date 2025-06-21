#!/usr/bin/env python3
"""
Test specifically for WEBDAV context issue
"""
import requests
from bs4 import BeautifulSoup
import re
import time

# Django server URL
BASE_URL = "http://127.0.0.1:8000"
CHAT_URL = f"{BASE_URL}/llm/chat/"

# Create a session to maintain cookies (Django session)
session = requests.Session()

def get_csrf_token():
    """Get CSRF token from the chat page"""
    response = session.get(CHAT_URL)
    soup = BeautifulSoup(response.text, 'html.parser')
    csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})
    if csrf_token:
        return csrf_token['value']
    return None

def send_chat_message(message):
    """Send a chat message and return the response"""
    csrf_token = get_csrf_token()
    data = {
        'csrfmiddlewaretoken': csrf_token,
        'user_input': message
    }
    
    response = session.post(CHAT_URL, data=data)
    return response.text

def extract_bot_response(html_content):
    """Extract the bot's response from the HTML"""
    soup = BeautifulSoup(html_content, 'html.parser')
    chat_bubbles = soup.find_all('div', class_='chat-bubble chat-bot')
    if chat_bubbles:
        # Get the last bot response
        last_response = chat_bubbles[-1]
        return last_response.get_text(strip=True)
    return "No bot response found"

def main():
    print("🔍 Testing WEBDAV Context-Aware Search")
    print("=" * 50)
    
    # Clear any existing context by starting fresh
    session.get(CHAT_URL)
    
    # First query - ask about Microsoft threats specifically
    print("\n1. Setting context with Microsoft threats...")
    response1_html = send_chat_message("What Microsoft threats were reported in the last 24 hours?")
    bot_response1 = extract_bot_response(response1_html)
    print(f"Response 1 preview: {bot_response1[:150]}...")
    
    # Check if Microsoft threats are mentioned
    if "microsoft" in bot_response1.lower() and ("webdav" in bot_response1.lower() or "zero-day" in bot_response1.lower()):
        print("✓ First response mentions Microsoft threats (possibly including WEBDAV)")
    else:
        print("⚠️  First response may not mention expected Microsoft threats")
    
    time.sleep(2)
    
    # Second query - ask specifically about WEBDAV now that context is set
    print("\n2. Testing context-aware WEBDAV query...")
    response2_html = send_chat_message("Tell me more about the WEBDAV vulnerability you mentioned")
    bot_response2 = extract_bot_response(response2_html)
    print(f"Response 2 preview: {bot_response2[:200]}...")
    
    # Check if WEBDAV is properly discussed
    if "webdav" in bot_response2.lower() and "microsoft" in bot_response2.lower():
        print("✅ SUCCESS: Context-aware search found WEBDAV vulnerability!")
    elif "cannot find" in bot_response2.lower() or "no information" in bot_response2.lower():
        print("❌ FAILED: Still cannot find WEBDAV information despite context")
    else:
        print("? UNCLEAR: Check response manually")
    
    # Third query - test asset correlation
    print("\n3. Testing asset correlation...")
    response3_html = send_chat_message("Which of our Windows servers might be affected by this WEBDAV issue?")
    bot_response3 = extract_bot_response(response3_html)
    print(f"Response 3 preview: {bot_response3[:200]}...")
    
    if "windows" in bot_response3.lower() and ("webdav" in bot_response3.lower() or "server" in bot_response3.lower()):
        print("✅ Asset correlation working with context")
    else:
        print("⚠️  Asset correlation may need improvement")

if __name__ == "__main__":
    main()