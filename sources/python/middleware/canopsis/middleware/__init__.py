# -*- coding: utf-8 -*-
#--------------------------------
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

__version__ = "0.1"

from urlparse import urlparse

from canopsis.configuration import Configurable, Parameter
from canopsis.configuration.configurable import MetaConfigurable

# char separator between a protocol and the associated data_type
PROTOCOL_SEPARATOR = '-'


class MetaMiddleware(MetaConfigurable):
    """
    Middleware meta class which register all middleware in a global
    set of middlewares.
    """

    def __init__(self, name, bases, attrs):

        super(MetaMiddleware, self).__init__(name, bases, attrs)

        # if the class claims to be registered
        if self.__register__:
            self.register_middleware()


class Middleware(Configurable):
    """
    Abstract class which aims to manage middleware.

    A middleware is something which connects itself to a foreign resource
        such as a database, a mom broker, etc.
    Optionnaly, it is related to a data_type:
    - pubsub dedicated to events, status, etc. ?
    - database dedicated to relational data, no-sql data, timed data, etc. ?
    """

    __metaclass__ = MetaMiddleware

    __register__ = False  # if True, automatically register this class
    __protocol__ = 'canopsis'  # protocol registration name if __register__
    __datatype__ = None  # data_type registration name if __register__

    # private class attribute which manages middlewares classes per data_type
    __MIDDLEWARES__ = {}

    CATEGORY = 'MIDDLEWARE'

    URI = 'uri'
    PROTOCOL = 'protocol'
    DATA_TYPE = 'data_type'
    DATA_SCOPE = 'data_scope'
    HOST = 'host'
    PORT = 'port'
    PATH = 'path'
    AUTO_CONNECT = 'auto_connect'
    SAFE = 'safe'
    CONN_TIMEOUT = 'conn_timeout'
    INPUT_TIMEOUT = 'in_timeout'
    OUTPUT_TIMEOUT = 'out_timeout'
    SSL = 'ssl'
    SSL_KEY = 'ssl_key'
    SSL_CERT = 'ssl_cert'
    USER = 'user'
    PWD = 'pwd'

    CONF_RESOURCE = 'middleware/middleware.conf'

    class Error(Exception):
        """
        Errors raised by the Middleware class.
        """

        pass

    def __init__(
        self,
        uri=None, data_type=None, data_scope='canopsis',
        protocol=None, host='localhost', port=0, path='canopsis',
        auto_connect=True, safe=False,
        conn_timeout=20000, in_timeout=100, out_timeout=2000,
        ssl=False, ssl_key=None, ssl_cert=None, user=None, pwd=None,
        *args, **kwargs
    ):
        """
        :param uri: middleware uri to connect to. If other uri parameters are
            avoided (protocol, data_type, data_scope, host, port, path, user,
            pwd).
        :param protocol: protocol managed if uri is not given.
        :param data_type: data type (typed, timed, event, etc.) managed if not
            uri.
        :param data_data_scope: data scope (perfdata, entities, etc.).
        :param host: host name.
        :param port: port.
        :param path: path name (end of the uri, could contains information
            such as db, virtual_host, etc.).
        :param auto_connect: auto connect when (re-)configured.
        :param safe: ensure output data.
        :param conn_timeout: connection timeout in milliseconds.
        :param in_timeout: input timeout in milliseconds.
        :param out_timeout: output timeout in milliseconds.
        :param ssl: ssl mode
        :param ssl_key: ssl keys file.
        :param ssl_cert: ssl certification file.
        :param user: user
        :param pwd: password

        :type uri: str
        :type protocol: str
        :type data_type: str
        :type data_scope: str
        :type host: str
        :type port: int
        :type path: str
        :type auto_connect: bool
        :type backend: str
        :type safe: bool
        :type conn_timeout: int
        :type in_timeout: int
        :type out_timeout: int
        :type ssl: bool
        :type ssl_key: str
        :type ssl_cert: str
        :type user: str
        :type pwd: str
        """

        super(Middleware, self).__init__(*args, **kwargs)

        # initialize instance properties with default values
        self._uri = uri
        self._protocol = protocol
        self._data_type = data_type
        self._data_scope = data_scope
        self._host = host
        self._port = port
        self._path = path
        self._auto_connect = auto_connect
        self._safe = safe
        self._conn_timeout = conn_timeout
        self._in_timeout = in_timeout
        self._out_timeout = out_timeout
        self._ssl = ssl
        self._ssl_key = ssl_key
        self._ssl_cert = ssl_cert
        self._user = user
        self._pwd = pwd

    @property
    def uri(self):
        result = self._uri

        # if self._uri is not resolved, generate it related to other parameters
        if not self._uri:

            result = self.host
            if self.user:
                if self.pwd:
                    result = '%s:%s@%s' % (self.user, self.pwd, result)
                else:
                    result = '%s@%s' % (self.user, result)

            if self.path:
                result = '%s/%s' % (result, self.path)

            if self.protocol:
                result = '%s://%s' % (self.protocol, result)

        return result

    @uri.setter
    def uri(self, value):
        self._uri = value
        self.reconnect()

    @property
    def protocol(self):
        return self._protocol

    @protocol.setter
    def protocol(self, value):
        self._protocol = value
        self.reconnect()

    @property
    def data_type(self):
        return self._data_type

    @data_type.setter
    def data_type(self, value):
        self._data_type = value

    @property
    def data_scope(self):
        return self._data_scope

    @data_scope.setter
    def data_scope(self, value):
        self._data_scope = value
        self.reconnect()

    @property
    def host(self):
        return self._host

    @host.setter
    def host(self, value):
        self._host = value
        self.reconnect()

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, value):
        self._port = value
        self.reconnect()

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, value):
        self._path = value
        self.reconnect()

    @property
    def auto_connect(self):
        return self._auto_connect

    @auto_connect.setter
    def auto_connect(self, value):
        self._auto_connect = value
        self.reconnect()

    @property
    def safe(self):
        return self._safe

    @safe.setter
    def safe(self, value):
        self._safe = value
        self.reconnect()

    @property
    def conn_timeout(self):
        return self._wtimeout

    @conn_timeout.setter
    def conn_timeout(self, value):
        self._conn_timeout = value
        self.reconnect()

    @property
    def in_timeout(self):
        return self._in_timeout

    @in_timeout.setter
    def in_timeout(self, value):
        self._in_timeout = value
        self.reconnect()

    @property
    def out_timeout(self):
        return self._out_timeout

    @out_timeout.setter
    def out_timeout(self, value):
        self._out_timeout = value
        self.reconnect()

    @property
    def ssl(self):
        return self._ssl

    @ssl.setter
    def ssl(self, value):
        self._ssl = value
        self.reconnect()

    @property
    def ssl_key(self):
        return self._ssl_key

    @ssl_key.setter
    def ssl_key(self, value):
        self._ssl_key = value
        self.reconnect()

    @property
    def ssl_cert(self):
        return self._ssl_cert

    @ssl_cert.setter
    def ssl_cert(self, value):
        self._ssl_cert = value
        self.reconnect()

    @property
    def user(self):
        return self._user

    @user.setter
    def user(self, value):
        self._user = value
        self.reconnect()

    @property
    def pwd(self):
        return self._pwd

    @pwd.setter
    def pwd(self, value):
        self._pwd = value
        self.reconnect()

    def connect(self, *args, **kwargs):
        """
        Connect this database.

        .. seealso:: disconnect(self), connected(self), reconnect(self)
        """

        raise NotImplementedError()

    def disconnect(self, *args, **kwargs):
        """
        Disconnect this database.

        .. seealso:: connect(self), connected(self), reconnect(self)
        """

        raise NotImplementedError()

    def connected(self, *args, **kwargs):
        """
        :returns: True if this is connected.
        """

        return False

    def reconnect(self, *args, **kwargs):
        """
        Try to reconnect and returns connection result

        :return: True if connected
        :rtype: bool
        """

        result = False

        try:
            self.disconnect()
        except Exception:
            pass
        else:
            try:
                result = self.connect()
            except Exception:
                pass

        return result

    def _configure(self, unified_conf, *args, **kwargs):

        super(Middleware, self)._configure(
            unified_conf=unified_conf, *args, **kwargs)

        reconnect = False

        path_properties = (parameter.name for parameter
            in self.conf[Middleware.CATEGORY])

        for path_property in path_properties:
            updated_property = self._update_property(
                unified_conf=unified_conf,
                param_name=path_property,
                public=False)
            if updated_property:
                reconnect = True

        if reconnect and self.auto_connect:
            self.reconnect()

    def _get_conf_files(self, *args, **kwargs):

        result = super(Middleware, self)._get_conf_files(*args, **kwargs)

        result.append(Middleware.CONF_RESOURCE)

        return result

    def _conf(self, *args, **kwargs):

        result = super(Middleware, self)._conf(*args, **kwargs)

        result.add_unified_category(
            name=Middleware.CATEGORY,
            new_content=(
                Parameter(Middleware.URI, self.uri),
                Parameter(Middleware.PROTOCOL, self.protocol),
                Parameter(Middleware.DATA_TYPE, self.data_type),
                Parameter(Middleware.DATA_SCOPE, self.data_scope),
                Parameter(Middleware.HOST, self.host),
                Parameter(Middleware.PORT, self.port, int),
                Parameter(Middleware.VIRTUAL_HOST, self.path),
                Parameter(
                    Middleware.AUTO_CONNECT,
                    self.auto_connect, Parameter.bool),
                Parameter(Middleware.SAFE, self.safe, Parameter.bool),
                Parameter(Middleware.CONN_TIMEOUT, self.conn_timeout, int),
                Parameter(Middleware.IN_TIMEOUT, self.in_timeout, int),
                Parameter(Middleware.OUT_TIMEOUT, self.out_timeout, int),
                Parameter(Middleware.SSL, self.ssl, Parameter.bool),
                Parameter(Middleware.SSL_KEY, self.ssl_key),
                Parameter(Middleware.SSL_CERT, self.ssl_cert),
                Parameter(Middleware.USER, self.user),
                Parameter(Middleware.PWD, self.pwd)))

        return result

    @classmethod
    def register_middleware(cls, protocol=None, data_type=None):
        """
        Register a middleware class with input protocol name and data_type.
        """

        if protocol is None:
            protocol = cls.__protocol__

        if data_type is None:
            data_type = cls.__datatype__

        data_types = Middleware.__MIDDLEWARES__.setdefault(protocol, {})

        data_types[data_type] = cls

    @staticmethod
    def resolve_middleware(uri, *args, **kwargs):
        """
        Instantiate the right middleware related to input uri.

        :param uri: the uri may contains a protocol of type 'protocol' or
            'protocol-data_type'.
        :type uri: str

        :param args: list of args given to the middleware to instantiate.
        :param kwargs: kwargs given to the middleware to instantiate.

        :return: Middleware type
        :rtype: type

        :raise: Middleware.Error if the uri is not reliable to a registered
            middleware.
        """

        result = None

        parsed_uri = urlparse(uri)

        protocol = parsed_uri.scheme

        if not protocol:
            raise Middleware.Error('Not protocol given in %s' % uri)

        else:
            if PROTOCOL_SEPARATOR in protocol:
                splitted_protocol = protocol.split(PROTOCOL_SEPARATOR)

                protocol = splitted_protocol[0]
                data_type = splitted_protocol[1]

                result = Middleware.__MIDDLEWARES__[protocol][data_type]
            else:
                result = Middleware.__MIDDLEWARES__[protocol][None]

        return result