# Phantasma Py

# swagger-client

No description provided (generated by Swagger Codegen https://github.com/swagger-api/swagger-codegen)

This Python package is automatically generated by the [Swagger Codegen](https://github.com/swagger-api/swagger-codegen) project:

- API version: v1
- Package version: 1.0.0
- Build package: io.swagger.codegen.v3.generators.python.PythonClientCodegen
  For more information, please visit [https://phantasma.io](https://phantasma.io)

## Requirements.

Python 2.7 and 3.4+

## Installation & Usage

### pip install

If the python package is hosted on Github, you can install directly from Github

```sh
pip install git+https://github.com/phantasma-io/Phantasma-Py.git
```

(you may need to run `pip` with root permission: `sudo pip install git+https://github.com/phantasma-io/Phantasma-Py.git`)

Then import the package:

```python
import swagger_client
```

### Setuptools

Install via [Setuptools](http://pypi.python.org/pypi/setuptools).

```sh
python setup.py install --user
```

(or `sudo python setup.py install` to install the package for all users)

Then import the package:

```python
import swagger_client
```

## Getting Started

Please follow the [installation procedure](#installation--usage) and then run the following:

```python
from __future__ import print_function
import time
import swagger_client
from swagger_client.rest import ApiException
from pprint import pprint

# create an instance of the API class
api_instance = swagger_client.AccountApi(swagger_client.ApiClient(configuration))
account = 'account_example' # str |  (optional)

try:
    api_response = api_instance.api_v1_get_account_get(account=account)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling AccountApi->api_v1_get_account_get: %s\n" % e)

# create an instance of the API class
api_instance = swagger_client.AccountApi(swagger_client.ApiClient(configuration))
account_text = 'account_text_example' # str |  (optional)

try:
    api_response = api_instance.api_v1_get_accounts_get(account_text=account_text)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling AccountApi->api_v1_get_accounts_get: %s\n" % e)

# create an instance of the API class
api_instance = swagger_client.AccountApi(swagger_client.ApiClient(configuration))
symbol = 'symbol_example' # str |  (optional)
extended = false # bool |  (optional) (default to false)

try:
    api_response = api_instance.api_v1_get_addresses_by_symbol_get(symbol=symbol, extended=extended)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling AccountApi->api_v1_get_addresses_by_symbol_get: %s\n" % e)

# create an instance of the API class
api_instance = swagger_client.AccountApi(swagger_client.ApiClient(configuration))
name = 'name_example' # str |  (optional)

try:
    api_response = api_instance.api_v1_look_up_name_get(name=name)
    pprint(api_response)
except ApiException as e:
    print("Exception when calling AccountApi->api_v1_look_up_name_get: %s\n" % e)
```

## Documentation for API Endpoints

All URIs are relative to _/_

| Class             | Method                                                                                                                              | HTTP request                                      | Description |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------- | ----------- |
| _AccountApi_      | [**api_v1_get_account_get**](docs/AccountApi.md#api_v1_get_account_get)                                                             | **GET** /api/v1/GetAccount                        |
| _AccountApi_      | [**api_v1_get_accounts_get**](docs/AccountApi.md#api_v1_get_accounts_get)                                                           | **GET** /api/v1/GetAccounts                       |
| _AccountApi_      | [**api_v1_get_addresses_by_symbol_get**](docs/AccountApi.md#api_v1_get_addresses_by_symbol_get)                                     | **GET** /api/v1/GetAddressesBySymbol              |
| _AccountApi_      | [**api_v1_look_up_name_get**](docs/AccountApi.md#api_v1_look_up_name_get)                                                           | **GET** /api/v1/LookUpName                        |
| _AuctionApi_      | [**api_v1_get_auction_get**](docs/AuctionApi.md#api_v1_get_auction_get)                                                             | **GET** /api/v1/GetAuction                        |
| _AuctionApi_      | [**api_v1_get_auctions_count_get**](docs/AuctionApi.md#api_v1_get_auctions_count_get)                                               | **GET** /api/v1/GetAuctionsCount                  |
| _AuctionApi_      | [**api_v1_get_auctions_get**](docs/AuctionApi.md#api_v1_get_auctions_get)                                                           | **GET** /api/v1/GetAuctions                       |
| _BlockApi_        | [**api_v1_get_block_by_hash_get**](docs/BlockApi.md#api_v1_get_block_by_hash_get)                                                   | **GET** /api/v1/GetBlockByHash                    |
| _BlockApi_        | [**api_v1_get_block_by_height_get**](docs/BlockApi.md#api_v1_get_block_by_height_get)                                               | **GET** /api/v1/GetBlockByHeight                  |
| _BlockApi_        | [**api_v1_get_block_height_get**](docs/BlockApi.md#api_v1_get_block_height_get)                                                     | **GET** /api/v1/GetBlockHeight                    |
| _BlockApi_        | [**api_v1_get_block_transaction_count_by_hash_get**](docs/BlockApi.md#api_v1_get_block_transaction_count_by_hash_get)               | **GET** /api/v1/GetBlockTransactionCountByHash    |
| _BlockApi_        | [**api_v1_get_latest_block_get**](docs/BlockApi.md#api_v1_get_latest_block_get)                                                     | **GET** /api/v1/GetLatestBlock                    |
| _BlockApi_        | [**api_v1_get_raw_block_by_hash_get**](docs/BlockApi.md#api_v1_get_raw_block_by_hash_get)                                           | **GET** /api/v1/GetRawBlockByHash                 |
| _BlockApi_        | [**api_v1_get_raw_block_by_height_get**](docs/BlockApi.md#api_v1_get_raw_block_by_height_get)                                       | **GET** /api/v1/GetRawBlockByHeight               |
| _BlockApi_        | [**api_v1_get_raw_latest_block_get**](docs/BlockApi.md#api_v1_get_raw_latest_block_get)                                             | **GET** /api/v1/GetRawLatestBlock                 |
| _ChainApi_        | [**api_v1_get_chains_get**](docs/ChainApi.md#api_v1_get_chains_get)                                                                 | **GET** /api/v1/GetChains                         |
| _ConnectionApi_   | [**api_v1_abci_query_get**](docs/ConnectionApi.md#api_v1_abci_query_get)                                                            | **GET** /api/v1/abci_query                        |
| _ConnectionApi_   | [**api_v1_get_validators_settings_get**](docs/ConnectionApi.md#api_v1_get_validators_settings_get)                                  | **GET** /api/v1/GetValidatorsSettings             |
| _ConnectionApi_   | [**api_v1_health_get**](docs/ConnectionApi.md#api_v1_health_get)                                                                    | **GET** /api/v1/health                            |
| _ConnectionApi_   | [**api_v1_net_info_get**](docs/ConnectionApi.md#api_v1_net_info_get)                                                                | **GET** /api/v1/net_info                          |
| _ConnectionApi_   | [**api_v1_request_block_get**](docs/ConnectionApi.md#api_v1_request_block_get)                                                      | **GET** /api/v1/request_block                     |
| _ConnectionApi_   | [**api_v1_status_get**](docs/ConnectionApi.md#api_v1_status_get)                                                                    | **GET** /api/v1/status                            |
| _ContractApi_     | [**api_v1_get_contract_by_address_get**](docs/ContractApi.md#api_v1_get_contract_by_address_get)                                    | **GET** /api/v1/GetContractByAddress              |
| _ContractApi_     | [**api_v1_get_contract_get**](docs/ContractApi.md#api_v1_get_contract_get)                                                          | **GET** /api/v1/GetContract                       |
| _LeaderboardApi_  | [**api_v1_get_leaderboard_get**](docs/LeaderboardApi.md#api_v1_get_leaderboard_get)                                                 | **GET** /api/v1/GetLeaderboard                    |
| _NexusApi_        | [**api_v1_get_nexus_get**](docs/NexusApi.md#api_v1_get_nexus_get)                                                                   | **GET** /api/v1/GetNexus                          |
| _OrganizationApi_ | [**api_v1_get_organization_by_name_get**](docs/OrganizationApi.md#api_v1_get_organization_by_name_get)                              | **GET** /api/v1/GetOrganizationByName             |
| _OrganizationApi_ | [**api_v1_get_organization_get**](docs/OrganizationApi.md#api_v1_get_organization_get)                                              | **GET** /api/v1/GetOrganization                   |
| _OrganizationApi_ | [**api_v1_get_organizations_get**](docs/OrganizationApi.md#api_v1_get_organizations_get)                                            | **GET** /api/v1/GetOrganizations                  |
| _PlatformApi_     | [**api_v1_get_interop_get**](docs/PlatformApi.md#api_v1_get_interop_get)                                                            | **GET** /api/v1/GetInterop                        |
| _PlatformApi_     | [**api_v1_get_platform_get**](docs/PlatformApi.md#api_v1_get_platform_get)                                                          | **GET** /api/v1/GetPlatform                       |
| _PlatformApi_     | [**api_v1_get_platforms_get**](docs/PlatformApi.md#api_v1_get_platforms_get)                                                        | **GET** /api/v1/GetPlatforms                      |
| _RpcApi_          | [**rpc_post**](docs/RpcApi.md#rpc_post)                                                                                             | **POST** /rpc                                     |
| _SaleApi_         | [**api_v1_get_latest_sale_hash_get**](docs/SaleApi.md#api_v1_get_latest_sale_hash_get)                                              | **GET** /api/v1/GetLatestSaleHash                 |
| _SaleApi_         | [**api_v1_get_sale_get**](docs/SaleApi.md#api_v1_get_sale_get)                                                                      | **GET** /api/v1/GetSale                           |
| _TokenApi_        | [**api_v1_get_nft_get**](docs/TokenApi.md#api_v1_get_nft_get)                                                                       | **GET** /api/v1/GetNFT                            |
| _TokenApi_        | [**api_v1_get_nfts_get**](docs/TokenApi.md#api_v1_get_nfts_get)                                                                     | **GET** /api/v1/GetNFTs                           |
| _TokenApi_        | [**api_v1_get_token_balance_get**](docs/TokenApi.md#api_v1_get_token_balance_get)                                                   | **GET** /api/v1/GetTokenBalance                   |
| _TokenApi_        | [**api_v1_get_token_data_get**](docs/TokenApi.md#api_v1_get_token_data_get)                                                         | **GET** /api/v1/GetTokenData                      |
| _TokenApi_        | [**api_v1_get_token_get**](docs/TokenApi.md#api_v1_get_token_get)                                                                   | **GET** /api/v1/GetToken                          |
| _TokenApi_        | [**api_v1_get_tokens_get**](docs/TokenApi.md#api_v1_get_tokens_get)                                                                 | **GET** /api/v1/GetTokens                         |
| _TransactionApi_  | [**api_v1_get_address_transaction_count_get**](docs/TransactionApi.md#api_v1_get_address_transaction_count_get)                     | **GET** /api/v1/GetAddressTransactionCount        |
| _TransactionApi_  | [**api_v1_get_address_transactions_get**](docs/TransactionApi.md#api_v1_get_address_transactions_get)                               | **GET** /api/v1/GetAddressTransactions            |
| _TransactionApi_  | [**api_v1_get_transaction_by_block_hash_and_index_get**](docs/TransactionApi.md#api_v1_get_transaction_by_block_hash_and_index_get) | **GET** /api/v1/GetTransactionByBlockHashAndIndex |
| _TransactionApi_  | [**api_v1_get_transaction_get**](docs/TransactionApi.md#api_v1_get_transaction_get)                                                 | **GET** /api/v1/GetTransaction                    |
| _TransactionApi_  | [**api_v1_invoke_raw_script_get**](docs/TransactionApi.md#api_v1_invoke_raw_script_get)                                             | **GET** /api/v1/InvokeRawScript                   |
| _TransactionApi_  | [**api_v1_send_raw_transaction_get**](docs/TransactionApi.md#api_v1_send_raw_transaction_get)                                       | **GET** /api/v1/SendRawTransaction                |
| _ValidatorApi_    | [**api_v1_get_validators_get**](docs/ValidatorApi.md#api_v1_get_validators_get)                                                     | **GET** /api/v1/GetValidators                     |
| _ValidatorApi_    | [**api_v1_get_validators_type_get**](docs/ValidatorApi.md#api_v1_get_validators_type_get)                                           | **GET** /api/v1/GetValidators/{type}              |

## Documentation For Models

- [ABIEventResult](docs/ABIEventResult.md)
- [ABIMethodResult](docs/ABIMethodResult.md)
- [ABIParameterResult](docs/ABIParameterResult.md)
- [AccountResult](docs/AccountResult.md)
- [Address](docs/Address.md)
- [AddressKind](docs/AddressKind.md)
- [ArchiveResult](docs/ArchiveResult.md)
- [AuctionResult](docs/AuctionResult.md)
- [BalanceResult](docs/BalanceResult.md)
- [BlockResult](docs/BlockResult.md)
- [ChainResult](docs/ChainResult.md)
- [ContractResult](docs/ContractResult.md)
- [CrowdsaleResult](docs/CrowdsaleResult.md)
- [EventResult](docs/EventResult.md)
- [GovernanceResult](docs/GovernanceResult.md)
- [InteropResult](docs/InteropResult.md)
- [LeaderboardResult](docs/LeaderboardResult.md)
- [LeaderboardRowResult](docs/LeaderboardRowResult.md)
- [NetInfoPeer](docs/NetInfoPeer.md)
- [NetInfoPeerConnectionStatus](docs/NetInfoPeerConnectionStatus.md)
- [NetInfoPeerConnectionStatusChannel](docs/NetInfoPeerConnectionStatusChannel.md)
- [NetInfoPeerConnectionStatusMonitor](docs/NetInfoPeerConnectionStatusMonitor.md)
- [NexusResult](docs/NexusResult.md)
- [NodeInfo](docs/NodeInfo.md)
- [NodeInfoOther](docs/NodeInfoOther.md)
- [NodeInfoProtocolVersion](docs/NodeInfoProtocolVersion.md)
- [OracleResult](docs/OracleResult.md)
- [OrganizationResult](docs/OrganizationResult.md)
- [PaginatedResult](docs/PaginatedResult.md)
- [PlatformResult](docs/PlatformResult.md)
- [PubKey](docs/PubKey.md)
- [ResponseQuery](docs/ResponseQuery.md)
- [ResultAbciQuery](docs/ResultAbciQuery.md)
- [ResultHealth](docs/ResultHealth.md)
- [ResultNetInfo](docs/ResultNetInfo.md)
- [ResultStatus](docs/ResultStatus.md)
- [ResultStatusSyncInfo](docs/ResultStatusSyncInfo.md)
- [ResultStatusValidatorInfo](docs/ResultStatusValidatorInfo.md)
- [RpcRequest](docs/RpcRequest.md)
- [RpcResponse](docs/RpcResponse.md)
- [ScriptResult](docs/ScriptResult.md)
- [SignatureResult](docs/SignatureResult.md)
- [StakeResult](docs/StakeResult.md)
- [StorageResult](docs/StorageResult.md)
- [TokenDataResult](docs/TokenDataResult.md)
- [TokenExternalResult](docs/TokenExternalResult.md)
- [TokenPriceResult](docs/TokenPriceResult.md)
- [TokenPropertyResult](docs/TokenPropertyResult.md)
- [TokenResult](docs/TokenResult.md)
- [TokenSeriesResult](docs/TokenSeriesResult.md)
- [TransactionResult](docs/TransactionResult.md)
- [ValidatorResult](docs/ValidatorResult.md)
- [ValidatorSettings](docs/ValidatorSettings.md)

## Documentation For Authorization

All endpoints do not require authorization.

## Python VM Samples

The VM Module implements the following classes EventDecoder, ScriptBuilder and Transaction in order to provide support to:

- Decode TX events data.
  Examples:
  /Python/Samples/VMSamples/parsetxevents.py

- Create Scripts, Transactions and Sign them using HEX Private Key.
  Examples:
  /Python/Samples/VMSamples/transferFungible.py
  /Python/Samples/VMSamples/transferNonFungible.py