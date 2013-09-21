#include <string>

#include "greet/greet.h"

int main(int argc, char** argv)
{
  bool sayinstall = false;
  bool long_install = false;

  if ((argc == 2) && (std::string("-i") == std::string(argv[1])))
  {
      sayinstall = true;
  }
  else if ((argc == 2) && (std::string("-l") == std::string(argv[1])))
  {
      long_install = true;
  }

  if (sayinstall)
  {
    greet::sayinstall();
  }
  else if (long_install)
  {
    greet::say_long_install();
  }
  else
  {
    greet::sayhello();
  }

  return 0;
}
