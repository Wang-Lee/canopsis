#!/usr/bin/env python
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

from logging import ERROR, getLogger
from time import time

from canopsis.old.storage import get_storage
from canopsis.old.account import Account
from canopsis.old.record import Record
from canopsis.old.tools import legend, uniq

legend_type = ['soft', 'hard']


class Archiver(object):

    def __init__(self, namespace, storage=None,
                 autolog=False, logging_level=ERROR):

        self.logger = getLogger('Archiver')
        self.logger.setLevel(logging_level)

        self.namespace = namespace
        self.namespace_log = namespace + '_log'

        self.autolog = autolog

        self.logger.debug("Init Archiver on %s" % namespace)

        self.account = Account(user="root", group="root")

        if not storage:
            self.logger.debug(" + Get storage")
            self.storage = get_storage(namespace=namespace,
                                       logging_level=logging_level)
        else:
            self.storage = storage

        self.collection = self.storage.get_backend(namespace)


    def beat(self):
        # Default values
        self.bagot_freq = 10
        self.bagot_time = 3600
        self.stealthy_time = 300
        self.restore_event = True
        self.stealthy_show = 300

        self.state_config = self.storage.find({'crecord_type': 'state-spec'})
        if len(self.state_config) == 1:
            self.state_config = self.state_config[0]

            if 'bagot' in self.state_config:
                self.bagot_freq = self.state_config['bagot'].setdefault('freq',
                                                                        10)
                self.bagot_time = self.state_config['bagot'].setdefault('time',
                                                                        3600)

            self.stealthy_time = self.state_config.setdefault('stealthy_time',
                                                              300)
            self.stealthy_show = self.state_config.setdefault('stealthy_show',
                                                              300)
            self.restore_event = self.state_config.setdefault('restore_event',
                                                              True)


    def check_bagot(self, event, devent):

        # flowchart 6 7
        if self.is_bagot(event):
            self.set_status(event, 3)
        # flowchart 8 9
        else:
            self.set_status(event, 2)


    def is_bagot(self, event):
        ts_curr = event['timestamp']
        ts_first_bagot = event.get('ts_first_bagot', 0)
        ts_diff_bagot = (ts_curr - ts_first_bagot)
        freq = event.get('bagot_freq', -1)

        # flowchart 6 7
        if ts_diff_bagot <= self.bagot_time and freq >= self.bagot_freq:
            return True
        return False


    def is_stealthy(self, event):
        ts_diff = event['timestamp'] - event['ts_first_stealthy']
        return ts_diff <= self.stealthy_time


    def set_status(self, event, status):
        log = 'Status is set to {} for event {}'.format(event['rk'])
        values = {
            0: {'freq': event['bagot_freq'],
                'name': 'Off'
                },
            1: {'freq': event['bagot_freq'],
                'name': 'On going'
                },
            2: {'freq': event['bagot_freq'],
                'name': 'Stealthy'
                },
            3: {'freq': event['bagot_freq'] + 1,
                'name': 'Bagot'
                },
            4: {'freq': event['bagot_freq'],
                'name': 'Cancelled'
                }
            }

        self.logger.debug(log.format(values[status]['name']))
        event['status'] = status
        event['bagot_freq'] = values[status]['freq']

        if status != 2 and status != 3:
            event['ts_first_stealthy'] = 0


    def check_statuses(self, event, devent):
        # Check if event is still canceled
        # status legend:
        # 0 == Off
        # 1 == On going
        # 2 == Stealthy
        # 3 == Bagot
        # 4 == Canceled

        ts_curr = event['timestamp']
        ts_prev = devent['timestamp']
        event['bagot_freq'] = devent.get('bagot_freq', 0)
        event['ts_first_stealthy'] = devent.get('ts_first_stealthy', 0)
        event['ts_first_bagot'] = devent.get('ts_first_bagot', 0)
        if event['ts_first_bagot'] - event['timestamp'] > self.bagot_time:
            event['ts_first_bagot'] = 0
            event['bagot_freq'] = 0
        # flowchart 1 2 3
        if (devent.get('status', 1) != 4
            or (devent['state'] != event['state']
                and (self.restore_event
                     or state == 0
                     or devent['state'] == 0))):
            # flowchart 4
            if (event['state'] == 0):
                # flowchart 5 6 8
                if (devent['state'] == 0
                    and not self.is_bagot(event)
                    and not self.is_stealthy(event)):
                    self.set_status(event, 0)
                else:
                    self.check_bagot(event, devent)

            else:
                # flowchart 7 9
                if (not self.is_bagot(event)
                    and not self.is_stealthy(event)):
                    self.set_status(event, 1)
                elif self.is_bagot(event):
                    self.set_status(event, 3)
                elif self.is_stealthy(event):
                    if devent['status'] == 2 or devent['status'] == 0:
                        self.set_status(event, 2)
                    else:
                        self.set_status(event, 1)
        else:
            self.set_status(event, 4)

        if ((not devent['state'] and event['state']) or
            devent['state'] and not event['state']):
            event['ts_first_stealthy'] = event['timestamp']
            event['bagot_freq'] += 1

            if not event['ts_first_bagot']:
                event['ts_first_bagot'] = event['timestamp']



    def check_event(self, _id, event):
        changed = False
        new_event = False
        devent = {}

        self.logger.debug(" + Event:")

        state = event['state']
        state_type = event['state_type']

        self.logger.debug("   - State:\t'%s'" % legend[state])
        self.logger.debug("   - State type:\t'%s'" % legend_type[state_type])

        now = int(time())

        event['timestamp'] = event.get('timestamp', now)
        try:
            # Get old record
            #record = self.storage.get(_id, account=self.account)
            exclusion_fields = {
                'perf_data_array',
                'processing'
            }

            devent = self.collection.find_one(_id)

            if not devent:
                new_event = True
                # may have side effects on acks/cancels
                devent = {}

            self.logger.debug(" + Check with old record:")
            old_state = devent['state']
            old_state_type = devent['state_type']
            event['last_state_change'] = devent.get('last_state_change',
                                                    event['timestamp'])

            self.logger.debug("   - State:\t\t'%s'" % legend[old_state])
            self.logger.debug("   - State type:\t'%s'" % legend_type[old_state_type])


            if state != old_state:
                event['previous_state'] = old_state

            if state != old_state or state_type != old_state_type:
                self.logger.debug(" + Event has changed !")
                changed = True
            else:
                self.logger.debug(" + No change.")

            self.check_statuses(event, devent)

        except:
            # No old record
            self.logger.debug(" + New event")
            event['ts_first_stealthy'] = (event.get('timestamp', now)
                                          * (not not event['state']))
            changed = True
            old_state = state

        if changed:
            # Tests if change is from alert to non alert
            if ('last_state_change' in event
                and (state == 0 or (state > 0 and old_state == 0))):
                event['previous_state_change_ts'] = event['last_state_change']
            event['last_state_change'] = event.get('timestamp', now)

        if new_event:
            self.store_new_event(_id, event)
        else:
            change = {}

            # keep ack information if status does not reset event
            if 'ack' in devent:
                if event['status'] == 0 and event.get('keep_state'):
                    #reset ack when manual criticity change
                    change['ack'] = {}
                elif event['status'] not in [0, 1] or event.get('keep_state'):
                    change['ack'] = devent['ack']
                else:
                    #drop ack
                    change['ack'] = {}


            # keep cancel information if status does not reset event
            if 'cancel' in devent:
                if event['status'] not in [0, 1]:
                    change['cancel'] = devent['cancel']
                else:
                    change['cancel'] = {}


            # keep incident information if status does not reset event
            if 'ticket_declared' in devent and event['status'] == 0:
                change['ticket_declared'] = {}


            for key in event:
                if key not in exclusion_fields:
                    if key in event and key in devent and devent[key] != event[key]:
                        change[key] = event[key]
                    elif key in event and key not in devent:
                        change[key] = event[key]


            #Manage keep state key that allow from UI to keep the choosen state into until next ok state
            event_reset = False

            #When a event is ok again, dismiss keep_state statement
            if devent.get('keep_state') and event['state'] == 0:
                change['keep_state'] = False
                event_reset = True

            #assume we don t just received a keep state and if keep state was sent previously
            #then override state of new event
            if 'keep_state' not in event:
                if not event_reset and devent.get('keep_state'):
                    change['state'] = devent['state']

            #Keep previous output
            if 'keep_state' in event:
                change['output'] = devent.get('output', '')

            if change:
                self.storage.get_backend('events').update({'_id': _id},
                                                          {'$set': change})

        mid = None
        if changed and self.autolog:
            #store ack information to log collection
            if 'ack' in devent:
                event['ack'] = devent['ack']
            mid = self.log_event(_id, event)


        return mid

    def store_new_event(self, _id, event):
        record = Record(event)
        record.type = "event"
        record.chmod("o+r")
        record._id = _id

        self.storage.put(record, namespace=self.namespace, account=self.account)

    def log_event(self, _id, event):
        self.logger.debug("Log event '%s' in %s ..." % (_id, self.namespace_log))
        record = Record(event)
        record.type = "event"
        record.chmod("o+r")
        record.data['event_id'] = _id
        record._id = _id + '.' + str(time())

        self.storage.put(record,
                         namespace=self.namespace_log,
                         account=self.account)
        return record._id

    def get_logs(self, _id, start=None, stop=None):
        return self.storage.find({'event_id': _id},
                                 namespace=self.namespace_log,
                                 account=self.account)

    def remove_all(self):
        self.logger.debug("Remove all logs and state archives")

        self.storage.drop_namespace(self.namespace)
        self.storage.drop_namespace(self.namespace_log)
