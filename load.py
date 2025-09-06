"""
Squaddie EDMC Plugin
"""

from __future__ import annotations

import logging
from queue import Queue
from threading import Thread
import time
import tkinter as tk
from typing import Optional
import requests  # type: ignore

import myNotebook as nb  # type: ignore noqa: N813
from config import appname, config  # type: ignore
from ttkHyperlinkLabel import HyperlinkLabel  # type: ignore  Add self import near the top


# self **MUST** match the name of the folder the plugin is in.
PLUGIN_NAME = "SquaddieEDMC"

logger = logging.getLogger(f"{appname}.{PLUGIN_NAME}")

# UI elements
squadName: Optional[tk.Label]


class SquaddieEDMC:
    """ """

    def __init__(self) -> None:
        # Be sure to use names that wont collide in our config variables
        logger.info("Squaddie Plugin instantiated")

        self.commander_name = ""
        self.squad_name = ""
        self.squad_tag = ""

        # worker
        self.server_address = "http://10.0.0.52:5000"
        self.shutting_down: bool = False
        self.message_queue: Queue = Queue()
        self.worker_thread: Thread = Thread(target=self.worker, name="Web worker")
        self.worker_thread.daemon = True
        self.worker_thread.start()

    def on_load(self) -> str:
        """
        on_load is called by plugin_start3 below.

        It is the first point EDMC interacts with our code after loading our module.

        :return: The name of the plugin, which will be used by EDMC for logging and for the settings window
        """
        _cmdr_name = config.get_str("SQUADDIE_commander_identifier")
        if _cmdr_name is not None:
            self.commander_name = _cmdr_name

        _squad_name = config.get_str("SQUADDIE_squadron")
        if _squad_name is not None:
            self.squad_name = _squad_name

        if self.squad_name == "" or self.squad_name is None:
            self.squad_search_thread = Thread(
                target=self.find_squad, name="Find Squad Thread"
            ).start()
        return PLUGIN_NAME

    def on_unload(self) -> None:
        """
        on_unload is called by plugin_stop below.

        It is the last thing called before EDMC shuts down. Note that blocking code here will hold the shutdown process.
        """
        self.shutting_down = True
        if self.commander_name != "" and self.commander_name is not None:
            config.set("SQUADDIE_commander_identifier", self.commander_name)

        if self.squad_name != "" and self.squad_name is not None:
            config.set("SQUADDIE_squadron", self.squad_name)
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
        nb.Label(
            frame,
            text="Commander name",
        ).grid(row=current_row)
        # current_row += 1
        # nb.EntryMenu(frame, textvariable=self.commander_identifier).grid(row=current_row, column=1)
        # current_row += (
        #     1  # Always increment our row counter, makes for far easier tkinter design.
        # )
        return frame

    def on_preferences_closed(self, cmdr: str, is_beta: bool) -> None:
        """
        on_preferences_closed is called by prefs_changed below.

        It is called when the preferences dialog is dismissed by the user.

        :param cmdr: The current ED Commander
        :param is_beta: Whether or not EDMC is currently marked as in beta mode
        """
        # You need to cast to `int` here to store *as* an `int`, so that

        return

    def journal_entry(
        self,
        cmdr: str,
        is_beta: bool,
        system: str,
        station: str,
        entry: dict[str, any],
        state: dict[str, any],
    ) -> str | None:
        logger.info("journal_entry")
        event_name = entry["event"]
        logger.info(f"New event detected: {event_name}")

        self.commander_name = cmdr
        logger.info(f"Now set to commander {cmdr}")

        match event_name:
            # case "SquadronStartup":
            #     self.user_squad = entry["SquadronName"]

            case "Bounty":
                credits = 0

                if "TotalReward" in entry:
                    credits = entry["TotalReward"]
                elif "Reward" in entry:
                    credits = entry["Reward"]

                self.queue_data("Combat Bonds", credits)

            case "MarketSell":
                if "TotalSale" in entry:
                    self.queue_data("Trade", entry["TotalSale"])

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
        self.libk_btn = tk.Label(self.frame, text=f"Squad: {self.squad_name}")
        self.libk_btn.grid()
        return self.frame

    def queue_data(self, data_type: str, units: float):
        """
        Update POST format:

        type=Combat Bonds / Trade / ect
        commander_identifier=niceygy
        units=66
        """

        if self.commander_name is None or self.commander_name is "":
            return

        self.message_queue.put(
            {
                "type:": data_type,
                "commander_identifier": self.commander_name,
                "units": units,
            }
        )
        return

    def find_squad(self):
        logger.info(f"No squad found for {self.commander_name}, starting lookup")
        if self.commander_name == "" or self.commander_name is None:
            logger.info("No commander found!")
            # Wait up to 5 seconds for commander_name to be set
            for _ in range(100):
                if self.commander_name != "" and self.commander_name is not None:
                    break
                time.sleep(0.1)
            else:
                logger.info("Timeout waiting for commander_name, aborting squad lookup.")
                return

        data = requests.get(
            f"{self.server_address}/edmc/search?cmdr={self.commander_name}"
        ).json()

        self.squad_name = data["squad_name"]
        self.squad_tag = data["squad_tag"]
        
        logger.info(f"Found squad for {self.commander_name}! They're in {self.squad_name} ({self.squad_tag})")

    def worker(self):
        """
        Sends to the backend using a queue
        """
        headers = {"User-Agent": "SquaddiePlugin V0.0.1"}
        while not self.shutting_down:
            item = self.message_queue.get()
            if self.commander_name != "" or self.squad_name != "":
                requests.post(
                    f"{self.server_address}/edmc/update", json=item, headers=headers
                )


cc = SquaddieEDMC()


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
