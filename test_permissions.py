#!/usr/bin/env python3
"""
Check Canvas permissions and try alternative course update methods
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_canvas_permissions():
    base_url = os.getenv("CANVAS_BASE_URL")
    token = os.getenv("CANVAS_API_TOKEN")
    
    headers = {"Authorization": f"Bearer {token}"}
    course_id = "12625554"
    
    print("🔍 Testing Canvas API permissions...")
    print("=" * 50)
    
    # Test basic course access
    print("1. Basic course access:")
    response = requests.get(f"{base_url}/api/v1/courses/{course_id}", headers=headers)
    print(f"   GET /courses/{course_id}: {response.status_code}")
    
    # Test course update (without event)
    print("\\n2. Basic course update:")
    data = {'course[name]': 'LLMTest'}
    response = requests.put(f"{base_url}/api/v1/courses/{course_id}", headers=headers, data=data)
    print(f"   PUT /courses/{course_id} (name update): {response.status_code}")
    if response.status_code != 200:
        print(f"   Error: {response.text[:200]}")
    
    # Test settings update
    print("\\n3. Course settings:")
    response = requests.get(f"{base_url}/api/v1/courses/{course_id}/settings", headers=headers)
    print(f"   GET /courses/{course_id}/settings: {response.status_code}")
    
    # Test account permissions
    print("\\n4. Account access:")
    response = requests.get(f"{base_url}/api/v1/accounts/self", headers=headers)
    print(f"   GET /accounts/self: {response.status_code}")
    
    # Test user permissions
    print("\\n5. User profile:")
    response = requests.get(f"{base_url}/api/v1/users/self", headers=headers)
    if response.status_code == 200:
        user = response.json()
        print(f"   User: {user.get('name')}")
        print(f"   Login ID: {user.get('login_id')}")
    
    print("\\n" + "=" * 50)
    print("💡 Course Publishing Information:")
    print("- Course publishing typically requires admin or teacher privileges")
    print("- Some Canvas instances restrict publishing to administrators only")
    print("- You can manually publish the course through the Canvas web interface:")
    print("  1. Go to your course in Canvas")
    print("  2. Click 'Settings' in the course navigation")
    print("  3. Click 'Publish' button at the top of the page")
    print("=" * 50)

if __name__ == "__main__":
    test_canvas_permissions()

# DEPRECATED: use python/scripts/test_permissions.py instead.
