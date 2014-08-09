#!/usr/bin/env python
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

from unittest import TestCase, main

from canopsis.middleware.manager import Manager


class TestManager(Manager):
    pass


class ManagerTest(TestCase):

    def setUp(self):
        self.storage_names = [
            'timed_storage',
            'periodic_storage',
            'storage',
            'typed_storage',
            'timed_typed_storage']

        self.manager = Manager(
            data_type=None,
            auto_connect=False)
        self.data_types = ['data_type_0', 'data_type_1']

        # get storage types loaded by the manager
        for attribute in dir(self.manager):
            if attribute.endswith('storage'):
                setattr(
                    self, attribute, type(getattr(self.manager, attribute)))

    def test_get_storage(self):

        for data_type in self.data_types:

            for storage_name in self.storage_names:

                storage_type = getattr(self, storage_name)

                storage = self.manager.get_storage(
                    data_type=data_type,
                    storage_type=storage_type)

                shared_storage = self.manager.get_storage(
                    data_type=data_type,
                    storage_type=storage_type,
                    shared=True)

                self.assertTrue(storage is shared_storage)

                not_shared_storage = self.manager.get_storage(
                    data_type=data_type,
                    storage_type=storage_type,
                    shared=False)

                self.assertFalse(storage is not_shared_storage)

                storage_method = getattr(
                    self.manager, 'get_{0}'.format(storage_name))

                sstorage = storage_method(data_type=data_type)

                self.assertTrue(sstorage is storage)

                shared_sstorage = storage_method(
                    data_type=data_type,
                    shared=True)

                self.assertTrue(sstorage is shared_sstorage)

                not_shared_storage = storage_method(
                    data_type=data_type,
                    shared=False)

                self.assertFalse(sstorage is not_shared_storage)


if __name__ == '__main__':
    main()