# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2024 CSI-Piemonte

from .child import AdminChildController, AdminError
from cement.ext.ext_argparse import ex
from beehive3_cli.core.controller import ARGS
from beehive3_cli.core.util import load_environment_config
from urllib.parse import urlencode


class MigrationP5p6AdminController(AdminChildController):
    def get_db_connection(self, db):
        from beecell.db import MysqlManager

        config = load_environment_config(self.app)
        mariadb = config.get("orchestrators", {})["mariadb"][self.env]
        host = mariadb["hosts"][0]
        port = mariadb["port"]
        users = mariadb["users"]
        user = None
        pwd = None
        for user in users:
            pwd = users[user]

        db_uri = "mysql+pymysql://%s:%s@%s:%s/%s" % (user, pwd, host, port, db)
        server = MysqlManager(1, db_uri)
        return server

    def execute_query(self, sqlstmnt):
        server = self.get_db_connection("ssh")
        server.create_simple_engine()
        connection = server.engine.connect()
        res = connection.execute(sqlstmnt)
        connection.close()
        return res

    class Meta:
        label = "migration-p5p6"
        description = "collection of commands to facilitate accounts migration to p5p6"
        help = "collection of commands to facilitate accounts migration to p5p6"

    @ex(
        help="update source account and create destination account",
        description="""This command does the following: 1) changes source account name from <src-account-name> to
        <src-account-name>-TODELETE; 2) creates a destination account with name, description and acronym equal to the
        source one before renaming""",
        arguments=ARGS(
            [
                (["src_account"], {"help": "source (p1p2p3) account id", "action": "store", "type": str}),
            ]
        ),
    )
    def create_update_accounts(self):
        src_account = self.app.pargs.src_account

        # get source account information
        src_account_config = self.api.business.account.get(src_account)
        src_account_name = src_account_config.get("name")
        src_account_uuid = src_account_config.get("uuid")
        src_account_desc = src_account_config.get("desc")
        src_account_acronym = src_account_config.get("acronym", "")
        src_account_type = src_account_config.get("account_type")
        src_account_mgmt_model = src_account_config.get("management_model")
        division_uuid = src_account_config.get("division_id")

        if "-TODELETE" in src_account_name:
            raise AdminError("Suffix -TODELETE already included in source account name")
        if src_account_type is not None and src_account_type == "":
            raise AdminError("Account type attribute cannot be null")
        if src_account_mgmt_model is not None and src_account_mgmt_model == "":
            raise AdminError("Account management model attribute cannot be null")

        # update source account name
        sqlstmnt = f"""
UPDATE service.account
SET
    name = '{src_account_name}-TODELETE'
WHERE uuid = '{src_account_uuid}'
"""
        self.execute_query(sqlstmnt)
        print(f"src account {src_account_uuid} updated")

        # create destination account
        dst_account_uuid = self.api.business.account.add(
            src_account_name,
            division_uuid,
            acronym=src_account_acronym,
            desc=src_account_desc,
            account_type=src_account_type,
            management_model=src_account_mgmt_model,
            pods="p5p6",
        )
        print(f"dst account {dst_account_uuid} created")

    def get_src_keypair_id(self, key_name):
        sqlstmnt = f"""
SELECT si.id FROM service.service_instance si
WHERE si.name = '{key_name}';
"""
        res = self.execute_query(sqlstmnt)
        return res.fetchone()[0]

    def get_src_keypair_config(self, key_id):
        sqlstmnt = f"""
SELECT sic.json_cfg FROM service.service_instance_config sic
WHERE sic.fk_service_instance_id = {key_id};
"""
        res = self.execute_query(sqlstmnt)
        return res.fetchone()[0]

    @staticmethod
    def update_src_keypair_config(key_cfg):
        from json import loads, dumps

        key_cfg_dict = loads(key_cfg)
        key_name = key_cfg_dict.get("KeyName")
        ssh_key_name = key_cfg_dict.get("SshKeyName")
        key_cfg_dict["KeyName"] = f"{key_name}-TODELETE"
        key_cfg_dict["SshKeyName"] = f"{ssh_key_name}-TODELETE"
        key_cfg = dumps(key_cfg_dict)
        return key_cfg

    @ex(
        help="rename source ssh key",
        description="rename source ssh key",
        arguments=ARGS(
            [
                (["key_name"], {"help": "ssh key name", "action": "store", "type": str}),
            ]
        ),
    )
    def rename_src_sshkey(self):
        key_name = self.app.pargs.key_name
        key_id = self.get_src_keypair_id(key_name)
        key_cfg = self.get_src_keypair_config(key_id)
        new_key_cfg = self.update_src_keypair_config(key_cfg)

        # update ssh
        sqlstmnt = f"""
UPDATE ssh.ssh_key
SET
    name = '{key_name}-TODELETE',
    `desc` = '{key_name}-TODELETE'
WHERE name = '{key_name}'
"""
        self.execute_query(sqlstmnt)

        # update service
        sqlstmnt = f"""
UPDATE service.service_instance
SET
    name = '{key_name}-TODELETE',
    `desc` = '{key_name}-TODELETE'
WHERE name = '{key_name}'
"""
        self.execute_query(sqlstmnt)

        # update service config
        sqlstmnt = f"""
UPDATE service.service_instance_config
SET
    json_cfg = '{new_key_cfg}'
WHERE fk_service_instance_id = {key_id};
"""
        self.execute_query(sqlstmnt)
        print(f"ssh key renamed")

    @ex(
        help="copy source ssh key content to new one",
        description="copy source ssh key content to new one",
        arguments=ARGS(
            [
                (["key_name"], {"help": "ssh key name", "action": "store", "type": str}),
            ]
        ),
    )
    def copy_src_sshkey(self):
        key_name = self.app.pargs.key_name
        old_key_name = f"{key_name}-TODELETE"
        sqlstmnt = f"""
UPDATE ssh.ssh_key nk
SET
  nk.priv_key = (
    SELECT priv_key FROM ssh.ssh_key ok
    WHERE ok.name = '{old_key_name}'
  ),
  nk.pub_key = (
    SELECT pub_key FROM ssh.ssh_key ok
    WHERE ok.name = '{old_key_name}'
  )
WHERE nk.name = '{key_name}'
"""
        self.execute_query(sqlstmnt)
        print(f"ssh key updated")

    @ex(
        help="add ssh key to user",
        description="add ssh key to user",
        arguments=ARGS(
            [
                (["id"], {"help": "ssh user uuid", "action": "store", "type": str}),
                (["key_name"], {"help": "ssh key name", "action": "store", "type": str}),
            ]
        ),
    )
    def link_sshkey(self):
        user_oid = self.app.pargs.id
        key_name = self.app.pargs.key_name
        # get user
        uri = "/v1.0/gas/users/%s" % user_oid
        user = self.cmp_get(uri).get("user")
        user_id = user["id"]
        ssh_key = self.cmp_get(f"/v1.0/gas/keys/{key_name}")
        ssh_key_id = ssh_key["key"]["id"]
        sqlstmnt = f"""
INSERT INTO ssh.keys_users (fk_key_id, fk_user_id) VALUES({ssh_key_id}, {user_id})
"""
        self.execute_query(sqlstmnt)
        print("ssh key linked to user")

    def get_res_stack_uuid(self, service_id):
        uri = f"/v2.0/nws/serviceinsts/{service_id}"
        res = self.cmp_get(uri).get("serviceinst")
        return res["resource_uuid"]

    def get_sql_stack_attribute(self, res_stack_id):
        sqlstmnt = f"""
SELECT src_res.attribute FROM resource.resource src_res
WHERE src_res.uuid = '{res_stack_id}'
"""
        res = self.execute_query(sqlstmnt)
        return res.fetchone()[0]

    def extract_ip_from_sql_stack_attrib(self, sql_stack_attribute):
        from json import loads

        sql_stack_attr_dict = loads(sql_stack_attribute)
        return sql_stack_attr_dict["outputs"]["ResourceIP"]["value"]

    @ex(
        help="copy dbaas sql stack attributes to new one",
        description="copy dbaas sql stack attributes to new one",
        arguments=ARGS(
            [
                (["src_id"], {"help": "source database id", "action": "store", "type": str}),
                (["dest_id"], {"help": "destination database id", "action": "store", "type": str}),
            ]
        ),
    )
    def copy_dbaas_stack_attributes(self):
        src_id = self.app.pargs.src_id
        dest_id = self.app.pargs.dest_id
        src_res_stack_id = self.get_res_stack_uuid(src_id)
        dest_res_stack_id = self.get_res_stack_uuid(dest_id)
        src_sql_stack_attribute = self.get_sql_stack_attribute(src_res_stack_id)
        dest_sql_stack_attribute = self.get_sql_stack_attribute(dest_res_stack_id)
        src_ip = self.extract_ip_from_sql_stack_attrib(src_sql_stack_attribute)
        dest_ip = self.extract_ip_from_sql_stack_attrib(dest_sql_stack_attribute)
        new_dest_sql_stack_attribute = src_sql_stack_attribute.replace(src_ip, dest_ip)
        sqlstmnt = f"""
UPDATE resource.resource dest_res
SET
    dest_res.attribute = '{new_dest_sql_stack_attribute}'
WHERE dest_res.uuid = '{dest_res_stack_id}'
"""
        self.execute_query(sqlstmnt)
