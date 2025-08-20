#!/usr/bin/env python3
"""
Test Canvas API authentication with different URLs
"""

import requests
import os
from dotenv import load_dotenv

load_dotenv()

def test_canvas_auth(base_url, token):
    """Test Canvas API authentication"""
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test endpoints
    endpoints = [
        "/api/v1/users/self",
        "/api/v1/courses"
    ]
    
    print(f"\n🔍 Testing Canvas URL: {base_url}")
    print("-" * 50)
    
    for endpoint in endpoints:
        url = f"{base_url}{endpoint}"
        try:
            response = requests.get(url, headers=headers, timeout=10)
            print(f"✅ {endpoint}: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                if endpoint == "/api/v1/users/self":
                    print(f"   User: {data.get('name', 'Unknown')}")
                elif endpoint == "/api/v1/courses":
                    print(f"   Courses found: {len(data)}")
            else:
                print(f"   Error: {response.text[:100]}")
        except requests.exceptions.RequestException as e:
            print(f"❌ {endpoint}: Connection error - {e}")

def main():
    token = os.getenv("CANVAS_API_TOKEN")
    if not token:
        print("❌ No CANVAS_API_TOKEN found in .env file")
        return
    
    print(f"🔑 Testing with token: {token[:10]}...")
    
    # Common Canvas URLs to test
    canvas_urls = [
        "https://canvas.instructure.com",
        "https://canvas.instructure.co.uk",  # UK instance
        # Add more common Canvas URLs here if needed
    ]
    
    print("\n" + "=" * 60)
    print("🎯 CANVAS API AUTHENTICATION TEST")
    print("=" * 60)
    
    for url in canvas_urls:
        test_canvas_auth(url, token)
    
    print("\n" + "=" * 60)
    print("💡 If all tests fail:")
    print("1. Your token may have expired - regenerate it in Canvas")
    print("2. You may be using a different Canvas URL (school-specific)")
    print("3. Check if your Canvas instance URL is different")
    print("=" * 60)

if __name__ == "__main__":
    main()

# DEPRECATED: use python/scripts/test_canvas_auth.py instead.
