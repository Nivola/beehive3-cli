# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from json import loads
from ipaddress import ip_address, ip_network
from cement.ext.ext_argparse import ex
from beehive3_cli.core.controller import ARGS
from beecell.types.type_dict import dict_get
from beecell.types.type_id import is_name, is_uuid
from beecell.types.type_string import str2bool
from beecell.types.type_ip import ip2cidr
from .child import AdminChildController, AdminError


class LoadBalancerAdminController(AdminChildController):
    class Meta:
        label = "loadbalancers"
        description = "loadbalancer administration commands"
        help = "loadbalancer administration commands"

    default_listeners = ["default_tcp_profile", "default_http_profile", "default_https_profile"]

    default_health_monitors = ["default_tcp_monitor", "default_http_monitor", "default_https_monitor"]

    template_mapping = {
        "internet": "internet",
        "internet2": "internet2",
        "web": "frontend",
        "be": "backend",
        "be2": "backend2",
    }

    deployment_envs = ["prod", "preprod", "stage", "test"]
    tag_prefix = "edge_"

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)

        self.lb_template = None
        self.private_master_subnet = None
        self.interpod_subnet = None
        self.uplink_vnic = None

    def check_appliance(self, appl_id):
        """Check whether the network appliance is supported and thus the import is possible

        :param appl_id: network appliance id
        :return:
        """
        res = self.api.resource.entity.get(appl_id)
        res = res.get("resource", {})
        objdef = dict_get(res, "__meta__.definition")
        objdef = objdef.rsplit(".", 1)[-1]
        objdef = objdef.lower()
        if "nsx" not in objdef and "edge" not in objdef:
            raise AdminError("Only import from vsphere nsx edge is supported for the time")

    def get_appliance_config(self, appl_id):
        """Get network appliance configuration

        :param appl_id: network appliance id
        """
        print("gathering information ...")
        self.appl_cfg = self.api.resource.vsphere.nsx_edge.get(appl_id)
        tags = self.get_tags(appl_id)

        self.lb_data["network_appliance"] = {
            "type": "vsphere",
            "uuid": self.appl_cfg.get("uuid"),
            "name": self.appl_cfg.get("name"),
            "ext_id": dict_get(self.appl_cfg, "details.id"),
            "tags": tags,
        }

    def get_load_balancer_data(self):
        """

        :return:
        """
        # get load balancer configuration
        self.load_balancer = dict_get(self.appl_cfg, "details.features.loadBalancer")

        # get global configuration
        self.lb_data.update(
            {
                "global": {
                    "enabled": self.load_balancer.get("enabled", True),
                    "acceleration": self.load_balancer.get("accelerationEnabled", False),
                    "logging": {
                        "enabled": dict_get(self.load_balancer, "logging.enable"),
                        "log_level": dict_get(self.load_balancer, "logging.logLevel"),
                    },
                }
            }
        )

        # get virtual servers
        self.virtual_servers = self.get_nested_data("virtualServer")

        # get listeners
        self.listeners = self.get_nested_data("applicationProfile")
        self.is_predefined(self.listeners, LoadBalancerAdminController.default_listeners)

        # get target groups
        self.target_groups = self.get_nested_data("pool")

        # get health monitors
        self.health_monitors = self.get_nested_data("monitor")
        self.is_predefined(self.health_monitors, LoadBalancerAdminController.default_health_monitors)

        # get application rules
        self.application_rules = self.get_nested_data("applicationRule")

    def get_private_master_subnet(self):
        """Get /21 private subnet

        :return:
        """
        # get private vpc id
        attachment_set = self.internet_gateway.get("attachmentSet")
        if not isinstance(attachment_set, list):
            attachment_set = [attachment_set]
        private_vpc_id = dict_get(attachment_set[0], "VpcSecurityGroupMembership.vpcId")
        # get private vpc
        private_vpc = self.api.business.netaas.vpc.get(private_vpc_id)
        # get cidr
        cidr = private_vpc.get("cidrBlock")
        self.private_master_subnet = cidr

    def get_interpod_subnet(self):
        """Get interpod subnet

        :return:
        """
        # get internet gateway service instance
        service_inst = self.api.business.service.instance.get(self.internet_gateway.get("internetGatewayId"))
        resource_uuid = dict_get(service_inst, "serviceinst.resource_uuid")
        # get resource
        gateway = self.api.resource.provider.gateway.get(resource_uuid)
        # get interpod vpc
        interpod_vpc = dict_get(gateway, "vpc.transport")
        if interpod_vpc is None:
            raise AdminError("Interpod vpc not found")
        if not isinstance(interpod_vpc, list):
            interpod_vpc = [interpod_vpc]
        if len(interpod_vpc) != 1:
            raise AdminError("Interpod vpc is not unique")
        interpod_vpc = interpod_vpc[0]
        # get cidr
        cidr = interpod_vpc.get("cidr")
        self.interpod_subnet = cidr

    def get_uplink_vnic(self, ip_addr):
        """Get configuration of uplink vnic connected to ext internet subnet

        :return:
        """
        vnics = self.api.resource.vsphere.nsx_edge.get_vnics(self.appl_cfg, vnic_type="uplink")
        uplink_vnic = None
        for vnic in vnics:
            primary_ip = dict_get(vnic, "addressGroups.addressGroup.primaryAddress")
            prefix = dict_get(vnic, "addressGroups.addressGroup.subnetPrefixLength")
            if ip_address(ip_addr) in ip_network(f"{primary_ip}/{prefix}", False):
                uplink_vnic = vnic
                break
        if uplink_vnic is None:
            raise AdminError("Uplink vnic connected to ext internet subnet not found, import failed")
        self.uplink_vnic = uplink_vnic
        self.lb_data["vnic"].update(
            {
                "uplink": {
                    "index": uplink_vnic.get("index"),
                    "primary_ip": primary_ip,
                    "prefix": prefix,
                    "portgroup_name": uplink_vnic.get("portgroupName"),
                }
            }
        )

    def get_fw_rules(self):
        """

        :return:
        """
        res = dict_get(self.appl_cfg, "details.features.firewall.firewallRules.firewallRule")
        if not isinstance(res, list):
            res = [res]
        self.fw_rules = res
        self.lb_data["fw_rules"] = {}

    def discover_any2lb_fw_rule(self):
        """

        :return:
        """
        # get load balancer ip address
        lb_ip = dict_get(self.lb_data, "virtual_server.ipAddress")

        # discover rule
        fw_rule = None
        for item in self.fw_rules:
            rule_type = item.get("ruleType")
            action = item.get("action")
            direction = item.get("direction", "in")
            src_ip = dict_get(item, "source.ipAddress", default="any")
            if not (rule_type == "user" and action == "accept" and direction == "in" and src_ip == "any"):
                continue
            dst_ips = dict_get(item, "destination.ipAddress")
            if dst_ips is None:
                continue
            if not isinstance(dst_ips, list):
                dst_ips = [dst_ips]
            found = False
            for dst_ip in dst_ips:
                cidr = ip2cidr(dst_ip)
                if ip_address(lb_ip) in ip_network(cidr):
                    found = True
                    break
            if found:
                # check if the discovered firewall rule is shared or not
                shared_rule = True
                if len(dst_ips) == 1:
                    service = dict_get(item, "application.service")
                    if not isinstance(service, list):
                        service = [service]
                    if len(service) == 1:
                        shared_rule = False
                item["is_shared"] = shared_rule
                fw_rule = item
                break

        if fw_rule is None:
            raise AdminError("any2lb firewall rule not found")
        print("discovered any2lb fw rule: %s" % fw_rule.get("id"))
        self.lb_data["fw_rules"].update({"any2lb": fw_rule})

    def discover_edge2backend_fw_rule(self):
        """

        :return:
        """
        fw_rule = None
        if self.private is False:
            # get balanced ip addresses
            balanced_ips = []
            balanced_targets = dict_get(self.lb_data, "target_group.member")
            if balanced_targets is None:
                balanced_targets = []
            if not isinstance(balanced_targets, list):
                balanced_targets = [balanced_targets]
            for item in balanced_targets:
                balanced_ips.append(item.get("ipAddress"))

            # get uplink vinc primary ip address
            primary_ip = dict_get(self.uplink_vnic, "addressGroups.addressGroup.primaryAddress")

            # discover rule
            for item in self.fw_rules:
                shared_rule = False
                rule_type = item.get("ruleType")
                direction = item.get("direction", "in")
                action = item.get("action")
                if not (rule_type == "user" and action == "accept" and direction == "in"):
                    continue
                src_ips = dict_get(item, "source.ipAddress")
                if src_ips is None or src_ips == "any":
                    continue
                if not isinstance(src_ips, list):
                    src_ips = [src_ips]
                if len(src_ips) > 1:
                    shared_rule = True
                src_found = False
                for src_ip in src_ips:
                    src_cidr = ip2cidr(src_ip)
                    if ip_address(primary_ip) in ip_network(src_cidr):
                        src_found = True
                if not src_found:
                    continue
                if src_found and not balanced_targets:
                    item["is_shared"] = shared_rule
                    fw_rule = item
                    break
                dst_ips = dict_get(item, "destination.ipAddress")
                if dst_ips is None:
                    continue
                if not isinstance(dst_ips, list):
                    dst_ips = [dst_ips]
                matched_ips = []
                dst_found = False
                for balanced_ip in balanced_ips:
                    for dst_ip in dst_ips:
                        dst_cidr = ip2cidr(dst_ip)
                        if shared_rule is False and dst_cidr.split("/")[1] != "32":
                            shared_rule = True
                        if ip_address(balanced_ip) in ip_network(dst_cidr):
                            dst_found = True
                            break
                    if not dst_found:
                        break
                    matched_ips.append(balanced_ip)
                if set(matched_ips) == set(balanced_ips):
                    if shared_rule is True:
                        pass
                    elif len(matched_ips) != len(dst_ips):
                        shared_rule = True
                    else:
                        service = dict_get(item, "application.service")
                        if service is None:
                            shared_rule = True
                            if not isinstance(service, list):
                                service = [service]
                            if len(service) == 1:
                                shared_rule = True
                    item["is_shared"] = shared_rule
                    fw_rule = item
                    break
        else:
            # discover rule
            found = False
            for item in self.fw_rules:
                rule_type = item.get("ruleType")
                action = item.get("action")
                direction = item.get("direction", "in")
                if not (rule_type == "user" and action == "accept" and direction == "in"):
                    continue
                src_ips = dict_get(item, "source.ipAddress")
                if src_ips is None or src_ips == "any":
                    continue
                if not isinstance(src_ips, list):
                    src_ips = [src_ips]
                for src_ip in src_ips:
                    cidr = ip2cidr(src_ip)
                    if cidr in [self.private_master_subnet]:
                        found = True
                        break
                if found:
                    item["is_shared"] = True
                    fw_rule = item
                    break
        if fw_rule is None:
            raise AdminError("edge2backend firewall rule not found")
        print("discovered edge2backend fw rule: %s" % fw_rule.get("id"))
        self.lb_data["fw_rules"].update({"edge2backend": fw_rule})

    def discover_interpod_fw_rule(self):
        """

        :return:
        """
        fw_rule = None
        found = False
        for item in self.fw_rules:
            rule_type = item.get("ruleType")
            action = item.get("action")
            direction = item.get("direction", "in")
            if not (rule_type == "user" and action == "accept" and direction == "in"):
                continue
            src_ips = dict_get(item, "source.ipAddress")
            if src_ips is None or src_ips == "any":
                continue
            if not isinstance(src_ips, list):
                src_ips = [src_ips]
            for src_ip in src_ips:
                cidr = ip2cidr(src_ip)
                if cidr in [self.interpod_subnet]:
                    found = True
                    break
            if found:
                item["is_shared"] = True
                fw_rule = item
                break
        if fw_rule is None:
            print("interpod fw rule not found")
        else:
            print(f"discovered interpod fw rule: {fw_rule.get('id')}")
            self.lb_data["fw_rules"].update({"interpod": fw_rule})

    def discover_fw_rules(self):
        """

        :return:
        """
        print("discovering firewall rules ...")
        # - any2lb
        self.discover_any2lb_fw_rule()
        # - edge2backend
        self.discover_edge2backend_fw_rule()
        # - interpod
        if self.interpod_subnet is not None:
            self.discover_interpod_fw_rule()

    @staticmethod
    def is_predefined(items, default_items):
        """Check whether a load balancer component item (i.e. health monitor, listener, target group,
           application rule) is predefined or not

        :param items: list of load balancer component items (for example, a list of listeners)
        :param default_items: list of predefined load balancer component items
        :return:
        """
        for v in items.values():
            v["predefined"] = False
            if v["name"] in default_items:
                v["predefined"] = True

    def get_nested_data(self, key):
        """

        :param key:
        :return:
        """
        items = self.load_balancer.pop(key, [])
        if not isinstance(items, list):
            items = [items]
        key = key + "Id"
        return {item.get(key): item for item in items}

    def check_and_organize(self, account=None, virtual_server=None):
        """

        :param account: account uuid
        :param virtual_server: virtual server name
        :return:
        """
        reorganized = []
        for k, v in self.virtual_servers.items():
            d = {}

            # - account and virtual server
            desc = v.get("description", {})
            # manage the case the virtual server description is not a JSON with the triplet org.div.account
            try:
                desc = loads(desc)
            except:
                continue
            account_triplet = desc.get("account")
            is_vip_static = desc.get("is_vip_static", False)
            if account_triplet is None:
                raise AdminError("Unable to get account in virtual server %s" % k)
            res = self.get_account(account_triplet)
            account_id = res["uuid"]
            if account is not None and account != account_id:
                continue
            if virtual_server is not None and virtual_server != v.get("name"):
                continue
            d["account"] = account_id
            d["virtual_server"] = v
            d["virtual_server"]["is_vip_static"] = is_vip_static

            # - listener
            listener_id = v.get("applicationProfileId")
            if listener_id is not None:
                d["listener"] = self.listeners[listener_id]

            # - target group
            target_group_id = v.get("defaultPoolId")
            if target_group_id is not None:
                d["target_group"] = self.target_groups[target_group_id]

            # - health monitor
            if target_group_id is not None:
                health_monitor_id = self.target_groups[target_group_id].get("monitorId")
                if health_monitor_id is not None:
                    d["health_monitor"] = self.health_monitors[health_monitor_id]

            # - application rule
            app_rule_id = v.get("applicationRuleId")
            if app_rule_id is not None:
                d["app_rule"] = self.application_rules[app_rule_id]

            reorganized.append(d)
        return reorganized

    def import_res_load_balancer(self):
        """

        :return:
        """
        print("importing resources ...")

        # get target group members
        target_group = self.lb_data.get("target_group")
        if target_group is None:
            raise AdminError("target group not defined, import failed")
        members = target_group.get("member", [])
        if not isinstance(members, list):
            members = [members]
        if len(members) == 0:
            raise AdminError("empty target group, import failed")

        # get site network
        pg_name = dict_get(self.lb_data, "vnic.uplink.portgroup_name")
        pg_name = pg_name[::-1]
        splits = pg_name.split("-", 2)
        if len(splits) != 3:
            raise AdminError("unable to get site network, import failed")
        site_network_name = splits[2]
        site_network_name = site_network_name[::-1]
        res = self.api.resource.provider.site_network.get(site_network_name)
        site_network_id = res.get("id")

        # get compute zone
        data = {"account_id": self.account, "flag_container": True, "plugintype": "NetworkService"}
        srv_instances = self.api.business.service.instance.list(**data).get("serviceinsts")
        srv_instance = srv_instances[0]
        compute_zone = srv_instance.get("resource_uuid")

        # get instance resource id
        for member in members:
            member: dict
            data = {"accounts": self.account, "name": member.get("name"), "size": -1}
            instances = self.api.business.cpaas.instance.list(**data).get("instances")
            if len(instances) == 0:
                raise AdminError("cpaas instance not found, import failed")
            instance = instances[0]
            resource_id = instance.get("nvl-resourceId")
            member["resource_uuid"] = resource_id

        virtual_server = self.lb_data.get("virtual_server")
        res_name = virtual_server.get("name")
        res_params = {"compute_zone": compute_zone, "site_network": site_network_id}
        res_params.update(self.lb_data)
        resource_id = self.api.resource.provider.load_balancer.load("ResourceProvider01", res_name, **res_params)
        return resource_id

    def check_private(self):
        """Determine whether an account is private or not checking the presence of the internet gateway
           among its services.

        :return: True or False
        """
        internet_gateways = self.api.business.netaas.internet_gateway.list(accounts=self.account)
        if not internet_gateways:
            return False
        if len(internet_gateways) == 1:
            self.internet_gateway = internet_gateways[0]
            return True
        if len(internet_gateways) > 1:
            raise AdminError(f"Account {self.account} with more than an internet gateway")

    def check_account(self):
        """

        :return:
        """
        print("getting account ...")
        self.account = self.lb_data.pop("account", None)
        self.private = self.check_private()
        print(f"account: {self.account}, {'' if self.private is True else 'not '}private")

    def get_subnets(self):
        """

        :return:
        """
        if self.private is True:
            if self.private_master_subnet is None:
                self.get_private_master_subnet()
            # print(f"private_master_subnet={self.private_master_subnet}")
            if not self.interpod_subnet:
                self.get_interpod_subnet()
            # print(f"interpod_subnet={self.interpod_subnet}")

    def get_network_config(self):
        """

        :return:
        """
        print("getting network configuration ...")
        self.lb_data["vnic"] = {}
        self.get_subnets()
        if self.uplink_vnic is None:
            vs_ip_addr = dict_get(self.lb_data, "virtual_server.ipAddress")
            self.get_uplink_vnic(vs_ip_addr)
        else:
            self.lb_data["vnic"].update(
                {
                    "uplink": {
                        "index": self.uplink_vnic.get("index"),
                        "primary_ip": self.uplink_vnic.get("addressGroups.addressGroup.primaryAddress"),
                        "prefix": self.uplink_vnic.get("addressGroups.addressGroup.subnetPrefixLength"),
                        "portgroup_name": self.uplink_vnic.get("portgroupName"),
                    }
                }
            )

    def import_srv_health_monitor(self):
        """Import health monitor as service instance

        :return: health monitor id
        """
        hm_data = self.lb_data.get("health_monitor")
        # health monitor not defined
        if hm_data is None:
            return None
        hm_predefined = hm_data.get("predefined")
        # select predefined health monitor
        if hm_predefined is True:
            hm_protocol = hm_data.get("type").lower()
            res = self.api.business.netaas.health_monitor.list(self.account, **hm_data)
            health_monitors = res.get("healthMonitorSet")
            health_monitor = [
                item
                for item in health_monitors
                if item.get("protocol").lower() == hm_protocol and item.get("predefined") == hm_predefined
            ]
            health_monitor = health_monitor[0]
            hm_id = health_monitor.get("healthMonitorId")
            print("select predefined health monitor: %s" % hm_id)
        # import custom health monitor
        else:
            hm_id = self.api.business.netaas.health_monitor.load(self.account, **hm_data)
        return hm_id

    def import_srv_target_group(self, hm_id):
        """Import target group as service instance

        :param hm_id: health monitor id
        :return: target group id
        """
        tg_data = self.lb_data.get("target_group")
        if tg_data is None:
            raise AdminError("target group not defined, import failed")
        tg_data["health_monitor"] = hm_id
        tg_id = self.api.business.netaas.target_group.load(self.account, **tg_data)
        return tg_id

    def register_targets(self, tg_id):
        """Register targets with target group

        :param tg_id: target group id
        :return: list of registered targets
        """
        t_ids = []
        if tg_id is not None:
            members = dict_get(self.lb_data, "target_group.member", default=[])
            t_ids = self.api.business.netaas.target_group.register_targets(self.account, tg_id, members)
        return t_ids

    def import_srv_listener(self):
        """Import listener as service instance

        :return: listener id
        """
        li_data = self.lb_data.get("listener")
        if li_data is None:
            raise AdminError("listener not defined, import failed")
        li_predefined = li_data.get("predefined")
        from beehive3_cli.plugins.business.controllers.netaas import ListenerNetServiceController

        li_traffic_type = ListenerNetServiceController.get_traffic_type(**li_data)
        # select predefined listener
        if li_predefined is True:
            res = self.api.business.netaas.listener.list(self.account)
            listeners = res.get("listenerSet")
            listener = [
                item
                for item in listeners
                if item.get("trafficType").lower() == li_traffic_type and item.get("predefined") == li_predefined
            ]
            listener = listener[0]
            li_id = listener.get("listenerId")
            print("select predefined listener: %s" % li_id)
        # import custom listener
        else:
            li_data["template"] = li_traffic_type
            li_id = self.api.business.netaas.listener.load(self.account, **li_data)
        return li_id

    def import_srv_load_balancer(self, listener, target_group, compute_resource):
        """Import load balancer (also called virtual server) as service instance

        :param listener: service instance listener id
        :param target_group: service instance target group id
        :param compute_resource: compute resource id
        :return: virtual server id
        """
        self.get_deployment_environment()
        lb_data = self.lb_data.get("virtual_server")
        if lb_data is None:
            raise AdminError("virtual server not defined, import failed")
        lb_data["listener"] = listener
        lb_data["target_group"] = target_group
        lb_data["resource_id"] = compute_resource
        lb_id = self.api.business.netaas.load_balancer.load(self.account, **lb_data)
        return lb_id

    def import_srv_instances(self, resource_id):
        """Import service instances composing load balancer

        :param resource_id: compute resource id
        :return:
        """
        print("importing service instances ...")

        # - import health monitor
        hm_id = self.import_srv_health_monitor()

        # - import target group
        tg_id = self.import_srv_target_group(hm_id)

        # - register targets if any
        targets_id = self.register_targets(tg_id)

        # - import listener
        li_id = self.import_srv_listener()

        # - import load balancer
        lb_id = self.import_srv_load_balancer(li_id, tg_id, resource_id)

    def get_lb_template(self):
        """

        :return:
        """
        dvpg = dict_get(self.lb_data, "vnic.uplink.portgroup_name", default="").lower()
        for k, v in LoadBalancerAdminController.template_mapping.items():
            if k in dvpg:
                template = f"loadbalancer-{v}{'-private' if self.private is True else ''}"
                return template
        return None

    def get_deployment_environment(self):
        """Get environment where projects are deployed from nsx edge tags

        :return:
        """
        tags = dict_get(self.lb_data, "network_appliance.tags")
        deployment_env = None
        for tag in tags:
            name = tag.get("name")
            tag_prefix = LoadBalancerAdminController.tag_prefix
            if name.startswith(tag_prefix):
                env = name[len(tag_prefix) :]
                if env in LoadBalancerAdminController.deployment_envs:
                    deployment_env = env
                    break
        self.lb_data["virtual_server"].update({"deployment_env": deployment_env})

    def get_tags(self, oid):
        """

        :return:
        """
        return self.api.resource.tag.list(resource=oid).get("resourcetags")

    @ex(
        help="import load balancer",
        description="import load balancer",
        arguments=ARGS(
            [
                (["appliance"], {"help": "network appliance (e.g. nsx edge) uuid", "action": "store", "type": str}),
                (
                    ["-account"],
                    {
                        "help": "the uuid of the account owner of the virtual server(s) to import",
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["-virtual-server"],
                    {
                        "help": "the name of the virtual server to import",
                        "action": "store",
                        "type": str,
                        "dest": "virtual_server",
                    },
                ),
            ]
        ),
    )
    def load(self):
        appl_uuid = self.app.pargs.appliance
        account_uuid = self.app.pargs.account
        vs_name = self.app.pargs.virtual_server

        go_ahead = True
        if account_uuid is None and vs_name is None:
            s1 = "WARNING: You are about to import ALL load balancer configured on network appliance %s\n" % appl_uuid
            s2 = "Use -account or -virtual_server options to narrow the amount of imports\n"
            s3 = "Are you sure to proceed? [y/n] "
            PROMPT_ASK_CONFIRM = s1 + s2 + s3
            check = self.ask(PROMPT_ASK_CONFIRM, yn=True)
            print()
            if check == "N":
                go_ahead = False

        if go_ahead:
            if not is_uuid(appl_uuid):
                raise AdminError("Network appliance input param is not a valid uuid")
            if account_uuid is not None and vs_name is not None:
                raise AdminError("Account and virtual server filters cannot be used together")
            if account_uuid is not None and not is_uuid(account_uuid):
                raise AdminError("Account param is not a valid uuid")
            if vs_name is not None and not is_name(vs_name):
                raise AdminError("Virtual server param is not a valid name")

            # check network appliance
            self.check_appliance(appl_uuid)

            self.lb_data = {}

            # get network appliance configuration
            self.get_appliance_config(appl_uuid)

            # get load balancer configuration
            self.get_load_balancer_data()

            # get firewall rules
            self.get_fw_rules()

            # reorganize data
            items = self.check_and_organize(account=account_uuid, virtual_server=vs_name)
            if not items:
                print("nothing to import")
            else:
                for item in items:
                    self.lb_data.update(item)

                    # get account
                    self.check_account()

                    # get network configuration
                    self.get_network_config()

                    # get load balancer template
                    self.lb_template = self.get_lb_template()
                    self.lb_data["virtual_server"].update({"template": self.lb_template})

                    # discover firewall rules related to load balancer
                    self.discover_fw_rules()

                    # import resources
                    resource_id = self.import_res_load_balancer()

                    # import service instances
                    self.import_srv_instances(resource_id)
                print("end")

    @ex(
        help="delete load balancer",
        description="delete load balancer",
        arguments=ARGS(
            [
                (["id"], {"help": "load balancer id", "action": "store", "type": str}),
                (
                    ["-no-linked-objs"],
                    {
                        "help": "Use this option to avoid deleting service instances like target group and custom "
                        "listener linked to load balancer",
                        "action": "store_true",
                        "dest": "no_linked_objs",
                    },
                ),
                (
                    ["-no-physical-resources"],
                    {
                        "help": "Use this option to delete only CMP metadata without deleting physical resources",
                        "action": "store_true",
                        "dest": "no_physical_resources",
                    },
                ),
            ]
        ),
    )
    def delete(self):
        lb_uuid = self.app.pargs.id
        no_linked_objs = self.app.pargs.no_linked_objs
        no_physical_res = self.app.pargs.no_physical_resources

        go_ahead = True
        s1 = "WARNING: You are about to delete load balancer %s\n" % lb_uuid
        s2 = "Use -no-physical-resources option to delete CMP metadata only, without deleting physical resources\n"
        s3 = (
            "Use -no-linked-objs option to delete load balancer without deleting target group and custom listener "
            "linked to it\n"
        )
        s4 = "Are you sure to proceed? [y/n] "
        PROMPT_ASK_CONFIRM = s1 + s2 + s3 + s4
        check = self.ask(PROMPT_ASK_CONFIRM, yn=True)
        print()
        if check == "N":
            go_ahead = False

        if go_ahead:
            if no_linked_objs is True and no_physical_res is True:
                raise AdminError("-no-linked-objs and -no-physical-resources options cannot be used together")

            print("gathering information ...")
            # - get compute lb uuid from service lb details
            lb_cfg = self.api.business.netaas.load_balancer.get(lb_uuid)
            res_compute_lb_id = lb_cfg.get("nvl-resourceId")

            srv_inst_cfg = self.api.business.service.instance.get(lb_uuid)
            lb_id = srv_inst_cfg.get("serviceinst").get("id")

            if no_physical_res is False:
                # delete netaas load balancer
                print(f"deleting service load balancer {lb_uuid} ...")
                self.api.business.netaas.load_balancer.delete(lb_id, no_linked_objs)
                print(f"service load balancer {lb_uuid} deleted")
            else:
                # get compute lb details
                res_compute_lb_cfg = self.api.resource.provider.load_balancer.get(res_compute_lb_id)

                # get zone lb from entities linked to compute lb
                linked_entities = self.api.resource.entity.get_linked_entities(res_compute_lb_id).get("resources")
                if len(linked_entities) == 0:
                    avz = dict_get(res_compute_lb_cfg, "availability_zone.name")
                    raise AdminError(f"load balancer in availability zone {avz} not found")
                res_zn_lb_cfg = linked_entities[0]
                res_zn_lb_id = res_zn_lb_cfg.get("uuid")

                # reset zone load balancer attributes
                print(f"updating resource zone load balancer {res_zn_lb_id} ...")
                self.api.resource.entity.update(res_zn_lb_id, attribute={})
                print(f"resource zone load balancer {res_zn_lb_id} updated")

                # delete zone load balancer
                print(f"deleting resource zone load balancer {res_zn_lb_id} ...")
                self.api.resource.entity.delete(res_zn_lb_id)
                print(f"resource zone load balancer {res_zn_lb_id} deleted")

                # delete compute load balancer
                print(f"deleting resource compute load balancer {res_compute_lb_id} ...")
                self.api.resource.entity.delete(res_compute_lb_id)
                print(f"resource compute load balancer {res_compute_lb_id} deleted")

                # get service links:
                # - between lb and li
                li_srv_link_id, li_id = self.api.business.netaas.load_balancer.get_listener(lb_id)
                # - between lb and tg
                tg_srv_link_id, tg_id = self.api.business.netaas.load_balancer.get_target_group(lb_id)
                # # - between tg and t
                # data = {"type": "tg-t", "start_service": tg_id}
                # t_srv_links = self.api.business.service.link.list(**data)
                # # - between tg and hm
                # hm_srv_link_id, hm_id = self.api.business.netaas.target_group.get_health_monitor(tg_id)

                # delete service links
                print("deleting service links ...")
                self.api.business.service.link.delete(li_srv_link_id)
                self.api.business.service.link.delete(tg_srv_link_id)
                # for t_srv_link in t_srv_links:
                #     t_srv_link_id = t_srv_link.get("id")
                #     self.api.business.service.link.delete(t_srv_link_id)
                # if hm_srv_link_id is not None:
                #     self.api.business.service.link.delete(hm_srv_link_id)
                print("service links deleted")

                # delete service instances:
                # - listener
                print(f"deleting service listener {li_id} ...")
                serv_inst = self.api.business.service.instance.get(li_id).get("serviceinst")
                if str2bool(dict_get(serv_inst, "config.predefined")) is True:
                    print(f"service listener {li_id} is predefined and cannot be deleted")
                else:
                    self.api.business.service.instance.delete(li_id)
                    print(f"service listener {li_id} deleted")
                # - target group
                print(f"deleting service target group {tg_id} ...")
                self.api.business.netaas.target_group.delete(tg_id)
                print(f"service target group {tg_id} deleted")
                # # - health monitor
                # if hm_id is not None:
                #     print(f"deleting service health monitor {hm_id} ...")
                #     serv_inst = self.api.business.service.instance.get(hm_id).get("serviceinst")
                #     if str2bool(dict_get(serv_inst, "config.predefined")) is True:
                #         print(f"service health monitor {hm_id} is predefined and cannot be deleted")
                #     else:
                #         self.api.business.service.instance.delete(hm_id)
                #         print(f"service health monitor {hm_id} deleted")
                # - load balancer
                print(f"deleting service load balancer {lb_uuid} ...")
                self.api.business.service.instance.delete(lb_id)
                print(f"service load balancer {lb_uuid} deleted")
                print("end")
