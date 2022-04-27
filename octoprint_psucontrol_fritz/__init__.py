# coding=utf-8
from __future__ import absolute_import

__author__ = "not-na <notna+gh@apparat.org>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"
__copyright__ = "Copyright (C) 2021-2022 Shawn Bruce and not-na - Released under terms of the AGPLv3 License"

import octoprint.plugin
import fritzctl

class PSUControl_Fritz(octoprint.plugin.StartupPlugin,
                        octoprint.plugin.RestartNeedingPlugin,
                        octoprint.plugin.TemplatePlugin,
                        octoprint.plugin.SettingsPlugin):

    def __init__(self):
        self.config = dict()

        self.session = None
        self.device = None


    def get_settings_defaults(self):
        return dict(
            address = 'fritz.box',
            username = '',
            password = '',
            ain = '',
        )


    def on_settings_initialized(self):
        self.reload_settings()


    def on_after_startup(self):
        self.reload_settings()

    def reload_settings(self):
        for k, v in self.get_settings_defaults().items():
            if type(v) == str:
                v = self._settings.get([k])
            elif type(v) == int:
                v = self._settings.get_int([k])
            elif type(v) == float:
                v = self._settings.get_float([k])
            elif type(v) == bool:
                v = self._settings.get_boolean([k])

            self.config[k] = v
            self._logger.debug("{}: {}".format(k, v))

        self.connect()

    def connect(self):
        try:
            self.session = fritzctl.Session(
                server=self.config["address"],
                user=self.config["username"],
                pwd=self.config["password"],
                authcheck=False
            )
            api = self.session.getOOAPI("avm_homeauto")
            self.device = api.getDeviceByAIN(self.config["ain"])

        except:
            self._logger.exception("Failed to initialize session. Likely incorrect credentials or permission of user account")


    def on_startup(self, host, port):
        psucontrol_helpers = self._plugin_manager.get_helpers("psucontrol")
        if not psucontrol_helpers or 'register_plugin' not in psucontrol_helpers.keys():
            self._logger.warning("The version of PSUControl that is installed does not support plugin registration.")
            return

        self._logger.debug("Registering plugin with PSUControl")
        psucontrol_helpers['register_plugin'](self)


    def get_sysinfo(self):
        cmd = dict(system=dict(get_sysinfo=dict()))
        result = self.send(cmd)

        try:           
            return result['system']['get_sysinfo']
        except (TypeError, KeyError):
            self._logger.error("Expecting get_sysinfo, got result={}".format(result))
            return dict()

    def check_connected(self):
        if self.session is None or self.device is None:
            return False
        return True

    def turn_psu_on(self):
        if not self.check_connected():
            self._logger.error("Skipping PSU on, since we aren't connected")
            return

        self._logger.debug("Switching PSU On")
        self.device.switch_state = True


    def turn_psu_off(self):
        if not self.check_connected():
            self._logger.error("Skipping PSU off, since we aren't connected")
            return

        self._logger.debug("Switching PSU Off")
        self.device.switch_state = False


    def get_psu_state(self):
        if not self.check_connected():
            self._logger.error("Skipping PSU state check, since we aren't connected")
            return

        self._logger.debug("get_psu_state")

        self.device.reloadData()
        return self.device.switch_state


    def on_settings_save(self, data):
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        self.reload_settings()


    def get_settings_version(self):
        return 1


    def on_settings_migrate(self, target, current=None):
        pass


    def get_template_configs(self):
        return [
            dict(type="settings", custom_bindings=False)
        ]


    def get_update_information(self):
        return dict(
            psucontrol_fritz=dict(
                displayName="PSU Control - Fritz!Box",
                displayVersion=self._plugin_version,

                # version check: github repository
                type="github_release",
                user="not-na",
                repo="OctoPrint-PSUControl-Fritz",
                current=self._plugin_version,

                # update method: pip w/ dependency links
                pip="https://github.com/not-na/OctoPrint-PSUControl-Fritz/archive/{target_version}.zip"
            )
        )

__plugin_name__ = "PSU Control - Fritz!Box"
__plugin_pythoncompat__ = ">=3,<4"

def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = PSUControl_Fritz()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }
