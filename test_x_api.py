#!/usr/bin/env python3
"""
Simple test script for X API integration
"""

import os
import requests
import json

# Test configuration
BASE_URL = "http://localhost:8000"  # Adjust as needed
TEST_TOKEN = "your_test_token_here"  # Replace with actual test token

def test_x_api_endpoints():
    """Test all X API endpoints"""
    
    headers = {
        'Authorization': f'Bearer {TEST_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    print("Testing X API endpoints...")
    
    # Test 1: Get user info
    print("\n1. Testing user info endpoint...")
    try:
        response = requests.get(
            f"{BASE_URL}/authentication/x_api/user_info/?username=elonmusk",
            headers=headers
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"User: {data.get('data', {}).get('name', 'Unknown')}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")
    
    # Test 2: Search tweets
    print("\n2. Testing search tweets endpoint...")
    try:
        response = requests.get(
            f"{BASE_URL}/authentication/x_api/search_tweets/?query=AI&max_results=5",
            headers=headers
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            tweets = data.get('data', [])
            print(f"Found {len(tweets)} tweets")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")
    
    # Test 3: Get trending topics
    print("\n3. Testing trending topics endpoint...")
    try:
        response = requests.get(
            f"{BASE_URL}/authentication/x_api/trending_topics/?count=5",
            headers=headers
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Trending topics retrieved")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")
    
    # Test 4: Post tweet (commented out for safety)
    print("\n4. Testing post tweet endpoint (SKIPPED for safety)...")
    print("Uncomment the code below to test posting tweets")
    
    # Uncomment to test posting tweets:
    # try:
    #     payload = {
    #         "text": "Test tweet from Banbury API integration"
    #     }
    #     response = requests.post(
    #         f"{BASE_URL}/authentication/x_api/post_tweet/",
    #         headers=headers,
    #         json=payload
    #     )
    #     print(f"Status: {response.status_code}")
    #     if response.status_code == 201:
    #         data = response.json()
    #         print(f"Tweet posted successfully")
    #     else:
    #         print(f"Error: {response.text}")
    # except Exception as e:
    #     print(f"Exception: {e}")

if __name__ == "__main__":
    # Check if environment variables are set
    required_vars = ['X_API_KEY', 'X_API_SECRET', 'X_BEARER_TOKEN']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"Missing environment variables: {missing_vars}")
        print("Please set the required X API environment variables")
        exit(1)
    
    if TEST_TOKEN == "your_test_token_here":
        print("Please update TEST_TOKEN with a valid authentication token")
        exit(1)
    
    test_x_api_endpoints()
