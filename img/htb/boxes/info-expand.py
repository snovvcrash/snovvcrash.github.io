#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from PIL import Image

new_size = (670, 380)

for f in os.listdir():
	if not f.endswith('.py'):
		with Image.open(f) as im:
			old_size = im.size
			new_im = Image.new('RGB', new_size, (12, 13, 14))
			new_im.paste(
				im,
				(
					int((new_size[0] - old_size[0]) / 2),
					int((new_size[1] - old_size[1]) / 2) + 1
				)
			)
			new_im.save(f)
