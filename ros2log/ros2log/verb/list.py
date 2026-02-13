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

from ros2cli.node.strategy import add_arguments
from ros2cli.node.strategy import NodeStrategy
from ros2log.verb import VerbExtension
from ros2node.api import get_node_names
from ros2node.api import NodeName


LOGGER_GET_SERVICE_SUFFIX = '/get_logger_levels'
LOGGER_SET_SERVICE_SUFFIX = '/set_logger_levels'
LOGGER_GET_SERVICE_TYPE = 'rcl_interfaces/srv/GetLoggerLevels'
LOGGER_SET_SERVICE_TYPE = 'rcl_interfaces/srv/SetLoggerLevels'


def _print_nodes_with_logger_services(*, node, include_hidden_nodes: bool = False):
    """Print node names that expose both get/set logger level services."""
    node_names = get_node_names(node=node, include_hidden_nodes=include_hidden_nodes)
    for node_name in node_names:
        if _node_has_logger_services(node, node_name):
            print(node_name.full_name)
    return


def _node_has_logger_services(node, node_name: NodeName) -> bool:
    """Check if a node provides both get/set logger level services."""
    services = node.get_service_names_and_types_by_node(node_name.name, node_name.namespace)
    service_map = dict(services)

    expected_get = f'{node_name.full_name}{LOGGER_GET_SERVICE_SUFFIX}'
    expected_set = f'{node_name.full_name}{LOGGER_SET_SERVICE_SUFFIX}'

    return (
        _service_has_type(service_map, expected_get, LOGGER_GET_SERVICE_TYPE) and
        _service_has_type(service_map, expected_set, LOGGER_SET_SERVICE_TYPE)
    )


def _service_has_type(service_map, service_name: str, service_type: str) -> bool:
    """Check if a service exists and matches the expected type."""
    types = service_map.get(service_name)
    if not types:
        return False
    return service_type in types


class ListVerb(VerbExtension):
    """Output a list of nodes with logger services enabled."""

    def add_arguments(self, parser, cli_name):
        """Add CLI arguments for the list verb."""
        add_arguments(parser)

    def main(self, *, args):
        """Execute the list verb."""
        with NodeStrategy(args) as node:
            _print_nodes_with_logger_services(node=node)
        return 0
