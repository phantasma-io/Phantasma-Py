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

class NodeInfoOther(object):
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
        'tx_index': 'str',
        'rpc_address': 'str'
    }

    attribute_map = {
        'tx_index': 'txIndex',
        'rpc_address': 'rpcAddress'
    }

    def __init__(self, tx_index=None, rpc_address=None):  # noqa: E501
        """NodeInfoOther - a model defined in Swagger"""  # noqa: E501
        self._tx_index = None
        self._rpc_address = None
        self.discriminator = None
        if tx_index is not None:
            self.tx_index = tx_index
        if rpc_address is not None:
            self.rpc_address = rpc_address

    @property
    def tx_index(self):
        """Gets the tx_index of this NodeInfoOther.  # noqa: E501


        :return: The tx_index of this NodeInfoOther.  # noqa: E501
        :rtype: str
        """
        return self._tx_index

    @tx_index.setter
    def tx_index(self, tx_index):
        """Sets the tx_index of this NodeInfoOther.


        :param tx_index: The tx_index of this NodeInfoOther.  # noqa: E501
        :type: str
        """

        self._tx_index = tx_index

    @property
    def rpc_address(self):
        """Gets the rpc_address of this NodeInfoOther.  # noqa: E501


        :return: The rpc_address of this NodeInfoOther.  # noqa: E501
        :rtype: str
        """
        return self._rpc_address

    @rpc_address.setter
    def rpc_address(self, rpc_address):
        """Sets the rpc_address of this NodeInfoOther.


        :param rpc_address: The rpc_address of this NodeInfoOther.  # noqa: E501
        :type: str
        """

        self._rpc_address = rpc_address

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
        if issubclass(NodeInfoOther, dict):
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
        if not isinstance(other, NodeInfoOther):
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        """Returns true if both objects are not equal"""
        return not self == other
