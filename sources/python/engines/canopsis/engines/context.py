# -*- coding: UTF-8 -*-
#--------------------------------
# Copyright (c) 2011 "Capensis" [http://www.capensis.com]
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

from canopsis.engines import Engine

from canopsis.context.manager import Context
"""
TODO: sla
from canopsis.middleware import Middleware
"""


class engine(Engine):
    etype = 'context'

    def __init__(self, *args, **kwargs):
        super(engine, self).__init__(*args, **kwargs)

        # get a context
        self.context = Context()
        """
        TODO: sla
        # get a storage for sla macro
        #self.storage = Middleware.get_middleware(
        #    protocol='storage', data_scope='global')

        #self.sla = None
        """
        self.beat()

    def beat(self):
        """
        TODO: sla
        sla = self.storage.find_elements(request={
            'crecord_type': 'sla',
            'objclass': 'macro'
        })

        if sla:
            self.sla = sla[0]
        """

    def work(self, event, *args, **kwargs):
        mCrit = 'PROC_CRITICAL'
        mWarn = 'PROC_WARNING'

        """
        TODO: sla
        if self.sla:
            mCrit = self.sla.data['mCrit']
            mWarn = self.sla.data['mWarn']
        """

        context = {}

        # Get event informations
        connector = event['connector']
        connector_name = event['connector_name']
        component = event['component']
        resource = event.get('resource', None)
        hostgroups = event.get('hostgroups', [])
        servicegroups = event.get('servicegroups', [])

        # add connector
        entity = {
            Context.NAME: connector
        }
        self.context.put(
            _type='connector', entity=entity)

        # add connector_name
        entity[Context.NAME] = connector

        context['connector'] = connector
        self.context.put(
            _type='connector_name', entity=entity, context=context)

        # add status entity which is a component or a resource
        entity[Context.NAME] = 'component'
        context['connector_name'] = connector_name
        status_entity = entity.copy()
        status_entity['hostgroups'] = hostgroups

        is_status_entity = False
        source_type = event['source_type']

        # create an entity status which is a component or a resource
        if source_type == 'component':
            is_status_entity = True

        elif source_type == 'resource':
            # add component
            self.context.put(
                _type='component', entity=status_entity, context=context)
            is_status_entity = True
            context['component'] = component
            status_entity[Context.NAME] = resource
            status_entity['servicegroups'] = servicegroups

        else:
            self.logger.warning('source_type unknown %s' % source_type)

        if is_status_entity:
            # add status entity
            status_entity['mCrit'] = event.get(mCrit, None)
            status_entity['mWarn'] = event.get(mWarn, None)
            status_entity['state'] = event['state']
            status_entity['state_type'] = event['state_type']
            self.context.put(
                _type=source_type, entity=status_entity, context=context)

        # add hostgroups
        for hostgroup in hostgroups:
            hostgroup_data = {
                Context.NAME: hostgroup
            }
            self.context.put(_type='hostgroup', entity=hostgroup_data)

        # add servicegroups
        for servicegroup in servicegroups:
            servicegroup_data = {
                Context.NAME: servicegroup
            }
            self.context.put(_type='servicegroup', entity=servicegroup_data)

        # add authored entity data (downtime, ack, metric, etc.)
        authored_data = entity.copy()
        if resource is not None:
            context['resource'] = resource
            if 'author' in event:
                authored_data['author'] = event['author']
            if 'comment' in event:
                authored_data['comment'] = event['comment']

        event_type = event['event_type']

        if event_type == 'ack':
            authored_data['timestamp'] = event['timestamp']
            authored_data[Context.NAME] = str(event['timestamp'])

        elif event_type == 'downtime':
            authored_data['downtime_id'] = event['downtime_id']
            authored_data['start'] = event['start']
            authored_data['end'] = event['end']
            authored_data['duration'] = event['duration']
            authored_data['fixed'] = event['fixed']
            authored_data['entry'] = event['entry']
            authored_data[Context.NAME] = event['id']

        self.context.put(
            _type=event_type, entity=authored_data, context=context)

        # add perf data
        for perfdata in event['perf_data_array']:
            perfdata_entity = entity.copy()
            perfdata_entity[Context.NAME] = perfdata['metric']
            perfdata_entity['internal'] = perfdata['metric'].startswith('cps')
            self.context.put(
                _type='metric', entity=perfdata_entity, context=context)

        return event
