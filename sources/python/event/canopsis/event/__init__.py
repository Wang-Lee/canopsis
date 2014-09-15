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


class Event(object):
    """
    Manage event content

    An event contains information and require a type and source_type.
    """

    TYPE = 'type'
    SOURCE = 'source'
    DATA = 'data'
    META = 'meta'

    __slots__ = (TYPE, SOURCE, DATA, META)

    def __init__(self, source, data, meta, _type=None):

        super(Event, self).__init__()

        self.type = type(self).__name__.lower() if _type is None else _type
        self.source = source
        self.data = data
        self.meta = meta

    @classmethod
    def new_event(event_class, **old_event):
        """
        Create an Event from an old event (ficus and older version).
        """

        _type = event_class.__name__.lower()
        _type = old_event.pop(Event.EVENT_TYPE, _type)
        source = old_event.pop(Event.SOURCE)
        data = old_event.pop(Event.DATA, None)
        meta = old_event.pop(Event.META, None)

        result = Event(
            _type=_type,
            source=source,
            data=data,
            meta=meta)

        return result
