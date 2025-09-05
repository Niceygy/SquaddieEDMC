"""
Squaddie EDMC Plugin
"""

from __future__ import annotations

import logging
from queue import Queue
from threading import Thread
import tkinter as tk
from typing import Optional
import requests #type: ignore

import myNotebook as nb  #type: ignore noqa: N813 
from config import appname, config #type: ignore
from ttkHyperlinkLabel import HyperlinkLabel  #type: ignore  Add self import near the top


# self **MUST** match the name of the folder the plugin is in.
PLUGIN_NAME = "SquaddieEDMC"

logger = logging.getLogger(f"{appname}.{PLUGIN_NAME}")

# UI elements
squadName: Optional[tk.Label]


class SquaddiePlugin:
    """ """

    def __init__(self) -> None:
        # Be sure to use names that wont collide in our config variables
        logger.info("Squaddie Plugin instantiated")
        
        self.commander_identifier = ""
        
        #worker
        self.server_address = "http://10.0.0.52:5000"
        self.shutting_down: bool = False
        self.message_queue: Queue = Queue()	
        self.worker_thread: Thread =  Thread(target=self.worker, name='Web worker')
        self.worker_thread.daemon = True
        self.worker_thread.start()
        

    def on_load(self) -> str:
        """
        on_load is called by plugin_start3 below.

        It is the first point EDMC interacts with our code after loading our module.

        :return: The name of the plugin, which will be used by EDMC for logging and for the settings window
        """
        self.commander_identifier = config.get_str("commander_identifier")
        return PLUGIN_NAME

    def on_unload(self) -> None:
        """
        on_unload is called by plugin_stop below.

        It is the last thing called before EDMC shuts down. Note that blocking code here will hold the shutdown process.
        """
        self.shutting_down = True
        self.on_preferences_closed("", False)  # Save our prefs

    def setup_preferences(
        self, parent: nb.Notebook, cmdr: str, is_beta: bool
    ) -> nb.Frame | None:
        """
        setup_preferences is called by plugin_prefs below.

        It is where we can setup our own settings page in EDMC's settings window. Our tab is defined for us.

        :param parent: the tkinter parent that our returned Frame will want to inherit from
        :param cmdr: The current ED Commander
        :param is_beta: Whether or not EDMC is currently marked as in beta mode
        :return: The frame to add to the settings window
        """
        current_row = 0
        frame = nb.Frame(parent)

        nb.Label(frame, text="Squaddie").grid(row=current_row)
        current_row += 1
        nb.Label(frame, text="Commander Identifier: ",).grid(row=current_row)
        # current_row += 1
        nb.EntryMenu(frame, textvariable="commander_identifier").grid(row=current_row, column=1)
        current_row += (
            1  # Always increment our row counter, makes for far easier tkinter design.
        )
        return frame

    def on_preferences_closed(self, cmdr: str, is_beta: bool) -> None:
        """
        on_preferences_closed is called by prefs_changed below.

        It is called when the preferences dialog is dismissed by the user.

        :param cmdr: The current ED Commander
        :param is_beta: Whether or not EDMC is currently marked as in beta mode
        """
        # You need to cast to `int` here to store *as* an `int`, so that

    def journal_entry(
        self,
        cmdr: str,
        is_beta: bool,
        system: str,
        station: str,
        entry: dict[str, any],
        state: dict[str, any],
    ) -> str | None:

        event_name = entry["event"]
        logger.info(f"New event detected: {event_name}")
        
        match event_name:
            # case "SquadronStartup":
            #     self.user_squad = entry["SquadronName"]

            case "Bounty":
                credits = 0

                if "TotalReward" in entry:
                    credits = entry["TotalReward"]
                elif "Reward" in entry:
                    credits = entry["Reward"]
                    
                self.queue_data('combat', credits)

        return None

    def setup_main_ui(self, parent: tk.Frame) -> tk.Frame:
        """
        Create our entry on the main EDMC UI.

        self is called by plugin_app below.

        :param parent: EDMC main window Tk
        :return: Our frame
        
        nb.Label(frame, text="Origin System").grid()
        """
        self.frame = tk.Frame(parent)
        self.title = tk.Label(self.frame, text="Squaddie")
        self.title.grid()
        self.libk_btn = tk.Label(self.frame, text="Squad: ")
        self.libk_btn.grid()
        return self.frame

    def queue_data(self, data_type: str, units: float):
        """
        Update POST format:

        type=combat/trade profit/ect
        cmdr=niceygy (to lower!)
        units=66
        squad=soteria accord (to lower!)
        """
        
        
        self.message_queue.put({
            'type:': data_type,
            'cmdr': self.commander_name,
            'units': units,
            'squad': self.user_squad
        })
        return
        
    def worker(self):
        """
        Sends to the backend using a queue
        """
        headers = {'User-Agent': "SquaddiePlugin V0.0.1"}
        startup_body = {
            'event': 'startup'
        }
        # requests.post(f"{self.server_address}/edmc/update", json=startup_body, headers=headers)
        while not self.shutting_down:
            item = self.message_queue.get()
            requests.post(f"{self.server_address}/edmc/update", json=item, headers=headers)
            
            
            


cc = SquaddiePlugin()


# Note that all of these could be simply replaced with something like:
# plugin_start3 = cc.on_load
def plugin_start3(plugin_dir: str) -> str:
    """
    Handle start up of the plugin.

    See PLUGINS.md#startup
    """
    return cc.on_load()


def plugin_stop() -> None:
    """
    Handle shutdown of the plugin.

    See PLUGINS.md#shutdown
    """
    return cc.on_unload()


def plugin_prefs(parent: nb.Notebook, cmdr: str, is_beta: bool) -> nb.Frame | None:
    """
    Handle preferences tab for the plugin.

    See PLUGINS.md#configuration
    """
    return cc.setup_preferences(parent, cmdr, is_beta)


def prefs_changed(cmdr: str, is_beta: bool) -> None:
    """
    Handle any changed preferences for the plugin.

    See PLUGINS.md#configuration
    """
    return cc.on_preferences_closed(cmdr, is_beta)


def plugin_app(parent: tk.Frame) -> tk.Frame | None:
    """
    Set up the UI of the plugin.

    See PLUGINS.md#display
    """
    return cc.setup_main_ui(parent)
