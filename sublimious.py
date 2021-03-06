import sys
import os
path = os.path.dirname(os.path.realpath(__file__))
is_zip = False

if "sublime-package" in path:
    is_zip = True

sys.path.append(path)

import sublime
import json

from .lib.collector import Collector
from .lib.io import write_sublimious_file
from .lib.packagecontroller import PackageController


def plugin_loaded():
    current_path = os.path.dirname(os.path.realpath(__file__))

    sublime_dir = os.path.dirname(sublime.packages_path())
    packages_dir = os.path.join(sublime_dir, 'Packages')
    sublimious_packages_dir = os.path.join(packages_dir, 'sublimious/')
    user_dir = os.path.join(packages_dir, 'User')

    status_panel = sublime.active_window().create_output_panel("sublimious_status_panel")
    sublime.active_window().run_command("show_panel", {"panel": "output.sublimious_status_panel", "toggle": False})

    pcontrol_settings = os.path.join(user_dir, 'Package Control.sublime-settings')
    settings_file = os.path.join(user_dir, 'Preferences.sublime-settings')

    collector = Collector(current_path)

    if not collector.get_user_config().nuke_everything:
        status_panel.run_command("status", {"text": "Sublimious is currently off."})
        status_panel.run_command("status", {"text": "Since this might be your first start, I created a ~/.sublimious file"})
        status_panel.run_command("status", {"text": "Open that file and change 'nuke_everything' to True to proceed\n"})
        sys.exit()

    status_panel.run_command("status", {"text": "Welcome to Sublimious."})

    # Nuke everything
    if not os.path.isdir(sublimious_packages_dir):
        os.mkdir(sublimious_packages_dir)

    settings_user = [os.path.join(user_dir, f) for f in os.listdir(user_dir) if f.endswith(".sublime-settings")]
    settings_current = [os.path.join(sublimious_packages_dir, f) for f in os.listdir(sublimious_packages_dir) if f.endswith(".sublime-settings")]
    filelist = settings_current + settings_user

    for f in filelist:
        os.remove(f)

    # Second iteration to initialise all layers with config
    collected_config = collector.get_collected_config()
    for layer in collector.get_layers():
        layer.init(collected_config)
        status_panel.run_command("status", {"text": "'%s' layer loaded..." % layer.name})

    # Collect all packages
    status_panel.run_command("status", {"text": "Collecting all packages..."})
    all_packages = collector.collect_key("required_packages") + collector.get_user_config().additional_packages
    write_sublimious_file(pcontrol_settings, json.dumps({'installed_packages': all_packages}))

    # Get all keybinding definitions and save to keymapfile
    status_panel.run_command("status", {"text": "Building keymap..."})
    write_sublimious_file("%s/Default.sublime-keymap" % user_dir, json.dumps(collector.collect_key("sublime_keymap")))

    # Generate a bunch of syntax files depending on layer config
    syntax_definitions = collector.collect_syntax_specific_settings()
    for syntax, value in syntax_definitions.items():
        write_sublimious_file("%s/%s.sublime-settings" % (sublimious_packages_dir, syntax), json.dumps(value))
        status_panel.run_command("status", {"text": "Collected %s syntax definition..." % syntax})

    # Generate package specific settings
    for package, setting in collector.get_collected_config()["package_settings"].items():
        write_sublimious_file("%s/%s.sublime-settings" % (user_dir, package), json.dumps(setting))

    # Take control over sublime settings file
    status_panel.run_command("status", {"text": "Taking control over Preferences.sublime-settings..."})
    write_sublimious_file(settings_file, json.dumps(collected_config))

    status_panel.run_command("status", {"text": "Pinging package control"})
    controller = PackageController()
    controller.reload()

    status_panel.run_command("status", {"text": "ALL DONE!"})
