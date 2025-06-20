# scripts/troubleshoot_camera.py
"""
Troubleshooting script for Reolink camera connection issues.
"""

import requests
import socket
import subprocess
import sys
from urllib.parse import urlparse

def resolve_hostname(host):
    """Resolve hostname to IP address."""
    print(f"🔍 Resolving hostname: {host}")
    try:
        ip_address = socket.gethostbyname(host)
        if ip_address != host:
            print(f"✅ Resolved {host} to IP: {ip_address}")
        else:
            print(f"✅ {host} is already an IP address")
        return ip_address
    except socket.gaierror as e:
        print(f"❌ DNS resolution failed: {e}")
        return None

def normalize_host(host):
    """Normalize host input to remove protocols, ports, etc."""
    # Remove protocol if present
    if host.startswith('http://'):
        host = host[7:]
    elif host.startswith('https://'):
        host = host[8:]
    
    # Remove trailing slash
    host = host.rstrip('/')
    
    # Remove port if present in hostname (but not for IPv6)
    if ':' in host and not host.count(':') > 1:  # IPv4 with port, not IPv6
        host = host.split(':')[0]
    
    return host.strip()

def test_network_connectivity(host, port=80):
    """Test basic network connectivity to the camera."""
    print(f"🌐 Testing network connectivity to {host}:{port}")
    
    # Normalize and resolve hostname
    normalized_host = normalize_host(host)
    resolved_ip = resolve_hostname(normalized_host)
    
    if not resolved_ip:
        print("❌ Cannot resolve hostname - check DNS or use IP address")
        return False
    
    # Test with both hostname and IP
    test_hosts = [normalized_host, resolved_ip] if normalized_host != resolved_ip else [resolved_ip]
    
    for test_host in test_hosts:
        print(f"\n📡 Testing connectivity to {test_host}...")
        
        try:
            # Test ping
            print(f"📡 Pinging {test_host}...")
            result = subprocess.run(['ping', '-c', '1', test_host], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print("✅ Ping successful")
            else:
                print(f"❌ Ping failed: {result.stderr}")
                continue
                
        except subprocess.TimeoutExpired:
            print("❌ Ping timeout")
            continue
        except FileNotFoundError:
            print("⚠️ Ping command not found (Windows?), skipping ping test")
        
        # Test TCP connection
        print(f"🔌 Testing TCP connection to {test_host}:{port}...")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((test_host, port))
            sock.close()
            
            if result == 0:
                print("✅ TCP connection successful")
                return True
            else:
                print(f"❌ TCP connection failed (error code: {result})")
                
        except socket.gaierror as e:
            print(f"❌ DNS resolution failed: {e}")
        except Exception as e:
            print(f"❌ Connection test failed: {e}")
    
    return False

def test_http_access(host, port=80):
    """Test HTTP access to camera web interface."""
    print(f"\n🌍 Testing HTTP access to camera...")
    
    # Normalize hostname
    normalized_host = normalize_host(host)
    resolved_ip = resolve_hostname(normalized_host)
    
    # Test with both hostname and IP
    test_hosts = []
    if normalized_host:
        test_hosts.append(normalized_host)
    if resolved_ip and resolved_ip != normalized_host:
        test_hosts.append(resolved_ip)
    
    if not test_hosts:
        print("❌ No valid hosts to test")
        return False
    
    # Test different URL patterns
    protocols = ['http', 'https']
    ports = [port, 80, 443, 8000] if port not in [80, 443, 8000] else [port]
    
    for test_host in test_hosts:
        print(f"\n🎯 Testing host: {test_host}")
        
        for protocol in protocols:
            for test_port in ports:
                test_urls = [
                    f"{protocol}://{test_host}:{test_port}/",
                    f"{protocol}://{test_host}:{test_port}/cgi-bin/api.cgi"
                ]
                
                for url in test_urls:
                    print(f"🔗 Testing: {url}")
                    try:
                        response = requests.get(url, timeout=5, verify=False)
                        print(f"✅ HTTP response: {response.status_code}")
                        
                        # Check if it looks like a Reolink camera
                        response_text = response.text.lower()
                        if any(keyword in response_text for keyword in ['reolink', 'ipc', 'camera', 'nvr']):
                            print("🎥 Looks like a Reolink camera!")
                        
                        if response.status_code == 200:
                            return True
                            
                    except requests.exceptions.SSLError as e:
                        print(f"🔒 SSL Error: {e}")
                        
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
    
    # Normalize and resolve hostname
    normalized_host = normalize_host(host)
    resolved_ip = resolve_hostname(normalized_host)
    
    test_hosts = []
    if normalized_host:
        test_hosts.append(normalized_host)
    if resolved_ip and resolved_ip != normalized_host:
        test_hosts.append(resolved_ip)
    
    print(f"👤 Username: {username}")
    print(f"🔑 Password: {'*' * len(password)}")
    
    # Test both HTTP and HTTPS
    protocols = ['http', 'https']
    
    for test_host in test_hosts:
        print(f"\n🎯 Testing API with host: {test_host}")
        
        for protocol in protocols:
            auth_url = f"{protocol}://{test_host}:{port}/cgi-bin/api.cgi"
            print(f"🌐 Auth URL: {auth_url}")
            
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
            
            try:
                # Disable SSL warnings
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                
                response = requests.post(auth_url, json=[auth_data], timeout=10, verify=False)
                print(f"📡 HTTP Status: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        result = response.json()
                        print(f"📄 API Response: {result}")
                        
                        if result[0]["code"] == 0:
                            token = result[0]["value"]["Token"]["name"]
                            print(f"✅ Authentication successful! Token: {token[:20]}...")
                            return True
                        else:
                            error_code = result[0]["code"]
                            print(f"❌ Authentication failed with code: {error_code}")
                            
                            # Common error codes
                            error_messages = {
                                1: "Invalid username or password",
                                3: "User already logged in",
                                4: "User locked out",
                                5: "Invalid request format"
                            }
                            
                            if error_code in error_messages:
                                print(f"💡 Error meaning: {error_messages[error_code]}")
                            
                    except ValueError as e:
                        print(f"❌ Invalid JSON response: {e}")
                        print(f"📄 Raw response: {response.text[:500]}")
                        
                else:
                    print(f"❌ HTTP error: {response.status_code}")
                    print(f"📄 Response: {response.text[:500]}")
                    
            except requests.exceptions.SSLError as e:
                print(f"🔒 SSL Error: {e}")
                
            except requests.exceptions.ConnectionError as e:
                print(f"❌ Connection error: {e}")
                
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
    print("📍 Enter camera address (IP or hostname):")
    print("   Examples: 192.168.1.100, camera.local, reolink-cam-01.mydomain.com")
    host = input("   Address: ").strip()
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
        print("\n❌ Network connectivity failed")
        print("💡 Possible issues:")
        print("   - Camera is offline or wrong address")
        print("   - DNS resolution failed (try IP address instead)")
        print("   - Network routing issues")
        print("   - Firewall blocking connection")
        
        # Offer network scan
        scan = input("\n🔍 Scan network for cameras? [y/N]: ").strip().lower()
        if scan in ['y', 'yes']:
            # Try to determine base network from hostname/IP
            normalized_host = normalize_host(host)
            resolved_ip = resolve_hostname(normalized_host)
            
            if resolved_ip and '.' in resolved_ip:
                base_ip = ".".join(resolved_ip.split(".")[:-1])
                scan_network_for_cameras(base_ip)
            else:
                print("🔍 Using default network 192.168.1")
                scan_network_for_cameras("192.168.1")
    
    print("\n" + "=" * 50)
    print("🎯 TROUBLESHOOTING TIPS:")
    print("1. Ensure camera address is correct and reachable")
    print("2. Try IP address instead of hostname if DNS fails")
    print("3. Check camera is powered on and connected to network")
    print("4. Verify username/password are correct")
    print("5. Try accessing camera web interface in browser")
    print("6. Check if camera uses HTTPS instead of HTTP")
    print("7. Ensure no firewall blocking connection")
    print("8. Try different ports (554 for RTSP, 443 for HTTPS)")
    print("\n💡 For hostname issues:")
    print("   - Check DNS resolution with: nslookup hostname")
    print("   - Try ping hostname to verify connectivity")
    print("   - Use IP address directly if hostname fails")

if __name__ == "__main__":
    main()