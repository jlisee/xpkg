# Author: Joseph Lisee <jlisee@gmail.com>

# Python Imports
import hashlib
import os
import shutil

# Project Imports
from xpkg import paths
from xpkg import util

# Get the hash types
valid_hash_types = set(['md5', 'sha1', 'sha224', 'sha256', 'sha384', 'sha512'])

def fetch_file(filehash, url):
    """
    Download the desired URL with the given hash
    """

    # Make sure cache exists
    cache_dir = paths.local_cache_dir()

    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    # Get the information we need to do the hashing
    hash_typename, hex_hash = filehash.split('-')

    hash_type = getattr(hashlib, hash_typename)

    have_hash = len(hex_hash) > 0


    # Determine if we have a hash to check against in our cache
    if have_hash:
        # Get the path where the file will be placed in our cache
        cache_path = os.path.join(cache_dir, filehash)

        # See if we need to download the file
        download_file = not os.path.exists(cache_path)

        check_file = not download_file
    else:
        # We don't have the file so download the file here and move it into
        # our cache
        download_file = False
        check_file = False

        with util.temp_dir(suffix='-xpkg-url-hash'):
            local_path = util.fetch_url(url, 'temp_download')

            hex_hash = util.hash_file(open(local_path), hash_type=hash_type)

            cache_path = os.path.join(cache_dir, filehash + hex_hash)

            shutil.move(local_path, cache_path)

    if check_file:
        # Lets verify the hash of the existing file, it's mostly ok to do this
        # because we need to read the file off disk to unpack it and the OS will
        # cache it.

        current_hash = util.hash_file(open(cache_path),
                                      hash_type=hash_type)

        # Check if the hashes don't match and if they don't make sure we can the
        # file
        if current_hash != hex_hash:
            download_file = True

    # Download if needed
    if download_file:
        p = util.fetch_url(url, cache_path)
        print url,p

    # If the user provided a hash double check that it matches
    if have_hash:
        current_hash = util.hash_file(open(cache_path),
                                      hash_type=hash_type)

        if current_hash != hex_hash:
            args (hex_hash, current_hash, url)
            raise BaseException("Error given hash '%s' != actual '%s': %s")

    return cache_path
