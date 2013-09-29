# Over all name and version
name: multipkg
version: 1.0.0

# This is a package description which installs multiple files
packages:
  # All files
  libmulti:
  # Development headers
  libmulti-dev:
    files: ['include/multi/.*']
    dependencies: ['libmulti']
  # All the tools
  multi-tools:
    version: 1.5.0
    files: ['bin/tool.*']
    dependencies: ['libmulti']

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
