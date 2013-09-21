#include <iostream>
#include <fstream>

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

void say_config_install()
{
  // Path to configuration file
  static const char* conf_path =
    STRINGIZE_VALUE_OF(INSTALL_DIR) "/share/libgreet/settings.conf";

  // Open configuration file
  std::ifstream conf(conf_path, std::ifstream::in);

  // Read line by line to find our greeting
  std::string greeting = "ERROR: could not find \"greeting\" in file";

  for( std::string line; getline( conf, line ); )
  {
    // Ignores lines that start with "#"
    if (line[0] == '#')
      continue;

    // Split line based on "="
    std::size_t pos = line.find('=');

    if (std::string::npos != pos)
    {
      // Read in the first part
      std::string key = line.substr(0, pos);

      // Grab the second half the greeting line
      if (key == "greeting")
      {
        greeting = line.substr(pos + 1, line.size() - pos - 1);
      }
    }
  }

  // Print our greeting, or an error
  std::cout << "Hello conf (" << conf_path << "): " << greeting << std::endl;
}

}
