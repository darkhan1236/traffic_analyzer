'''FrameElement — это контейнер одного кадра видео + всей информации о нём
кадр = фото 📦 FrameElement = папка с документами про это фото каждый node 
берёт FrameElement, добавляет/изменяет данные и передаёт дальше следующему node'''

import numpy as np
import time


class FrameElement:
    '''Класс, содержаций информацию о конкретном кадре видеопотока'''

    def __init__(
        self,
        source: str,
        frame: np.ndarray, 
        timestamp: float,
        frame_num: float,
        roads_info: dict,
        # черта | читается как «ИЛИ».  в этой переменной может лежать либо массив numpy или ничего
        frame_result: np.ndarray | None = None,
        detected_conf: list | None = None,
        detected_cls: list | None = None,
        # bounding boxes (детекция) Формат: [x1, y1, x2, y2] Пример: [[10,20,100,200], [50,60,120,180]]
        detected_xyxy: list[list] | None = None,
        tracked_conf: list | None = None,
        tracked_cls: list | None = None,
        tracked_xyxy: list[list] | None = None,
        id_list: list | None = None,
        buffer_tracks: dict | None = None,
    ) -> None:
        self.source = source # Путь к видео или номер камеры с которой берем поток
        self.frame = frame # кадр NumPy массив - форма: (H, W, 3)
        self.timestamp = timestamp # время с начала видео Пример: 12.53 секунд
        self.frame_num = frame_num # номер кадра
        self.roads_info = roads_info # Словарь с координатми дорог, примыкающих к участку кругового движения
        self.frame_result = frame_result # Итоговый обработанный кадр сюда рисуется: bbox - ID - текст - зоны
        # Результаты на выходе с YOLO:
        self.detected_conf = detected_conf # confidence от YOLOv8
        self.detected_cls = detected_cls # классы объектов
        self.detected_xyxy = detected_xyxy # bounding boxes (детекция)
        # Результаты корректировки трекинг алгоритмом:
        self.tracked_conf = tracked_conf # confidence после tracking
        self.tracked_cls = tracked_cls # классы после tracking
        self.tracked_xyxy = tracked_xyxy 
        self.id_list = id_list # ID объектов от ByteTrack
        # он копит координаты объекта из нескольких кадров подряд 
        # buffer_tracks нужен, чтобы понимать движение объекта во времени
        # с помощью этого можем посчитать скорость, направление и пересечение линий
        self.buffer_tracks = buffer_tracks # Буфер актуальных треков за выбранное время анализа
        self.info = {} # Словарь с результирующей статистикой (загруженность дорог + число машин)
        self.send_info_of_frame_to_db = False # Флаг того, будет ли с этого кадра инфа отправлена в бд


