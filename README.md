tp-hub: Bootstrap files and tools for a flexible single-box container-based web-services hub, built on Cloudflare, docker-compose, Traefik and Portainer
===================================================

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Latest release](https://img.shields.io/github/v/release/sammck/tp-hub.svg?style=flat-square&color=b44e88)](https://github.com/sammck/tp-hub/releases)

`tp-hub` is a project directory and collection of tools intended to make it easy to bootstrap a small container-based web-services hub
on an Ubuntu/Debian host machine. It is suitable for installation on Raspberry Pi or any dedicated 64-bit host that has ports 80, 443, and 7082 available for use.
The hub can manage multiple services sharing a single port and can expose individual services to the local intranet or to the public Internet. HTTPS termination is provided, including automatic provisioning of SSL certificates.

[Cloudflare](https://cloudflare.com/) is used to provision SSL certificates, terminate SSL/HTTP connections, manage public DNS, provide a public HTTP/HTTPS ingress, and securely tunnel inbound HTTP/HTTPS requests through NAT/firewalls to the hub. It can also provide a secure SSH tunnel into the hub.

[Traefik](https://doc.traefik.io/traefik/) is used as a reverse-proxy, and [Portainer](https://docs.portainer.io/) is used to manage service [docker-compose](https://docs.docker.com/compose/) stacks.

Table of contents
-----------------

* [Introduction](#introduction)
* [Installation](#installation)
* [Known issues and limitations](#known-issues-and-limitations)
* [Getting help](#getting-help)
* [Contributing](#contributing)
* [License](#license)
* [Authors and history](#authors-and-history)

Introduction
------------

`tp-hub` is a project directory and collection of tools intended to make it easy to bootstrap a small container-based web-services hub
on an Ubuntu/Debian host machine. It is suitable for installation on Raspberry Pi or any dedicated 64-bit host that has ports 80, 443, and 7082, available for use.

[Traefik](https://doc.traefik.io/traefik/) is used as a reverse-proxy, and [Portainer](https://docs.portainer.io/) is used to manage service [docker-compose](https://docs.docker.com/compose/) service stacks.

[Cloudflare](https://cloudflare.com/) is used to provision SSL certificates, terminate SSL/HTTP connections, manage public DNS, provide a public HTTP/HTTPS ingress, and securely tunnel inbound public requests through NAT/firewalls to the Traefik reverse proxy on the hub. It can also provide a secure way to SSH into your hub from the Internet. All of the Cloudflare features used by tp-hub are included in Cloudflare's free-tier offering.

All services other than `docker` and the `cloudflared` agent daemon, including Traefik and Portainer themselves, run in docker containers and are managed with [docker-compose](https://docs.docker.com/compose/).
 Individual service stacks can be easily configured to be visible to the LAN only, or to the public Internet.

A new web service can be added simply by authoring a docker-compose.yml file and using Portainer's web UI to add a managed stack. All reverse-proxy configuration settings for each service (including hostname/path routing, public/private entrypoints, etc.) are expressed with labels attached
to the service container and defined in its docker-compose.yml file, so there is never any need to edit reverse-proxy configuration as services are added, removed, and edited.

There are two primary docker-compose stacks that are directly configured and launched in the bootstrap process.:

  - [Traefik](https://doc.traefik.io/traefik/) is used as a reverse-proxy and firewall for all services.
  It has the wonderful quality of automatically provisioning/deprovisioning reverse-proxy policy for
  services in docker containers when they are launched, modified, or stopped--based solely on configuration
  info attached to the container's docker labels. Once traefik is launched it generally never needs to be explicitly
  managed again. Traefik can also automatically provisions private keys and SSL certificates (using lets-encrypt) for services as they
  are needed, and terminates HTTPS entrypoints so your service containers only need to implement HTTP (tp-hub does
  not use this capability, as Cloudflare is used to terminate SSL connections).).
  Traefik provides a web-based dashboard to view status and information related to the reverse-proxy.
  Traefik reverse-proxy has wide adoption, is open-source and free to use. 

  - [Portainer](https://docs.portainer.io/) is a nifty and very full-featured docker-compose service stack manager with a
  rich web UI to manage docker-compose stacks. With Portainer, you can add/remove/restart/reconfigure stacks, view logs, browse volumes,
  inspect resource usage, etc. Portainer includes a multiuser username/password database and full-featured access control
  if you need to allow multiple people to manage containers. Portainer Community Edition is open-source and free to use.
  The Portainer stack creates two containers--one for the main Portainer Web UI (Portainer itself), and another for the
  Portainer Agent--a backend service that allows Portainer to control Docker on the host machine. The two components
  are separated so that in complex environments, a single Portainer instance can manage Docker stacks on multiple host
  machines; for our purposes only one Portainer Agent is used and it is on the same host as Portainer itself

All of the containers in the two primary stacks are launched with `restart: always` so they will automatically be
restarted after host reboot or restart of the Docker daemon.

### Prerequisites

  - **Ubuntu/Debian**: The bootstrapping code provided here must be running an Ubuntu/Debian variant. The hub has only been tested
    on Ubuntu 22.04. However, if you skip auto-provisioning and manually install docker and docker-compose, the hub may well work
    on any Linux variant.
  - **Python 3.8+** is required by the bootstrapping scripts.

Installation
=====

## Create an account on Cloudflare
If you haven't already, head over to https://dash.cloudflare.com/sign-up?lang=en-US and create an account. The free tier
has all of the features needed by this project.

## Copy the Cloudflare Global API Key
Go to https://dash.cloudflare.com/profile/api-tokens, and click on "View" next to "Global API Key". You will be prompted for
your Cloudflare password.  Make a note of the displayed key value; you will use it later to configure Cloudflare for use with the hub.

## Register a public DNS Zone that you can administer
To serve requests to the Internet on well-known, easy-to-remember names, and to enable certificate generation for SSL/HTTPS, you must be able to create your own public DNS records that resolve to your hub's public service HTTP/HTTPS IP address. Administration and serving of this DNS zone will be delegated to Cloudflare (see below). But before you can do that you need to register a public DNS domain, or already have administrative access to a dedicated public domain. We will call it `${PARENT_DNS_DOMAIN}` (e.g., `smith-vacation-home.com`). You can use Cloudflare, AWS Route53, Squarespace, GoDaddy or whatever registrar you like.

Later, you will be asked to update the nameserver (NS) records for this domain to point at Cloudflare's nameservers (this is automatically done for you if you registered the domain through CloudFlare).

## Copy this project directory tree onto the hub host machine
A copy of this directory tree must be placed on the host machine. You can do this in several ways; for example:

 - If git is installed, you can directly clone it from GitHub:
   ```bash
   sudo apt-get install git   # if necessary to install git first
   cd ~
   git clone --branch stable https://github.com/sammck/tp-hub.git
   cd tp-hub
   ```

- If you have SSH access to the host, you can copy the directory tree from another machine using rsync:
  ```bash
  # On other machine
  rsync -a tp-hub/ <my-username>@<my-hub-host>:~/tp-hub/
  ssh <my-username>@<my-hub-host>
  # On the hub
  cd tp-hub
  ```

## Run bin/hub-env to install the project's Python virtualenv and launch a bash shell in the project enviromnent:

There is a script `<project-dir>/bin/hub-env` which will activate the project environment including the Python
virtualenv that it uses. It can be invoked in one of 3 ways:

  - If sourced from another script or on the command line (bash '.' or 'source' command), it will directly modify
  environment variables, etc in the running process to activate the environment. This is similar to the way
  `. .venv/bin/activate` is typically used with Python virtualenv's.
  - If invoked as a command with arguments, the arguments are treated as a command to run within the environment.
  The command will be executed, and when it exits, control will be returned to the original caller, without
  modifying the original caller's environment.
  - If invoked as a command with no arguments, launches an interactive bash shell within the environment. When the
  shell exits, control is returned to the original caller, without modifying the original caller's environment.

Regardless of which way hub-env is invoked, if the virtualenv does not exist, hub-env will create it and initialize it with required
packages.  If necessary, hub-env will install system prerequisites needed to create the virtualenv, which might require
sudo. This is only done the first time hub-env is invoked.

In addition, hub-env tweaks the Python virtualenv's .venv/bin/activate to activate the entire tp-hub project rather than just the virtualenv.
This is a convenience primarily so that tools (like vscode) that understand how to activate a Python virtualenv will work properly
with the tp-hub project.

To initialize and activate the environment for the first time:

```bash
$ cd ~/tp-hub
$ bin/hub-env
...
# The first time you run bin/hub-env, there will be a lot of output as prerequisites are
# installed, the virtualenv is created, and required Python packages are installed. If
# necessary for prerequisite installation, you may be asked to enter your sudo password.
# If you don't wish to do this, you can CTRL-C out, install the prerequisite manually,
# and then restart this step.
# After the first time you run bin/hub-env, there will be no such spew or prompts.
...
Launching hub-env bash shell...
(hub-env) $
# You are now running a bash shell in the project environment, with all commands in the search PATH, etc.
```
> **Note**
> All of the instructions that follow assume you are running in a hub-env activated bash shell.


## Install prerequisite system packages

The `cloudflared` package, Docker and docker-compose must be installed, and the bootstrapping user must be in the `docker`
security group. A script is provided to automatically do this:

```bash
# if not running in hub-env shell, launch with '~/tp-hub/bin/hub-env'
install-prereqs
```

This command is safe to run multiple times; it will only install what is missing.
If required, you will be prompted for your `sudo` password. If you don't wish to do this;
you can CRTL-C out, install the prerequisite manually, then restart this step.

> **Note**
> If you were not already in the `docker` security group when you started the current login session, you will
> be added, but the change will not take effect until you log out and log back in again. Until you do that,
> sudo will be required to run docker (you may be prompted for sudo password for each subsequent step that
> invokes docker).

## Configure Cloudflared for use with the hub
Before public HTTP(s) requests can be served, Cloudflared must be configured to be the DNS server for your
public DNS zone, and a Cloudflare tunnel must be established to proxy requests through the NAT/firewall into
the hub host machine. A script is provided to do most of the work and guide you through the parts you have to
help with:

```bash
# if not running in hub-env shell, launch with '~/tp-hub/bin/hub-env'
init-cloudflare
```
This command is safe to run multiple times; it will only install/configure what is missing.
If required, you will be prompted for your `sudo` password. If you don't wish to do this;
you can CRTL-C out, initialize the required parts manually, then restart this step.

Major steps performed by this script:
  - Logging in to Cloudflared using the Global API Key
  - Creation of a Cloudflared DNS Zone for your "${PARENT_DNS_DOMAIN}"
  - Guiding you to update DNS NS records to point at Cloudflare's DNS servers, and verifying that this was done correctly
  - Creating of A Cloudflare tunnel on the hub host
  - Creation of a wildcard DNS entry in the DNS zone that routes all subdomain requests to the newly created tunnel
  - Creation of a root DNS entry that routes requests to the bare DNS Zone name to the newly created tunnel
  - Installation of the `cloudflared` tunnel daemon as a systemd service on the hub host
  - Optionally, configuration of the `cloudflared` tunnel daemon to provide a secure SSH proxy through `https://ssh.${PARENT_DNS_DOMAIN}`
  - Configuration of the `cloudflared` tunnel daemon to serve a test page on `https://tunnel-test.${PARENT_DNS_DOMAIN}`
  - Optionally, configuration of the `cloudflared` tunnel daemon to serve the Traefik dashboard publicly on `https://traefik.${PARENT_DNS_DOMAIN}` via Traefik at `http://localhost: 8080`
  - Optionally, configuration of the `cloudflared` tunnel daemon to serve the Portainer UI publicly on `https://portainer.${PARENT_DNS_DOMAIN}` via Traefik at `http://localhost:9000`
  - Configuration of the `cloudflared` tunnel daemon to route all other HTTP(S) requests to Traefik at `http://localhost:7082`
  - Roubd-trip verification that the tunnel test page is being served.

## Create an initial tp-hub config.yml file with minimal required configuration settings

A script `init-config` is provided that will create a boilerplate config.yml if needed,
and prompt you to provide values for required config settings. These include:

  - An admin password to use for access to the Traefik dashboard web UI
  - An initial admin password to use for access to the Portainer web UI. Only used until the first time you set a new password.
  - The value of `${PARENT_DNS_DOMAIN}` that you set up as described above.

It is safe to run `init-config` multiple times; it will only prompt you for values that have not yet been
initialized.

```bash
# if not running in hub-env shell, launch with '~/tp-hub/bin/hub-env'
init-config
# Answer the questions as prompted
```

## Verify that the initial configuration is valid

Just to make sure the initial configuration is readable and all values are sane, run this command to display
the resolved configuration:

```bash
# if not running in hub-env shell, launch with './bin/hub-env'
hub config
# ...json configuration is displayed
```

## Build the traefik and portainer docker-compose configuration files and related dynamic content

The environment variables and other customizable configuration elements used by docker-compose
to launch the Traefik and Portainer docker-compose stacks are derived from the tp-hub configuration
you set up in previous steps. To prepare these derived files for use by docker-compose, run the following command:

```bash
# if not running in hub-env shell, launch with '~/tp-hub/bin/hub-env'
hub build
```
> **Note**
> If you ever change the settings in `config.yml`, either directly or through `hub config set`, you
> should rebuild the stack configurations with `hub build`.

## Launch Traefik reverse-proxy

Next, start the Traefik reverse-proxy. To perform this step, the user must be in the `docker` security group.

> **Note**
> If you were not already in the `docker` security group when you started the current login session, you were
> added by `install-prereqs.sh`, but the change will not take effect until you log out and log back in again.
> Until you do that, you will be prompted for your sudo password when invoking commands that require docker.

```bash
# if not running in hub-env shell, launch with '~/tp-hub/bin/hub-env'
hub traefik up
```

Traefik will immediately begin serving requests on ports 80 and 443 on both the local hub-host and on the public
Internet. It will also obtain a lets-encrypt SSL certificate for `traefik.${PARENT_DNS_DOMAIN}`.
However, no proxied services are yet exposed to the Internet, so requests to the public addresses will
always receive `404 page not found` regardless of host name.

## Verify basic Traefik functionality

Make a cursory check to see that everything thinks it is running by examining the logs

```bash
# if not running in hub-env shell, launch with '~/tp-hub/bin/hub-env'
hub traefik logs | grep error
```

Verify that the Traefik Dashboard is functioning by opening a web browser on the hub-host or any other
host in the LAN and navigating to `http://${HUB_LAN_IP}:8080`, where `${HUB_LAN_IP}` is the stable LAN
IP address of your hub-host, as described above.

You will be prompted for login credentials.  The username is "admin" and the password is the one you entered
for the Traefik dashboard in the above steps.

Verify that Traefik is serving LAN-local HTTP requests (from any host in the LAN):
```bash
curl http://${HUB_LAN_IP}
# you will receive "Found" due to a 302 redirect to the configured default shared app (/whoami/), which is expected
```

Verify that the tunnel is forwarding requests to Traefik:
```bash
curl https://hub.${PARENT_DNS_DOMAIN}
# you will receive "Found" due to a 302 redirect to the configured default shared app (/whoami/), which is expected
```

Verify that the Traefik dashboard is functional by opening a web browser on any machine inside your LAN and navigating to
http://${HUB_LAN_IP}:8080. The username is "admin" and the password is as you configured for the Traefik dashboard.


## Launch Portainer

Next, start the Portainer stack. To perform this step, the user must be in the `docker` security group.

> **Note**
> If you were not already in the `docker` security group when you started the current login session, you were
> added by `install-prereqs.sh`, but the change will not take effect until you log out and log back in again.
> Until you do that, you will be prompted for your sudo password when invoking commands that require docker.

```bash
# if not running in hub-env shell, launch with '~/tp-hub/bin/hub-env'
hub portainer up
```

Portainer will immediately be recognized by Traefik and Traefik will begin reverse-proxying requests to it.

## Verify basic Portainer functionality

Make a cursory check to see that everything thinks it is running by examining the logs

```bash
# if not running in hub-env shell, launch with '~/tp-hub/bin/hub-env'
hub portainer logs | grep ERR
```

Verify that the Portainer Web UI is functioning by opening a web browser on the hub-host or any other
host in the LAN and navigating to `http://${HUB_LAN_IP}:9000`, where `${HUB_LAN_IP}` is the stable LAN
IP address of your hub-host, as described above.

You will be prompted for login credentials.  The username is "admin" and the password is the one you entered
for the Portainer Web UI in the above steps.

## Done!
Congratulations, your `tp-hub` is up and running! Both the Traefik and Portainer stack containers were launched with `restart=always`, so they
will automatically restart when Docker is restarted or your hub host reboots. From here on, you can manage all of your web service stacks through
the Portainer UI, which you can browse to (from any client inside the LAN) at `http://${HUB_LAN_IP}:9000`. If your client can discover
the hub host via Bonjour or mDNS, then you can use `http://${HUB_HOSTNAME}:9000`  or `http://${HUB_HOSTNAME}.local:9000`.

Proceed to the next section to deploy your first example web service.

Adding an example "whoami" web service
=====

In this section, you will deploy a simple web service `whoami`. It simply accepts HTTP get requests and responds to them with plain text
describing all of the received HTTP headers, the URL path, Traefik route, etc. It will be configured to serve multiple entry points:

  - `http://whoami.${PARENT_DNS_DOMAIN}`            (both on private LAN and public Internet)
  - `https://whoami.${PARENT_DNS_DOMAIN}`           (both on private LAN and public Internet)
  - `http://hub.${PARENT_DNS_DOMAIN}/whoami`        (both on private LAN and public internet)
  - `https://hub.${PARENT_DNS_DOMAIN}/whoami`       (both on private LAN and public internet)
  - `http://${PARENT_DNS_DOMAIN}/whoami`            (both on private LAN and public internet)
  - `https://${PARENT_DNS_DOMAIN}/whoami`           (both on private LAN and public internet)
  - `http://lanhub.${PARENT_DNS_DOMAIN}/whoami`     (Private LAN only, requires DNS override--see above)
  - `http://${HUB_LAN_IP}/whoami`                   (Private LAN only)
  - `http://${HUB_HOSTNAME}/whoami`                 (Private LAN only)
  - `http://${HUB_HOSTNAME}.local/whoami`           (Private LAN only) (for Mac clients)
  - `http://localhost/whoami`                       (Hub host only only) (for clients on hub host itself)
  - `http://127.0.0.1/whoami`                       (Hub host only only) (for clients on hub host itself)

This list may vary depending on config settings.

## Grab the docker-compose.yml for the example service
The only file necessary to install this stack is the docker-compose.yml file in this project at `~/tp-hub/examples/whoami/docker-compose.yml`.

The easiest way to install it into Portainer is to copy it into the clipboard of the browser client on the private LAN that you will be using to
access Portainer.  Do that in whatever way is easiest for you. E.g., you can browse to https://github.com/sammck/tp-hub/blob/main/examples/whoami/docker-compose.yml and copy it into the clipboard from there.

> **Note:**
> For more sophisticated stacks Portainer is also able to clone a named github repo and run a docker-compose stack in it.

## Log into Portainer

On a web browser in the private LAN, navigate to `http://${HUB_LAN_IP}:9000`, `http://${HUB_HOSTNAME}:9000`,  or `http://${HUB_HOSTNAME}.local:9000`
as described above.

If prompted, log into Portainer with username 'admin' and the Portainer password you configured during setup. It is recommended
that you immediately change the temporary password assigned via `init-config`.`

## Navigate to the Portainer "stacks" page

From the Portainer Home page, click on the big box labeled "${HUB_HOSTNAME} portainer agent". This will move you into the Environment page
for the hub host (Portainer is capable of managing multiple Docker host machines, but tp-hub is set up to only manage a single Environment
on the same host that Portainer runs on).

Click on the box that says "Stacks". This will take to to the Page that lists all of the docker-compose stacks that exist on
your hub.  Two of the stacks--"traefik" and "portainer", were the stacks that we created directly outside of Portainer; they run Traefik
and Portainer themselves. Because they were created outside of Portainer, they are marked as Limited Control. You should not need to
mess with them ever from within Portainer.

Any stacks listed with Total Control are those you created with Portainer. If this is your first time using Portainer, there should not
be any such stacks listed.

## Create a new stack
Click on the button labelled "+ Add Stack".  This will take you to the "Create stack" page.

Give your stack the name "whoami". This is the name you will see in the listed stacks page, and it also becomes the project
name for docker-compose; it is used as a prefix for created docker container names, etc.

We are going to directly paste in docker-compose.yml content, so click on "Web editor".

Click inside the Web editor textbox and paste the content of the whoami example docker-compose.yml file.

Note: below the textbox, you may wish to click on "+ Add an Environment Variable" to define docker-compose environment variables that
will be expanded when the docker-compose.yml file is interpreted. However, for this example, most of the appropriate
variables have been injected into the Portainer runtime environment by tp-hub, so this stack will run perfectly without defining
any additional values.

Finally, click on "Deploy the stack". Within a few seconds it will be up and running and actively serving requests. You
will be taken to the "Stack details" page, where you can inspect the containers within the stack, view logs, resource usage
graphs, and even open a Web-UI terminal into any container.

## Use your new web service

In a browser on any host with Internet access, navigate to one of:

  - `http://whoami.${PARENT_DNS_DOMAIN}`            (public Internet)
  - `https://whoami.${PARENT_DNS_DOMAIN}`           (public Internet)
  - `http://hub.${PARENT_DNS_DOMAIN}/whoami`        (public internet)
  - `https://hub.${PARENT_DNS_DOMAIN}/whoami`       (public internet)
  - `http://${PARENT_DNS_DOMAIN}/whoami`            (public internet)
  - `https://${PARENT_DNS_DOMAIN}/whoami`           (public internet)

In a browser on any host inside the private LAN, navigate to:

  - `http://lanhub.${PARENT_DNS_DOMAIN}/whoami`     (Private LAN only, requires DNS override--see above)
  - `https://lanhub.${PARENT_DNS_DOMAIN}/whoami`    (Private LAN only, requires DNS override--see above)
  - `http://${HUB_LAN_IP}/whoami`                   (Private LAN only)
  - `http://${HUB_HOSTNAME}/whoami`                 (Private LAN only)
  - `http://${HUB_HOSTNAME}.local/whoami`           (Private LAN only) (for Mac clients)

Congratulations! You've just deployed a tp-hub web service stack and used it from the Internet and your private LAN, with valid HTTPS certificates.

Since the docker-compose service in your `whoami` stack was defined with `restart: always`, it will automatically restart when Docker is restarted
or the hub host is rebooted.

If you wish to remove the stack, you can click on the "Delete this stack" button in the "Stack details" page. Traefik will
automatically detect the removal of containers and remove the reverse-proxy routes associated with them.


Known issues and limitations
----------------------------

* TBD

Getting help
------------

Please report any problems/issues [here](https://github.com/sammck/tp-hub/issues).

Contributing
------------

Pull requests welcome.

License
-------

`tp-hub` is distributed under the terms of the [MIT License](https://opensource.org/licenses/MIT).  The license applies to this file and other files in the [GitHub repository](http://github.com/sammck/tp-hub) hosting this file.

Authors and history
-------------------

The author of `tp-hub` is [Sam McKelvie](https://github.com/sammck).
