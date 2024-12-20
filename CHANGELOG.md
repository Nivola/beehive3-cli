# Changelog

## Devel

* Added ...
    * mixed_output_handler
    * if stdout not a tty, default to old (mostly no color) output handler
    * bugfix ip_address column for platform vsphere server list missing in output
    * dedicated command for account capabilities update
* Updated ...
    * make 'type' param mandatory in staas efs add command
* Fixed ...
    * correct command returning nsx edge load balancers configuration   

## Version 1.16.0

* Added ...
    * Vsphere vms clone
    * Account existence control
    * CLI exit code
    * Account add/update new fields: account_type, management_model, pods
* Fixed ...
    * fix creating sqlserver using storage param
    * fix wait creating internet gateway

## Version 1.15.0

* Added ...
    * warning when importing all lb in nsx edge
    * clear cache
    * zabbix management
    * monitoring alert management
    * ontap platform
    * command to load resource volume on service
* Fixed ...
    * load balancer import
    * refactoring imports
    * some descriptions and messages
    * fix wait for task
    * bash completion
    * options when creatings security group

## Version 1.14.0

* Added ...
  * ssh gateway improvement
  * hypervisor and creation date infos to list-all vms
  * ssh nodes as inventory in JSON format
  * session set permission by role
  * veeam platform backup management
  * load balancer improvements
  * utility for metadata updating of databases as a service
* Fixed ...
  * Load balancer updates and reworks
  * Ssh Gateway updates and reworks
  * list-all vm counter
  * minor fixes

## Version 1.13.0

* Added ...
    * Get hostname using socket library
    * shh keys export to file
    * ssh key hide export
    * ask command
    * grafana filter dashboard per folder
    * monitoring as a service dashboard copy
    * logging as a service management
    * ssh gateway management
    * some improvement on query openstack platform
* Fixed ...
    * volume migrate and volume api extensions
    * add_oracle method
    * monitoring fix sync users
    * elasticsearch upgrade
    * other minor fixes
    * Pass number of vms to look for in list_all method
    * deprecated cpaas enable/disable monitoring/logging
    * fix cancellazione internet gateway
    * add compute instance quota
    * miglior output in caso di data None
    * ssh gateway api first commit

## Version 1.12.0

* Added ...
  * refresh vm state
  * monitor as a service management
  * Add command to refresh vm state
  * Add filter by account in compute tag list
  * add check in instance add for openstack host_group
  * add print cpaas instance list with host info
  * Add cmds to start/stop nsx edge lb
  * add security group in rule list
  * add auth perms get-method
  * Add load balancer health monitor cli business commands
  * Support for oracle 12EE
* Fixed ...
  * graphana protocolo connection
  * curl description
  * Openstack flavor creation made by customization
  * Vms load command
  * Reworked add methods for nsx edge monitor and app profile
  * Minor changes on vsphere nsx network edge load balancer platform cmds
  * Draft of network edge load balancer plugin vsphere cmds
  * Update nsx edge paltform commands
  * Update vsphere nsx edge load balancer platform cmds

## Version 1.11.0 (oct 11, 2022)
* Added ...
    * add grafana platform management
    * add kibana platform management
    * add bu.maas commands
    * add bu.logaas commands
* Various bugfixes

## Version 1.9.0 (Feb 11, 2022)

* Added ...
    * add command account definitions-get in order to get the service definition available for the account
    * add param options in dbaas db instances add
    * add command provider.site_network_subnet_add
    * add openstack aggregates and flavor extra spec in openstack platform section
    * add bu.service-insts patch command
    * add bu.cpaas.vms get-console command
    * add ssh.nodes admin-password-set and admin-password-get commands to get and set admin password
    * add platform.vsphere.dfw_section_add command to create dfw section
    * add bu.cpaas.vms commands to manage virtual machine backup and restore
    * add command platform.openstack project-quota-set
    * add zabbix platform proxy management
    * add graphite section
    * add command router_rewrite_routes in openstack platform to rewrite wrong route rules
* Fixed ...
    * fixed bug in SecurityGroup rule representation when protocol is icmp
    * big performance optimization
* Integrated ...
    * update bash completion reference file
    * update redis get command to support list
    * add redis ping cmp ping
    * update bu capabilities and account capabilities to support account definitions
* Various bugfixes

## Version 1.8.0 (Jun 11, 2021)

* Added ...
    * add db instance method start, stop, reboot
    * add db instance database method database_get, database_add, database_del
    * add db instance database method user_get, user_add, user_del, user_priv_grant, user_priv_revoke, user_password_set
    * add cmp command runtime_api_spec to get openapi spec for cmp subsystem
    * add cmp ssh ops command check_disk_rw
* Fixed ...
* Integrated ...
    * account delete command now permit defining if remove child services
* Various bugfixes

## Version 1.7.0 (May 03, 2021)

* Added ...
    * add commands dbaas_check_dd, dbaas_umount_dd, dbaas_mount_dd in section ssh.ops to manage mount and umount of
      datadomain nfs share used for logical dbaas backup
    * add commands in platform redis to manage redis with sentinel
    * add business compute instance methods to reboot, enable logging, enable monitorig
    * add group management method to awx section
    * add business internet gateway methods to manage bastion
    * add new platform check to nsx controller and components
    * add new section platform.cmp.logs2 to read log from new cmp elastic index
    * add awx ad_hoc_command section
    * add stack sql methods: get_dbs and get_users
    * add server group management in openstack platform client
* Fixed ...
    * renamed schema in db in platform mariadb
* Integrated ...
* Various bugfixes

## Version 1.6.0 (mar 01, 2021)

* Added ...
    * add platform virsh section that map libvirt client
    * add openstack paltform volume metadata and image metadata management
    * add openstack platform command sys_compute_hypervisor_servers
    * add openstack platform command servers_migrate, security_group_add, security_group_update
    * add DynamicOutputHandler to manage dinamic table in data rendering
    * add platform mysql commands binary_log_show and binary_log_purge
    * add provider instance methods to manage internal user
    * add business compute instance methods to manage internal user
    * add business compute customization
    * add node connection using another node as ssh gateway
    * add filters to cpaas vms list
* Fixed ...
    * update of remote shell console now was made with rsync
* Integrated ...
    * update section platform console to add some commands
    * integrated BeehiveApiClient method set_endpoints to set endpoints manually from config
    * update section cmp with access to k8s deploy
    * integrated node connect using password
    * integrated beedrones cmp api client
* Various bugfixes

## Version 1.5.0 (dec 03, 2020)

* Added ...
    * add openstack trilio platform section
    * add ping commando to openstack section
    * add platform k8s section
    * add section data quality
    * add service instance check command
    * add provider section instance_add command
    * add command to check all platform items
* Fixed ...
* Integrated ...
    * update section platform console to better manage remote console and users
* Various bugfixes

## Version 1.4.0 (Oct 23, 2020)

* Added ...
    * add openstack share network command
    * add openstack share server command
    * add openstack resource command for shares
    * add resource entities command cache_get and cache_del
    * add section for trilio
* Fixed ...
    * removed print of uuid in openstack resources
    * fixed provider resource command for shares
* Integrated ...
    * integrated render of tabular data with color in state and status
    * integrated staas efs api param PerformanceMode used to manage share based on netapp and new share base on local
      openstack server
* Various bugfixes

## Version 1.3.0 (Oct 2, 2020)

* Added ...
    * added list of ipv4 ip in vsphere server get and list
    * add provider stack and sql stack commands
    * add openstack server command to add/remove security group
    * add vsphere server command to add/remove security group
    * add native openstack volume command to manage volume snapshot, volume group, volume group snapshot
    * add native vsphere volume command to manage volume snapshot, volume group, volume group snapshot
    * add openstack volume command to add/remove volume snapshot
    * add openstack share-type-get command
    * add vsphere server command to add/remove/revert snapshot
    * add provider instance command to add/remove/revert snapshot
    * add business instance command to add/remove security group
    * add business instance command to add/remove/revert snapshots
* Fixed ...
    * fixed applied_customization_add
    * manage better openstack volume attachment
* Integrated ...
* Various bugfixes

## Version 1.2.0 (Sep 22, 2020)

* Added ...
    * added plugin system for customize
    * added command cpaas.images add, type, get, delete
* Fixed ...
    * command to make cmp subsystem create
    * post install renamed in costomize
    * correct command encrypt and decrypt
    * fixed cmp subsystem update without ansible playbook
* Integrated ...
    * delete of auth tokens now permits delete of all active tokens
    * added list of ports in openstack subnet get
* Various bugfixes
    * correct bug in staas grant_delete

## Version 1.2.0 (Aug 17, 2020)

* Added ...
    * command to manage business internet network gateway
    * extended layout of nsx edge get command
    * added nsx edge method for syslog
    * added nsx edge method for sslvpn
* Fixed ...
* Integrated ...
* Various bugfixes

## Version 1.1.0 (Aug 17, 2020)

* Added ...
    * command to manage remote shell console users
    * command to show platform hosts from ansible
    * provider commands for gateway
    * some fields in list o business capabilities
    * bash completion
* Fixed ...
* Integrated ...
* Various bugfixes
    * correct bug over appengine list
    * correct filter in netaas subnet list command
    * correct command result of res_provider rule_add

## Version 1.0.0 (Jun 21, 2020)

First production release.

## Version 0.1.0 (September 27, 2019)

First private preview release. Start porting from python 2.7 release.
