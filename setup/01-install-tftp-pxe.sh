#!/bin/bash

source ./functions

echo "Setup will now install the tftp and pxe server. This feature is required if automated OpenXT installs are desired."
echo "Install tftp and pxe server?"
proceed=$(prompt)
exists=$(is_installed "tftpd")
if [[ $proceed == "True" && $exists == "False" ]]; then
    sudo apt-get install tftpd-hpa
	wget https://www.kernel.org/pub/linux/utils/boot/syslinux/syslinux-6.03.tar.gz
	tar xvf syslinux-6.03.tar.gz
    #Configure tftp server
    CUR_USER=$USER
    sudo chown -R $CUR_USER /srv/tftp
	pushd $(pwd)/syslinux-6.03/bios/core
	install -m 644 -p isolinux.bin pxelinux.0 ldlinux.sys /srv/tftp
	popd
	pushd $(pwd)/syslinux-6.03/bios/com32/
	install -m 644 -p mboot/mboot.c32 modules/pxechn.c32 /srv/tftp
	install -m 655 -p cmenu/complex.c32 menu/menu.c32 /srv/tftp
	install -m 655 -p elflink/ldlinux/ldlinux.c32 /srv/tftp
	install -m 655 -p lib/libcom32.c32 /srv/tftp
	popd

    pushd /srv/tftp
    mkdir -p pxelinux.cfg
	popd
else
	if [[ $exists == "True" ]]; then
		echo "Skipping installation because tftp server and pxe already exist."
	else
	    echo "Skipping installation and configuration of tftp server and pxe."
	fi
fi
