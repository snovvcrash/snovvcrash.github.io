---
layout: post
title: "Pretending to Be smbpasswd with impacket"
date: 2020-10-31 19:00:00 +0300
author: snovvcrash
tags: [notes, hackthebox, machine, windows, null-session, smb, dcerpc, ms-samr, wireshark, smbpasswd, smbclient.py, rpcclient, chgpassworduser2, python, impacket, password-policies]
---

For me the most interesting aspect of pwning the Fuse machine from HTB was dealing with an expired domain user password. I found no other tools except smbpasswd to invoke such a password change remotely from Linux which seemed odd to me. So I decided to create a simple Python script with impacket which binds to the \samr pipe over SMB (MSRPC-SAMR) with a null session and calls SamrUnicodeChangePasswordUser2 to trigger the password change.

<!--cut-->

<p align="right">
	<a href="https://www.hackthebox.eu/home/machines/profile/256"><img src="https://img.shields.io/badge/%e2%98%90-Hack%20The%20Box-8ac53e?style=flat-square" alt="htb-badge.svg" /></a>
	<span class="score-medium">5.6/10</span>
</p>

![banner.png](/assets/images/htb/machines/fuse/banner.png)
{:.center-image}

![info.png](/assets/images/htb/machines/fuse/info.png)
{:.center-image}

* TOC
{:toc}

# Change Password over SMB

There is a user `tlavel` with an expired password `Fabricorp01`. When trying to connect to an SMB resource (at FUSE.FABRICORP.LOCAL) [STATUS_PASSWORD_MUST_CHANGE (0xC0000224)](https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-cifs/8f11e0f3-d545-46cc-97e6-f00569e3e1bc) error is raised:

[![cme_status_password_must_change.png](/assets/images/htb/machines/fuse/cme_status_password_must_change.png)](/assets/images/htb/machines/fuse/cme_status_password_must_change.png)
{:.center-image}

One way to get out of this situation remotely from Linux is to use this `smbpasswd` tool:

```
$ smbpasswd -r fuse.fabricorp.local -U 'tlavel'
Old SMB password: Fabricorp01
New SMB password: snovvcrash1!
Retype new SMB password: snovvcrash1!
```

[![smbpasswd.png](/assets/images/htb/machines/fuse/smbpasswd.png)](/assets/images/htb/machines/fuse/smbpasswd.png)
{:.center-image}

Under the hood it will try to authenticate as `tlavel:Fabricorp01` (red block in the Wireshark capture) and when it fails because of the above mentioned error, [it will initiate a null session](https://github.com/samba-team/samba/blob/08867de2efde05e4730b41a335d13f775e44e397/source3/libsmb/passchange.c#L113-L117) and call [SamrUnicodeChangePasswordUser2 (55)](https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-samr/acb3204a-da8b-478e-9139-1ea589edb880) function via DCE/RPC over [MS-SAMR](https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-samr/4df07fab-1bbc-452f-8e92-7853a3c7e380) protocol to change `tlavel`'s password (green block in the Wireshark capture):

[![smbpasswd_wireshark.png](/assets/images/htb/machines/fuse/smbpasswd_wireshark.png)](/assets/images/htb/machines/fuse/smbpasswd_wireshark.png)
{:.center-image}

So, let's say I'm annoyed with all this secure-interactive-input stuff like in smbpasswd and I want to be able to do the same thing in one line with password values passed as CLI arguments. When I try to achieve this with rpcclient and null authentication, I shall fail:

```
$ rpcclient -U'%' -c'chgpasswd2 tlavel Fabricorp01 snovvcrash1!' fuse.fabricorp.local
```

[![rpcclient_nt_status_access_denied.png](/assets/images/htb/machines/fuse/rpcclient_nt_status_access_denied.png)](/assets/images/htb/machines/fuse/rpcclient_nt_status_access_denied.png)
{:.center-image}

It's no secret that rpcclient [does a bad job when dealing with null session requests](https://sensepost.com/blog/2018/a-new-look-at-null-sessions-and-user-enumeration/). Long story short, after successfully binding to the `IPC$` share and creating `\samr` pipe, it makes a bunch of undesirable requests (red block in the Wireshark capture) which it does not really have permissions for within a null session and eventually dies with `NT_STATUS_ACCESS_DENIED`.

[![rpcclient_wireshark.png](/assets/images/htb/machines/fuse/rpcclient_wireshark.png)](/assets/images/htb/machines/fuse/rpcclient_wireshark.png)
{:.center-image}

Another way to try a password change over SMB is the impacket's smbclient.py [password](https://github.com/SecureAuthCorp/impacket/blob/a1a8d470319c73eba729d9b51969e94d7621c4e2/impacket/examples/smbclient.py#L107) functionality, but it will not work when the password is expired either:

```
$ smbclient.py 'tlavel:Fabricorp01@10.10.10.193'
```

[![smbclientpy_status_password_must_change.png](/assets/images/htb/machines/fuse/smbclientpy_status_password_must_change.png)](/assets/images/htb/machines/fuse/smbclientpy_status_password_must_change.png)
{:.center-image}

Same story with Samba's [NetCommand](https://www.samba.org/samba/docs/old/Samba3-HOWTO/NetCommand.html):

```
$ net rpc password tlavel 'snovvcrash1!' -S FUSE -U 'tlavel'%'Fabricorp01'
session setup failed: NT_STATUS_PASSWORD_MUST_CHANGE
Failed to set password for 'tlavel' with error: Failed to connect to IPC$ share on FUSE.
```

That's not what we want, so we can create a super simple Python script using impacket to initiate a null session and then change `tlavel`'s password directly with one single call to [hSamrUnicodeChangePasswordUser2](https://github.com/SecureAuthCorp/impacket/blob/2126aa130c26af96301cc6ce00230d1c41ee6809/impacket/dcerpc/v5/samr.py#L2774):

```python
#!/usr/bin/python2.7

from argparse import ArgumentParser

from impacket.dcerpc.v5 import transport, samr


def connect(host_name_or_ip):
	rpctransport = transport.SMBTransport(host_name_or_ip, filename=r'\samr')
	if hasattr(rpctransport, 'set_credentials'):
		rpctransport.set_credentials(username='', password='', domain='', lmhash='', nthash='', aesKey='') # null session

	dce = rpctransport.get_dce_rpc()
	dce.connect()
	dce.bind(samr.MSRPC_UUID_SAMR)

	return dce


def hSamrUnicodeChangePasswordUser2(username, oldpass, newpass, target):
	dce = connect(target)
	resp = samr.hSamrUnicodeChangePasswordUser2(dce, '\x00', username, oldpass, newpass)
	resp.dump()


parser = ArgumentParser()
parser.add_argument('username', help='username to change password for')
parser.add_argument('oldpass', help='old password')
parser.add_argument('newpass', help='new password')
parser.add_argument('target', help='hostname or IP')
args = parser.parse_args()

hSamrUnicodeChangePasswordUser2(args.username, args.oldpass, args.newpass, args.target)
```

Now we can trigger password change with a single command insecurely leaving all the sensitive information in `.bash_history`... Just as we've always wanted :expressionless:

```
$ ./smbpasswd.py tlavel Fabricorp01 'snovvcrash01!' FUSE.FABRICORP.LOCAL
```

[![smbpasswdpy.png](/assets/images/htb/machines/fuse/smbpasswdpy.png)](/assets/images/htb/machines/fuse/smbpasswdpy.png)
{:.center-image}

[![smbpasswdpy_wireshark.png](/assets/images/htb/machines/fuse/smbpasswdpy_wireshark.png)](/assets/images/htb/machines/fuse/smbpasswdpy_wireshark.png)
{:.center-image}

Later on I groomed up the code a little and made a [pull request](https://github.com/SecureAuthCorp/impacket/pull/918) to the impacket's master branch.

# Password Policies Notes

There is a couple of points to be cleared:

1\. From now on **both** passwords will be valid [for approximately one hour after the password change](https://www.ibm.com/support/knowledgecenter/SSPREK_9.0.6/com.ibm.isam.doc/wrp_config/reference/ref_pw_change_issue_ad_win.html). If I try to authorize with the old `Fabricorp01` password after the change was made, it actually works and the new `snovvcrash01!` password is valid too:

[![both_passwords_are_valid.png](/assets/images/htb/machines/fuse/both_passwords_are_valid.png)](/assets/images/htb/machines/fuse/both_passwords_are_valid.png)
{:.center-image}

2\. There is a scheduled task which reverts the password back to `Fabricorp01` every 1 minute:

[![schtasks.png](/assets/images/htb/machines/fuse/schtasks.png)](/assets/images/htb/machines/fuse/schtasks.png)
{:.center-image}

3\. If I try to change the password two times in a row but before it was reverted to default `Fabricorp01` by the scheduler task (`Fabricorp01` ⟶ `snovvcrash01!` ⟶ `snovvcrash02!`), it fails due to the *minimum password age policy* (1 day):

[![minimum_password_age_policy.png](/assets/images/htb/machines/fuse/minimum_password_age_policy.png)](/assets/images/htb/machines/fuse/minimum_password_age_policy.png)
{:.center-image}

[![minimum_password_age_policy_effect.png](/assets/images/htb/machines/fuse/minimum_password_age_policy_effect.png)](/assets/images/htb/machines/fuse/minimum_password_age_policy_effect.png)
{:.center-image}

4\. If I try to set the same password again after it was reverted to default `Fabricorp01` by the scheduler task (`Fabricorp01` ⟶ `snovvcrash01!` ⟶ `Fabricorp01` ⟶ `snovvcrash01!`), it fails due to the *enforce password history policy* (24 passwords):

[![enforce_password_history_policy.png](/assets/images/htb/machines/fuse/enforce_password_history_policy.png)](/assets/images/htb/machines/fuse/enforce_password_history_policy.png)
{:.center-image}

[![enforce_password_history_policy_effect.png](/assets/images/htb/machines/fuse/enforce_password_history_policy_effect.png)](/assets/images/htb/machines/fuse/enforce_password_history_policy_effect.png)
{:.center-image}

Cheers and happy hacking!
