#ifndef GREET_H
#define GREET_H

namespace greet {

// Prints a basic creating
void say_hello();

// Says hello from it's install location (embedded at build time)
void say_install();

// Says hello from path where the install location is sub string of string
// embedded in the binary.
void say_long_install();

}

#endif
