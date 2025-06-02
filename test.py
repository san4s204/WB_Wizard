import requests
import json

url = "https://seller-content.wildberries.ru/ns/analytics-api/content-analytics/api/v2/product/search-texts?nm_id=156960074"

payload = {}
headers = {
  'accept': '*/*',
  'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
  'content-type': 'application/json',
  'cookie': '__bsa=basket-ru-21; ___wbu=4211469e-c015-4562-a220-e87c052e416a.1717486866; wbx-validation-key=41427566-556b-4be5-9abf-b23616e077af; _wbauid=4965581071741317518; external-locale=ru; x-supplier-id-external=a59b225e-1830-4679-9523-4f92170eae3f; WBTokenV3=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE3NDEzMTc1NjIsInZlcnNpb24iOjIsInVzZXIiOiI1Mjk2MDUxNCIsInNoYXJkX2tleSI6IjE5IiwiY2xpZW50X2lkIjoic2VsbGVyLXBvcnRhbCIsInNlc3Npb25faWQiOiI1MzQ0ZWIwY2MxMjA0MGJmODgzN2I4ZTJjYjdkYmQxNSIsInVzZXJfcmVnaXN0cmF0aW9uX2R0IjoxNjkwMTc2NzY3LCJ2YWxpZGF0aW9uX2tleSI6ImQzMmU0MjgzYTIyY2YzZGVjZjRlZTFkNDM4NjUyZjI3Yjg5NGI4N2FmYjUxNzJjOTRiZDdiMjJmZjA4NTI0ZjMifQ.EloOIVyj37_EOzXkMzmf-ZjPhI36OaJ1RF-IdXOpeV2Lh8vNSejOc5KP-vYl69dDX8mjz3eKg-uIneKw1Q1qFrjCPhvDQtra7hc9iwbJ3EqO_Ex-bbWRYGJPLb_rdSKt8GBOcUD84V3rvzCiitz3zLQ5y9W0xI2MX3ANwNNW7oWaUdL5DrWJIcbci8xxS5ArIckc0JP2A2p34Dk_j7JxwXo1trfBlNaNJDEGIqPC7XUDWo8rlYq7uMbzsUBwRbdO41yHyTEbtON3yQB-zF70cAbig3kUhB-JkzrLmbFZU4VsPEhizLvLkbQNLmpvDUY7V-tVdEBKbZNFt0gIsD0aaQ',
  'origin': 'https://seller.wildberries.ru',
  'priority': 'u=1, i',
  'referer': 'https://seller.wildberries.ru/',
  'sec-ch-ua': '"Opera GX";v="116", "Chromium";v="131", "Not_A Brand";v="24"',
  'sec-ch-ua-mobile': '?0',
  'sec-ch-ua-platform': '"Windows"',
  'sec-fetch-dest': 'empty',
  'sec-fetch-mode': 'cors',
  'sec-fetch-site': 'same-site',
  'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 OPR/116.0.0.0 (Edition Yx GX)'
}

response = requests.request("GET", url, headers=headers, data=payload)

print(response.text)
