#
# Copyright (c) 2023 Samuel J. McKelvie
#
# MIT License - See LICENSE file accompanying this package.
#

"""
Config file support
"""

import sys
import yaml
import os
from copy import deepcopy
from functools import cache
from threading import Lock

from pydantic import (
    BaseModel,
    Field,
    validator,
)

from pydantic.fields import FieldInfo

from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
    PydanticBaseSettingsSource,
  )

from ..proj_dirs import get_project_dir
from ..util import (
    unindent_string_literal as usl,
    is_valid_email_address,
    is_valid_dns_name,
  )
from ..version import __version__ as pkg_version
from .yaml_config_settings_source import YAMLConfigSettingsSource
from ..pkg_logging import logger

from ..internal_types import *

class HubConfigError(HubError):
    """An error related to hub configuration"""
    pass

class EnvVarsModel(BaseModel):
    """A model for a collection of environment variable key/value pairsthat can be passed to
       docker-compose stacks, etc.
    """
    model_config = SettingsConfigDict(
        extra='allow'
    )


class HubSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file_encoding='utf-8',
        env_prefix='tp_hub_',
        env_nested_delimiter='__',
      )

    # @override
    @classmethod
    def settings_customise_sources(
            cls,
            settings_cls: Type[BaseSettings],
            init_settings: PydanticBaseSettingsSource,
            env_settings: PydanticBaseSettingsSource,
            dotenv_settings: PydanticBaseSettingsSource,
            file_secret_settings: PydanticBaseSettingsSource,
          ) -> Tuple[PydanticBaseSettingsSource, ...]:
        """
        Return the settings sources in order from highest precendence to lowest.

        Each returned source, when later called, will return a deep, possibly incomplete dictionary of key/value pairs that will be
        used to populate the settings model.

        Later, an empty aggregate dict will be created, and then the sources will be called in order from lowest to highest priority
        (the opposite of the order returned by this function), and the values from each source are deeply merged into (i.e., override) the
        running aggregate dict

        The arguments after settings_cls are the traditional, default sources that would be used if there were
        no override. Subclasses that override this method should not change the function signature, but can
        override the default sources by returning a different tuple of sources.

        Args:
            settings_cls: The Settings class.
            init_settings: The `InitSettingsSource` instance.
            env_settings: The `EnvSettingsSource` instance.
            dotenv_settings: The `DotEnvSettingsSource` instance.
            file_secret_settings: The `SecretsSettingsSource` instance.

        Returns:
            A tuple containing the sources in order from highest to lowest precedence.
            The default implementation returns the following tuple:
                    (init_settings, env_settings, dotenv_settings, file_secret_settings)
        """
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
            YAMLConfigSettingsSource(settings_cls),
        )

    
    hub_package_version: str = Field(default=pkg_version, description=usl(
        """The Hub package version for which the configuration was authored.
          If not provided, the current package version is used."""
      ))
    """The Hub package version for which the configuration was authored.
       If not provided, the current package version is used."""

    allowed_cert_resolvers: Set[str] = Field(default=None, description=usl(
        """A set of allowed certificate resolver names. May be provided as a list/set or a comma-delimited
           string. The default is ['prod', 'staging'].
           You should not need to override this unless you are using a custom certificate resolver.
        """
      ))
    """A list of allowed certificate resolver names. May be provided as a list or a comma-delimited
       string. The default is ['prod', 'staging'].
       You should not need to override this unless you are using a custom certificate resolver."""

    @validator('allowed_cert_resolvers', pre=True, always=True)
    def allowed_cert_resolvers_validator(cls, v, values, **kwargs):
        sname = 'allowed_cert_resolvers'
        logger.debug(f"{sname}_validator: v={v}, values={values}, kwargs={kwargs}")
        r = v
        if r is None:
            r = ['prod', 'staging']
        if isinstance(r, str):
            if r == '':
                r = []
            else:
                r = r.split(',')
        if not isinstance(r, Iterable):
            raise HubConfigError(f"Setting {sname}={v!r} must be a comma-delimited string or iterable; edit config.yml")
        r = set(x for x in r)
        for resolver in r:
            if not isinstance(resolver, str) or len(resolver) == 0 or "." in resolver:
                raise HubConfigError(f"Setting {sname}={v!r} must be a valid list or comma-delimited list of simple identifiers; edit config.yml")
        return r
        

    parent_dns_domain: str = Field(default=None, description=usl(
        """The registered public DNS domain under which subdomains are created
        as needed for added web services. You must be able to create DNS
        record sets in this domain. If hosted on AWS Route53, tools are
        provided to automate this. Also becomes the default value for
        Traefik and Portainer PARENT_DNS_DOMAIN stack variable.
        REQUIRED."""
      ))
    """The registered public DNS domain under which subdomains are created
    as needed for added web services. You must be able to create DNS
    record sets in this domain. If hosted on AWS Route53, tools are
    provided to automate this. Also becomes the default value for
    Traefik and Portainer PARENT_DNS_DOMAIN stack variable.
    REQUIRED."""

    @validator('parent_dns_domain', pre=True, always=True)
    def parent_dns_domain_validator(cls, v, values, **kwargs):
        sname = 'parent_dns_domain'
        logger.debug(f"{sname}_validator: v={v}, values={values}, kwargs={kwargs}")
        if v is None:
            raise HubConfigError(f"Setting {sname} is required; edit config.yml")
        if not is_valid_dns_name(v):
            raise HubConfigError(f"Setting '{sname}'={v!r} must be a valid DNS name; edit config.yml")
        return v
        
    admin_parent_dns_domain: str = Field(default=None, description=usl(
        """The registered public DNS domain under which the "traefik."
        and "portainer." subdomains are created to access the Traefik
        and Portainer web interfaces. You must be able to create DNS
        record sets in this domain. If hosted on AWS Route53, tools are
        provided to automate this. By default, the value of
        parent_dns_domain is used."""
      ))
    """The registered public DNS domain under which the "traefik."
    and "portainer." subdomains are created to access the Traefik
    and Portainer web interfaces. You must be able to create DNS
    record sets in this domain. If hosted on AWS Route53, tools are
    provided to automate this. By default, the value of
    parent_dns_domain is used."""

    @validator('admin_parent_dns_domain', pre=True, always=True)
    def admin_parent_dns_domain_validator(cls, v, values, **kwargs):
        sname = 'admin_parent_dns_domain'
        logger.debug(f"{sname}_validator: v={v}, values={values}, kwargs={kwargs}")
        if v is None:
            v = values['parent_dns_domain']
        if not is_valid_dns_name(v):
            raise HubConfigError(f"Setting {sname}={v!r} must be a valid DNS name; edit config.yml")
        return v
        
    letsencrypt_owner_email: str = Field(default=None, description=usl(
        """The default email address to use for Let's Encrypt registration  to produce
        SSL certificates. If not provided, and this project is a git clone of the
        rpi-hub project, the value from git config user.email is used. Otherwise, REQUIRED."""
      ))
    """The default email address to use for Let's Encrypt registration  to produce
    SSL certificates. If not provided, and this project is a git clone of the
    rpi-hub project, the value from git config user.email is used. Otherwise, REQUIRED."""

    @validator('letsencrypt_owner_email', pre=True, always=True)
    def letsencrypt_owner_email_validator(cls, v, values, **kwargs):
        sname = 'letsencrypt_owner_email'
        logger.debug(f"{sname}_validator: v={v}, values={values}, kwargs={kwargs}")
        if v is None:
            raise HubConfigError(f"Setting {sname} is required; edit config.yml")
        if not is_valid_email_address(v):
            raise HubConfigError(f"Setting {sname}={v!r} must be a valid email address; edit config.yml")
        return v

    letsencrypt_owner_email_prod: str = Field(default=None, description=usl(
        """The email address to use for Let's Encrypt registration in the "prod"
        name resolver, which produces genuine valid certificates. If not provided,
        the value from letsencrypt_owner_email is used."""
      ))
    """The email address to use for Let's Encrypt registration in the "prod"
    name resolver, which produces genuine valid certificates. If not provided,
    the value from letsencrypt_owner_email is used."""

    @validator('letsencrypt_owner_email_prod', pre=True, always=True)
    def letsencrypt_owner_email_prod_validator(cls, v, values, **kwargs):
        sname = 'letsencrypt_owner_email_prod'
        logger.debug(f"{sname}_validator: v={v}, values={values}, kwargs={kwargs}")
        if v is None:
            v = values['letsencrypt_owner_email']
        if not is_valid_email_address(v):
            raise HubConfigError(f"Setting {sname}={v!r} must be a valid email address; edit config.yml")
        return v

    letsencrypt_owner_email_staging: str = Field(default=None, description=usl(
        """The email address to use for Let's Encrypt registration in the "staging"
        name resolver, which produces untrusted certificates for testing purposes.
        Using the staging resolver avoids hitting rate limits on the prod resolver.
        If not provided, the value from letsencrypt_owner_email is used."""
      ))
    """The email address to use for Let's Encrypt registration in the "staging"
    name resolver, which produces untrusted certificates for testing purposes.
    Using the staging resolver avoids hitting rate limits on the prod resolver.
    If not provided, the value from letsencrypt_owner_email is used."""

    @validator('letsencrypt_owner_email_staging', pre=True, always=True)
    def letsencrypt_owner_email_staging_validator(cls, v, values, **kwargs):
        sname = 'letsencrypt_owner_email_staging'
        logger.debug(f"{sname}_validator: v={v}, values={values}, kwargs={kwargs}")
        if v is None:
            v = values['letsencrypt_owner_email']
        if not is_valid_email_address(v):
            raise HubConfigError(f"Setting {sname}={v!r} must be a valid email address; edit config.yml")
        return v

    default_cert_resolver: str = Field(default=None, description=usl(
        """The default name of the Traefik certificate resolver to use for HTTPS/TLS
        routes. Generally, this should be "prod" for production use (real certs),
        and "staging" for testing purposes (untrusted certs).
        If not provided, "staging" is used."""
      ))
    """The default name of the Traefik certificate resolver to use for HTTPS/TLS
    routes. Generally, this should be "prod" for production use (real certs),
    and "staging" for testing purposes (untrusted certs).
    If not provided, "staging" is used."""

    @validator('default_cert_resolver', pre=True, always=True)
    def default_cert_resolver_validator(cls, v, values, **kwargs):
        sname = 'default_cert_resolver'
        logger.debug(f"{sname}_validator: v={v}, values={values}, kwargs={kwargs}")
        if v is None:
            v = "staging"
        if not v in values['allowed_cert_resolvers']:
            raise HubConfigError(f"Setting {sname}={v!r} must be one of {list(values['allowed_cert_resolvers'])}; edit config.yml")
        return v

    admin_cert_resolver: str = Field(default=None, description=usl(
        """The default name of the Traefik certificate resolver to use for HTTPS/TLS
        routes for the Traefik dashboard and Portainer web interface. By default,
        "prod" is used."""
      ))
    """The default name of the Traefik certificate resolver to use for HTTPS/TLS
    routes for the Traefik dashboard and Portainer web interface. By default,
    "prod" is used."""

    @validator('admin_cert_resolver', pre=True, always=True)
    def admin_cert_resolver_validator(cls, v, values, **kwargs):
        sname = 'admin_cert_resolver'
        logger.debug(f"{sname}_validator: v={v}, values={values}, kwargs={kwargs}")
        if v is None:
            v = "prod"
        if not v in values['allowed_cert_resolvers']:
            raise HubConfigError(f"Setting {sname}={v!r} must be one of {list(values['allowed_cert_resolvers'])}; edit config.yml")
        return v

    traefik_dashboard_cert_resolver: str = Field(default=None, description=usl(
        """The name of the Traefik certificate resolver to use for the Traefik dashboard.
        By default, the value of admin_cert_resolver is used."""
      ))
    """The name of the Traefik certificate resolver to use for the Traefik dashboard.
    By default, the value of admin_cert_resolver is used."""

    @validator('traefik_dashboard_cert_resolver', pre=True, always=True)
    def traefik_dashboard_cert_resolver_validator(cls, v, values, **kwargs):
        sname = 'traefik_dashboard_cert_resolver'
        logger.debug(f"{sname}_validator: v={v}, values={values}, kwargs={kwargs}")
        if v is None:
            v = values['admin_cert_resolver']
        if not v in values['allowed_cert_resolvers']:
            raise HubConfigError(f"Setting {sname}={v!r} must be one of {list(values['allowed_cert_resolvers'])}; edit config.yml")
        return v

    portainer_cert_resolver: str = Field(default=None, description=usl(
        """The name of the Traefik certificate resolver to use for the Portainer web interface.
        By default, the value of admin_cert_resolver is used."""
      ))
    """The name of the Traefik certificate resolver to use for the Portainer web interface.
    By default, the value of admin_cert_resolver is used."""

    @validator('portainer_cert_resolver', pre=True, always=True)
    def portainer_cert_resolver_validator(cls, v, values, **kwargs):
        sname = 'portainer_cert_resolver'
        logger.debug(f"{sname}_validator: v={v}, values={values}, kwargs={kwargs}")
        if v is None:
            v = values['admin_cert_resolver']
        if not v in values['allowed_cert_resolvers']:
            raise HubConfigError(f"Setting {sname}={v!r} must be one of {list(values['allowed_cert_resolvers'])}; edit config.yml")
        return v

    portainer_agent_secret: str = Field(default=None, description=usl(
        """A random string used to secure communication between Portainer and the Portainer
        agent. Typically 32 hex digits.
        REQUIRED (generated and installed in user config by provisioning tools)."""
      ))
    """A random string used to secure communication between Portainer and the Portainer
    agent. Typically 32 hex digits.
    REQUIRED (generated and installed in user config by provisioning tools)."""

    @validator('portainer_agent_secret', pre=True, always=True)
    def portainer_agent_secret_validator(cls, v, values, **kwargs):
        sname = 'portainer_agent_secret'
        logger.debug(f"{sname}_validator: v={v}, values={values}, kwargs={kwargs}")
        if v is None:
            raise HubConfigError(f"Setting {sname} is required; use 'hub config set-portainer-secret' to set it to a random value")
        if not isinstance(v, str) or len(v) < 16:
            raise HubConfigError(f"Setting '{sname}'={v!r} must be a secret string >= 16 characters long; use 'hub config set-portainer-secret' to set it to a random value")
        return v

    traefik_dashboard_htpasswd: str = Field(default=None, description=usl(
        """The admin username and bcrypt-hashed password to use for HTTP Basic authhentication on
        the Traefik dashboard. The value of this string is of the form "username:hashed_password",
        and can be generated using the `htpasswd -nB admin` or tools included in this project.
        This value is sensitive, and should not be stored in a git repository. Also, a hard-to-guess
        password should be used to defend against a dictionary attack if the hash is ever compromised.
        Note that this value may contain dollar-signs, so when it is passed to docker-compose
        via an environment variable, all dollar-signs must be doubled to escape them (they
        are not doubled here).
        Example: 'admin:$2y$05$LCmVF2WJY/Ue0avRDcsDmelPqzXQcMIXoRxHF3bR62HuIP.fqqqZm'
        REQUIRED (generated and installed in user config by provisioning tools)."""
      ))
    """The admin username and bcrypt-hashed password to use for HTTP Basic authhentication on
    the Traefik dashboard. The value of this string is of the form "username:hashed_password",
    and can be generated using the `htpasswd -nB admin` or tools included in this project.
    This value is sensitive, and should not be stored in a git repository. Also, a hard-to-guess
    password should be used to defend against a dictionary attack if the hash is ever compromised.
    Note that this value may contain dollar-signs, so when it is passed to docker-compose
    via an environment variable, all dollar-signs must be doubled to escape them (they
    are not doubled here).
    Example: 'admin:$2y$05$LCmVF2WJY/Ue0avRDcsDmelPqzXQcMIXoRxHF3bR62HuIP.fqqqZm'
    REQUIRED (generated and installed in user config by provisioning tools)."""

    @validator('traefik_dashboard_htpasswd', pre=True, always=True)
    def traefik_dashboard_htpasswd_validator(cls, v, values, **kwargs):
        sname = 'traefik_dashboard_htpasswd'
        logger.debug(f"{sname}_validator: v={v}, values={values}, kwargs={kwargs}")
        if v is None:
            raise HubConfigError(f"Setting {sname} is required; generate a username/password hash and set it with 'hub config set-traefik-password'")
        if not isinstance(v, str):
            raise HubConfigError(f"Setting '{sname}'={v!r} must be a string; generate a username/password hash and set it with 'hub config set-traefik-password'")
        parts = v.split(':', 1)
        if len(parts) != 2 or len(parts[0]) == 0 or len(parts[1]) < 20 or not parts[1].startswith('$2'):
            raise HubConfigError(f"Setting '{sname}'={v!r} must be a string of the form '<username>:<bcrypt-hashed-password>'; generate a username/password hash and set it with 'hub config set-traefik-password'")
        return v

    stable_public_dns_name: str = Field(default=None, description=usl(
        """A permanent DNS name (e.g., ddns.mydnsname.com) that has been configured to always
        resolve to the current public IP address of your network's gateway router. Since typical
        residential ISPs may change your public IP address periodically, it is usually necessary to
        involve Dynamic DNS (DDNS) to make this work. Some gateway routers (e.g., eero) have DDNS
        support built-in. Otherwise, you can run a DDNS client agent on any host inside your network,
        and use a DDNS provider such as noip.com.
        Your DDNS provider will provide you with an obscure but unique and stable (as long as you stay
        with the DDNS provider) DNS name for your gateway's public IP address; e.g.,
        "g1234567.eero.online". You should then create a permanent CNAME entry (e.g., ddns.mydnsname.com)
        that points at the obscure DDNS name. That additional level of indirection makes an
        easy-to-remember DNS name for your network's public IP address, and ensures that if your
        provided obscure name ever changes, you will only have to update this one CNAME record to
        be back in business.
        All DNS names created by this project will be CNAME records that point to this DNS name.
        As a convenience, if this value is a sinple subdomain name with no dots, it will be
        automatically prepended to the value of admin_parent_dns_domain to form the full DNS name.
        The default value is "ddns"."""
      ))
    """A permanent DNS name (e.g., ddns.mydnsname.com) that has been configured to always
    resolve to the current public IP address of your network's gateway router. Since typical
    residential ISPs may change your public IP address periodically, it is usually necessary to
    involve Dynamic DNS (DDNS) to make this work. Some gateway routers (e.g., eero) have DDNS
    support built-in. Otherwise, you can run a DDNS client agent on any host inside your network,
    and use a DDNS provider such as noip.com.
    Your DDNS provider will provide you with an obscure but unique and stable (as long as you stay
    with the DDNS provider) DNS name for your gateway's public IP address; e.g.,
    "g1234567.eero.online". You should then create a permanent CNAME entry (e.g., ddns.mydnsname.com)
    that points at the obscure DDNS name. That additional level of indirection makes an
    easy-to-remember DNS name for your network's public IP address, and ensures that if your
    provided obscure name ever changes, you will only have to update this one CNAME record to
    be back in business.
    All DNS names created by this project will be CNAME records that point to this DNS name.
    As a convenience, if this value is a sinple subdomain name with no dots, it will be
    automatically prepended to the value of admin_parent_dns_domain to form the full DNS name.
    The default value is "ddns"."""

    @validator('stable_public_dns_name', pre=True, always=True)
    def stable_public_dns_name_validator(cls, v, values, **kwargs):
        sname = 'stable_public_dns_name'
        logger.debug(f"{sname}_validator: v={v}, values={values}, kwargs={kwargs}")
        if v is None:
            v = 'ddns'
        if '.' not in v:
            v = f"{v}.{values['admin_parent_dns_domain']}"
        if not is_valid_dns_name(v):
            raise HubConfigError(f"Setting {sname}={v!r} must be a valid DNS name or simple subdomain; edit config.yml")
        return v

    traefik_dashboard_dns_name: str = Field(default=None, description=usl(
        """The DNS name that is used for the traefik dashboard. If this is a simple subdomain with no dots, it will
          be prepended to the value of admin_parent_dns_domain to form the full DNS name. The default value is "traefik"."""
      ))
    """The DNS name that is used for the traefik dashboard. If this is a simple subdomain with no dots, it will
       be prepended to the value of admin_parent_dns_domain to form the full DNS name. The default value is "traefik"."""

    @validator('traefik_dashboard_dns_name', pre=True, always=True)
    def traefik_dashboard_dns_name_validator(cls, v, values, **kwargs):
        sname = 'stable_traefik_dashboard_dns_name'
        logger.debug(f"{sname}_validator: v={v}, values={values}, kwargs={kwargs}")
        if v is None:
            v = 'traefik'
        if '.' not in v:
            v = f"{v}.{values['admin_parent_dns_domain']}"
        if not is_valid_dns_name(v):
            raise HubConfigError(f"Setting {sname}={v!r} must be a valid DNS name or simple subdomain; edit config.yml")
        return v

    portainer_dns_name: str = Field(default=None, description=usl(
        """The DNS name that is used for the Portainer web UI. If this is a simple subdomain with no dots, it will
          be prepended to the value of admin_parent_dns_domain to form the full DNS name. The default value is "portainer"."""
      ))
    """The DNS name that is used for the Portainer web UI. If this is a simple subdomain with no dots, it will
       be prepended to the value of admin_parent_dns_domain to form the full DNS name. The default value is "portainer"."""

    @validator('portainer_dns_name', pre=True, always=True)
    def portainer_dns_name_validator(cls, v, values, **kwargs):
        sname = 'portainer_dns_name'
        logger.debug(f"{sname}_validator: v={v}, values={values}, kwargs={kwargs}")
        if v is None:
            v = 'portainer'
        if '.' not in v:
            v = f"{v}.{values['admin_parent_dns_domain']}"
        if not is_valid_dns_name(v):
            raise HubConfigError(f"Setting {sname}={v!r} must be a valid DNS name or simple subdomain; edit config.yml")
        return v

    shared_app_dns_name: str = Field(default=None, description=usl(
        """The DNS name to use for general-purpose path-routed web services created by Portainer.
          this allows multiple simple services to share a single provisioned DNS name and certificate
          if they can be routed with a traefik Path or PathPrefix rule. If this is a simple subdomain with no dots,
          it will be prepended to the value of parent_dns_domain to form the full DNS name. The default value is "hub"."""
      ))
    """The DNS name to use for general-purpose path-routed web services created by Portainer.
       this allows multiple simple services to share a single provisioned DNS name and certificate
       if they can be routed with a traefik Path or PathPrefix rule. If this is a simple subdomain with no dots,
       it will be prepended to the value of parent_dns_domain to form the full DNS name. The default value is "hub"."""

    @validator('shared_app_dns_name', pre=True, always=True)
    def shared_app_dns_name_validator(cls, v, values, **kwargs):
        sname = 'shared_app_dns_name'
        logger.debug(f"{sname}_validator: v={v}, values={values}, kwargs={kwargs}")
        if v is None:
            v = 'hub'
        if '.' not in v:
            v = f"{v}.{values['parent_dns_domain']}"
        if not is_valid_dns_name(v):
            raise HubConfigError(f"Setting {sname}={v!r} must be a valid DNS name or simple subdomain; edit config.yml")
        return v

    shared_app_cert_resolver: str = Field(default=None, description=usl(
        """The default name of the Traefik certificate resolver to use for HTTPS/TLS
           routes using the shared app DNS name. Generally, this should be "prod"
           once the shared app DNS route has been validated, or "staging"
           for testing purposes (untrusted certs). If not provided, the value of
           default_cert_resolver is used."""
      ))
    """The default name of the Traefik certificate resolver to use for HTTPS/TLS
       routes using the shared app DNS name. Generally, this should be "prod"
       once the shared app DNS route has been validated, or "staging"
       for testing purposes (untrusted certs). If not provided, the value of
       default_cert_resolver is used."""

    @validator('shared_app_cert_resolver', pre=True, always=True)
    def shared_app_cert_resolver_validator(cls, v, values, **kwargs):
        sname = 'shared_app_cert_resolver'
        logger.debug(f"{sname}_validator: v={v}, values={values}, kwargs={kwargs}")
        if v is None:
            v = values['default_cert_resolver']
        if not v in values['allowed_cert_resolvers']:
            raise HubConfigError(f"Setting {sname}={v!r} must be one of {list(values['allowed_cert_resolvers'])}; edit config.yml")
        return v

    @classmethod    
    def _validate_env_dict(cls, field_name: str, v, values, base_env: Optional[Dict[str, str]]=None, **kwargs) -> Dict[str, str]:
        logger.debug(f"{field_name}_validator: v={v}, values={values}, kwargs={kwargs}")
        if v is None:
            v = {}
        if not isinstance(v, dict):
            raise HubConfigError(f"Setting {field_name}={v!r} must be a dictionary; edit config.yml")
        if not base_env is None:
            v = { **base_env, **v }
        return v

    base_stack_env: Dict[str, str] = Field(default=None, description=usl(
        """Dictionary of environment variables that will be passed to all docker-compose stacks, including
           the Traefik and Portainer stacks, and stacks created by Portainer. Note that
           properties defined here will be installed directly into Portainer's runtime
           environment, and thus will be implicitly available for expansion in all docker-compose
           stacks started by Portainer."""
      ))
    """Dictionary of environment variables that will be passed to all docker-compose stacks, including
       the Traefik and Portainer stacks, and stacks created by Portainer. Note that
       properties defined here will be installed directly into Portainer's runtime
       environment, and thus will be implicitly available for expansion in all docker-compose
       stacks started by Portainer."""

    @validator('base_stack_env', pre=True, always=True)
    def base_stack_env_validator(cls, v, values, **kwargs):
        sname = 'base_stack_env'
        logger.debug(f"{sname}_validator: v={v}, values={values}, kwargs={kwargs}")
        return cls._validate_env_dict(sname, v, values, **kwargs)

    traefik_stack_env: Dict[str, str] = Field(default=None, description=usl(
        """Dictionary of environment variables that will be passed to the Traefik docker-compose stack.
        Actual used dict is created from base_stack_env, with this dict overriding."""
      ))
    """Dictionary of environment variables that will be passed to the Traefik docker-compose stack.
    Actual used dict is created from base_stack_env, with this dict overriding."""

    @validator('traefik_stack_env', pre=True, always=True)
    def traefik_stack_env_validator(cls, v, values, **kwargs):
        sname = 'traefic_stack_env'
        logger.debug(f"{sname}_validator: v={v}, values={values}, kwargs={kwargs}")
        return cls._validate_env_dict(sname, v, values, base_env=values['base_stack_env'], **kwargs)

    portainer_stack_env: Dict[str, str] = Field(default=None, description=usl(
        """Dictionary of environment variables that will be passed to the Portainer docker-compose stack.
        Actual used dict is created from base_stack_env, with this dict overriding."""
      ))
    """Dictionary of environment variables that will be passed to the Portainer docker-compose stack.
    Actual used dict is created from base_stack_env, with this dict overriding."""

    @validator('portainer_stack_env', pre=True, always=True)
    def portainer_stack_env_validator(cls, v, values, **kwargs):
        sname = 'portainer_stack_env'
        logger.debug(f"{sname}_validator: v={v}, values={values}, kwargs={kwargs}")
        return cls._validate_env_dict(sname, v, values, base_env=values['base_stack_env'], **kwargs)

    base_app_stack_env: Dict[str, str] = Field(default=None, description=usl(
        """Dictionary of environment variables that should be passed to all app stacks, including
        stacks created by Portainer. Note that properties defined here will be
        installed directly into Portainer's runtime environment, and thus will
        be implicitly available for expansion in all docker-compose stacks started by Portainer.
        Actual used dict is created from base_stack_env, with this dict overriding."""
      ))
    """Dictionary of environment variables that should be passed to all app stacks, including
    stacks created by Portainer. Note that properties defined here will be
    installed directly into Portainer's runtime environment, and thus will
    be implicitly available for expansion in all docker-compose stacks started by Portainer.
    Actual used dict is created from base_stack_env, with this dict overriding."""

    @validator('base_app_stack_env', pre=True, always=True)
    def base_app_stack_env_validator(cls, v, values, **kwargs):
        sname = 'base_app_stack_env'
        logger.debug(f"{sname}_validator: v={v}, values={values}, kwargs={kwargs}")
        return cls._validate_env_dict(sname, v, values, base_env=values['base_stack_env'], **kwargs)

    portainer_runtime_env: Dict[str, str] = Field(default=None, description=usl(
        """Dictionary of environment variables that will be installed into Portainer's actual runtime
           environment, and thus will be implicitly available for variable expansion in all
           docker-compose stacks started by Portainer, as well as by any processes started
           in the Portainer container.
           Actual used dict is created from base_app_stack_env, with this dict overriding."""
      ))
    """Dictionary of environment variables that will be installed into Portainer's actual runtime
       environment, and thus will be implicitly available for variable expansion in all
       docker-compose stacks started by Portainer, as well as by any processes started
       in the Portainer container.
       Actual used dict is created from base_app_stack_env, with this dict overriding."""

    @validator('portainer_runtime_env', pre=True, always=True)
    def portainer_runtime_env_validator(cls, v, values, **kwargs):
        sname = 'portainer_runtime_env'
        logger.debug(f"{sname}_validator: v={v}, values={values}, kwargs={kwargs}")
        return cls._validate_env_dict(sname, v, values, base_env=values['base_app_stack_env'], **kwargs)

@cache
def hub_settings(**params) -> HubSettings:
    return HubSettings(**params)

def clear_hub_settings_cache() -> None:
    hub_settings.cache_clear()

_current_hub_settings: Optional[HubSettings] = None
_current_hub_settings_lock: Lock = Lock()
def current_hub_settings() -> HubSettings:
    global _current_hub_settings

    with _current_hub_settings_lock:
        if _current_hub_settings is None:
            _current_hub_settings = hub_settings()
        return _current_hub_settings
    
def set_current_hub_settings(settings: HubSettings) -> HubSettings:
    global _current_hub_settings

    with _current_hub_settings_lock:
        _current_hub_settings = settings
        return _current_hub_settings

def init_current_hub_settings(**params) -> HubSettings:
    return set_current_hub_settings(hub_settings(**params))

def clear_current_hub_settings() -> None:
    global _current_hub_settings

    with _current_hub_settings_lock:
        _current_hub_settings = None

    


