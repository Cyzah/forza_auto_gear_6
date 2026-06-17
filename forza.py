import os
import sys
import time
import threading
import logging
from concurrent.futures.thread import ThreadPoolExecutor
from os import listdir
from os.path import isfile, join

import matplotlib.pyplot as plt

sys.path.append(r'./forza_motorsport')
from fdp import ForzaDataPacket

import constants
import gear_helper
import helper
import keyboard_helper
import plotter
from car_info import CarInfo
from constants import ConfigVersion
from logger import Logger

debug_properties = [
    'gear', 'current_engine_rpm', 'speed', 'tire_slip_ratio_RL', 'tire_slip_ratio_RR', 'tire_slip_ratio_FL', 'tire_slip_ratio_FR', 'tire_slip_angle_RL', 'tire_slip_angle_RR', 'tire_slip_angle_FL', 'tire_slip_angle_FR', 'acceleration_x', 'acceleration_y',
    'acceleration_z', 'velocity_x', 'velocity_y', 'velocity_z', 'accel', 'surface_rumble_FL', 'surface_rumble_FR', 'surface_rumble_RL', 'surface_rumble_RR', 'norm_driving_line', 'norm_ai_brake_diff', 'brake',
]


class Forza(CarInfo):
    def __init__(self, thread_pool: ThreadPoolExecutor, logger: logging.Logger = None, packet_format: str = 'fh4', enable_clutch: bool = False):
        super().__init__()
        self.ip: str = constants.ip
        self.port: int = constants.port
        self.logger: logging.Logger = (Logger()('Forza5')) if logger is None else logger
        self.packet_format: str = packet_format
        self.isRunning: bool = False
        self.threadPool: ThreadPoolExecutor = thread_pool
        self.enable_clutch: bool = enable_clutch
        self.farming: bool = False
        self.shift_point_factor: float = constants.shift_factor
        self.clutch: str = constants.clutch
        self.upshift: str = constants.upshift
        self.downshift: str = constants.downshift
        self.boundKeys = lambda: [self.clutch, self.upshift, self.downshift]
        self.config_folder: str = os.path.join(constants.root_path, constants.config_folder_name)
        if not os.path.exists(self.config_folder):
            os.makedirs(self.config_folder)
        helper.load_settings(self)
        self.gear_ratios: dict = {}
        self.rpm_torque_map: dict = {}
        self.shift_point: dict = {}
        self.records: list = []
        self.simulated_clutch: bool = False
        self.on_clutch_change = None
        self.last_upshift: float = time.time()
        self.last_downshift: float = time.time()
        self.last_shift: float = time.time()
        self._fdp_event: threading.Event = threading.Event()
        self._latest_fdp: ForzaDataPacket = None
        self.reset_car: int = 0
        self.isBrake: bool = False
        self.reset_time: float = time.time()
        self.reset_timer: float = time.time()
        self.break_timer: float = time.time()
        self.server_socket = None

    def test_gear(self, update_car_gui_func=None):
        """collect gear information

        Args:
            update_car_gui_func (optional): callback to update car gui. Defaults to None.
        """
        try:
            self.logger.debug(f'{self.test_gear.__name__} started')
            self.records = []
            while self.isRunning:
                self._fdp_event.clear()
                if not self._fdp_event.wait(timeout=1.0):
                    continue
                fdp = self._latest_fdp
                if fdp is None:
                    continue

                if fdp.speed > 0.1:
                    self.__update_forza_info(fdp, dump=False)
                    if update_car_gui_func is not None:
                        update_car_gui_func(fdp)
                    if fdp.current_engine_rpm > 1500 and fdp.clutch == 0:
                        ratio = fdp.speed * 3.6 / fdp.current_engine_rpm
                        info = {
                            'gear': fdp.gear,
                            'rpm': fdp.current_engine_rpm,
                            'time': time.time(),
                            'speed': fdp.speed * 3.6,
                            'slip': min(1.1, (fdp.tire_slip_ratio_RL + fdp.tire_slip_ratio_RR) / 2),
                            'clutch': fdp.clutch,
                            'power': fdp.power / 1000.0,
                            'torque': fdp.torque,
                            'speed/rpm': ratio
                        }
                        self.records.append(info)
                        self.logger.debug(info)
        except BaseException as e:
            self.logger.exception(e)
        finally:
            self.isRunning = False
            self.logger.debug(f'{self.test_gear.__name__} finished')

    def analyze_data(self):
        """analyze data (data processing only, safe to run in worker thread)"""
        try:
            self.logger.debug(f'{self.analyze_data.__name__} started')
            self.shift_point = gear_helper.calculate_optimal_shift_point(self)
            helper.dump_config(self)
            self._save_analysis_plot()
        except Exception as e:
            self.logger.exception(e)
            self.logger.error("something went wrong. please re-test the car")
        finally:
            self.logger.debug(f'{self.analyze_data.__name__} ended')

    def _save_analysis_plot(self):
        try:
            analysis_dir = os.path.join(constants.root_path, 'analysis')
            if not os.path.exists(analysis_dir):
                os.makedirs(analysis_dir)
            filename = f'{self.ordinal}-{self.car_perf}-{self.car_drivetrain}.png'
            filepath = os.path.join(analysis_dir, filename)

            plt.close()
            fig, ax = plt.subplots(2, 2, figsize=(25.6, 14.4), dpi=100)
            try:
                fig.tight_layout(pad=3.0)
            except Exception:
                pass
            plotter.plot_gear_ratio(self, ax, 0, 0)
            plotter.plot_torque_rpm(self, ax, 0, 1)
            plotter.plot_torque_speed(self, ax, 1, 0)
            plotter.plot_rpm_speed(self, ax, 1, 1)
            plt.savefig(filepath, bbox_inches='tight', dpi=100)
            plt.close()
            self.logger.info(f'Analysis plot saved to {filepath}')
        except Exception as e:
            self.logger.exception(e)
            self.logger.error("Failed to save analysis plot")

    def __update_forza_info(self, fdp: ForzaDataPacket, update_tree_func=lambda *args: None, dump: bool = True, first_load: bool = False):
        """update forza info while running

            # try to load config if:
            # self.ordinal != fdp.car_ordinal or self.car_perf != fdp.car_performance_index or self.car_class != fdp.car_class or self.car_drivetrain != fdp.drivetrain_type

        Args:
            fdp (ForzaDataPacket): datapackage
        """
        if first_load or self.ordinal != fdp.car_ordinal or self.car_perf != fdp.car_performance_index or self.car_class != fdp.car_class or self.car_drivetrain != fdp.drivetrain_type:
            self.ordinal = fdp.car_ordinal
            self.car_perf = fdp.car_performance_index
            self.car_class = fdp.car_class
            self.car_drivetrain = fdp.drivetrain_type
            res = True
            if dump:
                res = self.__try_auto_load_config(fdp)

            if not res:
                self.shift_point = {}

            if update_tree_func is not None:
                self.threadPool.submit(update_tree_func)

            return res
        else:
            return True

    def __try_auto_load_config(self, fdp: ForzaDataPacket):
        """auto load config while driving

        Args:
            fdp (ForzaDataPacket): fdp

        Returns:
            [bool]: success or failure
        """
        try:
            self.logger.debug(f'{self.__try_auto_load_config.__name__} started')
            configs = [f for f in listdir(self.config_folder) if (isfile(join(self.config_folder, f)) and str(fdp.car_ordinal) in f)]
            if len(configs) <= 0:
                self.logger.warning(f'config ({fdp.car_ordinal}) is not found at folder {self.config_folder}. Please run gear test ({constants.collect_data}) and/or analysis ({constants.analysis}) first!!')
                return False
            elif len(configs) > 0:
                self.logger.info(f'found ({fdp.car_ordinal}) config(s): {configs}')

                # latest config version: ordinal-perf-drivetrain.json, v2
                filename = helper.get_config_name(self)
                if filename is not None and filename in configs:
                    if self.__try_loading_config(filename):
                        # remove legacy config if necessary
                        if len(configs) > 1:
                            self.__cleanup_legacy_config(configs)

                        return True
                    else:
                        return False

                # if latest config version not existed. like only ordinal.json, v1
                filename = helper.get_config_name(self, ConfigVersion.v1)
                if filename is not None and filename in configs:
                    if self.__try_loading_config(filename):
                        self.car_perf = fdp.car_performance_index
                        self.car_class = fdp.car_class
                        self.car_drivetrain = fdp.drivetrain_type

                        # dump to latest config version
                        helper.dump_config(self)
                        self.__cleanup_legacy_config(configs)
                        return True
                    else:
                        return False

                # unknown config
                self.logger.warning(f'valid ({fdp.car_ordinal}) config(s) not found at {self.config_folder}: {configs}. Please run gear test ({constants.collect_data}) and/or analysis ({constants.analysis}) to create a new one!!')
                return False
        finally:
            self.logger.debug(f'{self.__try_auto_load_config.__name__} ended')

    def __cleanup_legacy_config(self, configs, latest_version: ConfigVersion = constants.default_config_version):
        """cleanup legacy configs

        Args:
            configs (list): list of configs
            latest_version (ConfigVersion, optional): config version. Defaults to constants.default_config_version.
        """
        for config in configs:
            version = helper.get_config_version(self, config)
            if version != latest_version:
                try:
                    self.logger.warning(f'removing legacy config {config}')
                    path = os.path.join(self.config_folder, config)
                    os.remove(path)
                except Exception as e:
                    self.logger.warning(f'failed to remove legacy config {config}: {e}')

    def __try_loading_config(self, config):
        """try to load config

        Args:
            config (str): config file name

        Returns:
            bool: success or failure
        """
        self.logger.info(f'loading config {config}')
        helper.load_config(self, os.path.join(self.config_folder, config))
        if len(self.shift_point) <= 0:
            self.logger.warning(f'Config is invalid. Please run gear test ({constants.collect_data}) and/or analysis ({constants.analysis}) to create a new one!!')
            return False

        self.logger.info(f'loaded config {config}')
        return True

    def shifting(self, iteration, fdp):
        gear = fdp.gear
        if len(self.shift_point) > 0 and fdp.speed > 0.1 and gear >= self.min_gear:
            iteration = iteration + 1

            slip = (fdp.tire_slip_ratio_RL + fdp.tire_slip_ratio_RR) / 2
            f_slip = (fdp.tire_slip_ratio_FL + fdp.tire_slip_ratio_FR) / 2
            angle_slip = abs((fdp.tire_slip_angle_RL + fdp.tire_slip_angle_RR) / 2)
            f_angle_slip = abs((fdp.tire_slip_angle_FL + fdp.tire_slip_angle_FR) / 2)
            slips = [slip, f_slip, angle_slip, f_angle_slip]
            speed = fdp.speed * 3.6
            rpm = fdp.current_engine_rpm
            accel = fdp.accel
            fired = False
            debug_log = fdp.to_list(debug_properties)
            self.logger.debug(f'[{iteration}] {debug_log}')

            if gear < self.max_gear and accel and gear in self.shift_point:
                target_rpm = self.shift_point[gear]['rpmo'] * self.shift_point_factor
                target_up_speed = int(self.shift_point[gear]['speed'] * self.shift_point_factor)

                if self.car_drivetrain == 1 and gear < 3 and (angle_slip >= 1 or slip >= 1):
                    target_rpm *= 0.95
                    target_up_speed = int(target_up_speed * 0.95)
                fired = self.__up_shift(rpm, target_rpm, speed, target_up_speed, slips, iteration, gear)

            if not fired and gear > self.min_gear:
                available_gears = self.shift_point.keys()
                if gear - 1 in available_gears:
                    lower_gear = gear - 1
                elif available_gears:
                    lower_gear = min(available_gears, key=lambda x: abs(x - (gear - 1)))
                else:
                    lower_gear = None

                if lower_gear is not None:
                    target_down_speed = self.shift_point[lower_gear]['speed'] * constants.downshift_hysteresis

                    if self.car_drivetrain == 1:
                        if gear >= 3:
                            self.__down_shift(speed, target_down_speed, slips, iteration, gear)
                    else:
                        self.__down_shift(speed, target_down_speed, slips, iteration, gear)

        return iteration

    def __up_shift(self, rpm: float, target_rpm: float, speed: float, target_up_speed: float, slips: list, iteration: int, gear: int):
        if rpm > target_rpm and slips[0] < 1 and speed > target_up_speed:
            self.logger.debug(f'[{iteration}] up shift triggered. rpm > target rmp({rpm} > {target_rpm}), speed > target up speed ({speed} > {target_up_speed}), slips {slips}')
            gear_helper.up_shift_handle(gear, self)
            return True
        else:
            return False

    def __down_shift(self, speed: float, target_down_speed: float, slips: list, iteration: int, gear: int):
        if speed < target_down_speed and slips[0] < 1:
            self.logger.debug(f'[{iteration}] down shift triggered. speed < target down speed ({speed} < {target_down_speed}), slips {slips}')
            gear_helper.down_shift_handle(gear, self)

    def __exp_farming_setup(self, fdp):
        """exp farming setup

        Args:
            fdp (ForzaDataPacket): datapackage
        """
        if self.farming and fdp.car_ordinal > 0:
            # enable reset car if exp or sp farming is True
            if abs(fdp.norm_driving_line) >= 127 or fdp.speed < 20:
                self.reset_car = self.reset_car + 1
                # reset car position
                if self.reset_car >= 100 and time.time() - self.reset_time > 10:
                    self.reset_car = 0
                    self.threadPool.submit(keyboard_helper.resetcar, self)
                    self.reset_time = time.time()
            else:
                self.reset_car = 0

            # exp or sp farming to avoid afk detection, 30s interval
            if time.time() - self.break_timer > 30 and fdp.norm_ai_brake_diff > 0:
                self.threadPool.submit(keyboard_helper.press_brake, self)
                self.break_timer = time.time()

    def run(self, update_tree_func=lambda *args: None, update_car_gui_func=lambda *args: None):
        try:
            self.logger.debug(f'{self.run.__name__} started')
            iteration = -1
            self.reset_car = 0
            self.reset_time = time.time()
            refresh_time = time.time()
            first_load = True
            last_data_time = time.time()
            enter_count = 0

            if self.farming:
                keyboard_helper.pressdown_str('w')

            while self.isRunning:
                self._fdp_event.clear()
                if not self._fdp_event.wait(timeout=1.0):
                    if self.farming and time.time() - last_data_time > 30:
                        enter_count += 1
                        self.logger.warning(f'No data for {int(time.time() - last_data_time)}s, sending Enter ({enter_count}/3)')
                        keyboard_helper.press_str('enter')
                        last_data_time = time.time()
                        if enter_count >= 3:
                            self.logger.error('Data timeout recovery failed after 3 attempts, stopping auto shift')
                            break
                    continue
                fdp = self._latest_fdp

                if fdp is None or fdp.car_ordinal <= 0:
                    continue

                last_data_time = time.time()
                enter_count = 0

                if update_car_gui_func is not None and time.time() - refresh_time > 0.1:
                    self.threadPool.submit(update_car_gui_func, fdp)
                    refresh_time = time.time()

                self.__update_forza_info(fdp, update_tree_func, first_load=first_load)
                first_load = False

                self.__exp_farming_setup(fdp)

                iteration = self.shifting(iteration, fdp)
        except BaseException as e:
            self.logger.exception(e)
        finally:
            self.isRunning = False
            if self.farming:
                keyboard_helper.release_str('w')

            self.logger.debug(f'{self.run.__name__} finished')
