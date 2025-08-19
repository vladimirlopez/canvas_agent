#!/usr/bin/env python3
"""
Test script to publish the LLMTest course
"""

import os
from dotenv import load_dotenv
from canvas_client_enhanced import CanvasClientEnhanced

load_dotenv()

def main():
    # Initialize Canvas client
    base_url = os.getenv("CANVAS_BASE_URL")
    token = os.getenv("CANVAS_API_TOKEN")
    
    if not base_url or not token:
        print("❌ Missing Canvas credentials in .env file")
        return
    
    client = CanvasClientEnhanced(base_url, token)
    
    print("🔍 Publishing LLMTest course...")
    print("=" * 50)
    
    # Your course ID from the debug output
    course_id = "12625554"
    
    try:
        # Get current course status
        print("📋 Current course status:")
        course = client.get_course(course_id)
        print(f"   Name: {course.get('name')}")
        print(f"   Status: {course.get('workflow_state')}")
        print()
        
        if course.get('workflow_state') == 'unpublished':
            print("🚀 Publishing course...")
            result = client.publish_course(course_id)
            print(f"✅ Success! Course published:")
            print(f"   Name: {result.get('name')}")
            print(f"   New Status: {result.get('workflow_state')}")
            print(f"   Course URL: {result.get('html_url', 'N/A')}")
        else:
            print(f"ℹ️ Course is already {course.get('workflow_state')}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
