import requests

url = "http://127.0.0.1:8000/api/ucp/checkout"
data = {"shopify_id": 7838383145003}

try:
    response = requests.post(url, json=data)
    print(f"Status: {response.status_code}")
    print(response.json())
except Exception as e:
    print(f"Error: {e}")
