#!/usr/bin/env python
# -*- coding: utf-8 -*-
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

from unittest import TestCase, main

from canopsis.rule import RULE
from canopsis.topology.manager import Topology
from canopsis.topology.process import event_processing, PUBLISHER
from canopsis.context.manager import Context


class ProcessingTest(TestCase):

    def setUp(self):
        self.context = Context()
        self.topology = Topology(data_scope='test')
        self.check = {
            'event_type': 'check',
            'connector': '',
            'connector_name': '',
            'component': '',
            'source_type': 'component',
            'state': 0}
        entity = self.context.get_entity(self.check)
        entity_id = self.context.get_entity_id(entity)
        self.node = {
            Topology.ENTITY_ID: entity_id,
            Topology.ID: 'test',
            'state': 0,
            RULE: 'canopsis.topology.rule.action.change_state'
        }
        self.topology.push_node(self.node)

    def test_no_bound(self):
        """
        Test in case of not bound nodes
        """

        _event = self.check.copy()
        _event['source_type'] = 'resource'
        _event['resource'] = ''
        event = event_processing(event=_event)
        self.assertEqual(_event, event)

    def test_one_node(self):
        """
        Test in case of one bound node
        """

        event = event_processing(event=self.check)
        _node = self.topology.get_nodes(ids=self.node[Topology.ID])
        self.assertEqual(
            self.node[Topology.ENTITY_ID], _node[Topology.ENTITY_ID])
        self.assertEqual(self.node[Topology.ID], _node[Topology.ID])
        self.assertEqual(self.check, event)

    def test_one_state(self):
        """
        Test with a changing state on one node.
        """

        # new state to propagate to one node
        new_state = 1
        self.check['state'] = new_state
        event = event_processing(event=self.check)
        self.assertEqual(event, self.check)

        _node = self.topology.get_nodes(ids=self.node[Topology.ID])
        self.assertNotEqual(self.node['state'], _node['state'])
        self.assertEqual(_node['state'], new_state)

    def test_nexts(self):
        """
        Test next nodes
        """

        # create a publisher
        class Publisher(object):
            def publish(self, event, **kwargs):
                event_processing(event=event, **kwargs)
        # create next nodes from self.nodes
        nexts = (
            {
                Topology.ID: str(i),
                RULE: self.node[RULE],
                'state': 0
            } for i in range(3)
        )
        # list of next ids
        next_ids = []
        for next in nexts:
            # push next nodes
            self.topology.push_node(next)
            next_ids.append(next[Topology.ID])
        # add next nodes into self.node
        self.node[Topology.NEXT] = next_ids
        # save the node
        self.topology.push_node(self.node)

        # propagate a new state
        new_state = 1
        self.check['state'] = new_state
        event_processing(event=self.check, ctx={PUBLISHER: Publisher()})

        for next in nexts:
            _node = self.topology.get_nodes(next[Topology.ID])
            self.assertEqual(_node['state'], 1)
            self.topology.delete_nodes(next[Topology.ID])

    def tearDown(self):
        self.topology.delete_nodes(self.node[Topology.ID])


if __name__ == '__main__':
    main()
