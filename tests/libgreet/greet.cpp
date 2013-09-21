#include <iostream>
#include "greet.h"

#ifndef GREETING
#define GREETING Hello!
#endif

#define STRINGIZE(x) #x
#define STRINGIZE_VALUE_OF(x) STRINGIZE(x)


namespace greet {

void say_hello()
{
  std::cout << STRINGIZE_VALUE_OF(GREETING) << std::endl;
}

void say_install()
{
  std::cout << "Hello from (bin): " << STRINGIZE_VALUE_OF(INSTALL_DIR)
            << std::endl;
}

void say_long_install()
{
  std::cout << "Hello from (bin/greet): "
            << STRINGIZE_VALUE_OF(INSTALL_DIR) "/greet"
            << std::endl;
}

}
