# coding: utf-8

"""
    Phantasma API

    No description provided (generated by Swagger Codegen https://github.com/swagger-api/swagger-codegen)  # noqa: E501

    OpenAPI spec version: v1
    
    Generated by: https://github.com/swagger-api/swagger-codegen.git
"""

import pprint
import re  # noqa: F401

import six

class CrowdsaleResult(object):
    """NOTE: This class is auto generated by the swagger code generator program.

    Do not edit the class manually.
    """
    """
    Attributes:
      swagger_types (dict): The key is attribute name
                            and the value is attribute type.
      attribute_map (dict): The key is attribute name
                            and the value is json key in definition.
    """
    swagger_types = {
        'hash': 'str',
        'name': 'str',
        'creator': 'str',
        'flags': 'str',
        'start_date': 'int',
        'end_date': 'int',
        'sell_symbol': 'str',
        'receive_symbol': 'str',
        'price': 'int',
        'global_soft_cap': 'str',
        'global_hard_cap': 'str',
        'user_soft_cap': 'str',
        'user_hard_cap': 'str'
    }

    attribute_map = {
        'hash': 'hash',
        'name': 'name',
        'creator': 'creator',
        'flags': 'flags',
        'start_date': 'startDate',
        'end_date': 'endDate',
        'sell_symbol': 'sellSymbol',
        'receive_symbol': 'receiveSymbol',
        'price': 'price',
        'global_soft_cap': 'globalSoftCap',
        'global_hard_cap': 'globalHardCap',
        'user_soft_cap': 'userSoftCap',
        'user_hard_cap': 'userHardCap'
    }

    def __init__(self, hash=None, name=None, creator=None, flags=None, start_date=None, end_date=None, sell_symbol=None, receive_symbol=None, price=None, global_soft_cap=None, global_hard_cap=None, user_soft_cap=None, user_hard_cap=None):  # noqa: E501
        """CrowdsaleResult - a model defined in Swagger"""  # noqa: E501
        self._hash = None
        self._name = None
        self._creator = None
        self._flags = None
        self._start_date = None
        self._end_date = None
        self._sell_symbol = None
        self._receive_symbol = None
        self._price = None
        self._global_soft_cap = None
        self._global_hard_cap = None
        self._user_soft_cap = None
        self._user_hard_cap = None
        self.discriminator = None
        if hash is not None:
            self.hash = hash
        if name is not None:
            self.name = name
        if creator is not None:
            self.creator = creator
        if flags is not None:
            self.flags = flags
        if start_date is not None:
            self.start_date = start_date
        if end_date is not None:
            self.end_date = end_date
        if sell_symbol is not None:
            self.sell_symbol = sell_symbol
        if receive_symbol is not None:
            self.receive_symbol = receive_symbol
        if price is not None:
            self.price = price
        if global_soft_cap is not None:
            self.global_soft_cap = global_soft_cap
        if global_hard_cap is not None:
            self.global_hard_cap = global_hard_cap
        if user_soft_cap is not None:
            self.user_soft_cap = user_soft_cap
        if user_hard_cap is not None:
            self.user_hard_cap = user_hard_cap

    @property
    def hash(self):
        """Gets the hash of this CrowdsaleResult.  # noqa: E501


        :return: The hash of this CrowdsaleResult.  # noqa: E501
        :rtype: str
        """
        return self._hash

    @hash.setter
    def hash(self, hash):
        """Sets the hash of this CrowdsaleResult.


        :param hash: The hash of this CrowdsaleResult.  # noqa: E501
        :type: str
        """

        self._hash = hash

    @property
    def name(self):
        """Gets the name of this CrowdsaleResult.  # noqa: E501


        :return: The name of this CrowdsaleResult.  # noqa: E501
        :rtype: str
        """
        return self._name

    @name.setter
    def name(self, name):
        """Sets the name of this CrowdsaleResult.


        :param name: The name of this CrowdsaleResult.  # noqa: E501
        :type: str
        """

        self._name = name

    @property
    def creator(self):
        """Gets the creator of this CrowdsaleResult.  # noqa: E501


        :return: The creator of this CrowdsaleResult.  # noqa: E501
        :rtype: str
        """
        return self._creator

    @creator.setter
    def creator(self, creator):
        """Sets the creator of this CrowdsaleResult.


        :param creator: The creator of this CrowdsaleResult.  # noqa: E501
        :type: str
        """

        self._creator = creator

    @property
    def flags(self):
        """Gets the flags of this CrowdsaleResult.  # noqa: E501


        :return: The flags of this CrowdsaleResult.  # noqa: E501
        :rtype: str
        """
        return self._flags

    @flags.setter
    def flags(self, flags):
        """Sets the flags of this CrowdsaleResult.


        :param flags: The flags of this CrowdsaleResult.  # noqa: E501
        :type: str
        """

        self._flags = flags

    @property
    def start_date(self):
        """Gets the start_date of this CrowdsaleResult.  # noqa: E501


        :return: The start_date of this CrowdsaleResult.  # noqa: E501
        :rtype: int
        """
        return self._start_date

    @start_date.setter
    def start_date(self, start_date):
        """Sets the start_date of this CrowdsaleResult.


        :param start_date: The start_date of this CrowdsaleResult.  # noqa: E501
        :type: int
        """

        self._start_date = start_date

    @property
    def end_date(self):
        """Gets the end_date of this CrowdsaleResult.  # noqa: E501


        :return: The end_date of this CrowdsaleResult.  # noqa: E501
        :rtype: int
        """
        return self._end_date

    @end_date.setter
    def end_date(self, end_date):
        """Sets the end_date of this CrowdsaleResult.


        :param end_date: The end_date of this CrowdsaleResult.  # noqa: E501
        :type: int
        """

        self._end_date = end_date

    @property
    def sell_symbol(self):
        """Gets the sell_symbol of this CrowdsaleResult.  # noqa: E501


        :return: The sell_symbol of this CrowdsaleResult.  # noqa: E501
        :rtype: str
        """
        return self._sell_symbol

    @sell_symbol.setter
    def sell_symbol(self, sell_symbol):
        """Sets the sell_symbol of this CrowdsaleResult.


        :param sell_symbol: The sell_symbol of this CrowdsaleResult.  # noqa: E501
        :type: str
        """

        self._sell_symbol = sell_symbol

    @property
    def receive_symbol(self):
        """Gets the receive_symbol of this CrowdsaleResult.  # noqa: E501


        :return: The receive_symbol of this CrowdsaleResult.  # noqa: E501
        :rtype: str
        """
        return self._receive_symbol

    @receive_symbol.setter
    def receive_symbol(self, receive_symbol):
        """Sets the receive_symbol of this CrowdsaleResult.


        :param receive_symbol: The receive_symbol of this CrowdsaleResult.  # noqa: E501
        :type: str
        """

        self._receive_symbol = receive_symbol

    @property
    def price(self):
        """Gets the price of this CrowdsaleResult.  # noqa: E501


        :return: The price of this CrowdsaleResult.  # noqa: E501
        :rtype: int
        """
        return self._price

    @price.setter
    def price(self, price):
        """Sets the price of this CrowdsaleResult.


        :param price: The price of this CrowdsaleResult.  # noqa: E501
        :type: int
        """

        self._price = price

    @property
    def global_soft_cap(self):
        """Gets the global_soft_cap of this CrowdsaleResult.  # noqa: E501


        :return: The global_soft_cap of this CrowdsaleResult.  # noqa: E501
        :rtype: str
        """
        return self._global_soft_cap

    @global_soft_cap.setter
    def global_soft_cap(self, global_soft_cap):
        """Sets the global_soft_cap of this CrowdsaleResult.


        :param global_soft_cap: The global_soft_cap of this CrowdsaleResult.  # noqa: E501
        :type: str
        """

        self._global_soft_cap = global_soft_cap

    @property
    def global_hard_cap(self):
        """Gets the global_hard_cap of this CrowdsaleResult.  # noqa: E501


        :return: The global_hard_cap of this CrowdsaleResult.  # noqa: E501
        :rtype: str
        """
        return self._global_hard_cap

    @global_hard_cap.setter
    def global_hard_cap(self, global_hard_cap):
        """Sets the global_hard_cap of this CrowdsaleResult.


        :param global_hard_cap: The global_hard_cap of this CrowdsaleResult.  # noqa: E501
        :type: str
        """

        self._global_hard_cap = global_hard_cap

    @property
    def user_soft_cap(self):
        """Gets the user_soft_cap of this CrowdsaleResult.  # noqa: E501


        :return: The user_soft_cap of this CrowdsaleResult.  # noqa: E501
        :rtype: str
        """
        return self._user_soft_cap

    @user_soft_cap.setter
    def user_soft_cap(self, user_soft_cap):
        """Sets the user_soft_cap of this CrowdsaleResult.


        :param user_soft_cap: The user_soft_cap of this CrowdsaleResult.  # noqa: E501
        :type: str
        """

        self._user_soft_cap = user_soft_cap

    @property
    def user_hard_cap(self):
        """Gets the user_hard_cap of this CrowdsaleResult.  # noqa: E501


        :return: The user_hard_cap of this CrowdsaleResult.  # noqa: E501
        :rtype: str
        """
        return self._user_hard_cap

    @user_hard_cap.setter
    def user_hard_cap(self, user_hard_cap):
        """Sets the user_hard_cap of this CrowdsaleResult.


        :param user_hard_cap: The user_hard_cap of this CrowdsaleResult.  # noqa: E501
        :type: str
        """

        self._user_hard_cap = user_hard_cap

    def to_dict(self):
        """Returns the model properties as a dict"""
        result = {}

        for attr, _ in six.iteritems(self.swagger_types):
            value = getattr(self, attr)
            if isinstance(value, list):
                result[attr] = list(map(
                    lambda x: x.to_dict() if hasattr(x, "to_dict") else x,
                    value
                ))
            elif hasattr(value, "to_dict"):
                result[attr] = value.to_dict()
            elif isinstance(value, dict):
                result[attr] = dict(map(
                    lambda item: (item[0], item[1].to_dict())
                    if hasattr(item[1], "to_dict") else item,
                    value.items()
                ))
            else:
                result[attr] = value
        if issubclass(CrowdsaleResult, dict):
            for key, value in self.items():
                result[key] = value

        return result

    def to_str(self):
        """Returns the string representation of the model"""
        return pprint.pformat(self.to_dict())

    def __repr__(self):
        """For `print` and `pprint`"""
        return self.to_str()

    def __eq__(self, other):
        """Returns true if both objects are equal"""
        if not isinstance(other, CrowdsaleResult):
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        """Returns true if both objects are not equal"""
        return not self == other
