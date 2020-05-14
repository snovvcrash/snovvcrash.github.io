---
layout: post
title: "Об обнаружении субдоменов"
date: 2020-05-10 22:00:00 +0300
author: snovvcrash
categories: /pentest
tags: [notes, external-pentest, osint, dns-enumeration, subdomain-discovery, amass, knockpy, altdns, massdns, methodology]
comments: true
published: true
---

Инструментарий и краткая методика для обнаружения субдоменов при проведении внешнего пентеста / анализа веб-приложений / конкурентной разведки.

<!--cut-->

![banner.png](/assets/images/subdomain-discovery/banner.png)
{:.center-image}

* TOC
{:toc}

# Amass

[Amass](https://github.com/OWASP/Amass) — инструмент проекта OWASP, предназначенный для сбора информации об объекте при проведении внешней разведки. Включает в себя несколько модулей, однако для нас полезнее всего модуль `enum`, который позволяет использовать пассивные (опрос поисковиков и различных агрегаторов) и активные (трансфер зоны NS-серверов, брутфорс) техники для обнаружения субдоменов.

## Установка

Amass написан на Golang, поэтому можно забрать готовый исполняемый файл [из релизов](https://github.com/OWASP/Amass/releases) и просто распаковать его у себя на машине:

```
$ wget https://github.com/OWASP/Amass/releases/download/v3.5.4/amass_v3.5.4_linux_amd64.zip -O ~/tools/amass.zip
$ cd ~/tools
$ unzip amass.zip && rm amass.zip && mv amass* amass
$ cd -
$ ln -s ~/tools/amass/amass /usr/local/bin/amass
```

## Настройка

Как и `recon-ng`, Amass использует некоторые сервисы (Shodan, Censys, SecurityTrails, VirusTotal и др.), требущие для работы API-ключ, поэтому сперва нужно создать конфигурационный файл:

```
# Provide API key information for a data source

[Censys]
apikey = <REDACTED>
secret = <REDACTED>

[GitHub]
apikey = <REDACTED>

[SecurityTrails]
apikey = <REDACTED>

[Shodan]
apikey = <REDACTED>

[VirusTotal]
apikey = <REDACTED>
```

Полный образец конфига можно найти [здесь](https://github.com/OWASP/Amass/blob/master/examples/config.ini). В нем очень много доступных настроек, однако все они могут быть заданы в виде аргументов командной строки, что является более гибким вариантом, поэтому в файле настроек я оставил только API-токены.

## Использование

Для примера соберем информацию о домене `zonetransfer.me`:

```
$ amass enum -v -df root-domains.txt -blf blacklisted-subdomains.txt -nf known-subdomains.txt -ipv4 -src -oA amass/out/subdomains.txt -config amass/config.ini -active -brute
```

Я остановился на использовании такого набора параметров. Вот, что они значат:

* `-v` — более подробный вывод;
* `-df <STRING>` — путь к текстовому файлу, содержащему список корневых доменов для анализа;
* `-blf <STRING>` — путь к текстовому файлу, содержащему список субдоменов, которые следует исключить из скоупа анализа;
* `-nf <STRING>` — путь к текстовому файлу, содержащему список субдоменов, о которых у пентестера уже есть информация (для них будет пропущен ряд процедур поиска);
* `-ipv4` — для каждого обнаруженного доменного имени показывать его IPv4-адрес;
* `-src` — для каждого обнаруженного доменного имени показывать источник, откуда была получена эта информация;
* `-oA <STRING>` — путь для сохранения результатов сканирования (форматы: `txt`, `json`);
* `-config <STRING>` — путь к файлу конфигурации;
* `-active` — использовать актиное сканирование (AXFR-запросы);
* `-brute` — использовать брутфорс субдоменов.

Последние два флага использовать с осторожностью, т. к. это может привлечь дополнительное внимание.

Также для некоторых флагов есть аналоги, не требующие создание файлов для входных значений. Удобно, когда целей для сканирования немного:

```
$ amass enum -v -d hackerone.com -bl xyz.hackerone.com -ipv4 -src -oA amass/out/subdomains.txt -config amass/config.ini -active -brute
```

### Пример

Для примера соберем информацию о субдоменах ресурса `zonetranfer.me`, уязвимого к трансферу зоны:

```
$ amass enum -v -d zonetransfer.me -ipv4 -src -o amass/out/subdomains.txt -config amass/config.ini -active -brute
```

![amass-1.png](/assets/images/subdomain-discovery/amass-1.png)
{:.center-image}

![amass-2.png](/assets/images/subdomain-discovery/amass-2.png)
{:.center-image}

Если запросить трансфер зоны напрямую с помощью `dig`, можно видеть, что Amass не обнаружил все записи NS-сервера `nsztm1.digi.ninja`, поэтому есть необходимость в дополнительной утилите для автоматизации zone transfer:

```
$ dig zonetransfer.me ns
$ dig axfr @nsztm1.digi.ninja zonetransfer.me
```

![dig-ns.png](/assets/images/subdomain-discovery/dig-ns.png)
{:.center-image}

![dig-axfr.png](/assets/images/subdomain-discovery/dig-axfr.png)
{:.center-image}

## Полезные ссылки

* [Amass/user_guide.md at master · OWASP/Amass](https://github.com/OWASP/Amass/blob/master/doc/user_guide.md)

# Knockpy

[Knockpy](https://github.com/guelfoweb/knock) — инструмент, который отлично справляется с проверкой возможности выгрузки зон DNS и автоматически делает это, если ответ положителен. Также умеет брутить субдомены по словарю, что относит его к категории «активных» энумеров.

## Установка

Knockpy написан на Python (требует v2.7.6), поэтому для установки нужно клонировать репозиторий и запустить `setup.py`:

```
$ git clone https://github.com/guelfoweb/knock ~/tools/knock
$ cd ~/tools/knock
$ sudo python -m pip install -r requirements.txt
$ sudo python setup.py install
$ cd -
```

## Использование

Пользоваться просто, как три копейки: указываем целевой домен в позиционном аргументе, и, при желании, кастомный словарь для перебора через флаг `-w` (но мы этого делать не будем):

```
$ knockpy hackerone.com
```

### Пример

Пробуем на примере того же самого `zonetransfer.me`, который разрешают легально сканировать и зонтрансферить:

```
$ knockpy zonetransfer.me
```

![knockpy.png](/assets/images/subdomain-discovery/knockpy.png)
{:.center-image}

После обнаружения трансфера зоны и ее выгрузки, предлагаю насильно остановить процесс через `^C`, потому что брутить субдомены можно более эффективно (см. следующий параграф). Полученные записи нужно вручную добавить в текстовый файл с результатами.

# MassDNS

Следующим шагом может стать валидация того факта, что все полученные субдомены живы и резолвятся. Для этого эффективно использовать [MassDNS](https://github.com/blechschmidt/massdns), ведь, по словам разработчика:

> MassDNS is capable of resolving over 350,000 names per second using publicly available resolvers...

## Установка

Проект написан на C, поэтому клонируем исходники и компилируем бинарник:

```
$ git clone https://github.com/blechschmidt/massdns ~/tools/massdns
$ cd ~/tools/massdns
$ make
$ cd -
$ ln -s ~/tools/massdns/bin/massdns /usr/local/bin/massdns
```

## Использование

Чтобы просто резолвить все записи DNS из собранного списка, можно использовать комманду такого вида:

```
$ massdns -r ~/tools/massdns/lists/resolvers.txt -s 15000 -t A -o S -w massdns-a.txt subdomains.txt
```

* `-r <STRING>` — путь к текстовому файлу, содержащему список резолверов;
* `-s <VALUE>` — интенсивность сканирования, кол-во одновременных запросов;
* `-t <VALUE>` — тип записи, который нужно спрашивать у DNS-сервера;
* `-o <VALUE>` — формат вывода, `S` для простого текстового файла;
* `-w <STRING>` — путь для сохранения результатов сканирования;
* `<STRING>` — путь к текстовому файлу, содержащему список субдоменов для сканирования.

Брутить же субдомены можно так:

```
$ ~/tools/massdns/scripts/subbrute.py /usr/share/commonspeak2/subdomains/subdomains.txt hackerone.com |massdns -r ~/tools/massdns/lists/resolvers.txt -t A -o S -w results.txt
```

Хороший словарь есть в коллекции [commonspeak2-wordlists](https://github.com/assetnote/commonspeak2-wordlists):

```
$ git clone https://github.com/assetnote/commonspeak2-wordlists /usr/share/commonspeak2
```

### Пример

```
$ massdns -r ~/tools/massdns/lists/resolvers.txt -s 15000 -t A -o S -w massdns-a.txt subdomains.txt
```

![massdns-resolve.png](/assets/images/subdomain-discovery/massdns-resolve.png)
{:.center-image}

# Altdns

При совсем жестком недостатке результатов, полученных на предыдущих этапах, можно подключить утилиту [Altdns](https://github.com/infosec-au/altdns), которая генерирует на лету различные мутации субдоменов из предложенного словаря и опционально проверяет их существование.

## Установка

Устанавливается через PyPI на вторую версию Python:

```
$ sudo python -m pip install py-altdns
```

Отдельно скачаем словарь для мутаций:

```
$ mkdir altdns
$ wget https://raw.githubusercontent.com/infosec-au/altdns/master/words.txt -O altdns/words.txt
```

## Использование

```
$ altdns -i subdomains.txt -o data_output -w words.txt -r -s results_output.txt
```

* `-i <STRING>` — путь к текстовому файлу, содержащему список известных существующих субдоменов (цели);
* `-o <STRING>` — путь к текстовому файлу, в который сохранятся все мутации;
* `-w <STRING>` — путь к текстовому файлу, содержащему список слов, на основе которых будут мутировать субдомены;
* `-r` — осуществлять резолв по генерируемому списку;
* `-s <STRING>` — путь к текстовому файлу для сохранения результатов.

Лучше не использовать флаг `-r`, а сгенерировать список мутировавших субдоменов и проверить их существование с помощью massdns.

## Пример

```
$ altdns -i subdomains.txt -o subdomains-mutated.txt -w altdns/words.txt
$ massdns -r ~/tools/massdns/lists/resolvers.txt -s 15000 -t A -o S -w massdns-a-mutated.txt subdomains-mutated.txt
```

![massdns-resolve-mutated.png](/assets/images/subdomain-discovery/massdns-resolve-mutated.png)
{:.center-image}

Следует иметь в виду, что некоторые резолверы из дефолтного списка massdns отдают устаревшую/некорректную информацию (видно на скриншоте), поэтому лучше всегда перепроверять информацию.

Список публично доступных (бесплатных) DNS-серверов для России можно найти на [public-dns.info](https://public-dns.info/nameserver/ru.html).

# Дополнительные способы

Еще один очень известный брутер:

* [TheRook/subbrute: A DNS meta-query spider that enumerates DNS records, and subdomains.](https://github.com/TheRook/subbrute)

Асинхронный DNS-брутфорсер:

* [blark/aiodnsbrute: Python 3.5+ DNS asynchronous brute force utility](https://github.com/blark/aiodnsbrute)

Как заОСИНТить DNS с AWS за $0.02:

* [Rapid7 Open Data and AWS: Conducting DNS Reconnaissance](https://blog.rapid7.com/2018/10/16/how-to-conduct-dns-reconnaissance-for-02-using-rapid7-open-data-and-aws/)

Если речь идет о брутфорсе виртуальных хостов (aka Virtual Host Routing), то можно:

1\. Фаззить заголовок Host и анализировать ответы сервера с помощью [wfuzz](https://github.com/xmendez/wfuzz):

```
$ wfuzz -H 'Host: FUZZ.example.local' -u 'http://example.local/' -w /usr/share/seclists/Discovery/DNS/shubs-subdomains.txt --hc 400 --hh 0
```

2\. Использовать тулзу [vhostbrute](https://github.com/allyshka/vhostbrute).

В Nmap NSE есть скрипт для брутфорса DNS:

```
$ nmap --script dns-brute --dns-servers ns.example.com example.com
```

Также домены можно брутить с помощью известного [gobuster](https://github.com/OJ/gobuster):

```
$ gobuster dns -d hackerone.com -i -w /usr/share/commonspeak2/subdomains/subdomains.txt
```

![gobuster-dns.png](/assets/images/subdomain-discovery/gobuster-dns.png)
{:.center-image}

А еще использовать гугл дорки:

```
site:*.hackerone.com -www
site:*.*.hackerone.com
site:hackerone.com inurl:login,register,upload,logout,redirect,redir,goto,admin
```

И онлайн-сервисы:

* [Find Subdomains Online / Pentest-Tools.com](https://pentest-tools.com/information-gathering/find-subdomains-of-domain)
* [Find DNS Host Records / Subdomain Finder / HackerTarget.com](https://hackertarget.com/find-dns-host-records/)
* [Subdomain finder and subdomain Enumerating tools online](https://www.nmmapper.com/sys/tools/subdomainfinder/)
* [DNSdumpster.com - dns recon and research, find and lookup dns records](https://dnsdumpster.com/)

# Методика

В конечном итоге вырисовывается такая методика обнаружения субдоменов:

1. Пассивное обнаружение:
	* Amass
	* Гугл дорки
	* [dnsdumpster.com](https://dnsdumpster.com/)
2. Активное обнаружение:
	* Knockpy (AXFR)
	* massdns (Brute)
	* *[опц.]* AltDNS + massdns (Permutate & Brute)
3. Проверка резолва:
	* massdns (Resolve)

# Полезные ссылки

* [PayloadsAllTheThings/Subdomains Enumeration.md at master · swisskyrepo/PayloadsAllTheThings](https://github.com/swisskyrepo/PayloadsAllTheThings/blob/master/Methodology%20and%20Resources/Subdomains%20Enumeration.md)
* [Top 7 Subdomain Scanner tools to find subdomains](https://securitytrails.com/blog/subdomain-scanner-find-subdomains)
* [Subdomain Enumeration: 2019 Workflow](https://0xpatrik.com/subdomain-enumeration-2019/)
