# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

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
from beehive3_cli.translate import _


class SshOperationController(SshControllerChild):
    class Meta:
        stacked_on = "ssh"
        stacked_type = "nested"
        label = "ops"
        description = _("custom operations")
        help = _("custom operations")

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
            uri = f"{self.baseuri}/nodes/{node_id}"
            node = self.cmp_get(uri).get("node", {})
            nodes = [node]
        elif node_name is not None:
            uri = f"{self.baseuri}/nodes"
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
                uri = f"{self.baseuri}/nodes/{node_id}"
                node = self.cmp_get(uri).get("node", {})
                nodes.append(node)
        else:
            nodes = []

        return nodes

    def __node_run_cmd(self, scm, node, cmd, noresult=False):
        try:
            res = scm.sshcmd2node(node=node, user="root", cmd=cmd, timeout=30.0)
        except Exception as exception:
            res = {"stderr": str(exception)}
        status = False
        if res.get("stderr", "") != "":
            status = False
        elif len(res.get("stdout", [])) > 0 or noresult is True:
            status = True

        run_res = {"cmd": cmd, "res": res, "status": status}
        return run_res

    def __node_run_cmds(self, scm, nodes, cmds, out_file):
        resp = {}

        for node in nodes:
            node_status = True
            node_res = []
            node_err = None
            
            for cmd in cmds:
                node_partial_res = self.__node_run_cmd(scm, node, cmd[0], noresult=cmd[1])
                node_res.append(node_partial_res)
                
                if node_partial_res.get("status") is False:
                    node_status = False
                    node_err = dict_get(node_partial_res, "res.stderr")
                    break

            resp[node["name"]] = node_res
            
            if node_err is not None:
                print(f"{node['name']:60} {node['ip_address']:18} {node_status}: {node_err}")
            else:
                print(f"{node['name']:60} {node['ip_address']:18} {node_status}")

        with open(out_file, "w", encoding="utf-8") as f:
            f.write(dumps(resp))

    @ex(
        help=_("check virtual machine boot disk is writable"),
        description=_("check virtual machine boot disk is writable"),
        arguments=PARGS(
            [
                (
                    ["-node"],
                    {
                        "help": _("node id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("node name pattern"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-file"],
                    {
                        "help": _("node list in a file"),
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
        help=_("check data domain mounted in dbaas"),
        description=_("check data domain mounted in dbaas"),
        example="beehive ssh ops dbaas-check-dd; beehive ssh ops dbaas-check-dd -name dbs -size 10",
        arguments=PARGS(
            [
                (
                    ["-node"],
                    {
                        "help": _("node id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("node name pattern"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-file"],
                    {
                        "help": _("node list in a file"),
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
        help=_("umount data domain mounted in dbaas"),
        description=_("umount data domain mounted in dbaas"),
        arguments=PARGS(
            [
                (
                    ["-node"],
                    {
                        "help": _("node id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("node name pattern"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-file"],
                    {
                        "help": _("node list in a file"),
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
        help=_("mount data domain mounted in dbaas"),
        description=_("mount data domain mounted in dbaas"),
        arguments=PARGS(
            [
                (
                    ["-node"],
                    {
                        "help": _("node id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("node name pattern"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-file"],
                    {
                        "help": _("node list in a file"),
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
        help=_("show action on dbaas"),
        description=_("show action on dbaas"),
        example="beehive ssh ops dbaas-show-response node-check.json",
        arguments=PARGS(
            [
                (
                    ["file"],
                    {
                        "help": _("response file name"),
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
                msg = f"status: {cmd['status']} - cmd: {cmd['cmd']}"
                if cmd["status"] is False:
                    msg += f" - error: {cmd['res']['stderr']}"
                    self.app.error(msg)
                else:
                    print(msg)
                # print('cmd: %s - status: %s - res: %s' % (cmd['cmd'], cmd['status'], cmd['res']))

    @ex(help=_("check volumes"), description=_("check volumes"), arguments=PARGS([]))
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
            print(f"openstack --- id: {items[0]} | name: {items[1]}")
            try:
                ops_volume = self.client.volume_v3.get(items[0])
            except Exception as exc:
                self.app.error(exc)
                ops_volume = None
            if ops_volume is not None:
                try:
                    uri = f"/v1.0/nrs/openstack/volumes/{items[1]}"
                    res_volume = self.cmp_get(uri).get("volume")
                    print(f"resource  --- id: {res_volume['id']} | ext_id: {res_volume['ext_id']}")
                    if res_volume["ext_id"] != items[0]:
                        self.app.error("## ext_id wrong")
                    if res_volume["name"] != items[1]:
                        self.app.error("## name wrong")
                except Exception as exc:
                    self.app.error(exc)

    @ex(
        help=_("restore volume with ext_id and name wrong"),
        description=_("restore volume with ext_id and name wrong"),
        arguments=PARGS(
            [
                (
                    ["ext_id"],
                    {"help": _("openstack volume ext_id"), "action": "store", "type": str},
                ),
                (["id"], {"help": _("resource id"), "action": "store", "type": str}),
            ]
        ),
    )
    def restore_volume(self):
        ext_id = self.app.pargs.ext_id
        oid = self.app.pargs.id

        self.__config_openstack_client()

        uri = f"/v1.0/nrs/entities/{oid}"
        res = self.cmp_get(uri).get("resource")
        print(f"- resource  # name: {res['name']} | ext_id: {res['ext_id']}")

        ops = self.client.volume_v3.get(ext_id)
        print(f"- openstack # name: {ops['name']} | ext_id: {ops['id']}")

        self.client.volume_v3.update(ext_id, name=res["name"])
        print("--> update openstack")
        uri = f"/v1.0/nrs/entities/{oid}"
        res = self.cmp_put(uri, data={"resource": {"ext_id": ext_id}})
        print("--> update resource")

        uri = f"/v1.0/nrs/entities/{oid}"
        res = self.cmp_get(uri).get("resource")
        print(f"- resource  # name: {res['name']} | ext_id: {res['ext_id']}")

        ops = self.client.volume_v3.get(ext_id)
        print(f"- openstack # name: {ops['name']} | ext_id: {ops['id']}")

    @ex(
        help=_("restore vm in cmp from trilio backup"),
        description=_("restore vm in cmp from trilio backup"),
        arguments=PARGS(
            [
                (
                    ["opsvm"],
                    {"help": _("openstack vm name"), "action": "store", "type": str},
                ),
                (
                    ["-server"],
                    {
                        "help": _("if true update ext_id from openstack server to resource"),
                        "action": "store_true",
                    },
                ),
                (
                    ["-volume"],
                    {
                        "help": _("if true update ext_id in volume. Syntax volume_name:ext_id"),
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
            uri = f"/v1.0/nrs/openstack/servers/{opsvm}"
            res_server = self.cmp_get(uri).get("server")
            volumes = res_server.get("details").pop("volumes", [])
            # get volumes
            res_volumes = {}
            for v in volumes:
                uri = f"/v1.0/nrs/openstack/volumes/{v['name']}"
                res_volume = self.cmp_get(uri).get("volume")
                res_volumes[v["name"]] = res_volume

            print("------------------------------------------------")
            print("physical openstack server")
            print(f" - name: {ope_server['name']}")
            print(f" - ext_id: {ope_server['id']}")
            print(" - volumes:")
            for ope_volume in ope_volumes:
                print(f"   - ext_id: {ope_volume['id']}, size: {ope_volume['size']}")
            print("")
            print("cmp openstack server")
            print(f" - uuid: {res_server['uuid']}")
            print(f" - ext_id: {res_server['ext_id']}")
            print(" - volumes:")
            for v in volumes:
                rv = res_volumes.get(v["name"])
                print(
                    f"   - ext_id: {rv['ext_id']}, id: {v['id']}, "
                    f"name: {v['name']}, type: {v['type']}, size: {v['size']}"
                )
            print("------------------------------------------------")

            if restore_server is True:
                uri = f"/v1.0/nrs/entities/{res_server['uuid']}"
                print("\nupdate server ext_id")
                self.cmp_put(uri, data={"resource": {"ext_id": ope_server["id"]}})
            if restore_volume is not None:
                restore_volume = restore_volume.split(":")
                uri = f"/v1.0/nrs/entities/{restore_volume[0]}"
                print("\nupdate server ext_id")
                self.cmp_put(uri, data={"resource": {"ext_id": restore_volume[1]}})
        else:
            raise Exception("no server found or too much servers founds")

    @ex(
        help=_("assign dbaas node to dbacsi group"),
        description=_("assign dbaas node to dbacsi group"),
        arguments=PARGS(
            [
                (
                    ["-type"],
                    {
                        "help": _("vm type. Can be mysql or oracle [default=mysql]"),
                        "action": "store",
                        "type": str,
                        "default": "mysql",
                    },
                ),
                (
                    ["-ids"],
                    {
                        "help": _("dbaas uuids"),
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
            uri = f"{self.baseuri}/databaseservices/instance/describedbinstances"
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
                dbaas.append(f"{i.get('nvl-name')}.{mapping.get(i.get('AvailabilityZone'))}")

        elif dbtype == "oracle":
            data_search = {}
            data_search["MaxResults"] = self.app.pargs.size
            uri = f"{self.baseuri}/computeservices/instance/describeinstances"
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
            print(f"node: {d}")

            # check permission
            has_role = False
            try:
                uri = f"{self.baseuri}/nodes/{d}/groups"
                res = self.cmp_get(uri)
                for g in res.get("groups", []):
                    print(f"  SSH - {g.get('name')}, {g.get('role')}")
                    if g.get("name") == "DbaCsi" and g.get("role") == "connect.root":
                        has_role = True

                if has_role is False:
                    # assign role to group
                    data = {"group": {"group_id": "DbaCsi", "role": "connect.root"}}
                    uri = f"{self.baseuri}/nodes/{d}/groups"
                    res = self.cmp_post(uri, data)
            except Exception as exc:
                print(exc)
                print("  SSH - not registered")
