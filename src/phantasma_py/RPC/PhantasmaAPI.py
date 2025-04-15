import requests
import json

class PhantasmaAPI:
	base_url = None 

	def __init__(self, base_url="https://phantasma.info"):
		self.base_url = base_url
		self.session = requests.Session()
		self.session.headers.update({"Content-Type": "application/json"})

	def _request(self, method, endpoint, params=None, json=None):
		url = f"{self.base_url}{endpoint}"
		response = self.session.request(method, url, params=params, json=json)

		if response.status_code == 200:
			return response.json()
		else:
			response.raise_for_status()


	# Account methods
	def getAccount(self, account):
		endpoint = "/api/v1/GetAccount"
		params = {"account": account}
		return self._request("GET", endpoint, params=params)

	def getAccounts(self, account_text):
		endpoint = "/api/v1/GetAccounts"
		params = {"accountText": account_text}
		return self._request("GET", endpoint, params=params)