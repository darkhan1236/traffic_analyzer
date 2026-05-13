class TrackElement:
    """Класс, содержащий информацию о конкретном треке машины
    TrackElement → что происходит с одной машиной"""
    def __init__(
            self, 
            id: int, 
            timestamp_first: float,
            start_road: int | None = None,
    ) -> None:
        self.id = id # Номер этого трека
        self.timestamp_first = timestamp_first # Таймстемп инициализации (в сек)
        self.timestamp_last = timestamp_first # Таймстемп последнего обнаружения (в сек)
        self.start_road = start_road # Номер дороги, с которой приехал может быть: None → ещё не определили
        self.timestamp_init_road = timestamp_first # Таймстемп инициализации номера дороги (в сек)
        # ps: если дорога не будет определена, то значение останется равным первому появлению
    # вызывается каждый кадр, когда объект снова найден
    def update(self, timestamp):
         # Обновление времени последнего обнаружения
        self.timestamp_last = timestamp 