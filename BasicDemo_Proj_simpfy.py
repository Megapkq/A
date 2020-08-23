# -- coding: utf-8 --
import sys
import _tkinter
import tkinter.messagebox
import tkinter as tk
import sys, os
from tkinter import ttk

sys.path.append("../MvImport")
# sys.path.append(r"E:\\graduated\workspace\7.24\\camera\\MVS\Development\Samples\\Python\\MvImport")
from MvCameraControl_class import *
from CamOperation_class_Proj import *


# 获取选取设备信息的索引，通过[]之间的字符去解析
def TxtWrapBy(start_str, end, all):
    start = all.find(start_str)
    if start >= 0:
        start += len(start_str)
        end = all.find(end, start)
        if end >= 0:
            return all[start:end].strip()


# 将返回的错误码转换为十六进制显示
def ToHexStr(num):
    chaDic = {10: 'a', 11: 'b', 12: 'c', 13: 'd', 14: 'e', 15: 'f'}
    hexStr = ""
    if num < 0:
        num = num + 2 ** 32
    while num >= 16:
        digit = num % 16
        hexStr = chaDic.get(digit, str(digit)) + hexStr
        num //= 16
    hexStr = chaDic.get(num, str(num)) + hexStr
    return hexStr


if __name__ == "__main__":
    global deviceList
    deviceList = MV_CC_DEVICE_INFO_LIST()
    global tlayerType
    tlayerType = MV_GIGE_DEVICE | MV_USB_DEVICE
    global cam
    cam = MvCamera()
    global nSelCamIndex
    nSelCamIndex = 0
    global obj_cam_operation_group
    obj_cam_operation_group = {}


    # 绑定下拉列表至设备信息索引
    def xFunc(event):
        global nSelCamIndex
        nSelCamIndex = TxtWrapBy("[", "]", device_list.get())


    # ch:枚举相机 | en:enum devices
    def enum_devices():
        global deviceList
        deviceList = MV_CC_DEVICE_INFO_LIST()
        tlayerType = MV_GIGE_DEVICE | MV_USB_DEVICE
        ret = MvCamera.MV_CC_EnumDevices(tlayerType, deviceList)
        if ret != 0:
            tkinter.messagebox.showerror('show error', 'enum devices fail! ret = ' + ToHexStr(ret))

        # 显示相机个数
        text_number_of_devices.delete(1.0, tk.END)
        text_number_of_devices.insert(1.0, str(deviceList.nDeviceNum) + 'Cameras')

        if deviceList.nDeviceNum == 0:
            tkinter.messagebox.showinfo('show info', 'find no device!')

        print("Find %d devices!" % deviceList.nDeviceNum)

        devList = []
        for i in range(0, deviceList.nDeviceNum):
            mvcc_dev_info = cast(deviceList.pDeviceInfo[i], POINTER(MV_CC_DEVICE_INFO)).contents
            if mvcc_dev_info.nTLayerType == MV_GIGE_DEVICE:
                print("\ngige device: [%d]" % i)
                strModeName = ""
                for per in mvcc_dev_info.SpecialInfo.stGigEInfo.chModelName:
                    strModeName = strModeName + chr(per)
                print("device model name: %s" % strModeName)

                nip1 = ((mvcc_dev_info.SpecialInfo.stGigEInfo.nCurrentIp & 0xff000000) >> 24)
                nip2 = ((mvcc_dev_info.SpecialInfo.stGigEInfo.nCurrentIp & 0x00ff0000) >> 16)
                nip3 = ((mvcc_dev_info.SpecialInfo.stGigEInfo.nCurrentIp & 0x0000ff00) >> 8)
                nip4 = (mvcc_dev_info.SpecialInfo.stGigEInfo.nCurrentIp & 0x000000ff)
                print("current ip: %d.%d.%d.%d\n" % (nip1, nip2, nip3, nip4))
                devList.append(
                    "Gige[" + str(i) + "]:" + str(nip1) + "." + str(nip2) + "." + str(nip3) + "." + str(nip4))
            elif mvcc_dev_info.nTLayerType == MV_USB_DEVICE:
                print("\nu3v device: [%d]" % i)
                strModeName = ""
                for per in mvcc_dev_info.SpecialInfo.stUsb3VInfo.chModelName:
                    if per == 0:
                        break
                    strModeName = strModeName + chr(per)
                print("device model name: %s" % strModeName)

                strSerialNumber = ""
                for per in mvcc_dev_info.SpecialInfo.stUsb3VInfo.chSerialNumber:
                    if per == 0:
                        break
                    strSerialNumber = strSerialNumber + chr(per)
                print("user serial number: %s" % strSerialNumber)
                devList.append("USB[" + str(i) + "]" + str(strSerialNumber))
        device_list["value"] = devList
        device_list.current(0)


    # ch:打开相机 | en:open device
    def open_device():
        global deviceList
        global nSelCamIndex
        global obj_cam_operation_group

        if False == obj_cam_operation_group.has_key(nSelCamIndex):
            obj_cam_operation_group[nSelCamIndex] =CameraOperation(cam, deviceList, nSelCamIndex)
        if True == obj_cam_operation_group[nSelCamIndex].b_is_run:
            tkinter.messagebox.showinfo('show info', 'Camera is running!')
            return
        ret = obj_cam_operation_group[nSelCamIndex].Open_device()
        if 0 != ret:
            obj_cam_operation_group[nSelCamIndex].b_is_run = False
            tkinter.messagebox.showinfo('show info', 'Camera open error!')
            return
        else:
            model_val.set('continuous')
            obj_cam_operation_group[nSelCamIndex].b_is_run = True
            tkinter.messagebox.showinfo('show info', 'Camera open sucessfully!')
            return


    # ch:开始取流 | en:Start grab image
    def start_grabbing():
        global nSelCamIndex
        global obj_cam_operation_group
        obj_cam_operation_group[nSelCamIndex].Start_grabbing()
        return


    # ch:停止取流 | en:Stop grab image
    def stop_grabbing():
        global nSelCamIndex
        global obj_cam_operation_group
        obj_cam_operation_group[nSelCamIndex].Stop_grabbing()
        return


    # ch:关闭设备 | Close device
    def close_device():
        global nSelCamIndex
        global obj_cam_operation_group
        obj_cam_operation_group[nSelCamIndex].Close_device()
        obj_cam_operation_group[nSelCamIndex].b_is_run = False


    # ch:设置触发模式 | en:set trigger mode
    # def set_triggermode():
    #     global obj_cam_operation
    #     strMode = model_val.get()
    #     obj_cam_operation.Set_trigger_mode(strMode)

    # #ch:设置触发命令 | en:set trigger software
    # def trigger_once():
    #     global triggercheck_val
    #     global obj_cam_operation
    #     nCommand = triggercheck_val.get()
    #     obj_cam_operation.Trigger_once(nCommand)

    # #ch:保存bmp图片 | en:save bmp image
    # def bmp_save():
    #     global obj_cam_operation
    #     obj_cam_operation.b_save_jpg = True

    # #ch:保存jpg图片 | en:save jpg image
    # def jpg_save():
    #     global obj_cam_operation
    #     obj_cam_operation.b_save_jpg = True

    def get_parameter():
        global nSelCamIndex
        global obj_cam_operation_group
        obj_cam_operation_group[nSelCamIndex].Get_parameter()
        text_frame_rate.delete(1.0, tk.END)
        text_frame_rate.insert(1.0, obj_cam_operation_group[nSelCamIndex].frame_rate)
        text_exposure_time.delete(1.0, tk.END)
        text_exposure_time.insert(1.0, obj_cam_operation_group[nSelCamIndex].exposure_time)
        text_gain.delete(1.0, tk.END)
        text_gain.insert(1.0, obj_cam_operation_group[nSelCamIndex].gain)


    def set_parameter():
        global nSelCamIndex
        global obj_cam_operation_group
        obj_cam_operation_group[nSelCamIndex].exposure_time = text_exposure_time.get(1.0, tk.END)
        obj_cam_operation_group[nSelCamIndex].exposure_time = obj_cam_operation_group[
            nSelCamIndex].exposure_time.rstrip("\n")
        obj_cam_operation_group[nSelCamIndex].gain = text_gain.get(1.0, tk.END)
        obj_cam_operation_group[nSelCamIndex].gain = obj_cam_operation_group[nSelCamIndex].gain.rstrip("\n")
        obj_cam_operation_group[nSelCamIndex].frame_rate = text_frame_rate.get(1.0, tk.END)
        obj_cam_operation_group[nSelCamIndex].frame_rate = obj_cam_operation_group[nSelCamIndex].frame_rate.rstrip("\n")
        obj_cam_operation_group[nSelCamIndex].Set_parameter(obj_cam_operation_group[nSelCamIndex].frame_rate,
                                                            obj_cam_operation_group[nSelCamIndex].exposure_time,
                                                            obj_cam_operation_group[nSelCamIndex].gain)


    def get_area_edge():
        global nSelCamIndex
        global obj_cam_operation_group
        # obj_cam_operation.get_area_edge()
        text_set_area_x1.delete(1.0, tk.END)
        text_set_area_x1.insert(1.0, obj_cam_operation_group[nSelCamIndex].x1)
        text_set_area_x2.delete(1.0, tk.END)
        text_set_area_x2.insert(1.0, obj_cam_operation_group[nSelCamIndex].x2)
        text_set_area_y1.delete(1.0, tk.END)
        text_set_area_y1.insert(1.0, obj_cam_operation_group[nSelCamIndex].y1)
        text_set_area_y2.delete(1.0, tk.END)
        text_set_area_y2.insert(1.0, obj_cam_operation_group[nSelCamIndex].y2)

    def set_area_edge():
        global nSelCamIndex
        global obj_cam_operation_group
        x1 = text_set_area_x1.get(1.0, tk.END)
        x1 = x1.rstrip("\n")
        x2 = text_set_area_x2.get(1.0, tk.END)
        x2 = x2.rstrip("\n")
        y1 = text_set_area_y1.get(1.0, tk.END)
        y1 = y1.rstrip("\n")
        y2 = text_set_area_y2.get(1.0, tk.END)
        y2 = y2.rstrip("\n")
        obj_cam_operation_group[nSelCamIndex].Set_area_edge(int(x1), int(x2), int(y1), int(y2))

    def set_timer():
        global nSelCamIndex
        global obj_cam_operation_group
        timer = text_interval.get(1.0, tk.END)
        obj_cam_operation_group[nSelCamIndex].Set_timer(int(timer))
        return

    def start_screenshot():
        global nSelCamIndex
        global obj_cam_operation_group
        if True == obj_cam_operation_group[nSelCamIndex].b_start_grabbing:
            obj_cam_operation_group[nSelCamIndex].Start_Screenshot()
        return

    def stop_screenshot():
        global nSelCamIndex
        global obj_cam_operation_group
        if True == obj_cam_operation_group[nSelCamIndex].Screenshot_running:
            obj_cam_operation_group[nSelCamIndex].Stop_Screenshot()
        return

    def set_timer_all():
        global nSelCamIndex
        global obj_cam_operation_group
        timer = text_interval_all.get(1.0, tk.END)
        for i in obj_cam_operation_group.key():
            obj_cam_operation_group[i].Set_timer(int(timer))
        return

    def start_screenshot_all():
        global nSelCamIndex
        global obj_cam_operation_group
        for i in obj_cam_operation_group.key():
            if True == obj_cam_operation_group[i].b_start_grabbing:
                obj_cam_operation_group[i].Start_Screenshot()
        return

    def stop_screenshot_all():
        global nSelCamIndex
        global obj_cam_operation_group
        for i in obj_cam_operation_group.key():
            if True == obj_cam_operation_group[i].Screenshot_running:
                obj_cam_operation_group[i].Stop_Screenshot()
        return

    # 界面设计代码
    window = tk.Tk()
    window.title('BasicDemo')
    window.geometry('600x600')
    model_val = tk.StringVar()
    global triggercheck_val
    triggercheck_val = tk.IntVar()

    text_number_of_devices = tk.Text(window, width=10, height=1)
    text_number_of_devices.place(x=200, y=20)
    xVariable = tkinter.StringVar()
    device_list = ttk.Combobox(window, textvariable=xVariable, width=20)
    device_list.place(x=20, y=20)
    device_list.bind("<<ComboboxSelected>>", xFunc)

    label_exposure_time = tk.Label(window, text='Exposure Time', width=15, height=1)
    label_exposure_time.place(x=20, y=200)
    text_exposure_time = tk.Text(window, width=15, height=1)
    text_exposure_time.place(x=160, y=200)

    label_gain = tk.Label(window, text='Gain', width=15, height=1)
    label_gain.place(x=20, y=250)
    text_gain = tk.Text(window, width=15, height=1)
    text_gain.place(x=160, y=250)

    label_frame_rate = tk.Label(window, text='Frame Rate', width=15, height=1)
    label_frame_rate.place(x=20, y=300)
    text_frame_rate = tk.Text(window, width=15, height=1)
    text_frame_rate.place(x=160, y=300)

    btn_enum_devices = tk.Button(window, text='Enum Devices', width=35, height=1, command=enum_devices)
    btn_enum_devices.place(x=20, y=50)
    btn_open_device = tk.Button(window, text='Open Device', width=15, height=1, command=open_device)
    btn_open_device.place(x=20, y=100)
    btn_close_device = tk.Button(window, text='Close Device', width=15, height=1, command=close_device)
    btn_close_device.place(x=160, y=100)

    # radio_continuous = tk.Radiobutton(window, text='Continuous',variable=model_val, value='continuous',width=15, height=1,command=set_triggermode)
    # radio_continuous.place(x=20,y=150)
    # radio_trigger = tk.Radiobutton(window, text='Trigger Mode',variable=model_val, value='triggermode',width=15, height=1,command=set_triggermode)
    # radio_trigger.place(x=160,y=150)

    btn_start_grabbing = tk.Button(window, text='Start Grabbing', width=15, height=1, command=start_grabbing)
    btn_start_grabbing.place(x=20, y=150)
    btn_stop_grabbing = tk.Button(window, text='Stop Grabbing', width=15, height=1, command=stop_grabbing)
    btn_stop_grabbing.place(x=160, y=150)

    # checkbtn_trigger_software = tk.Checkbutton(window, text='Tigger by Software', variable=triggercheck_val, onvalue=1, offvalue=0)
    # checkbtn_trigger_software.place(x=20,y=250)
    # btn_trigger_once = tk.Button(window, text='Trigger Once', width=15, height=1, command = trigger_once)
    # btn_trigger_once.place(x=160, y=250)

    # btn_save_bmp = tk.Button(window, text='Save as BMP', width=15, height=1, command = bmp_save )
    # btn_save_bmp.place(x=20, y=300)
    # btn_save_jpg = tk.Button(window, text='Save as JPG', width=15, height=1, command = jpg_save)
    # btn_save_jpg.place(x=160, y=300)

    btn_get_parameter = tk.Button(window, text='Get Parameter', width=15, height=1, command=get_parameter)
    btn_get_parameter.place(x=20, y=350)
    btn_set_parameter = tk.Button(window, text='Set Parameter', width=15, height=1, command=set_parameter)
    btn_set_parameter.place(x=160, y=350)

    text_set_area = tk.Label(window, text='select photo area', width=15, height=1)
    text_set_area.place(x=400, y=20)

    set_area_x1 = tk.Label(window, text='x1', width=2, height=1)
    set_area_x1.place(x=300, y=50)
    text_set_area_x1 = tk.Text(window, width=14, height=1)
    text_set_area_x1.place(x=330, y=50)

    set_area_x2 = tk.Label(window, text='x2', width=2, height=1)
    set_area_x2.place(x=440, y=50)
    text_set_area_x2 = tk.Text(window, width=14, height=1)
    text_set_area_x2.place(x=470, y=50)

    set_area_y1 = tk.Label(window, text='y1', width=2, height=1)
    set_area_y1.place(x=300, y=100)
    text_set_area_y1 = tk.Text(window, width=14, height=1)
    text_set_area_y1.place(x=330, y=100)

    set_area_y2 = tk.Label(window, text='y2', width=2, height=1)
    set_area_y2.place(x=440, y=100)
    text_set_area_y2 = tk.Text(window, width=14, height=1)
    text_set_area_y2.place(x=470, y=100)

    btn_get_area_edge = tk.Button(window, text='Get area edge', width=15, height=1, command=get_area_edge)
    btn_get_area_edge.place(x=320, y=130)
    btn_set_area_edge = tk.Button(window, text='Set area edge', width=15, height=1, command=set_area_edge)
    btn_set_area_edge.place(x=470, y=130)




    text_screenshot = tk.Label(window, text='screenshot', width=15, height=1)
    text_screenshot.place(x=400, y=200)

    btn_interval = tk.Button(window, text='interval', width=15, height=1, command=set_timer)
    btn_interval.place(x=300, y=250)
    text_interval = tk.Text(window, width=15, height=1)
    text_interval.place(x=440, y=250)

    btn_start_screenshot = tk.Button(window, text='Start screenshot', width=15, height=1, command=start_screenshot)
    btn_start_screenshot.place(x=300, y=300)
    btn_stop_screenshot = tk.Button(window, text='Stop screenshot', width=15, height=1, command=stop_screenshot)
    btn_stop_screenshot.place(x=440, y=300)


    text_screenshot_all = tk.Label(window, text='screenshot for all camera', width=20, height=1)
    text_screenshot_all.place(x=200, y=420)

    btn_interval_all = tk.Button(window, text='interval', width=15, height=1, command=set_timer_all)
    btn_interval_all.place(x=150, y=450)
    text_interval_all = tk.Text(window, width=15, height=1)
    text_interval_all.place(x=290, y=450)

    btn_start_screenshot_all = tk.Button(window, text='Start screenshot for all', width=25, height=1,
                                         command=start_screenshot_all)
    btn_start_screenshot_all.place(x=140, y=500)
    btn_stop_screenshot_all = tk.Button(window, text='Stop screenshot for all', width=25, height=1,
                                        command=stop_screenshot_all)
    btn_stop_screenshot_all.place(x=290, y=500)

    window.mainloop()
