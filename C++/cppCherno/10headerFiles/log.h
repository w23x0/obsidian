// 头文件保护机制
#pragma once
// 确保同一个头文件在一个翻译单元中只被包含一次，防止结构体或类的重定义错误

// 条件编译指令
// #ifndef LOG_H
// #define LOG_H





void initlog();
void Log(const char* message);