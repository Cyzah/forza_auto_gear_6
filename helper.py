import json
import locale
import os
import socket
import sys
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from forza import Forza

from fdp import ForzaDataPacket

import constants
import keyboard_helper
from constants import ConfigVersion


def nextFdp(server_socket: socket.socket, fmt: str) -> Optional[ForzaDataPacket]:
    try:
        message, _ = server_socket.recvfrom(1024)
        return ForzaDataPacket(message, packet_format=fmt)
    except BaseException:
        return None


def convert(n: object):
    import numpy as np
    if isinstance(n, (np.int32, np.int64)):
        return n.item()


def dump_settings(forza: 'Forza'):
    json_data = {
        'clutch':       forza.clutch,
        'upshift':      forza.upshift,
        'downshift':    forza.downshift,
        'offroad_rally': forza.shift_point_factor == constants.offroad_rally_shift_factor,
        'enable_clutch': forza.enable_clutch,
        'farming':      forza.farming,
    }
    settings_path = os.path.join(forza.config_folder, constants.setting_filename)
    forza.logger.info(f'saving program settings to {settings_path}')
    with open(settings_path, "w") as f:
        json.dump(json_data, f, default=convert, indent=4)


def dump_config(forza: 'Forza', config_version: ConfigVersion = constants.default_config_version):
    try:
        forza.logger.debug(f'{dump_config.__name__} started')
        config_name = get_config_name(forza, config_version)
        forza.logger.info(f'saving config {config_name}')
        config = {
            'version': config_version.name,
            'ordinal': forza.ordinal,
            'perf': forza.car_perf,
            'class': forza.car_class,
            'drivetrain': forza.car_drivetrain,
            'min_gear': forza.min_gear,
            'max_gear': forza.max_gear,
            'gear_ratios': forza.gear_ratios,
            'rpm_torque_map': forza.rpm_torque_map,
            'shift_point': forza.shift_point,
            'records': forza.records,
        }
        with open(os.path.join(forza.config_folder, config_name), "w") as f:
            json.dump(config, f, default=convert, indent=4)
    finally:
        forza.logger.debug(f'{dump_config.__name__} ended')


def get_config_version(forza: 'Forza', filename: str) -> ConfigVersion:
    try:
        with open(os.path.join(forza.config_folder, filename), "r") as f:
            config = json.loads(f.read())
        if 'version' in config:
            if config['version'] == str(ConfigVersion.v2):
                return ConfigVersion.v2
            elif config['version'] == str(ConfigVersion.v1):
                return ConfigVersion.v1
            else:
                return ConfigVersion[config['version']]
        else:
            return ConfigVersion.v1
    except Exception as e:
        forza.logger.warning(f'failed to get version of {filename}: {e}')
        return ConfigVersion.v1


def get_config_name(forza: 'Forza', config_version: ConfigVersion = constants.default_config_version) -> Optional[str]:
    if config_version == ConfigVersion.v2:
        return f'{forza.ordinal}-{forza.car_perf}-{forza.car_drivetrain}.json'
    elif config_version == ConfigVersion.v1:
        return f'{forza.ordinal}.json'
    else:
        forza.logger.warning(f'Invalid config version {str(config_version)}')
        return None


def load_settings(forza: 'Forza'):
    forza.logger.debug(f'{load_settings.__name__} started')
    settings_path = os.path.join(forza.config_folder, constants.setting_filename)
    try:
        valid_keys = keyboard_helper.keybind.keys()
        if os.path.exists(settings_path):
            forza.logger.info(f'loading program settings from {settings_path}')
            with open(settings_path, "r") as f:
                settings = json.loads(f.read())
            if 'clutch' in settings:
                clutch_shortcut = settings['clutch']
                if clutch_shortcut in valid_keys:
                    forza.clutch = clutch_shortcut
                else:
                    forza.logger.warning(f'clutch shortcut {clutch_shortcut} in {settings_path} is not valid')
            if 'upshift' in settings:
                upshift_shortcut = settings['upshift']
                if upshift_shortcut in valid_keys:
                    forza.upshift = upshift_shortcut
                else:
                    forza.logger.warning(f'upshift shortcut {upshift_shortcut} in {settings_path} is not valid')
            if 'downshift' in settings:
                downshift_shortcut = settings['downshift']
                if downshift_shortcut in valid_keys:
                    forza.downshift = downshift_shortcut
                else:
                    forza.logger.warning(f'downshift shortcut {downshift_shortcut} in {settings_path} is not valid')
            if 'offroad_rally' in settings:
                forza.shift_point_factor = constants.offroad_rally_shift_factor if settings['offroad_rally'] else constants.shift_factor
            if 'enable_clutch' in settings:
                forza.enable_clutch = settings['enable_clutch']
            if 'farming' in settings:
                forza.farming = settings['farming']
    except Exception as e:
        forza.logger.warning(f'failed to load settings {settings_path}: {e}')
    finally:
        forza.logger.debug(f'{load_settings.__name__} ended')


def load_config(forza: 'Forza', path: str):
    try:
        forza.logger.debug(f'{load_config.__name__} started')
        with open(os.path.join(forza.config_folder, path), "r") as f:
            config = json.loads(f.read())
        if 'ordinal' in config:
            forza.ordinal = int(config['ordinal'])
        if 'perf' in config:
            forza.car_perf = int(config['perf'])
        if 'class' in config:
            forza.car_class = int(config['class'])
        if 'drivetrain' in config:
            forza.car_drivetrain = int(config['drivetrain'])
        if 'minGear' in config:
            forza.min_gear = config['minGear']
        elif 'min_gear' in config:
            forza.min_gear = config['min_gear']
        if 'maxGear' in config:
            forza.max_gear = config['maxGear']
        elif 'max_gear' in config:
            forza.max_gear = config['max_gear']
        if 'gear_ratios' in config:
            forza.gear_ratios = {int(key): value for key, value in config['gear_ratios'].items()}
        if 'rpm_torque_map' in config:
            forza.rpm_torque_map = {int(key): value for key, value in config['rpm_torque_map'].items()}
        if 'shift_point' in config:
            forza.shift_point = {int(key): value for key, value in config['shift_point'].items()}
        if 'records' in config:
            forza.records = config['records']
    except BaseException as e:
        forza.logger.exception(e)
    finally:
        forza.logger.debug(f'{load_config.__name__} ended')


def get_sys_lang() -> int:
    try:
        lang = locale.getdefaultlocale()[0]
        if lang is not None:
            return 1 if 'zh' in lang else 0
        return constants.default_language
    except Exception:
        return constants.default_language


def create_socket(forza: 'Forza'):
    if getattr(forza, 'server_socket', None) is not None:
        try:
            forza.server_socket.getsockname()
            forza.logger.info('reusing existing socket')
            return
        except Exception:
            pass
    forza.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    forza.server_socket.settimeout(1)
    forza.server_socket.bind((forza.ip, forza.port))
    forza.logger.info(f'listening on IP {forza.ip}, Port {forza.port}')


def close_socket(forza: 'Forza'):
    if getattr(forza, 'server_socket', None):
        try:
            forza.server_socket.close()
        except Exception:
            pass
        forza.server_socket = None
        forza.logger.info('socket closed')
