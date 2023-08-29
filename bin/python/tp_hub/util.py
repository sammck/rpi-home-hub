#
# Copyright (c) 2023 Samuel J. McKelvie
#
# MIT License - See LICENSE file accompanying this package.
#

"""
Handy Python utilities for this project
"""

from __future__ import annotations

import os
import sys
import dotenv
import json
import re
import urllib3
from functools import cache
import copy
from .internal_types import *
from .internal_types import _CMD, _FILE, _ENV
from .pkg_logging import logger

from project_init_tools.installer.docker import install_docker, docker_is_installed
from project_init_tools.installer.docker_compose import install_docker_compose, docker_compose_is_installed
from project_init_tools.installer.aws_cli import install_aws_cli, aws_cli_is_installed
from project_init_tools.util import (
    sudo_check_call,
    sudo_check_output,
    sudo_check_call_stderr_exception,
    sudo_check_output_stderr_exception,
    should_run_with_group,
    download_url_text,
)

@cache
def get_public_ip_address() -> str:
    """
    Get the public IP address of this host by asking https://api.ipify.org/
    """
    try:
        result = download_url_text("https://api.ipify.org/").strip()
        if result == "":
            raise HubError("https://api.ipify.org returned an empty string")
        return result
    except Exception as e:
        raise HubError("Failed to get public IP address") from e

class IpRouteInfo():
    remote_ip_addr: str
    """The IP address of the remote host"""

    gateway_lan_addr: str
    """The LAN-local IP address of the gateway router on the route to the remote host"""

    network_interface: str
    """The name of the local network interface that is on the route to remote host"""

    local_lan_addr: str
    """The LAN-local IP address of this host on the route to the remote host"""

    _ip_route_re = re.compile(r"^(?P<remote_addr>\d+\.\d+\.\d+\.\d+)\s+via\s+(?P<gateway_lan_addr>\d+\.\d+\.\d+\.\d+)\s+dev\s+(?P<network_interface>.*[^\s])\s+src\s+(?P<local_lan_addr>\d+\.\d+\.\d+\.\d+)\s+uid\s")

    def __init__(self, remote_ip_addr: str):
        """
        Get info about the route to a remote IP address
        
        This is done by parsing the output of the "ip route" command when it describes
        the route to the remote address; e.g.:

                $ ip -o route get 8.8.8.8
                8.8.8.8 via 192.168.0.1 dev eth0 src 192.168.0.245 uid 1000 \    cache 
        """
        
        self.remote_ip_addr = remote_ip_addr
        response = sudo_check_output_stderr_exception(
            ["ip", "-o", "route", "get", remote_ip_addr],
            use_sudo=False,
        ).decode("utf-8").split('\n')[0].rstrip()
        match = self._ip_route_re.match(response)
        if match is None:
            raise HubError(f"Failed to parse output of 'ip -o route get {remote_ip_addr}: '{response}'")
        self.gateway_lan_addr = match.group("gateway_lan_addr")
        self.network_interface = match.group("network_interface")
        self.local_lan_addr = match.group("local_lan_addr")

@cache
def get_route_info(remote_ip_addr: str) -> IpRouteInfo:
    """
    Get info about the route to a remote IP address
    """
    return IpRouteInfo(remote_ip_addr)

@cache
def get_internet_route_info() -> IpRouteInfo:
    """
    Get info about the route to the public internet.

    An arbitrary internet host address (Google's name servers) is used to determine the route.

    """
    return IpRouteInfo("8.8.8.8")

@cache
def get_lan_ip_address() -> str:
    """
    Get the LAN-local IP address of this host that is on the same subnet with the default gateway
    router. This will be the address that should be used for port-forwarding.
    """
    # Get info about the route to an arbitrary internet host (Google's DNS servers)
    info = get_internet_route_info()
    return info.local_lan_addr

@cache
def get_gateway_lan_ip_address() -> str:
    """
    Get the LAN-local IP address of the default gateway
    router.
    """
    # Get info about the route to an arbitrary internet host (Google's DNS servers)
    info = get_internet_route_info()
    return info.gateway_lan_addr

@cache
def get_default_interface() -> str:
    """
    Get the name of the network interface that is on the route to the default gateway router.
    """
    # Get info about the route to an arbitrary internet host (Google's DNS servers)
    info = get_internet_route_info()
    return info.network_interface

def loads_ndjson(text: str) -> List[JsonableDict]:
    """
    Parse a string containing newline-delimited JSON into a list of objects
    """
    result: List[JsonableDict] = list(json.loads(line) for line in text.split("\n") if line != "")
    assert isinstance(result, list)
    return result

def ndjson_to_dict(text:str, key_name: str="Name") -> Dict[str, JsonableDict]:
    """
    Parse a string containing newline-delimited JSON objects, each with a key property,
    into a dictionary of objects.
    """
    data = loads_ndjson(text)
    result: Dict[str, JsonableDict] = {}
    for item in data:
        if not isinstance(item, dict):
            raise HubError("ndjson Object is not a dictionary")
        key = item.get(key_name)
        if key is None:
            raise HubError(f"ndjson Object is missing key {key_name}")
        if not isinstance(key, str):
            raise HubError(f"ndjson Object key {key_name} is not a string")
        result[key] = item
    return result

def docker_call(
        args: List[str],
        env: Optional[_ENV]=None,
        cwd: Optional[StrOrBytesPath]=None,
        stderr_exception: bool=True,
      ) -> None:
    """
    Call docker with the given arguments.
    Automatically uses sudo if login session is not yet in the "docker" group.
    If an error occurs, stderr output is printed and an exception is raised.
    """
    logger.debug(f"docker_call: Running {['docker']+args}, cwd={cwd!r}")
    if stderr_exception:
        sudo_check_call_stderr_exception(
            ["docker"] + args,
            use_sudo=False,
            run_with_group="docker",
            env=env,
            cwd=cwd,
        )
    else:
        sudo_check_call(
            ["docker"] + args,
            use_sudo=False,
            run_with_group="docker",
            env=env,
            cwd=cwd,
        )

def docker_call_output(
        args: List[str],
        env: Optional[_ENV]=None,
        cwd: Optional[StrOrBytesPath]=None,
        stderr_exception: bool=True,
      ) -> str:
    """
    Call docker with the given arguments and return the stdout text
    Automatically uses sudo if login session is not yet in the "docker" group.
    If an error occurs, stderr output is printed and an exception is raised.
    """
    logger.debug(f"docker_call_output: Running {['docker']+args}, cwd={cwd!r}")
    result_bytes: bytes
    if stderr_exception:
        result_bytes = cast(bytes, sudo_check_output_stderr_exception(
            ["docker"] + args,
            use_sudo=False,
            run_with_group="docker",
            env=env,
            cwd=cwd,
        ))
    else:
        result_bytes = cast(bytes, sudo_check_output(
            ["docker"] + args,
            use_sudo=False,
            run_with_group="docker",
            env=env,
            cwd=cwd,
        ))
    return result_bytes.decode("utf-8")

@cache
def get_docker_networks() -> Dict[str, JsonableDict]:
    """
    Get all docker networks
    """
    data_json = docker_call_output(
        ["network", "ls", "--format", "json"],
      )
    result = ndjson_to_dict(data_json)
    return result

def refresh_docker_networks() -> None:
    """
    Refresh the cache of docker networks
    """
    get_docker_networks.cache_clear()

def create_docker_network(name: str, driver: str="bridge", allow_existing: bool=True) -> None:
    """
    Create a docker network
    """
    if not (allow_existing and name in get_docker_networks()):
        try:
            docker_call(["network", "create", "--driver", driver, name])
        finally:
            refresh_docker_networks()

@cache
def get_docker_volumes() -> Dict[str, JsonableDict]:
    """
    Get all docker volumes
    """
    data_json = docker_call_output(
        ["volume", "ls", "--format", "json"],
      )
    result = ndjson_to_dict(data_json)
    return result

def refresh_docker_volumes() -> None:
    """
    Refresh the cache of docker volumes
    """
    get_docker_volumes.cache_clear()

def create_docker_volume(name: str, allow_existing: bool=True) -> None:
    """
    Create a docker volume
    """
    if not (allow_existing and name in get_docker_volumes()):
        try:
            docker_call(["volume", "create", name])
        finally:
            refresh_docker_volumes()

def docker_compose_call(
        args: List[str],
        env: Optional[_ENV]=None,
        cwd: Optional[StrOrBytesPath]=None,
        stderr_exception: bool=True,
      ) -> None:
    """
    Call docker-compose with the given arguments.
    Automatically uses sudo if login session is not yet in the "docker" group.
    If an error occurs, stderr output is printed and an exception is raised.
    """
    # use the "docker compose" plugin form
    docker_call(
        ["compose"] + args,
        env=env,
        cwd=cwd,
        stderr_exception=stderr_exception,
      )

def docker_compose_call_output(
        args: List[str],
        env: Optional[_ENV]=None,
        cwd: Optional[StrOrBytesPath]=None,
        stderr_exception: bool=True,
      ) -> str:
    """
    Call docker-compose with the given arguments and return the stdout text
    Automatically uses sudo if login session is not yet in the "docker" group.
    If an error occurs, stderr output is printed and an exception is raised.
    """
    # use the "docker compose" plugin form
    return docker_call_output(
        ["compose"] + args,
        env=env,
        cwd=cwd,
        stderr_exception=stderr_exception,
      )

def raw_resolve_public_dns(public_dns: str) -> JsonableDict:
    """
    Resolve a public DNS name to an IP address. Bypasses all host files, mDNS, intranet DNS servers etc.
    """
    http = urllib3.PoolManager()
    response = http.request("GET", "https://dns.google/resolve", fields=dict(name=public_dns))
    if response.status != 200:
        raise HubError(f"Failed to resolve public DNS name {public_dns}: {response.status} {response.reason}")
    data: JsonableDict = json.loads(response.data.decode("utf-8"))
    return data

def resolve_public_dns(public_dns: str, error_on_empty: bool = True) -> List[str]:
    """
    Resolve a public DNS name to one or more A record IP addresses. Bypasses all host files, mDNS, intranet DNS servers etc.
    """
    data = raw_resolve_public_dns(public_dns)
    results: List[str] = []
    if not "Status" in data:
        raise HubError(f"Failed to resolve public DNS name {public_dns}: No Status in response")
    if data["Status"] != 3:
        if data["Status"] != 0:
            raise HubError(f"Failed to resolve public DNS name {public_dns}: Status {data['Status']}")
        if not "Answer" in data:
            raise HubError(f"Failed to resolve public DNS name {public_dns}: No Answer in response")
        answers = data["Answer"]
        if not isinstance(answers, list):
            raise HubError(f"Failed to resolve public DNS name {public_dns}: Answer is not a list")
        for answer in answers:
            if not isinstance(answer, dict):
                raise HubError(f"Failed to resolve public DNS name {public_dns}: Answer entry is not a dictionary")
            if not "type" in answer:
                raise HubError(f"Failed to resolve public DNS name {public_dns}: Answer entry is missing type field")
            if answer["type"] == 1:
                if not "data" in answer:
                    raise HubError(f"Failed to resolve public DNS name {public_dns}: Answer entry is missing data field")
                result = answer["data"]
                if not isinstance(result, str):
                    raise HubError(f"Failed to resolve public DNS name {public_dns}: Answer entry data field is not a string")
                results.append(result)
    if len(results) == 0 and error_on_empty:
        raise HubError(f"Failed to resolve public DNS name {public_dns}: No A records found")
    return results

_KT = TypeVar("_KT")
_VT = TypeVar("_VT")
MappingScalarValue  = Union[int, float, bool, str, bytes]
MappingValue = Union[MappingScalarValue, Mapping[_KT, Any], Sequence[Any]]
MutableMappingValue = Union[MappingScalarValue, MutableMapping[_KT, Any], MutableSequence[Any]]

def shallow_make_mutable(value: MappingValue) -> MutableMappingValue:
    if isinstance(value, Mapping) and not isinstance(value, MutableMapping):
        value = dict(value)
    elif isinstance(value, Sequence) and not isinstance(value, MutableSequence):
        value = list(value)
    return value

def shallow_copy_mutable(value: MappingValue) -> MutableMappingValue:
    value = copy.copy(value)
    value = shallow_make_mutable(value)
    return value

def deep_make_mutable(value: MappingValue) -> MutableMappingValue:
    mutable_value = shallow_make_mutable(value)
    if isinstance(mutable_value, Mapping):
        assert isinstance(mutable_value, MutableMapping)
        for k, v in mutable_value.items():
            if ((isinstance(v, Mapping) and not isinstance(v, MutableMapping)) or
                (isinstance(v, Sequence) and not isinstance(v, MutableSequence))):
                mutable_value[k] = deep_make_mutable(v)
    elif isinstance(mutable_value, Sequence):
        assert isinstance(mutable_value, MutableSequence)
        for i, v in enumerate(mutable_value):
            if ((isinstance(v, Mapping) and not isinstance(v, MutableMapping)) or
                (isinstance(v, Sequence) and not isinstance(v, MutableSequence))):
                mutable_value[i] = deep_make_mutable(v)
    return mutable_value


def deep_copy_mutable(value: MappingValue) -> MutableMappingValue:
    result = copy.deepcopy(value)
    result = deep_make_mutable(result)
    return result

def deep_merge_mutable(
        dest: MappingValue,
        source: MappingValue,
        allow_retype_mapping: bool=False
      ) -> MutableMappingValue:

    result: MutableMappingValue
    if isinstance(dest, Mapping):
        if isinstance(source, Mapping):
            # Merging source map into dest map
            # If dest is not mutable, convert it into a dict
            mutable_dest = shallow_make_mutable(dest)
            assert isinstance(mutable_dest, MutableMapping)
            for k, v in source.items():
                if k in mutable_dest:
                    # key is present; just recurse to update it
                    new_v = deep_merge_mutable(mutable_dest[k], v, allow_retype_mapping=allow_retype_mapping)
                else:
                    # key is not present. make a deep mutable copy of source value.
                    new_v = deep_copy_mutable(v)
                if not v is new_v:
                    mutable_dest[k] = new_v
            result = mutable_dest
        else:
            # replacing a mapping with something else
            if not allow_retype_mapping:
                raise HubError(
                    f"While merging data, an attempt was made to replace a Mapping type "
                    f"{dest.__class__.__name__} with non-mapping type {source.__class__.__name__}")
            result = deep_copy_mutable(source)
    else:
        result = deep_copy_mutable(source)
    return result

@overload
def normalize_update_args(other: Mapping[_KT, _VT], __m: SupportsKeysAndGetItem[_KT, _VT], **kwargs: _VT) -> List[Tuple[_KT, _VT]]: ...

@overload
def normalize_update_args(other: Iterable[Tuple[_KT, _VT]], **kwargs: _VT) -> List[Tuple[_KT, _VT]]: ...

@overload
def normalize_update_args(other: Mapping[_KT, _VT], **kwargs: _VT) -> List[Tuple[_KT, _VT]]: ...

@overload
def normalize_update_args(other: None, **kwargs: _VT) -> List[Tuple[_KT, _VT]]: ...

def normalize_update_args(other=None, /, **kwargs):
    """
    Normalize the arguments to MutableMapping.update() to be a list of key-value tuples
    """
    result = []
    if not other is None:
        if isinstance(other, Mapping):
            for key in other:
                result.append((key, other[key]))
        elif hasattr(other, "keys"):
            for key in other.keys():
                result.append((key, other[key]))
        else:
            for key, value in other:
                result.append((key, value))
    for key, value in kwargs.items():
        result.append((key, value))
    return result

@overload
def deep_update_mutable(dest: MutableMapping[str, _VT], other: SupportsKeysAndGetItem[_KT, _VT], **kwargs: _VT) -> MutableMapping[_KT, _VT]: ...

@overload
def deep_update_mutable(dest: MutableMapping[str, _VT], other: Iterable[Tuple[_KT, _VT]], **kwargs: _VT) -> MutableMapping[_KT, _VT]: ...

@overload
def deep_update_mutable(dest: MutableMapping[str, _VT], **kwargs: _VT) -> MutableMapping[_KT, _VT]: ...

def deep_update_mutable(
        dest,
        other=None,
        /,
        **kwargs
      ):
    updates = normalize_update_args(other, **kwargs)
    update_mapping = dict(updates)
    mutable_dest = deep_merge_mutable(dest, update_mapping)
    assert isinstance(mutable_dest, MutableMapping)
    return mutable_dest
