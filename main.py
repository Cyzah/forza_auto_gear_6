import os
import sys
import threading
import warnings
from concurrent.futures import ThreadPoolExecutor

from pynput.keyboard import Listener

import constants
import forza
import helper

warnings.filterwarnings("ignore", category=UserWarning)
threadPool = ThreadPoolExecutor(max_workers=8, thread_name_prefix="exec")
forza5 = forza.Forza(threadPool, packet_format=constants.packet_format, enable_clutch=constants.enable_clutch)

_bg_listener_stop = threading.Event()


def _start_bg_listener():
    try:
        helper.create_socket(forza5)
    except Exception:
        return

    def _listen():
        while not _bg_listener_stop.is_set():
            try:
                fdp = helper.nextFdp(forza5.server_socket, forza5.packet_format)
                if fdp is not None and fdp.car_ordinal > 0:
                    forza5._latest_fdp = fdp
                    forza5._fdp_event.set()
            except Exception:
                if not _bg_listener_stop.is_set():
                    pass

    t = threading.Thread(target=_listen, daemon=True)
    t.start()


def press_collect_data():
    if forza5.isRunning:
        forza5.logger.info('stopping gear test')
        threadPool.submit(lambda: setattr(forza5, 'isRunning', False))
    else:
        forza5.logger.info('starting gear test')

        def starting():
            forza5.isRunning = True
            forza5.test_gear()

        threadPool.submit(starting)


def press_analysis():
    if len(forza5.records) <= 0:
        forza5.logger.info(f'load config {constants.example_car_ordinal}.json for analysis as an example')
        helper.load_config(forza5, os.path.join(constants.root_path, 'example', f'{constants.example_car_ordinal}.json'))
    forza5.logger.info('Analysis')
    threadPool.submit(forza5.analyze_data)


def press_auto_shift():
    if forza5.isRunning:
        forza5.logger.info('stopping auto gear')
        threadPool.submit(lambda: setattr(forza5, 'isRunning', False))
    else:
        forza5.logger.info('starting auto gear')

        def starting():
            forza5.isRunning = True
            forza5.run()

        threadPool.submit(starting)


def on_press(key):
    try:
        if key == constants.collect_data:
            press_collect_data()
        elif key == constants.analysis:
            press_analysis()
        elif key == constants.auto_shift:
            press_auto_shift()
        elif key == constants.stop:
            forza5.isRunning = False
            forza5.logger.info('stopped')
        elif key == constants.close:
            forza5.isRunning = False
            _bg_listener_stop.set()
            threadPool.shutdown(wait=False)
            forza5.logger.info('bye~')
            sys.exit(0)
    except Exception as e:
        forza5.logger.exception(e)


if __name__ == "__main__":
    try:
        forza5.logger.info('Forza Auto Gear Shifting Started!!!')
        _start_bg_listener()
        with Listener(on_press=on_press) as listener:
            listener.join()
    finally:
        forza5.isRunning = False
        _bg_listener_stop.set()
        threadPool.shutdown(wait=False)
        forza5.logger.info('Forza Auto Gear Shifting Ended!!!')
