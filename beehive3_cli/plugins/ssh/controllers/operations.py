# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from urllib.parse import urlencode
from cement import ex
from ujson import dumps
from beecell.types.type_dict import dict_get
from beecell.file import read_file
from beedrones.openstack.client import OpenstackManager
from beehive3_cli.core.connect import SshConnectionManager
from beehive3_cli.core.controller import PARGS
from beehive3_cli.core.util import load_environment_config, load_config
from beehive3_cli.plugins.ssh.controllers.ssh import SshControllerChild


class SshOperationController(SshControllerChild):
    class Meta:
        stacked_on = "ssh"
        stacked_type = "nested"
        label = "ops"
        description = "custom operations"
        help = "custom operations"

    def pre_command_run(self):
        super(SshOperationController, self).pre_command_run()

    def __config_openstack_client(self):
        self.config = load_environment_config(self.app)

        orchestrators = self.config.get("orchestrators", {}).get("openstack", {})
        conf = orchestrators.get(self.env)

        project = getattr(self.app.pargs, "project", None)
        if project is None:
            project = conf.get("project")
        self.client = OpenstackManager(conf.get("uri"), default_region=conf.get("region"))
        self.client.authorize(
            conf.get("user"),
            conf.get("pwd"),
            project=project,
            domain=conf.get("domain"),
            key=self.key,
        )

        self._meta.cmp = {"baseuri": "/v1.0/nrs", "subsystem": "resource"}
        self.configure_cmp_api_client()

    def __get_nodes(self):
        node_id = self.app.pargs.node
        node_name = self.app.pargs.name
        node_file = self.app.pargs.file
        size = self.app.pargs.size
        page = self.app.pargs.page
        if node_id is not None:
            uri = "%s/nodes/%s" % (self.baseuri, node_id)
            node = self.cmp_get(uri).get("node", {})
            nodes = [node]
        elif node_name is not None:
            uri = "%s/nodes" % self.baseuri
            data = {"names": node_name, "size": size, "page": page}
            nodes = self.cmp_get(uri, data=urlencode(data)).get("nodes", [])
        elif node_file is not None:
            data = read_file(node_file)
            nodes = []
            for item in data.split("\n"):
                out = item.split("  ")
                node_id = out[0]
                if node_id == "":
                    continue
                uri = "%s/nodes/%s" % (self.baseuri, node_id)
                node = self.cmp_get(uri).get("node", {})
                nodes.append(node)
        else:
            nodes = []

        return nodes

    def __node_run_cmd(self, scm, node, cmd, noresult=False):
        try:
            res = scm.sshcmd2node(node=node, user="root", cmd=cmd, timeout=30.0)
        except Exception as ex:
            res = {"stderr": str(ex)}
        status = False
        if res.get("stderr", "") != "":
            status = False
        elif len(res.get("stdout", [])) > 0 or noresult is True:
            status = True

        run_res = {"cmd": cmd, "res": res, "status": status}
        return run_res

    def __node_run_cmds(self, scm, nodes, cmds, out_file):
        resp = {}

        f = open(out_file, "w")
        for node in nodes:
            node_status = True
            node_res = []
            node_err = None
            for cmd in cmds:
                node_partial_res = self.__node_run_cmd(scm, node, cmd[0], noresult=cmd[1])
                node_res.append(node_partial_res)
                resp[node["name"]] = node_res
                if node_partial_res.get("status") is False:
                    node_status = False
                    node_err = dict_get(node_partial_res, "res.stderr")  # cmd[0]
                    break

            resp[node["name"]] = node_res
            if node_err is not None:
                print("%-60s %-18s %s: %s" % (node["name"], node["ip_address"], node_status, node_err))
            else:
                print("%-60s %-18s %s" % (node["name"], node["ip_address"], node_status))

        f.write(dumps(resp))
        f.close()

    @ex(
        help="check virtual machine boot disk is writable",
        description="check virtual machine boot disk is writable",
        arguments=PARGS(
            [
                (
                    ["-node"],
                    {
                        "help": "node id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "node name pattern",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-file"],
                    {
                        "help": "node list in a file",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def check_disk_rw(self):
        nodes = self.__get_nodes()
        scm = SshConnectionManager(self)
        cmds = [
            ("df -k", False),
            ("touch /tmp/xxxx && ls /tmp/xxxx && rm /tmp/xxxx", False),
        ]
        self.__node_run_cmds(scm, nodes, cmds, "node-check.json")

    @ex(
        help="check data domain mounted in dbaas",
        description="check data domain mounted in dbaas",
        example="beehive ssh ops dbaas-check-dd;beehive ssh ops dbaas-check-dd -name dbs -size 10",
        arguments=PARGS(
            [
                (
                    ["-node"],
                    {
                        "help": "node id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "node name pattern",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-file"],
                    {
                        "help": "node list in a file",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def dbaas_check_dd(self):
        nodes = self.__get_nodes()
        scm = SshConnectionManager(self)
        cmds = [
            ("mount | grep /bck_logici", False),
            ("ls -la /bck_logici | grep .snapshot", False),
            (
                "touch /bck_logici/xxxx && ls /bck_logici/xxxx && rm /bck_logici/xxxx",
                False,
            ),
        ]
        self.__node_run_cmds(scm, nodes, cmds, "node-check.json")

    @ex(
        help="umount data domain mounted in dbaas",
        description="umount data domain mounted in dbaas",
        arguments=PARGS(
            [
                (
                    ["-node"],
                    {
                        "help": "node id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "node name pattern",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-file"],
                    {
                        "help": "node list in a file",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def dbaas_umount_dd(self):
        nodes = self.__get_nodes()
        scm = SshConnectionManager(self)
        cmds = [
            ("cat /etc/fstab | grep /bck_logici", False),
            ("umount /bck_logici", True),
        ]
        self.__node_run_cmds(scm, nodes, cmds, "node-umount.json")

    @ex(
        help="mount data domain mounted in dbaas",
        description="mount data domain mounted in dbaas",
        arguments=PARGS(
            [
                (
                    ["-node"],
                    {
                        "help": "node id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": "node name pattern",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-file"],
                    {
                        "help": "node list in a file",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def dbaas_mount_dd(self):
        nodes = self.__get_nodes()
        scm = SshConnectionManager(self)
        cmds = [
            ("cat /etc/fstab | grep /bck_logici", False),
            ("mount -a", True),
            ("ls -la /bck_logici | grep .snapshot", False),
            (
                "touch /bck_logici/xxxx && ls /bck_logici/xxxx && rm /bck_logici/xxxx",
                False,
            ),
        ]
        self.__node_run_cmds(scm, nodes, cmds, "node-mount.json")

    @ex(
        help="show action on dbaas",
        description="show action on dbaas",
        example="beehive ssh ops dbaas-show-response node-check.json;beehive ssh ops dbaas-show-response node-check.json",
        arguments=PARGS(
            [
                (
                    ["file"],
                    {
                        "help": "response file name",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def dbaas_show_response(self):
        file = self.app.pargs.file
        res = read_file(file)
        for node, res in res.items():
            self.c(node, "underline")
            for cmd in res:
                msg = "status: %s - cmd: %s" % (cmd["status"], cmd["cmd"])
                if cmd["status"] is False:
                    msg += " - error: %s" % cmd["res"]["stderr"]
                    self.app.error(msg)
                else:
                    print(msg)
                # print('cmd: %s - status: %s - res: %s' % (cmd['cmd'], cmd['status'], cmd['res']))

    @ex(help="check volumes", description="check volumes", arguments=PARGS([]))
    def check_volume(self):
        data = load_config("/home/beehive3/volumes")
        data = data.split("\n")

        self.__config_openstack_client()

        for item in data[2:]:
            items = item.split(",")
            if items[1].find("manila") >= 0:
                continue
            if items[1].find("temp") >= 0:
                continue

            print("-----------------------")
            print("openstack --- id: %s | name: %s" % (items[0], items[1]))
            try:
                ops_volume = self.client.volume_v3.get(items[0])
            except Exception as ex:
                self.app.error(ex)
                ops_volume = None
            if ops_volume is not None:
                try:
                    uri = "/v1.0/nrs/openstack/volumes/%s" % items[1]
                    res_volume = self.cmp_get(uri).get("volume")
                    print("resource  --- id: %s | ext_id: %s" % (res_volume["id"], res_volume["ext_id"]))
                    if res_volume["ext_id"] != items[0]:
                        self.app.error("## ext_id wrong")
                    if res_volume["name"] != items[1]:
                        self.app.error("## name wrong")
                except Exception as ex:
                    self.app.error(ex)

    @ex(
        help="restore volume with ext_id and name wrong",
        description="restore volume with ext_id and name wrong",
        arguments=PARGS(
            [
                (
                    ["ext_id"],
                    {"help": "openstack volume ext_id", "action": "store", "type": str},
                ),
                (["id"], {"help": "resource id", "action": "store", "type": str}),
            ]
        ),
    )
    def restore_volume(self):
        ext_id = self.app.pargs.ext_id
        oid = self.app.pargs.id

        self.__config_openstack_client()

        uri = "/v1.0/nrs/entities/%s" % oid
        res = self.cmp_get(uri).get("resource")
        print("- resource  # name: %s | ext_id: %s" % (res["name"], res["ext_id"]))

        ops = self.client.volume_v3.get(ext_id)
        print("- openstack # name: %s | ext_id: %s" % (ops["name"], ops["id"]))

        self.client.volume_v3.update(ext_id, name=res["name"])
        print("--> update openstack")
        uri = "/v1.0/nrs/entities/%s" % oid
        res = self.cmp_put(uri, data={"resource": {"ext_id": ext_id}})
        print("--> update resource")

        uri = "/v1.0/nrs/entities/%s" % oid
        res = self.cmp_get(uri).get("resource")
        print("- resource  # name: %s | ext_id: %s" % (res["name"], res["ext_id"]))

        ops = self.client.volume_v3.get(ext_id)
        print("- openstack # name: %s | ext_id: %s" % (ops["name"], ops["id"]))

    @ex(
        help="restore vm in cmp from trilio backup",
        description="restore vm in cmp from trilio backup",
        arguments=PARGS(
            [
                (
                    ["opsvm"],
                    {"help": "openstack vm name", "action": "store", "type": str},
                ),
                (
                    ["-server"],
                    {
                        "help": "if true update ext_id from openstack server to resource",
                        "action": "store_true",
                    },
                ),
                (
                    ["-volume"],
                    {
                        "help": "if true update ext_id in volume. Syntax volume_name:ext_id",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def restore_vm(self):
        opsvm = self.app.pargs.opsvm
        restore_server = self.app.pargs.server
        restore_volume = self.app.pargs.volume

        self.__config_openstack_client()

        ope_server = self.client.server.list(name=opsvm, detail=True)
        if len(ope_server) == 1:
            ope_server = ope_server[0]
            ope_volumes = []
            for o in ope_server["os-extended-volumes:volumes_attached"]:
                v = self.client.volume.get(o["id"])
                ope_volumes.append({"id": v["id"], "size": v["size"]})

            # get server
            uri = "/v1.0/nrs/openstack/servers/%s" % opsvm
            res_server = self.cmp_get(uri).get("server")
            volumes = res_server.get("details").pop("volumes", [])
            # get volumes
            res_volumes = {}
            for v in volumes:
                uri = "/v1.0/nrs/openstack/volumes/%s" % v["name"]
                res_volume = self.cmp_get(uri).get("volume")
                res_volumes[v["name"]] = res_volume

            print("------------------------------------------------")
            print("physical openstack server")
            print(" - name: %s" % ope_server["name"])
            print(" - ext_id: %s" % ope_server["id"])
            print(" - volumes:")
            for ope_volume in ope_volumes:
                print("   - ext_id: %s, size: %s" % (ope_volume["id"], ope_volume["size"]))
            print("")
            print("cmp openstack server")
            print(" - uuid: %s" % res_server["uuid"])
            print(" - ext_id: %s" % res_server["ext_id"])
            print(" - volumes:")
            for v in volumes:
                rv = res_volumes.get(v["name"])
                print(
                    "   - ext_id: %s, id: %s, name: %s, type: %s, size: %s"
                    % (rv["ext_id"], v["id"], v["name"], v["type"], v["size"])
                )
            print("------------------------------------------------")

            if restore_server is True:
                uri = "/v1.0/nrs/entities/%s" % res_server["uuid"]
                print("\nupdate server ext_id")
                self.cmp_put(uri, data={"resource": {"ext_id": ope_server["id"]}})
            if restore_volume is not None:
                restore_volume = restore_volume.split(":")
                uri = "/v1.0/nrs/entities/%s" % restore_volume[0]
                print("\nupdate server ext_id")
                self.cmp_put(uri, data={"resource": {"ext_id": restore_volume[1]}})
        else:
            raise Exception("no server found or too much servers founds")

    @ex(
        help="assign dbaas node to dbacsi group",
        description="assign dbaas node to dbacsi group",
        arguments=PARGS(
            [
                (
                    ["-type"],
                    {
                        "help": "vm type. Can be mysql or oracle [default=mysql]",
                        "action": "store",
                        "type": str,
                        "default": "mysql",
                    },
                ),
                (
                    ["-ids"],
                    {
                        "help": "dbaas uuids",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def assign_dbaas_node_to_dbacsi(self):
        dbtype = self.app.pargs.type

        dbaas = []

        self._meta.cmp = {"baseuri": "/v1.0/nws", "subsystem": "service"}
        self.configure_cmp_api_client()

        if dbtype == "mysql":
            data_search = {}
            data_search["MaxRecords"] = self.app.pargs.size
            data_search["Marker"] = self.app.pargs.page
            ids = self.app.pargs.ids
            if ids is not None:
                data_search["db-instance-id.N"] = ids.split(",")
            uri = "%s/databaseservices/instance/describedbinstances" % self.baseuri
            res = self.cmp_get(uri, data=urlencode(data_search, doseq=True))
            res = res.get("DescribeDBInstancesResponse").get("DescribeDBInstancesResult")
            instances = res.get("DBInstances", [])

            mapping = {
                "SiteTorino01": "site01.nivolapiemonte.it",
                "SiteTorino02": "site02.nivolapiemonte.it",
                "SiteVercelli01": "site03.nivolapiemonte.it",
            }

            for i in instances:
                i = i.get("DBInstance")
                dbaas.append("%s.%s" % (i.get("nvl-name"), mapping.get(i.get("AvailabilityZone"))))

        elif dbtype == "oracle":
            data_search = {}
            data_search["MaxResults"] = self.app.pargs.size
            uri = "%s/computeservices/instance/describeinstances" % self.baseuri
            res = self.cmp_get(uri, data=urlencode(data_search, doseq=True))
            res = res.get("DescribeInstancesResponse").get("reservationSet")[0]
            instances = res.get("instancesSet")

            for i in instances:
                image = i.get("nvl-imageName", "")
                if image is None:
                    image = ""
                if image.lower().find("oracle") >= 0:
                    dbaas.append(i.get("privateDnsName"))

        self._meta.cmp = {"baseuri": "/v1.0/gas", "subsystem": "ssh"}
        self.configure_cmp_api_client()

        for d in dbaas:
            print("node: %s" % d)

            # check permission
            has_role = False
            try:
                uri = "%s/nodes/%s/groups" % (self.baseuri, d)
                res = self.cmp_get(uri)
                for g in res.get("groups", []):
                    print("  SSH - %s, %s" % (g.get("name"), g.get("role")))
                    if g.get("name") == "DbaCsi" and g.get("role") == "connect.root":
                        has_role = True

                if has_role is False:
                    # assign role to group
                    data = {"group": {"group_id": "DbaCsi", "role": "connect.root"}}
                    uri = "%s/nodes/%s/groups" % (self.baseuri, d)
                    res = self.cmp_post(uri, data)
            except Exception as ex:
                print(ex)
                print("  SSH - not registered")
