import pymem
import pymem.process
import psutil
import time

# Адреса pitch и yaw в памяти -155 28
PITCH_ADDRESS = 0x66AB4288C
YAW_ADDRESS = 0x65ED33CC4

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

def main():
    java_processes = list_java_processes()
    if not java_processes:
        print("Нет запущенных процессов javaw.exe")
        return

    print("Запущенные процессы javaw.exe:")
    for proc in java_processes:
        print(f"PID: {proc['pid']}, Name: {proc['name']}")

    selected_pid = int(input("Введите PID нужного процесса javaw.exe: "))
    
    pm = pymem.Pymem(selected_pid)

    while True:
        pitch = read_float(pm, PITCH_ADDRESS)
        yaw = read_float(pm, YAW_ADDRESS)

        if pitch is not None and yaw is not None:
            print(f'Pitch: {pitch}, Yaw: {yaw}')  # Вывод значений pitch и yaw

        time.sleep(0.01)  # Задержка 100 мс

if __name__ == '__main__':
    main()
