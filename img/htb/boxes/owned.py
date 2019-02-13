#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PIL import Image

X = 245
Y = 204

L = 533
W = 78

im = Image.open('owned.png')

offset_x, offset_y = 0, 0
for i in range(1, 18):
	im.crop((X+offset_x, Y+offset_y, X+offset_x+L, Y+offset_y+W)).save(f'{i}-owned-root.png')
	offset_x += 553
	if i % 4 == 0:
		offset_x = 0
		offset_y += 104

X = 245
Y = 837

L = 533
W = 78

offset_x, offset_y = 0, 0
for i in range(1, 18):
	im.crop((X+offset_x, Y+offset_y, X+offset_x+L, Y+offset_y+W)).save(f'{i}-owned-user.png')
	offset_x += 553
	if i % 4 == 0:
		offset_x = 0
		offset_y += 104
