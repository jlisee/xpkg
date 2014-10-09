#! /bin/bash

# Author: Joseph Lisee <jlisee@gmail.com>
# Copies all the Ubuntu libc files so we can bring them into our xpkg
# enviornment

dest_dir=$1

packages=(
    libc6
    libc6-dev
    libc-bin
    libc-dev-bin
    linux-libc-dev
)

for package in "${packages[@]}"; do
    for file in $(dpkg -L $package); do
        # Ignore the .
        if [ $file == "/." ]; then
            continue
        fi

        # Echo our file
        echo $file
    done
done
