#include "log.h"
#include <iostream>


void Log(const char* message)
{
    std::cout << message << std::endl;
}

void initlog()
{
    Log("Hello!");
}