#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from PIL import Image

X = 974
Y = 31

L = 533
W = 340

i = 1
for f in os.listdir():
	if f.startswith('Screenshot'):
		with Image.open(f) as im:
			im.crop((X, Y, X+L, Y+W)).save(f'{i}-trophy.png')
		i += 1
