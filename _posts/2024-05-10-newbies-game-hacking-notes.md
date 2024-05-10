---
layout: post
title: "Newbie's Game Hacking Notes (ft. Turbo Overkill)"
date: 2024-05-10 00:00:00 +0300
author: snovvcrash
tags: [game-hacking, cheat-engine, cheat-developement, trainer-developement, dll-injection]
---

A terse-comments blog of making myself more comfortable with Cheat Engine and the basics of cheats/trainers developement. Practice is based on the awesome Turbo Overkill FPS (v1.35).

<!--cut-->

![banner.png](/assets/images/newbies-game-hacking-notes/banner.png)
{:.center-image}

<p align="center">
  <iframe src="https://store.steampowered.com/widget/1328350/" frameborder="0" width="646" height="190"></iframe>
</p>

* TOC
{:toc}

# Infinite Ammo

An example for [Uzis](https://turbo-overkill.fandom.com/wiki/Uzis):

1. **"First Scan"**: value of the current ammo counter.
2. Shoot!
3. **"Next Scan"**: value of the updated ammo counter. Repeat 1-3 until you're confident in the match.
4. **"Add selected addresses to the addresslist"**.
5. **"Find out what writes to this address"**.
6. Shoot!
7. **"Show this address in the dissasembler"**.
8. Search for code that writes to this address (it probably dereference a pointer with `[]`).
9. **"Tools"** → **"Auto Assemble"** → **"Template"** → **"AOB (Array of Bytes) Injection"**:

```actionscript
{ Game   : Turbo Overkill.exe
  Version: 
  Date   : 2024-05-04
  Author : snovvcrash

  This script gives infinite Uzis ammo
}

[ENABLE]

aobscanmodule(INF_AMMO_UZIS,GameAssembly.dll,89 5F 30 0F 84 46 FF FF FF) // should be unique
alloc(newmem,$1000,INF_AMMO_UZIS)

label(code)
label(return)

newmem:

code:
  //mov [rdi+30],ebx       // original
  //mov [rdi+30],00000258  // patched: set ammo to 600 (0x258)
  push rbx
  mov ebx,[rax+08]
  mov [rdi+30],ebx
  pop rbx
  je GameAssembly.dll+3D7CFC
  jmp return

INF_AMMO_UZIS:
  jmp newmem
  nop 4
return:
registersymbol(INF_AMMO_UZIS)

[DISABLE]

INF_AMMO_UZIS:
  db 89 5F 30 0F 84 46 FF FF FF

unregistersymbol(INF_AMMO_UZIS)
dealloc(newmem)

{
// ORIGINAL CODE - INJECTION POINT: GameAssembly.dll+3D7DAD

GameAssembly.dll+3D7D91: 2B DE                 - sub ebx,esi
GameAssembly.dll+3D7D93: 48 8B 80 B8 00 00 00  - mov rax,[rax+000000B8]
GameAssembly.dll+3D7D9A: 8B 48 08              - mov ecx,[rax+08]
GameAssembly.dll+3D7D9D: 78 08                 - js GameAssembly.dll+3D7DA7
GameAssembly.dll+3D7D9F: 3B D9                 - cmp ebx,ecx
GameAssembly.dll+3D7DA1: 7E 06                 - jle GameAssembly.dll+3D7DA9
GameAssembly.dll+3D7DA3: 8B D9                 - mov ebx,ecx
GameAssembly.dll+3D7DA5: EB 02                 - jmp GameAssembly.dll+3D7DA9
GameAssembly.dll+3D7DA7: 33 DB                 - xor ebx,ebx
GameAssembly.dll+3D7DA9: 80 7F 64 00           - cmp byte ptr [rdi+64],00
// ---------- INJECTING HERE ----------
GameAssembly.dll+3D7DAD: 89 5F 30              - mov [rdi+30],ebx
// ---------- DONE INJECTING  ----------
GameAssembly.dll+3D7DB0: 0F 84 46 FF FF FF     - je GameAssembly.dll+3D7CFC
GameAssembly.dll+3D7DB6: 3B 5F 68              - cmp ebx,[rdi+68]
GameAssembly.dll+3D7DB9: 0F 8D 3D FF FF FF     - jnl GameAssembly.dll+3D7CFC
GameAssembly.dll+3D7DBF: C6 47 64 00           - mov byte ptr [rdi+64],00
GameAssembly.dll+3D7DC3: E9 0D FF FF FF        - jmp GameAssembly.dll+3D7CD5
GameAssembly.dll+3D7DC8: 8B 5F 34              - mov ebx,[rdi+34]
GameAssembly.dll+3D7DCB: 3B DE                 - cmp ebx,esi
GameAssembly.dll+3D7DCD: 0F 8C FF 01 00 00     - jl GameAssembly.dll+3D7FD2
GameAssembly.dll+3D7DD3: 48 8B 05 36 CE 06 02  - mov rax,[GameAssembly.dll+2444C10]
GameAssembly.dll+3D7DDA: 83 B8 E0 00 00 00 00  - cmp dword ptr [rax+000000E0],00
}
```

Discover max ammo values of all the weapons:

1. **"Set breakpoint (Hardware Breakpoint)"** on `mov ecx,[rax+08]`. `RAX` probably points to a value of a structure with weapons stats.
2. Shoot!
3. Examine the value of `RAX`.
4. **"Tools"** → **"Dissect data/structures"** → Value of `RAX`.
5. **"Structures"** → **"Define new structure"**.

[![weapons-stats-structure.png](/assets/images/newbies-game-hacking-notes/weapons-stats-structure.png)](/assets/images/newbies-game-hacking-notes/weapons-stats-structure.png)
{:.center-image}

Repeat the algorithm to create a script for any weapon changing the offsets to current and max ammo values.

[![uzis-infinite-ammo-demo.gif](/assets/images/newbies-game-hacking-notes/uzis-infinite-ammo-demo.gif)](/assets/images/newbies-game-hacking-notes/uzis-infinite-ammo-demo.gif)
{:.center-image}

Click to expand
{:.quote}

## !Refs

- [Absolute beginner: Your first ammo script - FearLess Cheat Engine](https://fearlessrevolution.com/viewtopic.php?t=4113)
- [How to Make a Trainer with Cheat Engine [HuniePop Trainer Example] - YouTube](https://youtu.be/uiX1eQhSboE?si=fjmjYvGan-uJ0Dil)

# Movement Hacks

## Infinite Jumps

To get infinite jumps I'll make an assumption that there is a byte counter which can take values `0-2`:

1. **"First Scan"**: `0`.
2. Single jump.
3. **"Next Scan"**: `1`.
4. Double jump.
5. **"Next Scan"**: `2`. Repeat 1-5 until you're confident in the match.
6. **"Find out what writes to this address"** → **"Show this address in the dissasembler"**.

We probably want to look for `INC` instruction and, for example, patch it to `NOP`:

```actionscript
{ Game   : Turbo Overkill
  Version: 
  Date   : 2024-05-03
  Author : snovvcrash

  This script gives infinite jumps
}

[ENABLE]

aobscanmodule(NOPs,GameAssembly.dll,FF 83 84 01 00 00) // should be unique
alloc(newmem,$1000,NOPs)

label(code)
label(return)

newmem:

code:
  //inc [rbx+00000184]
  jmp return

NOPs:
  jmp newmem
  nop
return:
registersymbol(NOPs)

[DISABLE]

NOPs:
  db FF 83 84 01 00 00

unregistersymbol(NOPs)
dealloc(newmem)

{
// ORIGINAL CODE - INJECTION POINT: GameAssembly.dll+3F31BF

GameAssembly.dll+3F3196: 33 D2                 - xor edx,edx
GameAssembly.dll+3F3198: 48 8B C8              - mov rcx,rax
GameAssembly.dll+3F319B: E8 20 34 FB FF        - call GameAssembly.dll+3A65C0
GameAssembly.dll+3F31A0: 80 BB 5C 01 00 00 00  - cmp byte ptr [rbx+0000015C],00
GameAssembly.dll+3F31A7: 75 1C                 - jne GameAssembly.dll+3F31C5
GameAssembly.dll+3F31A9: 48 8B 43 18           - mov rax,[rbx+18]
GameAssembly.dll+3F31AD: 48 85 C0              - test rax,rax
GameAssembly.dll+3F31B0: 0F 84 99 02 00 00     - je GameAssembly.dll+3F344F
GameAssembly.dll+3F31B6: 80 B8 13 01 00 00 00  - cmp byte ptr [rax+00000113],00
GameAssembly.dll+3F31BD: 75 06                 - jne GameAssembly.dll+3F31C5
// ---------- INJECTING HERE ----------
GameAssembly.dll+3F31BF: FF 83 84 01 00 00     - inc [rbx+00000184]
// ---------- DONE INJECTING  ----------
GameAssembly.dll+3F31C5: 48 8B 4B 48           - mov rcx,[rbx+48]
GameAssembly.dll+3F31C9: 48 85 C9              - test rcx,rcx
GameAssembly.dll+3F31CC: 0F 84 7D 02 00 00     - je GameAssembly.dll+3F344F
GameAssembly.dll+3F31D2: 33 D2                 - xor edx,edx
GameAssembly.dll+3F31D4: E8 F7 D9 70 01        - call GameAssembly.dll+1B00BD0
GameAssembly.dll+3F31D9: 84 C0                 - test al,al
GameAssembly.dll+3F31DB: 0F 85 85 00 00 00     - jne GameAssembly.dll+3F3266
GameAssembly.dll+3F31E1: 38 05 F3 F8 18 02     - cmp [GameAssembly.dll+2582ADA],al
GameAssembly.dll+3F31E7: 8B BB 84 01 00 00     - mov edi,[rbx+00000184]
GameAssembly.dll+3F31ED: 75 13                 - jne GameAssembly.dll+3F3202
}
```

[![infinite-jumps-demo.gif](/assets/images/newbies-game-hacking-notes/infinite-jumps-demo.gif)](/assets/images/newbies-game-hacking-notes/infinite-jumps-demo.gif)
{:.center-image}

Click to expand
{:.quote}

## Infinite Dashes

To get infinite dashes I'll make an assumption that there is a (float) "dash recharge" value which probably resides nearby the jump counter. I will extract .NET assemblies from the [IL2CPP](http://blogs.unity3d.com/2015/05/06/an-introduction-to-ilcpp-internals/) **GameAssembly.dll** with [Il2CppDumper](https://github.com/Perfare/Il2CppDumper) and open **Assembly-CSharp.dll** in [dnSpy](https://github.com/dnSpy/dnSpy).

Searching for "dash" gives me `dashRechargeDelay` field with the offset of `0xF4`. In the same time, the `jumpCount` has the offset of `0x184`.

[![player-movement-values.gif](/assets/images/newbies-game-hacking-notes/player-movement-values.gif)](/assets/images/newbies-game-hacking-notes/player-movement-values.gif)
{:.center-image}

Click to expand
{:.quote}

I'll calculate the address of `dashRechargeDelay` relative to `jumpCount` as:

```python
>>> hex(0x26836B266C4-0x184+0xf4)
'0x26836b26634'
```

Now **"Find out what accesses this address"** and setting the recharge value to `0` gives me infinite dashes:

```actionscript
{ Game   : Turbo Overkill
  Version: 
  Date   : 2024-05-06
  Author : snovvcrash

  This script gives infinite dashes
}

[ENABLE]

aobscanmodule(INF_DASHES,GameAssembly.dll,F3 0F 11 83 F4 00 00 00 0F) // should be unique
alloc(newmem,$1000,INF_DASHES)

label(code)
label(return)

newmem:

code:
  //movss [rbx+000000F4],xmm0
  mov [rbx+000000F4],0
  jmp return

INF_DASHES:
  jmp newmem
  nop 3
return:
registersymbol(INF_DASHES)

[DISABLE]

INF_DASHES:
  db F3 0F 11 83 F4 00 00 00

unregistersymbol(INF_DASHES)
dealloc(newmem)

{
// ORIGINAL CODE - INJECTION POINT: GameAssembly.dll+3EF4C7

GameAssembly.dll+3EF499: 48 85 C9                 - test rcx,rcx
GameAssembly.dll+3EF49C: 0F 84 E8 02 00 00        - je GameAssembly.dll+3EF78A
GameAssembly.dll+3EF4A2: 48 8B 15 C7 AC 02 02     - mov rdx,[GameAssembly.dll+241A170]
GameAssembly.dll+3EF4A9: 45 33 C0                 - xor r8d,r8d
GameAssembly.dll+3EF4AC: E8 3F DB FE FF           - call GameAssembly.dll+3DCFF0
GameAssembly.dll+3EF4B1: 84 C0                    - test al,al
GameAssembly.dll+3EF4B3: 74 0A                    - je GameAssembly.dll+3EF4BF
GameAssembly.dll+3EF4B5: F3 0F 10 05 33 BC 8F 01  - movss xmm0,[GameAssembly.dll+1CEB0F0]
GameAssembly.dll+3EF4BD: EB 08                    - jmp GameAssembly.dll+3EF4C7
GameAssembly.dll+3EF4BF: F3 0F 10 05 E5 B8 8F 01  - movss xmm0,[GameAssembly.dll+1CEADAC]
// ---------- INJECTING HERE ----------
GameAssembly.dll+3EF4C7: F3 0F 11 83 F4 00 00 00  - movss [rbx+000000F4],xmm0
// ---------- DONE INJECTING  ----------
GameAssembly.dll+3EF4CF: 0F 2F BB F0 00 00 00     - comiss xmm7,[rbx+000000F0]
GameAssembly.dll+3EF4D6: 0F 87 E9 01 00 00        - ja GameAssembly.dll+3EF6C5
GameAssembly.dll+3EF4DC: 80 3D 07 2F 19 02 00     - cmp byte ptr [GameAssembly.dll+25823EA],00
GameAssembly.dll+3EF4E3: 75 13                    - jne GameAssembly.dll+3EF4F8
GameAssembly.dll+3EF4E5: 48 8D 0D EC BA 03 02     - lea rcx,[GameAssembly.dll+242AFD8]
GameAssembly.dll+3EF4EC: E8 1F 89 E4 FF           - call GameAssembly.il2cpp_get_exception_argument_null+2A0
GameAssembly.dll+3EF4F1: C6 05 F2 2E 19 02 01     - mov byte ptr [GameAssembly.dll+25823EA],01
GameAssembly.dll+3EF4F8: 48 8B 05 D9 BA 03 02     - mov rax,[GameAssembly.dll+242AFD8]
GameAssembly.dll+3EF4FF: F3 0F 10 0D 25 BC 8F 01  - movss xmm1,[GameAssembly.dll+1CEB12C]
GameAssembly.dll+3EF507: 48 8B 88 B8 00 00 00     - mov rcx,[rax+000000B8]
}
```

[![infinite-dashes-demo.gif](/assets/images/newbies-game-hacking-notes/infinite-dashes-demo.gif)](/assets/images/newbies-game-hacking-notes/infinite-dashes-demo.gif)
{:.center-image}

Click to expand
{:.quote}

The same approach can be followed to enable/disable the God Mode:

```csharp
// Token: 0x020003C6 RID: 966
[Token(Token = "0x20003C6")]
public class Vitals : MonoBehaviourPun
{
    // ...
    // Token: 0x04001CF9 RID: 7417
    [Token(Token = "0x4001CF9")]
    [FieldOffset(Offset = "0x89")]
    public bool godMode;
    // ...
```

# From Cheat Engine to a Standalone DLL

Having got the appropriate offsets, I can implement the AOB injection logic within a simple standalone DLL in C.

Here's a PoC for toggling infinite jumps and dashes via `F11` and `F12` respectively:

```c
#include <windows.h>

typedef struct HookTrampolineBuffers
{
    BOOL enabled;
    BYTE originalBytes[10];
    BYTE patchBytes[10];
    DWORD originalBytesSize;
    UINT_PTR addressToHook;
} HookTrampolineBuffers;

UINT_PTR find_code_cave(UINT_PTR patchAddr)
{
    LPVOID alloc = NULL;
    UINT_PTR loaderAddress;
    BOOL foundMem = FALSE;

    for (loaderAddress = (patchAddr & 0xFFFFFFFFFFF70000) - 0x70000000;
        loaderAddress < patchAddr + 0x70000000;
        loaderAddress += 0x10000)
    {
        alloc = VirtualAlloc((LPVOID)loaderAddress, 0x1000, MEM_RESERVE|MEM_COMMIT, PAGE_EXECUTE_READWRITE);
        if (alloc == NULL) continue;
        foundMem = TRUE;
        break;
    }

    return foundMem ? (UINT_PTR)alloc : 0;
}

void init_trampoline(HookTrampolineBuffers* hook, UINT_PTR addressToHook, UINT_PTR jumpAddress)
{
    BYTE trampoline[10] = {
        0xE9, 0x00, 0x00, 0x00, 0x00,  // jmp rel32
        0x00, 0x00, 0x00, 0x00, 0x00
    };

    DWORD offset = jumpAddress - addressToHook - 5;
    memcpy(&trampoline[1], &offset, sizeof(offset));
    memset(&trampoline[5], 0x90, hook->originalBytesSize - 5);
    memcpy(hook->patchBytes, &trampoline, hook->originalBytesSize);
}

void init_hook(HookTrampolineBuffers* hook, BYTE* originalBytes, DWORD originalBytesSize, BYTE* extraBytes, DWORD extraBytesSize, DWORD offset)
{
    HMODULE hGameAssembly = GetModuleHandleA("GameAssembly.dll");

    hook->enabled = FALSE;
    hook->originalBytesSize = originalBytesSize;
    memcpy(hook->originalBytes, originalBytes, hook->originalBytesSize);
    UINT_PTR patchAddr = (UINT_PTR)hGameAssembly + offset;
    hook->addressToHook = patchAddr;

    UINT_PTR codeCave = find_code_cave(patchAddr);
    if (codeCave)
    {
        if (extraBytes)
            memcpy((BYTE*)codeCave, extraBytes, extraBytesSize);
        BYTE jmp[5] = {0xE9, 0x00, 0x00, 0x00, 0x00};
        DWORD ret = patchAddr - codeCave - extraBytesSize;
        memcpy(&jmp[1], &ret, sizeof(ret));
        memcpy((BYTE*)((PBYTE)codeCave + extraBytesSize), jmp, sizeof(jmp));
        init_trampoline(hook, patchAddr, codeCave);
    }
}

BOOL toggle_hook(HookTrampolineBuffers* hook)
{
    DWORD oldProtect;
    BOOL ret = FALSE;

    if (VirtualProtect(
        (LPVOID)(hook->addressToHook),
        hook->originalBytesSize,
        PAGE_EXECUTE_READWRITE,
        &oldProtect))
    {
        if (!hook->enabled)
            memcpy((BYTE*)(hook->addressToHook), hook->patchBytes, hook->originalBytesSize);
        else
            memcpy((BYTE*)(hook->addressToHook), hook->originalBytes, hook->originalBytesSize);

        ret = TRUE;
    }

    VirtualProtect((LPVOID)(hook->addressToHook), hook->originalBytesSize, oldProtect, &oldProtect);
    return ret;
}

DWORD WINAPI MainThread(LPVOID param)
{
    HookTrampolineBuffers infJumpsHook = { 0 };
    BYTE infJumpsOrigin[] = { 0xFF, 0x83, 0x84, 0x01, 0x00, 0x00 };
    DWORD infJumpsOffset = 0x3F31BF;
    init_hook(&infJumpsHook, infJumpsOrigin, sizeof(infJumpsOrigin), NULL, 0, infJumpsOffset);

    HookTrampolineBuffers infDashesHook = { 0 };
    BYTE infDashesOrigin[] = { 0xF3, 0x0F, 0x11, 0x83, 0xF4, 0x00, 0x00, 0x00 };
    BYTE zeroDashRechargeDelay[] = { 0xC7, 0x83, 0xF4, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 };
    DWORD infDashesOffset = 0x3EF4C7;
    init_hook(&infDashesHook, infDashesOrigin, sizeof(infDashesOrigin), zeroDashRechargeDelay, sizeof(zeroDashRechargeDelay), infDashesOffset);

    while (TRUE)
    {
        if ((GetAsyncKeyState(VK_F11) & 0x1) && toggle_hook(&infJumpsHook))
            infJumpsHook.enabled = !infJumpsHook.enabled;
        else if ((GetAsyncKeyState(VK_F12) & 0x1) && toggle_hook(&infDashesHook))
            infDashesHook.enabled = !infDashesHook.enabled;
        Sleep(5);
    }

    return 0;
}

BOOL APIENTRY DllMain(HANDLE hModule, DWORD ul_reason_for_call, LPVOID lpReserved)
{
    switch(ul_reason_for_call)
    {
        case DLL_PROCESS_ATTACH:
            CreateThread(0, 0, MainThread, hModule, 0, 0);
        case DLL_PROCESS_DETACH:
        case DLL_THREAD_ATTACH:
        case DLL_THREAD_DETACH:
            break;
    }

    return TRUE;
}
```

[![standalone-dll-demo.gif](/assets/images/newbies-game-hacking-notes/standalone-dll-demo.gif)](/assets/images/newbies-game-hacking-notes/standalone-dll-demo.gif)
{:.center-image}

Click to expand
{:.quote}

## !Refs

- [From Cheat Engine to a DLL - how to make a working game trainer in C [Game Hacking 101] - YouTube](https://youtu.be/QDOgJAvG9bQ?si=kpVEwl_eHm18eWvP)
