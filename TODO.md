Showstoppers
-------------

Things a package manager must have (and ours needs to work)

 - fix packing parsing, tasks 3 seconds do an info call on the python package, now everything is freaking slow because of it
     - maybe switch to msgpack or bson for the file cache
     - split things into metadata + contents, so we don't have to parse/handle
       contents all the time
     - lazy load the content as needed (we don't need the bulky contents all the time)
     - A pure binary format would be too much right now :(

 - split up python into minimal (just core interp, key libs), normal, and dev
 - split out libstdc++ and libgcc_s from gcc

 - things to look at:
    - look at how fakeroot works for package isolation
    - arch build tool: https://wiki.archlinux.org/index.php/Makepkg
      - its in: ftp://ftp.archlinux.org/other/pacman/pacman-4.1.2.tar.gz

 - create a way for a for package to hard-link/copy in system libraries
   - used for opengl so we can link again the vendor version
   - X11 we will just build ourselves

 - make sure binutils is not searching the local system directories

 - generalize the ubuntu-libc package to "local-libc"

 - proper environment creation
   - storage of environment settings

 - file hashing:
   - store the hash of the files in a package
   - handle the has of files with install path offsets

 - environment lock file to prevent two processes from changing the env at once
   - use the python "lockfile" module
   - only do write lock access

 - crashes during install should roll back and remove all files properly
   - right now it just leaves a bunch of files laying around

 - isolated (chroot?) builds (KEY FEATURE)
   - other utils? (docker, by-hand lxc?)
   - need the ability to install to a <dir>, but use the root prefix
   - manually map bash because we need a shell
   - setup system to create a "build env"
   - install build deps into the env
   - run the build in there
   - figure out if we need python in there

 - put the build logs somewhere else

References
-----------

 - Stock (CLI only) linux from scratch:
    http://www.linuxfromscratch.org/lfs/view/stable/
 - Cross compile LFS:
    http://www.cross-lfs.org/view/CLFS-3.0.0-RC1-SYSTEMD/x86/
 - Beyond LFS X11 section:
    http://www.linuxfromscratch.org/blfs/view/stable/x/installing.html

Nice to haves
--------------

 - SAT solver:
   - Wiki: http://en.wikipedia.org/wiki/Boolean_satisfiability_problem
   - General Idea (my understanding):
     - Assume: want to install A
       - A needs B* & C*
       - C needs B2
       - B has versions B1 and B
     - A! or B1 or B2
     - A! or C
     - C! or B2
   - PicoSAT (small C based solver): 
     - CNF: format a list of OR clauses AND together
     - Python wrapper: https://pypi.python.org/pypi/pycosat
   - SUSE SAT solver lib:
     libsolv (C): https://github.com/openSUSE/libsolv
     high level wrapper (python & C): https://github.com/akozumpl/hawkey
   - SUSE zypper SAT solver, papers:
     http://files.opensuse.org/opensuse/en/b/b9/Fosdem2008-solver.pdf
     https://www.youtube.com/watch?v=Z8ArpGRbxTM
   - SUSE SAT solver guides:
     http://en.opensuse.org/openSUSE:Libzypp_satsolver_basics (Copy of FOSDEM2008)
     http://en.opensuse.org/openSUSE:Libzypp_satsolver_internals
     http://doc.opensuse.org/projects/satsolver/HEAD/ (doxygen docs)

 - support for network access to package roots, and environments

 - separate builds into steps
   - make the builder just a system that runs a generic set of steps
   - independent of the builder we can produce the steps (used for nix/disthash style input derivations)

 - create python packages
   - need pip package
   - helper function to generate xpd from pypi would help
   - just use pip to do the install
   - maybe even have a way to install from pypi directly, without needed to have
     the xpd file, would only work for pure packages

 - create a command to build all bootstrap packages
   - it's the set of all dependencies for the compiler in an enviornment
   - build the set of packages which are needed to build packages
   - this is used to provide the user on a specific platform with the chicken and egg packages

 - better mirror support:
   - support "content addressable" mirror
   - turn the cache into just a local content addressbale mirro
   - support file name based mirrors as well
   - make mirror support transparent

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

 - commands for managing the environment
   - add additional trees
   - add additional roots

 - better building workflow support:
   - command to setup the temp dir and download files
   - command that lets you jump into the temp dir, and manually examine and
     execute steps

 - xz compression support, see: https://github.com/peterjc/backports.lzma
   - then we can support newer coreutils version
   - also newer grep versions

 - info support for XPD files

 - support for multiple download sources for the same file, allowing for
   slightly more robust file fetching

 - support for running with another libc! (Abandoning for now)
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

 - good source of packages for windows (see SDL as well):

   http://win-builds.org/stable/packages/windows_32/package_list.html

 - good yaml source of packages needed for building python scientific environments:

   https://github.com/hashdist/hashstack2

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
