name: hello

files:
  md5-%(filehash)s:
    url: file://%(filepath)s

configure:
  ./configure --prefix=%(prefix)s

build:
  make -j%(jobs)s

install:
  make install
