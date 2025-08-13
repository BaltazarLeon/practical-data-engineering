import requests

# Your cookie and user agent
cf_clearance = "tmEcqu8TPoEZinWFhNKYXWCVa__03jy.Srm8cnNAs7s-1755055749-1.2.1.1-NPpjzpt3UZfAjsV2PvbA6pLrUde3fE1X.V4KZICfwFso_ZL_peboAgZLE.MaSRylQdpOQF5uxigCsDEdryhydiIcLjVqKtTVpv7iyVmZPbs9.LuDJH52EzVtKOUENWc04WjbkF2VXQdbJn24j1r3Ni6ma8NaTMhAjkSTGKeiRmdI.4nxcjYqh873N9l6Ldn0p7Fm6Vo6teYx0ulwilRO1RgRXipkCcOEFpo5bWlntzTy74Y03WW0kIBRuCmxBXsk"
user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"

# Test request
session = requests.Session()
session.headers.update({
    'User-Agent': user_agent,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
})
session.cookies.set('cf_clearance', cf_clearance, domain='.inmuebles24.com')

# Test with the exact same URL format from your Unflare request
url = "https://www.inmuebles24.com/departamentos-en-venta-en-ciudad-de-mexico-mas-de-5-pesos-pagina-6.html"

response = session.get(url)
print(f"Status: {response.status_code}")
print(f"Content-Type: {response.headers.get('content-type')}")
print(f"First 500 chars of response:")
print(response.text)