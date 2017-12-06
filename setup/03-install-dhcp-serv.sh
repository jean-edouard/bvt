#!/bin/bash

source ./functions

echo "Setup will now install isc-dhcp-server. Configuration will overwrite the 
/etc/dhcp/dhcpd.conf file with a custom version."
echo "Install ISC DHCP server?"
proceed=$(prompt)
exists=$(is_installed "isc-dhcp-server")
if [[ $proceed == "True" && $exists == "False" ]]; then

    sudo apt-get install isc-dhcp-server
	echo "Please provide configuration information for the dhcp server. It is always possible to change the values in /etc/dhcp/dhcpd.conf later."
	read -p "Domain name: " DOMAIN_NAME
	read -p "Subnet: " SUBNET
	read -p "Network interface: " INTERFACE
	read -p "Lower bound for available addresses: " RANGE_LOWER
	read -p "Upper bound for available addresseS: " RANGE_UPPER
	read -p "Broadcast address: " BROADCAST
	read -p "Routers: " ROUTERS
	read -p "Dns servers: " DNS_SERVERS
	read -p "Hostname of test machine: " TEST_MACHINE
	read -p "MAC address of test machine: " MAC
	read -p "Static IP to give test machine: " STATIC_IP
	cp dhcpd.conf.template dhcpd.conf
	sed -i "s/{DOMAIN_NAME}/$DOMAIN_NAME/g" dhcpd.conf
	sed -i "s/{SUBNET}/$SUBNET/g" dhcpd.conf
	sed -i "s/{INTERFACE}/$INTERFACE/g" dhcpd.conf
	sed -i "s/{RANGE_LOWER}/$RANGE_LOWER/g" dhcpd.conf
	sed -i "s/{RANGE_UPPER}/$RANGE_UPPER/g" dhcpd.conf
	sed -i "s/{BROADCAST}/$BROADCAST/g" dhcpd.conf
	sed -i "s/{ROUTERS}/$ROUTERS/g" dhcpd.conf
	sed -i "s/{DNS_SERVERS}/$DNS_SERVERS/g" dhcpd.conf
	sed -i "s/{TEST_MACHINE}/$TEST_MACHINE/g" dhcpd.conf
	sed -i "s/{MAC}/$MAC/g" dhcpd.conf
	sed -i "s/{STATIC_IP}/$STATIC_IP/g" dhcpd.conf
	sudo mv dhcpd.conf /etc/dhcp/
    sudo sed -i "s/INTERFACES=\"\"/INTERFACES=\"${INTERFACE}\"/g" /etc/default/isc-dhcp-server

	echo "Finished basic configuration of dhcp server. Edit /etc/dhcp/dhcpd.conf directly to enable additional features like reverse lookup or ddns."
    #Also need to alias in /etc/hosts
    echo "Make sure to alias the fixed addresses in /etc/hosts for test machines."
    echo "Done!"
	echo "Setup will now install utilities to support DDNS (libnet-dns-zonefile-fast-perl and bind9).  Would you like to install these?"
	proceed=$(prompt)
	if [[ $proceed == "True" ]]; then
		sudo apt-get install libnet-dns-zonefile-fast-perl bind9
	else
		echo "Skipping installation of dns utilities."
	fi
else
    echo "Skipping Installation and Configuration of ISC DHCP Server."
fi
