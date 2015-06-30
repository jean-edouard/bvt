#!/bin/bash

source ./functions

echo "Install Apache Web server?"
proceed=$(prompt)
if [[ $proceed == "True" ]]; then
    sudo apt-get install apache2
else
    echo "Skipping installation and configuration of Apache Web Server."
fi

