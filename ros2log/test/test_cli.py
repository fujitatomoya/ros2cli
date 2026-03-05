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

import contextlib
import functools
import os
import re
import sys
import unittest

from launch import LaunchDescription
from launch.actions import ExecuteProcess
from launch.actions import RegisterEventHandler
from launch.actions import ResetEnvironment
from launch.actions import SetEnvironmentVariable
from launch.event_handlers import OnShutdown

from launch_ros.actions import Node

import launch_testing
import launch_testing.actions
import launch_testing.asserts
import launch_testing.markers
import launch_testing.tools
from launch_testing_ros.actions import EnableRmwIsolation
import launch_testing_ros.tools

import pytest

from rclpy.utilities import get_available_rmw_implementations
from ros2cli.helpers import get_rmw_additional_env


# Skip cli tests on Windows while they exhibit pathological behavior
# https://github.com/ros2/build_farmer/issues/248
if sys.platform.startswith('win'):
    pytest.skip(
        'CLI tests can block for a pathological amount of time on Windows.',
        allow_module_level=True)


@pytest.mark.rostest
@launch_testing.parametrize('rmw_implementation', get_available_rmw_implementations())
def generate_test_description(rmw_implementation):
    path_to_fixtures = os.path.join(os.path.dirname(__file__), 'fixtures')
    additional_env = get_rmw_additional_env(rmw_implementation)
    additional_env['PYTHONUNBUFFERED'] = '1'
    set_env_actions = [SetEnvironmentVariable(k, v) for k, v in additional_env.items()]

    path_to_talker_node_script = os.path.join(path_to_fixtures, 'talker_node.py')
    path_to_listener_node_script = os.path.join(path_to_fixtures, 'listener_node.py')

    talker_node_action = Node(
        executable=sys.executable,
        arguments=[path_to_talker_node_script],
        name='talker',
    )

    listener_node_action = Node(
        executable=sys.executable,
        arguments=[path_to_listener_node_script],
        name='listener',
    )

    return LaunchDescription([
        # Always restart daemon to isolate tests.
        ExecuteProcess(
            cmd=['ros2', 'daemon', 'stop'],
            name='daemon-stop',
            on_exit=[
                *set_env_actions,
                EnableRmwIsolation(),
                RegisterEventHandler(OnShutdown(on_shutdown=[
                    # Stop daemon in isolated environment with proper ROS_DOMAIN_ID
                    ExecuteProcess(
                        cmd=['ros2', 'daemon', 'stop'],
                        name='daemon-stop-isolated',
                        # Use the same isolated environment
                        additional_env=dict(additional_env),
                    ),
                    # This must be done after stopping the daemon in the isolated environment
                    ResetEnvironment(),
                ])),
                ExecuteProcess(
                    cmd=['ros2', 'daemon', 'start'],
                    name='daemon-start',
                    on_exit=[
                        talker_node_action,
                        listener_node_action,
                        launch_testing.actions.ReadyToTest(),
                    ],
                )
            ]
        ),
    ])


class TestROS2LogCLI(unittest.TestCase):

    @classmethod
    def setUpClass(
        cls,
        launch_service,
        proc_info,
        proc_output,
        rmw_implementation
    ):
        rmw_implementation_filter = launch_testing_ros.tools.basic_output_filter(
            filtered_patterns=['WARNING:.*'],
            filtered_rmw_implementation=rmw_implementation
        )

        @contextlib.contextmanager
        def launch_log_command(self, arguments):
            log_command_action = ExecuteProcess(
                cmd=['ros2', 'log', *arguments],
                name='ros2log-cli',
                output='screen'
            )
            with launch_testing.tools.launch_process(
                launch_service, log_command_action, proc_info, proc_output,
                output_filter=rmw_implementation_filter
            ) as log_command:
                yield log_command
        cls.launch_log_command = launch_log_command

    @launch_testing.markers.retry_on_failure(times=2, delay=1)
    def test_watch_basic(self):
        """Test basic ros2 log watch command."""
        with self.launch_log_command(arguments=['watch']) as log_command:
            assert log_command.wait_for_output(functools.partial(
                launch_testing.tools.expect_output, expected_lines=[
                    re.compile(r'.*\[INFO\].*\[(talker|listener)\] : Info message:'),
                ], strict=False
            ), timeout=10)
        assert log_command.wait_for_shutdown(timeout=10)

    @launch_testing.markers.retry_on_failure(times=2, delay=1)
    def test_watch_level_filter(self):
        """Test ros2 log watch with level filter."""
        with self.launch_log_command(
            arguments=['watch', '--level', 'ERROR']
        ) as log_command:
            assert log_command.wait_for_output(functools.partial(
                launch_testing.tools.expect_output, expected_lines=[
                    re.compile(r'.*\[ERROR\].*\[(talker|listener)\] : Error message'),
                ], strict=False
            ), timeout=10)
        assert log_command.wait_for_shutdown(timeout=10)

    @launch_testing.markers.retry_on_failure(times=2, delay=1)
    def test_watch_logger_filter(self):
        """Test ros2 log watch with logger name filter."""
        with self.launch_log_command(
            arguments=['watch', '--logger', 'talker']
        ) as log_command:
            assert log_command.wait_for_output(functools.partial(
                launch_testing.tools.expect_output, expected_lines=[
                    re.compile(r'.*\[INFO\].*\[talker\] : Info message'),
                ], strict=False
            ), timeout=10)
        assert log_command.wait_for_shutdown(timeout=10)

    @launch_testing.markers.retry_on_failure(times=2, delay=1)
    def test_watch_regex_filter(self):
        """Test ros2 log watch with regex filter."""
        with self.launch_log_command(
            arguments=['watch', '--regex', 'Publishing.*']
        ) as log_command:
            assert log_command.wait_for_output(functools.partial(
                launch_testing.tools.expect_output, expected_lines=[
                    re.compile(r'.*Publishing: Hello World'),
                ], strict=False
            ), timeout=10)
        assert log_command.wait_for_shutdown(timeout=10)

    @launch_testing.markers.retry_on_failure(times=2, delay=1)
    def test_watch_no_color(self):
        """Test ros2 log watch with color disabled."""
        with self.launch_log_command(
            arguments=['watch', '--no-color']
        ) as log_command:
            assert log_command.wait_for_output(functools.partial(
                launch_testing.tools.expect_output, expected_lines=[
                    re.compile(r'.*\[INFO\].*\[(talker|listener)\] : Info message'),
                ], strict=False
            ), timeout=10)
        assert log_command.wait_for_shutdown(timeout=10)
        # Check that no ANSI escape codes are present
        assert '\033[' not in log_command.output

    @launch_testing.markers.retry_on_failure(times=2, delay=1)
    def test_watch_no_timestamp(self):
        """Test ros2 log watch with timestamp disabled."""
        with self.launch_log_command(
            arguments=['watch', '--no-timestamp']
        ) as log_command:
            assert log_command.wait_for_output(functools.partial(
                launch_testing.tools.expect_output, expected_lines=[
                    re.compile(r'.*\[INFO\].*\[(talker|listener)\] : Info message'),
                ], strict=False
            ), timeout=10)
        assert log_command.wait_for_shutdown(timeout=10)

    @launch_testing.markers.retry_on_failure(times=2, delay=1)
    def test_watch_function_detail(self):
        """Test ros2 log watch with function details enabled."""
        with self.launch_log_command(
            arguments=['watch', '--function-detail']
        ) as log_command:
            assert log_command.wait_for_output(functools.partial(
                launch_testing.tools.expect_output, expected_lines=[
                    re.compile(r'.*\[INFO\].*\[(talker|listener)\] \[.*@.*:\d+\] : Info message'),
                ], strict=False
            ), timeout=10)
        assert log_command.wait_for_shutdown(timeout=10)

    @launch_testing.markers.retry_on_failure(times=2, delay=1)
    def test_watch_combined_filters(self):
        """Test ros2 log watch with multiple filters."""
        with self.launch_log_command(
            arguments=[
                'watch',
                '--level', 'INFO',
                '--logger', 'talker',
                '--no-color',
                '--no-timestamp'
            ]
        ) as log_command:
            assert log_command.wait_for_output(functools.partial(
                launch_testing.tools.expect_output, expected_lines=[
                    re.compile(r'.*\[INFO\].*\[talker\] : Info message:'),
                ], strict=False
            ), timeout=10)
        assert log_command.wait_for_shutdown(timeout=10)
        # Should have no ANSI codes
        assert '\033[' not in log_command.output

    @launch_testing.markers.retry_on_failure(times=2, delay=1)
    def test_watch_with_debug_flag(self):
        """Test ros2 log watch with global debug flag."""
        with self.launch_log_command(
            arguments=['--debug', 'watch', '--logger', 'talker']
        ) as log_command:
            assert log_command.wait_for_output(functools.partial(
                launch_testing.tools.expect_output, expected_lines=[
                    re.compile(r'.*\[INFO\].*\[talker\] : Info message'),
                ], strict=False
            ), timeout=10)
        assert log_command.wait_for_shutdown(timeout=10)

    @launch_testing.markers.retry_on_failure(times=2, delay=1)
    def test_watch_with_qos_options(self):
        """Test ros2 log watch with QoS options."""
        with self.launch_log_command(
            arguments=[
                'watch',
                '--qos-reliability', 'reliable',
                '--qos-durability', 'transient_local'
            ]
        ) as log_command:
            assert log_command.wait_for_output(functools.partial(
                launch_testing.tools.expect_output, expected_lines=[
                    re.compile(r'.*\[INFO\].*\[(talker|listener)\] : Info message'),
                ], strict=False
            ), timeout=10)
        assert log_command.wait_for_shutdown(timeout=10)

    @launch_testing.markers.retry_on_failure(times=2, delay=1)
    def test_levels_basic(self):
        """Test ros2 log levels command."""
        with self.launch_log_command(arguments=['levels']) as log_command:
            assert log_command.wait_for_output(functools.partial(
                launch_testing.tools.expect_output, expected_lines=[
                    re.compile(r'^UNSET\s+:.*'),
                    re.compile(r'^DEBUG\s+:.*'),
                    re.compile(r'^INFO\s+:.*'),
                    re.compile(r'^WARN\s+:.*'),
                    re.compile(r'^ERROR\s+:.*'),
                    re.compile(r'^FATAL\s+:.*'),
                ], strict=False
            ), timeout=10)
        assert log_command.wait_for_shutdown(timeout=10)

    @launch_testing.markers.retry_on_failure(times=2, delay=1)
    def test_levels_with_value(self):
        """Test ros2 log levels --value command."""
        with self.launch_log_command(arguments=['levels', '--value']) as log_command:
            assert log_command.wait_for_output(functools.partial(
                launch_testing.tools.expect_output, expected_lines=[
                    re.compile(r'^UNSET\s+\(\s*\d+\)\s*:.*'),
                    re.compile(r'^DEBUG\s+\(\s*\d+\)\s*:.*'),
                ], strict=False
            ), timeout=10)
        assert log_command.wait_for_shutdown(timeout=10)

    @launch_testing.markers.retry_on_failure(times=2, delay=1)
    def test_list_logger_service_nodes(self):
        """Test ros2 log list command."""
        with self.launch_log_command(arguments=['list']) as log_command:
            assert log_command.wait_for_output(functools.partial(
                launch_testing.tools.expect_output, expected_lines=[
                    re.compile(r'^/talker$'),
                ], strict=False
            ), timeout=10)
        assert log_command.wait_for_shutdown(timeout=10)
        assert '/no_logger_service' not in log_command.output
