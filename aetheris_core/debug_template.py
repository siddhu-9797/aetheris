#!/usr/bin/env python3
"""
Debug what template is actually being served
"""
import requests

BASE_URL = "http://127.0.0.1:8000"
CHAT_URL = f"{BASE_URL}/llm/chat/"

def debug_template():
    session = requests.Session()
    response = session.get(CHAT_URL)
    
    print("🔍 Template Debug")
    print("=" * 40)
    print(f"Status: {response.status_code}")
    print(f"Content-Type: {response.headers.get('content-type')}")
    
    # Check for key template elements
    if "--primary-blue" in response.text:
        print("✅ CSS variables found")
    else:
        print("❌ CSS variables missing")
    
    if "sendMessage()" in response.text:
        print("✅ AJAX functions found") 
    else:
        print("❌ AJAX functions missing")
    
    if "threat-dashboard" in response.text:
        print("✅ Dashboard styling found")
    else:
        print("❌ Dashboard styling missing")
    
    # Save first 2000 chars to see what's actually loaded
    with open("template_debug.html", "w") as f:
        f.write(response.text)
    
    print(f"\n📄 Full template saved to template_debug.html")
    print(f"📏 Template size: {len(response.text)} characters")

if __name__ == "__main__":
    debug_template()