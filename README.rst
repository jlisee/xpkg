XPM
====

:Authors: Joseph Lisee <jlisee@gmail.com>
:License: BSD (3-Clause)

A cross platform package manager for C & C++ development.

Example usage (still a work in progress):

  > xpm jump my-project

  > xpm install yaml-cpp

  > xpm list
    yaml-cpp - 1.2.0

  > xpm info yaml-cpp
     name: yaml-cpp
     version: 1.2.0
     description: YAML parser for C++
     files:
       - lib/yaml-cpp.so
       - include/yaml-cpp/yaml.hpp

  > xpm remove yaml-cpp

  > xpm list

When you jump into an environment you paths are modified so that you
can access the binaries and libraries installed there.  All installed
packages are contained within that environment.


Design
=======

Concepts:

 - Environment: directory which supports your application
   - contains a set of installed packages (managed by the install database)
   - structured like a linux/unix tree
   - you "jump" into the environment
   - tool can pick up on this with an environment variable

 - Install database:
   - Manages information about the packages in an environment

 - Package tree:
   - database of package descriptions
   - can contain multiple version of each description
   - initially will just be file tree

 - Package description:
   - lists files needed
   - instructions for building and configuring
   - later:
     - instructions for packaging
     - customization of build (ie: with or without python, )
     - patching instructions

 - Package repository: Pile of binary packages

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
