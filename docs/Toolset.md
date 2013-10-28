Toolset
========

This represent the set of packages you are using to build software.  This
concept exists so that packages can specify that they need a C++ compiler, but
let you pick the specific compiler.

This is done by using special build dependencies that are interpreted based on
the current toolset.  Here is the currently supported working set:

 - tl:shell - POSIX compliant shell
 - tl:base - base OS utilities (cp, mv, ln, etc.)
 - tl:c++-compiler - C++ compiler
 - tl:c-compiler - C compiler
 - tl:linker - provides the platform specific linker

The are prefixed with "tl:" to prevent name space collisions with existing
packages.

Todo
-----

 - Define a method for specify known version restrictions for a package, so that
   a package which needs gcc >= 4.7 can specify that.


Workflows
----------

 - User creates environment, with no toolset:
   - Special local toolset installs no packages, assumes users environment has
     the package
   - TODO: consider checking for tools at first

 - User creates an environment with a toolset
   - Possibly check to make sure the toolset set packages are all available to
     be installed

 - User builds a package
   - Any build dep in the package is replaced with the toolset equivalent, and
     things proceed as normal
   - Special environment variables from the toolset are applied when building
