class CarInfo:
    def __init__(self):
        self.ordinal = -1
        self.car_perf = 0
        self.car_class = -1
        self.car_drivetrain = -1
        self.min_gear = 1
        self.max_gear = 10
        self.gear_ratios = {}
        self.rpm_torque_map = {}
        self.shift_point = {}
        self.records = []
        self.logger = None
        self._records_by_gear_cache = {}
        self._records_dirty = True

    def set_records(self, records):
        self.records = records
        self._records_dirty = True
        self._records_by_gear_cache.clear()

    def get_gear_raw_records(self, g: int):
        if self._records_dirty or g not in self._records_by_gear_cache:
            self._records_by_gear_cache[g] = [item for item in self.records if item['gear'] == g]
            self._records_dirty = False
        return self._records_by_gear_cache[g]
