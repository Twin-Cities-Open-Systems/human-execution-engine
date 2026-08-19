## Deployment and Integration Architecture
To integrate this script with your existing mail transfer configuration without introducing background processes or user-space tracking scripts, you can hook it directly into a standard Postfix aliases pipeline.
## 1. Configure the MTA Ingress Pipe
Add a line to your local on-prem server mail aliases file (typically located at /etc/aliases):

hee-gateway: "|/usr/local/bin/hee-mail-ingress.sh"

Run the newaliases command to update the lookup tables. When an agent or operator emails hee-gateway@yourdomain.org, Postfix captures the raw data stream and feeds it directly into the standard input of the shell script.
## 2. Local Key Management Setup
The script isolates key tracking to a root-managed path (/etc/hee/gpg/). To seed the authorized registry:

* Import your senior keys into the isolated directory using: gpg --homedir /etc/hee/gpg/ --import senior_key.asc
* Export the 40-character fingerprint and append it to your authorized validation ledger at /etc/hee/authorized_senior_signers.list.

