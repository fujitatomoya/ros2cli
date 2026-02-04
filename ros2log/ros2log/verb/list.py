# Copyright 2025 Tomoya Fujita, Fumiya Ohnishi
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
from typing import List

from ros2cli.node.strategy import add_arguments
from ros2cli.node.strategy import NodeStrategy
from ros2node.api import get_node_names
from ros2node.api import NodeName

from ros2log.verb import VerbExtension


LOGGER_GET_SERVICE_SUFFIX = '/get_logger_levels'
LOGGER_SET_SERVICE_SUFFIX = '/set_logger_levels'
LOGGER_GET_SERVICE_TYPE = 'rcl_interfaces/srv/GetLoggerLevels'
LOGGER_SET_SERVICE_TYPE = 'rcl_interfaces/srv/SetLoggerLevels'


def _get_nodes_with_logger_services(*, node, include_hidden_nodes: bool = False) -> List[NodeName]:
    node_names = get_node_names(node=node, include_hidden_nodes=include_hidden_nodes)
    return [n for n in node_names if _node_has_logger_services(node, n)]


def _node_has_logger_services(node, node_name: NodeName) -> bool:
    services = node.get_service_names_and_types_by_node(node_name.name, node_name.namespace)
    service_map = {service_name: types for service_name, types in services}

    expected_get = f'{node_name.full_name}{LOGGER_GET_SERVICE_SUFFIX}'
    expected_set = f'{node_name.full_name}{LOGGER_SET_SERVICE_SUFFIX}'

    return (
        _service_has_type(service_map, expected_get, LOGGER_GET_SERVICE_TYPE) and
        _service_has_type(service_map, expected_set, LOGGER_SET_SERVICE_TYPE)
    )


def _service_has_type(service_map, service_name: str, service_type: str) -> bool:
    types = service_map.get(service_name)
    if not types:
        return False
    return service_type in types


class ListVerb(VerbExtension):
    """Output a list of nodes with logger services enabled."""

    def add_arguments(self, parser, cli_name):
        add_arguments(parser)

    def main(self, *, args):
        with NodeStrategy(args) as node:
            node_names = _get_nodes_with_logger_services(node=node)

        if node_names:
            sorted_names = sorted(n.full_name for n in node_names)
            print(*sorted_names, sep='\n')
        return 0
