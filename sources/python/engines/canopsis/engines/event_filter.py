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

from canopsis.engines import Engine, DROP

from canopsis.old.account import Account
from canopsis.old.storage import get_storage
from canopsis.old.event import forger, get_routingkey
from canopsis.old.mfilter import check

from ast import literal_eval
from time import time


class engine(Engine):
    etype = 'event_filter'

    def __init__(self, *args, **kargs):
        super(engine, self).__init__(*args, **kargs)

        account = Account(user="root", group="root")
        self.storage = get_storage(logging_level=self.logging_level,
                       account=account)
        self.derogations = []
        self.name = kargs['name']

    def pre_run(self):
        self.drop_event_count = 0
        self.pass_event_count = 0
        self.beat()

    def time_conditions(self, derogation):
        conditions = derogation.get('time_conditions', None)

        if not isinstance(conditions, list):
            self.logger.error(("Invalid time conditions field in '%s': %s"
                       % (derogation['_id'], conditions)))
            self.logger.debug(derogation)
            return False

        result = False

        now = time()
        for condition in conditions:
            if (condition['type'] == 'time_interval'
                and condition['startTs']
                    and condition['stopTs']):
                always = condition.get('always', False)

                if always:
                    self.logger.debug(" + 'time_interval' is 'always'")
                    result = True

                elif (now >= condition['startTs']
                      and now < condition['stopTs']):
                    self.logger.debug(" + 'time_interval' Match")
                    result = True

        return result

    # Override/adds 'field' of event with 'value'
    def a_override(self, event, action):
        afield = action.get('field', None)
        avalue = action.get('value', None)

        if afield and avalue:
            event[afield] = avalue
            self.logger.debug(("    + %s: Override: '%s' -> '%s'"
                           % (event['rk'], afield, avalue)))
            return True

        else:
            self.logger.error("Action malformed (needs 'field' and 'value'): %s" % action)
            return False

    # Remove field 'key', if element is specified,
    # remove 'element' in 'key' instead
    def a_remove(self, event, action):
        akey = action.get('key', None)
        aelement = action.get('element', None)
        del_met = action.get('met', 0)

        if akey:
            if aelement:
                if del_met:
                    for i, met in enumerate(event[akey]):
                        if met['name'] == aelement:
                            del event[akey][i]
                            break
                elif isinstance(event[akey], dict):
                    del event[akey][aelement]
                elif isinstance(event[akey], list):
                    del event[akey][event[akey].index(aelement)]

                self.logger.debug("    + %s: Removed: '%s' from '%s'"
                        % (event['rk'], aelement, akey))

            else:
                del event[akey]
                self.logger.debug("    + %s: Removed: '%s'"
                        % (event['rk'], akey))

            return True

        else:
            self.logger.error("Action malformed (needs 'key' and/or 'element'): %s" % action)
            return False


    # Wrap modification action functions
    def a_modify(self, event, derogation, action, _name):
        name = derogation.get('name', None)
        _id = derogation.get('_id', None)

        # If _id is ObjectId(), transform it to str()
        if not isinstance(_id, str):
            _id = str(_id)

        derogated = False
        atype = action.get('type', None)
        actionMap = {'override': self.a_override,
                     'remove': self.a_remove}

        if actionMap[atype]:
            derogated = actionMap[atype](event, action)

        else:
            self.logger.warning("Unknown action '%s'" % atype)

        # If the event was derogated, fill some informations
        if derogated:
            self.logger.debug("Event changed by rule '%s'" % name)

    # simple drop
    def a_drop(self, event, derogation, action, name):
        self.logger.debug("Event dropped by rule '%s'" % name)
        self.drop_event_count += 1
        return DROP

    # simple pass
    def a_pass(self, event, derogation, action, name):
        self.logger.debug("Event passed by rule '%s'" % name)
        self.pass_event_count += 1
        return event

    # Change next_amqp_queues of engine
    # (will be reseted in Engine after this current call)
    def a_route(self, event, derogation, action, name):
        if "route" in action:
            self.next_amqp_queues = [action["route"]]
            self.logger.debug("Event re-routed by rule '%s'" % name)
        else:
            self.logger.error("Action malformed (needs 'route'): %s" % action)

        return None

    def work(self, event, *xargs, **kwargs):

        rk = get_routingkey(event)
        default_action = self.configuration.get('default_action', 'pass')

        # list of actions supported
        actionMap = {'drop': self.a_drop,
                     'pass': self.a_pass,
                     'override': self.a_modify,
                     'remove': self.a_modify,
                     'route': self.a_route}

        rules = self.configuration.get('rules', [])

        # When list configuration then check black and
        # white lists depending on json configuration
        for filterItem in rules:
            actions = filterItem.get('actions')
            name = filterItem.get('name', 'no_name')

            self.logger.debug(
                'Event: {}, will apply rule {}'.format(event['rk'], filterItem)
                )

            # Try filter rules on current event
            if check(filterItem['mfilter'], event):

                self.logger.debug(
                    'Event: {}, filter matches'.format(event['rk'])
                    )

                for action in actions:
                    if (action['type'] in actionMap):
                        ret = actionMap[action['type']](event, filterItem,
                                        action, name)
                        # If pass then ret == event; end loop
                        if ret:
                            return (DROP if ret == DROP else event)

                    else:
                        self.logger.warning("Unknown action '%s'" % action)

        # No rules matched
        if default_action == 'drop':
            self.logger.debug("Event '%s' dropped by default action" % (rk))
            self.drop_event_count += 1
            return DROP

        self.logger.debug("Event '%s' passed by default action" % (rk))
        self.pass_event_count += 1

        self.logger.debug('Event before sent to next engine')
        event['rk'] = event['_id'] = get_routingkey(event)

        return event

    def beat(self, *args, **kargs):
        """ Configuration reload for realtime ui changes handling """
        self.derogations = []
        self.configuration = {'rules': [],
                      'default_action': self.find_default_action()}

        self.logger.debug('Reload configuration rules')
        try:
            records = self.storage.find({'crecord_type': self.etype},
                            sort='priority')

            for record in records:
                record_dump = record.dump()
                record_dump["mfilter"] = literal_eval(record_dump["mfilter"])
                self.logger.debug('Loading record_dump:')
                self.logger.debug(record_dump)
                self.configuration['rules'].append(record_dump)
            self.logger.info('Loaded {} rules'.format(len(self.configuration['rules'])))
            self.send_stat_event()

        except Exception as e:
            self.logger.warning(str(e))

    def send_stat_event(self):
        """ Send AMQP Event for drop and pass metrics """

        event = forger(
            connector="Engine",
            connector_name="engine",
            event_type="check",
            source_type="resource",
            resource=self.amqp_queue + '_data',
            state=0,
            state_type=1,
            output=("%s event dropped since %s"
                  % (self.drop_event_count, self.beat_interval)),
            perf_data_array = [
                {'metric': 'pass_event',
                 'value': self.pass_event_count,
                 'type': 'GAUGE'},
                {'metric': 'drop_event',
                 'value': self.drop_event_count,
                 'type': 'GAUGE'}])

        self.logger.debug(("%s event dropped since %s"
                   % (self.drop_event_count, self.beat_interval)))
        self.logger.debug(("%s event passed since %s"
                   % (self.pass_event_count, self.beat_interval)))

        rk = get_routingkey(event)
        self.amqp.publish(event, rk, self.amqp.exchange_name_events)
        self.drop_event_count = 0
        self.pass_event_count = 0

    def find_default_action(self):
        """ Find the default action stored and returns it, else assume it default action is pass """

        records = self.storage.find({'crecord_type': 'defaultrule'})
        if records:
            return records[0].dump()["action"]

        self.logger.debug("No default action found. Assuming default action is pass")
        return 'pass'
