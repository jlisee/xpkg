name: pygreet
version: 1.0.0
description: Basic python hello world greet library

# Not gonna do real build dependencies for these yet
#build-dependencies:
#  - python

#dependencies:
#  - make

files:
  md5-%(filehash)s:
    url: file://%(filepath)s

build:
  make

install:
  make install DESTDIR=%(prefix)s
