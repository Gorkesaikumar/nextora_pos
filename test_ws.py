import urllib.request
import json
import asyncio
import websockets

def get_token():
    data = json.dumps({'email': 'admin@nextora.com', 'password': 'admin'}).encode('utf-8')
    req = urllib.request.Request('http://127.0.0.1:8000/api/v1/auth/token/', data=data, headers={'Content-Type': 'application/json'})
    try:
        res = urllib.request.urlopen(req)
        return json.loads(res.read())['data']['access']
    except Exception as e:
        print('Login failed:', e)
        return None

async def test_ws(token):
    try:
        async with websockets.connect(f'ws://127.0.0.1:8000/ws/events/?token={token}') as ws:
            print('WS Connected!')
    except Exception as e:
        print('WS failed:', e)

token = get_token()
if token:
    asyncio.run(test_ws(token))
