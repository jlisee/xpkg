#include <string>

#include "greet/greet.h"

int main(int argc, char** argv)
{
  bool say_install = false;
  bool long_install = false;
  bool say_config = false;
  bool print_double = false;

  if ((argc == 2) && (std::string("-i") == std::string(argv[1])))
  {
      say_install = true;
  }
  else if ((argc == 2) && (std::string("-l") == std::string(argv[1])))
  {
      long_install = true;
  }
  else if ((argc == 2) && (std::string("-c") == std::string(argv[1])))
  {
      say_config = true;
  }
  else if ((argc == 2) && (std::string("-d") == std::string(argv[1])))
  {
      print_double = true;
  }

  if (say_install)
  {
    greet::say_install();
  }
  else if (long_install)
  {
    greet::say_long_install();
  }
  else if (say_config)
  {
    greet::say_config_install();
  }
  else if (print_double)
  {
    greet::print_double_install();
  }
  else
  {
    greet::say_hello();
  }

  return 0;
}
