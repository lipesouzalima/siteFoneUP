import urllib.request
url = "https://www.iplace.com.br/file/general/iplaceprd_130126_iphone16e_camera_small.png"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as resp:
        print("Success:", len(resp.read()))
except Exception as e:
    print("Fail:", e)
