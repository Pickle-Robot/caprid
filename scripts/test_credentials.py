"""
Script to test different credential combinations and auth methods for Reolink cameras.
"""

import requests
import urllib3
import getpass

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_credentials(host, port, protocol, username, password):
    """Test specific credentials with given protocol/port"""
    auth_url = f"{protocol}://{host}:{port}/cgi-bin/api.cgi"
    
    auth_data = {
        "cmd": "Login",
        "action": 0,
        "param": {
            "User": {
                "userName": username,
                "password": password
            }
        }
    }
    
    print(f"\n🔐 Testing: {protocol.upper()} on port {port}")
    print(f"   URL: {auth_url}")
    print(f"   Username: {username}")
    print(f"   Password: {'*' * len(password)}")
    
    try:
        response = requests.post(auth_url, json=[auth_data], timeout=10, verify=False)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            content_type = response.headers.get('content-type', '').lower()
            print(f"   Content-Type: {content_type}")
            
            if 'application/json' in content_type or response.text.strip().startswith('['):
                try:
                    result = response.json()
                    print(f"   Response: {result}")
                    
                    if result and len(result) > 0:
                        code = result[0].get("code")
                        if code == 0:
                            token = result[0]["value"]["Token"]["name"]
                            print(f"   ✅ SUCCESS! Token: {token[:20]}...")
                            return True
                        else:
                            error_messages = {
                                1: "Invalid username or password",
                                3: "User already logged in (try logging out first)",
                                4: "User account locked",
                                5: "Invalid request format",
                                -1: "Command not supported"
                            }
                            error_msg = error_messages.get(code, f"Unknown error code: {code}")
                            print(f"   ❌ Auth failed: {error_msg}")
                            
                            # If user already logged in, try logout first
                            if code == 3:
                                print("   🔄 Attempting logout first...")
                                if logout_user(host, port, protocol, username, password):
                                    print("   🔄 Retrying login...")
                                    return test_credentials(host, port, protocol, username, password)
                
                except ValueError as e:
                    print(f"   ❌ JSON parse error: {e}")
                    print(f"   Raw response: {response.text[:200]}...")
            else:
                print(f"   ❌ Non-JSON response (likely HTML)")
                if response.text.strip().startswith('<'):
                    print("   💡 Got HTML - wrong endpoint or web interface")
        else:
            print(f"   ❌ HTTP error: {response.status_code}")
            
    except requests.exceptions.SSLError as e:
        print(f"   ❌ SSL Error: {e}")
    except requests.exceptions.ConnectionError as e:
        print(f"   ❌ Connection Error: {e}")
    except requests.exceptions.Timeout:
        print(f"   ❌ Timeout")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    return False

def logout_user(host, port, protocol, username, password):
    """Attempt to logout user"""
    auth_url = f"{protocol}://{host}:{port}/cgi-bin/api.cgi"
    
    logout_data = {
        "cmd": "Logout",
        "action": 0,
        "param": {
            "User": {
                "userName": username
            }
        }
    }
    
    try:
        response = requests.post(auth_url, json=[logout_data], timeout=10, verify=False)
        if response.status_code == 200:
            result = response.json()
            if result and len(result) > 0 and result[0].get("code") == 0:
                print("   ✅ Logout successful")
                return True
    except:
        pass
    
    print("   ❌ Logout failed")
    return False

def test_common_credentials(host):
    """Test common username/password combinations"""
    
    # Common Reolink defaults
    common_creds = [
        ("admin", ""),           # Empty password
        ("admin", "admin"),      # Default admin/admin  
        ("admin", "123456"),     # Common default
        ("admin", "password"),   # Another common default
        ("user", ""),            # Empty password for user
        ("user", "user"),        # Default user/user
    ]
    
    protocols_ports = [
        ("https", 443),
        ("http", 80),
        ("https", 8000),
        ("http", 8000)
    ]
    
    print("🔍 Testing common credential combinations...")
    
    for protocol, port in protocols_ports:
        print(f"\n{'='*50}")
        print(f"Testing {protocol.upper()} on port {port}")
        print(f"{'='*50}")
        
        for username, password in common_creds:
            if test_credentials(host, port, protocol, username, password):
                print(f"\n🎉 FOUND WORKING CREDENTIALS!")
                print(f"   Protocol: {protocol.upper()}")
                print(f"   Port: {port}")
                print(f"   Username: {username}")
                print(f"   Password: {password if password else '(empty)'}")
                return True
    
    return False

def interactive_credential_test(host):
    """Interactive credential testing"""
    print("\n🔧 Interactive Credential Testing")
    print("=" * 40)
    
    # Test what we know works (HTTPS/443) with custom credentials
    while True:
        print(f"\nTesting camera at: {host}")
        print("Based on logs, HTTPS on port 443 seems to work best")
        
        username = input("👤 Enter username [admin]: ").strip() or "admin"
        password = getpass.getpass("🔑 Enter password: ")
        
        if test_credentials(host, 443, "https", username, password):
            print(f"\n🎉 SUCCESS! Use these credentials:")
            print(f"   Host: {host}")
            print(f"   Port: 443")
            print(f"   Protocol: HTTPS")
            print(f"   Username: {username}")
            print(f"   Password: {password}")
            break
        
        retry = input("\n🔄 Try different credentials? [y/N]: ").strip().lower()
        if retry not in ['y', 'yes']:
            break

def main():
    print("🔐 Reolink Credential Tester")
    print("=" * 40)
    
    host = input("📍 Enter camera IP [192.168.10.50]: ").strip() or "192.168.10.50"
    
    print(f"\n🎯 Testing camera at: {host}")
    
    # First try common credentials
    print("\n1️⃣ Trying common default credentials...")
    if test_common_credentials(host):
        return
    
    # Then do interactive testing
    print("\n2️⃣ Common credentials failed. Let's try manual testing...")
    interactive_credential_test(host)
    
    print("\n💡 TIPS:")
    print("1. Check camera label for default username/password")
    print("2. Try accessing web interface in browser first")
    print("3. Look for reset button to restore defaults")
    print("4. Check camera manual for default credentials")
    print("5. Some cameras use empty password initially")

if __name__ == "__main__":
    main()