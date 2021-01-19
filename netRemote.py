# lampControllerComunicator
# Copyright (C) 2021 Hiroki Fujii <hfujii@hisystron.com>

import os
import win32api
import threading
import time
import json
import wx
import requests
import constants
import globalVars
import listManager
from soundPlayer.constants import *


class lampController(threading.Thread):
    def __init__(self):
        # 定数
        self.TITLE = 0
        self.PATH = 1
        self.ARTIST = 2
        self.ALBUM = 3
        self.ALBUM_ARTIST = 4
        self.LENGTH = 5
        
        self.fileInfo = ["", "", "", "", "", 0]
        self.exitFlag = False
        self.playbackTime = 0
        super().__init__()

    def run(self):
        while not self.exitFlag:
            time.sleep(1    )
            if self.exitFlag: break
            responseObject = requests.post("http://localhost:8091/lamp/api/v1/comunication", json=self.__makeData(), timeout=5)
            responseObject.encoding="utf-8"
            resJson = responseObject.json()
            for o in resJson["operation"]:
                if o == "play":
                    wx.CallAfter(globalVars.eventProcess.playButtonControl)

    def exit(self):
        self.exitFlag = True
    
    def __makeData(self):
        if globalVars.play.getStatus() == PLAYER_STATUS_PLAYING: playStatus = "playing"
        elif globalVars.play.getStatus() == PLAYER_STATUS_PAUSED: playStatus = "paused"
        else: playStatus = "stopped"
        jData = {}
        jData["apiVersion"] = 1
        jData["authentication"] = {"userName": "hirokif", "softwareKey": "1"}
        jData["software"] = {
            "driveSerialNo": win32api.GetVolumeInformation(os.environ["SystemRoot"][:3])[1],
            "pcName": os.environ["COMPUTERNAME"]
        }
        jData["status"] = {
            "playbackStatus": playStatus,
            "fileTitle": self.fileInfo[self.TITLE],
            "filePath": self.fileInfo[self.PATH],
            "fileArtist": self.fileInfo[self.ARTIST],
            "fileAlbum": self.fileInfo[self.ALBUM],
            "fileAlbumArtist": self.fileInfo[self.ALBUM_ARTIST],
            "playbackTime": self.__getPlaybackTime(),
            "fileLength": self.fileInfo[self.LENGTH]
        }
        return jData
    
    def setFileInfo(self):
        if globalVars.eventProcess.playingList == constants.PLAYLIST: t = listManager.getTuple(constants.PLAYLIST)
        else: t = globalVars.listInfo.playingTmp
        if t[constants.ITEM_TITLE] == "": self.fileInfo = [t[constants.ITEM_NAME]]
        else: self.fileInfo = [t[constants.ITEM_TITLE]]
        self.fileInfo += [t[constants.ITEM_PATH],
            t[constants.ITEM_ARTIST], t[constants.ITEM_ALBUM], t[constants.ITEM_ALBUMARTIST]]
        if t[constants.ITEM_LENGTH] == None: self.fileInfo.append(0)
        else: self.fileInfo.append(t[constants.ITEM_LENGTH])

    def clearFileInfo(self):
        self.fileInfo = ["", "", "", "", "", 0]

    def __getPlaybackTime(self):
        ret = self.playbackTime
        self.playbackTime = 0
        return ret

    def setPlaybackTime(self, sec):
        if (isinstance(sec, int) or isinstance(sec, float)) and sec >= 0:
            self.playbackTime = int(sec)
        else: self.playbackTime = 0
