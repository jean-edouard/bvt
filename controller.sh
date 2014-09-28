#!/bin/bash

set -e

command=$1

./build_watcher.py $command
./bvt_daemon.py $command

echo "Successfully issued $command to daemons."
