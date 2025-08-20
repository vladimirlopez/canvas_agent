#!/usr/bin/env python3
"""
Create a Week 1 module in the LLMTest course
"""

# DEPRECATED: Use python/scripts/create_week1_module.py instead.

import os
from dotenv import load_dotenv
from canvas_client_enhanced import CanvasClientEnhanced

load_dotenv()

def create_week1_module():
    # Initialize Canvas client
    base_url = os.getenv("CANVAS_BASE_URL")
    token = os.getenv("CANVAS_API_TOKEN")
    
    if not base_url or not token:
        print("❌ Missing Canvas credentials in .env file")
        return
    
    client = CanvasClientEnhanced(base_url, token)
    
    print("📚 Creating 'Week 1' module in LLMTest course...")
    print("=" * 50)
    
    # Your course ID
    course_id = "12625554"
    
    try:
        # First, check current modules
        print("📋 Current modules:")
        existing_modules = client.list_modules(course_id)
        if existing_modules:
            for module in existing_modules:
                print(f"   • {module.get('name')} (ID: {module.get('id')})")
        else:
            print("   No existing modules found")
        
        print()
        
        # Create the Week 1 module
        print("🚀 Creating 'Week 1' module...")
        
        result = client.create_module(course_id, "Week 1", position=1, publish=True)
        
        print("✅ Successfully created module:")
        print(f"   Name: {result.get('name')}")
        print(f"   ID: {result.get('id')}")
        print(f"   Position: {result.get('position')}")
        print(f"   Published: {result.get('published')}")
        
        print("\\n📚 Updated module list:")
        updated_modules = client.list_modules(course_id)
        for module in updated_modules:
            print(f"   • {module.get('name')} (ID: {module.get('id')})")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    create_week1_module()
