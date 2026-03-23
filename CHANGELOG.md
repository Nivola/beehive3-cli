# Changelog

## Version 2025.08.11 (2025-08-11)

* Fixed
  - Fix staas visualization

## Version 2025.08.05 (2025-08-05)

* Added
  - set_lang
  - translations
  - Add optional param log in res-provider create sg rule command
  - redis: add connection port
  - datastore_get: add filters
  - Introduced NotImplementedError for CmpApiClient.wait_job, indicating that direct waiting for job IDs is not supported by the current API client for task v1.
  - Switched to yaml.safe_load for safer and forward-compatible YAML parsing
  - Fix(pylint): Rename snapshot_policies to avoid E0203
  - Use builtins.list to bypass shadowed 'list' name
  - admin tool italian translation
* Fixed
  - Fix openstack revert volume
  - Fix to support id in get volume

## Version 2025.06.12 (2025-06-12)

* Added
  - update translations
  - The admin tool now uses the Resource Provider Compute API instead of Simple Resource, as the old one sometimes does not populate blockdevices
* Fixed
  - fix dns: zone_fqdn_query, zone_alias_query return error
  - fix awx job list: add job name
  - fix vsphere deleting folder, server
  - fix test run filter fromtest

## Version 2025.05.22 (2025-05-22)

* Added
  - database admin mgmt tool add sqlstack check
  - patchset for admin check tools
  - update staas v2 enable compliance option, in order to accept rpo value
  - staas v2 enable/disable compliance to ACN requirements
  - commented staas v2 action commands merged into update command
  - Add staas v2 update check: only one param at a time can be updated
  - Multilingual translations
  - filter accounts for status and expired
* Fixed
  - Fix cache invalidation in cpaas admin check tool

## Version 2025.04.29 (2025-04-24)

* Added
  - dbaas admin tool: discriminate data starting from mount point
  - Various fix in dbaas admin tool
  - Bulk tag update
  - Openstack database volumes suggestion
  - Add check to admin cmds
  - fix description logaas, maas

## Version 2025.04.17 (2025-04-17)

* Added
  - Handling of volume for command beehive mgmt database check
  - Added handling for dbaas tags in management command
  - cmp fernet key can be stored in envirinment configuration  as an encripted value named cmpkey
  - get definition  now create a cutomization yaml file
  - backup job add instance plugintype
  - Add platform command to get Ontap snapshot policies
  - Minor changes to staas v2 add grant superuser option
  - mgmt tool provider volume name and better checks
  - db mgmt when add a volume in cmp for dbaas has_quotas=False
* Fixed
  - fix account service-del: delete also ComputeVolume
  - fix veeam job description
  - bugfix provider volumes for database should be imported with quotas disabled
  - Fix db mgmt when quota flag is None

## Version 2025.03.31 (2025-03-31)

* Added
  - task list: show pod
  - staas v2 protocol in rule creation
  - beehive auth perms list
  - added optional (commented) bit to check ssh user perms
  - command iamdev
  - zabbix timeout at 60 sec
  - capability check before updating (with diff)
  - Correct type hint in staas-v2 grant-add co
* Fixed
  - fixed service filter output
  - fix tag get filters
  - fix account servce del for  private

## Version 2025.03.12 (2025-03-07)

* Fixed
  - Correct type hint in staas-v2 grant-add command

## Version 2025.03.06 (2025-03-06)

* Added
  - Remove type (i.e. service-def) optional param from staas-v2 add and add-legacy commands
  - Enabled encryption option in staas-v2 create volume
  - no more six
  - envs: remove orchestrators info
* Fixed
  - fix dfw delete rule
  - Fix page number in cpaas vms list

## Version 2025.02.27 (2025-02-27)

* Added
  - Add page and size param for command beehive platform vsphere nsx-manager-event-get
  - Commented staas v2 volume encryption option for the moment
  - awx relaunch job return new job id
  - Add encrypt option in create staas v2 command
  - run test add -totest param
  - sg rules new print and section_name filter
  - provider rule get, service filter and warning
  - Renamed some res-provider share methods
  - add vsphere sg_rule_get command
  - Removed some redundant headers in staas efs list command
  - staas bu source view
  - staas bu replica view
  - staas fix resource list
  - vsphere ipset platform filters and output
  - staas mount fix + minor
  - add plugintype parameter for serch definitions
  - improve service delete
  - vsphere platform dvpg-find (by name and/or vlan_id), minor corrections, list_servers for dvpg-get
  - openstack platform filter servers by ip and power_state; fix parameters errors, removed duplicate function, renamed function with wrong name
  - Correct staas replica mount command
  - staas snapmirror delete
  - staas svm-set refactor
  - staas platform snaplock info
  - test run add param fromtest
  - Correct online/offline field name in staas list command
  - timer improve
  - pylint, share-add-v2, share-mount
  - platform staas new snapmirror visualization
  - staas bu replica-add
  - staas visualization mount target and bugfix
  - Add staas grant-list command
  - Correct online/offline endpoint command - part2
  - redis log host info
  - staas rules v1 new visualization
  - Correct online/offline endpoint command
  - Add missing param path to expanduser method
  - test: run param failfast default True
  - Staas mount replica command implementation
  - update definition: confirm change
  - delete account: delete_tags default true
  - vpc get
  - Staas replica suspend and resume commands implementation
  - Staas replica unlink cmd implementation
  - Correct typo in 'choices' option
  - Add set online/offline share status command at res provider level
  - Arranged set online/offline share status commands
  - Refactoring staas delete export policy rule
  - Remove mandatory clients param from add staas command
  - provider rule_add with reserved, orchestrators params
  - attivato comando con starter pack oracle
  - added  new arameters in dbaas add oracle
  - sg: add in add_rule param orchestrators
  - real delete account
  - render task trace, link list
  - new command set-env
  - hide commands, check developer user
  - Add filter -version to staas efs list command
  - dry run
  - Updated efs list cmd output with params taken from efs target-list
  - register entity and link commands
  - commands update: review kibana dashboard
  - kibana review dashboard commands
  - logaas instance WARNING msgs
* Fixed
  - fix container update
  - fixed  parameters  in generic service delete
  - staas bu bugfix v1 mount target and maybe grants
  - bugfix staas v1 mount targets
  - Fixed staas get command
  - fix capability data output
  - Bug fixing staas add export policy rule
  - fix msg volume delete
  - fix compatibility cement 3.0.12
  - fix render site_network_get

## Version 2024.12.04 (2024-12-03)

* Added
  - command auto complete
  - res synchronize add comment Default params
  - platform cmp customize run: comment Update service definition config for prod
  - platform cmp customize run: add dry param for test, now only for service definitions
  - Try to support ssh cp with gateway
* Fixed
  - map[fix:parametr "key" ambigous or conflicting]
  - Fix i ssh command
  - Fix for beehive ssh commands

## Version 2024.11.06 (2024-11-29)

* Added
  - Commented encrypt and decrypt methods
  - logaas instance list with detail (uncommented)
  - Renamed LDAP "key" argument in order not to be in conflicy with global app.key used to encrypt/decrypt
  - Correct the way rancher uri is acquired
  - Changes to use encrypted passwords in env files
  - Add type and bits in keypairs get
  - fix user, role get commands
  - remove some sensitive information

## Version 2024.11.05 (2024-11-20)

* Added
  - update color status (account)
  - remove account close
  - Deprecated efs add and efs target-add commands
  - aggiunte funzione per comandi interattivi
  - aggiunti commenti
  - vsphere volumetype_get add filter, sort output
  - task parent param for task log
  - CLone help
  - Clone; minor in help and examples
  - expire role
  - grafana team uid
  - Add check for vm creation for boot and disk options
  - elastic: filters query with wildcard
  - fisx default hypervisor in help string
  - pep8
* Fixed
  - Fix in clone

## Version 2024-11.02 (2024-11-04)

* Fixed
  - Fix commit 03e66496

## Version 2024-11.01 (2024-10-31)

* Added
  - accounts triplet new command
  - grafana: rename and update copy dashboard
  - monitoring: disable_dashboard
* Fixed
  - map[alert:fix len user group name]

## Version 2024-10.01 (2024-10-24)

* Added
  - Clone allowed without specify ssh key for windows
  - Add -type options in get linked entities command
  - Add options appliedTo and direction to dfw rule update cmd
  - cmp image info and packages
  - platform awx commands about execution environment
  - Prevents sys.platform from being overwritten by by a platform.py. This occurs on alpine cli (hivetool/docker/cli/py-alpine.env)
  - logaas instance list with detail (commented)
  - Update requirements
  - platform awx execution environments
  - USe cypto utils
  - Update to crypto utils
  - Update dfw rule update method
  - Set default rule logging value to True
  - Add command to update an existing vsphere dfw rule
  - Add log option into create rule command
  - nuovo comando creazione dp postgresql
  - popular resource list command with pages
  - check MAX_RECORDS in list commands
  - colortext columns exclusion
  - list commands with render per page
  - Rm netaddr
  - Remove passlib dep
  - Packages files
  - Remove unused libraries
  - Update manifest
  - compute_zone_quota_check - bugfix wrong param name and wrong value type. added a better description
  - add postgresql2 for testiting new parameters
  - adde original command in order to have both
  - added test command
  - pagination_list: if size less than -1, call API paging
  - update desc service definition
  - log for bee_client
  - Add OS mandatory param to vm load command
  - Add acronym mgmt in vm load command
* Fixed
  - Fix vsphere dfw rule get command output
  - Fix sg rule get platform command for Openstack
  - pg fix typo in extnsion parameter
  - fix tag_add_account_insts: get account
  - fix return map not array when putput is not text
  - fix tag_add_account_insts: get account

## Version 2024-08.04 (2024-08-08)

* Updated
  - Add OS mandatory param to vm load command

## Version 2024-08.03 (2024-08-07)

* Updated
  - Add acronym mgmt in vm load command

## Version 2024-08.02 (2024-08-06)

* Fixed
  - Add some checks in migration-p5p6 commands

## Version 2024-08.01 (2024-08-01)

* Added
  - map[tag:tag_add_account_insts]
  - get product codes
  - bu accounts-auth users-add-from-account
  - map[grafana:authentication with token]

## Version 2024-07.02 (2024-07-22)

* Added
  - mgmt migration-p5p6 commands
  - bu dbaas load, imports the dbaas vm into a specified container

## Version 2024-07.01 (2024-07-09)

* Fixed
  - Correct bug in create account

## Version 2024.04 (2024-04-13)
cambio logica di versionamento

* Added
  - mixed_output_handler
  - if stdout not a tty, default to old (mostly no color) output handler
  - dedicated command for account capabilities update
* Fixed
  - bugfix ip_address column for platform vsphere server list missing in output
  - correct command returning nsx edge load balancers configuration
* Updated
  - make 'type' param mandatory in staas efs add command

## Version 1.16.0 ()

* Added
  - Vsphere vms clone
  - Account existence control
  - CLI exit code
  - Account add/update new fields: account_type, management_model, pods

* Fixed
  - fix creating sqlserver using storage param
  - fix wait creating internet gateway

## Version 1.15.0 ()

* Added
  - warning when importing all lb in nsx edge
  - clear cache
  - zabbix management
  - monitoring alert management
  - ontap platform
  - command to load resource volume on service
* Fixed
  - load balancer import
  - refactoring imports
  - some descriptions and messages
  - fix wait for task
  - bash completion
  - options when creatings security group

## Version 1.14.0 ()

* Added
  - ssh gateway improvement
  - hypervisor and creation date infos to list-all vms
  - ssh nodes as inventory in JSON format
  - session set permission by role
  - veeam platform backup management
  - load balancer improvements
  - utility for metadata updating of databases as a service
* Fixed
  - Load balancer updates and reworks
  - Ssh Gateway updates and reworks
  - list-all vm counter
  - minor fixes

## Version 1.13.0 ()

* Added
  - Get hostname using socket library
  - shh keys export to file
  - ssh key hide export
  - ask command
  - grafana filter dashboard per folder
  - monitoring as a service dashboard copy
  - logging as a service management
  - ssh gateway management
  - some improvement on query openstack platform
* Fixed
  - volume migrate and volume api extensions
  - add_oracle method
  - monitoring fix sync users
  - elasticsearch upgrade
  - other minor fixes
  - Pass number of vms to look for in list_all method
  - deprecated cpaas enable/disable monitoring/logging
  - fix cancellazione internet gateway
  - add compute instance quota
  - miglior output in caso di data None
  - ssh gateway api first commit

## Version 1.12.0 ()

* Added
  - refresh vm state
  - monitor as a service management
  - Add command to refresh vm state
  - Add filter by account in compute tag list
  - add check in instance add for openstack host_group
  - add print cpaas instance list with host info
  - Add cmds to start/stop nsx edge lb
  - add security group in rule list
  - add auth perms get-method
  - Add load balancer health monitor cli business commands
  - Support for oracle 12EE
* Fixed
  - graphana protocolo connection
  - curl description
  - Openstack flavor creation made by customization
  - Vms load command
  - Reworked add methods for nsx edge monitor and app profile
  - Minor changes on vsphere nsx network edge load balancer platform cmds
  - Draft of network edge load balancer plugin vsphere cmds
  - Update nsx edge paltform commands
  - Update vsphere nsx edge load balancer platform cmds

## Version 1.11.0 (2022-10-11)

* Added
  - add grafana platform management
  - add kibana platform management
  - add bu.maas commands
  - add bu.logaas commands

## Version 1.9.0 (2022-02-11)

* Added
  - add command account definitions-get in order to get the service definition available for the account
  - add param options in dbaas db instances add
  - add command provider.site_network_subnet_add
  - add openstack aggregates and flavor extra spec in openstack platform section
  - add bu.service-insts patch command
  - add bu.cpaas.vms get-console command
  - add ssh.nodes admin-password-set and admin-password-get commands to get and set admin password
  - add platform.vsphere.dfw_section_add command to create dfw section
  - add bu.cpaas.vms commands to manage virtual machine backup and restore
  - add command platform.openstack project-quota-set
  - add zabbix platform proxy management
  - add graphite section
  - add command router_rewrite_routes in openstack platform to rewrite wrong route rules
* Fixed
  - fixed bug in SecurityGroup rule representation when protocol is icmp
  - big performance optimization
* Updated
  - update bash completion reference file
  - update redis get command to support list
  - add redis ping cmp ping
  - update bu capabilities and account capabilities to support account definitions

## Version 1.8.0 (2021-06-11)

* Added
  - add db instance method start, stop, reboot
  - add db instance database method database_get, database_add, database_del
  - add db instance database method user_get, user_add, user_del, user_priv_grant, user_priv_revoke, user_password_set
  - add cmp command runtime_api_spec to get openapi spec for cmp subsystem
  - add cmp ssh ops command check_disk_rw
* Updated
  - account delete command now permit defining if remove child services

## Version 1.7.0 (2021-05-03)

* Added
  - add commands dbaas_check_dd, dbaas_umount_dd, dbaas_mount_dd in section ssh.ops to manage mount and umount of datadomain nfs share used for logical dbaas backup
  - add commands in platform redis to manage redis with sentinel
  - add business compute instance methods to reboot, enable logging, enable monitorig
  - add group management method to awx section
  - add business internet gateway methods to manage bastion
  - add new platform check to nsx controller and components
  - add new section platform.cmp.logs2 to read log from new cmp elastic index
  - add awx ad_hoc_command section
  - add stack sql methods: get_dbs and get_users

  - add server group management in openstack platform client
* Fixed
  - renamed schema in db in platform mariadb

## Version 1.6.0 (2021-03-01)

* Added
  - add platform virsh section that map libvirt client
  - add openstack paltform volume metadata and image metadata management
  - add openstack platform command sys_compute_hypervisor_servers
  - add openstack platform command servers_migrate, security_group_add, security_group_update
  - add DynamicOutputHandler to manage dinamic table in data rendering
  - add platform mysql commands binary_log_show and binary_log_purge
  - add provider instance methods to manage internal user
  - add business compute instance methods to manage internal user
  - add business compute customization
  - add node connection using another node as ssh gateway
  - add filters to cpaas vms list
* Fixed
  - update of remote shell console now was made with rsync
* Updated
  - update section platform console to add some commands
  - integrated BeehiveApiClient method set_endpoints to set endpoints manually from config
  - update section cmp with access to k8s deploy
  - integrated node connect using password
  - integrated beedrones cmp api client

## Version 1.5.0 (2020-12-03)

* Added
  - add openstack trilio platform section
  - add ping commando to openstack section
  - add platform k8s section
  - add section data quality
  - add service instance check command
  - add provider section instance_add command
  - add command to check all platform items
* Updated
  - update section platform console to better manage remote console and users

## Version 1.4.0 (2020-10-23)

* Added
  - add openstack share network command
  - add openstack share server command
  - add openstack resource command for shares
  - add resource entities command cache_get and cache_del
  - add section for trilio
* Fixed
  - removed print of uuid in openstack resources
  - fixed provider resource command for shares
* Updated
  - integrated render of tabular data with color in state and status
  - integrated staas efs api param PerformanceMode used to manage share based on netapp and new share base on local openstack server

## Version 1.3.0 (2020-10-02)

* Added
  - added list of ipv4 ip in vsphere server get and list
  - add provider stack and sql stack commands
  - add openstack server command to add/remove security group
  - add vsphere server command to add/remove security group
  - add native openstack volume command to manage volume snapshot, volume group, volume group snapshot
  - add native vsphere volume command to manage volume snapshot, volume group, volume group snapshot
  - add openstack volume command to add/remove volume snapshot
  - add openstack share-type-get command
  - add vsphere server command to add/remove/revert snapshot
  - add provider instance command to add/remove/revert snapshot
  - add business instance command to add/remove security group
  - add business instance command to add/remove/revert snapshots
* Fixed
  - fixed applied_customization_add
  - manage better openstack volume attachment

## Version 1.2.0 (2020-09-22)

* Added
  - added plugin system for customize
  - added command cpaas.images add, type, get, delete
* Fixed
  - command to make cmp subsystem create
  - post install renamed in costomize
  - correct command encrypt and decrypt
  - fixed cmp subsystem update without ansible playbook
  - correct bug in staas grant_delete
* Updated
  - delete of auth tokens now permits delete of all active tokens
  - added list of ports in openstack subnet get

## Version 1.2.0 (2020-08-17)

* Added
  - command to manage business internet network gateway
  - extended layout of nsx edge get command
  - added nsx edge method for syslog
  - added nsx edge method for sslvpn

## Version 1.1.0 (2020-08-17)

* Added
  - command to manage remote shell console users
  - command to show platform hosts from ansible
  - provider commands for gateway
  - some fields in list o business capabilities
  - bash completion
* Fixed
  - correct bug over appengine list
  - correct filter in netaas subnet list command
  - correct command result of res_provider rule_add

## Version 1.0.0 ((Jun 21, 2020))
First production release.


## Version 0.1.0 (2019-09-27)
First private preview release. Start porting from python 2.7 release.

