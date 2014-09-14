# Author: Joseph Lisee <jlisee@gmail.com>

# Python Imports
import StringIO
import hashlib
import os
import re
import subprocess

from collections import namedtuple, defaultdict

# Project Imports
from xpkg import cache
from xpkg import util


PkgInfo = namedtuple('PkgInfo', [
    'url',
    'name',
    'version',
    'hash',
    'description',
    'build_sys',
    'languages',
    ])

# http://ftp.gnu.org/gnu/patch/patch-2.7.1.tar.bz2

PKG_VER_REGEX = re.compile('([a-zA-Z0-9]+)-([0-9\.]+).*')

def get_name_version(url):
    """
    Returns the name and version of the project based on the given URL
    """

    r, file_name = os.path.split(url)

    # Pull out the name and version from the package
    m = PKG_VER_REGEX.match(file_name)

    name = None
    version = None

    if m:
        groups = m.groups()
        if len(groups) > 0:
            name = groups[0].lower()
        if len(groups) > 1:
            version = groups[1].strip('.')

    return name, version


def get_pkg_info(url):
    # Pull out the name and version from the package
    name, version = get_name_version(url)

    # Grab the file
    cache_path = cache.fetch_file('md5-', url)

    # Get the file hash out
    _, file_hash = os.path.split(cache_path)

    # Get the description based on apt-cache
    args = ['apt-cache','search', '^%s$' % name]
    res = subprocess.check_output(args)

    description = None

    if len(res):
        parts = res.split('-')

        if len(parts) > 1:
            fname = parts[0]
            description = '-'.join(parts[1:]).strip()

    # Unpack the package and guess the build system
    package_dir = util.unpack_tarball(cache_path)

    root_files = os.listdir(package_dir)
    #full_file_path = [os.path.join(output_name, f) for f in root_files]

    build_sys = None

    if 'configure' in root_files:
        build_sys = 'autotools'
    elif 'Makefile' in root_files:
        build_sys = 'make'

    # Try to guess project languages
    extensions = defaultdict(int)

    for root, dirs, files in os.walk(package_dir):
        for fullname in files:
            fname, ext = os.path.splitext(fullname)
            extensions[ext] += 1

    languages = set()

    extension_lang = {
        '.c' : 'c',
        '.cc' : 'c++',
        '.C' : 'c++',
        '.cxx' : 'c++',
        '.c++' : 'c++',
        }

    for ext in extensions:
        lang = extension_lang.get(ext, None)

        if lang:
            languages.add(lang)

    # Return our results
    return PkgInfo(
        url=url,
        name=name,
        version=version,
        hash=file_hash,
        description=description,
        build_sys=build_sys,
        languages=languages,
        )


def generate_yaml(pkg_info):
    output = StringIO.StringIO()

    # Header
    output.write('name: %s\n' % pkg_info.name)
    description = '' if pkg_info.description is None else pkg_info.description
    output.write('description: %s\n' % description)
    output.write('version: %s\n\n' % pkg_info.version)

    # Deps
    pkgs = []
    build_pkgs = []

    if pkg_info.build_sys == 'autotools':
        if 'c' in pkg_info.languages:
            build_pkgs.extend([
                'autotools-build',
                'tl:c-compiler',
                'tl:linker',
                ])

    elif pkg_info.build_sys == 'make':
        if 'c' in pkg_info.languages:
            build_pkgs.extend([
                'tl:base',
                'tl:c-compiler',
                'tl:linker',
                'make'
                ])

    if 'c' in pkg_info.languages:
        pkgs.extend([
            'tl:libc'
        ])

    output.write('build-dependencies:\n')
    for pkg in build_pkgs:
        output.write('  - %s\n' % pkg)
    output.write('\n')

    output.write('dependencies:\n')
    for pkg in pkgs:
        output.write('  - %s\n' % pkg)
    output.write('\n')

    # Files
    args = (pkg_info.hash, pkg_info.url)
    output.write('files:\n  %s:\n    url: %s\n\n' % args)

    # Build description
    if pkg_info.build_sys == 'autotools':
        output.write('configure:\n  ./configure --prefix=%(prefix)s\n\n')

    if pkg_info.build_sys in ['autotools', 'make']:
        output.write('build:\n  make -j%(jobs)s\n\n')
        output.write('install:\n  make -j%(jobs)s install\n')

    return output.getvalue()


def url_to_xpd(url):
    """
    Create a basic XPD file based on the given URL.  Write now this only
    supports C & autoconf based based packages.
    """

    with util.temp_dir(suffix='-xpkg-url-to-xpd'):
        pkg_info = get_pkg_info(url)
        xpd_text = generate_yaml(pkg_info)

    return xpd_text
