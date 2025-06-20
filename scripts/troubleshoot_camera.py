"""
Troubleshooting script for Reolink camera connection issues.
"""

import requests
import socket
import subprocess
import sys
from urllib.parse import urlparse

def test_network_connectivity(host, port=80):
    """Test basic network connectivity to the camera."""
    print(f"🌐 Testing network connectivity to {host}:{port}")
    
    try:
        # Test ping
        print(f"📡 Pinging {host}...")
        result = subprocess.run(['ping', '-c', '1', host], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Ping successful")
        else:
            print(f"❌ Ping failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Ping timeout")
        return False
    except FileNotFoundError:
        print("⚠️ Ping command not found (Windows?), skipping ping test")
    
    # Test TCP connection
    print(f"🔌 Testing TCP connection to {host}:{port}...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print("✅ TCP connection successful")
            return True
        else:
            print(f"❌ TCP connection failed (error code: {result})")
            return False
            
    except socket.gaierror as e:
        print(f"❌ DNS resolution failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

def test_http_access(host, port=80):
    """Test HTTP access to camera web interface."""
    print(f"\n🌍 Testing HTTP access to camera...")
    
    # Test different URL patterns
    test_urls = [
        f"http://{host}:{port}/",
        f"http://{host}:{port}/cgi-bin/api.cgi",
        f"http://{host}/",  # Without port
        f"http://{host}/cgi-bin/api.cgi"  # Without port
    ]
    
    for url in test_urls:
        print(f"🔗 Testing: {url}")
        try:
            response = requests.get(url, timeout=10, verify=False)
            print(f"✅ HTTP response: {response.status_code}")
            
            # Check if it looks like a Reolink camera
            if 'reolink' in response.text.lower() or 'ipc' in response.text.lower():
                print("🎥 Looks like a Reolink camera!")
            
            return True
            
        except requests.exceptions.SSLError as e:
            print(f"🔒 SSL Error (camera might use HTTPS): {e}")
            
            # Try HTTPS version
            https_url = url.replace('http://', 'https://')
            try:
                print(f"🔗 Trying HTTPS: {https_url}")
                response = requests.get(https_url, timeout=10, verify=False)
                print(f"✅ HTTPS response: {response.status_code}")
                print("⚠️ Camera uses HTTPS - you may need to modify the client code")
                return True
            except Exception as https_e:
                print(f"❌ HTTPS also failed: {https_e}")
                
        except requests.exceptions.ConnectionError as e:
            print(f"❌ Connection error: {e}")
        except requests.exceptions.Timeout:
            print("❌ Request timeout")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
    
    return False

def test_reolink_api(host, port, username, password):
    """Test Reolink API authentication."""
    print(f"\n🔐 Testing Reolink API authentication...")
    
    auth_url = f"http://{host}:{port}/cgi-bin/api.cgi"
    
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
    
    print(f"🌐 Auth URL: {auth_url}")
    print(f"👤 Username: {username}")
    print(f"🔑 Password: {'*' * len(password)}")
    
    try:
        response = requests.post(auth_url, json=[auth_data], timeout=10, verify=False)
        print(f"📡 HTTP Status: {response.status_code}")
        print(f"📄 Content-Type: {response.headers.get('content-type', 'unknown')}")
        print(f"📄 Response Length: {len(response.text)} characters")
        
        if response.status_code == 200:
            # Check if response is JSON
            content_type = response.headers.get('content-type', '').lower()
            
            if 'application/json' in content_type or response.text.strip().startswith('['):
                try:
                    result = response.json()
                    print(f"📄 API Response: {result}")
                    
                    if result and len(result) > 0 and result[0].get("code") == 0:
                        token = result[0]["value"]["Token"]["name"]
                        print(f"✅ Authentication successful! Token: {token[:20]}...")
                        return True
                    else:
                        if result and len(result) > 0:
                            error_code = result[0].get("code", "unknown")
                            print(f"❌ Authentication failed with code: {error_code}")
                            
                            # Common error codes
                            error_messages = {
                                1: "Invalid username or password",
                                3: "User already logged in",
                                4: "User locked out",
                                5: "Invalid request format",
                                -1: "Command not found or malformed request"
                            }
                            
                            if error_code in error_messages:
                                print(f"💡 Error meaning: {error_messages[error_code]}")
                        else:
                            print("❌ Empty or malformed API response")
                        
                        return False
                        
                except ValueError as e:
                    print(f"❌ Invalid JSON response: {e}")
                    print(f"📄 Raw response (first 500 chars): {response.text[:500]}")
                    
                    # Check if it's HTML (common with wrong endpoint)
                    if response.text.strip().startswith('<'):
                        print("💡 Response appears to be HTML - wrong endpoint or web interface")
                        print("💡 Try accessing the camera web interface directly in a browser")
                    
                    return False
            else:
                print(f"❌ Response is not JSON (Content-Type: {content_type})")
                print(f"📄 Raw response (first 500 chars): {response.text[:500]}")
                
                # Check if it's HTML
                if response.text.strip().startswith('<'):
                    print("💡 Response appears to be HTML - this might be the web interface")
                    print("💡 The API endpoint might be different or disabled")
                
                return False
                
        else:
            print(f"❌ HTTP error: {response.status_code}")
            print(f"📄 Response: {response.text[:500]}")
            
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection error: {e}")
        print("💡 Check if the IP address and port are correct")
        
    except requests.exceptions.Timeout:
        print("❌ Request timeout")
        print("💡 Camera might be slow to respond or unreachable")
        
    except requests.exceptions.SSLError as e:
        print(f"🔒 SSL Error: {e}")
        print("💡 Try HTTPS instead of HTTP, or check certificate settings")
        
    except Exception as e:
        print(f"❌ API test failed: {e}")
        
    return False

def scan_network_for_cameras(base_ip="192.168.1"):
    """Scan network for potential Reolink cameras."""
    print(f"\n🔍 Scanning {base_ip}.1-254 for cameras (this may take a while)...")
    
    found_cameras = []
    
    for i in range(1, 255):
        ip = f"{base_ip}.{i}"
        try:
            # Quick TCP connect test
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            result = sock.connect_ex((ip, 80))
            sock.close()
            
            if result == 0:
                print(f"🎯 Found device at {ip}")
                
                # Quick HTTP test
                try:
                    response = requests.get(f"http://{ip}/", timeout=2, verify=False)
                    if 'reolink' in response.text.lower() or 'ipc' in response.text.lower():
                        print(f"🎥 Possible camera at {ip}")
                        found_cameras.append(ip)
                except:
                    pass
                    
        except:
            pass
    
    if found_cameras:
        print(f"\n✅ Found potential cameras: {found_cameras}")
    else:
        print("\n❌ No cameras found in network scan")
    
    return found_cameras

def main():
    print("🔧 Reolink Camera Connection Troubleshooter")
    print("=" * 50)
    
    # Get camera details
    host = input("📍 Enter camera IP address (e.g., 192.168.1.100): ").strip()
    if not host:
        host = "192.168.1.100"
    
    port = input("🔌 Enter camera port [80]: ").strip()
    if not port:
        port = 80
    else:
        port = int(port)
    
    username = input("👤 Enter username [admin]: ").strip()
    if not username:
        username = "admin"
    
    password = input("🔑 Enter password: ").strip()
    
    print(f"\n📋 Testing connection to {host}:{port}")
    print("=" * 50)
    
    # Run tests
    network_ok = test_network_connectivity(host, port)
    
    if network_ok:
        http_ok = test_http_access(host, port)
        
        if http_ok and password:
            api_ok = test_reolink_api(host, port, username, password)
        else:
            print("\n⚠️ Skipping API test (no password provided or HTTP failed)")
    else:
        print("\n❌ Network connectivity failed - camera may be offline or wrong IP")
        
        # Offer network scan
        scan = input("\n🔍 Scan network for cameras? [y/N]: ").strip().lower()
        if scan in ['y', 'yes']:
            base_ip = ".".join(host.split(".")[:-1])  # Get base network
            scan_network_for_cameras(base_ip)
    
    print("\n" + "=" * 50)
    print("🎯 TROUBLESHOOTING TIPS:")
    print("1. Ensure camera IP is correct and reachable")
    print("2. Check camera is powered on and connected to network")
    print("3. Verify username/password are correct")
    print("4. Try accessing camera web interface in browser")
    print("5. Check if camera uses HTTPS instead of HTTP")
    print("6. Ensure no firewall blocking connection")
    print("7. Try different port (554 for RTSP, 443 for HTTPS)")

if __name__ == "__main__":
    main()