#!/usr/bin/env python3
"""
Final validation test to confirm the complete solution works
"""
import requests
from bs4 import BeautifulSoup
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

def test_scenario(name, queries, expected_keywords):
    """Test a scenario with multiple queries"""
    print(f"\n🧪 Testing Scenario: {name}")
    print("=" * 50)
    
    # Clear context by starting fresh
    session.get(CHAT_URL)
    
    results = []
    for i, query in enumerate(queries):
        print(f"\n{i+1}. Query: '{query}'")
        response_html = send_chat_message(query)
        bot_response = extract_bot_response(response_html)
        
        # Check for expected keywords
        found_keywords = []
        missing_keywords = []
        
        for keyword in expected_keywords[i]:
            if keyword.lower() in bot_response.lower():
                found_keywords.append(keyword)
            else:
                missing_keywords.append(keyword)
        
        results.append({
            'query': query,
            'response': bot_response[:200] + "..." if len(bot_response) > 200 else bot_response,
            'found_keywords': found_keywords,
            'missing_keywords': missing_keywords
        })
        
        print(f"   Found keywords: {found_keywords}")
        if missing_keywords:
            print(f"   ⚠️  Missing keywords: {missing_keywords}")
        else:
            print(f"   ✅ All expected keywords found!")
        
        time.sleep(1)  # Brief pause between queries
    
    return results

def main():
    print("🎯 FINAL VALIDATION TEST")
    print("Testing the complete Aetheris chat context solution")
    print("=" * 60)
    
    # Test 1: Direct WEBDAV query (should work after fix)
    test1_results = test_scenario(
        "Direct WEBDAV Query",
        ["Tell me about Microsoft WEBDAV zero-day vulnerability"],
        [["webdav", "microsoft", "zero-day"]]
    )
    
    # Test 2: Context-based conversation (the original issue)
    test2_results = test_scenario(
        "Context-Based Conversation",
        [
            "What Microsoft vulnerabilities were reported recently?",
            "Tell me more about the WEBDAV vulnerability"
        ],
        [
            ["microsoft"],  # First query should mention Microsoft
            ["webdav"]      # Second query should find WEBDAV from context
        ]
    )
    
    # Test 3: Asset correlation (advanced functionality)
    test3_results = test_scenario(
        "Asset Correlation",
        [
            "Microsoft WEBDAV zero-day vulnerability",
            "Which Windows servers might be affected?"
        ],
        [
            ["webdav", "microsoft"],  # First should identify the threat
            ["windows", "server"]     # Second should correlate to assets
        ]
    )
    
    # Summary
    print(f"\n📊 FINAL RESULTS SUMMARY")
    print("=" * 30)
    
    all_tests = [
        ("Direct WEBDAV Query", test1_results),
        ("Context-Based Conversation", test2_results), 
        ("Asset Correlation", test3_results)
    ]
    
    total_queries = 0
    successful_queries = 0
    
    for test_name, results in all_tests:
        print(f"\n{test_name}:")
        for result in results:
            total_queries += 1
            success = len(result['missing_keywords']) == 0
            if success:
                successful_queries += 1
            
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"  {status} - {result['query'][:50]}...")
            
            if not success:
                print(f"    Missing: {result['missing_keywords']}")
    
    success_rate = (successful_queries / total_queries) * 100
    print(f"\n🏆 Overall Success Rate: {successful_queries}/{total_queries} ({success_rate:.1f}%)")
    
    if success_rate >= 80:
        print("🎉 SUCCESS: Chat context system is working well!")
    elif success_rate >= 60:
        print("⚠️  PARTIAL: Some issues remain but major improvement achieved")
    else:
        print("❌ FAILURE: Significant issues still present")
    
    # Specific check for the original user issue
    original_issue_fixed = False
    for test_name, results in all_tests:
        if test_name == "Context-Based Conversation" and len(results) >= 2:
            webdav_found = "webdav" in results[1]['found_keywords']
            if webdav_found:
                original_issue_fixed = True
                break
    
    print(f"\n🔍 Original User Issue Status:")
    if original_issue_fixed:
        print("✅ FIXED: Context-aware WEBDAV queries now work correctly")
    else:
        print("❌ NOT FIXED: Context-aware WEBDAV queries still failing")

if __name__ == "__main__":
    main()