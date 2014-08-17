#include <stdio.h>

// Print an embedded binary string replace after the build
void print_hard();

// Embedded hard coded string we are going to replace
static const char* hard_path = "/i/am/a/bad/path";

int main(int argc, char** argv)
{
  int print_hard = 0;

  if ((argc == 2) && (strcmp("-h", argv[1]) == 0))
  {
      print_hard = 1;
  }

  if (print_hard)
  {
    printf("Path: %s\n", hard_path);
  }
  else
  {
    printf("I'm %s\n", argv[0]);
  }

  return 0;
}
