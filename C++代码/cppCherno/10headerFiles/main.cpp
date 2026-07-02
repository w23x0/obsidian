#include <iostream> //c头文件带.h而c++没有 所以别感到奇怪
#include "log.h"
// <> 是系统头文件仅用于编译器包含路径，"" 是用户自定义头文件适用于所有情况
// “../” 是相对路径，表示上一级目录




int main()
{
    initlog();
    Log("Hello, Log!");
    std::cin.get();
}