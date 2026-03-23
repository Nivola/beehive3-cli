# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from json import tool

from cement import ex
from beecell.file import read_file
from beehive3_cli.core.controller import PARGS, ARGS
from beehive3_cli.plugins.business.controllers.authority import AuthorityControllerChild
from beehive3_cli.translate import _
from yaml import safe_dump
from typing import TypedDict, List

MetaCapaDict = TypedDict(
    "MetaCapaDict",
    {
        "definition": str,
        "objid": str,
        "type": str,
        "uri": str,
    },
)

CapaServiceReqDict = TypedDict(
    "CapaServiceReqDict",
    {
        "name": str,
        "type": str,
    },
)

CapaServiceDict = TypedDict(
    "CapaServiceDict",
    {
        "name": str,
        "require": CapaServiceReqDict,
        "template": str,
        "type": str,
        "params": dict,
    },
)

CapaParamDict = TypedDict(
    "CapaParamDict",
    {
        "account_type": str,
        "definitions": List[str],
        "pods": str,
        "services": List[CapaServiceDict],
    },
)

CapaDict = TypedDict(
    "CapaDict",
    {
        "__meta__": MetaCapaDict,
        "active": bool,
        "date": dict,
        "desc": str,
        "id": int,
        "name": str,
        "params": CapaParamDict,
        "status": str,
        "uuid": str,
        "version": str,
    },
)


class AccountCapabilitiesController(AuthorityControllerChild):
    class Meta:
        label = "capabilities"
        description = _("capabilities management")
        help = _("capabilities management")

        headers = ["uuid", "name", "desc", "status", "date"]
        fields = ["uuid", "name", "desc", "status", "date.creation"]

    @ex(
        help=_("get capabilities"),
        description=_(
            "This command is used to retrieve the capabilities of a backend service. "
            "Capabilities define the actions or operations that a backend service can perform. "
            "By running this command without any arguments, it will return all the capabilities "
            "of all registered backend services. "
            "Specific capabilities of a backend service can also be retrieved by providing "
            "the backend service ID as an optional argument to this command."
        ),
        example="beehive bu capabilities get -id CsiCloud-ComputeService-backend",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": _("account uuid"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-objid"],
                    {
                        "help": _("authorization id"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-name"],
                    {
                        "help": _("name"),
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["--tofile"],
                    {
                        "help": _(
                            "store output to a customization yaml file. In order to get or modify the cmp configuration"
                        ),
                        "action": "store_true",
                        "dest": "tofile",
                        "default": False,
                    },
                ),
                (
                    ["-o"],
                    {
                        "help": _("when --tofile specify filename "),
                        "action": "store",
                        "dest": "outfilename",
                        "type": str,
                        "default": None,
                    },
                ),
            ]
        ),
    )
    def get(self):
        oid = getattr(self.app.pargs, "id", None)
        tofile: bool = self.app.pargs.tofile
        outfilename:str = self.app.pargs.outfilename
        if oid is not None:
            uri = f"{self.baseuri}/capabilities/{oid}"
            res = self.cmp_get(uri).get("capability", {})

            if tofile:
                c: CapaDict = res
                name = c.get("name")
                outdata = {
                    "configs": {
                        "service": {
                            "capabilities": [
                                {
                                    "name": name,
                                    "desc": c.get("desc"),
                                    "account_type": c.get("params").get("account_type"),
                                    "pods": c.get("params").get("pods"),
                                    "definitions": c.get("params").get("services"),
                                    "services": c.get("params").get("services"),
                                }
                            ]
                        }
                    }
                }
                if outfilename ==None:
                    outfilename = name
                with open(f"{outfilename}.yml", "w", encoding="utf-8") as o_stream:
                    safe_dump(outdata, stream=o_stream, sort_keys=False)
            if self.is_output_text():
                params = res.pop("params", {})
                services = params.get("services", [])
                account_type = params.get("account_type", [])
                pods = params.get("pods", [])
                definitions = [{"name": d} for d in params.get("definitions", [])]
                self.app.render(res, details=True)

                if account_type and account_type.split():
                    print("")
                    self.app.render({"account_type": account_type, "pods": pods}, details=True)

                print("\nservices:")
                transform = {"params.colortext": False}
                self.app.render(
                    services,
                    maxsize=200,
                    headers=["type", "name", "template", "require.name", "params"],
                    transform=transform,
                )
                print("\ndefinitions:")
                self.app.render(definitions, maxsize=200, headers=["name"])
            else:
                self.app.render(res, key="capability", details=True)
        else:
            params = ["name"]
            mappings = {"name": lambda n: "%" + n + "%"} 
            data = self.format_paginated_query(params, mappings=mappings)
            uri = f"{self.baseuri}/capabilities"
            res = self.cmp_get(uri, data=data)
            if tofile:
                l:List[CapaDict] = res.get("capabilities")
                capa = []
                for c  in l:
                    capa.append(
                        {
                            "name": c.get("name"),
                            "desc": c.get("desc"),
                            "account_type": c.get("params").get("account_type"),
                            "pods": c.get("params").get("pods"),
                            "definitions": c.get("params").get("definitions"),
                            "services": c.get("params").get("services"),
                        }
                    )
                outdata = {"configs": {"service": {"capabilities": capa}}}
                if outfilename == None:
                    outfilename = "capabilities"
                with open(f"{outfilename}.yml", "w", encoding="utf-8") as o_stream:
                    safe_dump(outdata, stream=o_stream, sort_keys=False)
            self.app.render(
                res,
                key="capabilities",
                headers=self._meta.headers,
                fields=self._meta.fields,
                maxsize=200,
            )

    @ex(
        help=_("add capability"),
        description=_(
            "This command adds a capability to the system. "
            "The required 'config' argument specifies the capability configuration to add."
        ),
        example="beehive bu capabilities add config fsdfds -e <env>",
        arguments=ARGS(
            [
                (
                    ["config"],
                    {"help": _("capability config"), "action": "store", "type": str},
                ),
            ]
        ),
    )
    def add(self):
        config = self.app.pargs.config
        params = read_file(config).get("capability")
        data = {
            "capability": {
                "name": params.get("name"),
                "desc": params.get("desc", None),
                "version": params.get("version", "1.0"),
                "services": params.get("services", None),
                "definitions": params.get("definitions", None),
            }
        }
        uri = f"{self.baseuri}/capabilities"
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": f"Add capability {res}"})

    @ex(
        help=_("delete capability"),
        description=_(
            "This command deletes a capability from a Nivola CMP backend by its UUID. "
            "The 'id' argument is required and specifies the UUID of the capability to delete."
        ),
        arguments=ARGS(
            [
                (["id"], {"help": _("capability uuid"), "action": "store", "type": str}),
            ]
        ),
    )
    def delete(self):
        oid = self.app.pargs.id
        uri = f"{self.baseuri}/capabilities/{oid}"
        self.cmp_delete(uri, entity=f"capability {oid}")
