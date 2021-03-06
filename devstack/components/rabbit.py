# vim: tabstop=4 shiftwidth=4 softtabstop=4

#    Copyright (C) 2012 Yahoo! Inc. All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from tempfile import TemporaryFile
import time

from devstack import component as comp
from devstack import log as logging
from devstack import settings
from devstack import shell as sh
from devstack import trace as tr

#id
TYPE = settings.RABBIT
LOG = logging.getLogger("devstack.components.rabbit")

#hopefully these are distro independent..
START_CMD = ['service', "rabbitmq-server", "start"]
STOP_CMD = ['service', "rabbitmq-server", "stop"]
STATUS_CMD = ['service', "rabbitmq-server", "status"]
RESTART_CMD = ['service', "rabbitmq-server", "restart"]
PWD_CMD = ['rabbitmqctl', 'change_password', 'guest']

#the pkg json files rabbit mq server requires for installation
REQ_PKGS = ['rabbitmq.json']

#default password
RESET_BASE_PW = ''

#how long we wait for rabbitmq to start up before doing commands on it
WAIT_ON_TIME = 5


class RabbitUninstaller(comp.PkgUninstallComponent):
    def __init__(self, *args, **kargs):
        comp.PkgUninstallComponent.__init__(self, TYPE, *args, **kargs)
        self.runtime = RabbitRuntime(*args, **kargs)

    def pre_uninstall(self):
        try:
            self.runtime.restart()
            LOG.info("Attempting to reset the rabbit-mq guest password to \"%s\"", RESET_BASE_PW)
            cmd = PWD_CMD + [RESET_BASE_PW]
            sh.execute(*cmd, run_as_root=True)
        except IOError:
            LOG.warn(("Could not reset the rabbit-mq password. You might have to manually "
                      "reset the password to \"%s\" before the next install") % (RESET_BASE_PW))


class RabbitInstaller(comp.PkgInstallComponent):
    def __init__(self, *args, **kargs):
        comp.PkgInstallComponent.__init__(self, TYPE, *args, **kargs)
        self.runtime = RabbitRuntime(*args, **kargs)

    def warm_configs(self):
        pws = ['rabbit']
        for pw_key in pws:
            self.cfg.get("passwords", pw_key)

    def _setup_pw(self):
        LOG.info("Setting up your rabbit-mq guest password.")
        self.runtime.restart()
        passwd = self.cfg.get("passwords", "rabbit")
        cmd = PWD_CMD + [passwd]
        sh.execute(*cmd, run_as_root=True)
        LOG.info("Restarting so that your rabbit-mq guest password is reflected.")
        self.runtime.restart()

    def post_install(self):
        comp.PkgInstallComponent.post_install(self)
        self._setup_pw()

    def _get_pkgs(self):
        return list(REQ_PKGS)


class RabbitRuntime(comp.EmptyRuntime):
    def __init__(self, *args, **kargs):
        comp.EmptyRuntime.__init__(self, TYPE, *args, **kargs)
        self.tracereader = tr.TraceReader(self.tracedir, tr.IN_TRACE)

    def start(self):
        if self.status() == comp.STATUS_STOPPED:
            self._run_cmd(START_CMD)
            return 1
        else:
            return 0

    def status(self):
        #this has got to be the worst status output
        #i have ever seen (its like a weird mix json+crap)
        (sysout, _) = sh.execute(*STATUS_CMD,
                        run_as_root=True,
                        check_exit_code=False)
        if sysout.find('nodedown') != -1 or sysout.find("unable to connect to node") != -1:
            return comp.STATUS_STOPPED
        elif sysout.find('running_applications') != -1:
            return comp.STATUS_STARTED
        else:
            return comp.STATUS_UNKNOWN

    def _run_cmd(self, cmd):
        #this seems to fix one of the bugs with rabbit mq starting and stopping
        #not cool, possibly connected to the following bugs:
        #https://bugs.launchpad.net/ubuntu/+source/rabbitmq-server/+bug/878597
        #https://bugs.launchpad.net/ubuntu/+source/rabbitmq-server/+bug/878600
        #
        #rhel seems to have this bug also...
        with TemporaryFile() as f:
            sh.execute(*cmd, run_as_root=True,
                        stdout_fh=f, stderr_fh=f)

    def restart(self):
        LOG.info("Restarting rabbit-mq.")
        self._run_cmd(RESTART_CMD)
        LOG.info("Please wait %s seconds while it starts up." % (WAIT_ON_TIME))
        time.sleep(WAIT_ON_TIME)
        return 1

    def stop(self):
        if self.status() == comp.STATUS_STARTED:
            self._run_cmd(STOP_CMD)
            return 1
        else:
            return 0


def describe(opts=None):
    description = """
 Module: {module_name}
  Description:
   {description}
  Component options:
   {component_opts}
"""
    params = dict()
    params['component_opts'] = "TBD"
    params['module_name'] = __name__
    params['description'] = __doc__ or "Handles actions for the rabbit-mq component."
    out = description.format(**params)
    return out.strip("\n")
