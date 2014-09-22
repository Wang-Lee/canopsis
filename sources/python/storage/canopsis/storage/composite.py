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

from uuid import uuid4 as uuid

from canopsis.configuration.parameters import Parameter
from canopsis.common.utils import ensure_iterable, isiterable, get_first
from canopsis.storage import Storage


class CompositeStorage(Storage):
    """
    Storage dedicated to manage composite data identified by a data id in a
    path of ordered fields.

    For example, a metric is identified by a unique name in the path
    (type=metric, connector, component, resource) or
    (type=metric, connector, component).

    In addition to such composity, data of the same name and type can be the
    same data with different path. In such case, they are called shared and
    share the same value which is unique among all composite data.
    """

    __datatype__ = 'composite'  #: registered such as a composite storage

    PATH_SEPARATOR = '/'  #: char separator between path values

    SHARED = 'shared'  #: shared field name
    VALUE = 'value'  #: data value
    PATH = 'path'  #: path value

    def __init__(self, path=None, *args, **kwargs):
        """
        :param path: iterable of ordered lists of path names
        :type path: Iterable
        """

        super(CompositeStorage, self).__init__(*args, **kwargs)

        self._path = path

    @property
    def path(self):
        """
        tuple of ordered field names.
        """
        return self._path

    @path.setter
    def path(self, value):

        self._path = value
        self.reconnect()

    def all_indexes(self, *args, **kwargs):

        result = super(CompositeStorage, self).all_indexes(*args, **kwargs)

        # add index to shared property
        result.append([(CompositeStorage.SHARED, Storage.ASC)])

        return result

    def get_shared_data(self, shared_ids):
        """
        Get all shared data related to input shared ids.

        :param data: one or more data

        :return: depending on input shared_ids::

            - one shared id: one list of shared data
            - list of shared ids: list of list of shared data
        """

        result = []

        sids = ensure_iterable(shared_ids, iterable=set)

        for shared_id in sids:
            query = {CompositeStorage.SHARED: shared_id}
            shared_data = self.get_elements(query=query)
            result.append(shared_data)

        # return first or data if data is not an iterable
        if not isiterable(shared_ids, is_str=False):
            result = get_first(result)

        return result

    def share_data(
        self, data, shared_id=None, share_extended=False
    ):
        """
        Set input data as a shared data with input shared id

        :param data: one data

        :param shared_id: unique shared id. If None, the id is generated.

        :param share_extended: if True (False by default), set shared value to
            all shared data with input data

        :return: shared_id value (generated if None)
        """

        result = str(uuid()) if shared_id is None else shared_id

        # get an iterable version of input data
        #print 'plop', data
        data_to_share = ensure_iterable(data)

        for dts in data_to_share:
            # update extended data if necessary
            if share_extended:
                path, data_id = self.get_path_with_id(dts)
                extended_data = self.get(
                    path=path, data_ids=data_id, shared=True)
                # decompose extended data into a list
                dts = []
                for ed in extended_data:
                    dts += ed
            else:
                dts = [dts]

            for dt in dts:
                path, data_id = self.get_path_with_id(dt)
                dt[CompositeStorage.SHARED] = result
                self.put(path=path, data_id=data_id, data=dt)

        return result

    def unshare_data(self, data):
        """
        Remove share property from input data

        :param data: one or more data to unshare
        """
        data = ensure_iterable(data)

        for d in data:
            if CompositeStorage.SHARED in d:
                d[CompositeStorage.SHARED] = str(uuid())
                path, data_id = self.get_path_with_id(d)
                self.put(path=path, data_id=data_id, data=d)

    def get(
        self,
        path, data_ids=None, _filter=None, shared=False,
        limit=0, skip=0, sort=None
    ):
        """
        Get data related to input data_ids, input path and input filter.

        :param path: dictionnary of path valut by path name
        :type path: dict

        :param data_ids: data ids in the input path.
        :type data_ids: str or iterable of str

        :param _filter: additional filter condition to input path
        :type _filter: storage filter

        :param shared: if True, convert result to list of list of data where
            list of data are list of shared data.
        :type shared: bool

        :param limit: max number of data to get. Useless if data_id is given.
        :type limit: int

        :param skip: starting index of research if multi data to get
        :type skip: int

        :param sort: couples of field (name, value) to sort with ASC/DESC
            Storage fields
        :type sort: dict

        :return: a data or a list of data respectively to ids such as a str or
            an iterable of str
        :rtype: dict or list of dict
        """

        raise NotImplementedError()

    def find(self, path, _filter, shared=False, limit=0, skip=0, sort=None):
        """
        Get a list of data identified among a dictionary of composite values by
        name.

        :param path: path
        :type path: storage filter

        :param _filter: additional filter condition to input path
        :type _filter: storage filter

        :param shared: if True, convert result to list of list of data where
            list of data are list of shared data.
        :type shared: bool

        :param limit: max number of data to get. Useless if data_id is given.
        :type limit: int

        :param skip: starting index of research if multi data to get
        :type skip: int

        :param sort: couples of field (name, value) to sort with ASC/DESC
            Storage fields
        :type sort: dict

        :return: a list of data.
        :rtype: list of dict
        """

        raise NotImplementedError()

    def put(self, path, data_id, data, shared_id=None):
        """
        Put a data related to an id

        :param path: path
        :type path: storage filter

        :param data_id: data id
        :type data_id: str

        :param data: data to update
        :type data: dict

        :param shared_id: shared_id id not None
        :type shared_id: str
        """

        raise NotImplementedError()

    def remove(self, path, data_ids=None, shared=False):
        """
        Remove data from ids or type

        :param path: path to remove
        :type path: storage filter

        :param data_ids: data id or list of data id
        :type data_ids: list or str

        :param shared: remove shared data if data ids are related to shared
            data.
        :type shared: bool
        """

        raise NotImplementedError()

    def get_path_with_id(self, data):
        """
        Get input data path and id

        :type data: dict

        :return: data path, data id
        :rtype: tuple
        """
        path = {field: data[field] for field in data if field in self.path}

        result = path, data[Storage.DATA_ID]

        return result

    def get_absolute_path(self, path, data_id):
        """
        Get input data absolute path.

        :param path: path to remove
        :type path: storage filter

        :param data_id: data id
        :type data_id: str
        """

        result = ''

        for n, field in enumerate(self.path):
            if field in path:
                result = '%s%s%s' % (
                    result, CompositeStorage.PATH_SEPARATOR,
                        path[field])
            else:
                break

        if result:
            result = '%s%s%s' % (
                result, CompositeStorage.PATH_SEPARATOR,
                data_id)

        return result

    def _conf(self, *args, **kwargs):

        result = super(CompositeStorage, self)._conf(*args, **kwargs)

        category = None

        for _category in result:
            category = _category

        # add path property to the last category
        if category is not None:
            category += Parameter(CompositeStorage.PATH, self.path, eval)

        return result

    def _configure(self, unified_conf, *args, **kwargs):

        super(CompositeStorage, self)._configure(
            unified_conf=unified_conf, *args, **kwargs)

        # update the path property
        self._update_property(
                unified_conf=unified_conf,
                param_name=CompositeStorage.PATH)
