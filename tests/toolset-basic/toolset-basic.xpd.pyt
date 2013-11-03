name: toolset-basic
version: 1.0.0
description: Basic C hello world program

build-dependencies:
  - tl:base
  - tl:c-compiler
  - tl:linker
  - tl:libc
# Lets ignore make for now
#  - make

files:
  md5-%(filehash)s:
    url: file://%(filepath)s

build:
  make

install:
  make install DESTDIR=%(prefix)s
