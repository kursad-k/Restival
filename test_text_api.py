#!/usr/bin/env python3
"""
Simple test script for the new text file API endpoints.
Run this after starting the Restival server in Blender.
"""

import json
import requests

BASE_URL = "http://localhost:2357/api/v1"

def test_text_endpoints():
    """Test the text file endpoints."""
    
    # Test 1: List existing text files
    print("1. Listing existing text files...")
    response = requests.get(f"{BASE_URL}/texts")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()
    
    # Test 2: Create a new text file
    print("2. Creating a new text file...")
    new_script = {
        "name": "agent_test_script.py",
        "content": """import bpy

# Script created by agent via REST API
print("Hello from agent-created script!")

# Example: Select all mesh objects
for obj in bpy.context.scene.objects:
    if obj.type == 'MESH':
        obj.select_set(True)
        print(f"Selected mesh: {obj.name}")
"""
    }
    
    response = requests.post(
        f"{BASE_URL}/texts",
        headers={"Content-Type": "application/json"},
        json=new_script
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()
    
    # Test 3: Get the created text file
    print("3. Retrieving the created text file...")
    response = requests.get(f"{BASE_URL}/texts/agent_test_script.py")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()
    
    # Test 4: Try to create duplicate (should fail)
    print("4. Trying to create duplicate (should fail)...")
    response = requests.post(
        f"{BASE_URL}/texts",
        headers={"Content-Type": "application/json"},
        json=new_script
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")

if __name__ == "__main__":
    try:
        test_text_endpoints()
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to Restival server.")
        print("Make sure Blender is running with Restival server started.")
    except Exception as e:
        print(f"Error: {e}")