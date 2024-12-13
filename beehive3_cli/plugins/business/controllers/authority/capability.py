# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from cement import ex
from beecell.file import read_file
from beehive3_cli.core.controller import PARGS, ARGS
from beehive3_cli.plugins.business.controllers.authority import AuthorityControllerChild


class AccountCapabilitiesController(AuthorityControllerChild):
    class Meta:
        label = "capabilities"
        description = "capabilities management"
        help = "capabilities management"

        headers = ["uuid", "name", "desc", "status", "date"]
        fields = ["uuid", "name", "desc", "status", "date.creation"]

    @ex(
        help="get capabilities",
        description="This command is used to retrieve the capabilities of a backend service. Capabilities define the actions or operations that a backend service can perform. By running this command without any arguments, it will return all the capabilities of all registered backend services. Specific capabilities of a backend service can also be retrieved by providing the backend service ID as an optional argument to this command.",
        example="beehive bu capabilities get ;beehive bu capabilities get -id CsiCloud-ComputeService-backend",
        arguments=PARGS(
            [
                (
                    ["-id"],
                    {
                        "help": "account uuid",
                        "action": "store",
                        "type": str,
                        "default": None,
                    },
                ),
                (
                    ["-objid"],
                    {
                        "help": "authorization id",
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
            uri = "%s/capabilities/%s" % (self.baseuri, oid)
            res = self.cmp_get(uri).get("capability", {})

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
                self.app.render(
                    services,
                    maxsize=200,
                    headers=["type", "name", "template", "require.name", "params"],
                )
                print("\ndefinitions:")
                self.app.render(definitions, maxsize=200, headers=["name"])
            else:
                self.app.render(res, key="capability", details=True)
        else:
            params = []
            data = self.format_paginated_query(params)
            uri = "%s/capabilities" % self.baseuri
            res = self.cmp_get(uri, data=data)
            self.app.render(
                res,
                key="capabilities",
                headers=self._meta.headers,
                fields=self._meta.fields,
                maxsize=200,
            )

    @ex(
        help="add capability",
        description="This command adds a capability to the system. The required 'config' argument specifies the capability configuration to add.",
        example="beehive bu capabilities add config fsdfds -e <env>",
        arguments=ARGS(
            [
                (
                    ["config"],
                    {"help": "capability config", "action": "store", "type": str},
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
        uri = "%s/capabilities" % self.baseuri
        res = self.cmp_post(uri, data=data)
        self.app.render({"msg": "Add capability %s" % res})

    @ex(
        help="delete capability",
        description="This command deletes a capability from a Nivola CMP backend by its UUID. The 'id' argument is required and specifies the UUID of the capability to delete.",
        arguments=ARGS(
            [
                (["id"], {"help": "capability uuid", "action": "store", "type": str}),
            ]
        ),
    )
    def delete(self):
        oid = self.app.pargs.id
        uri = "%s/capabilities/%s" % (self.baseuri, oid)
        self.cmp_delete(uri, entity="capability %s" % oid)
