import urllib.request
import json
import sys

def test_chat_api():
    url = "http://localhost:8000/api/v1/chat"
    
    payload = {
        "messages": [
            {"role": "user", "content": "Hello, who are you?"}
        ]
    }
    
    print(f"Testing Chat API at {url}...")
    
    try:
        req = urllib.request.Request(
            url, 
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        
        with urllib.request.urlopen(req) as response:
            if response.status != 200:
                print(f"Error: Status code {response.status}")
                return False
                
            print("Response stream started. Reading chunks...")
            
            full_content = ""
            for line in response:
                line = line.decode('utf-8').strip()
                if line:
                    try:
                        chunk = json.loads(line)
                        if chunk["type"] == "content":
                            content = chunk["content"]
                            full_content += content
                            sys.stdout.write(content)
                            sys.stdout.flush()
                        elif chunk["type"] == "tool_start":
                            print(f"\n[Tool Start: {chunk['tool']}]")
                        elif chunk["type"] == "tool_end":
                            print(f"\n[Tool End: {chunk['tool']}]")
                    except json.JSONDecodeError:
                        print(f"\nInvalid JSON: {line}")
                    
        print("\n\nTest completed successfully!")
        return True
        
    except Exception as e:
        print(f"Exception: {e}")
        return False

if __name__ == "__main__":
    test_chat_api()
