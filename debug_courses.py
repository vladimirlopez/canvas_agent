#!/usr/bin/env python3
"""
Detailed Canvas courses investigation
"""

import requests
import os
from dotenv import load_dotenv
import json

load_dotenv()

def test_courses_detailed():
    """Test Canvas courses API with detailed output"""
    token = os.getenv("CANVAS_API_TOKEN")
    base_url = os.getenv("CANVAS_BASE_URL")
    
    if not token or not base_url:
        print("❌ Missing Canvas credentials in .env file")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"🔍 Testing Canvas courses for: {base_url}")
    print("=" * 60)
    
    # Test different course endpoints
    endpoints = [
        "/api/v1/courses",  # All courses
        "/api/v1/courses?enrollment_type=student",  # Student courses
        "/api/v1/courses?enrollment_type=teacher",  # Teacher courses  
        "/api/v1/courses?enrollment_type=ta",       # TA courses
        "/api/v1/courses?state=available",          # Available courses
        "/api/v1/courses?include[]=term",           # Include term info
        "/api/v1/courses?per_page=100",             # More results
    ]
    
    for endpoint in endpoints:
        url = f"{base_url}{endpoint}"
        print(f"\n📋 Testing: {endpoint}")
        print("-" * 40)
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                courses = response.json()
                print(f"Courses found: {len(courses)}")
                
                if courses:
                    print("\n📚 Course Details:")
                    for i, course in enumerate(courses[:3]):  # Show first 3
                        print(f"  {i+1}. {course.get('name', 'Unnamed Course')}")
                        print(f"     ID: {course.get('id')}")
                        print(f"     Code: {course.get('course_code', 'No code')}")
                        print(f"     State: {course.get('workflow_state', 'Unknown')}")
                        print(f"     Term: {course.get('term', {}).get('name', 'No term')}")
                        
                        # Check enrollments
                        enrollments = course.get('enrollments', [])
                        if enrollments:
                            enrollment_types = [e.get('type') for e in enrollments]
                            print(f"     Enrollments: {', '.join(enrollment_types)}")
                        print()
                
                if len(courses) > 3:
                    print(f"     ... and {len(courses) - 3} more courses")
                    
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"Response: {response.text[:200]}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Connection error: {e}")
    
    print("\n" + "=" * 60)
    print("🔍 Raw API Test - All Courses:")
    print("=" * 60)
    
    # One more detailed test
    try:
        url = f"{base_url}/api/v1/courses?per_page=100&include[]=term&include[]=teachers"
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            courses = response.json()
            print(f"📊 Total courses returned: {len(courses)}")
            
            if courses:
                print("\n🔍 All Course Details:")
                for course in courses:
                    print(json.dumps({
                        'id': course.get('id'),
                        'name': course.get('name'),
                        'course_code': course.get('course_code'),
                        'workflow_state': course.get('workflow_state'),
                        'enrollments': [
                            {
                                'type': e.get('type'),
                                'enrollment_state': e.get('enrollment_state')
                            }
                            for e in course.get('enrollments', [])
                        ]
                    }, indent=2))
                    print("-" * 30)
            else:
                print("⚠️ No courses found in detailed test")
        else:
            print(f"❌ Detailed test failed: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Detailed test error: {e}")

if __name__ == "__main__":
    test_courses_detailed()
