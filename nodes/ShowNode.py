import random # для слуйного выбора цвета
import cv2 
import numpy as np 

from utils_local.utils import profile_time, FPS_Counter 
from elements.VideoEndBreakElement import VideoEndBreakElement 
from elements.FrameElement import FrameElement 


class ShowNode:
    """Модуль для отображения видео с наложенными детекциями и треками"""

    def __init__(self, config) -> None:
        data_colors = config["general"]["colors_of_roads"] 
        self.colors_roads = {key: tuple(value) for key, value in data_colors.items()} 
        self.buffer_analytics_sec = (
            config["general"]["buffer_analytics"] * 60 + 
            config["general"]["min_time_life_track"]
        )
        config_show_node = config["show_node"]
        self.scale = config_show_node["scale"]
        self.fps_counter_N_frames_stat = config_show_node["fps_counter_N_frames_stat"]
        self.default_fps_counter = FPS_Counter(self.fps_counter_N_frames_stat) 
        self.draw_fps_info = config_show_node["draw_fps_info"]
        self.show_roi = config_show_node["show_roi"]
        self.overlay_transparent_mask = config_show_node["overlay_transparent_mask"]
        self.imshow = config_show_node["imshow"] 
        self.show_only_yolo_detections = config_show_node["show_only_yolo_detections"]
        self.show_track_id_different_colors = config_show_node["show_track_id_different_colors"]
        self.show_info_statistics = config_show_node["show_info_statistics"]

        self.show_number_of_road = True 

        self.fontFace = 1 # шрифт для отображения текста (1 - простой, 2 - сложный, 3 - рукописный, 4 - монорепа)
        self.fontScale = 2.0 # размер шрифта для отображения текста
        self.thickness = 2 # толщина линий и текста для отображения на видео

        # parameters for polygons and bboxes
        self.thickness_lines = 3 

        # parameters for display statistics 
        self.width_info = 600

    @profile_time 
    def process(self, frame_element: FrameElement, fps_counter=None) -> FrameElement:
        # Выйти из обработки если это пришел VideoEndBreakElement а не FrameElement
        if isinstance(frame_element, VideoEndBreakElement):
            return frame_element 
        assert isinstance(
            frame_element, FrameElement
        ), f"ShowNode | Incorrect input element format {type(frame_element)}"

        frame_result = frame_element.frame.copy()

        # imagine only detections result 
        if self.show_only_yolo_detections:
            # zip — это функция, которая объединяет несколько списков в один. Она создаёт итератор, который возвращает кортежи, где i-й кортеж содержит i-й элемент из каждого из входных списков. В нашем случае мы объединяем список координат боксов (frame_element.detected_xyxy) и список классов (frame_element.detected_cls) в один итератор, который возвращает пары (box, class_name) для каждой детекции.
            for box, class_name in zip(frame_element.detected_xyxy, frame_element.detected_cls): 
                x1, y1, x2, y2 = box 
                # cv2.rectangle — функция из OpenCV для рисования прямоугольника на изображении. Она принимает следующие аргументы:
                # - frame_result: изображение, на котором нужно нарисовать прямоугольник
                # - (x1, y1): координаты верхнего левого угла прямоугольника
                # - (x2, y2): координаты нижнего правого угла прямоугольника
                # - (0, 0, 0): цвет прямоугольника в формате BGR (в данном случае черный)           
                # - thickness: толщина линий прямоугольника (в данном случае 2 пикселя)
                cv2.rectangle(frame_result, (x1, y1), (x2, y2), (0, 0, 0), 2) 
                cv2.putText(
                    frame_result, 
                    class_name, 
                    (x1, y1 - 10),
                    fontFace=self.fontFace,
                    fontScale=self.fontScale,
                    thickness=self.thickness,
                    color=(0, 0, 255)
                )
        else:
            # imagine trecking result 
            for box, class_name, id in zip(
                frame_element.tracked_xyxy, frame_element.tracked_cls, frame_element.id_list
            ):
                x1, y1, x2, y2 = box
                # Отрисовка прямоугольника 
                if self.show_track_id_different_colors:
                    # Отображаем кадый трек своим цветом 
                    random.seed(int(id)) # устанавливаем seed для генератора случайных чисел на основе ID трека, чтобы цвет был постоянным для каждого ID
                    color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                else:
                    # Отображаем каждый трек согласно цвету пересечения с дорогой 
                    try:
                        start_road = frame_element.buffer_tracks[int(id)].start_road 
                        if start_road is not None:
                            color = self.colors_roads[int(start_road)] # получаем цвет дороги, с которой начался трек, из словаря colors_roads
                        else: # если трек не пересекается ни с одной дорогой, то отображаем его черным цветом
                            color = (0, 0, 0)
                    except KeyError:
                        color = (0, 0, 0)

                cv2.rectangle(frame_result, (x1, y1), (x2, y2), color, self.thickness_lines)
                # Добавление подписи с именем класса
                cv2.putText(
                    frame_result,
                    f"{id}",
                    (x1, y1 - 10),
                    fontFace=self.fontFace,
                    fontScale=self.fontScale,
                    thickness=self.thickness,
                    color=(0, 0, 255),
                )

        # Построение полигонов дорог 
        if self.show_roi:
            for road_id, points in frame_element.roads_info.items():
                color = self.colors_roads[int(road_id)]
                points = np.array(points, np.int32)
                points = points.reshape((-1, 1, 2)) # reshape -1 NumPy сам вычислит количество точек. Было 6 чисел: NumPy понимает: по 2 числа на точку, значит 3 точки
                # 2 - Последняя размерность: [x, y] Каждая точка состоит из двух чисел.
                # 1 - Предпоследняя размерность: 1 - это формат, который требует функция polylines для рисования многоугольника. Она ожидает массив точек в виде [[x1, y1]], [[x2, y2]], ..., где каждая точка обернута в дополнительный массив.
                # polylines — функция из OpenCV для рисования многоугольников на изображении. Она принимает следующие аргументы:
                # рисует линии по набору точек, то есть контур полигона.
                cv2.polylines(
                    frame_result,
                    [points],
                    isClosed=True, # True означает, что последний пункт соединяется с первым, замыкая контур полигона.
                    color=color,
                    thickness=self.thickness_lines,
                )

                if self.overlay_transparent_mask:
                    frame_result = self._overlay_transparent_mask(
                        frame_result, points, mask_color=color, alpha=0.3
                    )
                
                # Отображение номера дороги в залитой окружности
                if self.show_number_of_road:
                    moments = cv2.moments(points) # Найти центр области  OpenCV вычисляет геометрические характеристики полигона.
                    # Например: площадь, центр массы, распределение точек
                    # m00 - это площадь полигона, m10 и m01 - это моменты, которые используются для вычисления координат центра масс (cx, cy) полигона. Если площадь (m00) не равна нулю, то можно вычислить координаты центра масс следующим образом:
                    # Если вырезать фигуру из картона и положить её на палец, то точка, где она будет балансировать — это и есть центр массы.
                    if moments["m00"] != 0:
                        cx = int(moments["m10"] / moments["m00"])
                        cy = int(moments["m01"] / moments["m00"])

                        # OpenCV вычисляет размер текста в пикселях. Функция cv2.getTextSize принимает текст, шрифт, размер и толщину, и возвращает размер текста в виде (ширина, высота) и базовую линию. В нашем случае мы используем эту функцию для вычисления размера текста, который будет отображать номер дороги (road_id). Это нужно для того, чтобы правильно разместить текст внутри окружности и убедиться, что он не выходит за её пределы.
                        (label_width, label_height), _ = cv2.getTextSize(
                            str(road_id),
                            fontFace=self.fontFace,
                            fontScale=self.fontScale * 1.3,
                            thickness=self.thickness,
                        ) 
                        # определение радиуса круга
                        circle_radius = max(label_width, label_height) // 2 
                        # рисуем окружность (центр в точке (cx, cy), радиус circle_radius + 6 для отступа, цвет (200, 200, 200) - светло-серый, толщина -1 для заливки - Закрашенный круг.)
                        cv2.circle(
                            frame_result,
                            (cx, cy),
                            circle_radius + 6,
                            (200, 200, 200),
                            -1,
                        )
                        # нанесение подписи road_id в центре области 
                        cv2.putText(
                            frame_result,
                            str(road_id),
                            (cx + 2 - label_width // 2, cy + 2 + label_height // 2),
                            fontFace=self.fontFace,
                            fontScale=self.fontScale * 1.3,
                            thickness=self.thickness,
                            color=(0, 0, 0),
                        ) 
        
        # count and show FPS 
        if self.draw_fps_info:
            fps_counter = fps_counter if fps_counter is not None else self.default_fps_counter 
            fps_real = fps_counter.calc_FPS()

            text = f"FPS: {fps_real:.1f}"
            (label_width, label_height), _ = cv2.getTextSize(
                text, 
                fontFace=self.fontFace,
                fontScale=self.fontScale,
                thickness=self.thickness,
            )
            cv2.rectangle(
                frame_result, (0, 0), (10 + label_width, 35 + label_height), (0, 0, 0), -1 # -1 для заливки прямоугольника
            )
            cv2.putText(
                img=frame_result,
                text=text,
                org=(10, 40), # координаты (x, y) для нижнего левого угла текста. В данном случае текст будет располагаться с отступом 10 пикселей от левого края и 40 пикселей от верхнего края изображения.
                fontFace=self.fontFace,
                fontScale=self.fontScale,
                thickness=self.thickness,
                color=(255, 255, 255),
            )

        # обработка отдельного окна с выводом статистики 
        if self.show_info_statistics:
            black_image = np.zeros((frame_result.shape[0], self.width_info, 3), dtype=np.uint8)
            data_info = frame_element.info 

            # текст для количества машин 
            text_cars = f"Cars amount: {data_info['cars_amount']}"
            # начальная координата для текста 
            y = 55 
            cv2.putText(
                img=black_image,
                text=text_cars,
                org=(10, y),
                fontFace=self.fontFace,
                fontScale=self.fontScale * 1.5,
                thickness=self.thickness,
                color=(255, 255, 255),
            )
            # getTextSize возвращает размер текста в пикселях, который мы используем для определения отступа между строками. Мы умножаем fontScale на 1.5, чтобы увеличить размер текста для лучшей читаемости. Затем мы добавляем к координате  y высоту текста (label_height) и дополнительный отступ (25 пикселей) для следующей строки статистики, которая будет отображать активность по дорогам. Таким образом, каждая строка статистики будет располагаться ниже предыдущей с достаточным отступом для удобства чтения.
            y += (
                cv2.getTextSize(text_cars, self.fontFace, self.fontScale * 1.5, self.thickness)[0][1] + 25
            )
            text_info = "Traffic congestion"
            cv2.putText(
                img=black_image,
                text=text_info,
                org=(20, y),
                fontFace=self.fontFace,
                fontScale=self.fontScale * 1.5,
                thickness=self.thickness,
                color=(255, 255, 255),
            )
            y += (
                cv2.getTextSize(text_cars, self.fontFace, self.fontScale * 1.5, self.thickness)[0][1] + 25
            )

            if frame_element.timestamp >= self.buffer_analytics_sec:
                for key, value in data_info["roads_activity"].items():
                    # выводим статистику по каждой дороге, но только если видео уже проигралось достаточно долго, чтобы накопить данные для расчета активности дорог (buffer_analytics_sec)
                    text_road = f"road {key}: {value:.1f} cars/min"
                    cv2.putText(
                        img=black_image,
                        text=text_road,
                        org=(20, y), 
                        fontFace=self.fontFace,
                        fontScale=self.fontScale * 1.5,
                        thickness=self.thickness,
                        color=(255, 255, 255),)
                    y += (
                        cv2.getTextSize(text_cars, self.fontFace, self.fontScale * 1.5, self.thickness)[0][1] + 25
                    )
            else:
                text_to_show = (
                    f"wait {round(self.buffer_analytics_sec - frame_element.timestamp)} sec"
                )
                cv2.putText(
                    img=black_image,
                    text=text_to_show,
                    org=(20, y),
                    fontFace=self.fontFace,
                    fontScale=self.fontScale * 1.5,
                    thickness=self.thickness,
                    color=(255, 255, 255),
                )
            frame_result = np.hstack((frame_result, black_image)) # объединяем по горизонтали (hstack) основное видео с отдельным окном статистики (black_image)
                    
        frame_element.frame_result = frame_result
        frame_show = cv2.resize(frame_result.copy(), (-1, -1), fx=self.scale, fy=self.scale)

        if self.imshow:
            cv2.imshow(frame_element.source, frame_show)
            cv2.waitKey(1)
        
        return frame_element 

    def _overlay_transparent_mask(self, img, points, mask_color=(0, 255, 255), alpha=0.3):
        binary_mask = np.zeros((img.shape[0], img.shape[1]), dtype=np.uint8)
        # cv2.fillPoly — функция из OpenCV для заполнения многоугольника на изображении. Она принимает следующие аргументы:
        # - binary_mask: изображение, на котором нужно заполнить многоугольник (в данном случае это черная маска, которая будет использоваться для создания прозрачного наложения)
        # - pts=[points]: список точек, которые определяют вершины многоугольника. В нашем случае points - это массив координат, который описывает контур дороги. Мы оборачиваем его в список, потому что функция fillPoly ожидает список многоугольников, даже если у нас только один многоугольник.
        # - color=1: цвет, которым нужно заполнить многоугольник. Поскольку binary_mask - это одноканальное изображение (черно-белая маска), мы используем значение 1 для заполнения многоугольника, что означает, что пиксели внутри многоугольника будут иметь значение 1, а все остальные пиксели останутся 0.
        binary_mask = cv2.fillPoly(binary_mask, pts=[points], color=1)
        # Создаем цветную маску, умножая бинарную маску на заданный цвет. Это позволяет нам получить цветное наложение для области дороги. Мы добавляем новую ось к бинарной маске с помощью np.newaxis, чтобы она имела форму (H, W, 1), что позволяет нам умножать ее на цвет (кортеж из трех значений для BGR) и получать цветную маску в формате (H, W, 3). Затем мы приводим результат к типу uint8, чтобы он был совместим с изображением.
        colored_mask = (binary_mask[:, :, np.newaxis] * mask_color).astype(np.uint8) 
        # cv2.addWeighted — функция из OpenCV для наложения одного изображения на другое с заданной прозрачностью. Она принимает следующие аргументы:
        # - img: базовое изображение, на которое будет наложена маска (в данном случае это исходное видео)
        # - 1: вес базового изображения (в данном случае мы сохраняем его без изменений, поэтому используем вес 1)
        # - colored_mask: изображение маски, которое будет наложено на базовое изображение (в данном случае это цветная маска, которая выделяет область дороги)
        # - alpha: коэффициент прозрачности для наложенной маски (в данном случае 0.3 означает, что маска будет полупрозрачной, позволяя видеть видео под ней)
        # - 0: гамма-коррекция (в данном случае мы не используем её, поэтому устанавливаем значение 0)
        return cv2.addWeighted(img, 1, colored_mask, alpha, 0)

                


 

                            






