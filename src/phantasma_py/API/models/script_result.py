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

class ScriptResult(object):
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
        'events': 'list[EventResult]',
        'result': 'str',
        'error': 'str',
        'results': 'list[str]',
        'oracles': 'list[OracleResult]'
    }

    attribute_map = {
        'events': 'events',
        'result': 'result',
        'error': 'error',
        'results': 'results',
        'oracles': 'oracles'
    }

    def __init__(self, events=None, result=None, error=None, results=None, oracles=None):  # noqa: E501
        """ScriptResult - a model defined in Swagger"""  # noqa: E501
        self._events = None
        self._result = None
        self._error = None
        self._results = None
        self._oracles = None
        self.discriminator = None
        if events is not None:
            self.events = events
        if result is not None:
            self.result = result
        if error is not None:
            self.error = error
        if results is not None:
            self.results = results
        if oracles is not None:
            self.oracles = oracles

    @property
    def events(self):
        """Gets the events of this ScriptResult.  # noqa: E501


        :return: The events of this ScriptResult.  # noqa: E501
        :rtype: list[EventResult]
        """
        return self._events

    @events.setter
    def events(self, events):
        """Sets the events of this ScriptResult.


        :param events: The events of this ScriptResult.  # noqa: E501
        :type: list[EventResult]
        """

        self._events = events

    @property
    def result(self):
        """Gets the result of this ScriptResult.  # noqa: E501


        :return: The result of this ScriptResult.  # noqa: E501
        :rtype: str
        """
        return self._result

    @result.setter
    def result(self, result):
        """Sets the result of this ScriptResult.


        :param result: The result of this ScriptResult.  # noqa: E501
        :type: str
        """

        self._result = result

    @property
    def error(self):
        """Gets the error of this ScriptResult.  # noqa: E501


        :return: The error of this ScriptResult.  # noqa: E501
        :rtype: str
        """
        return self._error

    @error.setter
    def error(self, error):
        """Sets the error of this ScriptResult.


        :param error: The error of this ScriptResult.  # noqa: E501
        :type: str
        """

        self._error = error

    @property
    def results(self):
        """Gets the results of this ScriptResult.  # noqa: E501


        :return: The results of this ScriptResult.  # noqa: E501
        :rtype: list[str]
        """
        return self._results

    @results.setter
    def results(self, results):
        """Sets the results of this ScriptResult.


        :param results: The results of this ScriptResult.  # noqa: E501
        :type: list[str]
        """

        self._results = results

    @property
    def oracles(self):
        """Gets the oracles of this ScriptResult.  # noqa: E501


        :return: The oracles of this ScriptResult.  # noqa: E501
        :rtype: list[OracleResult]
        """
        return self._oracles

    @oracles.setter
    def oracles(self, oracles):
        """Sets the oracles of this ScriptResult.


        :param oracles: The oracles of this ScriptResult.  # noqa: E501
        :type: list[OracleResult]
        """

        self._oracles = oracles

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
        if issubclass(ScriptResult, dict):
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
        if not isinstance(other, ScriptResult):
            return False

        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        """Returns true if both objects are not equal"""
        return not self == other
