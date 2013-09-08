name: faketools
version: 1.0.0

files:
  md5-%(filehash)s:
    url: file://%(filepath)s

configure:
  ./configure --prefix=%(prefix)s

build:
  make -j%(jobs)s

install:
  make install
