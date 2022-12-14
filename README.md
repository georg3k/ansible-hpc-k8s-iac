# Ansible HPC

```
       {_                          {__       {__          {__     {__{_______      {__   
      {_ __                      {_{__       {__          {__     {__{__    {__ {__   {__
     {_  {__    {__ {__   {____    {__       {__   {__    {__     {__{__    {__{__       
    {__   {__    {__  {__{__    {__{__ {__   {__ {_   {__ {______ {__{_______  {__       
   {______ {__   {__  {__  {___ {__{__   {__ {__{_____ {__{__     {__{__       {__       
  {__       {__  {__  {__    {__{__{__   {__ {__{_        {__     {__{__        {__   {__
 {__         {__{___  {__{__ {__{__{__ {__  {___  {____   {__     {__{__          {____ 
```

## Infrastructure as Code

The purpose of this project is to provide an automated environment for setting up and managing HPC clusters (and other stuff).

> **Note**
> This project was originally meant to be a tool for automatic HPC cluster configuration and maintenance, however over time it became a single point of management for my local lab cluster and includes various somehow unrelated services. It is not advisable to use such a monolithic project to control and maintain all of your infrastructure, however in a lab environment it does serve well. You can use this project as a cookbook and take separate roles that you actually need. Currently it can be used to configure all kind of clusters (LDAP and ssh auth, DHCP, DNS, NTP, PXE boot, IPMI, etc), HPC clusters (Slurm), deploy monitoring (Zabbix), high-availability clusters (Kubernetes), Gitlab instances, Ingress and SSL termination points (Nginx reverse proxy) and other. My lab cluster consists of 4 compute nodes equiped with 2x GPUs and 2x CPUs, 8 compute nodes with CPUs only and 12 kubernetes nodes for web services. Use in production at your own risk, security and reliability not guaranteed.

## Quick start

> **Note**
> For simplicity control node playbook deploys all services on one central node. This approach may be ok in testing environments or small scale applications, but is generally not recommended. You may want to deploy services not directly involved in HPC computations (Gitlab, Zabbix, etc) on separate servers. This requires some modifications to the code.

### Prerequisites

Before deploying configuration make sure that the control node meets all the requirements:
- CentOS 8 Stream installed
- Internet connection available
- Dependencies installed

This project assumes following criteria:
- /home is not mounted as a separate partition
- /docker is not mounted as a separate partition
- /export is not mounted as a separate partition

List of all dependencies are contained within several files. To install them:

```bash
dnf install -y epel-release
xargs dnf install -y < ./dnf.list
pip3 install -r ./requirements.txt
ansible-galaxy collection install -r ./requirements.yml
```

### Infrastructure preparations

All cluster nodes (including control node) are supposed to be connected to one local network, optional management subnet can be used for IPMI control and monitoring. Appliances (switches, UPS, etc) should be configured to use DHCP network configuration and PXE boot should be enabled on all nodes.

### Control node configuration

To start configuration execute:

```bash
ansible-playbook setup-control-node.yml --ask-vault-pass
```

Enter Ansible Vault pass and wait for completion.

### Appliances configuration

To configure UPS, switches and other devices execute:

```bash
ansible-playbook setup-appliances.yml --ask-vault-pass
```

### Nodes configuration

Cluster nodes configuration playbook assumes that the operating system is already installed on them. Control node playbook includes PXE network boot and install services so you can reboot your nodes and automatically install a distributive (You have to choose this option during startup though). After that you can proceed to configuration:

```bash
ansible-playbook setup-cluster-nodes.yml --ask-vault-pass
```

## Structure

### inventory

inventory file determines list of managed devices and separates them into groups:

```
[group_name]
host_name_1
host_name_2 <options>
```

### group_vars

> **Note**
> Encrypted passwords marked with !vault don't contain any real information and given for demonstrational purposes only, change them to match your data

**group_vars/all.yml** file includes global configuration parameters such as network CIDRs, domain names, etc. You should change these options to match your environment. Purpose of each parameter is described in comments.

### host_vars

**host_vars** directory contains variables for every managed device. This includes MAC addresses, bonding parameters, resources information, etc. You should create a separate file for every cluster node present in the inventory file.

### roles

All services are presented as distinct and isolated Ansible role. Some roles can be applied to both control node and cluster node, but their behaviour differs depending on host type.

* auth\
Basic authentication services:
    * For control node:
        * OpenLDAP setup (as docker service)
        * LAM setup (as docker service)
    * For all nodes:
        * LDAP client setup
        * LDAP integration
        * LDAP SSH key auth
        * Welcome screen
        * SSH configuration (key-based auth for external connections and host-based auth for internal connections)
        * Home directories creation and misc (oddjobd, autofs)
* chrony\
NTP server
    * Time sync setup
* DHCP\
Distributes IP addresses for cluster nodes and appliances
    * Manages IPs for all managed subnets 
    * Reserves IPs based on MAC
    * Gives PXE boot server location
    * Gives DNS server location
    * Gives NTP server location
* DNS\
BIND9 server
    * Sets up BIND9 server
    * Generates forward and reverse zones for all managed subnets and devices based on their hostnames
* Docker\
Docker containers support:
    * For control node:
        * Creates directory on NAS for persistent storage
        * Creates Docker Swarm cluster
    * For all nodes:
        * Installs Docker
        * Installs docker-compose
        * Mounts NFS directory for persistent bind mounts
* NAS\
Manages network attached storage:
    * For control node:
        * Mounts iSCSI LUN
        * Creates several required directories on NAS
        * Manages access to NAS via NFS
    * For all nodes:
        * Installs NFS services
        * Mounts NFS shares
* network\
Basic network configuration:
    * Sets hostnames
    * Enables routing and masquerading (NAT) via control node
    * Configures static and dynamic interfaces
    * Configures interface bonding
    * Configures firewall (firewalld) zones
* PXE\
Enables PXE boot within cluster network:
    * Installs tFTP
    * Downloads, verifies and extracts CentOS installer image
    * Generates kickstart installation script
    * Manages NFS directory for installation image
* NGINX \
Reverse proxy server and SSL termination point:
    * Reverse proxy
    * SSL certs from LetsEncrypt
    * Automatic certs updates using Certbot
* Gitlab\
Gitlab git and CI/CD server:
    * Installs Gitlab EE
    * Sets up LDAP login and accounts management
    * Installs special script that implements some of paid Gitlab EE features regarding LDAP synchronization, admin management, etc.\
      Script project: [https://github.com/georg3k/gitlab-ldap-sync](https://github.com/georg3k/gitlab-ldap-sync)
* hass \
Home Assistant instance to manage HVAC and power devices:
    * LDAP sync (for admins only)
    * Custom auth plugin for LDAP auth: roles/hass/files/hass-ldap-sync.py
    * Broadlink and SonoffLAN installed
    * Preconfigured (you may want to provide your own configuration since this one is very specific for my environment)
* zabbix \
Infrastructure monitoring:
    * Deploys Zabbix in docker
    * Enables LDAP sync and login
    * Discovery rules
    * Installs special script that implements LDAP accounts synchronization similar to Gitlab \
      Script project: [https://github.com/georg3k/zabbix-ldap-sync](https://github.com/georg3k/zabbix-ldap-sync)
* apcupsd \
Automatic UPS shutdown on power loss:
    * Installs and configures apcupsd
* Kubernetes \
Kubernetes high-availability cluster:
    * Uses kubeadm
    * Calico as network backend
    * MetalLB as load balancer

### Roles structure

Each role may have following directories structure (some may be absent):
* tasks\
List of role tasks that will be executed in playbook
* handlers\
Conditional actions triggered by some tasks
* files\
Static files
* templates\
Jinja2 templates
* meta\
Meta information about given role (usually dependencies)

### Playbooks

Main purpose of playbooks is to connect hosts from the inventory file with corresponding roles. There are three playbooks in this project, they can be executed individually and independently:

* setup-control-node.yml
* setup-cluster-nodes.yml
* setup-appliances.yml

### Other files

* dnf.list - system dependencies
* requirements.txt - Python pip dependencies
* requirements.yml - Ansible Galaxy dependencies
* ansible.cfg - main Ansible configuration file
