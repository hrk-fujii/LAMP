﻿# -*- coding: utf-8 -*-
#main view
#Copyright (C) 2019 Yukio Nozawa <personal@nyanchangames.com>
#Copyright (C) 2019-2020 yamahubuki <itiro.ishino@gmail.com>

from views import lampViewObject
from views import setting_dialog
from views import notificationText
from views import versionDialog
import logging
import os
import sys
import wx
import re
import ctypes
import pywintypes

import constants
import errorCodes
import globalVars
import hotkeyHandler
import menuItemsStore
import settings
import m3uManager
import effector
import listManager
from soundPlayer import player
from soundPlayer.constants import *

import view_manager
import sendToManager
from views import mkDialog
from views import fileAssocDialog

from logging import getLogger
from simpleDialog import dialog
from .base import *
from simpleDialog import *

import views.mkOpenDialog


class MainView(BaseView):
	def __init__(self):
		super().__init__("mainView")
		self.log.debug("created")
		self.app=globalVars.app
		self.events=Events(self,self.identifier)
		title=constants.APP_NAME
		super().Initialize(
			title,
			self.app.config.getint(self.identifier,"sizeX",800),
			self.app.config.getint(self.identifier,"sizeY",600),
			self.app.config.getint(self.identifier,"positionX"),
			self.app.config.getint(self.identifier,"positionY")
		)
		self.InstallMenuEvent(Menu(self.identifier, self.events),self.events.OnMenuSelect)
		
		# 矢印キーUpを握りつぶしてショートカットキーの重複を回避
		def stopArrowPropagation(evt):
			if evt.GetKeyCode() in (wx.WXK_UP, wx.WXK_DOWN, wx.WXK_LEFT, wx.WXK_RIGHT): evt.StopPropagation()
			else: evt.Skip()
		

		#上余白
		self.creator.AddSpace(15)

		# ボタン・音量スライダエリア
		self.horizontalCreator = views.ViewCreator.ViewCreator(self.viewMode, self.hPanel, self.creator.GetSizer(), wx.HORIZONTAL,style=wx.LEFT | wx.RIGHT | wx.EXPAND,space=20,margin=65)
		self.previousBtn = self.horizontalCreator.button("", self.events.onButtonClick, style=wx.BU_NOTEXT|wx.BU_EXACTFIT|wx.BORDER_NONE, enableTabFocus=False)
		view_manager.setBitmapButton(self.previousBtn, self.hPanel, wx.Bitmap("./resources/back.dat", wx.BITMAP_TYPE_GIF), _("前へ"))
		self.playPauseBtn = self.horizontalCreator.button("", self.events.onButtonClick, style=wx.BU_NOTEXT|wx.BU_EXACTFIT|wx.BORDER_NONE, enableTabFocus=False)
		view_manager.setBitmapButton(self.playPauseBtn, self.hPanel, wx.Bitmap("./resources/play.dat", wx.BITMAP_TYPE_GIF), _("再生"))
		self.nextBtn = self.horizontalCreator.button("", self.events.onButtonClick, style=wx.BU_NOTEXT|wx.BU_EXACTFIT|wx.BORDER_NONE, enableTabFocus=False)
		view_manager.setBitmapButton(self.nextBtn, self.hPanel, wx.Bitmap("./resources/next.dat", wx.BITMAP_TYPE_GIF), _("次へ"))
		self.stopBtn = self.horizontalCreator.button("", self.events.onButtonClick, style=wx.BU_NOTEXT|wx.BU_EXACTFIT|wx.BORDER_NONE, enableTabFocus=False)
		view_manager.setBitmapButton(self.stopBtn, self.hPanel, wx.Bitmap("./resources/stop.dat", wx.BITMAP_TYPE_GIF), _("停止"))
		self.repeatLoopBtn = self.horizontalCreator.button("", self.events.onButtonClick, style=wx.BU_NOTEXT|wx.BU_EXACTFIT|wx.BORDER_NONE, enableTabFocus=False)
		view_manager.setBitmapButton(self.repeatLoopBtn, self.hPanel, wx.Bitmap("./resources/repeatLoop.dat", wx.BITMAP_TYPE_GIF), _("リピートに切り替える"))
		self.shuffleBtn = self.horizontalCreator.button("", self.events.onButtonClick, style=wx.BU_NOTEXT|wx.BU_EXACTFIT|wx.BORDER_NONE, enableTabFocus=False)
		view_manager.setBitmapButton(self.shuffleBtn, self.hPanel, wx.Bitmap("./resources/shuffle_off.dat", wx.BITMAP_TYPE_GIF), _("シャッフルをオンにする"))
		self.horizontalCreator.GetSizer().AddStretchSpacer(1)
		self.muteBtn = self.horizontalCreator.button("", self.events.onButtonClick, style=wx.BU_NOTEXT|wx.BU_EXACTFIT|wx.BORDER_NONE, sizerFlag=wx.ALL|wx.ALIGN_CENTER, enableTabFocus=False)
		if globalVars.app.config.getstring("view","colorMode","white",("white","dark")) == "white":
			view_manager.setBitmapButton(self.muteBtn, self.hPanel, wx.Bitmap("./resources/volume.dat", wx.BITMAP_TYPE_GIF), _("ミュートをオンにする"))
		else: view_manager.setBitmapButton(self.muteBtn, self.hPanel, wx.Bitmap("./resources/volume_bk.dat", wx.BITMAP_TYPE_GIF), _("ミュートをオンにする"))
		self.volumeSlider, dummy = self.horizontalCreator.clearSlider(_("音量"), 0, 100, self.events.onSlider,
			globalVars.app.config.getint("volume","default",default=100, min=0, max=100), x=150, sizerFlag=wx.ALIGN_CENTER, textLayout=None)
		self.volumeSlider.Bind(wx.EVT_KEY_UP, stopArrowPropagation)
		self.volumeSlider.SetThumbLength(25)
		self.volumeSlider.setToolTip(self.val2vol)
		#self.hFrame.Bind(wx.EVT_BUTTON, self.events.onButtonClick)

		self.creator.AddSpace(10)

		# 曲情報表示
		infoCreator = views.ViewCreator.ViewCreator(self.viewMode, self.hPanel, self.creator.GetSizer(), wx.HORIZONTAL,0, style=wx.EXPAND | wx.LEFT | wx.RIGHT, margin=60)
		lb = infoCreator.staticText("♪")
		f = lb.GetFont()
		f.SetPointSize(f.GetPointSize() * (5/3))
		lb.SetFont(f)
		infoRight = views.ViewCreator.ViewCreator(self.viewMode, infoCreator.GetPanel(), infoCreator.GetSizer(), wx.VERTICAL,0, style=wx.EXPAND | wx.LEFT, margin=5, proportion=1)
		self.viewTitle = infoRight.staticText("")
		self.viewTagInfo = infoRight.staticText("")
		f = self.viewTagInfo.GetFont()
		f.SetPointSize(f.GetPointSize() * (2/3))
		self.viewTagInfo.SetFont(f)
		self.tagInfoTimer = wx.Timer()
		self.tagInfoTimer.Bind(wx.EVT_TIMER, globalVars.eventProcess.refreshTagInfo)
		self.nowTime = infoCreator.staticText("0:00:00 / 0:00:00", sizerFlag=wx.ALL, proportion = 0)

		self.creator.AddSpace(10)

		#トラックバーエリア
		#self.horizontalCreator = views.ViewCreator.ViewCreator(self.viewMode, self.hPanel, self.creator.GetSizer(), wx.HORIZONTAL,0, style=wx.EXPAND | wx.LEFT | wx.RIGHT, margin=60)
		self.trackBar, dummy = self.creator.clearSlider(_("トラックバー"), x=1000, sizerFlag=wx.EXPAND | wx.LEFT | wx.RIGHT, proportion=0, margin=60, textLayout=None)
		self.trackBar.SetThumbLength(30)
		self.trackBar.Bind(wx.EVT_KEY_UP, stopArrowPropagation)
		self.trackBar.Bind(wx.EVT_SCROLL, self.events.onSlider)
		self.trackBar.setToolTip(self.sec2TimeStr)

		self.creator.AddSpace(20)

		# リストビューエリア
		self.horizontalCreator = views.ViewCreator.ViewCreator(self.viewMode, self.hPanel, self.creator.GetSizer(), wx.HORIZONTAL, 15, style=wx.EXPAND | wx.LEFT | wx.LEFT | wx.RIGHT, proportion=1, margin=60)
		self.playlistView, self.playlistLabel = self.horizontalCreator.customListCtrl(lampViewObject.playlist, _("プレイリスト") + " (0" + _("件") + ")", style=wx.LC_NO_HEADER, sizerFlag=wx.EXPAND | wx.RIGHT,proportion=2,textLayout=wx.VERTICAL)
		self.playlistView.SetFocus()
		view_manager.listViewSetting(self.playlistView, "playlist")
		self.queueView, self.queueLabel = self.horizontalCreator.customListCtrl(lampViewObject.queue, _("キュー") + " (0" + _("件") + ")", style=wx.LC_NO_HEADER, sizerFlag=wx.EXPAND,proportion=1, textLayout=wx.VERTICAL)
		view_manager.listViewSetting(self.queueView, "queue")

		self.hPanel.Layout()

		lb = wx.StaticText(self.hPanel, label=_("状況"), size=(0,0))
		self.shadowList = wx.ListBox(self.hPanel, size=(0,0))
		view_manager.setValueShadowList(self.shadowList)
		
		# タイマーの呼び出し
		self.timer = wx.Timer(self.hFrame)
		self.timer.Start(100)
		self.hFrame.Bind(wx.EVT_TIMER, self.events.timerEvent, self.timer)

		self.hFrame.Layout()
		self.notification = notificationText.notification(self.hPanel)

		self.hotkey = hotkeyHandler.HotkeyHandler(None,hotkeyHandler.HotkeyFilter().SetDefault())
		if self.hotkey.addFile(constants.KEYMAP_FILE_NAME,["HOTKEY"])!=errorCodes.OK:
			self.hotkey.addDict(defaultKeymap.defaultKeymap, ["HOTKEY"])
			self.hotkey.SaveFile(constants.KEYMAP_FILE_NAME)
		errors=self.hotkey.GetError("HOTKEY")
		if errors:
			tmp=_(constants.KEYMAP_FILE_NAME+"で設定されたホットキーが正しくありません。キーの重複、存在しないキー名の指定、使用できないキーパターンの指定などが考えられます。以下のキーの設定内容をご確認ください。\n\n")
			for v in errors:
				tmp+=v+"\n"
			dialog(_("エラー"),tmp)
		self.hotkey.Set("HOTKEY",self.hFrame)

	def val2vol(self, val):
		return "%d%%" %(round(val))

	def sec2TimeStr(self, sec):
		i = int(sec)
		hour = 0
		min = 0
		sec = 0
		if i > 0: hour = i // 3600
		if i-(hour*3600) > 0: min = (i - hour) // 60
		if i-(hour*3600)-(min*60) > 0: sec = i - (hour*3600) - (min*60)
		return f"{hour:01}:{min:02}:{sec:02}"

class Menu(BaseMenu):
	def __init__(self, identifier, event):
		super().__init__(identifier)
		self.event = event
	
	def Apply(self,target):
		"""指定されたウィンドウに、メニューを適用する。"""

		#メニューの大項目を作る
		self.hFileMenu=wx.Menu()
		self.hFunctionMenu = wx.Menu()
		self.hPlaylistMenu=wx.Menu()
		self.hOperationMenu=wx.Menu()
		self.hSettingsMenu=wx.Menu()
		self.hHelpMenu=wx.Menu()

		#ファイルメニューの中身
		self.RegisterMenuCommand(self.hFileMenu,"FILE_OPEN",_("ファイルを開く"))
		self.RegisterMenuCommand(self.hFileMenu,"DIR_OPEN",_("フォルダを開く"))
		self.RegisterMenuCommand(self.hFileMenu,"URL_OPEN",_("URLを開く"))
		self.RegisterMenuCommand(self.hFileMenu,"M3U_OPEN",_("プレイリストを開く"))
		self.RegisterMenuCommand(self.hFileMenu,"NEW_M3U8_SAVE",_("名前を付けてプレイリストを保存"))
		self.RegisterMenuCommand(self.hFileMenu,"M3U8_SAVE",_("プレイリストを上書き保存"))
		self.hFileMenu.Enable(menuItemsStore.getRef("M3U8_SAVE"), False)
		self.RegisterMenuCommand(self.hFileMenu,"M3U_ADD",_("プレイリストから読み込む"))
		self.RegisterMenuCommand(self.hFileMenu,"M3U_CLOSE",_("プレイリストを閉じる"))
		self.hFileMenu.Enable(menuItemsStore.getRef("M3U_CLOSE"), False)
		self.RegisterMenuCommand(self.hFileMenu,"EXIT",_("終了"))
		#機能メニューの中身
		self.RegisterMenuCommand(self.hFunctionMenu, "SET_SLEEPTIMER", _("スリープタイマーを設定"))
		self.RegisterMenuCommand(self.hFunctionMenu, "SET_EFFECTOR", _("エフェクター"))
		self.RegisterMenuCommand(self.hFunctionMenu, "ABOUT_PLAYING", _("再生中のファイルについて"))
		self.hFunctionMenu.Enable(menuItemsStore.getRef("ABOUT_PLAYING"), False)
		# プレイリストメニューの中身
		self.RegisterMenuCommand(self.hPlaylistMenu,"PLAYLIST_HISTORY_LABEL",_("履歴（20件まで）"))
		self.hPlaylistMenu.Enable(menuItemsStore.getRef("PLAYLIST_HISTORY_LABEL"), False)
		#操作メニューの中身
		self.RegisterMenuCommand(self.hOperationMenu, "PLAY_PAUSE", _("再生 / 一時停止"))
		self.RegisterMenuCommand(self.hOperationMenu, "STOP", _("停止"))
		self.RegisterMenuCommand(self.hOperationMenu, "PREVIOUS_TRACK", _("前へ / 頭出し"))
		self.RegisterMenuCommand(self.hOperationMenu, "NEXT_TRACK", _("次へ"))
		skipRtn = settings.getSkipInterval()
		self.RegisterMenuCommand(self.hOperationMenu, "SKIP", skipRtn[1]+" "+_("進む"))
		self.RegisterMenuCommand(self.hOperationMenu, "REVERSE_SKIP", skipRtn[1]+" "+_("戻る"))
		#スキップ間隔設定
		self.hSetSkipIntervalInOperationMenu=wx.Menu()
		self.hOperationMenu.AppendSubMenu(self.hSetSkipIntervalInOperationMenu, _("スキップ間隔設定"))
		self.RegisterMenuCommand(self.hSetSkipIntervalInOperationMenu, "SKIP_INTERVAL_INCREASE", _("間隔を大きくする"))
		self.RegisterMenuCommand(self.hSetSkipIntervalInOperationMenu, "SKIP_INTERVAL_DECREASE", _("間隔を小さくする"))
		#音量
		self.hVolumeInOperationMenu=wx.Menu()
		self.hOperationMenu.AppendSubMenu(self.hVolumeInOperationMenu, _("音量"))
		self.RegisterMenuCommand(self.hVolumeInOperationMenu, "VOLUME_DEFAULT", _("音量を100%に設定"))
		self.RegisterMenuCommand(self.hVolumeInOperationMenu, "VOLUME_UP", _("音量を上げる"))
		self.RegisterMenuCommand(self.hVolumeInOperationMenu, "VOLUME_DOWN", _("音量を下げる"))
		self.RegisterMenuCommand(self.hVolumeInOperationMenu, "MUTE", _("消音に設定"))
		#リピート・ループ
		self.hRepeatLoopInOperationMenu=wx.Menu()
		self.hOperationMenu.AppendSubMenu(self.hRepeatLoopInOperationMenu, _("リピート・ループ")+"\tCtrl+R")
		self.RegisterRadioMenuCommand(self.hRepeatLoopInOperationMenu, "REPEAT_LOOP_NONE", _("解除する"))
		self.RegisterRadioMenuCommand(self.hRepeatLoopInOperationMenu, "RL_REPEAT", _("リピート"))
		self.RegisterRadioMenuCommand(self.hRepeatLoopInOperationMenu, "RL_LOOP", _("ループ"))
		self.RegisterCheckMenuCommand(self.hOperationMenu, "SHUFFLE", _("シャッフル再生"))
		self.RegisterCheckMenuCommand(self.hOperationMenu, "MANUAL_SONG_FEED", _("手動で曲送り"))
		# 設定メニューの中身
		self.hDeviceChangeInSettingsMenu = wx.Menu()
		self.hSettingsMenu.AppendSubMenu(self.hDeviceChangeInSettingsMenu, _("再生出力先の変更"))
		self.RegisterMenuCommand(self.hSettingsMenu, "FILE_ASSOCIATE", _("ファイルの関連付け"))
		self.RegisterMenuCommand(self.hSettingsMenu, "SET_SENDTO", _("送るメニューに登録"))
		self.RegisterMenuCommand(self.hSettingsMenu, "SET_FONT", _("フォント設定"))
		self.RegisterMenuCommand(self.hSettingsMenu, "SET_KEYMAP", _("ショートカットキー設定"))
		self.RegisterMenuCommand(self.hSettingsMenu, "SET_HOTKEY", _("グローバルホットキー設定"))
		self.RegisterMenuCommand(self.hSettingsMenu, "ENVIRONMENT", _("環境設定"))
		#ヘルプメニューの中身
		self.RegisterMenuCommand(self.hHelpMenu,"HELP",_("ヘルプ"))
		self.RegisterMenuCommand(self.hHelpMenu,"CHECK_UPDATE",_("更新の確認"))
		self.RegisterMenuCommand(self.hHelpMenu,"VERSION_INFO",_("バージョン情報"))

		#メニューバーの生成
		self.hMenuBar.Append(self.hFileMenu,_("ファイル") + " (&F)")
		self.hMenuBar.Append(self.hFunctionMenu, _("機能") + " (&U)")
		self.hMenuBar.Append(self.hPlaylistMenu,_("プレイリスト") + " (&P)")
		self.hMenuBar.Append(self.hOperationMenu,_("操作") + " (&O)")
		self.hMenuBar.Append(self.hSettingsMenu,_("設定") + "(&S)")
		self.hMenuBar.Append(self.hHelpMenu,_("ヘルプ") + " (&H)")
		target.SetMenuBar(self.hMenuBar)

		# イベント
		target.Bind(wx.EVT_MENU_OPEN, self.event.OnMenuOpen)

class Events(BaseEvents):
	def OnMenuSelect(self,event):
		"""メニュー項目が選択されたときのイベントハンドら。"""
		#ショートカットキーが無効状態のときは何もしない
		if not self.parent.shortcutEnable:
			event.Skip()
			return

		selected=event.GetId()#メニュー識別しの数値が出る

		if selected==menuItemsStore.getRef("FILE_OPEN"):
			dialog= views.mkOpenDialog.Dialog("fileOpenDialog")
			dialog.Initialize(0) #0=ファイルダイアログ
			rtnCode = dialog.Show()
			if rtnCode == dialog.PLAYLIST:
				listManager.addItems([dialog.GetValue()], globalVars.app.hMainView.playlistView)
			elif rtnCode == dialog.QUEUE:
				listManager.addItems([dialog.GetValue()], globalVars.app.hMainView.queueView)
			else:
				return
		elif selected==menuItemsStore.getRef("DIR_OPEN"):
			dialog= views.mkOpenDialog.Dialog("directoryOpenDialog")
			dialog.Initialize(1) #1=フォルダダイアログ
			rtnCode = dialog.Show()
			if rtnCode == dialog.PLAYLIST:
				listManager.addItems([dialog.GetValue()], globalVars.app.hMainView.playlistView)
			elif rtnCode == dialog.QUEUE:
				listManager.addItems([dialog.GetValue()], globalVars.app.hMainView.queueView)
			else:
				return
		elif selected==menuItemsStore.getRef("URL_OPEN"):
			dialog= views.mkOpenDialog.Dialog("urlOpenDialog")
			dialog.Initialize(2) #2=URLダイアログ
			rtnCode = dialog.Show()
			if rtnCode == dialog.PLAYLIST:
				listManager.addItems([dialog.GetValue()], globalVars.app.hMainView.playlistView)
			elif rtnCode == dialog.QUEUE:
				listManager.addItems([dialog.GetValue()], globalVars.app.hMainView.queueView)
			else:
				return
		elif selected==menuItemsStore.getRef("M3U_OPEN"):
			m3uManager.loadM3u()
		elif selected==menuItemsStore.getRef("NEW_M3U8_SAVE"):
			m3uManager.saveM3u8()
		elif selected==menuItemsStore.getRef("M3U8_SAVE"):
			m3uManager.saveM3u8(globalVars.playlist.playlistFile)
		elif selected==menuItemsStore.getRef("M3U_ADD"):
			m3uManager.loadM3u(None, m3uManager.ADD)
		elif selected==menuItemsStore.getRef("M3U_CLOSE"):
			m3uManager.closeM3u()
		elif selected == menuItemsStore.getRef("EXIT"):
			self.Exit()
		#機能メニューのイベント
		elif selected == menuItemsStore.getRef("SET_SLEEPTIMER"):
			globalVars.sleepTimer.set()
		elif selected == menuItemsStore.getRef("SET_EFFECTOR"):
			effector.effector()
		elif selected == menuItemsStore.getRef("ABOUT_PLAYING"):
			if globalVars.eventProcess.playingList == constants.PLAYLIST:
				listManager.infoDialog(listManager.getTuple(constants.PLAYLIST))
			else:
				listManager.infoDialog(globalVars.listInfo.tmpTuple)
		# 操作メニューのイベント
		elif selected==menuItemsStore.getRef("PLAY_PAUSE"):
			globalVars.eventProcess.playButtonControl()
		elif selected==menuItemsStore.getRef("STOP"):
			globalVars.eventProcess.stop()
		elif selected==menuItemsStore.getRef("PREVIOUS_TRACK"):
			globalVars.eventProcess.previousBtn()
		elif selected==menuItemsStore.getRef("NEXT_TRACK"):
			globalVars.eventProcess.nextFile(button=True)
		elif selected==menuItemsStore.getRef("VOLUME_DEFAULT"):
			globalVars.eventProcess.changeVolume(vol=100)
		elif selected==menuItemsStore.getRef("VOLUME_UP"):
			globalVars.eventProcess.changeVolume(+1)
		elif selected==menuItemsStore.getRef("VOLUME_DOWN"):
			globalVars.eventProcess.changeVolume(-1)
		elif selected==menuItemsStore.getRef("MUTE"):
			globalVars.eventProcess.mute()
		elif selected==menuItemsStore.getRef("FAST_FORWARD"):
			globalVars.play.fastForward()
		elif selected==menuItemsStore.getRef("REWIND"):
			globalVars.play.rewind()
		elif selected==menuItemsStore.getRef("SAY_TIME"):
			pos = globalVars.play.getPosition()
			if pos == -1: time = _("情報がありません")
			else:
				hour = pos // 3600
				min = (pos - hour * 3600) // 60
				sec = int(pos - hour * 3600 - min * 60)
				if hour == 0: sHour = ""
				else: sHour = str(int(hour)) + _("時間") + " "
				if min == 0: sMin = ""
				else: sMin = str(int(min)) + _("分") + " "
				time = sHour + sMin + str(int(sec)) + _("秒")
			globalVars.app.say(time)
		elif selected==menuItemsStore.getRef("SKIP"):
			globalVars.eventProcess.skip(settings.getSkipInterval()[0])
		elif selected==menuItemsStore.getRef("REVERSE_SKIP"):
			globalVars.eventProcess.skip(settings.getSkipInterval()[0], False)
		elif selected==menuItemsStore.getRef("SKIP_INTERVAL_INCREASE"):
			globalVars.eventProcess.setSkipInterval()
		elif selected==menuItemsStore.getRef("SKIP_INTERVAL_DECREASE"):
			globalVars.eventProcess.setSkipInterval(False)
		elif selected==menuItemsStore.getRef("REPEAT_LOOP"):
			globalVars.eventProcess.repeatLoopCtrl()
		elif selected==menuItemsStore.getRef("REPEAT_LOOP_NONE"):
			globalVars.eventProcess.repeatLoopCtrl(0)
		elif selected==menuItemsStore.getRef("RL_REPEAT"):
			globalVars.eventProcess.repeatLoopCtrl(1)
		elif selected==menuItemsStore.getRef("RL_LOOP"):
			globalVars.eventProcess.repeatLoopCtrl(2)
		elif selected==menuItemsStore.getRef("SHUFFLE"):
			globalVars.eventProcess.shuffleSw()
		elif selected==menuItemsStore.getRef("MANUAL_SONG_FEED"):
			globalVars.eventProcess.setSongFeed()
		elif selected >= constants.DEVICE_LIST_MENU and selected < constants.DEVICE_LIST_MENU + 500:
			if selected == constants.DEVICE_LIST_MENU: globalVars.play.setDevice(PLAYER_DEFAULT_SPEAKER)
			else: globalVars.play.setDevice(selected - constants.DEVICE_LIST_MENU)
		elif selected >= constants.PLAYLIST_HISTORY and selected < constants.PLAYLIST_HISTORY+ 20:
			m3uManager.loadM3u(globalVars.m3uHistory.getList()[selected - constants.PLAYLIST_HISTORY])
		elif selected==menuItemsStore.getRef("FILE_ASSOCIATE"):
			fileAssocDialog.assocDialog()
		elif selected==menuItemsStore.getRef("SET_SENDTO"):
			sendToManager.sendToCtrl("LAMP")
		elif selected==menuItemsStore.getRef("ENVIRONMENT"):
			d = setting_dialog.settingDialog("environment_dialog")
			d.Initialize()
			d.Show()
		elif selected==menuItemsStore.getRef("CHECK_UPDATE"):
			globalVars.update.update()
		elif selected==menuItemsStore.getRef("VERSION_INFO"):
			versionDialog.versionDialog()

	def OnMenuOpen(self, event):
		menuObject = event.GetEventObject()
		
		if event.GetMenu()==self.parent.menu.hDeviceChangeInSettingsMenu:
			menu = self.parent.menu.hDeviceChangeInSettingsMenu
			# 内容クリア
			for i in range(menu.GetMenuItemCount()):
				menu.DestroyItem(menu.FindItemByPosition(0))
			# デバイスリスト追加
			deviceList = player.getDeviceList()
			deviceIndex = 0
			for d in deviceList:
				if deviceIndex == 0: menu.AppendCheckItem(constants.DEVICE_LIST_MENU, _("規定の出力先"))
				elif d != None: menu.AppendCheckItem(constants.DEVICE_LIST_MENU + deviceIndex, d)
				deviceIndex += 1
			# 現在の設定にチェック
			deviceNow = globalVars.play.getConfig(PLAYER_CONFIG_DEVICE)
			if deviceNow == PLAYER_DEFAULT_SPEAKER: menu.Check(constants.DEVICE_LIST_MENU, True)
			elif deviceNow > 0 and deviceNow < len(deviceList) and deviceList[deviceNow] != None: menu.Check(constants.DEVICE_LIST_MENU + deviceNow, True)
		elif menuObject == self.parent.menu.hPlaylistMenu:
			menu = self.parent.menu.hPlaylistMenu
			# 履歴部分を削除
			for i in range(menu.GetMenuItemCount() - 1):
				menu.DestroyItem(menu.FindItemByPosition(1))
			# 履歴部分を作成
			index = 0
			for path in globalVars.m3uHistory.getList():
				menu.Insert(1, constants.PLAYLIST_HISTORY + index, path)
				index += 1
		elif menuObject == self.parent.menu.hOperationMenu:
			self.parent.menu.hOperationMenu.Check(menuItemsStore.getRef("MANUAL_SONG_FEED"), globalVars.app.config.getboolean("player", "manualSongFeed", False))
	
	def onButtonClick(self, event):
			if event.GetEventObject() == globalVars.app.hMainView.previousBtn:
				globalVars.eventProcess.previousBtn()
			elif event.GetEventObject() == globalVars.app.hMainView.playPauseBtn:
				globalVars.eventProcess.playButtonControl()
			elif event.GetEventObject() == globalVars.app.hMainView.nextBtn:
				globalVars.eventProcess.nextFile(button=True)
			elif event.GetEventObject() == globalVars.app.hMainView.stopBtn:
				globalVars.eventProcess.stop()
			elif event.GetEventObject() == globalVars.app.hMainView.repeatLoopBtn:
				globalVars.eventProcess.repeatLoopCtrl()
			elif event.GetEventObject() == globalVars.app.hMainView.shuffleBtn:
				globalVars.eventProcess.shuffleSw()
			elif event.GetEventObject() == globalVars.app.hMainView.muteBtn:
				globalVars.eventProcess.mute()

	def onSlider(self, evt):
		if evt.GetEventObject() == globalVars.app.hMainView.volumeSlider:
			val = globalVars.app.hMainView.volumeSlider.GetValue()
			globalVars.eventProcess.changeVolume(vol=val)
		elif evt.GetEventObject() == globalVars.app.hMainView.trackBar:
			globalVars.eventProcess.trackBarCtrl(evt.GetEventObject())
	
	def timerEvent(self, evt):
		globalVars.eventProcess.refreshView()

	def Exit(self, evt=None):
		globalVars.app.hMainView.timer.Stop()
		globalVars.app.hMainView.tagInfoTimer.Stop()
		super().Exit()
