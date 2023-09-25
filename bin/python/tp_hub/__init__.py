#!/usr/bin/env python3

"""
Handy Python utilities for this project
"""

from .version import __version__

from .internal_types import *

from .pkg_logging import logger

from .config import (
    HubConfigError,
    HubSettings,
    hub_settings,
    clear_hub_settings_cache,
    current_hub_settings,
    set_current_hub_settings,
    init_current_hub_settings,
    clear_current_hub_settings,
    clear_config_yml_cache,
    get_config_yml_pathname,
    get_config_yml,
    get_roundtrip_config_yml,
    save_roundtrip_config_yml,
    get_config_yml_property,
    set_config_yml_property,
  )

from .proj_dirs import (
    get_tp_hub_package_dir,
    get_project_python_dir,
    get_project_bin_dir,
    get_project_dir,
    get_pkg_data_dir,
    set_project_dir,
    get_project_bin_data_dir,
    get_project_build_dir,
  )

from .util import (
    normalize_ip_address,
    normalize_ipv4_address,
    normalize_ipv6_address,
    is_ip_address,
    is_ipv4_address,
    is_ipv6_address,
    Ipv6RouteInfo,
    Ipv4RouteInfo,
    get_public_ipv4_egress_address,
    get_ipv4_route_info,
    get_internet_ipv4_route_info,
    get_lan_ipv4_address,
    get_gateway_lan_ip4_address,
    get_default_ipv4_interface,
    get_public_ipv6_egress_address,
    get_ipv6_route_info,
    get_internet_ipv6_route_info,
    get_routed_egress_ipv6_address,
    get_gateway_lan_ip6_address,
    get_default_ipv6_interface,
    docker_call,
    docker_call_output,
    docker_compose_call,
    docker_compose_call_output,
    loads_ndjson,
    get_docker_networks,
    get_docker_volumes,
    create_docker_network,
    create_docker_volume,
    docker_is_installed,
    install_docker,
    docker_compose_is_installed,
    install_docker_compose,
    docker_compose_is_installed,
    install_aws_cli,
    aws_cli_is_installed,
    should_run_with_group,
    sudo_check_call_stderr_exception,
    sudo_check_output_stderr_exception,
    download_url_text,
    resolve_public_dns,
    raw_resolve_public_dns,
    unindent_text,
    unindent_string_literal,
    is_valid_ipv4_address,
    is_valid_dns_name,
    is_valid_dns_name_or_ipv4_address,
    is_valid_email_address,
    rel_symlink,
    atomic_mv,
  )

from .docker_util import (
    read_docker_volume_text_file,
    write_docker_volume_text_file,
    list_files_in_docker_volume,
    remove_docker_volume_file,
    docker_volume_exists,
    verify_docker_volume_exists,
  )

from .acme_util import (
    list_traefik_acme_files,
    load_traefik_acme_data,
    save_traefik_acme_data,
    get_acme_domain_data
  )

from .password_hash import hash_password, check_password, hash_username_password, check_username_password

from .docker_compose_stack import DockerComposeStack

from .x_dotenv import (
    x_dotenv_loads,
    x_dotenv_load_file,
    x_dotenv_dumps,
    x_dotenv_save_file,
    x_dotenv_update_file,  
)

from .builder import (
    build_traefik,
    build_portainer,
    build_hub,
  )

from .yaml_template import load_yaml_template_str, load_yaml_template_file
