import os
import sys
import json
import httpx
import logging
import socket
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def comprehensive_diagnostics():
    """
    Perform a comprehensive diagnostic check.
    Returns a dictionary with diagnostic information.
    """
    diagnostics = {
        "environment": {},
        "network": {},
        "endpoints": {}
    }

    # Check Environment Variables
    diagnostics["environment"]["AIPROXY_TOKEN"] = bool(os.environ.get("AIPROXY_TOKEN"))
    
    # Internet Connectivity
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        diagnostics["network"]["internet_connection"] = True
    except (socket.error, socket.timeout):
        diagnostics["network"]["internet_connection"] = False
    
    # DNS Resolution
    endpoints = [
        "aiproxy.sanand.workers.dev",
        "aiproxy.vercel.app", 
        "aiproxy.sanand.org",
        "api.aiproxy.sanand.dev"
    ]
    
    diagnostics["network"]["dns_resolution"] = {}
    for endpoint in endpoints:
        try:
            ip = socket.gethostbyname(endpoint)
            diagnostics["network"]["dns_resolution"][endpoint] = ip
        except socket.gaierror:
            diagnostics["network"]["dns_resolution"][endpoint] = None
    
    return diagnostics

def test_aiproxy_endpoints(token):
    """
    Attempt to connect to multiple AI Proxy endpoints.
    
    :param token: AI Proxy authentication token
    :return: Dictionary of connection results
    """
    endpoints = [
        "http://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
    ]
    
    results = {}
    
    for endpoint in endpoints:
        try:
            with httpx.Client(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
                response = client.post(
                    endpoint, 
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [{"role": "user", "content": "Test connection"}],
                        "max_tokens": 10
                    }
                )
                
                results[endpoint] = {
                    "status_code": response.status_code,
                    "success": response.status_code == 200,
                    "response_text": response.text
                }
        
        except Exception as e:
            results[endpoint] = {
                "status_code": None,
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
    
    return results

def main():
    print("🕵️ Advanced AI Proxy Diagnostic Tool 🕵️")
    print("======================================")
    
    # Comprehensive Diagnostics
    print("\n🔍 Running Comprehensive Diagnostics...")
    diagnostics = comprehensive_diagnostics()
    
    # Print Diagnostic Results
    print("\n📋 Diagnostic Report:")
    print("Environment:")
    print(f"  - AIPROXY_TOKEN set: {diagnostics['environment']['AIPROXY_TOKEN']}")
    
    print("\nNetwork:")
    print(f"  - Internet Connection: {'✅ Active' if diagnostics['network']['internet_connection'] else '❌ Inactive'}")
    
    print("\nDNS Resolution:")
    for endpoint, ip in diagnostics['network']['dns_resolution'].items():
        print(f"  - {endpoint}: {ip if ip else '❌ Failed'}")
    
    # Check Token
    token = os.environ.get("AIPROXY_TOKEN")
    if not token:
        print("\n❌ Error: AIPROXY_TOKEN is not set!")
        print("Set it using: export AIPROXY_TOKEN=your_token_here")
        sys.exit(1)
    
    # Test Endpoints
    print("\n🌐 Testing AI Proxy Endpoints...")
    endpoint_results = test_aiproxy_endpoints(token)
    
    print("\n📡 Endpoint Connection Results:")
    for endpoint, result in endpoint_results.items():
        if result['success']:
            print(f"  - {endpoint}: ✅ Successful")
        else:
            print(f"  - {endpoint}: ❌ Failed")
            if 'error' in result:
                print(f"    Error: {result['error']}")
    
    # Final Verdict
    successful_endpoints = [ep for ep, res in endpoint_results.items() if res['success']]
    
    if successful_endpoints:
        print("\n✅ Successfully connected to the following endpoints:")
        for ep in successful_endpoints:
            print(f"  - {ep}")
    else:
        print("\n❌ Failed to connect to any AI Proxy endpoint.")
        print("\nTroubleshooting Recommendations:")
        print("1. Verify AIPROXY_TOKEN is correct and current")
        print("2. Check network connectivity")
        print("3. Confirm endpoint URLs with service provider")
        print("4. Ensure firewall/security settings allow connections")
        sys.exit(1)

if __name__ == "__main__":
    main()
