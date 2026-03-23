# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from base64 import b64decode, b64encode
from cement import ex
from beehive3_cli.core.controller import PARGS, ARGS
from beehive3_cli.core.util import load_config
from beehive3_cli.plugins.ssh.controllers.ssh import SshControllerChild
from beehive3_cli.translate import _


class SshKeyController(SshControllerChild):
    class Meta:
        stacked_on = "ssh"
        stacked_type = "nested"
        label = "keys"
        description = _("ssh key management")
        help = _("ssh key management")

        headers = ["id", "name", "desc", "date", "pub_key"]
        fields = ["uuid", "name", "desc", "date.creation", "pub_key"]

    def pre_command_run(self):
        super().pre_command_run()

        self.configure_cmp_api_client()

    @ex(
        help=_("get ssh keys"),
        description=_("get ssh keys"),
        example="beehive ssh keys get",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("ssh key uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def get(self):
        oid = getattr(self.app.pargs, "id", None)
        if oid is not None:
            uri = f"{self.baseuri}/keys/{oid}"
            res = self.cmp_get(uri)
            print(
                f"""
            {res}
             """
            )
            self.app.render(res, key="key", details=True)
        else:
            params = []
            mappings = {}
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/keys"
            res = self.cmp_get(uri, data=data)
            self.app.render(res, key="keys", headers=self._meta.headers, fields=self._meta.fields)

    @ex(
        help=_("export key private and public key as string"),
        description=_("export key private and public key as string"),
        example="beehive ssh keys export <uuid>",
        arguments=ARGS(
            [
                (["id"], {"help": _("ssh key uuid"), "action": "store", "type": str}),
                (
                    ["--tofile"],
                    {
                        "help": _("store to file"),
                        "dest": "tofile",
                        "action": "store_true",
                        "default": False,
                    },
                ),
            ]
        ),
    )
    def export(self):
        oid = self.app.pargs.id
        tofile = self.app.pargs.tofile
        uri = f"{self.baseuri}/keys/{oid}"
        res = self.cmp_get(uri).get("key")
        fname = res.get("name", "mykey")
        private_key_content = b64decode(res.get("priv_key")).decode("utf-8")
        public_key_content = b64decode(res.get("pub_key")).decode("utf-8")
        print(f""" Key name: {fname}""")
        print("Private key:")
        print(private_key_content)
        print("Public key:")
        print(public_key_content)
        if tofile:
            import os

            with open(fname, "w", encoding="utf-8") as f:
                f.write(private_key_content)
            os.chmod(fname, 0o0400)

            fname = fname + ".pub"
            with open(fname, "w", encoding="utf-8") as f:
                f.write(public_key_content)
            os.chmod(fname, 0o0400)

    @ex(
        help=_("load an existing ssh key"),
        description=_("load an existing ssh key"),
        arguments=PARGS(
            [
                (["name"], {"help": _("ssh key uuid"), "action": "store", "type": str}),
                (
                    ["priv_key"],
                    {
                        "help": _("file where is located private key"),
                        "action": "store",
                        "type": str,
                    },
                ),
                (
                    ["pub_key"],
                    {
                        "help": _("file where is located the public key"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("key description"),
                        "action": "store",
                        "type": str,
                        "default": "",
                    },
                ),
                (
                    ["-attrib"],
                    {
                        "help": _("key attribute"),
                        "action": "store",
                        "type": str,
                        "default": "",
                    },
                ),
            ]
        ),
    )
    def load(self):
        name = self.app.pargs.name
        priv_key = self.app.pargs.priv_key
        pub_key = self.app.pargs.pub_key
        desc = self.app.pargs.desc
        attribute = self.app.pargs.attrib

        priv_key = load_config(priv_key)
        priv_key = bytes(priv_key, "utf-8")
        if pub_key is not None:
            pub_key = load_config(pub_key)
        else:
            pub_key = ""
        pub_key = bytes(pub_key, "utf-8")
        data = {
            "key": {
                "name": name,
                "priv_key": b64encode(priv_key),
                "pub_key": b64encode(pub_key),
                "desc": desc,
                "attribute": attribute,
            }
        }
        uri = f"{self.baseuri}/keys"
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": res})

    @ex(
        help=_("add ssh key"),
        description=_("add ssh key"),
        example="beehive ssh keys add key-pinerolo-maggioli-key -bits 2048; beehive ssh keys add gaeacc-key -bits 2048",
        arguments=ARGS(
            [
                (["name"], {"help": _("ssh key uuid"), "action": "store", "type": str}),
                (
                    ["-type"],
                    {
                        "help": _("key type like dsa, rsa, ecda [default=rsa]"),
                        "action": "store",
                        "type": str,
                        "default": "rsa",
                    },
                ),
                (
                    ["-bits"],
                    {
                        "help": _("key length [default=2048]"),
                        "action": "store",
                        "type": str,
                        "default": 2048,
                    },
                ),
                (
                    ["-desc"],
                    {
                        "help": _("key description"),
                        "action": "store",
                        "type": str,
                        "default": "",
                    },
                ),
                (
                    ["-attrib"],
                    {
                        "help": _("key attribute"),
                        "action": "store",
                        "type": str,
                        "default": "",
                    },
                ),
            ]
        ),
    )
    def add(self):
        name = self.app.pargs.name
        key_type = self.app.pargs.type
        bits = self.app.pargs.bits
        desc = self.app.pargs.desc
        attribute = self.app.pargs.attrib
        if key_type not in ["rsa"]:
            raise Exception("Only rsa key are supported")
        data = {
            "key": {
                "name": name,
                "type": key_type,
                "bits": bits,
                "desc": desc,
                "attribute": attribute,
            }
        }
        uri = f"{self.baseuri}/keys"
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": f"add key {name} with uuid: {res.get('uuid')}"})

    @ex(
        help=_("delete ssh key"),
        description=_("delete key"),
        arguments=ARGS(
            [
                (["id"], {"help": _("ssh key uuid"), "action": "store", "type": str}),
            ]
        ),
    )
    def delete(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/keys/{oid}"
        # get key name
        name = self.cmp_get(uri).get("key").get("name")
        # since name is unique, check if it's related to any compute key pair. if so except
        # because it has to be deleted from beehive bu cpaas keypairs delete
        try:
            self.api.error_if_service_exists(name=name, exact_name_match=True, servtype="ComputeKeyPairs")
        except Exception as kp_ex:
            raise Exception(
                "Ssh key is still being used by a keypair business object. Please delete it from there if necessary."
            ) from kp_ex
        self.cmp_delete(uri, data="", entity=f"ssh key {oid}")


class SshKeyAuthController(SshControllerChild):
    class Meta:
        label = "keys_auth"
        description = _("manage key authorization")
        help = _("manage key authorization")

    @ex(
        help=_("get key roles"),
        description=_("get key roles"),
        example="beehive ssh keys-auth role-get; beehive ssh keys-auth role-get <uuid>",
        arguments=ARGS([(["id"], {"help": _("key uuid"), "action": "store", "type": str})]),
    )
    def role_get(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/keys/{oid}/roles"
        res = self.cmp_get(uri)
        self.app.render(res, key="roles", headers=["name", "desc"], maxsize=200)

    @ex(
        help=_("get key users"),
        description=_("get key users"),
        example="beehive ssh keys-auth user-get <uuid>; beehive ssh keys-auth user-get ",
        arguments=ARGS([(["id"], {"help": _("key uuid"), "action": "store", "type": str})]),
    )
    def user_get(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/keys/{oid}/users"
        res = self.cmp_get(uri)
        self.app.render(
            res,
            key="users",
            headers=["id", "name", "desc", "role"],
            fields=["uuid", "name", "desc", "role"],
            maxsize=200,
        )

    @ex(
        help=_("add key role to a user"),
        description=_("add key role to a user"),
        example="beehive ssh keys-auth user-add <uuid> viewer abc.def@ghi.lmno",
        arguments=ARGS(
            [
                (["id"], {"help": _("key uuid"), "action": "store", "type": str}),
                (
                    ["role"],
                    {"help": _("authorization role"), "action": "store", "type": str},
                ),
                (
                    ["user"],
                    {"help": _("authorization user"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def user_add(self):
        oid = self.app.pargs.id
        role = self.app.pargs.role
        user = self.app.pargs.user
        data = {"user": {"user_id": user, "role": role}}
        uri = f"{self.baseuri}/keys/{oid}/users"
        res = self.cmp_post(uri, data)
        self.app.render({"msg": res})

    @ex(
        help=_("remove key role from a user"),
        description=_("remove key role from a user"),
        arguments=ARGS(
            [
                (["id"], {"help": _("key uuid"), "action": "store", "type": str}),
                (
                    ["role"],
                    {"help": _("authorization role"), "action": "store", "type": str},
                ),
                (
                    ["user"],
                    {"help": _("authorization user"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def user_del(self):
        oid = self.app.pargs.id
        role = self.app.pargs.role
        user = self.app.pargs.user
        data = {"user": {"user_id": user, "role": role}}
        uri = f"{self.baseuri}/keys/{oid}/users"
        res = self.cmp_delete(uri, data, entity=f"role {role} from user {user}")
        self.app.render({"msg": res})

    @ex(
        help=_("get key groups"),
        description=_("get key groups"),
        example="beehive ssh keys-auth group-get <uuid>; beehive ssh keys-auth group-get <uuid>",
        arguments=ARGS([(["id"], {"help": _("key uuid"), "action": "store", "type": str})]),
    )
    def group_get(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/keys/{oid}/groups"
        res = self.cmp_get(uri)
        self.app.render(
            res,
            key="groups",
            headers=["id", "name", "desc", "role"],
            fields=["uuid", "name", "desc", "role"],
            maxsize=200,
        )

    @ex(
        help=_("add key role to a group"),
        description=_("add key role to a group"),
        example="beehive ssh keys-auth group-add <uuid> viewer GR-xxx",
        arguments=ARGS(
            [
                (["id"], {"help": _("key uuid"), "action": "store", "type": str}),
                (
                    ["role"],
                    {"help": _("authorization role"), "action": "store", "type": str},
                ),
                (
                    ["group"],
                    {"help": _("authorization group"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def group_add(self):
        oid = self.app.pargs.id
        role = self.app.pargs.role
        group = self.app.pargs.group
        data = {"group": {"group_id": group, "role": role}}
        uri = f"{self.baseuri}/keys/{oid}/groups"
        res = self.cmp_post(uri, data)
        self.app.render({"msg": res})

    @ex(
        help=_("remove key role from a group"),
        description=_("remove key role from a group"),
        example="beehive ssh keys-auth group-del <uuid> master GR-sdptoolc-jv-sdpqueryapi",
        arguments=ARGS(
            [
                (["id"], {"help": _("key uuid"), "action": "store", "type": str}),
                (
                    ["role"],
                    {"help": _("authorization role"), "action": "store", "type": str},
                ),
                (
                    ["group"],
                    {"help": _("authorization group"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def group_del(self):
        oid = self.app.pargs.id
        role = self.app.pargs.role
        group = self.app.pargs.group
        data = {"group": {"group_id": group, "role": role}}
        uri = f"{self.baseuri}/keys/{oid}/groups"
        res = self.cmp_delete(uri, data, entity=f"role {role} from group {group}")
        self.app.render({"msg": res})
