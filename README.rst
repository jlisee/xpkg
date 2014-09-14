Xpkg
=====

:Authors: Joseph Lisee <jlisee@gmail.com>
:License: BSD (3-Clause)

A cross platform package manager for C & C++ development.

Example usage (still a work in progress)::

  > xpkg init ~/projects/my-project/env my-project

  > xpkg jump my-project

  > xpkg install yaml-cpp

  > xpkg list
    yaml-cpp - 1.2.0

  > xpkg info yaml-cpp
     name: yaml-cpp
     version: 1.2.0
     description: YAML parser for C++
     files:
       - lib/yaml-cpp.so
       - include/yaml-cpp/yaml.hpp

  > xpkg remove yaml-cpp

  > xpkg list

When you jump into an environment you paths are modified so that you
can access the binaries and libraries installed there.  All installed
packages are contained within that environment.


Run Time requirements
======================

   sudo apt-get install liblzma-dev
   pip install -r python/requirements.txt


Design
=======

Concepts:

- Environment: directory which supports your application

  - Properties of an environment:
    - name
    - packages
    - toolset
    - tree/repo?

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

    - manifest of files & hashes
    - package dependencies (name + version)
    - system dependencies (tag/name + version), example:
        libc >= 2.15
        linux >= 3.1
    - inputs file (to be definied)

  - try to hold off on pre-post install scripts


- Toolset: compiler, standard libraries, language revision

  - Will need a way to specify compatibility between toolsets


- Platform: for us this is the binary format and expected kernel

- Places with pages:

 - https://earthserver.com/Setting_up_a_modern_C%2B%2B_development_environment_on_Linux_with_Clang_and_Emacs (Web archive: http://web.archive.org/web/20131111034941/https://earthserver.com/Setting_up_a_modern_C%2B%2B_development_environment_on_Linux_with_Clang_and_Emacs)


Similar Projects
=================

- disthash: http://hashdist.github.io/
- nix: http://nixos.org/nix/
