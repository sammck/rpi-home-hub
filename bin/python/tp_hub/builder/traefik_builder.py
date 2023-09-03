#
# Copyright (c) 2023 Samuel J. McKelvie
#
# MIT License - See LICENSE file accompanying this package.
#

"""
Builder tools for traefik
"""

import os

from ..internal_types import *
from ..pkg_logging import logger
from ..util import rel_symlink
from ..config import HubSettings, current_hub_settings
from ..proj_dirs import get_project_dir, get_project_build_dir
from ..x_dotenv import x_dotenv_save_file

def build_traefik(settings: Optional[HubSettings]=None):
    if settings is None:
        settings = current_hub_settings()

    logger.info("Building Traefik")

    project_dir = get_project_dir()
    src_dir = os.path.join(project_dir, "stacks", "traefik")
    build_dir = get_project_build_dir()
    os.makedirs(build_dir, exist_ok=True)
    dst_dir = os.path.join(build_dir, "stacks", "traefik")
    os.makedirs(dst_dir, mode=0o700, exist_ok=True)
    src_compose_pathname = os.path.join(src_dir, "docker-compose.yml")
    dst_compose_pathname = os.path.join(dst_dir, "docker-compose.yml")
    src_env_pathname = os.path.join(src_dir, ".env")
    dst_env_pathname = os.path.join(dst_dir, ".env")
    if not os.path.islink(src_env_pathname):
        rel_symlink(dst_env_pathname, src_env_pathname)
    if os.path.exists(dst_compose_pathname) or os.path.islink(dst_compose_pathname):
        os.unlink(dst_compose_pathname)
    rel_symlink(src_compose_pathname, dst_compose_pathname)
    env = dict(settings.traefik_stack_env)
    x_dotenv_save_file(dst_env_pathname, env)

    logger.info("Traefik build complete")
