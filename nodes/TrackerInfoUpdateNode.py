import logging
from logging import config 

from elements.FrameElement import FrameElement
from elements.VideoEndBreakElement import VideoEndBreakElement
from elements.TrackElement import TrackElement
from utils_local.utils import profile_time, intersects_central_point 

# создаём логгер с именем "buffer_tracks"
logger = logging.getLogger("buffer_tracks")

class TrackerInfoUpdateNode:
    """Модуль обновления актуальных трековю."""

    def __init__(self, config: dict) -> None:
        config_general = config["general"]
        
        self.size_buffer_analytics = (
            config_general["buffer_analytics"] * 60
        ) # число секунд в буфере аналитики (сколько времени хранить треки в памяти для аналитики)
        # добавим мин времени жизни чтобы при расчете статистики были именно машины за последие buffer_analytics минут:
        self.size_buffer_analytics += config_general["min_time_life_track"]
        self.buffer_tracks = {} # Буфер актуальных треков (словарь, где ключ - id трека, значение - объект TrackElement)

    # декоратор для замера времени выполнения функции
    @profile_time 
    def process(self, frame_element: FrameElement) -> FrameElement:
        # Выйти из если это пришел VideoEndBreakElement а не FrameElement
        if isinstance(frame_element, VideoEndBreakElement):
            return frame_element 
        assert isinstance(
            frame_element, FrameElement
        ), f"TrackerInfoupdateNode | Неправильный формат входного элемента {type(frame_element)}"

        # `id_list` - это список идентификаторов треков, которые были обнаружены на текущем кадре.
        id_list = frame_element.id_list 

        for i, id in enumerate(id_list):
            # Обновление или создание нового трека 
            if id not in self.buffer_tracks:
                # Создаем новый ключ 
                self.buffer_tracks[id] = TrackElement(
                    id=id,
                    timestamp_first=frame_element.timestamp,
                )
            # Если трек уже существует в буфере, то обновляем время последнего обнаружения этого трека (метод update класса TrackElement)
            else:
                # Обновление времени последнего обнаружения
                self.buffer_tracks[id].update(frame_element.timestamp) 

            # Поиск первого пересечения с полигонами дорог
            if self.buffer_tracks[id].start_road is None:
                self.buffer_tracks[id].start_road = intersects_central_point(
                    tracked_xyxy=frame_element.tracked_xyxy[i],
                    polygons=frame_element.roads_info,
                )
                # Проверка того, что отработка функции дала наконец-то актуальный номер дороги:
                if self.buffer_tracks[id].start_road is not None:
                    # Тогда сохраняем время такого момента:
                    self.buffer_tracks[id].timestamp_init_road = frame_element.timestamp 

        # Удаление старых айдишников из словаря если их время жизни > size_buffer_analytics
        keys_to_remove = []
        for key, track_element in sorted(self.buffer_tracks.items()):
            # Если время жизни трека (текущее время - время последнего обнаружения) больше размера буфера аналитики, то добавляем этот ключ в список на удаление
            if frame_element.timestamp - track_element.timestamp_first < self.size_buffer_analytics:
                break 
            else:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            self.buffer_tracks.pop(key) # Удаляем элемент из словаря
            logger.info(f"Removed tracker with key {key}")

        # Запись результатов обработки:
        frame_element.buffer_tracks = self.buffer_tracks 

        return frame_element 
    
