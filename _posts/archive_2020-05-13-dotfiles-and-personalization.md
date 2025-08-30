---
layout: post
title: "О дотфайлах, персонализации и Kali"
date: 2020-05-13 22:00:00 +0300
author: snovvcrash
tags: [xakep-ru, notes, personalization, dotfiles, linux, windows, wsl, zsh, tmux, tilix, wsltty, kali-setup]
---

[//]: # (2020-04-13)

В недавнем времени мне приходилось часто разворачивать свою рабочую среду (в частности, Kali Linux) на новых машинах: то на железе, то на виртуалках, то снова на железе... В общем, ты понял. В какой-то момент мне надоели рутинные действия, и я решил извлечь из этой ситуации максимальную пользу для себя и окружающих. В этой статье поговорим о том, как можно организовать хранение своих дотфайлов, чтобы более-менее автоматизировать процесс настройки и персонализации различных ОС для дома и работы.

<!--cut-->

<p align="right">
  <a href="https://xakep.ru/2020/04/13/linux-dotfiles/"><img src="https://img.shields.io/badge/%5d%5b-%d0%a5%d0%b0%d0%ba%d0%b5%d1%80-red?style=flat-square" alt="xakep-badge.svg" /></a>
</p>

![banner.png](/assets/images/dotfiles-and-personalization/banner.png)
{:.center-image}

* TOC
{:toc}

# .файлы

Помнится, как-то раз я прочитал [статью](https://0x46.net/thoughts/2019/02/01/dotfile-madness/), которая произвела на меня сильное впечатление. Речь там шла немного не о том, о чем поговорим сегодня мы, однако главная идея одна и та же: большинство системных утилит используют стандартные пути для хранения своих конфигурационных файлов, поэтому совсем несложно создать персонализированную коллекцию настроек для разных программ и восстанавливать их от одного деплоя операционной системы к другому. Эта концепция стара как мир и носит название дотфайлов: файлов, имена которых начинаются с точки, а так как большинство конфигов в \*NIX-ах и правда начинаются с точки (чтобы стать скрытыми и не мозолить глаза юзера при очередном `ls`), то все вполне логично.

Удобнее всего, на мой взгляд, организовать хранение дотфайлов в системе управления версиями (CVS), чтобы можно было клонировать репозиторий одним действием при настройке новой системы. Однако, это накладывает определенные условия на то, что́ смогут содержать твои конфиги, так как нельзя забывать, что CVS — штука публичная. Приватными репозиториями пользоваться бессмысленно, так как это убьет все преимущества такой организации дотфайлов: например, их не повытаскиваешь из скриптов по-отдельности без токенов авторизации. Кто-то может использовать облака для более удобной синхронизации, чтобы избежать миллионов пушей по каждой мелочи. В любом случае, это вопрос вкусовщины, и в этой статье я покажу один из способов, как можно хранить свои настройки на GitHub.

Итак, у меня есть два репозитория.

Первый — [dotfiles-linux](https://github.com/snovvcrash/dotfiles-linux) — конфигурационные файлы для приложений на Linux.

![dotfiles-linux.png](/assets/images/dotfiles-and-personalization/dotfiles-linux.png)

Второй — [dotfiles-windows](https://github.com/snovvcrash/dotfiles-windows) — конфигурационные файлы для приложений на Windows.

![dotfiles-windows.png](/assets/images/dotfiles-and-personalization/dotfiles-windows.png)

В первом репозитории две ветки: `master` и `wsl`. Ветка `wsl` отвечает за версии дотфайлов, которые я использую во втором репозитории для персонализации Windows Subsytem for Linux. Когда в процессе настройки винды я заметил, что \*NIX-овые конфиги не получается юзать для WSL «в чистом виде», то решил вести отдельную ветку, которую позже включил в `dotfiles-windows` в качестве [подмодуля](https://git-scm.com/book/ru/v2/%D0%98%D0%BD%D1%81%D1%82%D1%80%D1%83%D0%BC%D0%B5%D0%BD%D1%82%D1%8B-Git-%D0%9F%D0%BE%D0%B4%D0%BC%D0%BE%D0%B4%D1%83%D0%BB%D0%B8).

Результат такой: когда я разворачиваю дотфайлы на новой системе с Windows, я должен выполнить следующие команды изнутри WSL.

```
~$ WIN_DOTFILES_DIR="$(wslpath `cmd.exe /C "echo %USERPROFILE%" | tr -d "\r"`)/.dotfiles"
```

Первым действием с помощью `wslpath`, который резолвит пути между хостовой ОС и WSL, я создаю переменную с именем директории, куда я клонирую репозиторий с моими дотфайлами для Windows. В моем случае, директория будет называться `/mnt/c/Users/snovvcrash/.dotfiles`.

```
~$ git clone https://github.com/snovvcrash/dotfiles-windows "${WIN_DOTFILES_DIR}"
```

Далее я выкачиваю `dotfiles-windows` по этому пути.

```
~$ ln -sv "${WIN_DOTFILES_DIR}/wsl" ~/.dotfiles
```

Последним действием я создаю символическую ссылку в файловой системе WSL, которая будет указывать на подмодуль `/mnt/c/Users/snovvcrash/.dotfiles/wsl`, который мы заберем с гита, как показано ниже.

```
/mnt/c/Users/snovvcrash/.dotfiles$ git submodule update --init --remote
/mnt/c/Users/snovvcrash/.dotfiles$ git submodule foreach "git checkout $(git config -f $toplevel/.gitmodules submodule.$name.branch || echo master)"
```

Здесь я инициализирую git-подмодуль для данного репозитория на основании настроек [.gitmodules](https://github.com/snovvcrash/dotfiles-windows/blob/master/.gitmodules), а потом восстанавливаю стейт `detached HEAD` для всех подгрузившихся подмодулей, так как по дефолту они выкачиваются [с отваленными головами](https://stackoverflow.com/q/18770545/6253579).

Настроить такую схему можно с помощью одной команды, которая добавит подмодуль `wsl` в твой репозиторий дотфайлов из существующего ремоута.

```
/mnt/c/Users/snovvcrash/.dotfiles$ git submodule add https://github.com/snovvcrash/dotfiles-linux wsl
```

Это эквивалентно тому, как если бы я вручную изменил конфиг `.gitmodules` с помощью `git config`.

```
/mnt/c/Users/snovvcrash/.dotfiles$ git config -f .gitmodules submodule.wsl.branch wsl
```

Про концепцию хранения дотфайлов поговорили, а что же, собственно, можно в них хранить? Я остановлюсь только на некоторых тулзах, которыми я пользуюсь на постоянной основе в Linux, потому что описание всего, что там лежит, может растянуться на долгие часы.

# Zsh

С какого-то момента я перестал воспринимать Bash, как шелл, в котором можно комфортно работать. Да, разумеется, если жизнь заставит (особенно, если это реверс-коннект с машины-жертвы), можно юзать и обычный `/bin/sh` без TAB-ов, истории и управляющих символов. Но даже реверс-шелл можно довести до ума, [апгредив](https://forum.hackthebox.eu/discussion/comment/22312#Comment_22312) его до PTY, чего уж говорить о дефолтной оболочке на своей машине. Поэтому я использую [Zsh](https://www.zsh.org/). Не [писал](https://habr.com/ru/post/326580/) о нем только ленивый, поэтому сразу перейдем к минимальному набору приятностей, нужных, чтобы удобно с ним существовать.

## Oh My Zsh

В первую очередь, это, конечно же, фреймворк [Oh My Zsh](https://ohmyz.sh/), позволяющий играючи управлять дополнениями и плагинами Zsh. Мастхевом я считаю [zsh-syntax-highlighting](https://github.com/zsh-users/zsh-syntax-highlighting) для подсветки синтаксиса команд в терминале, и [zsh-autosuggestions](https://github.com/zsh-users/zsh-autosuggestions) для предложения автозавершения команд на основе твоей истории. Установка сводится к выполнению трех простых действий, после которых нужно перелогиниться, чтобы изменения возымели эффект.

```
$ apt install zsh -y && sh -c "$(curl -fsSL https://raw.githubusercontent.com/robbyrussell/oh-my-zsh/master/tools/install.sh)"
$ git clone https://github.com/zsh-users/zsh-syntax-highlighting.git ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting
$ git clone https://github.com/zsh-users/zsh-autosuggestions ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-autosuggestions
$ sed -i 's/plugins=(git)/plugins=(git zsh-syntax-highlighting zsh-autosuggestions)/g' ~/.zshrc
```

## Про темы и промпт темы robbyrussell

Zsh не Zsh без цветастого промпта, однако большая часть кастомных тем слишком нагружает интерпретатор и появляется input lag. Чтобы этого не было, я использую дефолтную тему с одним изменением: ту часть промпта, в которой отражается текущая рабочая директория, я настроил так, чтобы она отражала две родительские папки «назад» и корень, потому что по умолчанию тема `robbyrussell` показывается только одну папку. Таким образом ты не допустишь засорения экрана при работе в «длинной» директории, но всегда будешь в курсе, где сейчас находишься.

```
$ cp "$ZSH/themes/robbyrussell.zsh-theme" "$ZSH_CUSTOM/themes/robbyrussell.zsh-theme"
$ echo '[*] replace "%c" with "%(4~|%-1~/…/%2~|%3~)" in "$ZSH_CUSTOM/themes/robbyrussell.zsh-theme"'
```

Теперь если заменить `%c` на `%(4~|%-1~/…/%2~|%3~)` в файле `$ZSH_CUSTOM/themes/robbyrussell.zsh-theme`, то все будет по плану.

![zsh-prompt.png](/assets/images/dotfiles-and-personalization/zsh-prompt.png)

## Source it!

Последним действием я добавляю настройки source-а внешних дотфайлов, которые лежат в папке [~/.dotfiles/system](https://github.com/snovvcrash/dotfiles-linux/tree/master/system), в конфиг `.zshrc`.

```bash
$ cat << 'EOT' >> ~/.zshrc

# Resolve DOTFILES_DIR
if [ -d "$HOME/.dotfiles" ]; then
    DOTFILES_DIR="$HOME/.dotfiles"
else
    echo "Unable to find dotfiles, exiting..."
    return
fi

# Source dotfiles
for DOTFILE in "$DOTFILES_DIR"/system/.*; do
    [ -f "$DOTFILE" ] && . "$DOTFILE"
done
EOT
```

Там, в основном, определены дополнительные переменные для экспорта, системные алиасы, настройки виртуальных сред (для Python) и тому прочее.

# tmux

Как-то я уже говорил, что большой фанат [tmux](https://ru.wikipedia.org/wiki/Tmux). Это и правда очень удобная штука, которая помогает оставаться организованным в контексте одновременной работы с несколькими сессиями. Для его настройки так же есть туча опций, как и для практически любой линуксовой утилиты.

На мой сетап можно [посмотреть](https://github.com/snovvcrash/dotfiles-linux/blob/master/tmux/.tmux.conf) на GitHub, а выглядит вживую он примерно так.

![tmux-rocks.png](/assets/images/dotfiles-and-personalization/tmux-rocks.png)

Из необычного здесь только [панель](https://github.com/thewtex/tmux-mem-cpu-load) в правом нижнем углу, на которой висят мониторы системных ресурсов. Устанавливается она отдельно, поэтому я объединил процесс настройки tmux в небольшой скрипт (предполагается, что директория `.dotfiles` со всем необходимым уже существует в твоем домашнем каталоге).

```bash
#!/usr/bin/env bash
sudo apt install wget git xclip -y
rm -rf ${HOME}/.tmux*
git clone "https://github.com/tmux-plugins/tpm" ${HOME}/.tmux/plugins/tpm
ln -sv ${HOME}/.dotfiles/tmux/.tmux.conf ${HOME}/.tmux.conf
git clone "https://github.com/thewtex/tmux-mem-cpu-load" ${HOME}/.tmux/plugins/tmux-mem-cpu-load
cd ${HOME}/.tmux/plugins/tmux-mem-cpu-load
cmake .
make
sudo make install
cd -
```

# Tilix

Если ты так же, как и я, влюбишься в tmux, то тебе понадобится минималистичный терминальный эмулятор, не перегруженный лишними фичами по типу создания новых вкладок, хоткеев на copy-paste (так как в tmux-е у нас все свое) и странного поведения на нажатие правой кнопки мыши. С этим проблематичнее, так как практически все, что я пробовал, уже было заточено под «свою атмосферу», где tmux-у были не слишком рады. В итоге я остановился на [Tilix](https://gnunn1.github.io/tilix-web/) для Linux и [WSLtty](https://github.com/mintty/wsltty) для WSL.

Tilix не попадает под определение минималистичного терминала из коробки, однако все его навороты (TAB-ы, панели, верхние менюшки), в отличии от других эмуляторов, могут быть отключены из настроек. В итоге я остановился на голом borderless-окне с эффектом прозрачности, и полностью доволен результатом.

![tilix-rocks.png](/assets/images/dotfiles-and-personalization/tilix-rocks.png)

Был период, когда я экспериментировал с [форком](https://github.com/LukeSmithxyz/st) st, но как-то не срослось. Может, сам он и ультра-минималистичный, но вот только зависимостей для него нужно поставить немало, которых ко всему прочему может не оказаться в дефолтном провайдере пакетов, если только ты сидишь не на Arch-е. Пробный конфиг вместе со скриптом для сборки можно найти [здесь](https://github.com/snovvcrash/dotfiles-linux/blob/master/st/INSTALL.sh).

# Лайфхаки по настройке Kali

Как я уже сказал, разворачивать и настраивать Kali в последние дни приходилось довольно часто, а когда делаешь что-то с завидной регулярностью, то волей-неволей вырабатываешь для себя некоторую методику, которой стараешься придерживаться в дальнейшем. Вот мои рутинные действия при установке этой ОС, как в случае [с установкой на ВМ](https://www.offensive-security.com/kali-linux-vm-vmware-virtualbox-image-download/#1572305786534-030ce714-cc3b), так и на железо.

**Первое.** Если на ВМ: отключить систему управления питанием, чтобы машина не уходила в сон и не лочила экран. Для меня это обязательная опция, потому что часто работаешь с активной Kali на фоне.

**Второе.** Если на ВМ: настроить параллельную работу сетевых интерфейсов. Обычно, у меня включены три сетки на виртуалке (будем говорить [терминами](https://www.virtualbox.org/manual/ch06.html) VirtualBox): NAT, внутренняя сеть и виртуальный адаптер хоста.

С заводскими настройками Kali не позволяет использовать все коннекты одновременно — NetworkManager не разрешает. Однако, если делегировать полномочия управления сетью на старинный `ifconfig`, то обеспечить одновременную работу сетевых интерфейсов можно, задав соответствующие настройки в `/etc/network/interfaces`.

```
$ cat /etc/network/interfaces
# This file describes the network interfaces available on your system
# and how to activate them. For more information, see interfaces(5).

source /etc/network/interfaces.d/*

# NAT
allow-hotplug eth0
iface eth0 inet dhcp

# Internal
allow-hotplug eth1
iface eth1 inet dhcp

# Host-only
allow-hotplug eth2
iface eth2 inet dhcp

# The loopback network interface
auto lo
iface lo inet loopback
```

После этого поднимаем каждый из указанных интерфейсов and we're good to go!

```
$ ifup eth0
$ ifup eth1
$ ifup eth2
```

В теории это можно сделать через настройку сетевых профилей для NetworkManager-а, но я привык по старинке.

**Третье.** Обновляем систему. Если виртуалка установлена у тебя на рабочей машине, включенной в домен, и ты не можешь выключить антивир на период обновлений (ибо политика не разрешает), то настоятельно рекомендую вытягивать апдейты по HTTPS, чтобы не стриггерить 9999 алертов со стороны хоста. Для этого достаточно добавить букву `s` в `http` в файле `/etc/apt/sources.list`.

```
$ sudo vi /etc/apt/sources.list
...Переходим на HTTPS по необходимости...
$ sudo apt update && sudo upgrade -y
$ sudo reboot
```

**Четвертое.** Если на ВМ: ставим Guest Additions только в том случае, если что-то из его фич **не** работает: нативное разрешение не подтягивается либо не работает Drag'n'Drop или общий буфер обмена. В противном случае оставляем все, как есть, потому что обычно готовые образы содержат предустановленные гостевые дополнения, которые, в свою очередь, очень хрупкие и ломаются от любого чиха.

**Пятое.** Решаем из-под какого пользователя будем работать. С правами рута жить проще, но намного опаснее, поэтому рекомендую все же отказаться от суперюзера хотя бы в том случае, если Kali была установлена на железо. Однако, признаться честно, на виртуалках я продолжаю работать с повышенными привилегиями, поэтому на этом этапе я задаю пароль для `root` и отключаю дефолтного юзера `kali`.

```
kali@kali:$ sudo -i
kali@kali:$ passwd root
...Перелогиниваемся как root...
root@kali:$ usermod -L kali && usermod -s /sbin/nologin kali && chage -E0 kali
```

**Шестое.** Если работаешь под обычным юзером, можно продлить время тайм-аута на ввод пароля для sudo. Опционально, и может быть кем-то расценено как небезопасная настройка, поэтому здесь на твое усмотрение.

```
$ sudo visudo
...
Defaults    env_reset,timestamp_timeout=45
...
```

**Седьмое.** Устанавливаем `cmake`, так как он понадобится для сборки софта и дергаем свои конфиги с GitHub.

```
$ sudo apt install cmake -y
$ git clone https://github.com/snovvcrash/dotfiles-linux ~/.dotfiles
```

После всего этого можно быстро настроить то, что было описано выше, и идти вершить Великие дела. Чтобы не вбивать команды по одной, я набросал несколько тематических [скриптов](https://github.com/snovvcrash/dotfiles-linux/tree/master/00-autoconfig), которые выполнят необходимые установки.
