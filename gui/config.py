import time

from dearpygui import dearpygui as dpg

START_TIME = time.time()  # Initialize ASAP
INIT_FILENAME = "midiexplorer.ini"
DEBUG = True  # TODO: allow changing with CLI parameter to the main appS


def save() -> None:
    dpg.save_init_file(INIT_FILENAME)
