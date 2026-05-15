import requests

try:
    response = requests.get("http://127.0.0.1:5000/inventario")
    if response.status_code == 200:
        data = response.json()
        print(f"Success! Found {len(data)} products.")
        print(f"Keys in first product: {data[0].keys()}")
        print(f"First product: {data[0]}")
    else:
        print(f"Error: {response.status_code}")
except Exception as e:
    print(f"Connection failed: {e}")
