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

class ResponseQuery(object):
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
        'code': 'int',
        'log': 'str',
        'info': 'str',
        'index': 'str',
        'key': 'str',
        'value': 'str',
        'proof': 'str',
        'height': 'str',
        'codespace': 'str'
    }

    attribute_map = {
        'code': 'code',
        'log': 'log',
        'info': 'info',
        'index': 'index',
        'key': 'key',
        'value': 'value',
        'proof': 'proof',
        'height': 'height',
        'codespace': 'codespace'
    }

    def __init__(self, code=None, log=None, info=None, index=None, key=None, value=None, proof=None, height=None, codespace=None):  # noqa: E501
        """ResponseQuery - a model defined in Swagger"""  # noqa: E501
        self._code = None
        self._log = None
        self._info = None
        self._index = None
        self._key = None
        self._value = None
        self._proof = None
        self._height = None
        self._codespace = None
        self.discriminator = None
        if code is not None:
            self.code = code
        if log is not None:
            self.log = log
        if info is not None:
            self.info = info
        if index is not None:
            self.index = index
        if key is not None:
            self.key = key
        if value is not None:
            self.value = value
        if proof is not None:
            self.proof = proof
        if height is not None:
            self.height = height
        if codespace is not None:
            self.codespace = codespace

    @property
    def code(self):
        """Gets the code of this ResponseQuery.  # noqa: E501


        :return: The code of this ResponseQuery.  # noqa: E501
        :rtype: int
        """
        return self._code

    @code.setter
    def code(self, code):
        """Sets the code of this ResponseQuery.


        :param code: The code of this ResponseQuery.  # noqa: E501
        :type: int
        """

        self._code = code

    @property
    def log(self):
        """Gets the log of this ResponseQuery.  # noqa: E501


        :return: The log of this ResponseQuery.  # noqa: E501
        :rtype: str
        """
        return self._log

    @log.setter
    def log(self, log):
        """Sets the log of this ResponseQuery.


        :param log: The log of this ResponseQuery.  # noqa: E501
        :type: str
        """

        self._log = log

    @property
    def info(self):
        """Gets the info of this ResponseQuery.  # noqa: E501


        :return: The info of this ResponseQuery.  # noqa: E501
        :rtype: str
        """
        return self._info

    @info.setter
    def info(self, info):
        """Sets the info of this ResponseQuery.


        :param info: The info of this ResponseQuery.  # noqa: E501
        :type: str
        """

        self._info = info

    @property
    def index(self):
        """Gets the index of this ResponseQuery.  # noqa: E501


        :return: The index of this ResponseQuery.  # noqa: E501
        :rtype: str
        """
        return self._index

    @index.setter
    def index(self, index):
        """Sets the index of this ResponseQuery.


        :param index: The index of this ResponseQuery.  # noqa: E501
        :type: str
        """

        self._index = index

    @property
    def key(self):
        """Gets the key of this ResponseQuery.  # noqa: E501


        :return: The key of this ResponseQuery.  # noqa: E501
        :rtype: str
        """
        return self._key

    @key.setter
    def key(self, key):
        """Sets the key of this ResponseQuery.


        :param key: The key of this ResponseQuery.  # noqa: E501
        :type: str
        """

        self._key = key

    @property
    def value(self):
        """Gets the value of this ResponseQuery.  # noqa: E501


        :return: The value of this ResponseQuery.  # noqa: E501
        :rtype: str
        """
        return self._value

    @value.setter
    def value(self, value):
        """Sets the value of this ResponseQuery.


        :param value: The value of this ResponseQuery.  # noqa: E501
        :type: str
        """

        self._value = value

    @property
    def proof(self):
        """Gets the proof of this ResponseQuery.  # noqa: E501


        :return: The proof of this ResponseQuery.  # noqa: E501
        :rtype: str
        """
        return self._proof

    @proof.setter
    def proof(self, proof):
        """Sets the proof of this ResponseQuery.


        :param proof: The proof of this ResponseQuery.  # noqa: E501
        :type: str
        """

        self._proof = proof

    @property
    def height(self):
        """Gets the height of this ResponseQuery.  # noqa: E501


        :return: The height of this ResponseQuery.  # noqa: E501
        :rtype: str
        """
        return self._height

    @height.setter
    def height(self, height):
        """Sets the height of this ResponseQuery.


        :param height: The height of this ResponseQuery.  # noqa: E501
        :type: str
        """

        self._height = height

    @property
    def codespace(self):
        """Gets the codespace of this ResponseQuery.  # noqa: E501


        :return: The codespace of this ResponseQuery.  # noqa: E501
        :rtype: str
        """
        return self._codespace

    @codespace.setter
    def codespace(self, codespace):
        """Sets the codespace of this ResponseQuery.


        :param codespace: The codespace of this ResponseQuery.  # noqa: E501
        :type: str
        """

        self._codespace = codespace

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
        if issubclass(ResponseQuery, dict):
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
        if not isinstance(other, ResponseQuery):
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        """Returns true if both objects are not equal"""
        return not self == other