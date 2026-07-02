#include <iostream>
#include "log.h"

int main()
{
  
    Log::SetLevel(Log::LevelWarning);

    Log::Warn("Using Enums now!");

    return 0;
}