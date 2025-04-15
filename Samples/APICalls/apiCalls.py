import json
import requests
import sys

sys.path.append("../../src/swagger_client")


import swagger_client
from swagger_client.api.account_api import AccountApi  # noqa: E501
from swagger_client.rest import ApiException

try:
    config = swagger_client.Configuration()
    config.host = "http://testnet.phantasma.info"
    config.verify_ssl = False
    client = swagger_client.ApiClient(config)
    api = AccountApi(client)
    response = api.api_v1_get_account_get(async_req=False, account="P2KF1znccUWFAxNQBczuKdBReRbBtqb9qsyC7fF9SRHTGBy")
    print(response)

except Exception as ex:
    print("error", ex)
