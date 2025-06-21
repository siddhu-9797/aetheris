#!/usr/bin/env python3
"""
Quick test of the improved interface and context system
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

def test_interface():
    print("🎨 Testing Improved Aetheris Chat Interface")
    print("=" * 45)
    
    # Test 1: Load the interface
    print("1. Loading interface...")
    response = session.get(CHAT_URL)
    
    # Check for key interface elements
    if "Aetheris Threat Intelligence" in response.text:
        print("   ✅ Main title loaded")
    else:
        print("   ❌ Main title missing")
    
    if "Welcome to Aetheris Threat Intelligence" in response.text:
        print("   ✅ Welcome message displayed")
    else:
        print("   ❌ Welcome message missing")
        
    if "quick-action-btn" in response.text:
        print("   ✅ Quick action buttons present")
    else:
        print("   ❌ Quick action buttons missing")
    
    # Test 2: Send a message to verify functionality
    print("\n2. Testing chat functionality...")
    chat_response = send_chat_message("Microsoft WEBDAV vulnerability")
    
    if "webdav" in chat_response.lower():
        print("   ✅ WEBDAV query response working")
    else:
        print("   ⚠️  WEBDAV query may need verification")
    
    # Test 3: Check for improved styling elements
    if "threat-dashboard" in response.text:
        print("   ✅ Modern dashboard styling applied")
    else:
        print("   ❌ Dashboard styling missing")
        
    if "typing-indicator" in response.text:
        print("   ✅ Typing indicator present")
    else:
        print("   ❌ Typing indicator missing")
    
    print("\n🎉 Interface testing complete!")
    print("Visit http://127.0.0.1:8000/llm/chat/ to see the improvements")

if __name__ == "__main__":
    test_interface()