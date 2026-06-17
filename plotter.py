import numpy as np
from matplotlib.axes import Axes
from matplotlib.pyplot import cm


def _get_valid_gears(forza):
    return {g: item for g, item in forza.gear_ratios.items() if item['ratio'] > 0}


def _get_gear_data(forza, g, x_key, y_key):
    """Extract sorted x/y data for a gear from records."""
    if g not in forza.rpm_torque_map:
        return None, None
    item = forza.rpm_torque_map[g]
    raw_records = forza.get_gear_raw_records(g)
    if not raw_records:
        return None, None
    data = np.array([[i[x_key], i[y_key]] for i in raw_records[item['min_rpm_index']:item['max_rpm_index'] + 1]])
    data = np.sort(data, 0)
    return np.array([d[0] for d in data]), np.array([d[1] for d in data])


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
        x, y = _get_gear_data(forza, g, 'rpm', 'torque')
        if x is None:
            continue
        ratio = valid_gears[g]['ratio']
        a.plot(x, y / ratio, label=f'Gear {g} torque', color=next(color))
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
        x, y = _get_gear_data(forza, g, 'speed', 'torque')
        if x is None:
            continue
        ratio = valid_gears[g]['ratio']
        a.plot(x, y / ratio, label=f'Gear {g} torque', color=next(color))
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
        x, y = _get_gear_data(forza, g, 'speed', 'rpm')
        if x is None:
            continue
        a.plot(x, y, label=f'Gear {g} rpm', color=next(color))
    a.set_xlabel('speed (km/h)')
    a.set_ylabel('rpm (r/m)')
    a.tick_params('y')
    a.legend(loc='lower right', fontsize=8)
    a.set_title('rpm vs Speed')
    a.grid(visible=True, color='grey', linestyle='--')
