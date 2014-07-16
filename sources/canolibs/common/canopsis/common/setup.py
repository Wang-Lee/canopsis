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

from setuptools import setup as _setup, find_packages

from os import walk, getenv
from os.path import join, dirname, expanduser, abspath, basename, exists

from sys import path, argv

from canopsis.common.utils import resolve_element

#import canopsis
#from pkgutil import extend_path

# TODO: set values in a dedicated configuration file
AUTHOR = 'Capensis'
AUTHOR_EMAIL = 'canopsis@capensis.fr'
LICENSE = 'AGPL V3'
ZIP_SAFE = False
URL = 'http://www.canopsis.org'
KEYWORDS = ' Canopsis Hypervision Hypervisor Monitoring'


def setup(description, keywords, add_etc=True, **kwargs):
    """
    Setup dedicated to canolibs projects.

    :param description: project description
    :type description: str

    :param keywords: project keywords
    :type keywords: str

    :param add_etc: add automatically etc files (default True)
    :type add_etc: bool

    :param kwargs: enrich setuptools.setup method
    """

    # get setup path which corresponds to first python argument
    filename = argv[0]

    _path = dirname(abspath(expanduser(filename)))
    name = basename(_path)

    # add path to python path
    path.append(_path)

    # extend canopsis path with new sub modules and packages
    # canopsis.__path__ = extend_path(canopsis.__path__, canopsis.__name__)

    # get package
    package = resolve_element("canopsis.{0}".format(name))

    # set default parameters if not setted
    kwargs.setdefault('name', package.__name__)
    kwargs.setdefault('author', AUTHOR)
    kwargs.setdefault('author_email', AUTHOR_EMAIL)
    kwargs.setdefault('license', LICENSE)
    kwargs.setdefault('zip_safe', ZIP_SAFE)
    kwargs.setdefault('url', URL)
    kwargs.setdefault('package_dir', {'': _path})

    kwargs.setdefault('keywords', kwargs.get('keywords', '') + KEYWORDS)

    # set version
    version = getattr(package, '__version__', None)
    if version is not None:
        kwargs.setdefault('version', version)

    # add etc content if exist
    if add_etc:
        etc_path = join(_path, 'etc')

        if exists(etc_path):
            data_files = kwargs.get('data_files', [])
            target = getenv('CPS_PREFIX', '/opt/canopsis/etc/')

            for root, dirs, files in walk(etc_path):
                files_to_copy = [join(root, _file) for _file in files]
                data_files.append((target, files_to_copy))
            kwargs['data_files'] = data_files

    # add scripts if exist
    if 'scripts' not in kwargs:
        scripts_path = join(_path, 'scripts')
        if exists(scripts_path):
            scripts = []
            for root, dirs, files in walk(scripts_path):
                for _file in files:
                    scripts.append(join(root, _file))
            kwargs['scripts'] = scripts

    # add packages
    if 'packages' not in kwargs:
        packages = find_packages(where=_path, exclude=['test'])
        kwargs['packages'] = packages

    # add description
    if 'long_description' not in kwargs:
        readme_path = join(_path, 'README')
        if exists(readme_path):
            with open(join(_path, 'README')) as f:
                kwargs['long_description'] = f.read()

    # add test
    if 'test_suite' not in kwargs and exists(join(_path, 'test')):
        for test_folder in ['test', 'tests']:
            if exists(join(_path, test_folder)):
                kwargs['test_suite'] = test_folder
                break

    _setup(**kwargs)
