X11 & OpenGL
=============

Some notes about how to handle building applications that link against
X11. At this point we don't want to ship an X11 stack, so presumably we
just use the client library.

X11 Libs
----------

libX11 - main library (ABI good since 2009) [Download site][3]
libXau - X11 authentication library [Download site][3]
libxcb - X protocol C-language binding [Website][1]
libXdmcp - implement X protocol for talking to the display manager [Download site][3]

TODO: What about xrandr and Xinerama extensions

More docs on the X11 environment in the [linux from scratch guide][2].

OpenGL
-------

There appears to be an OpenGL spec for Linux
(http://www.opengl.org/registry/ABI/) so we could get away with just
having the mesa-common-dev like packages which packs the headers itself.

[1]:http://markdown-here.com/livedemo.html
[2]:http://www.linuxfromscratch.org/blfs/view/svn/x/installing.html
[3]:http://xorg.freedesktop.org/releases/individual/lib/
