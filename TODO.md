TODO
=====

 - repos and packages:
   - make sure we can specify multiple source locations

 - path editing - make sure we can change embedded

 - build package before installing it

 - create core package to support chroot builds
   - coreutils
   - make
   - gcc
   - cmake
   - ld (part of gcc?)

 - chroot builds
   - other utils?
   - manually map bash because we need a shell
   - setup system to create a "build env"
   - install build deps into the env
   - run the build in there
   - figure out if we need python in there

 - decide on system packages:
   - opengl, x11, and eventually wayland, xmir
   - can't build opengl, it comes from the vendor
   - need a way to install these in chroot, need a way to create these header
     only packages, and pull in the needed binaries into the chroot

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
