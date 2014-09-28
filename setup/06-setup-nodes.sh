#!/bin/bash

source ./functions

REGEX="[^0-9]"
echo "BVT uses file locks to guarantee concurrency across testing nodes. The following operation will create 0 length files in the bvt directory purely to provide a target for file locks. Allow node creation?"
proceed=$(prompt)
if [[ $proceed == "True" ]]; then
	read -p "How many test nodes in your testing pool? " nodes
	if [[ $nodes =~ $REGEX ]]; then
		echo "Invalid entry."
		exit 1
	else
		n=$nodes
	fi


	mkdir -p ../nodes
	for (( i=0; i < $n; i++ )); do
		touch ../nodes/node$i
	done
else
	echo "Skipping node creation."
fi
