import requests

url = "https://www.searchapi.io/api/v1/search"
params = {
  "engine": "google_images",
  "q": "apple"
}

response = requests.get(url, params=params)
print(response.text)

