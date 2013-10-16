name: patchme
version: 1.0.0
description: A simple patched C program

# Not gonna do real build dependencies for these yet
#build-dependencies:
#  - make

files:
  md5-%(filehash)s:
    url: file://%(filepath)s

  %(hash-message.patch)s:
     url: xpd://message.patch


build:
  # Patch our program
  - patch -p0 -i ../message.patch
  - make

install:
  make install DESTDIR=%(prefix)s
