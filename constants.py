import enum
import os
import sys
from pynput.keyboard import Key


# config version
class ConfigVersion(enum.Enum):
    v1 = 1
    v2 = 2


default_config_version = ConfigVersion.v2

# repo path - use exe directory when frozen
if getattr(sys, 'frozen', False):
    root_path = os.path.dirname(sys.executable)
else:
    root_path = os.path.dirname(os.path.abspath(__file__))

sys.path.append(os.path.join(root_path, 'forza_motorsport'))
setting_filename = 'settings.json'
config_folder_name = 'configs'

# socket information
ip = '127.0.0.1'
port = 12350

# data format
packet_format = 'fh4'

# clutch setup
enable_clutch = True

# default car config
example_car_ordinal = 'example'

# === UI settings ===
background_color = "#1a181a"
text_color = "#a1a1a1"
accent_color = "#0f3460"
highlight_color = "#e94560"
text_secondary = "#a0a0b0"

# car drivetrain
car_drivetrain_list = [
    ('FWD', '前驱'),
    ('RWD', '后驱'),
    ('AWD', '四驱'),
    ('N', 'N')
]

# car class mapping
car_class_list = ['D', 'C', 'B', 'A', 'S1', 'S2', 'R', 'X', 'N']
car_class_color = ['#3dafd1', '#edc786', '#f28240', '#e22b2a', '#8729e2', '#3256ba', '#E91E8C', '#46ce67', text_color]

# === short-cut ===
stop = Key.pause  # stop program
close = Key.end  # close program
collect_data = Key.f10
analysis = Key.f8
auto_shift = Key.f7

# === Keyboard ===
clutch = 'i'  # clutch
upshift = 'e'  # up shift
downshift = 'q'  # down shift
acceleration = 'w'  # acceleration
brake = 's'  # brake

# === Delay Settings ===
delay_clutch_to_shift = 0.08
delay_shift_to_clutch = 0.06
delay_shift_to_throttle = 0.1
downshift_cooldown = 0.35
upshift_cooldown = 0.35
shift_cooldown = 0.5
blip_throttle_duration = 0.12

# === Gear Shift Settings ===
shift_factor = 0.99
offroad_rally_shift_factor = 0.93
downshift_hysteresis = 0.94  # additional reduction for downshift threshold to prevent up/down oscillation

# === Text Settings ===
select_language_txt = ['Select Language:', '选择语言:']
language_txt = ['English', '中文']
default_language = 0

clutch_shortcut_txt = ['Clutch Shortcut:', '离合快捷键:']
upshift_shortcut_txt = ['Upshift Shortcut:', '升档快捷键:']
downshift_shortcut_txt = ['Downshift Shortcut:', '降档快捷键:']
clutch_status_txt = ['Clutch', '离合']
clutch_txt = ['Enable Clutch', '开启离合']
farm_txt = ['Enable Farm', '开启刷图']
offroad_rally_txt = ['Offroad, Rally', '越野，拉力']
car_id = ['Car ID:', '车辆序号:']
car_class = ['Car Class:', '车辆等级:']
car_perf = ['Car Performance:', '车辆性能:']
car_drivetrain = ['Car Drivetrain:', '车辆传动:']
tire_information_txt = ['Tire Information', '轮胎信息']
accel_txt = ['Acceleration', '加速']
brake_txt = ['Brake', '刹车']
shift_point_txt = ['Shift Point', '换挡点']
tree_value_txt = ['Value', '结果']
speed_txt = ['Speed', '速度']
rpm_txt = ['RPM', '转速']
collect_button_txt = ['Collect Data', '收集数据']
analysis_button_txt = ['Analysis', '分析数据']
run_button_txt = ['Run Auto Shift', '运行自动换挡']
pause_button_txt = ['Pause', '暂停']
exit_button_txt = ['Exit', '退出']
clear_log_txt = ['Clear', '清空']
save_shift_txt = ['Save Shift Points', '保存换挡点']

program_info_txt = [
    'If you found any issues, or want to contribute to the program, feel free to visit github: https://github.com/Cyzah/forza_auto_gear_6',
    '如果您发现任何bugs，或想参加这个project，欢迎访问我的github: https://github.com/Cyzah/forza_auto_gear_6'
]

live_data_txt = ['Live Data', '实时数据']
