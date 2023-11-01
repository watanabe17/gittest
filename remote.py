import sys
print(sys.executable)
import socket
import threading
import time
import cv2
import numpy as np
import PySimpleGUI as sg
from PIL import Image, ImageTk

# キャプチャする映像ストリームの保存先ファイル名
output_file = 'captured_video.mp4'

# キャプチャする映像ストリームの設定
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(output_file, fourcc, 20.0, (640, 480))

DISPLAY_SIZE = (800, 600)
layout = [
    [sg.Image(filename="", key="image", size=DISPLAY_SIZE)],
    [sg.Text("Command:"), sg.Input(), sg.Button("OK")],
    [
        sg.Text(key="sent", font=("monospace", 20)),
        sg.Text(text="-->"),
        sg.Text(key="recv", font=("monospace", 20)),
    ],
    [sg.Text(key="state", font=("monospace", 20))],
    [
        sg.Button("Quit", font=("Arial", 32)),
        sg.Button("Takeoff", font=("Arial", 32)),
        sg.Button("Land", font=("Arial", 32)),
    ],
]
window = sg.Window("My Drone", layout)


class Info:
    def __init__(self):
        self.__state = {}
        self.__is_active = True
        self.__image = None
        self.__command = ""
        self.__sent_command = ""
        self.__result = ""

    def set_states(self, states):
        self.__state = states

    def get_states(self):
        return self.__state

    def get_state(self, name):
        return self.__state.get(name, 0.0)

    def is_active(self):
        return self.__is_active

    def stop(self):
        self.__is_active = False

    def set_image(self, image):
        self.__image = image

    def get_image(self):
        return self.__image

    def entry_command(self, command):
        self.__command = command

    def pick_command(self):
        command = self.__command
        self.__command = ""
        return command

    def set_sent_command(self, command):
        self.__sent_command = command

    def get_sent_command(self):
        return self.__sent_command

    def set_command_result(self, result):
        self.__result = result

    def get_command_result(self):
        return self.__result


info = Info()


def __get_drone_state(data):
    s = data.decode(errors="replace")
    values = s.split(";")
    state = {}
    for v in values:
        kv = v.split(":")
        if len(kv) > 1:
            state[kv[0]] = float(kv[1])
    return state


sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("", 8889))

sock.sendto("command".encode(), ("192.168.10.1", 8889))
sock.recvfrom(1024)
sock.sendto("streamon".encode(), ("192.168.10.1", 8889))
sock.recvfrom(1024)

state_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
state_sock.bind(("", 8890))


def receive_state():
    while info.is_active():
        try:
            data, _ = state_sock.recvfrom(1024)
            info.set_states(__get_drone_state(data))
        except Exception:
            print("\nExit . . .\n")
            break


state_receive_thread = threading.Thread(target=receive_state)
state_receive_thread.start()


def receive_video():
    cap = cv2.VideoCapture("udp://0.0.0.0:11111?overrun_nonfatal=1")
    """"
    #############################################################
    output_folder = "C:/Users/81809/Documents/tello/video" 
    frame_count = 0                                
    #############################################################
    """
    while info.is_active():
        success, image = cap.read()
        if not success:
            continue
        """"
        ###############################################################
        if frame_count % 100 == 0:
            file_name = f"{output_folder}/frame_{frame_count//100:04d}.jpg"
            cv2.imwrite(file_name, image)
        frame_count += 1
        time.sleep(1)
        ###########################################################
"""
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        info.set_image(image)
        out.write(image)

    cap.release()
    out.release()


video_receive_thread = threading.Thread(target=receive_video)
video_receive_thread.start()


def send_command():
    while info.is_active():
        time.sleep(0.1)
        msg = info.pick_command()
        if msg == "":
            continue

        sock.sendto(msg.encode(), ("192.168.10.1", 8889))
        info.set_command_result("")
        info.set_sent_command(msg)
        start = time.time()
        data, _ = sock.recvfrom(1024)
        info.set_command_result(f"{data.decode()} {time.time() - start:.1f}")


command_send_thread = threading.Thread(target=send_command)
command_send_thread.start()

while True:
    msg = ""
    event, values = window.read(timeout=1)
    window["state"].update(f'battery: {info.get_state("bat"):.1f}%')
    tello_address = ('192.168.10.1', 8889)                            ##################


    image = info.get_image()
    if image is None:
        continue

    h, w, _ = np.shape(image)
    r = DISPLAY_SIZE[0] / w
    image = cv2.resize(image, (int(w * r), int(h * r)))
    photoImage = ImageTk.PhotoImage(Image.fromarray(image))
    window["image"].update(data=photoImage)

    if event == sg.WINDOW_CLOSED or event == "Quit":
        break
    if event == "OK":
        msg = values[0]
    if event == "Takeoff":
        msg = "takeoff"
    if event == "Land":
        msg = "land"

    if msg != "":
        info.entry_command(msg)

    ############################
    if event == "Takeoff":
    # 離陸
        sock.sendto("takeoff".encode('utf-8'), tello_address)
        time.sleep(5)
    elif event == "Land":
    # 着陸
        sock.sendto("land".encode('utf-8'), tello_address)
    elif event == "CustomCommandButton":  # ボタンのラベルを変更して、カスタムコマンドを実行するボタンを作成することもできます
    # カスタムコマンドを実行
        custom_command = "your_custom_command_here"
        sock.sendto(custom_command.encode('utf-8'), tello_address)
        time.sleep(5)
    ###########################


    window["sent"].update(info.get_sent_command())
    window["recv"].update(info.get_command_result())



info.stop()
window.close()