import urllib.request
import re

try:
    html = urllib.request.urlopen('http://127.0.0.1:8000/dashboard/restaurant/d6b017d7-c921-4d8c-905d-86bbd45d2885/tables/').read().decode('utf-8')
    urls = re.findall(r'hx-get="(/dashboard/restaurant/[^"]+/edit/)"', html)
    print('Found URLs:', urls)
    if urls:
        print('Fetching:', urls[0])
        res = urllib.request.urlopen('http://127.0.0.1:8000' + urls[0])
        print('Status:', res.status)
except Exception as e:
    import traceback
    traceback.print_exc()
