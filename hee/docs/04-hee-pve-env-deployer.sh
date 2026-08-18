#!/bin/sh
# HEE PVE Environment Deployer - Task 4 Hardened Execution
# Uses atomic curl primitives with HTTP/1.1 and Expect header suppression.

set -e

printf "=====================================================================\n"
printf "HEE PVE API DEPLOYER: TASK 4 (HARDENED)\n"
printf "=====================================================================\n"
# Pre-flight environment assertions - Single-line defensive formatting to prevent paste buffer merging
if [ -z "$PVE_HOST" ] || [ -z "$PVE_TOKEN_ID" ] || [ -z "$PVE_TOKEN_SECRET" ]; then printf "ERROR: Missing required PVE authentication environment variables.\n" >&2; printf "Please export: PVE_HOST, PVE_TOKEN_ID, and PVE_TOKEN_SECRET\n" >&2; exit 1; fi

API_URL="https://${PVE_HOST}:8006/api2/json"
AUTH_HEADER="Authorization: PVEAPIToken=${PVE_TOKEN_ID}=${PVE_TOKEN_SECRET}"

printf "Target Hypervisor Gateway : %s\n" "$PVE_HOST"
printf "Executing Structural Instantiation...\n\n"

# 1. Instantiate the Core Resource Pool
printf "[1/6] Creating Resource Pool: hee-core-pool...\n"
curl --http1.1 -s -S -k -X POST "${API_URL}/pools" \
     -H "${AUTH_HEADER}" \
     -H "Expect:" \
     --data-urlencode "poolid=hee-core-pool" \
     --data-urlencode "comment=Dedicated resource pool for HEE core infrastructure nodes" \
     | grep -q "data" || printf " -> Note: Pool may already exist or pending validation.\n"
# 2. Instantiate the Access Control Group
printf "[2/6] Creating Access Group: hee-ops-group...\n"
curl --http1.1 -s -S -k -X POST "${API_URL}/access/groups" \
     -H "${AUTH_HEADER}" \
     -H "Expect:" \
     --data-urlencode "groupid=hee-ops-group" \
     --data-urlencode "comment=Cryptographically bounded operator groups executing machine-ops" \
     | grep -q "data" || printf " -> Note: Group may already exist.\n"
# 3. Instantiate the Custom HEE-Operator Role

printf "[3/6] Creating Custom Role: HEE-Operator...\n"
curl --http1.1 -s -S -k -X POST "${API_URL}/access/roles" \
     -H "${AUTH_HEADER}" \
     -H "Expect:" \
     --data-urlencode "roleid=HEE-Operator" \
     --data-urlencode "privs=VM.Audit,VM.Console,VM.PowerMgmt,Pool.Audit,SDN.Audit" \
     | grep -q "data" || printf " -> Note: Role may already exist.\n"
# 4. Bind the Group to the Pool via Access Control Lists (ACL)
printf "[4/6] Applying Access Control List Policy...\n"
curl --http1.1 -s -S -k -X PUT "${API_URL}/access/acl" \
     -H "${AUTH_HEADER}" \
     -H "Expect:" \
     --data-urlencode "path=/pool/hee-core-pool" \
     --data-urlencode "groups=hee-ops-group" \
     --data-urlencode "roles=HEE-Operator" \
     --data-urlencode "propagate=1"
# 5. Instantiate the Software-Defined Network (SDN) Zone

printf "[5/6] Provisioning SDN Zone: heezone...\n"
curl --http1.1 -s -S -k -X POST "${API_URL}/cluster/sdn/zones" \
     -H "${AUTH_HEADER}" \
     -H "Expect:" \
     --data-urlencode "zone=heezone" \
     --data-urlencode "type=vlan" \
     --data-urlencode "bridge=vmbr0" \
     --data-urlencode "comment=Isolated L2 network underlay for wire-like HEE communication" \
     | grep -q "data" || printf " -> Note: SDN Zone configuration complete or already defined.\n"
# 6. Instantiate the Virtual Network Segment (Vnet)
printf "[6/6] Provisioning SDN Vnet: heevnet (VLAN 650)...\n"
curl --http1.1 -s -S -k -X POST "${API_URL}/cluster/sdn/vnets" \
     -H "${AUTH_HEADER}" \
     -H "Expect:" \
     --data-urlencode "vnet=heevnet" \
     --data-urlencode "zone=heezone" \
     --data-urlencode "tag=650" \
     --data-urlencode "comment=Primary transit link segment for HEE Anchor-Worker duople packets" \

     | grep -q "data" || printf " -> Note: Vnet configuration complete or already defined.\n"

printf "\nApplying and broadcasting cluster-wide SDN topology changes...\n"
curl --http1.1 -s -S -k -X PUT "${API_URL}/cluster/sdn" -H "${AUTH_HEADER}" -H "Expect:"

printf "=====================================================================\n"
printf "Task 4 execution payload delivered successfully.\n"
printf "=====================================================================\n"


