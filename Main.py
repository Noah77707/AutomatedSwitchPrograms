import os
from queue import Queue
from threading import Event, Thread

from Modules.Controller import Controller
from Modules.GUI import App, GUI
from Modules.Control_System import start_control_video, controller_control, check_threads
from Modules.Image_Processing import Image_Processing

MODULE_NAME = 'SwitchConnector'
if __name__ == "__main__":
    def main_menu():
        # This passes the port of the capture card to the capture module. This is hardcoded as port 2 right now, but will be set by the user in the future.

        Image_queue = Queue()
        Command_queue = Queue()
        Switch_Controller = Controller('COM15', 115200)
        shutdown_event = Event()
        stop_event = Event()
        image = Image_Processing()

        threads = []
        threads.append({
            'function': 'control_system',
            'thread': Thread(target=lambda:
                             start_control_video(2, Switch_Controller, Image_queue, shutdown_event, stop_event),
                             daemon= True
                            )
        })

        threads.append({
            'function': 'controller_control',
            'thread': Thread(target=lambda: controller_control(Switch_Controller, Image_queue, Command_queue, shutdown_event, stop_event, image),
                              daemon= True)
        })

        threads.append({
            'function': 'check_threads',
            'thread': Thread(target=lambda: check_threads(threads, shutdown_event),
                             daemon= True
                             )
        })

        for thread in threads:
            thread['thread'].start()

        GUI_App = App()
        GUI(Image_queue, Command_queue, shutdown_event, stop_event, image)
        GUI_App.exec()

        shutdown_event.set()
    main_menu()
        