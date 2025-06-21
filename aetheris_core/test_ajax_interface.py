#!/usr/bin/env python3
"""
Test the new AJAX chat interface
"""
import requests
from bs4 import BeautifulSoup
import time

BASE_URL = "http://127.0.0.1:8000"
CHAT_URL = f"{BASE_URL}/llm/chat/"

session = requests.Session()

def get_csrf_token():
    """Get CSRF token from the chat page"""
    response = session.get(CHAT_URL)
    soup = BeautifulSoup(response.text, 'html.parser')
    csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})
    if csrf_token:
        return csrf_token['value']
    return None

def test_ajax_functionality():
    print("🚀 Testing AJAX Chat Interface")
    print("=" * 40)
    
    # Test 1: Load the interface and check for professional styling
    print("1. Loading professional interface...")
    response = session.get(CHAT_URL)
    
    if "Aetheris Threat Intelligence" in response.text:
        print("   ✅ Professional title loaded")
    else:
        print("   ❌ Title missing")
    
    if "--primary-blue: #2563eb" in response.text:
        print("   ✅ Professional CSS variables loaded")
    else:
        print("   ❌ Professional styling missing")
    
    if "sendMessage()" in response.text:
        print("   ✅ AJAX JavaScript functions present")
    else:
        print("   ❌ AJAX functionality missing")
    
    # Test 2: Send AJAX message
    print("\n2. Testing AJAX message sending...")
    csrf_token = get_csrf_token()
    
    ajax_data = {
        'csrfmiddlewaretoken': csrf_token,
        'user_input': 'Microsoft vulnerabilities',
        'ajax': '1'
    }
    
    headers = {
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': csrf_token
    }
    
    try:
        ajax_response = session.post(CHAT_URL, data=ajax_data, headers=headers)
        
        if ajax_response.headers.get('content-type', '').startswith('application/json'):
            print("   ✅ AJAX response returned JSON")
            
            json_data = ajax_response.json()
            if json_data.get('success'):
                print("   ✅ AJAX request successful")
                print(f"   📊 Message count: {json_data.get('message_count', 0)}")
                if json_data.get('response_html'):
                    print("   ✅ HTML response received")
                else:
                    print("   ❌ No HTML response")
            else:
                print("   ❌ AJAX request failed")
        else:
            print("   ❌ Non-JSON response received")
            
    except Exception as e:
        print(f"   ❌ AJAX test failed: {e}")
    
    # Test 3: Clear context via AJAX
    print("\n3. Testing AJAX context clearing...")
    clear_data = {
        'csrfmiddlewaretoken': csrf_token,
        'clear_context': '1',
        'ajax': '1'
    }
    
    try:
        clear_response = session.post(CHAT_URL, data=clear_data, headers=headers)
        
        if clear_response.headers.get('content-type', '').startswith('application/json'):
            clear_json = clear_response.json()
            if clear_json.get('success') and clear_json.get('message_count') == 0:
                print("   ✅ AJAX context clearing successful")
            else:
                print("   ❌ Context clearing failed")
        else:
            print("   ❌ Non-JSON response for context clear")
            
    except Exception as e:
        print(f"   ❌ Context clear test failed: {e}")
    
    print("\n🎉 AJAX interface testing complete!")
    print("🌐 Visit http://127.0.0.1:8000/llm/chat/ to experience the professional interface")

if __name__ == "__main__":
    test_ajax_functionality()