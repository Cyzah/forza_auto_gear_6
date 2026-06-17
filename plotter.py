import numpy as np
from matplotlib.axes import Axes
from matplotlib.pyplot import cm


def _get_valid_gears(forza):
    return {g: item for g, item in forza.gear_ratios.items() if item['ratio'] > 0}


def plot_gear_ratio(forza, ax: np.ndarray, row: int, col: int):
    gear = np.array([item['gear'] for item in forza.records])
    time = np.array([item['time'] for item in forza.records])
    ratio = np.array([item['speed/rpm'] for item in forza.records])
    time0 = forza.records[0]['time']
    time = np.where(time > 0, time - time0, 0)

    a: Axes = ax[row, col]
    a.plot(time, ratio, label='speed/rpm', color='b')
    valid_gears = _get_valid_gears(forza)
    color = iter(cm.rainbow(np.linspace(0, 1, max(len(valid_gears), 1))))
    for g, item in valid_gears.items():
        a.hlines(item['ratio'], time[0], time[-1], label=f'gear {g} ratio', color=next(color), linestyles='dashed')
    a.set_xlabel('time')
    a.set_ylabel('ratio (km/h/rpm)', color='b')
    a.tick_params('y', color='b')
    a.legend(fontsize=8)
    a.set_title('Gear Ratio (speed/rpm)')

    ax0 = a.twinx()
    ax0.plot(time, gear, label='gear', color='r')
    ax0.set_ylabel('gear', color='r')
    ax0.tick_params('y', colors='r')
    ax0.legend(loc=4, fontsize=8)


def plot_torque_rpm(forza, ax: np.ndarray, row: int, col: int):
    a: Axes = ax[row, col]
    valid_gears = _get_valid_gears(forza)
    color = iter(cm.rainbow(np.linspace(0, 1, max(len(valid_gears), 1))))
    for g in sorted(valid_gears.keys()):
        if g not in forza.rpm_torque_map:
            continue
        item = forza.rpm_torque_map[g]
        raw_records = forza.get_gear_raw_records(g)
        if not raw_records:
            continue
        data = np.array([[i['rpm'], i['torque']] for i in raw_records[item['min_rpm_index']:item['max_rpm_index'] + 1]])
        data = np.sort(data, 0)
        c = next(color)

        rpms = np.array([d[0] for d in data])
        torque = np.array([d[1] for d in data])
        ratio = valid_gears[g]['ratio']

        a.plot(rpms, torque / ratio, label=f'Gear {g} torque', color=c)
        a.set_xlabel('rpm (r/m)')
        a.set_ylabel('Torque (N/m)')
        a.tick_params('y')

    a.legend(loc='lower left', fontsize=8)
    a.set_title('Output Torque vs rpm')
    a.grid(visible=True, color='grey', linestyle='--')


def plot_torque_speed(forza, ax: np.ndarray, row: int, col: int):
    a: Axes = ax[row, col]
    valid_gears = _get_valid_gears(forza)
    color = iter(cm.rainbow(np.linspace(0, 1, max(len(valid_gears), 1))))
    for g in sorted(valid_gears.keys()):
        if g not in forza.rpm_torque_map:
            continue
        item = forza.rpm_torque_map[g]
        raw_records = forza.get_gear_raw_records(g)
        if not raw_records:
            continue
        data = np.array([[i['speed'], i['torque']] for i in raw_records[item['min_rpm_index']:item['max_rpm_index'] + 1]])
        data = np.sort(data, 0)
        c = next(color)

        speeds = np.array([d[0] for d in data])
        torque = np.array([d[1] for d in data])
        ratio = valid_gears[g]['ratio']

        a.plot(speeds, torque / ratio, label=f'Gear {g} torque', color=c)
        a.set_xlabel('speed (km/h)')
        a.set_ylabel('Torque (N/m)')
        a.tick_params('y')

    a.legend(loc='upper right', fontsize=8)
    a.set_title('Output Torque vs Speed')
    a.grid(visible=True, color='grey', linestyle='--')


def plot_rpm_speed(forza, ax: np.ndarray, row: int, col: int):
    a: Axes = ax[row, col]
    valid_gears = _get_valid_gears(forza)
    color = iter(cm.rainbow(np.linspace(0, 1, max(len(valid_gears), 1))))
    for g in sorted(valid_gears.keys()):
        if g not in forza.rpm_torque_map:
            continue
        item = forza.rpm_torque_map[g]
        raw_records = forza.get_gear_raw_records(g)
        if not raw_records:
            continue
        data = np.array([[i['speed'], i['rpm']] for i in raw_records[item['min_rpm_index']:item['max_rpm_index'] + 1]])
        data = np.sort(data, 0)
        c = next(color)

        speeds = np.array([d[0] for d in data])
        rpm = np.array([d[1] for d in data])

        a.plot(speeds, rpm, label=f'Gear {g} rpm', color=c)
        a.set_xlabel('speed (km/h)')
        a.set_ylabel('rpm (r/m)')
        a.tick_params('y')

    a.legend(loc='lower right', fontsize=8)
    a.set_title('rpm vs Speed')
    a.grid(visible=True, color='grey', linestyle='--')
