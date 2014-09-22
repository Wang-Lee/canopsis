#!/usr/bin/env python
# --------------------------------
# Copyright (c) 2014 "Capensis" [http://www.capensis.com]
#
# This file is part of Canopsis.
#
# Canopsis is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Canopsis is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Canopsis.  If not, see <http://www.gnu.org/licenses/>.
# ---------------------------------

from inspect import getargspec

from canopsis.common.utils import ensure_iterable

from json import loads

from bottle import request

from functools import wraps


def response(data):
    """
    Construct a REST response from input data.

    :param data: data to convert into a REST response.
    :param kwargs: service function parameters.
    """

    # calculate result_data and total related to data type
    if isinstance(data, tuple):
        result_data = ensure_iterable(data[0])
        total = data[1]

    else:
        result_data = None if data is None else ensure_iterable(data)
        total = 0 if result_data is None else len(result_data)

    result = {
        'total': total,
        'data': result_data,
        'success': True
    }

    return result


def route_name(operation_name, *parameters):
    """
    Get the right route related to input operation_name
    """

    result = '/%s' % operation_name.replace('_', '-')

    for parameter in parameters:
        result = '%s/:%s' % (result, parameter)

    return result


class route(object):
    """
    Decorator which add ws routes to a callable object.

    Example::

        @route(get, payload='c')
        def entities(a, b, c=None, d=None):
            ...

        Fill ``a``, ``b``, ``d`` parameters in entities function and provide
        the three urls:

            - '/entities/a/:b'
            - '/entities/a/:b'
            - '/entities/a/:b/:d'

        And manage ``c`` such as a request body parameter.
    """

    def __init__(self, op, name=None, payload=None, response=response):
        """
        :param op: ws operation for routing a function
        :param str name: ws name
        :param payload: body parameter names (won't be generated in routes)
        :type payload: str or list of str
        :param function response: response to apply on decorated function
            result
        """

        super(route, self).__init__()

        self.op = op
        self.name = name
        self.payload = ensure_iterable(payload)
        self.response = response

    def __call__(self, function):

        # generate an interceptor
        @wraps(function)
        def interceptor(*args, **kwargs):

            # add body parameters in kwargs
            for body_param in self.payload:
                # TODO: remove reference from bottle
                param = request.params.get(body_param)
                # if param exists, add it into kwargs in deserializing it
                if param is not None:
                    try:
                        kwargs[body_param] = loads(param)
                    except ValueError:  # error while deserializing
                        # get the str value and cross fingers ...
                        kwargs[body_param] = param

            result_function = function(*args, **kwargs)

            result = self.response(result_function)

            return result

        # add routes
        argspec = getargspec(function)
        args, defaults = argspec.args, argspec.defaults
        result = self.apply_route_on_function(interceptor, args, defaults)

        return result

    def apply_route_on_function(self, function, args=None, defaults=None):
        """
        Automatically apply routes parameterized by input function and return
        the intercepted function.

        :param callable function: function from where generate ws redirection
        :param list args: list of function arg names
        :param list defaults: list of function arg default values
        """

        # get the right function name
        function_name = function.__name__ if self.name is None else self.name

        if args is None:
            argspec = getargspec(function)
            args, defaults = argspec.args, argspec.defaults

        # get defaults len for dynamic programming concerns
        len_defaults = 0 if defaults is None else len(defaults)

        # list of optional header parameters
        optional_header_params = []

        # identify optional parameters without body parameters
        for i in range(len_defaults):
            if args[- (i + 1)] not in self.payload:
                optional_header_params.append(args[- (i + 1)])

        optional_header_params.reverse()

        # get required header parameters without body parameters
        required_header_params = args[:len(args) - len_defaults]
        required_header_params = [param for param in required_header_params
            if param not in self.payload]

        # add routes with optional parameters
        for i in range(len(optional_header_params) + 1):
            header_params = required_header_params + optional_header_params[:i]
            route = route_name(function_name, *header_params)
            function = self.op(route)(function)

        return function
