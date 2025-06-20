"""
Advanced authentication tester for Reolink cameras that tries multiple methods.
"""

import requests
import urllib3
import base64
import hashlib
import json
from requests.auth import HTTPBasicAuth, HTTPDigestAuth

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_basic_auth(host, port, protocol, username, password):
    """Test HTTP Basic Authentication"""
    print(f"\n🔐 Testing HTTP Basic Auth...")
    
    test_urls = [
        f"{protocol}://{host}:{port}/",
        f"{protocol}://{host}:{port}/cgi-bin/api.cgi",
        f"{protocol}://{host}:{port}/api/v1/login"
    ]
    
    for url in test_urls:
        try:
            response = requests.get(url, auth=HTTPBasicAuth(username, password), 
                                  timeout=10, verify=False)
            print(f"   URL: {url}")
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"   ✅ Basic Auth successful!")
                return True
            elif response.status_code == 401:
                print(f"   ❌ Authentication failed")
            else:
                print(f"   ⚠️ Unexpected status: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    return False

def test_digest_auth(host, port, protocol, username, password):
    """Test HTTP Digest Authentication"""
    print(f"\n🔐 Testing HTTP Digest Auth...")
    
    test_urls = [
        f"{protocol}://{host}:{port}/",
        f"{protocol}://{host}:{port}/cgi-bin/api.cgi"
    ]
    
    for url in test_urls:
        try:
            response = requests.get(url, auth=HTTPDigestAuth(username, password), 
                                  timeout=10, verify=False)
            print(f"   URL: {url}")
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"   ✅ Digest Auth successful!")
                return True
            elif response.status_code == 401:
                print(f"   ❌ Authentication failed")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    return False

def test_token_based_auth(host, port, protocol, username, password):
    """Test various token-based authentication methods"""
    print(f"\n🔐 Testing Token-Based Auth...")
    
    auth_url = f"{protocol}://{host}:{port}/cgi-bin/api.cgi"
    
    # Different token request formats
    token_formats = [
        # Format 1: GetToken command
        {
            "cmd": "GetToken",
            "action": 0,
            "param": {
                "User": {
                    "userName": username,
                    "password": password
                }
            }
        },
        # Format 2: Auth command
        {
            "cmd": "Auth",
            "action": 0,
            "param": {
                "userName": username,
                "password": password
            }
        },
        # Format 3: LoginToken
        {
            "cmd": "LoginToken",
            "param": {
                "User": {
                    "userName": username,
                    "password": password
                }
            }
        }
    ]
    
    for i, auth_data in enumerate(token_formats, 1):
        try:
            print(f"   📝 Trying token format {i}...")
            response = requests.post(auth_url, json=[auth_data], timeout=10, verify=False)
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"   Response: {result}")
                    
                    if result and len(result) > 0 and result[0].get("code") == 0:
                        print(f"   ✅ Token auth successful with format {i}!")
                        return True
                        
                except ValueError:
                    print(f"   ❌ Invalid JSON response")
            
        except Exception as e:
            print(f"   ❌ Format {i} failed: {e}")
    
    return False

def test_direct_rtsp_auth(host, username, password):
    """Test if RTSP authentication works without API"""
    print(f"\n🔐 Testing Direct RTSP Access...")
    
    import cv2
    
    rtsp_urls = [
        f"rtsp://{username}:{password}@{host}:554/h264Preview_01_main",
        f"rtsp://{username}:{password}@{host}:554/Preview_01_main", 
        f"rtsp://{username}:{password}@{host}:554/cam/realmonitor?channel=1&subtype=0",
        f"rtsp://{username}:{password}@{host}:554/live",
        f"rtsp://{username}:{password}@{host}:554/stream1",
        f"rtsp://{username}:{password}@{host}:554/11"
    ]
    
    for i, url in enumerate(rtsp_urls, 1):
        print(f"   📹 Testing RTSP format {i}...")
        try:
            cap = cv2.VideoCapture(url)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    print(f"   ✅ RTSP successful! Format {i} works")
                    print(f"   📺 Frame size: {frame.shape}")
                    cap.release()
                    return True, url
                cap.release()
            print(f"   ❌ RTSP format {i} failed")
            
        except Exception as e:
            print(f"   ❌ RTSP format {i} error: {e}")
    
    return False, None

def test_web_interface_auth(host, port, protocol, username, password):
    """Test web interface authentication"""
    print(f"\n🔐 Testing Web Interface Auth...")
    
    session = requests.Session()
    
    # Try to get login page
    try:
        login_url = f"{protocol}://{host}:{port}/"
        response = session.get(login_url, timeout=10, verify=False)
        
        if response.status_code == 200:
            print(f"   📄 Got web interface (status: 200)")
            
            # Look for login forms or authentication endpoints
            content = response.text.lower()
            
            if 'login' in content:
                print(f"   📝 Found login form in web interface")
                
                # Try common web login endpoints
                login_endpoints = [
                    "/api/login",
                    "/cgi-bin/login.cgi",
                    "/login.cgi",
                    "/api/auth/login"
                ]
                
                for endpoint in login_endpoints:
                    try:
                        login_data = {
                            "username": username,
                            "password": password
                        }
                        
                        web_login_url = f"{protocol}://{host}:{port}{endpoint}"
                        response = session.post(web_login_url, data=login_data, 
                                              timeout=10, verify=False)
                        
                        print(f"   🌐 {endpoint}: {response.status_code}")
                        
                        if response.status_code == 200:
                            if "success" in response.text.lower() or "token" in response.text.lower():
                                print(f"   ✅ Web login successful at {endpoint}!")
                                return True
                                
                    except Exception as e:
                        print(f"   ❌ {endpoint} failed: {e}")
            else:
                print(f"   ❌ No login form found in web interface")
        else:
            print(f"   ❌ Web interface not accessible (status: {response.status_code})")
            
    except Exception as e:
        print(f"   ❌ Web interface test failed: {e}")
    
    return False

def test_alternative_api_endpoints(host, port, protocol, username, password):
    """Test alternative API endpoints"""
    print(f"\n🔐 Testing Alternative API Endpoints...")
    
    api_endpoints = [
        "/api/v1/login",
        "/api/login", 
        "/cgi-bin/login.cgi",
        "/login",
        "/auth/login",
        "/rpc/login",
        "/json/login"
    ]
    
    for endpoint in api_endpoints:
        try:
            url = f"{protocol}://{host}:{port}{endpoint}"
            print(f"   🌐 Testing: {endpoint}")
            
            # Try different data formats
            login_formats = [
                {"username": username, "password": password},
                {"user": username, "pass": password},
                {"userName": username, "password": password},
                {"login": username, "password": password}
            ]
            
            for login_data in login_formats:
                try:
                    response = requests.post(url, json=login_data, timeout=10, verify=False)
                    if response.status_code == 200:
                        try:
                            result = response.json()
                            if "token" in str(result).lower() or "success" in str(result).lower():
                                print(f"   ✅ Success at {endpoint} with format: {login_data}")
                                return True
                        except:
                            pass
                except:
                    pass
                    
        except Exception as e:
            continue
    
    return False

def comprehensive_auth_test(host, port, protocol, username, password):
    """Run comprehensive authentication tests"""
    print(f"\n{'='*60}")
    print(f"🔬 COMPREHENSIVE AUTHENTICATION TEST")
    print(f"{'='*60}")
    print(f"Target: {protocol}://{host}:{port}")
    print(f"Username: {username}")
    print(f"Password: {'*' * len(password)}")
    
    tests = [
        ("HTTP Basic Auth", lambda: test_basic_auth(host, port, protocol, username, password)),
        ("HTTP Digest Auth", lambda: test_digest_auth(host, port, protocol, username, password)),
        ("Token-Based Auth", lambda: test_token_based_auth(host, port, protocol, username, password)),
        ("Web Interface Auth", lambda: test_web_interface_auth(host, port, protocol, username, password)),
        ("Alternative API Endpoints", lambda: test_alternative_api_endpoints(host, port, protocol, username, password)),
    ]
    
    successful_methods = []
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        try:
            if test_func():
                successful_methods.append(test_name)
                print(f"   ✅ {test_name} SUCCEEDED!")
            else:
                print(f"   ❌ {test_name} failed")
        except Exception as e:
            print(f"   💥 {test_name} crashed: {e}")
    
    # Test RTSP separately (doesn't need API auth)
    print(f"\n🧪 Running: Direct RTSP Access")
    rtsp_success, rtsp_url = test_direct_rtsp_auth(host, username, password)
    if rtsp_success:
        successful_methods.append("Direct RTSP")
        print(f"   ✅ RTSP Access SUCCEEDED!")
        print(f"   📹 Working URL: rtsp://{username}:***@{host}:554/...")
    
    return successful_methods, rtsp_url if rtsp_success else None

def main():
    print("🔬 Advanced Reolink Authentication Tester")
    print("=" * 50)
    
    host = input("📍 Enter camera IP [192.168.10.50]: ").strip() or "192.168.10.50"
    
    # Based on previous logs, we know HTTPS/443 works best
    print(f"\n🎯 Testing camera at: {host}")
    print("Note: Based on previous tests, focusing on HTTPS/443")
    
    username = input("👤 Enter username [admin]: ").strip() or "admin"
    
    import getpass
    password = getpass.getpass("🔑 Enter password: ")
    
    # Test primary protocol first
    successful_methods, rtsp_url = comprehensive_auth_test(host, 443, "https", username, password)
    
    print(f"\n{'='*60}")
    print(f"📊 RESULTS SUMMARY")
    print(f"{'='*60}")
    
    if successful_methods:
        print(f"✅ Successful authentication methods:")
        for method in successful_methods:
            print(f"   • {method}")
            
        if rtsp_url:
            print(f"\n📹 RTSP Stream URL that works:")
            print(f"   {rtsp_url}")
            print(f"\n💡 You can use RTSP directly without API authentication!")
            print(f"   Just update your config to skip authentication.")
            
    else:
        print(f"❌ No authentication methods worked")
        print(f"\n💡 TROUBLESHOOTING SUGGESTIONS:")
        print(f"   1. Double-check username/password by logging into web interface")
        print(f"   2. Try factory reset if possible")
        print(f"   3. Check camera manual for specific auth requirements")
        print(f"   4. Some cameras need firmware updates for API access")
        print(f"   5. Try different user accounts (user vs admin)")

if __name__ == "__main__":
    main()