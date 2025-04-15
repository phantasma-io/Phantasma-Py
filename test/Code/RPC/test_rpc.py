import unittest
from phantasma_py.API import ApiClient, Configuration
from phantasma_py.API.API import AccountApi

class TestRpc(unittest.TestCase):
    def test_rpc_working(self):
        apiURL = "https://pharpc1.phantasma.info"
        config = Configuration()
        config.host = apiURL
        api = ApiClient(configuration=config)
        accountAPI = AccountApi(api)
        account = accountAPI.GetAccount(account="P2K7YKXhG8uvdpATM2oe5i6bCEDuQiNq2kSaeiZcakMWZTZ")
        print(account)
        #self.assertEqual(True, False)  # add assertion here


if __name__ == '__main__':
    unittest.main()
