#!/usr/bin/env python3
"""
Script to test the chat context issue by simulating the user's scenario
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
    if not csrf_token:
        print("Failed to get CSRF token")
        return None
    
    data = {
        'csrfmiddlewaretoken': csrf_token,
        'user_input': message
    }
    
    print(f"\n=== SENDING MESSAGE ===")
    print(f"Message: {message}")
    print(f"CSRF Token: {csrf_token[:20]}...")
    
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
    print("🤖 Testing Aetheris Chat Context Issue")
    print("=" * 50)
    
    # First message - ask about threats in last 24 hours
    print("\n1. Testing first query (should mention threats)...")
    response1_html = send_chat_message("any threats in the last 24 hours?")
    if response1_html:
        bot_response1 = extract_bot_response(response1_html)
        print(f"\nBot Response 1 (first 200 chars):")
        print(bot_response1[:200] + "..." if len(bot_response1) > 200 else bot_response1)
        
        # Look for specific threat mentions
        if "webdav" in bot_response1.lower() or "microsoft" in bot_response1.lower():
            print("✓ First response mentions relevant threats")
        else:
            print("⚠️  First response doesn't mention expected threats")
    
    # Wait a moment
    time.sleep(2)
    
    # Second message - follow up about specific threat (this is where context should be used)
    print("\n2. Testing follow-up query (should maintain context)...")
    response2_html = send_chat_message("Any affected assets regarding the WEBDAV Zero-Day?")
    if response2_html:
        bot_response2 = extract_bot_response(response2_html)
        print(f"\nBot Response 2 (first 200 chars):")
        print(bot_response2[:200] + "..." if len(bot_response2) > 200 else bot_response2)
        
        # Check if context is maintained
        if "webdav" in bot_response2.lower() or "microsoft" in bot_response2.lower():
            print("✓ Second response maintains context about WEBDAV")
        elif "fortinet" in bot_response2.lower():
            print("❌ Context LOST! Responding about Fortinet instead of WEBDAV")
        else:
            print("? Second response unclear - check manually")

if __name__ == "__main__":
    main()