from ultralytics import YOLO 
import torch 
import numpy as np

# декоратор — считает время выполнения функции
from utils_local.utils import profile_time
from elements.FrameElement import FrameElement 
from elements.VideoEndBreakElement import VideoEndBreakElement 
# алгоритм трекинга (следит за объектами)
from byte_tracker.byte_tracker_model import BYTETracker as ByteTracker

class DetectionTrackingNodes:
    """Модуль инференса модели детекции + трекинг алгоритма"""

    def __init__(self, config) -> None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Детекция будет производиться на {device}")

        config_yolo = config["detection_node"] # берём настройки
        self.model = YOLO(config_yolo["weight_pth"], task="detect") # загружаем модель (веса)
        self.classes = self.model.names # список классов (car, person…) 
        self.conf = config_yolo["confidence"] # порог уверенности для детекции
        self.iou = config_yolo["iou"] # порог для NMS (non-maximum suppression) - алгоритм для удаления лишних детекций
        self.imgsz = config_yolo["imgsz"] # размер входного изображения для модели
        self.classes_to_detect = config_yolo["classes_to_detect"] # классы для детекции (например только машины)

        config_bytetrack = config["tracking_node"] # настройки для трекера

        # ByteTrack param
        first_track_thresh = config_bytetrack["first_track_thresh"]
        second_track_thresh = config_bytetrack["second_track_thresh"] # пороги для трекера (для создания новых треков и поддержания существующих)
        match_thresh = config_bytetrack["match_thresh"] 
        track_buffer = config_bytetrack["track_buffer"] # сколько кадров держать трек в памяти без обновления
        fps = 30 
        # инициализируем трекер с этими параметрами (ByteTracker - алгоритм трекинга, который хорошо работает с детекциями от YOLO)
        self.tracker = ByteTracker(
            fps, first_track_thresh, second_track_thresh, match_thresh, track_buffer, 1
        ) 


    @profile_time # декоратор для замера времени выполнения функции
    def process(self, frame_element: FrameElement) -> FrameElement:
        '''принимает кадр, возвращает обработанный кадр'''
        # Выйти из обработки если это пришел VideoEndBreakElement а не FrameElement 
        # Функция isinstance(obj, Class) проверяет: является ли объект экземпляром класса
        if isinstance(frame_element, VideoEndBreakElement):
            return frame_element 
        assert isinstance(
            frame_element, FrameElement
        ), f"DetectionTrackingNodes | Неправильный формат входного элемента {type(frame_element)}"

        frame = frame_element.frame.copy() # копируем кадр из элемента
        # outputs: объект(ы) результатов от Ultralytics YOLO (обычно список Results). Каждый результат содержит поля с детекциями:
        outputs = self.model.predict(frame, imgsz=self.imgsz, conf=self.conf, verbose=False,
                                     iou=self.iou, classes=self.classes_to_detect) # получаем детекции от модели 
        frame_element.detected_conf = outputs[0].boxes.conf.cpu().tolist() # сохраняем confidence детекций в элементе кадра
        detected_cls = outputs[0].boxes.cls.cpu().int().tolist() # получаем классы детекций (числовые индексы)
        frame_element.detected_cls = [self.classes[i] for i in detected_cls] # преобразуем числовые классы в текстовые (car, person…)
        frame_element.detected_xyxy = outputs[0].boxes.xyxy.cpu().int().tolist() # получаем координаты боксов детекций (формат [x1, y1, x2, y2])
        
        # Преподготовка данных на подачу в трекер
        # Преобразует выход Ultralytics (Results/Boxes) в формат numpy-массива, который ожидает ваш трекер (ByteTracker).
        detections_list = self._get_results_dor_tracker(outputs)

        # Если детекций нет, то оправляем пустой массив
        if len(detections_list) == 0:
            detections_list = np.empty((0, 5)) # пустой массив для трекера (формат [x1, y1, x2, y2, conf])
        
        # Обновляем трекер новыми детекциями и получаем список треков (каждый трек - это объект, который трекается во времени с уникальным ID)
        # трекер: связывает объекты между кадрами даёт каждому ID
        track_list = self.tracker.update(torch.tensor(detections_list), xyxy=True)

        # Получение id list (список ID треков для текущего кадра) и сохраняем его в элементе кадра
        frame_element.id_list = [int(t.track_id) for t in track_list] 

        # Получение координат треков после трекинга и сохраняем их в элементе кадра
        frame_element.tracked_xyxy = [list(t.tlbr.astype(int)) for t in track_list]

        # Получение классов объектов после трекинга и сохраняем их в элементе кадра
        frame_element.tracked_cls = [self.classes[int(t.class_name)] for t in track_list]

        # Получение confidence после трекинга и сохраняем их в элементе кадра
        frame_element.tracked_conf = [t.score for t in track_list] 

        # Возвращаем элемент кадра с добавленной информацией о детекции и трекинге
        return frame_element 

    def _get_results_dor_tracker(self, results) -> np.ndarray:
        # Приведение данных в правильную форму для трекера (ByteTracker ожидает массив с колонками [x1, y1, x2, y2, conf])
        detection_list = []

        # каждый result = один объект
        for result in results[0]:
            class_id = result.boxes.cls.cpu().numpy().astype(int)
            # трекаем те же классы что и детектируем
            if class_id[0] in self.classes_to_detect:
                bbox = result.boxes.xyxy.cpu().numpy() # координаты бокса в формате [x1, y1, x2, y2]
                confidence = result.boxes.conf.cpu().numpy() # confidence детекции

                class_id_value = (
                    2 # Будем все трекуемые объекты считать классом car чтобы не было ошибок
                )
                
                # объединяем данные в один список для трекера
                merged_detection = [
                    bbox[0][0],
                    bbox[0][1],
                    bbox[0][2],
                    bbox[0][3],
                    confidence[0],
                    class_id_value,
                ]

                detection_list.append(merged_detection)
                
        return np.array(detection_list)