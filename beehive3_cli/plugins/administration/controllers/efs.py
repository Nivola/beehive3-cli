# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2026 CSI-Piemonte

from cement.ext.ext_argparse import ex
from beecell.simple import merge_list
from beehive3_cli.core.controller import BASE_ARGS, ARGS
from beehive3_cli.translate import _
from .child import AdminChildController, AdminError


def efs_admin_args(*list_args):
    l_efs_admin_args = [
        (
            ["-Ofb", "--ontap_fallback"],
            {
                "action": "store",
                "dest": "ontap_fallback",
                "help": _("ontap platform reference label. Used when no ontap orchestrator found in cmp."),
            },
        ),
        (
            ["-Olab", "--ontap_label"],
            {"action": "store", "dest": "ontap_label", "help": _("when multiple ontap orchestrators available.")},
        ),
    ]
    res = merge_list(BASE_ARGS, l_efs_admin_args, *list_args)
    return res


class EfsAdminController(AdminChildController):
    """
    controller of efs admin commands
    """

    class Meta:
        """efs meta"""

        label = "efs-adm"
        description = _("efs administartion commands")
        help = _("efs administartion commands")

    @staticmethod
    def __extract_service_name(provider_res_name: str, svm_name: str = None) -> str:
        if provider_res_name.startswith("dr-"):
            prefix = "dr-"
            service_name = provider_res_name[3:]
        else:
            prefix = ""
            service_name = provider_res_name

        # remove svm
        if svm_name:
            service_name = service_name.replace(f"{svm_name}-","")
        # remove uuid part, if present

        parts = service_name.rsplit('-', 2)
        if len(parts) == 3 and parts[2].startswith('cz') and parts[2][2:].isdigit():
            main_name = parts[0]
        else:
            # Non corrisponde al pattern, restituisci originale
            main_name = service_name
        return f"{prefix}{main_name}"

    @ex(
        help=_("import efs service instance from existing imported provider resource"),
        description=_("This command imports a staas efs instance from a share v2 resource"),
        arguments=ARGS([
            (
                ["-awx_orchestrator_tag"],
                {
                    "help": _("awx orchestrator tag"),
                    "action": "store",
                    "type": str,
                    "default": "02"
                }
            ),
            (
                ["-force_service_name"],
                {
                    "help": _("force service name to the specified one"),
                    "action": "store",
                    "type": str,
                    "default": None
                }
            ),
            (
                ["-desc"],
                {
                    "help": _("efs description"),
                    "action": "store",
                    "type": str,
                    "default": None,
                },
            ),
            (
                ["-service_definition_name"],
                {
                    "help": _("service definition name"),
                    "action": "store",
                    "type": str,
                    "default": None
                }
            ),
            (
                ["-service_definition_id"],
                {
                    "help": _("service definition id"),
                    "action": "store",
                    "type": str,
                    "default": None,
                },
            ),
            (
                ["account"],
                {
                    "help": _("account id"),
                    "action": "store",
                    "type": str
                }
            ),
            (
                ["resource"],
                {
                    "help": _("share resource id"),
                    "action": "store",
                    "type": str,
                    "default": None,
                },
            ),
        ]),
    )
    def import_res(self):
        """
        example:
        - name: test-micro-volume-0
        - account: account_ale_gw2 (or id, or uuid)
        - plugintype: ComputeService
        - container_plugintype: ComputeService
        - resource: <uuid>
        [ optional
            - service_definition_id: 13
            - parent: <uuid>
        ] optional

        creates service instance and service instance config for existing resource
        """
        self.app.print(_("Getting account information..."))
        account = self.get_account(self.app.pargs.account)
        account_id = account.get("uuid")

        filters = {
            "flag_container": True,
            "size": 1,
            "page": 0,
            "account_id": account_id,
            "plugintype": "StorageService"
        }

        try:
            parent = self.find_cmp_service_instance(**filters)
        except Exception as exc:
            raise Exception(
                _("error while searching for account StorageService: {error}")
                .format(error=str(exc))
            ) from exc

        expected_compute_zone_uuid = parent.get("resource_uuid")
        parent_id = parent.get("id")

        self.app.print(_("Getting resource information..."))
        resource = self.get_cmp_resource(self.app.pargs.resource)
        res_def = resource.get("__meta__").get("definition")
        if res_def!="Provider.ComputeZone.ComputeFileShareV2":
            raise AdminError(_("Unsupported resource type: {res_def}").format(res_def))
        compute_zone = self.get_cmp_resource(resource.get("parent"))

        found_uuid = compute_zone.get("uuid")
        if found_uuid != expected_compute_zone_uuid:
            raise AdminError(
                _("Compute zone mismatch. expected {expected_cz} but found {found_cz}").format(
                    expected_cz=expected_compute_zone_uuid,
                    found_cz=found_uuid,
                )
            )

        share_type = resource.get("attributes").get("type")
        if share_type!='ontap':
            raise AdminError(_("Unsupported orchestrator type {orch_type}").format(orch_type=share_type))

        if self.app.pargs.service_definition_id:
            # id given
            service_definition_identifier = self.app.pargs.service_definition_id
        elif self.app.pargs.service_definition_name:
            # name given
            service_definition_identifier = self.app.pargs.service_definition_name
        else:
            # neither given, use default
            service_definition_identifier = "store.ontap.m1"

        service_definition = self.get_cmp_service_definition(service_definition_identifier)
        service_definition_id = service_definition.get("id")

        share_proto: str = resource.get("attributes").get("proto")
        if not share_proto:
            raise AdminError(_("Unknown share protocol: {share_proto}").format(share_proto=share_proto))

        has_compliance_resource = resource.get("attributes").get("compliance_zone") is not None

        role_specific_conf = {}
        source_share = None
        share_role = resource.get("attributes").get("share_role")
        if share_role=="replica":
            rpo = resource.get("details").get("snapmirror_policy")
            parts = rpo.split("_")
            rpo = parts[-1]
            # get linked provider resource
            sources = self.get_cmp_linkedres(resource["id"], link_type="snapmirror")
            if not sources or len(sources)>1:
                raise AdminError(
                    _("resource condition error: invalid number of linked resources: expected 1 but found {found}")
                    .format(found=len(sources) if sources else "0")
                )
            source_res_uuid = sources[0]["uuid"]
            source_provider_share = self.get_cmp_resource(source_res_uuid)
            source_share = self.find_cmp_service_instance(resource_uuid=source_res_uuid)
            role_specific_conf.update({"SourceId": source_share["uuid"], "Rpo": rpo})
        elif has_compliance_resource:
            # main with snaplock
            rpo = resource.get("details").get("snaplock").get("policy_name")
            parts = rpo.split("_")
            rpo = parts[-1]
            role_specific_conf.update({"Rpo": rpo})

        try:
            resource_name: str = resource.get("name")
            if share_role=="replica":
                resource_svm: str = source_provider_share.get("details").get("svm")
            else:
                resource_svm: str = resource.get("details").get("svm")
            service_name = self.__extract_service_name(resource_name, resource_svm)
        except Exception as exc:
            raise AdminError(
                _("Unable to determine service name: check resource metadata. err:") + f" {exc!s}"
            ) from exc

        # keep previous check as a sort of sanity check even if service name is given as parameter
        if self.app.pargs.force_service_name:
            service_name = self.app.pargs.force_service_name

        yes = self.app.pargs.assumeyes
        if not yes:
            account_name = account.get("name")
            res_uuid = resource.get("uuid")
            msg_tmpl = _(
                "About to create a service with name '{service_name}' in account '{account_name}', "
                "mapping provider share resource '{resource_name}' (uuid = '{resource_uuid}'). Continue?"
            )
            msg = msg_tmpl.format(
                service_name=service_name,
                resource_name=resource_name,
                account_name=account_name,
                resource_uuid=res_uuid,
            )
            ans = self._ct.prompt_choice(msg)
            if ans!='y':
                return

        plugintype = "StorageEFS"
        container_plugintype = "StorageService"
        if self.app.pargs.desc:
            desc = self.app.pargs.desc
        else:
            desc = f"imported {service_name}"

        additional_config = {
            "container": "ResourceProvider01",
            "share_proto_prefix": "netapp",
            "orchestrator_type": "ontap",
            "orchestrator_tag": "legacyfas",
            "StorageService": expected_compute_zone_uuid,
            "version": self.app.pargs.awx_orchestrator_tag,
            "share_data": {
                "Nvl_shareProto": share_proto.upper(),
                "CreationToken": service_name,
                "Nvl_FileSystem_Type": service_definition.get("name"),
                "Nvl_FileSystem_Size": int(resource.get("details").get("size")),
                # "Encrypted": a mano ma non serve. letto automaticamente da resource
                "ComplianceMode": has_compliance_resource,
                "SiteName": resource.get("availability_zone").get("name")
            }
        }
        additional_config["share_data"].update(role_specific_conf)
        data = {
            "serviceinst": {
                "name": service_name,
                "desc": desc,
                "account_id": account_id,
                "plugintype": plugintype,
                "container_plugintype": container_plugintype,
                "resource_id": resource.get("uuid"),
                "service_definition_id": str(service_definition_id), #TODO check
                "parent_id": str(parent_id), # TODO check
                "additional_config": additional_config,
                "instance_version": "2.0"
            }
        }

        __message = _("Please check these values are valid:")
        __message += f'\n- protocol: {share_proto}\n'
        __message += f'- compliance: {has_compliance_resource}\n'
        if has_compliance_resource:
            __message += f'- rpo: {rpo}\n'
        if source_share:
            __message += f'- source id: {source_share["uuid"]}\n'
        __message += _("Service configuration that will be used for import:\n")
        from ujson import dumps
        __message += dumps(data)
        print(self.styler.yellow(__message))
        if not yes:
            ans = self._ct.prompt_choice('Continue?')
            if ans!='y':
                return

        uri = "/v2.0/nws/serviceinsts/import"
        res = self.cmp_post(uri, data=data)
        service_uuid = res.get("uuid")
        self.app.render({"msg": f"import service plugin instance {service_name} (uuid = '{service_uuid}')"})
