# Over all name and version
name: multipkg
version: 1.0.0

# This is a package description which installs multiple files
packages:
  multi-toola:
    files: ['bin/toola']
  multi-toolb:
    # This version version provided
    version: 2.0.0
    files: ['bin/toolb']

# Depends here are applied to all projects
dependencies:
 - faketools # Needed for configuration

files:
  md5-%(filehash)s:
    url: file://%(filepath)s

configure:
  ./configure --prefix=%(prefix)s

build:
  make -j%(jobs)s

install:
  make install
