import time
from typing import TYPE_CHECKING

import numpy as np

import constants
import keyboard_helper
from car_info import CarInfo

if TYPE_CHECKING:
    from forza import Forza

# === Optimal Shift Point ===
# speed = rpm * 60 * (dia of tire * PI ) / gear ratio / other ratio
# dia of tire, other ratio and PI are constants, said C. So we have:
# speed = C * rpm * / gear ratio / other ratio, where the gR is the 1/ (gear ratio * other ratio)
# speed = rpm * gR (gear ratio), where the gR is the 1/ (gear ratio * other ratio * C)
# The best shift point is using: https://glennmessersmith.com/shiftpt.html
#
# Now we want to shift from Gear G1 to Gear G2 (continued) at r (rpm), the gear ratio is gR1 and gR2 while at G1 and G2.
# Let's said getTorque(r) return the Torque while rpm is r.
# We have: delta = getTorque(r) / gR1 - getTorque(r / gR2 * gR1) / gR2
# The goal is to make sure the delta is closed to 0. Then the r is the optimal shift point, said rpmo.
# We cannot get the gR1 or gR2 directly but we know we could get C * gR from speed / rpm, said S/R, while at Gear G.
# Then we could calculate gRn at Gn by (Sn / Rn), said gR(G) is the ration at Gear G
# Meanwhile the C is a constant and could be combined with gR. We have:
# delta(r, G) = getTorque(r) / gR(G) - getTorque(r / gR(G + 1) * gR(G)) / gR(G + 1)
# and delta(r, G) -> 0


def set_car_properties(records: dict, forza: CarInfo):
    gears = np.array([item['gear'] for item in records])
    gear_list = np.unique(gears)
    forza.min_gear = gear_list.min()
    forza.max_gear = gear_list.max()


def get_rpm_torque_map(records: dict, forza: CarInfo):
    res = {}

    for g in sorted(records.keys()):
        torques = np.array([item['torque'] for item in records[g]])
        n = len(torques)

        torque_indices = np.where(torques < 0)[0]
        length = -1
        min_rpm_index = 0
        max_rpm_index = n - 1

        if len(torque_indices) == 0:
            pass
        else:
            for i in range(len(torque_indices)):
                if torque_indices[i] == 0:
                    continue

                if i == 0 and torque_indices[i] > 0:
                    length = torque_indices[i]
                    min_rpm_index = 0
                    max_rpm_index = torque_indices[i] - 1
                elif i == len(torque_indices) - 1 and torque_indices[i] < n - 1:
                    tmp_len = n - torque_indices[i] - 1
                    if tmp_len > length:
                        length = tmp_len
                        min_rpm_index = torque_indices[i] + 1
                        max_rpm_index = n - 1
                else:
                    tmp_len = torque_indices[i] - torque_indices[i - 1] - 1
                    if tmp_len > length:
                        length = tmp_len
                        min_rpm_index = torque_indices[i - 1] + 1
                        max_rpm_index = torque_indices[i] - 1

        if min_rpm_index > max_rpm_index:
            min_rpm_index = 0
            max_rpm_index = n - 1

        res[g] = {'min_rpm_index': min_rpm_index, 'max_rpm_index': max_rpm_index}

        lower_rpm = records[g][min_rpm_index]['rpm']
        upper_rpm = records[g][max_rpm_index]['rpm']
        forza.logger.info(f'For Gear {g}, the min_rpm_index: {min_rpm_index}, max_rpm_index: {max_rpm_index}, rpm range: {lower_rpm} ~ {upper_rpm}')
    return res


def get_gear_ratio_map(records: dict, forza):
    """get gear ratio on each gear

    Args:
        records (dict): records
        forza: car info

    Returns:
        [dict]: gear ratio on each gear
    """
    res = {}

    for gear, items in records.items():
        var = 99999
        ratio = -1
        for index in range(0, len(items) - 20, 5):
            t = items[index:index + 20]
            ratios = [item['speed/rpm'] for item in t]
            tmp_var = np.var(ratios)
            if tmp_var < var:
                ratio = np.average(ratios)
                var = tmp_var

        forza.logger.info(f'Gear ratio at Gear {gear} is {ratio}')
        res[gear] = {
            'ratio': ratio,
        }

    return res


def get_torque(r: float, record_by_gear: list):
    """get torque by rpm on a specific gear

    Args:
        r (int): rpm
        record_by_gear (list): record

    Returns:
        [float]: torque
    """
    rpms = np.array([item['rpm'] for item in record_by_gear])

    # find the closest rpm vs r in rpms list
    r_index = np.abs(rpms - r).argmin()
    return record_by_gear[r_index]['torque']



def calculate_optimal_shift_point(forza: 'Forza'):
    res = {}
    records_by_gears = {}
    for items in forza.records:
        gear = items['gear']
        if gear not in records_by_gears:
            records_by_gears[gear] = []
        records_by_gears[gear].append(items)

    set_car_properties(forza.records, forza)
    forza.gear_ratios = get_gear_ratio_map(records_by_gears, forza)

    forward_gears = [g for g in forza.gear_ratios if forza.gear_ratios[g]['ratio'] > 0]
    if forward_gears:
        forza.min_gear = min(forward_gears)
        forza.max_gear = max(forward_gears)

    forza.rpm_torque_map = get_rpm_torque_map(records_by_gears, forza)
    forward_gears = sorted([g for g in forza.gear_ratios.keys() if forza.gear_ratios[g]['ratio'] > 0])

    for i in range(len(forward_gears) - 1):
        gear = forward_gears[i]
        next_gear = forward_gears[i + 1]

        rpm_torque = forza.rpm_torque_map[gear]
        rpm_torque1 = forza.rpm_torque_map[next_gear]
        rpm_to_torque = records_by_gears[gear][rpm_torque['min_rpm_index']:rpm_torque['max_rpm_index'] + 1]
        rpm_to_torque1 = records_by_gears[next_gear][rpm_torque1['min_rpm_index']:rpm_torque1['max_rpm_index'] + 1]

        ratio = forza.gear_ratios[gear]['ratio']
        ratio1 = forza.gear_ratios[next_gear]['ratio']

        rpms = np.array([item['rpm'] for item in rpm_to_torque])
        rpms1 = np.array([item['rpm'] for item in rpm_to_torque1])

        if len(rpms) == 0 or len(rpms1) == 0:
            forza.logger.warning(f'Skipping optimal shift point from {gear} to {next_gear}: insufficient data')
            continue

        max_rpm = int(max(np.max(rpms), np.max(rpms1)))
        min_rpm = int(max(np.min(rpms), np.min(rpms1)))

        step = 10
        prev_delta = None
        rpmo = max_rpm
        min_dt_torque = 9999999

        for r in range(max_rpm, min_rpm, -step):
            torque = get_torque(r, rpm_to_torque) / ratio
            r_next = r * ratio / ratio1
            torque1 = get_torque(r_next, rpm_to_torque1) / ratio1
            delta = torque - torque1

            if abs(delta) < min_dt_torque:
                min_dt_torque = abs(delta)
                rpmo = r

            if prev_delta is not None and prev_delta > 0 and delta <= 0:
                frac = prev_delta / (prev_delta - delta)
                rpmo = (r + step) - step * frac
                break

            prev_delta = delta

        speedo = rpm_to_torque[np.abs(rpms - rpmo).argmin()]['speed']
        forza.logger.info(f'Optimal shift point from {gear} to {next_gear}: rpm={rpmo:.0f}, speed={speedo:.1f} km/h, delta_torque={min_dt_torque:.1f}')
        res[gear] = {'rpmo': rpmo, 'speed': speedo}

    return res


def blip_throttle():
    keyboard_helper.pressdown_str(constants.acceleration)
    time.sleep(constants.blip_throttle_duration)
    keyboard_helper.release_str(constants.acceleration)


def _shift_handle(gear: int, forza: 'Forza', direction: str):
    is_up = direction == 'up'
    label = '[UpShift]' if is_up else '[DownShift]'
    target_gear = gear + 1 if is_up else gear - 1
    shift_key = forza.upshift if is_up else forza.downshift
    max_gear = forza.max_gear if is_up else forza.min_gear
    in_range = gear < max_gear if is_up else gear > max_gear
    in_range = in_range and (gear in forza.shift_point if is_up else True)

    cur = time.time()
    last_shift_time = forza.last_upshift if is_up else forza.last_downshift

    if in_range and cur - forza.last_shift >= constants.shift_cooldown:
        gap = cur - last_shift_time
        forza.logger.info(f'{label} {gear} > {target_gear} ({"max" if is_up else "min"}: {max_gear}), gap >= shift_cooldown ({gap:.2f} >= {constants.shift_cooldown})')

        if is_up:
            forza.last_upshift = cur
        else:
            forza.last_downshift = cur
        forza.last_shift = cur

        if forza.farming:
            keyboard_helper.release_str(constants.acceleration)
            time.sleep(0.08)

        if forza.enable_clutch:
            forza.simulated_clutch = True
            if forza.on_clutch_change:
                forza.on_clutch_change(True)
            keyboard_helper.pressdown_str(forza.clutch)
            time.sleep(0.04)
            forza.logger.debug(f'{label} clutch {forza.clutch} down on {gear}')

        keyboard_helper.press_str(shift_key)
        forza.logger.debug(f'{label} {"upshift" if is_up else "downshift"} {shift_key} down and up on {gear}')

        if forza.enable_clutch:
            keyboard_helper.release_str(forza.clutch)
            time.sleep(0.04)
            forza.simulated_clutch = False
            if forza.on_clutch_change:
                forza.on_clutch_change(False)
            forza.logger.debug(f'{label} clutch {forza.clutch} up on {gear}')

        if forza.farming:
            keyboard_helper.pressdown_str(constants.acceleration)
    else:
        gap = cur - last_shift_time
        forza.logger.debug(f'{label} skip. {gear} > {target_gear} ({"max" if is_up else "min"}: {max_gear}), gear out of range or gap < shift_cooldown ({gap:.2f} < {constants.shift_cooldown})')


def up_shift_handle(gear: int, forza: 'Forza'):
    _shift_handle(gear, forza, 'up')


def down_shift_handle(gear: int, forza: 'Forza'):
    _shift_handle(gear, forza, 'down')
