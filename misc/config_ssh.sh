#!/bin/bash

ssh -lroot $1 mkdir -p .ssh

cat ~/.ssh/id_rsa.pub | ssh -lroot $1 'cat >> .ssh/authorized_keys'

