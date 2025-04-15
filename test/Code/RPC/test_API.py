import unittest
from phantasma_py.RPC import PhantasmaAPI

class TestAPI(unittest.TestCase):
    def test_something(self):
        API = PhantasmaAPI("https://pharpc1.phantasma.info")
        account = API.getAccount("P2K7YKXhG8uvdpATM2oe5i6bCEDuQiNq2kSaeiZcakMWZTZ")
        print(account)
        #self.assertEqual(True, False)  # add assertion here


if __name__ == '__main__':
    unittest.main()
