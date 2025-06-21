#!/usr/bin/env python3
"""
Test that directly asks about WEBDAV to see the response
"""
import requests
from bs4 import BeautifulSoup

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
    print("🎯 Direct WEBDAV Test")
    print("=" * 30)
    
    # Direct query about WEBDAV
    print("Testing direct WEBDAV query...")
    response_html = send_chat_message("Tell me about Microsoft WEBDAV zero-day vulnerability")
    bot_response = extract_bot_response(response_html)
    
    print(f"\nBot Response:")
    print(bot_response)
    
    # Check if WEBDAV is mentioned
    if "webdav" in bot_response.lower():
        print("\n✅ SUCCESS: WEBDAV vulnerability found and discussed!")
    else:
        print("\n❌ FAILED: WEBDAV vulnerability not found in response")
    
    # Check if specific CVE or details are mentioned
    if "cve" in bot_response.lower() or "patch" in bot_response.lower():
        print("✅ Additional details (CVE/patches) mentioned")
    else:
        print("⚠️  No specific vulnerability details mentioned")

if __name__ == "__main__":
    main()