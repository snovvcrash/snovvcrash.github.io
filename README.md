### [snovvcrash.github.io](https://snovvcrash.github.io/)

#### Install

```
$ git clone https://github.com/snovvcrash/snovvcrash.github.io && cd snovvcrash.github.io
$ sudo apt install ruby ruby-all-dev zlib1g-dev -y
$ gem install bundler
$ bundle install
```

#### Run

**Host:**

```
Cmd > JEKYLL_ENV=production bundle exec jekyll serve [--host 0.0.0.0] [--no-watch]
PS > $env:JEKYLL_NO_BUNDLER_REQUIRE = "1"
PS > $env:Path += ";C:\Ruby34-x64\bin"
PS > jekyll serve -l -H 0.0.0.0
```

**WSL 2:**

```
$ JEKYLL_ENV=production bundler exec jekyll build && bash -c 'python3 -m http.server -b 127.0.0.1 -d _site 3000'
```

#### Update

```
$ bundle update
```

#### Themes

* [Is there a "Dark Minima" theme out there? · Issue #143 · jekyll/minima](https://github.com/jekyll/minima/issues/143)
