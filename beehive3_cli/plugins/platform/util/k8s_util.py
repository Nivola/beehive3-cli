# SPDX-License-Identifier: EUPL-1.2
#
# (C) Copyright 2018-2022 CSI-Piemonte

# Copyright 2018 The Kubernetes Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from re import sub
from kubernetes import client
from kubernetes.utils import FailToCreateError


def list_from_dict(k8s_client, data, verbose=False, namespace='default', kinds=None, **kwargs):
    """Perform an action from a dictionary containing valid kubernetes API object (i.e. List, Service, etc).

    :param k8s_client: an ApiClient object, initialized with the client args.
    :param data: a dictionary holding valid kubernetes objects
    :param verbose: If True, print confirmation from the create action. Default is False.
    :param namespace: string. Contains the namespace to create all resources inside. The namespace must preexist
        otherwise the resource creation will fail. If the API object in the yaml file already contains a namespace
        definition this parameter has no effect.
    :param kinds: list of kinds [optional]
    :returns: The queried kubernetes API objects.
    :raises: FailToCreateError which holds list of `client.rest.ApiException` instances for each object that failed
        to create.
    """
    # If it is a list type, will need to iterate its items
    api_exceptions = []
    k8s_objects = []

    if "List" in data["kind"]:
        # Could be "List" or "Pod/Service/...List"
        # This is a list type. iterate within its items
        kind = data["kind"].replace("List", "")
        for yml_object in data["items"]:
            # Mitigate cases when server returns a xxxList object
            # See kubernetes-client/python#586
            # name = yml_object["metadata"]["name"]
            if kind != "":
                yml_object["apiVersion"] = data["apiVersion"]
                yml_object["kind"] = kind
            try:
                queried = get_from_yaml_single_item(k8s_client, yml_object, verbose, namespace=namespace, kinds=kinds,
                                                    **kwargs)
                if queried is not None:
                    k8s_objects.append(queried)
            except client.rest.ApiException as api_exception:
                api_exceptions.append(api_exception)
    else:
        # This is a single object. Call the single item method
        try:
            queried = get_from_yaml_single_item(k8s_client, data, verbose, namespace=namespace, kinds=kinds, **kwargs)
            if queried is not None:
                k8s_objects.append(queried)
        except client.rest.ApiException as api_exception:
            api_exceptions.append(api_exception)

    # In case we have exceptions waiting for us, raise them
    if api_exceptions:
        raise FailToCreateError(api_exceptions)

    return k8s_objects


def get_from_yaml_single_item(k8s_client, yml_object, verbose=False, kinds=None, **kwargs):
    group, _, version = yml_object["apiVersion"].partition("/")
    if version == "":
        version = group
        group = "core"
    # Take care for the case e.g. api_type is "apiextensions.k8s.io"
    # Only replace the last instance
    group = "".join(group.rsplit(".k8s.io", 1))
    # convert group name from DNS subdomain format to
    # python class name convention
    group = "".join(word.capitalize() for word in group.split('.'))
    fcn_to_call = "{0}{1}Api".format(group, version.capitalize())
    k8s_api = getattr(client, fcn_to_call)(k8s_client)
    # Replace CamelCased action_type into snake_case
    kind = yml_object["kind"]

    if kinds is not None and kind not in kinds:
        return None

    kind = sub('(.)([A-Z][a-z]+)', r'\1_\2', kind)
    kind = sub('([a-z0-9])([A-Z])', r'\1_\2', kind).lower()
    name = yml_object["metadata"]["name"]
    # Expect the user to create namespaced objects more often
    resp = None
    if hasattr(k8s_api, "read_namespaced_{0}".format(kind)):
        # Decide which namespace we are going to put the object in,
        # if any
        if "namespace" in yml_object["metadata"]:
            namespace = yml_object["metadata"]["namespace"]
            kwargs['namespace'] = namespace
            kwargs['name'] = name
        resp = getattr(k8s_api, "read_namespaced_{0}".format(kind))(**kwargs)
    else:
        kwargs.pop('namespace', None)
        kwargs['name'] = name
        resp = getattr(k8s_api, "read_{0}".format(kind))(**kwargs)
    if verbose:
        msg = "{0} queried.".format(kind)
        if hasattr(resp, 'status'):
            msg += " status='{0}'".format(str(resp.status))
        print(msg)

    return resp


def delete_from_dict(k8s_client, data, verbose=False, namespace='default', **kwargs):
    """Perform an action from a dictionary containing valid kubernetes API object (i.e. List, Service, etc).

    :param k8s_client: an ApiClient object, initialized with the client args.
    :param data: a dictionary holding valid kubernetes objects
    :param verbose: If True, print confirmation from the create action. Default is False.
    :param namespace: string. Contains the namespace to create all resources inside. The namespace must preexist
        otherwise the resource creation will fail. If the API object in the yaml file already contains a namespace
        definition this parameter has no effect.
    :returns: The deleted kubernetes API objects.
    :raises: FailToCreateError which holds list of `client.rest.ApiException` instances for each object that failed
        to create.
    """
    # If it is a list type, will need to iterate its items
    api_exceptions = []
    k8s_objects = []

    if "List" in data["kind"]:
        # Could be "List" or "Pod/Service/...List"
        # This is a list type. iterate within its items
        kind = data["kind"].replace("List", "")
        for yml_object in data["items"]:
            # Mitigate cases when server returns a xxxList object
            # See kubernetes-client/python#586
            name = yml_object["metadata"]["name"]
            if kind != "":
                yml_object["apiVersion"] = data["apiVersion"]
                yml_object["kind"] = kind
            try:
                deleted = delete_from_yaml_single_item(k8s_client, yml_object, verbose, namespace=namespace, **kwargs)
                k8s_objects.append({'namespace': namespace, 'kind': kind, 'name': name})
            except client.rest.ApiException as api_exception:
                api_exceptions.append(api_exception)
    else:
        # This is a single object. Call the single item method
        try:
            name = data["metadata"]["name"]
            kind = data["kind"]
            deleted = delete_from_yaml_single_item(k8s_client, data, verbose, namespace=namespace, **kwargs)
            k8s_objects.append({'namespace': namespace, 'kind': kind, 'name': name})
        except client.rest.ApiException as api_exception:
            api_exceptions.append(api_exception)

    # In case we have exceptions waiting for us, raise them
    if api_exceptions:
        raise FailToCreateError(api_exceptions)

    return k8s_objects


def delete_from_yaml_single_item(k8s_client, yml_object, verbose=False, **kwargs):
    group, _, version = yml_object["apiVersion"].partition("/")
    if version == "":
        version = group
        group = "core"
    # Take care for the case e.g. api_type is "apiextensions.k8s.io"
    # Only replace the last instance
    group = "".join(group.rsplit(".k8s.io", 1))
    # convert group name from DNS subdomain format to
    # python class name convention
    group = "".join(word.capitalize() for word in group.split('.'))
    fcn_to_call = "{0}{1}Api".format(group, version.capitalize())
    k8s_api = getattr(client, fcn_to_call)(k8s_client)
    # Replace CamelCased action_type into snake_case
    kind = yml_object["kind"]
    kind = sub('(.)([A-Z][a-z]+)', r'\1_\2', kind)
    kind = sub('([a-z0-9])([A-Z])', r'\1_\2', kind).lower()
    name = yml_object["metadata"]["name"]
    # Expect the user to create namespaced objects more often
    resp = None
    if hasattr(k8s_api, "delete_namespaced_{0}".format(kind)):
        # Decide which namespace we are going to put the object in,
        # if any
        if "namespace" in yml_object["metadata"]:
            namespace = yml_object["metadata"]["namespace"]
            kwargs['namespace'] = namespace
            kwargs['name'] = name
        resp = getattr(k8s_api, "delete_namespaced_{0}".format(kind))(**kwargs)
    else:
        kwargs.pop('namespace', None)
        kwargs['name'] = name
        resp = getattr(k8s_api, "delete_{0}".format(kind))(**kwargs)
    if verbose:
        msg = "{0} deleted.".format(kind)
        if hasattr(resp, 'status'):
            msg += " status='{0}'".format(str(resp.status))
        print(msg)
    return resp