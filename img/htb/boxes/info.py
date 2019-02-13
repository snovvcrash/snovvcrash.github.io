#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from PIL import Image

X = 942
Y = 31

L = 598
W = 380

for f in os.listdir():
	if f.startswith('Screenshot'):
		with Image.open(f) as im:
			im.crop((X, Y, X+L, Y+W)).save(f'{f.split()[-1][:-4].lower()}-info.png')
