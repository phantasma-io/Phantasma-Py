# coding: utf-8

"""
    Phantasma API

    No description provided (generated by Swagger Codegen https://github.com/swagger-api/swagger-codegen)  # noqa: E501

    OpenAPI spec version: v1
    
    Generated by: https://github.com/swagger-api/swagger-codegen.git
"""

from __future__ import absolute_import

import re  # noqa: F401

# python 2 and python 3 compatibility library
import six

from ..api_client import ApiClient


class TokenApi(object):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    Ref: https://github.com/swagger-api/swagger-codegen
    """

    def __init__(self, api_client=None):
        if api_client is None:
            api_client = ApiClient()
        self.api_client = api_client

    def GetNFT(self, **kwargs):  # noqa: E501
        """api_v1_get_nft_get  # noqa: E501

        This method makes a synchronous HTTP request by default. To make an
        asynchronous HTTP request, please pass async_req=True
        >>> thread = api.api_v1_get_nft_get(async_req=True)
        >>> result = thread.get()

        :param async_req bool
        :param str symbol:
        :param str i_dtext:
        :param bool extended:
        :return: TokenDataResult
                 If the method is called asynchronously,
                 returns the request thread.
        """
        kwargs['_return_http_data_only'] = True
        if kwargs.get('async_req'):
            return self.api_v1_get_nft_get_with_http_info(**kwargs)  # noqa: E501
        else:
            (data) = self.api_v1_get_nft_get_with_http_info(**kwargs)  # noqa: E501
            return data

    def api_v1_get_nft_get_with_http_info(self, **kwargs):  # noqa: E501
        """api_v1_get_nft_get  # noqa: E501

        This method makes a synchronous HTTP request by default. To make an
        asynchronous HTTP request, please pass async_req=True
        >>> thread = api.api_v1_get_nft_get_with_http_info(async_req=True)
        >>> result = thread.get()

        :param async_req bool
        :param str symbol:
        :param str i_dtext:
        :param bool extended:
        :return: TokenDataResult
                 If the method is called asynchronously,
                 returns the request thread.
        """

        all_params = ['symbol', 'i_dtext', 'extended']  # noqa: E501
        all_params.append('async_req')
        all_params.append('_return_http_data_only')
        all_params.append('_preload_content')
        all_params.append('_request_timeout')

        params = locals()
        for key, val in six.iteritems(params['kwargs']):
            if key not in all_params:
                raise TypeError(
                    "Got an unexpected keyword argument '%s'"
                    " to method api_v1_get_nft_get" % key
                )
            params[key] = val
        del params['kwargs']

        collection_formats = {}

        path_params = {}

        query_params = []
        if 'symbol' in params:
            query_params.append(('symbol', params['symbol']))  # noqa: E501
        if 'i_dtext' in params:
            query_params.append(('IDtext', params['i_dtext']))  # noqa: E501
        if 'extended' in params:
            query_params.append(('extended', params['extended']))  # noqa: E501

        header_params = {}

        form_params = []
        local_var_files = {}

        body_params = None
        # HTTP header `Accept`
        header_params['Accept'] = self.api_client.select_header_accept(
            ['application/json'])  # noqa: E501

        # Authentication setting
        auth_settings = []  # noqa: E501

        return self.api_client.call_api(
            '/api/v1/GetNFT', 'GET',
            path_params,
            query_params,
            header_params,
            body=body_params,
            post_params=form_params,
            files=local_var_files,
            response_type='TokenDataResult',  # noqa: E501
            auth_settings=auth_settings,
            async_req=params.get('async_req'),
            _return_http_data_only=params.get('_return_http_data_only'),
            _preload_content=params.get('_preload_content', True),
            _request_timeout=params.get('_request_timeout'),
            collection_formats=collection_formats)

    def GetNFTs(self, **kwargs):  # noqa: E501
        """api_v1_get_nfts_get  # noqa: E501

        This method makes a synchronous HTTP request by default. To make an
        asynchronous HTTP request, please pass async_req=True
        >>> thread = api.api_v1_get_nfts_get(async_req=True)
        >>> result = thread.get()

        :param async_req bool
        :param str symbol:
        :param str id_text:
        :param bool extended:
        :return: list[TokenDataResult]
                 If the method is called asynchronously,
                 returns the request thread.
        """
        kwargs['_return_http_data_only'] = True
        if kwargs.get('async_req'):
            return self.api_v1_get_nfts_get_with_http_info(**kwargs)  # noqa: E501
        else:
            (data) = self.api_v1_get_nfts_get_with_http_info(**kwargs)  # noqa: E501
            return data

    def api_v1_get_nfts_get_with_http_info(self, **kwargs):  # noqa: E501
        """api_v1_get_nfts_get  # noqa: E501

        This method makes a synchronous HTTP request by default. To make an
        asynchronous HTTP request, please pass async_req=True
        >>> thread = api.api_v1_get_nfts_get_with_http_info(async_req=True)
        >>> result = thread.get()

        :param async_req bool
        :param str symbol:
        :param str id_text:
        :param bool extended:
        :return: list[TokenDataResult]
                 If the method is called asynchronously,
                 returns the request thread.
        """

        all_params = ['symbol', 'id_text', 'extended']  # noqa: E501
        all_params.append('async_req')
        all_params.append('_return_http_data_only')
        all_params.append('_preload_content')
        all_params.append('_request_timeout')

        params = locals()
        for key, val in six.iteritems(params['kwargs']):
            if key not in all_params:
                raise TypeError(
                    "Got an unexpected keyword argument '%s'"
                    " to method api_v1_get_nfts_get" % key
                )
            params[key] = val
        del params['kwargs']

        collection_formats = {}

        path_params = {}

        query_params = []
        if 'symbol' in params:
            query_params.append(('symbol', params['symbol']))  # noqa: E501
        if 'id_text' in params:
            query_params.append(('IDText', params['id_text']))  # noqa: E501
        if 'extended' in params:
            query_params.append(('extended', params['extended']))  # noqa: E501

        header_params = {}

        form_params = []
        local_var_files = {}

        body_params = None
        # HTTP header `Accept`
        header_params['Accept'] = self.api_client.select_header_accept(
            ['application/json'])  # noqa: E501

        # Authentication setting
        auth_settings = []  # noqa: E501

        return self.api_client.call_api(
            '/api/v1/GetNFTs', 'GET',
            path_params,
            query_params,
            header_params,
            body=body_params,
            post_params=form_params,
            files=local_var_files,
            response_type='list[TokenDataResult]',  # noqa: E501
            auth_settings=auth_settings,
            async_req=params.get('async_req'),
            _return_http_data_only=params.get('_return_http_data_only'),
            _preload_content=params.get('_preload_content', True),
            _request_timeout=params.get('_request_timeout'),
            collection_formats=collection_formats)

    def GetTokenBalance(self, **kwargs):  # noqa: E501
        """api_v1_get_token_balance_get  # noqa: E501

        This method makes a synchronous HTTP request by default. To make an
        asynchronous HTTP request, please pass async_req=True
        >>> thread = api.api_v1_get_token_balance_get(async_req=True)
        >>> result = thread.get()

        :param async_req bool
        :param str account:
        :param str token_symbol:
        :param str chain_input:
        :return: BalanceResult
                 If the method is called asynchronously,
                 returns the request thread.
        """
        kwargs['_return_http_data_only'] = True
        if kwargs.get('async_req'):
            return self.api_v1_get_token_balance_get_with_http_info(**kwargs)  # noqa: E501
        else:
            (data) = self.api_v1_get_token_balance_get_with_http_info(**kwargs)  # noqa: E501
            return data

    def api_v1_get_token_balance_get_with_http_info(self, **kwargs):  # noqa: E501
        """api_v1_get_token_balance_get  # noqa: E501

        This method makes a synchronous HTTP request by default. To make an
        asynchronous HTTP request, please pass async_req=True
        >>> thread = api.api_v1_get_token_balance_get_with_http_info(async_req=True)
        >>> result = thread.get()

        :param async_req bool
        :param str account:
        :param str token_symbol:
        :param str chain_input:
        :return: BalanceResult
                 If the method is called asynchronously,
                 returns the request thread.
        """

        all_params = ['account', 'token_symbol', 'chain_input']  # noqa: E501
        all_params.append('async_req')
        all_params.append('_return_http_data_only')
        all_params.append('_preload_content')
        all_params.append('_request_timeout')

        params = locals()
        for key, val in six.iteritems(params['kwargs']):
            if key not in all_params:
                raise TypeError(
                    "Got an unexpected keyword argument '%s'"
                    " to method api_v1_get_token_balance_get" % key
                )
            params[key] = val
        del params['kwargs']

        collection_formats = {}

        path_params = {}

        query_params = []
        if 'account' in params:
            query_params.append(('account', params['account']))  # noqa: E501
        if 'token_symbol' in params:
            query_params.append(('tokenSymbol', params['token_symbol']))  # noqa: E501
        if 'chain_input' in params:
            query_params.append(('chainInput', params['chain_input']))  # noqa: E501

        header_params = {}

        form_params = []
        local_var_files = {}

        body_params = None
        # HTTP header `Accept`
        header_params['Accept'] = self.api_client.select_header_accept(
            ['application/json'])  # noqa: E501

        # Authentication setting
        auth_settings = []  # noqa: E501

        return self.api_client.call_api(
            '/api/v1/GetTokenBalance', 'GET',
            path_params,
            query_params,
            header_params,
            body=body_params,
            post_params=form_params,
            files=local_var_files,
            response_type='BalanceResult',  # noqa: E501
            auth_settings=auth_settings,
            async_req=params.get('async_req'),
            _return_http_data_only=params.get('_return_http_data_only'),
            _preload_content=params.get('_preload_content', True),
            _request_timeout=params.get('_request_timeout'),
            collection_formats=collection_formats)

    def GetTokenData(self, **kwargs):  # noqa: E501
        """api_v1_get_token_data_get  # noqa: E501

        This method makes a synchronous HTTP request by default. To make an
        asynchronous HTTP request, please pass async_req=True
        >>> thread = api.api_v1_get_token_data_get(async_req=True)
        >>> result = thread.get()

        :param async_req bool
        :param str symbol:
        :param str i_dtext:
        :return: TokenDataResult
                 If the method is called asynchronously,
                 returns the request thread.
        """
        kwargs['_return_http_data_only'] = True
        if kwargs.get('async_req'):
            return self.api_v1_get_token_data_get_with_http_info(**kwargs)  # noqa: E501
        else:
            (data) = self.api_v1_get_token_data_get_with_http_info(**kwargs)  # noqa: E501
            return data

    def api_v1_get_token_data_get_with_http_info(self, **kwargs):  # noqa: E501
        """api_v1_get_token_data_get  # noqa: E501

        This method makes a synchronous HTTP request by default. To make an
        asynchronous HTTP request, please pass async_req=True
        >>> thread = api.api_v1_get_token_data_get_with_http_info(async_req=True)
        >>> result = thread.get()

        :param async_req bool
        :param str symbol:
        :param str i_dtext:
        :return: TokenDataResult
                 If the method is called asynchronously,
                 returns the request thread.
        """

        all_params = ['symbol', 'i_dtext']  # noqa: E501
        all_params.append('async_req')
        all_params.append('_return_http_data_only')
        all_params.append('_preload_content')
        all_params.append('_request_timeout')

        params = locals()
        for key, val in six.iteritems(params['kwargs']):
            if key not in all_params:
                raise TypeError(
                    "Got an unexpected keyword argument '%s'"
                    " to method api_v1_get_token_data_get" % key
                )
            params[key] = val
        del params['kwargs']

        collection_formats = {}

        path_params = {}

        query_params = []
        if 'symbol' in params:
            query_params.append(('symbol', params['symbol']))  # noqa: E501
        if 'i_dtext' in params:
            query_params.append(('IDtext', params['i_dtext']))  # noqa: E501

        header_params = {}

        form_params = []
        local_var_files = {}

        body_params = None
        # HTTP header `Accept`
        header_params['Accept'] = self.api_client.select_header_accept(
            ['application/json'])  # noqa: E501

        # Authentication setting
        auth_settings = []  # noqa: E501

        return self.api_client.call_api(
            '/api/v1/GetTokenData', 'GET',
            path_params,
            query_params,
            header_params,
            body=body_params,
            post_params=form_params,
            files=local_var_files,
            response_type='TokenDataResult',  # noqa: E501
            auth_settings=auth_settings,
            async_req=params.get('async_req'),
            _return_http_data_only=params.get('_return_http_data_only'),
            _preload_content=params.get('_preload_content', True),
            _request_timeout=params.get('_request_timeout'),
            collection_formats=collection_formats)

    def GetToken(self, **kwargs):  # noqa: E501
        """api_v1_get_token_get  # noqa: E501

        This method makes a synchronous HTTP request by default. To make an
        asynchronous HTTP request, please pass async_req=True
        >>> thread = api.api_v1_get_token_get(async_req=True)
        >>> result = thread.get()

        :param async_req bool
        :param str symbol:
        :param bool extended:
        :return: TokenResult
                 If the method is called asynchronously,
                 returns the request thread.
        """
        kwargs['_return_http_data_only'] = True
        if kwargs.get('async_req'):
            return self.api_v1_get_token_get_with_http_info(**kwargs)  # noqa: E501
        else:
            (data) = self.api_v1_get_token_get_with_http_info(**kwargs)  # noqa: E501
            return data

    def api_v1_get_token_get_with_http_info(self, **kwargs):  # noqa: E501
        """api_v1_get_token_get  # noqa: E501

        This method makes a synchronous HTTP request by default. To make an
        asynchronous HTTP request, please pass async_req=True
        >>> thread = api.api_v1_get_token_get_with_http_info(async_req=True)
        >>> result = thread.get()

        :param async_req bool
        :param str symbol:
        :param bool extended:
        :return: TokenResult
                 If the method is called asynchronously,
                 returns the request thread.
        """

        all_params = ['symbol', 'extended']  # noqa: E501
        all_params.append('async_req')
        all_params.append('_return_http_data_only')
        all_params.append('_preload_content')
        all_params.append('_request_timeout')

        params = locals()
        for key, val in six.iteritems(params['kwargs']):
            if key not in all_params:
                raise TypeError(
                    "Got an unexpected keyword argument '%s'"
                    " to method api_v1_get_token_get" % key
                )
            params[key] = val
        del params['kwargs']

        collection_formats = {}

        path_params = {}

        query_params = []
        if 'symbol' in params:
            query_params.append(('symbol', params['symbol']))  # noqa: E501
        if 'extended' in params:
            query_params.append(('extended', params['extended']))  # noqa: E501

        header_params = {}

        form_params = []
        local_var_files = {}

        body_params = None
        # HTTP header `Accept`
        header_params['Accept'] = self.api_client.select_header_accept(
            ['application/json'])  # noqa: E501

        # Authentication setting
        auth_settings = []  # noqa: E501

        return self.api_client.call_api(
            '/api/v1/GetToken', 'GET',
            path_params,
            query_params,
            header_params,
            body=body_params,
            post_params=form_params,
            files=local_var_files,
            response_type='TokenResult',  # noqa: E501
            auth_settings=auth_settings,
            async_req=params.get('async_req'),
            _return_http_data_only=params.get('_return_http_data_only'),
            _preload_content=params.get('_preload_content', True),
            _request_timeout=params.get('_request_timeout'),
            collection_formats=collection_formats)

    def GetTokens(self, **kwargs):  # noqa: E501
        """api_v1_get_tokens_get  # noqa: E501

        This method makes a synchronous HTTP request by default. To make an
        asynchronous HTTP request, please pass async_req=True
        >>> thread = api.api_v1_get_tokens_get(async_req=True)
        >>> result = thread.get()

        :param async_req bool
        :param bool extended:
        :return: list[TokenResult]
                 If the method is called asynchronously,
                 returns the request thread.
        """
        kwargs['_return_http_data_only'] = True
        if kwargs.get('async_req'):
            return self.api_v1_get_tokens_get_with_http_info(**kwargs)  # noqa: E501
        else:
            (data) = self.api_v1_get_tokens_get_with_http_info(**kwargs)  # noqa: E501
            return data

    def api_v1_get_tokens_get_with_http_info(self, **kwargs):  # noqa: E501
        """api_v1_get_tokens_get  # noqa: E501

        This method makes a synchronous HTTP request by default. To make an
        asynchronous HTTP request, please pass async_req=True
        >>> thread = api.api_v1_get_tokens_get_with_http_info(async_req=True)
        >>> result = thread.get()

        :param async_req bool
        :param bool extended:
        :return: list[TokenResult]
                 If the method is called asynchronously,
                 returns the request thread.
        """

        all_params = ['extended']  # noqa: E501
        all_params.append('async_req')
        all_params.append('_return_http_data_only')
        all_params.append('_preload_content')
        all_params.append('_request_timeout')

        params = locals()
        for key, val in six.iteritems(params['kwargs']):
            if key not in all_params:
                raise TypeError(
                    "Got an unexpected keyword argument '%s'"
                    " to method api_v1_get_tokens_get" % key
                )
            params[key] = val
        del params['kwargs']

        collection_formats = {}

        path_params = {}

        query_params = []
        if 'extended' in params:
            query_params.append(('extended', params['extended']))  # noqa: E501

        header_params = {}

        form_params = []
        local_var_files = {}

        body_params = None
        # HTTP header `Accept`
        header_params['Accept'] = self.api_client.select_header_accept(
            ['application/json'])  # noqa: E501

        # Authentication setting
        auth_settings = []  # noqa: E501

        return self.api_client.call_api(
            '/api/v1/GetTokens', 'GET',
            path_params,
            query_params,
            header_params,
            body=body_params,
            post_params=form_params,
            files=local_var_files,
            response_type='list[TokenResult]',  # noqa: E501
            auth_settings=auth_settings,
            async_req=params.get('async_req'),
            _return_http_data_only=params.get('_return_http_data_only'),
            _preload_content=params.get('_preload_content', True),
            _request_timeout=params.get('_request_timeout'),
            collection_formats=collection_formats)
