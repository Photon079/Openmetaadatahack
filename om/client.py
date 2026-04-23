import requests
import base64
from config import OM_BASE_URL, OM_USERNAME, OM_PASSWORD

class OMClient:
    def __init__(self):
        self.base_url = OM_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self._login()

    def _login(self):
        login_url = f"{self.base_url}/users/login"
        encoded_pw = base64.b64encode(OM_PASSWORD.encode("utf-8")).decode("utf-8")
        
        # OM default login might use email admin@openmetadata.org if username is 'admin'
        email = "admin@openmetadata.org" if OM_USERNAME == "admin" else OM_USERNAME
        
        payload = {
            "email": email,
            "password": encoded_pw
        }
        resp = self.session.post(login_url, json=payload)
        
        if resp.status_code != 200:
            raise Exception(f"Failed to login to OpenMetadata: {resp.text}")
            
        token = resp.json().get("accessToken")
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def get(self, endpoint, params=None):
        url = f"{self.base_url}{endpoint}"
        resp = self.session.get(url, params=params)
        
        if resp.status_code != 200:
            raise Exception(f"API call to {endpoint} failed: {resp.status_code} {resp.text}")
            
        return resp.json()
