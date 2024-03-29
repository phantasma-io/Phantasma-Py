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

class ResultStatusSyncInfo(object):
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
        'latest_block_hash': 'str',
        'latest_app_hash': 'str',
        'latest_block_height': 'str',
        'latest_block_time': 'str',
        'catching_up': 'bool'
    }

    attribute_map = {
        'latest_block_hash': 'latestBlockHash',
        'latest_app_hash': 'latestAppHash',
        'latest_block_height': 'latestBlockHeight',
        'latest_block_time': 'latestBlockTime',
        'catching_up': 'catchingUp'
    }

    def __init__(self, latest_block_hash=None, latest_app_hash=None, latest_block_height=None, latest_block_time=None, catching_up=None):  # noqa: E501
        """ResultStatusSyncInfo - a model defined in Swagger"""  # noqa: E501
        self._latest_block_hash = None
        self._latest_app_hash = None
        self._latest_block_height = None
        self._latest_block_time = None
        self._catching_up = None
        self.discriminator = None
        if latest_block_hash is not None:
            self.latest_block_hash = latest_block_hash
        if latest_app_hash is not None:
            self.latest_app_hash = latest_app_hash
        if latest_block_height is not None:
            self.latest_block_height = latest_block_height
        if latest_block_time is not None:
            self.latest_block_time = latest_block_time
        if catching_up is not None:
            self.catching_up = catching_up

    @property
    def latest_block_hash(self):
        """Gets the latest_block_hash of this ResultStatusSyncInfo.  # noqa: E501


        :return: The latest_block_hash of this ResultStatusSyncInfo.  # noqa: E501
        :rtype: str
        """
        return self._latest_block_hash

    @latest_block_hash.setter
    def latest_block_hash(self, latest_block_hash):
        """Sets the latest_block_hash of this ResultStatusSyncInfo.


        :param latest_block_hash: The latest_block_hash of this ResultStatusSyncInfo.  # noqa: E501
        :type: str
        """

        self._latest_block_hash = latest_block_hash

    @property
    def latest_app_hash(self):
        """Gets the latest_app_hash of this ResultStatusSyncInfo.  # noqa: E501


        :return: The latest_app_hash of this ResultStatusSyncInfo.  # noqa: E501
        :rtype: str
        """
        return self._latest_app_hash

    @latest_app_hash.setter
    def latest_app_hash(self, latest_app_hash):
        """Sets the latest_app_hash of this ResultStatusSyncInfo.


        :param latest_app_hash: The latest_app_hash of this ResultStatusSyncInfo.  # noqa: E501
        :type: str
        """

        self._latest_app_hash = latest_app_hash

    @property
    def latest_block_height(self):
        """Gets the latest_block_height of this ResultStatusSyncInfo.  # noqa: E501


        :return: The latest_block_height of this ResultStatusSyncInfo.  # noqa: E501
        :rtype: str
        """
        return self._latest_block_height

    @latest_block_height.setter
    def latest_block_height(self, latest_block_height):
        """Sets the latest_block_height of this ResultStatusSyncInfo.


        :param latest_block_height: The latest_block_height of this ResultStatusSyncInfo.  # noqa: E501
        :type: str
        """

        self._latest_block_height = latest_block_height

    @property
    def latest_block_time(self):
        """Gets the latest_block_time of this ResultStatusSyncInfo.  # noqa: E501


        :return: The latest_block_time of this ResultStatusSyncInfo.  # noqa: E501
        :rtype: str
        """
        return self._latest_block_time

    @latest_block_time.setter
    def latest_block_time(self, latest_block_time):
        """Sets the latest_block_time of this ResultStatusSyncInfo.


        :param latest_block_time: The latest_block_time of this ResultStatusSyncInfo.  # noqa: E501
        :type: str
        """

        self._latest_block_time = latest_block_time

    @property
    def catching_up(self):
        """Gets the catching_up of this ResultStatusSyncInfo.  # noqa: E501


        :return: The catching_up of this ResultStatusSyncInfo.  # noqa: E501
        :rtype: bool
        """
        return self._catching_up

    @catching_up.setter
    def catching_up(self, catching_up):
        """Sets the catching_up of this ResultStatusSyncInfo.


        :param catching_up: The catching_up of this ResultStatusSyncInfo.  # noqa: E501
        :type: bool
        """

        self._catching_up = catching_up

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
        if issubclass(ResultStatusSyncInfo, dict):
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
        if not isinstance(other, ResultStatusSyncInfo):
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        """Returns true if both objects are not equal"""
        return not self == other
