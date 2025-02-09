import pymem.process
import psutil
import os
import time
import csv
import pyautogui
from keyboard import is_pressed
from PIL import Image
import win32api
import win32con
import mss  

# Адреса смещений мыши в памяти
XOFFSET_ADDRESS = 0x66AB4288C # Смещение мыши по горизонтали (XOffset)
YOFFSET_ADDRESS = 0x65ED33CC4  # Смещение мыши по вертикали (YOffset)

# Глобальные переменные
data_log = []
frame_count = 0
current_key = -1
output_dir = "D:/minecraft_data"
screenshot_scale = 0.5
mouse_left_pressed = False  
width, height = pyautogui.size()


previous_xoffset, previous_yoffset = 0.0, 0.0

os.makedirs(output_dir, exist_ok=True)

# Функция для записи аннотаций в CSV
def save_data():
    csv_path = os.path.join(output_dir, "annotations.csv")
    file_exists = os.path.isfile(csv_path)
    with open(csv_path, mode='a', newline='') as file:
        writer = csv.writer(file)
        if not file_exists:  # Если файл не существует, записываем заголовок
            writer.writerow(["frame_name", "key_class", "xoffset_delta", "yoffset_delta", "left_click"])
        writer.writerows(data_log)
    print(f"Аннотации успешно сохранены: {csv_path}")
    data_log.clear()  


def get_current_key():
    keys = {"w": 2, "a": 3, "s": 4, "d": 5, "space": 6, "shift": 7} #добавьте свои данные для сбора , мне достаточно этого. "1" оставте под ничего не нажато это важно для обучения модели
    for key, num in keys.items():
        if is_pressed(key):
            return num
    return 1  


def is_left_mouse_pressed():
    return win32api.GetAsyncKeyState(win32con.VK_LBUTTON) < 0


def resize_screenshot(image, scale):
    width, height = image.size
    new_size = (int(width * scale), int(height * scale))
    return image.resize(new_size, Image.Resampling.LANCZOS)

#самое главное , используйте утелиту для нахождения адресса вращения персонажа , я пользуюсь cheate engine , убедитесь что адресс коректен 
def list_java_processes():
    processes = []
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] == 'javaw.exe':
            processes.append(proc.info)
    return processes

def read_float(pm, address):
    try:
        return pm.read_float(address)
    except Exception as e:
        print(f"Ошибка при чтении памяти: {e}")
        return None

def normalize_angle(angle):
    """Приводит угол к диапазону [-180, 180]."""
    while angle > 180:
        angle -= 360
    while angle < -180:
        angle += 360
    return angle

def get_mouse_offsets(pm):
    xoffset = read_float(pm, XOFFSET_ADDRESS)
    yoffset = read_float(pm, YOFFSET_ADDRESS)
    return xoffset, yoffset

# Функция для чтения последнего кадра из CSV - это нужно что бы данные о смещение мыши были актуальны ведь на момент скриншота они устарели на кадр
def get_last_frame_count():
    csv_path = os.path.join(output_dir, "annotations.csv")
    if not os.path.isfile(csv_path):
        return 0  

    with open(csv_path, mode='r') as file:
        reader = csv.reader(file)
        last_row = None
        for row in reader:
            last_row = row

        if last_row:
            # Извлекаем номер последнего кадра
            last_frame_name = last_row[0]
            return int(last_frame_name.split('_')[1].split('.')[0])
        else:
            return 0  


def capture_data(pm):
    global frame_count, data_log, current_key, mouse_left_pressed, previous_xoffset, previous_yoffset

    # Получаем последний сохраненный кадр
    frame_count = get_last_frame_count()
    print(f"Продолжаем запись данных с кадра {frame_count}")

    print("Начинаю сбор данных. Нажмите Esc для остановки.")

    with mss.mss() as sct:
        monitor = sct.monitors[1]  

        while not is_pressed("esc"):
            start_time = time.time() 

            # Создаем скриншот
            screenshot = sct.grab(monitor)
            screenshot_image = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            resized_screenshot = resize_screenshot(screenshot_image, screenshot_scale)


            frame_name = f"frame_{frame_count:04d}.png"
            screenshot_path = os.path.join(output_dir, frame_name)
            resized_screenshot.save(screenshot_path)

            # Собираем данные о смещении мыши
            xoffset, yoffset = get_mouse_offsets(pm)

            # Нормализуем углы
            xoffset = normalize_angle(xoffset)
            yoffset = normalize_angle(yoffset)

 
            xoffset_delta = xoffset - previous_xoffset
            yoffset_delta = yoffset - previous_yoffset

            if xoffset_delta > 180:
                xoffset_delta -= 360
            elif xoffset_delta < -180:
                xoffset_delta += 360


            if yoffset_delta > 180:
                yoffset_delta -= 360
            elif yoffset_delta < -180:
                yoffset_delta += 360


            previous_xoffset, previous_yoffset = xoffset, yoffset

            yoffset_delta = -yoffset_delta  # Инвертируем ось Y из за инверсии движения в майне 


            current_key = get_current_key()
            mouse_left_pressed = is_left_mouse_pressed()

            # Логируем кадр
            data_log.append([frame_name, current_key, xoffset_delta, yoffset_delta, int(mouse_left_pressed)])
            print(f"[{frame_count}] Кадр: {frame_name}, Клавиша: {current_key}, "
                  f"XOffset Delta: {xoffset_delta:.4f}, YOffset Delta: {yoffset_delta:.4f}, ЛКМ: {mouse_left_pressed}")

            frame_count += 1


            time.sleep(0.2) #вполне достаточно 
            

# Подключение к процессу Minecraft
def main():
    java_processes = list_java_processes()
    if not java_processes:
        print("Нет запущенных процессов javaw.exe")
        return

    print("Запущенные процессы javaw.exe:")
    for proc in java_processes:
        print(f"PID: {proc['pid']}, Name: {proc['name']}")

    selected_pid = int(input("Введите PID нужного процесса javaw.exe: ")) #так у java зачастую 2 процесса
    pm = pymem.Pymem(selected_pid)

    time.sleep(2)

    try:
        capture_data(pm)
    except KeyboardInterrupt:
        print("Прерывание программы.")
    finally:
        save_data()

if __name__ == '__main__':
    main()
