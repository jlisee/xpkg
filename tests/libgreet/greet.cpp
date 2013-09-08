#include <iostream>
#include "greet.h"

#ifndef GREETING
#define GREETING Hello!
#endif

#define STRINGIZE(x) #x
#define STRINGIZE_VALUE_OF(x) STRINGIZE(x)


namespace greet {

void sayhello()
{
  std::cout << STRINGIZE_VALUE_OF(GREETING) << std::endl;
}

}
