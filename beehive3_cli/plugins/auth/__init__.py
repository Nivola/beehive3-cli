# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

import os

from beehive3_cli.plugins.auth.controllers.auth import AuthController, ProviderController
from beehive3_cli.plugins.auth.controllers.group import AuthGroupController
from beehive3_cli.plugins.auth.controllers.ldap import AuthLdapController
from beehive3_cli.plugins.auth.controllers.oauth2 import Oauth2TokenController, ScopeController, ClientController, \
     AuthorizationCodeController, Oauth2SessionController
from beehive3_cli.plugins.auth.controllers.object import AuthObjectController
from beehive3_cli.plugins.auth.controllers.role import AuthRoleController
from beehive3_cli.plugins.auth.controllers.token import AuthTokenController
from beehive3_cli.plugins.auth.controllers.user import AuthUserController


def add_template_dir(app):
    path = os.path.join(os.path.dirname(__file__), 'templates')
    app.add_template_dir(path)


def load(app):
    app.handler.register(AuthController)
    app.handler.register(ScopeController)
    app.handler.register(ClientController)
    app.handler.register(AuthorizationCodeController)
    app.handler.register(Oauth2SessionController)
    app.handler.register(Oauth2TokenController)
    app.handler.register(AuthObjectController)
    app.handler.register(AuthRoleController)
    app.handler.register(AuthGroupController)
    app.handler.register(AuthUserController)
    app.handler.register(AuthTokenController)
    app.handler.register(AuthLdapController)
    app.handler.register(ProviderController)
    app.hook.register('post_setup', add_template_dir)
