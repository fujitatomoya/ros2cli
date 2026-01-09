# ros2log

The log command for ROS 2 command line tools.

## Overview

`ros2log` provides a unified command-line interface for monitoring and managing ROS 2 logging. It allows users to watch logs in real-time with powerful filtering capabilities.

## Commands

### `ros2 log watch`

Monitor and display logs in real-time by subscribing to the `/rosout` topic.

**Usage:**
```bash
ros2 log watch [options]
```

**Options:**
- `--level <level>`: Show only logs at or above the specified severity level (DEBUG, INFO, WARN, ERROR, FATAL)
- `--logger <logger_name>`: Filter logs by logger name
- `--regex <pattern>`: Filter log messages matching the specified regular expression pattern
- `--no-color`: Disable colorized output
- `--no-timestamp`: Disable timestamp display
- `--function-detail`: Output function name, file, and line number

**Examples:**
```bash
# Watch all logs from /rosout topic
ros2 log watch

# Watch logs from a specific logger
ros2 log watch --logger my_node.perception

# Watch only ERROR and FATAL logs
ros2 log watch --level ERROR

# Watch logs containing specific text pattern
ros2 log watch --regex "sensor.*timeout"

# Combine filters: ERROR logs from specific logger matching pattern
ros2 log watch --level ERROR --logger my_node.vision --regex "camera"

# Watch with function details
ros2 log watch --function-detail

# Watch without colors or timestamps
ros2 log watch --no-color --no-timestamp
```

## Implementation Notes

The `watch` command subscribes to the `/rosout` topic with transient local durability to receive existing messages as well as new ones. Filtering is performed client-side to ensure consistent behavior across all RMW implementations.

When the underlying RMW implementation supports Content Filtered Topics, future versions may leverage this feature to reduce network traffic.

## License

Apache License, Version 2.0
