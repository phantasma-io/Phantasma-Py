import requests
import json

class PhantasmaRPC:
	url = None 

	def __init__(self, url):
		self.url = url

	def __JSON_RPC(self, method, params):
		headers = {'content-type': 'application/json'}

		payload = {
				"method": method,
				"params": params,
				"jsonrpc": "2.0",
				"id": 1,
		}
		response = requests.post(self.url, data=json.dumps(payload), headers=headers).json()

		if "jsonrpc" not in response or response["jsonrpc"] != "2.0":
			raise Exception("Invalid RPC response: missing or incorrect 'jsonrpc' version")

		if "id" not in response or response["id"] != 1:
			raise Exception("Invalid RPC response: 'id' mismatch or missing")

		if "error" in response:
			raise Exception(response["error"].get("Message", "Unknown RPC error"))

		if "result" not in response:
			raise Exception("Malformed RPC response: missing 'result' field")

		return response["result"]


	# Account methods
	def getAccount(self, addressText):
		"""
		Returns the account name and balance of given address.
		
		Args:
			addressText: Address of account
		
		"""
		params = [addressText];
		return self.__JSON_RPC("getAccount", params);	
	
	def lookUpName(self, name):
		"""
		Returns the address that owns a given name.
		
		Args:
			name: Name of account
		
		"""
		params = [name];
		return self.__JSON_RPC("lookUpName", params);	

	# Block methods
	def getBlockHeight(self, chainInput):
		"""
		Returns the height of a chain.
		
		Args:
			chainInput: Address or name of chain
		
		"""
		params = [chainInput];
		return self.__JSON_RPC("getBlockHeight", params);	
	
	def getBlockTransactionCountByHash(self, blockHash):
		"""
		Returns the number of transactions of given block hash or error if given hash is invalid or is not found.
		
		Args:
			blockHash: Hash of block
		
		"""
		params = [blockHash];
		return self.__JSON_RPC("getBlockTransactionCountByHash", params);	
	
	def getBlockByHash(self, blockHash):
		"""
		Returns information about a block by hash.
		
		Args:
			blockHash: Hash of block
		
		"""
		params = [blockHash];
		return self.__JSON_RPC("getBlockByHash", params);	
	
	def getRawBlockByHash(self, blockHash):
		"""
		Returns a serialized string, containing information about a block by hash.
		
		Args:
			blockHash: Hash of block
		
		"""
		params = [blockHash];
		return self.__JSON_RPC("getRawBlockByHash", params);	
	
	def getBlockByHeight(self, chainInput, height):
		"""
		Returns information about a block by height and chain.
		
		Args:
			chainInput: Address or name of chain
			height: Height of block
		
		"""
		params = [chainInput, height];
		return self.__JSON_RPC("getBlockByHeight", params);	
	
	def getRawBlockByHeight(self, chainInput, height):
		"""
		Returns a serialized string, in hex format, containing information about a block by height and chain.
		
		Args:
			chainInput: Address or name of chain
			height: Height of block
		
		"""
		params = [chainInput, height];
		return self.__JSON_RPC("getRawBlockByHeight", params);	
	
	def getTransactionByBlockHashAndIndex(self, blockHash, index):
		"""
		Returns the information about a transaction requested by a block hash and transaction index.
		
		Args:
			blockHash: Hash of block
			index: Index of transaction
		
		"""
		params = [blockHash, index];
		return self.__JSON_RPC("getTransactionByBlockHashAndIndex", params);	
	
	def getAddressTransactions(self, addressText, page, pageSize):
		"""
		Returns last X transactions of given address.
		
		Args:
			addressText: Address of account
			page: Index of page to return
			pageSize: Number of items to return per page
		
		"""
		params = [addressText, page, pageSize];
		return self.__JSON_RPC("getAddressTransactions", params);	
	
	def getAddressTransactionCount(self, addressText, chainInput):
		"""
		Get number of transactions in a specific address and chain
		
		Args:
			addressText: Address of account
			chainInput: Name or address of chain, optional
		
		"""
		params = [addressText, chainInput];
		return self.__JSON_RPC("getAddressTransactionCount", params);	
	
	def sendRawTransaction(self, txData):
		"""
		Allows to broadcast a signed operation on the network, but it&apos;s required to build it manually.
		
		Args:
			txData: Serialized transaction bytes, in hexadecimal format
		
		"""
		params = [txData];
		return self.__JSON_RPC("sendRawTransaction", params);	
	
	def invokeRawScript(self, chainInput, scriptData):
		"""
		Allows to invoke script based on network state, without state changes.
		
		Args:
			chainInput: Address or name of chain
			scriptData: Serialized script bytes, in hexadecimal format
		
		"""
		params = [chainInput, scriptData];
		return self.__JSON_RPC("invokeRawScript", params);	
	
	def getTransaction(self, hashText):
		"""
		Returns information about a transaction by hash.
		
		Args:
			hashText: Hash of transaction
		
		"""
		params = [hashText];
		return self.__JSON_RPC("getTransaction", params);	
	
	def cancelTransaction(self, hashText):
		"""
		Removes a pending transaction from the mempool.
		
		Args:
			hashText: Hash of transaction
		
		"""
		params = [hashText];
		return self.__JSON_RPC("cancelTransaction", params);	
	
	def getChains(self):
		"""
		Returns an array of all chains deployed in Phantasma.
		
		Args:
			None
		
		"""
		params = [];
		return self.__JSON_RPC("getChains", params);	
	
	def getTokens(self):
		"""
		Returns an array of tokens deployed in Phantasma.
		
		Args:
			None
		
		"""
		params = [];
		return self.__JSON_RPC("getTokens", params);	
	
	def getToken(self, symbol):
		"""
		Returns info about a specific token deployed in Phantasma.
		
		Args:
			symbol: Token symbol to obtain info
		
		"""
		params = [symbol];
		return self.__JSON_RPC("getToken", params);	
	
	def getTokenData(self, symbol, IDtext):
		"""
		Returns data of a non-fungible token, in hexadecimal format.
		
		Args:
			symbol: Symbol of token
			IDtext: ID of token
		
		"""
		params = [symbol, IDtext];
		return self.__JSON_RPC("getTokenData", params);	
	
	def getApps(self):
		"""
		Returns an array of apps deployed in Phantasma.
		
		Args:
			None
		
		"""
		params = [];
		return self.__JSON_RPC("getApps", params);	
	
	def getTokenTransfers(self, tokenSymbol, page, pageSize):
		"""
		Returns last X transactions of given token.
		
		Args:
			tokenSymbol: Token symbol
			page: Index of page to return
			pageSize: Number of items to return per page
		
		"""
		params = [tokenSymbol, page, pageSize];
		return self.__JSON_RPC("getTokenTransfers", params);	
	
	def getTokenTransferCount(self, tokenSymbol):
		"""
		Returns the number of transaction of a given token.
		
		Args:
			tokenSymbol: Token symbol
		
		"""
		params = [tokenSymbol];
		return self.__JSON_RPC("getTokenTransferCount", params);	
	
	def getTokenBalance(self, addressText, tokenSymbol, chainInput):
		"""
		Returns the balance for a specific token and chain, given an address.
		
		Args:
			addressText: Address of account
			tokenSymbol: Token symbol
			chainInput: Address or name of chain
		
		"""
		params = [addressText, tokenSymbol, chainInput];
		return self.__JSON_RPC("getTokenBalance", params);	
	
	def getAuctionsCount(self, chainAddressOrName, symbol):
		"""
		Returns the number of active auctions.
		
		Args:
			chainAddressOrName: Chain address or name where the market is located
			symbol: Token symbol used as filter
		
		"""
		params = [chainAddressOrName, symbol];
		return self.__JSON_RPC("getAuctionsCount", params);	
	
	def getAuctions(self, chainAddressOrName, symbol, page, pageSize):
		"""
		Returns the auctions available in the market.
		
		Args:
			chainAddressOrName: Chain address or name where the market is located
			symbol: Token symbol used as filter
			page: Index of page to return
			pageSize: Number of items to return per page
		
		"""
		params = [chainAddressOrName, symbol, page, pageSize];
		return self.__JSON_RPC("getAuctions", params);	
	
	def getAuction(self, chainAddressOrName, symbol, IDtext):
		"""
		Returns the auction for a specific token.
		
		Args:
			chainAddressOrName: Chain address or name where the market is located
			symbol: Token symbol
			IDtext: Token ID
		
		"""
		params = [chainAddressOrName, symbol, IDtext];
		return self.__JSON_RPC("getAuction", params);	
	
	def getArchive(self, hashText):
		"""
		Returns info about a specific archive.
		
		Args:
			hashText: Archive hash
		
		"""
		params = [hashText];
		return self.__JSON_RPC("getArchive", params);	
	
	