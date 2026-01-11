import requests
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('GOOGLE_MAPS_API_KEY')
lat, lng = 42.3868, -72.5301  # UMass Amherst

url = "https://maps.googleapis.com/maps/api/streetview/metadata"
params = {
    'location': f'{lat},{lng}',
    'key': api_key
}

response = requests.get(url, params=params)
print(response.json())