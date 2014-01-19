name: env-command
version: 1.0.0
description: Advanced command helper

# Not gonna do real build dependencies for these yet
#build-dependencies:
#  - make

files:
  md5-%(filehash)s:
    url: file://%(filepath)s

build:
  env:
    EXTRA_FLAGS: '-DGREETING=\"Hi\"'
  cmds:
    make

install:
  make install DESTDIR=%(prefix)s
