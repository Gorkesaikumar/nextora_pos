import requests

def test():
    # Make a request to the local server
    try:
        # Assuming we can just hit a public endpoint to see if server is alive
        res = requests.get('http://127.0.0.1:8000/api/v1/')
        print("Server alive, status:", res.status_code)
    except Exception as e:
        print("Error:", e)

test()
