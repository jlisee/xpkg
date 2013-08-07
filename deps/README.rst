Build Notes

Files:

  * http://llvm.org/releases/3.3/cfe-3.3.src.tar.gz
  * http://llvm.org/releases/3.3/llvm-3.3.src.tar.gz
  * http://llvm.org/releases/3.3/compiler-rt-3.3.src.tar.gz
  * http://yaml-cpp.googlecode.com/files/yaml-cpp-0.5.1.tar.gz
  * http://www.cmake.org/files/v2.8/cmake-2.8.11.2.tar.gz

Hashes (MD5):

 * 8284891e3e311829b8e44ac813d0c9ef  cfe-3.3.src.tar.gz
 * 6f5d7b8e7534a5d9e1a7664ba63cf882  cmake-2.8.11.2.tar.gz
 * 9c129ce24514467cfe492cf2fed8e2c4  compiler-rt-3.3.src.tar.gz
 * 40564e1dc390f9844f1711c08b08e391  llvm-3.3.src.tar.gz
 * 0fa47a5ed8fedefab766592785c85ee7  yaml-cpp-0.5.1.tar.gz


What I did:

  # Unpack things
  tar xf cfe-3.3.src.tar.gz
  tar xf compiler-rt-3.3.src.tar.gz
  tar xf llvm-3.3.src.tar.gz

  # Moves things into the right place
  mv cfe-3.3.src llvm-3.3.src/tools/clang
  mv compiler-rt-3.3.src llvm-3.3.src/projects/compiler-rt

  # Grab a latest g++
  sudo add-apt-repository ppa:ubuntu-toolchain-r/test

  # Build LLVM/Clang
  CXX=g++-4.8 CC=gcc-4.8 CXXCPP="g++-4.8 -E" ./configure --prefix=/home/jlisee/projects/xpm/env
  make -j4 install

  # Build cmake
  ./bootstrap --prefix=/home/jlisee/projects/xpm/env
  make -j5 install

  # Building boost (TODO: come with our own python)
  ./bootstrap.sh --with-toolset=clang --prefix=/home/jlisee/projects/xpm/env/ --with-libraries=all
  ./b2 --prefix=/home/jlisee/projects/xpm/env/ toolset=clang threading=multi link=shared install

  # Build yaml lib
  ./active-env.py
  mkdir build
  cd build
  cmake .. -DCMAKE_INSTALL_PREFIX=/home/jlisee/projects/xpm/env
  make -j5 install
