import os

httpx_base_url = 'https://api-west.millis.ai'

def get_httpx_headers():
    return {
        "Authorization": os.getenv('MILLIS_API_PRIVATE_KEY')
    }
