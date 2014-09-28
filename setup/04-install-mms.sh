#!/bin/bash

source ./functions

echo "Setup will now install Mongo Management Studio. MMS is not required, but it is one of the superior GUIs available for administration of a Mongo database."
echo "Install Mongo Management Studio?"
proceed=$(prompt)
if [[ $proceed == "True" ]]; then
    mkdir -p mongoMS
    pushd mongoMS
    wget http://packages.litixsoft.de/mms/1.7.0/mms-v1.7.0-community-linux.tar.gz
    tar xvf mms-v1.7.0-community-linux.tar.gz
    tar xvf mms-v1.7.0-community-linux-$(uname -m).tar.gz
    cd mms-v1.7.0-community-linux-$(uname -m)
    #Install dependencies.
    sudo apt-get install curl
    sudo curl -sL https://deb.nodesource.com/setup | sudo bash -
    sudo apt-get install nodejs
    sudo ./install.sh
    echo "Default configuration specifies server address as localhost.  Change host in /opt/lx-mms/config.js if access over the network is desired.  Invoke with lx-mms"
    popd
    echo "Done!"
else
    echo "Skipping installation and configuration of Mongo Management Studio."
fi
