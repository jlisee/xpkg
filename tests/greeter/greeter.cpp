#include <string>

#include "greet/greet.h"

int main(int argc, char** argv)
{
  bool sayinstall = false;

  if ((argc == 2) && (std::string("-i") == std::string(argv[1])))
      sayinstall = true;

  if (sayinstall)
  {
    greet::sayinstall();
  }
  else
  {
    greet::sayhello();
  }

  return 0;
}
