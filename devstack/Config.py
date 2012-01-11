# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

import os
import re
import ConfigParser

import Shell
import Logger
import Exceptions
from Exceptions import (BadParamException)

LOG = Logger.getLogger("install.config")
PW_TMPL = "Enter a password for %s: "
ENV_PAT = re.compile(r"^\s*\$\{([\w\d]+):\-(.*)\}\s*$")


class EnvConfigParser(ConfigParser.RawConfigParser):
    def __init__(self):
        ConfigParser.RawConfigParser.__init__(self)
        self.pws = dict()

    def _makekey(self, section, option):
        key = option + "@" + section
        return key

    def get(self, section, option):
        key = self._makekey(section, option)
        LOG.debug("Fetching value for param %s" % (key))
        v = self._get_special(section, option)
        LOG.debug("Fetched \"%s\" for %s" % (v, key))
        return v

    def _get_special(self, section, option):
        key = self._makekey(section, option)
        v = ConfigParser.RawConfigParser.get(self, section, option)
        if(v == None):
            return v
        mtch = ENV_PAT.match(v)
        if(mtch):
            env = mtch.group(1).strip()
            defv = mtch.group(2)
            if(len(defv) == 0 and len(env) == 0):
                msg = "Invalid bash-like value %s for %s" % (v, key)
                raise BadParamException(msg)
            if(len(env) == 0):
                return defv
            LOG.debug("Looking up environment variable %s" % (env))
            v = os.getenv(env)
            if(v == None):
                LOG.debug("Could not find anything in environment variable %s (using default value)" % (env))
                v = defv
            return v
        else:
            return v

    def getpw(self, section, option):
        key = self._makekey(section, option)
        pw = self.pws.get(key)
        if(pw != None):
            return pw
        pw = self.get(section, option)
        if(pw == None):
            pw = ""
        if(len(pw) == 0):
            while(len(pw) == 0):
                pw = Shell.password(PW_TMPL % (key))
        LOG.debug("Password for %s will be %s" % (key, pw))
        self.pws[key] = pw
        return pw