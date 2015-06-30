#!/bin/bash

if [[ $(basename $(pwd)) != "setup" ]]; then
	echo "Run this script inside setup directory."
	exit -1
fi

source ./00-install-prereqs.sh
source ./01-install-tftp-pxe.sh
source ./02-install-apache.sh
source ./03-install-dhcp-serv.sh
source ./04-install-mms.sh
source ./05-install-mail.sh
source ./06-setup-nodes.sh
source ./07-init-mongodb.sh
