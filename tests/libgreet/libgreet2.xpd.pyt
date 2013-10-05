name: libgreet
version: 2.0.0

build-dependencies:
 - faketools # Needed for configuration

files:
  md5-%(filehash)s:
    url: file://%(filepath)s

configure:
  ./configure --prefix=%(prefix)s

build:
  make -j%(jobs)s EXTRA_FLAGS='-DGREETING="Welcome to a better world!"'

install:
  make install
