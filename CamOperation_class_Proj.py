# -- coding: utf-8 --
import sys
import threading
import msvcrt
import _tkinter
import tkinter.messagebox
import tkinter as tk
import numpy as np
import cv2
import time
import sys, os
import datetime
import inspect
import ctypes
import random
from ctypes import *
from tkinter import ttk

sys.path.append("../MvImport")
# sys.path.append(r"E:\\graduated\workspace\7.24\\camera\\MVS\Development\Samples\\Python\\MvImport")
from MvCameraControl_class import *


def Async_raise(tid, exctype):
    tid = ctypes.c_long(tid)
    if not inspect.isclass(exctype):
        exctype = type(exctype)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
    if res == 0:
        raise ValueError("invalid thread id")
    elif res != 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
        raise SystemError("PyThreadState_SetAsyncExc failed")


def Stop_thread(thread):
    Async_raise(thread.ident, SystemExit)


class CameraOperation():

    def __init__(self, obj_cam, st_device_list, n_connect_num=0, b_open_device=False, b_start_grabbing=False,
                 h_thread_handle=None, b_thread_closed=False, st_frame_info=None, buf_cache=None, b_is_run=False,
                 b_exit=False, b_save_bmp=False, b_save_jpg=False, buf_save_image=None, n_save_image_size=0,
                 n_payload_size=0, n_win_gui_id=0, frame_rate=0, exposure_time=0, gain=0):

        self.obj_cam = obj_cam
        self.st_device_list = st_device_list
        self.n_connect_num = n_connect_num
        self.b_open_device = b_open_device
        self.b_start_grabbing = b_start_grabbing
        self.b_thread_closed = b_thread_closed
        self.st_frame_info = st_frame_info
        self.buf_cache = buf_cache
        self.b_is_run = b_is_run
        self.b_exit = b_exit
        self.b_save_bmp = b_save_bmp
        self.b_save_jpg = b_save_jpg
        self.n_payload_size = n_payload_size
        self.buf_save_image = buf_save_image
        self.h_thread_handle = h_thread_handle
        self.n_win_gui_id = n_win_gui_id
        self.n_save_image_size = n_save_image_size
        self.b_thread_closed
        self.frame_rate = frame_rate
        self.exposure_time = exposure_time
        self.gain = gain
        self.x1 = 0
        self.x2 = 0
        self.y1 = 0
        self.y2 = 0
        self.timer = -1
        self.Screenshot_flag = False
        self.Screenshot_running = False
        self.Screenshot_thread_handle = None
        self.Screenshot_thread_exit = False

    def To_hex_str(self, num):
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

    def Open_device(self):
        if False == self.b_open_device:
            # ch:选择设备并创建句柄 | en:Select device and create handle
            nConnectionNum = int(self.n_connect_num)
            stDeviceList = cast(self.st_device_list.pDeviceInfo[int(nConnectionNum)],
                                POINTER(MV_CC_DEVICE_INFO)).contents
            self.obj_cam = MvCamera()
            ret = self.obj_cam.MV_CC_CreateHandle(stDeviceList)
            if ret != 0:
                self.obj_cam.MV_CC_DestroyHandle()
                tkinter.messagebox.showerror('show error', 'create handle fail! ret = ' + self.To_hex_str(ret))
                return ret

            ret = self.obj_cam.MV_CC_OpenDevice(MV_ACCESS_Exclusive, 0)
            if ret != 0:
                tkinter.messagebox.showerror('show error', 'open device fail! ret = ' + self.To_hex_str(ret))
                return ret
            print("open device successfully!")
            self.b_open_device = True
            self.b_thread_closed = False

            # ch:探测网络最佳包大小(只对GigE相机有效) | en:Detection network optimal package size(It only works for the GigE camera)
            if stDeviceList.nTLayerType == MV_GIGE_DEVICE:
                nPacketSize = self.obj_cam.MV_CC_GetOptimalPacketSize()
                if int(nPacketSize) > 0:
                    ret = self.obj_cam.MV_CC_SetIntValue("GevSCPSPacketSize", nPacketSize)
                    if ret != 0:
                        print("warning: set packet size fail! ret[0x%x]" % ret)
                else:
                    print("warning: set packet size fail! ret[0x%x]" % nPacketSize)

            stBool = c_bool(False)
            ret = self.obj_cam.MV_CC_GetBoolValue("AcquisitionFrameRateEnable", byref(stBool))
            if ret != 0:
                print("get acquisition frame rate enable fail! ret[0x%x]" % ret)

            stParam = MVCC_INTVALUE()
            memset(byref(stParam), 0, sizeof(MVCC_INTVALUE))

            ret = self.obj_cam.MV_CC_GetIntValue("PayloadSize", stParam)
            if ret != 0:
                print("get payload size fail! ret[0x%x]" % ret)
            self.n_payload_size = stParam.nCurValue
            if None == self.buf_cache:
                self.buf_cache = (c_ubyte * self.n_payload_size)()

            # ch:设置触发模式为off | en:Set trigger mode as off
            ret = self.obj_cam.MV_CC_SetEnumValue("TriggerMode", MV_TRIGGER_MODE_OFF)
            if ret != 0:
                print("set trigger mode fail! ret[0x%x]" % ret)
            return 0

    def Start_grabbing(self):
        if False == self.b_start_grabbing and True == self.b_open_device:
            self.b_exit = False
            ret = self.obj_cam.MV_CC_StartGrabbing()
            if ret != 0:
                tkinter.messagebox.showerror('show error', 'start grabbing fail! ret = ' + self.To_hex_str(ret))
                return
            self.b_start_grabbing = True
            print("start grabbing successfully!")
            try:
                self.n_win_gui_id = random.randint(1, 10000)
                self.h_thread_handle = threading.Thread(target=CameraOperation.Work_thread, args=(self,))
                self.h_thread_handle.start()
                self.b_thread_closed = True
            except:
                tkinter.messagebox.showerror('show error', 'error: unable to start thread')
                False == self.b_start_grabbing

    def Stop_grabbing(self):
        if True == self.b_start_grabbing and self.b_open_device == True:
            # 退出线程
            if True == self.b_thread_closed:
                Stop_thread(self.h_thread_handle)
                self.b_thread_closed = False
            ret = self.obj_cam.MV_CC_StopGrabbing()
            if ret != 0:
                tkinter.messagebox.showerror('show error', 'stop grabbing fail! ret = ' + self.To_hex_str(ret))
                return
            print("stop grabbing successfully!")
            self.b_start_grabbing = False
            self.b_exit = True

    def Close_device(self):
        if True == self.b_open_device:
            # 退出线程
            if True == self.b_thread_closed:
                Stop_thread(self.h_thread_handle)
                self.b_thread_closed = False
            ret = self.obj_cam.MV_CC_CloseDevice()
            if ret != 0:
                tkinter.messagebox.showerror('show error', 'close deivce fail! ret = ' + self.To_hex_str(ret))
                return

        # ch:销毁句柄 | Destroy handle
        self.obj_cam.MV_CC_DestroyHandle()
        self.b_open_device = False
        self.b_start_grabbing = False
        self.b_exit = True
        print("close device successfully!")

    def Set_trigger_mode(self, strMode):
        if True == self.b_open_device:
            if "continuous" == strMode:
                ret = self.obj_cam.MV_CC_SetEnumValue("TriggerMode", 0)
                if ret != 0:
                    tkinter.messagebox.showerror('show error', 'set triggermode fail! ret = ' + self.To_hex_str(ret))
            if "triggermode" == strMode:
                ret = self.obj_cam.MV_CC_SetEnumValue("TriggerMode", 1)
                if ret != 0:
                    tkinter.messagebox.showerror('show error', 'set triggermode fail! ret = ' + self.To_hex_str(ret))
                ret = self.obj_cam.MV_CC_SetEnumValue("TriggerSource", 7)
                if ret != 0:
                    tkinter.messagebox.showerror('show error', 'set triggersource fail! ret = ' + self.To_hex_str(ret))

    def Trigger_once(self, nCommand):
        if True == self.b_open_device:
            if 1 == nCommand:
                ret = self.obj_cam.MV_CC_SetCommandValue("TriggerSoftware")
                if ret != 0:
                    tkinter.messagebox.showerror('show error',
                                                 'set triggersoftware fail! ret = ' + self.To_hex_str(ret))

    def Get_parameter(self):
        if True == self.b_open_device:
            stFloatParam_FrameRate = MVCC_FLOATVALUE()
            memset(byref(stFloatParam_FrameRate), 0, sizeof(MVCC_FLOATVALUE))
            stFloatParam_exposureTime = MVCC_FLOATVALUE()
            memset(byref(stFloatParam_exposureTime), 0, sizeof(MVCC_FLOATVALUE))
            stFloatParam_gain = MVCC_FLOATVALUE()
            memset(byref(stFloatParam_gain), 0, sizeof(MVCC_FLOATVALUE))
            ret = self.obj_cam.MV_CC_GetFloatValue("AcquisitionFrameRate", stFloatParam_FrameRate)
            if ret != 0:
                tkinter.messagebox.showerror('show error',
                                             'get acquistion frame rate fail! ret = ' + self.To_hex_str(ret))
            self.frame_rate = stFloatParam_FrameRate.fCurValue
            ret = self.obj_cam.MV_CC_GetFloatValue("ExposureTime", stFloatParam_exposureTime)
            if ret != 0:
                tkinter.messagebox.showerror('show error', 'get exposure time fail! ret = ' + self.To_hex_str(ret))
            self.exposure_time = stFloatParam_exposureTime.fCurValue
            ret = self.obj_cam.MV_CC_GetFloatValue("Gain", stFloatParam_gain)
            if ret != 0:
                tkinter.messagebox.showerror('show error', 'get gain fail! ret = ' + self.To_hex_str(ret))
            self.gain = stFloatParam_gain.fCurValue
            tkinter.messagebox.showinfo('show info', 'get parameter success!')

    def Set_parameter(self, frameRate, exposureTime, gain):
        if '' == frameRate or '' == exposureTime or '' == gain:
            tkinter.messagebox.showinfo('show info', 'please type in the text box !')
            return
        if True == self.b_open_device:
            ret = self.obj_cam.MV_CC_SetFloatValue("ExposureTime", float(exposureTime))
            if ret != 0:
                tkinter.messagebox.showerror('show error', 'set exposure time fail! ret = ' + self.To_hex_str(ret))

            ret = self.obj_cam.MV_CC_SetFloatValue("Gain", float(gain))
            if ret != 0:
                tkinter.messagebox.showerror('show error', 'set gain fail! ret = ' + self.To_hex_str(ret))

            ret = self.obj_cam.MV_CC_SetFloatValue("AcquisitionFrameRate", float(frameRate))
            if ret != 0:
                tkinter.messagebox.showerror('show error',
                                             'set acquistion frame rate fail! ret = ' + self.To_hex_str(ret))

            tkinter.messagebox.showinfo('show info', 'set parameter success!')

    def Set_timer(self, timer):
        if timer <= 0:
            tkinter.messagebox.showerror('unreasonable timer')
        else:
            self.timer = timer
        return

    def Set_area_edge(self, x1, x2, y1, y2):
        if self.Is_area():
            self.x1 = x1
            self.x2 = x2
            self.y1 = y1
            self.y2 = y2
        else:
            tkinter.messagebox.showerror('unreasonable screenshot area')
        return

    def Is_area(self):
        if self.x1 != self.x2 and self.y1 != self.y2:
            return True
        else:
            return False

    def resetpoint(self):
        x = self.x1 + self.x2
        y = self.y1 + self.y2
        self.x1 = min(self.x1, self.x2)
        self.x2 = x - self.x1
        self.y1 = min(self.y1, self.y2)
        self.y2 = y - self.y1

    def Work_thread(self):
        # ch:创建显示的窗口 | en:Create the window for display
        cv2.namedWindow(str(self.n_win_gui_id), 0)
        cv2.resizeWindow(str(self.n_win_gui_id), 500, 500)
        cv2.setMouseCallback(str(self.n_win_gui_id), self.on_mouse)
        stFrameInfo = MV_FRAME_OUT_INFO_EX()
        img_buff = None

        while True:
            ret = self.obj_cam.MV_CC_GetOneFrameTimeout(byref(self.buf_cache), self.n_payload_size, stFrameInfo, 1000)
            if ret == 0:
                # 获取到图像的时间开始节点获取到图像的时间开始节点
                self.st_frame_info = stFrameInfo
                print("get one frame: Width[%d], Height[%d], nFrameNum[%d]" % (
                    self.st_frame_info.nWidth, self.st_frame_info.nHeight, self.st_frame_info.nFrameNum))
                self.n_save_image_size = self.st_frame_info.nWidth * self.st_frame_info.nHeight * 3 + 2048
                if img_buff is None:
                    img_buff = (c_ubyte * self.n_save_image_size)()

                if True == self.b_save_jpg:
                    self.Save_jpg()  # ch:保存Jpg图片 | en:Save Jpg
                if self.buf_save_image is None:
                    self.buf_save_image = (c_ubyte * self.n_save_image_size)()

                stParam = MV_SAVE_IMAGE_PARAM_EX()
                stParam.enImageType = MV_Image_Bmp;  # ch:需要保存的图像类型 | en:Image format to save
                stParam.enPixelType = self.st_frame_info.enPixelType  # ch:相机对应的像素格式 | en:Camera pixel type
                stParam.nWidth = self.st_frame_info.nWidth  # ch:相机对应的宽 | en:Width
                stParam.nHeight = self.st_frame_info.nHeight  # ch:相机对应的高 | en:Height
                stParam.nDataLen = self.st_frame_info.nFrameLen
                stParam.pData = cast(self.buf_cache, POINTER(c_ubyte))
                stParam.pImageBuffer = cast(byref(self.buf_save_image), POINTER(c_ubyte))
                stParam.nBufferSize = self.n_save_image_size  # ch:存储节点的大小 | en:Buffer node size
                stParam.nJpgQuality = 80;  # ch:jpg编码，仅在保存Jpg图像时有效。保存BMP时SDK内忽略该参数
                if True == self.b_save_bmp:
                    self.Save_Bmp()  # ch:保存Bmp图片 | en:Save Bmp
            else:
                continue

            # 转换像素结构体赋值
            stConvertParam = MV_CC_PIXEL_CONVERT_PARAM()
            memset(byref(stConvertParam), 0, sizeof(stConvertParam))
            stConvertParam.nWidth = self.st_frame_info.nWidth
            stConvertParam.nHeight = self.st_frame_info.nHeight
            stConvertParam.pSrcData = self.buf_cache
            stConvertParam.nSrcDataLen = self.st_frame_info.nFrameLen
            stConvertParam.enSrcPixelType = self.st_frame_info.enPixelType

            # Mono8直接显示
            if PixelType_Gvsp_Mono8 == self.st_frame_info.enPixelType:
                numArray = CameraOperation.Mono_numpy(self, self.buf_cache, self.st_frame_info.nWidth,
                                                      self.st_frame_info.nHeight)

            # RGB直接显示
            elif PixelType_Gvsp_RGB8_Packed == self.st_frame_info.enPixelType:
                numArray = CameraOperation.Color_numpy(self, self.buf_cache, self.st_frame_info.nWidth,
                                                       self.st_frame_info.nHeight)

            # 如果是黑白且非Mono8则转为Mono8
            elif True == self.Is_mono_data(self.st_frame_info.enPixelType):
                nConvertSize = self.st_frame_info.nWidth * self.st_frame_info.nHeight
                stConvertParam.enDstPixelType = PixelType_Gvsp_Mono8
                stConvertParam.pDstBuffer = (c_ubyte * nConvertSize)()
                stConvertParam.nDstBufferSize = nConvertSize
                ret = self.obj_cam.MV_CC_ConvertPixelType(stConvertParam)
                if ret != 0:
                    tkinter.messagebox.showerror('show error', 'convert pixel fail! ret = ' + self.To_hex_str(ret))
                    continue
                cdll.msvcrt.memcpy(byref(img_buff), stConvertParam.pDstBuffer, nConvertSize)
                numArray = CameraOperation.Mono_numpy(self, img_buff, self.st_frame_info.nWidth,
                                                      self.st_frame_info.nHeight)

            # 如果是彩色且非RGB则转为RGB后显示
            elif True == self.Is_color_data(self.st_frame_info.enPixelType):
                nConvertSize = self.st_frame_info.nWidth * self.st_frame_info.nHeight * 3
                stConvertParam.enDstPixelType = PixelType_Gvsp_RGB8_Packed
                stConvertParam.pDstBuffer = (c_ubyte * nConvertSize)()
                stConvertParam.nDstBufferSize = nConvertSize
                ret = self.obj_cam.MV_CC_ConvertPixelType(stConvertParam)
                if ret != 0:
                    tkinter.messagebox.showerror('show error', 'convert pixel fail! ret = ' + self.To_hex_str(ret))
                    continue
                cdll.msvcrt.memcpy(byref(img_buff), stConvertParam.pDstBuffer, nConvertSize)
                numArray = CameraOperation.Color_numpy(self, img_buff, self.st_frame_info.nWidth,
                                                       self.st_frame_info.nHeight)

            cv2.resizeWindow(str(self.n_win_gui_id), 500, 500)
            # cv2.rectangle(numArray, (100,100), (200,200), (0, 0, 255), thickness=10)
            if self.Is_area():
                cv2.rectangle(numArray, (self.x1, self.y1), (self.x2, self.y2), (0, 0, 255), thickness=10)
            if self.Screenshot_flag == True:
                self.Screenshot_flag = False
                if self.Is_area():
                    self.resetpoint()
                    img = numArray[self.y1:self.y2, self.x1:self.x2]
                else:
                    img = numArray
                file_path = str(self.n_win_gui_id) + "_" + str(self.st_frame_info.nFrameNum) + ".jpg"
                cv2.imwrite(file_path, img)

            cv2.imshow(str(self.n_win_gui_id), numArray)
            cv2.waitKey(1)

            if self.b_exit == True:
                cv2.destroyAllWindows()
                if img_buff is not None:
                    del img_buff
                if self.buf_cache is not None:
                    del buf_cache
                break

    def on_mouse(self, event, x, y, flags, param):

        if event == cv2.EVENT_LBUTTONDOWN:  # 左键点击,则在原图打点
            print("1-EVENT_LBUTTONDOWN")
            point1 = (x, y)
            # cv2.circle(img2, point1, 10, (0, 255, 0), 5)
            # cv2.imshow('image', img2)
            self.x1 = x
            self.y1 = y

        elif event == cv2.EVENT_MOUSEMOVE and (flags & cv2.EVENT_FLAG_LBUTTON):  # 按住左键拖曳，画框
            print("2-EVENT_FLAG_LBUTTON")
            self.x2 = x
            self.y2 = y
            # cv2.rectangle(img2, point1, (x, y), (255, 0, 0), thickness=2)
            # cv2.imshow('image', img2)

        elif event == cv2.EVENT_LBUTTONUP:  # 左键释放，显示
            print("3-EVENT_LBUTTONUP")
            # point2 = (x, y)
            # cv2.rectangle(img2, point1, point2, (0, 0, 255), thickness=2)
            # cv2.imshow('image', img2)
            # if point1!=point2:
            #     min_x = min(point1[0], point2[0])
            #     min_y = min(point1[1], point2[1])
            #     width = abs(point1[0] - point2[0])
            #     height = abs(point1[1] - point2[1])
            #     g_rect=[min_x,min_y,width,height]
            #     cut_img = img[min_y:min_y + height, min_x:min_x + width]
            #     cv2.imshow('ROI', cut_img)
            self.x2 = x
            self.y2 = y
        return

    def time_thread(self):
        while True:
            print('screen shot')
            self.Screenshot_flag = True
            time.sleep(self.timer)
            if self.Screenshot_thread_exit == True:
                break

    def Start_Screenshot(self):
        if self.timer == -1:
            self.Screenshot_flag = True
        else:
            if self.Screenshot_running == False and self.b_open_device == True:
                self.Screenshot_running = True
                self.Screenshot_thread_handle = threading.Thread(target=CameraOperation.time_thread, args=(self,))
                self.Screenshot_thread_handle.start()
            else:
                tkinter.messagebox.showerror('show error', 'error: open device or stop screenshot first')
        return

    def Stop_Screenshot(self):
        if self.Screenshot_running == True:
            self.Screenshot_thread_exit = True
            Stop_thread(self.Screenshot_thread_handle)
            print("stop screenshot successfully")

    def Save_jpg(self):
        if (None == self.buf_cache):
            return
        self.buf_save_image = None
        file_path = str(self.st_frame_info.nFrameNum) + ".jpg"
        self.n_save_image_size = self.st_frame_info.nWidth * self.st_frame_info.nHeight * 3 + 2048
        if self.buf_save_image is None:
            self.buf_save_image = (c_ubyte * self.n_save_image_size)()

        stParam = MV_SAVE_IMAGE_PARAM_EX()
        stParam.enImageType = MV_Image_Jpeg;  # ch:需要保存的图像类型 | en:Image format to save
        stParam.enPixelType = self.st_frame_info.enPixelType  # ch:相机对应的像素格式 | en:Camera pixel type
        stParam.nWidth = self.st_frame_info.nWidth  # ch:相机对应的宽 | en:Width
        stParam.nHeight = self.st_frame_info.nHeight  # ch:相机对应的高 | en:Height
        stParam.nDataLen = self.st_frame_info.nFrameLen
        stParam.pData = cast(self.buf_cache, POINTER(c_ubyte))
        stParam.pImageBuffer = cast(byref(self.buf_save_image), POINTER(c_ubyte))
        stParam.nBufferSize = self.n_save_image_size  # ch:存储节点的大小 | en:Buffer node size
        stParam.nJpgQuality = 80;  # ch:jpg编码，仅在保存Jpg图像时有效。保存BMP时SDK内忽略该参数
        return_code = self.obj_cam.MV_CC_SaveImageEx2(stParam)

        if return_code != 0:
            tkinter.messagebox.showerror('show error', 'save jpg fail! ret = ' + self.To_hex_str(return_code))
            self.b_save_jpg = False
            return
        file_open = open(file_path.encode('ascii'), 'wb+')
        img_buff = (c_ubyte * stParam.nImageLen)()
        try:
            cdll.msvcrt.memcpy(byref(img_buff), stParam.pImageBuffer, stParam.nImageLen)
            file_open.write(img_buff)
            self.b_save_jpg = False
            tkinter.messagebox.showinfo('show info', 'save bmp success!')
        except:
            self.b_save_jpg = False
            raise Exception("get one frame failed:%s" % e.message)
        if (None != img_buff):
            del img_buff

    def Save_Bmp(self):
        if (0 == self.buf_cache):
            return
        self.buf_save_image = None
        file_path = str(self.st_frame_info.nFrameNum) + ".bmp"
        self.buf_save_image = self.st_frame_info.nWidth * self.st_frame_info.nHeight * 3 + 2048
        if self.buf_save_image is None:
            self.buf_save_image = (c_ubyte * self.n_save_image_size)()

        stParam = MV_SAVE_IMAGE_PARAM_EX()
        stParam.enImageType = MV_Image_Bmp;  # ch:需要保存的图像类型 | en:Image format to save
        stParam.enPixelType = self.st_frame_info.enPixelType  # ch:相机对应的像素格式 | en:Camera pixel type
        stParam.nWidth = self.st_frame_info.nWidth  # ch:相机对应的宽 | en:Width
        stParam.nHeight = self.st_frame_info.nHeight  # ch:相机对应的高 | en:Height
        stParam.nDataLen = self.st_frame_info.nFrameLen
        stParam.pData = cast(self.buf_cache, POINTER(c_ubyte))
        stParam.pImageBuffer = cast(byref(self.buf_save_image), POINTER(c_ubyte))
        stParam.nBufferSize = self.n_save_image_size  # ch:存储节点的大小 | en:Buffer node size
        return_code = self.obj_cam.MV_CC_SaveImageEx2(stParam)
        if return_code != 0:
            tkinter.messagebox.showerror('show error', 'save bmp fail! ret = ' + self.To_hex_str(return_code))
            self.b_save_bmp = False
            return
        file_open = open(file_path.encode('ascii'), 'wb+')
        img_buff = (c_ubyte * stParam.nImageLen)()
        try:
            cdll.msvcrt.memcpy(byref(img_buff), stParam.pImageBuffer, stParam.nImageLen)
            file_open.write(img_buff)
            self.b_save_bmp = False
            tkinter.messagebox.showinfo('show info', 'save bmp success!')
        except:
            self.b_save_bmp = False
            raise Exception("get one frame failed:%s" % e.message)
        if (None != img_buff):
            del img_buff

    def Is_mono_data(self, enGvspPixelType):
        if PixelType_Gvsp_Mono8 == enGvspPixelType or PixelType_Gvsp_Mono10 == enGvspPixelType \
                or PixelType_Gvsp_Mono10_Packed == enGvspPixelType or PixelType_Gvsp_Mono12 == enGvspPixelType \
                or PixelType_Gvsp_Mono12_Packed == enGvspPixelType:
            return True
        else:
            return False

    def Is_color_data(self, enGvspPixelType):
        if PixelType_Gvsp_BayerGR8 == enGvspPixelType or PixelType_Gvsp_BayerRG8 == enGvspPixelType \
                or PixelType_Gvsp_BayerGB8 == enGvspPixelType or PixelType_Gvsp_BayerBG8 == enGvspPixelType \
                or PixelType_Gvsp_BayerGR10 == enGvspPixelType or PixelType_Gvsp_BayerRG10 == enGvspPixelType \
                or PixelType_Gvsp_BayerGB10 == enGvspPixelType or PixelType_Gvsp_BayerBG10 == enGvspPixelType \
                or PixelType_Gvsp_BayerGR12 == enGvspPixelType or PixelType_Gvsp_BayerRG12 == enGvspPixelType \
                or PixelType_Gvsp_BayerGB12 == enGvspPixelType or PixelType_Gvsp_BayerBG12 == enGvspPixelType \
                or PixelType_Gvsp_BayerGR10_Packed == enGvspPixelType or PixelType_Gvsp_BayerRG10_Packed == enGvspPixelType \
                or PixelType_Gvsp_BayerGB10_Packed == enGvspPixelType or PixelType_Gvsp_BayerBG10_Packed == enGvspPixelType \
                or PixelType_Gvsp_BayerGR12_Packed == enGvspPixelType or PixelType_Gvsp_BayerRG12_Packed == enGvspPixelType \
                or PixelType_Gvsp_BayerGB12_Packed == enGvspPixelType or PixelType_Gvsp_BayerBG12_Packed == enGvspPixelType \
                or PixelType_Gvsp_YUV422_Packed == enGvspPixelType or PixelType_Gvsp_YUV422_YUYV_Packed == enGvspPixelType:
            return True
        else:
            return False

    def Mono_numpy(self, data, nWidth, nHeight):
        data_ = np.frombuffer(data, count=int(nWidth * nHeight), dtype=np.uint8, offset=0)
        data_mono_arr = data_.reshape(nHeight, nWidth)
        numArray = np.zeros([nHeight, nWidth, 1], "uint8")
        numArray[:, :, 0] = data_mono_arr
        return numArray

    def Color_numpy(self, data, nWidth, nHeight):
        data_ = np.frombuffer(data, count=int(nWidth * nHeight * 3), dtype=np.uint8, offset=0)
        data_r = data_[0:nWidth * nHeight * 3:3]
        data_g = data_[1:nWidth * nHeight * 3:3]
        data_b = data_[2:nWidth * nHeight * 3:3]

        data_r_arr = data_r.reshape(nHeight, nWidth)
        data_g_arr = data_g.reshape(nHeight, nWidth)
        data_b_arr = data_b.reshape(nHeight, nWidth)
        numArray = np.zeros([nHeight, nWidth, 3], "uint8")

        numArray[:, :, 2] = data_r_arr
        numArray[:, :, 1] = data_g_arr
        numArray[:, :, 0] = data_b_arr
        return numArray
