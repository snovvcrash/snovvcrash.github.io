---
layout: post
title: "Abusing Kerberos Constrained Delegation without Protocol Transition"
date: 2022-03-06 19:00:00 +0300
author: snovvcrash
tags: [internal-pentest, active-directory, kerberos, constrained-delegation, s4u2self, s4u2proxy, rubeus]
---

In this blog post I will go through a study case in abusing Kerberos constrained delegation without protocol transition (Kerberos only authentication).

<!--cut-->

![banner.png](/assets/images/abusing-kcd-without-protocol-transition/banner.png)
{:.center-image}

S4U2proxy Exchange (pic stolen from ["CVE-2020-17049: Kerberos Bronze Bit Attack – Theory"](https://www.netspi.com/blog/technical/network-penetration-testing/cve-2020-17049-kerberos-bronze-bit-theory/))
{:.quote}

* TOC
{:toc}

## TL;DR

**UPD:** a variation of this attack was already [described](https://shenaniganslabs.io/2019/01/28/Wagging-the-Dog.html) by [Elad Shamir](https://twitter.com/elad_shamir) in section *"When Accounts Collude - TrustedToAuthForDelegation Who?"*.

Let's say an attacker has compromised a machine **TEXAS** in AD domain **tinycorp.net** with Kerberos constrained delegation enabled to service `http/CHICAGO.tinycorp.net` without protocol transition. In order to abuse this configuration the attacker needs to provide the TEXAS's own TGT as well as a TGS to TEXAS host service (for example) of the user that the attacker wants to impersonate for service `http/CHICAGO.tinycorp.net`. In case there was Kerberos constrained delegation **with protocol transition** enabled on TEXAS, the attacker could go straight for the full S4U chain requesting the TGS via S4U2self first and then passing it as an "evidence" to S4U2proxy. But in our case we have to find a way to obtain a forwardable TGS of the target user to TEXAS service manually in order to initiate S4U2proxy with it.

Elad Shamir described a generic approach in his incredible [*"Wagging the Dog: Abusing Resource-Based Constrained Delegation to Attack Active Directory"*](https://shenaniganslabs.io/2019/01/28/Wagging-the-Dog.html) research (section *"A Selfless Abuse Case: Skipping S4U2Self"*) where a social engineering attack is supposed to be used in order to coerce the victim into authenticating to a compromised service with RBCD (resource-based constrained delegation) configured. Then the attacker can dump the desired TGS and use it in S4U2proxy as an "evidence".

But what if a social engineering attack is not an option, can we get the target user's TGS without user interaction? Yes, we can! With [@MzHmO](https://github.com/MzHmO) and [@PShlyundin](https://github.com/PShlyundin) we found a simple way to do that by configuring another type of delegation (RBCD2self this time) on the compromised machine and obtaining the TGS as a result of a full S4U attack against the TEXAS service.

## The Attack

Let's take a look at the initial setup.

[![initial-setup.png](/assets/images/abusing-kcd-without-protocol-transition/initial-setup.png)](/assets/images/abusing-kcd-without-protocol-transition/initial-setup.png)
{:.center-image}

Now I'm going to PsExec as LocalSystem on TEXAS and ask for its TGT via the [tgtdeleg](https://github.com/GhostPack/Rubeus#tgtdeleg) trick.

[![tgtdeleg.png](/assets/images/abusing-kcd-without-protocol-transition/tgtdeleg.png)](/assets/images/abusing-kcd-without-protocol-transition/tgtdeleg.png)
{:.center-image}

We can try to run a full S4U chain with it against `http/CHICAGO.tinycorp.net` which will expectedly fail.

[![s4u-fail.png](/assets/images/abusing-kcd-without-protocol-transition/s4u-fail.png)](/assets/images/abusing-kcd-without-protocol-transition/s4u-fail.png)
{:.center-image}

As we can see, the TGS we got is not forwardable and the S4U2proxy stage raises `KDC_ERR_BADOPTION` error.

[![describe-ticket-1.png](/assets/images/abusing-kcd-without-protocol-transition/describe-ticket-1.png)](/assets/images/abusing-kcd-without-protocol-transition/describe-ticket-1.png)
{:.center-image}

Acting as `TEXAS$` user I can modify my own `msds-AllowedToActOnBehalfOfOtherIdentity` property and set it to trust myself for RBCD.

[![configure-rbcd.png](/assets/images/abusing-kcd-without-protocol-transition/configure-rbcd.png)](/assets/images/abusing-kcd-without-protocol-transition/configure-rbcd.png)
{:.center-image}

Now it's time for the full S4U attack against `host/TEXAS.tinycorp.net`.

[![s4u-success.png](/assets/images/abusing-kcd-without-protocol-transition/s4u-success.png)](/assets/images/abusing-kcd-without-protocol-transition/s4u-success.png)
{:.center-image}

It gives us a valid forwardable TGS.

[![describe-ticket-2.png](/assets/images/abusing-kcd-without-protocol-transition/describe-ticket-2.png)](/assets/images/abusing-kcd-without-protocol-transition/describe-ticket-2.png)
{:.center-image}

It can now be used to abuse S4U2proxy for the KCD with Kerberos only authentication and access the `http/CHICAGO.tinycorp.net` service impersonating an arbitrary user (which is not in Protected Users or sensitive accounts).

[![s4u2proxy.png](/assets/images/abusing-kcd-without-protocol-transition/s4u2proxy.png)](/assets/images/abusing-kcd-without-protocol-transition/s4u2proxy.png)
{:.center-image}

## Extra: Delegate 2 Thyself

I've also tried requesting a service ticket for TEXAS without explicitly configuring RBCD2self on it but using `/self` option from Rubeus (see [@exploitph](https://twitter.com/exploitph)'s post [*"Revisiting 'Delegate 2 Thyself'"*](https://exploit.ph/revisiting-delegate-2-thyself.html)).

That's not an option for our case because the resulting TGS is returned as non-forwardable.

[![delegate2self.png](/assets/images/abusing-kcd-without-protocol-transition/delegate2self.png)](/assets/images/abusing-kcd-without-protocol-transition/delegate2self.png)
{:.center-image}

## Conclusion

Nothing new in this post, just a way to manually perform S4U2proxy with Rubeus in case of KCD Kerberos only configuration.

Mitigating factors for various delegation attacks can be observed again in Elad Shamir's [post](https://shenaniganslabs.io/2019/01/28/Wagging-the-Dog.html) :clap:

Happy hacking!

## Credits & References

* [@MzHmO](https://github.com/MzHmO)
* [@PShlyundin](https://github.com/PShlyundin)
* [Elad Shamir](https://twitter.com/elad_shamir) · [Wagging the Dog: Abusing Resource-Based Constrained Delegation to Attack Active Directory](https://shenaniganslabs.io/2019/01/28/Wagging-the-Dog.html)
* [Charlie Clark](https://twitter.com/exploitph) · [Revisiting 'Delegate 2 Thyself'](https://exploit.ph/revisiting-delegate-2-thyself.html)
