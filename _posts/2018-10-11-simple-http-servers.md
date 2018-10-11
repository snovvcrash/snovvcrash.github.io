---
layout: post
title: "О быстром развертывании простых http-серверов для трансфера файлов под Linux"
date: 2018-10-11 00:00:00 +0300
author: snovvcrash
categories: ctf-tools cheatsheets
tags: [ctf-tools, cheatsheets, linux, file-transfer, http-server, python-server, php-server, nginx]
comments: true
---

Последнее время часто сталкивался с необходимостью обмена файлами между двумя Linux-машинами. В этом посте опишу 3 удобных способа, как можно быстро и легко развернуть тривиальный http-сервер для трансфера файлов.

<!--cut-->

![simple-http-servers-banner.png]({{ "/img/simple-http-servers-banner.png" | relative_url }})

<h4 style="color:red;margin-bottom:0;">Local: 10.10.10.1</h4>
<h4 style="color:red;">Remote: 10.10.10.2</h4>

* TOC
{:toc}

# Python
Питон может выручить практически в любой ситуации, и наш случай не исключение.

Всем известны эти замечательные команды для запуска http-серверов для второй версии питона:
```text
local@server:~$ python -m SimpleHTTPServer [port]
```

И ее аналог для Python 3:
```text
local@server:~$ python3 -m http.server [-h] [--cgi] [--bind ADDRESS] [port]
```

Таким способом можно только выдергивать файлы оттуда, где подняли сервер, т. к. единственные методы, который он понимает "из коробки", это `HEAD` и `GET`. Однако никто не запрещает нам немного модифицировать дефолтное поведение, добавив, к примеру, обработку `POST` (выводим содержимое в консоль для примера) и `PUT` -запросов.

Простой скрипт:
```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Usage: python3 SimpleHTTPServer+.py [-h] [--bind ADDRESS] [port]

import http.server
import os

from argparse import ArgumentParser


class HTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
	def _set_headers(self):
		self.send_response(200)
		self.send_header('Content-type', 'text/html')
		self.end_headers()

	def do_POST(self):
		content_length = int(self.headers['Content-Length'])
		post_data = self.rfile.read(content_length)
		self._set_headers()
		self.wfile.write(b'<html><body><h1>POST!</h1></body></html>')

		print(post_data.decode('utf-8'))

	def do_PUT(self):
		path = self.translate_path(self.path)
		if path.endswith('/'):
			self.send_response(405, 'Method Not Allowed')
			self.wfile.write(b'PUT not allowed on a directory\n')
			return
		else:
			try:
				os.makedirs(os.path.dirname(path))
			except FileExistsError: pass
			length = int(self.headers['Content-Length'])
			with open(path, 'wb') as f:
				f.write(self.rfile.read(length))
			self.send_response(201, 'Created')
			self.end_headers()


def cli_options():
	parser = ArgumentParser()

	parser.add_argument(
		'--bind',
		'-b',
		default='',
		metavar='ADDRESS',
		help='Specify alternate bind address [default: all interfaces]'
	)

	parser.add_argument(
		'port',
		action='store',
		default=8000,
		type=int,
		nargs='?',
		help='Specify alternate port [default: 8000]'
	)

	return parser.parse_args()


if __name__ == '__main__':
	args = cli_options()
	http.server.test(HandlerClass=HTTPRequestHandler, port=args.port, bind=args.bind)
```

Позволяет успешно как *выгружать файлы с*:
```text
local@server:~$ wget 10.10.10.2:8881/message
--2018-10-11 10:51:35--  http://10.10.10.2:8881/message
Connecting to 10.10.10.2:8881... connected.
HTTP request sent, awaiting response... 200 OK
Length: 10 [application/octet-stream]
Saving to: ‘message’

message              100%[===================>]      10  --.-KB/s    in 0s

2018-10-11 10:51:35 (2.40 MB/s) - ‘message’ saved [10/10]
```

```text
local@server:~$ cat message
Hi there!
```

```text
remote@server:~$ python3 SimpleHTTPServer+.py 8881
Serving HTTP on 0.0.0.0 port 8881 (http://0.0.0.0:8881/) ...
10.10.10.1 - - [11/Oct/2018 11:04:37] "GET /message HTTP/1.1" 200 -
```

Так и *загружать на* Linux-машину:
```text
local@server:~$ curl --upload-file message 10.10.10.2:8881
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100    10    0     0  100    10      0      9  0:00:01  0:00:01 --:--:--     9


local@server:~$ curl -d @message -X POST 10.10.10.2:8881
<html><body><h1>POST!</h1></body></html>
```

```text
remote@server:~$ python3 SimpleHTTPServer+.py 8881
Serving HTTP on 0.0.0.0 port 8881 (http://0.0.0.0:8881/) ...
10.10.10.1 - - [11/Oct/2018 10:52:10] "PUT /message HTTP/1.1" 201 -
10.10.10.1 - - [11/Oct/2018 10:52:18] "POST / HTTP/1.1" 200 -
Hi there!
```

```text
remote@server:~$ cat message
Hi there!
```

Доступные методы: `GET`, `POST`, `PUT`.

# PHP
Неудивительно, что двухстрочный скрипт на *PHP* может решить все наши проблемы — "препроцессор гипертекста" как-никак :sunglasses:

Итак, для тривиального PHP-сервера нам понадобится такой код:
```php
<?php
$fname = basename($_REQUEST['filename']);
file_put_contents('uploads/' . $fname, file_get_contents('php://input'));
?>
```

На скриншоте ниже (кликабельно) можно видеть все шаги настройки сервера: предварительная настройка на панели слева, тесты — справа.

[![simple-http-servers-php.png]({{ "/img/simple-http-servers-php.png" | relative_url }})]({{ "/img/simple-http-servers-php.png" | relative_url }})

Несколько слов о том, что здесь происходит:
  1. Создаем необходимые директории и скрипт с содержимым выше.
  2. Создаем пользователя, от которого будет крутиться сервер. Новый пользователь нужен для того, чтобы недруги не смогли выполнить код, который сами загрузят. Поэтому командой `umask 555` задаем настройку прав доступа, выдаваемых всем новым файлам, которые будет создавать наш юзер. `555` это `777 XOR 222`, следовательно дефолтные биты будут выставлены, как если бы мы каждому новому файлу вручную задавали `chmod 222` (разрешена только запись).
  3. Запускаем сервер и тестируем.
  4. **???????**
  5. PROFIT

Доступные методы: `GET`, `POST`, `PUT`.

# Nginx
Ну и куда же без *the High-Performance Web Server and Reverse Proxy*? Благо, на большинстве Linux-дистрибутивах *Nginx* предустановлен, поэтому настроить и развернуть его можно в считанные минуты.

На скриншоте ниже (кликабельно) можно видеть все шаги настройки сервера: предварительная настройка на панели сверху, тесты — снизу.

[![simple-http-servers-nginx.png]({{ "/img/simple-http-servers-nginx.png" | relative_url }})]({{ "/img/simple-http-servers-nginx.png" | relative_url }})

Что происходит здесь:
  1. Создаем необходимые директории и конфигурацию сервера по образцу из `default`'а (содержимое конфига есть ниже).
  2. Делаем конфиг активным (симлинк в `/etc/nginx/sites-enabled/`)
  3. Перезапускаем службу `nginx`, проверяем ее активность и тестируем сервер.
  4. **???????**
  5. PROFIT

Файл с конфигом:
```text
root@kali:~# cat /etc/nginx/sites-available/file_upload
server {
	listen 8881 default_server;
	server_name snovvcrash.top;
	location / {
		root                  /var/www/uploads;
		dav_methods           PUT;
		create_full_put_path  on;
    		dav_access            group:rw all:r;
	}
}
```

Как напользовались, не забываем остановить сервер:
```text
root@kali:~# systemctl stop nginx
```

Доступные методы: `GET`, `PUT`.
