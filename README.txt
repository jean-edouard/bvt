* DEPENDENCIES

These can be installed by running ./install.py

** postgresql
** Python2.6
** Twisted 10.0
** Conch
** stan
** psycopg2 2.2.1 or later
  earlier versions have relevant bugs
** datatables 1.6.2
   
   http://datatables.net/releases/dataTables-1.6.2.zip

 ** pyasn1

* TFTP server configuration

Autotest needs control of a standard Linux TFTP server in order to
support automated installation of XenClient (and installer status
reports).

** Setup:
*** Create a user "autotest" on the TFTP server 
*** On the autotest machine:
**** ssh-keygen
***** type "/scratch/credentials/id_rsa_tftp" when prompted for key location
*** Set up key based SSH access to the autotest account on the TFTP server. As that user:
**** mkdir -p ~autotest/.ssh
**** chmod 700 ~autotest/.ssh
**** transfer /scratch/credentials/id_rsa_tftp.pub made above and append it to ~autotest/.ssh/authorized_keys
