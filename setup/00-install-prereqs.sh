#!/bin/bash

echo "Installing required prereqs..."

sudo apt-get update

sudo apt-get install build-essential git python postgresql python-twisted conch python-psycopg2 python-pyasn1 python-setuptools python-docutils python-nevow amtterm lftp dirmngr

# To get correct python-bson version (2.6.3-1build1)
# Note: may need to remove already-installed version(s) of bson
#[add Trusty main repo here and refresh/update]
#sudo apt-get install python-bson=2.6.3-1build1

sudo easy_install pymongo==2.2 # To get correct python-pymongo version (2.2): 
sudo easy_install pysnmp
sudo easy_install requests

#Install amtctrl tool for wsman-only AMT versions
git clone https://github.com/sdague/amt
pushd amt
sudo python setup.py install
popd

echo "Done!"
#Setup python stuff
echo "Installing required python-daemon package..."
pushd ~/
wget https://pypi.python.org/packages/source/p/python-daemon/python-daemon-2.0.2.tar.gz
tar xvf python-daemon-2.0.2.tar.gz
cd python-daemon-2.0.2
python setup.py build
sudo python setup.py install
popd
echo "Done!"

echo "Installing required Mongodb..."
#Mongodb, from mongo
# The Mongodb repository we use is old and un-maintained...
# Below is the gpg key for it, but it's long expired...
# Using apt-get --allow-unauthenticated to work around that
#sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 7F0CEB10
echo 'deb http://downloads-distro.mongodb.org/repo/debian-sysvinit dist 10gen' | sudo tee /etc/apt/sources.list.d/mongodb.list
sudo apt-get update
sudo apt-get install -y --allow-unauthenticated mongodb-org=2.6.6 mongodb-org-server=2.6.6 mongodb-org-shell=2.6.6 mongodb-org-mongos=2.6.6 mongodb-org-tools=2.6.6
echo "Done!"

echo "Creating empty private_settings.py"
touch ../src/bvtlib/private_settings.py
echo "Done!"
