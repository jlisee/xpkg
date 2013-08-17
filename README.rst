XPM
====

:Authors: Joseph Lisee <jlisee@gmail.com>
:License: BSD (3-Clause)

A cross platform package manager for C & C++ development.

Example usage (still a work in progress):

  xpm jump my-project

  xpm install clang
  xpm install boost
  xpm install yaml-cpp

You now have those package installed in the root directory for that
project.  Your environment variables will also be modified so that the
binaries and

Design
=======

Concepts:

 - Environment: directory which supports your application
   - contains a set of installed packages
   - structured like a linux/unix tree
   - you "jump" into the environment

 - Package description:
   - lists files needed
   - instructions for building and configuring
   - later:
     - instructions for packaging
     - customization of build (ie: with or without python, )
     - patching instructions

 - Binary Package: bundle of files with metadata
   - either a zip or tar ball
   - metadata:
     - manifest of files
     - info on platform & toolset
     - raw package file
   - try to hold off on pre-post install scripts

 - Toolset: compiler, standard libraries, language revision
   - Will need a way to specify compatibility between toolsets

 - Platform: for us this is the binary format and expected kernel
