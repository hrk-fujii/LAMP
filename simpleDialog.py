﻿# -*- coding: utf-8 -*-
#Simple dialog

import ctypes

def winDialog(title,message):
	ctypes.windll.user32.MessageBoxW(0,message,title,0x00000040)

def dialog(title,message):
	ctypes.windll.user32.MessageBoxW(0,message,title,0x00000040)
