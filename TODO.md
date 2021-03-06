Showstoppers
-------------

Things a package manager must have (and ours needs to work)

 - proper environment creation
   - storage of environment settings

 - toolsets (KEY FEATURE)
   - defines a set of build depenencies
   - name -> list of deps, example:

     shell: dash
     base: coreutils
     bin: binutils
     compiler: gcc

 - support for running with another libc!
   - plan:
     - Make sure when environment is created we have a symlink ld-linux in the env at all times (try make it pickable)
       - Make this some kind of ensure function that is run when ever the environment is changed
       - By default have this link to proper libc
     - add a pure which sets environment up explicitly to make builds more reliable,
       half way to chroot basically
   - notes:
     - see: http://stackoverflow.com/a/851229/138948
        -Wl,--dynamic-linker=/path/to/newglibc/ld-linux.so.2
     - hope that are standard null termination binary patch overwrite technique
     will work
     - If not see here for tips on ELF patching: http://siddhesh.in/journal/2011/03/27/changing-the-default-loader-for-a-program-in-its-elf/
     - Also see this relocatable patch: http://git.yoctoproject.org/cgit.cgi/poky/plain/meta/recipes-core/eglibc/eglibc-2.17/relocatable_sdk.patch

 - file hashing:
   - store the hash of the files in a package
   - handle the has of files with install path offsets

 - chroot builds (KEY FEATURE)
   - other utils?
   - manually map bash because we need a shell
   - setup system to create a "build env"
   - install build deps into the env
   - run the build in there
   - figure out if we need python in there


Nice to haves
--------------

 - mini-toolset to test toolset support on:
   - busybox - replaces coreutils (maybe toybox)
   - uclibc - replaces glibc (or maybe musl it's smaller)
   - tcc - replaces gcc + binutils

 - output to stdout/stderr and to a log file for builds:
     http://stackoverflow.com/a/4985080/138948

 - search all package descriptions

 - long form package descriptions

 - use the python logger for tracing

 - handle dependencies with versions somehow properly with multipkgs

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

 - xz compression support, see: https://github.com/peterjc/backports.lzma
   - then we can support newer coreutils version

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
