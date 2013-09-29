TODO
=====

Game changers
--------------

Things that are considered and advantage vs. other package managers.

 - chroot builds
   - other utils?
   - manually map bash because we need a shell
   - setup system to create a "build env"
   - install build deps into the env
   - run the build in there
   - figure out if we need python in there


Showstoppers
-------------

Things a package manager must have

 - create core package to support chroot builds
   - coreutils
   - make
   - gcc
   - cmake
   - ld (part of gcc?)

 - repos and packages:
   - make sure we can specify multiple source locations

 - file hashing:
   - store the hash of the files in a package
   - handle the has of files with install path offsets

 - create much better tracing functionality
   - log build output somewhere in the environment itself


Nice to haves
--------------

 - search all package descriptions

 - long form package descriptions

 - handle dependencies with versions somehow properly with multipkgs

 - add the concept of build only dependencies

 - add support for a check/test step (libgmp, libmpfr have "make check")

 - add the concept of package input hashing (commands and files, to make
   the file cache more reliable)

 - add some way to easily check/configure environment variables

 - environment audit function which checks for:
   - files that don't belong
   - files which are owned by two packages

 - only warn about a directory having files (on removal) if no other
   package has files in that directory

 - decide on system packages:
   - opengl, x11, and eventually wayland, xmir
   - can't build opengl, it comes from the vendor
   - need a way to install these in chroot, need a way to create these
     header only packages, and pull in the needed binaries into the
     chroot

 - info support for XPD files

 - support for multiple download sources for the same file, allowing for
   slightly more robust file fetching

Docs
------

 - Document use cases:
   - package a set of pre-existing files
   - package an existing library
   - package an existing command line program

 - Document file formats:
   - package-name.xpd - format
   - xpkg.yml - format (see PackageBuilder.build method)

 - Create the concept of a toolset

 - Steps in building a package:
   - Install build deps
     - Fetch the descriptions for all packages
     - Validate versions to make sure things will work
     - Topo sort our dep graph
     - Install things in order

   - Compile & Install:
     - Download needed sources
     - Compile
     - Install

   - Form binary package:
     - Build metafile
     - Package files
     - Build package
