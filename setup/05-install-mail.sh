#!/bin/bash

source ./functions

echo "Setup will now install mailutils and postfix. While not required, this enables email notifications to be sent to interested admins about test case results."
echo "Install mailutils and postfix?"
proceed=$(prompt)
if [[ $proceed == "True" ]]; then
    sudo apt-get install mailutils postfix
    echo "Done!"
else
    echo "Skipping installation and configuration of mailutils and postfix."
fi

