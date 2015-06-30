#!/bin/bash

source ./functions

echo "Setup will now initialize some mongodb entries (duts and suites).  Manual entry can always be performed at a later time."
echo "Init mongodb entries?"
proceed=$(prompt)

if [[ $proceed == "True" ]]; then
	../mongo-init.py
else
	echo "Skipping initialization of mongodb."
fi
