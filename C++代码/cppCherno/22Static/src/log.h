#pragma once
#include <iostream>
#define LOG(x) std::cout << x << std::endl
class Log
{
public:
	static const int LogLevelError = 0;
	static const int LogLevelWarning = 1;
	static const int LogLevelInfo = 2;

private:
	inline static int m_LogLevel = LogLevelInfo;
	//static不能在头文件中定义变量，必须在cpp文件中定义
	//加上inline后，允许在头文件中定义变量，编译器会处理重复定义的问题

public:
	static void SetLevel(int level)
	{
		m_LogLevel = level;
	}
	static void Error(const char* message)
	{
		if (m_LogLevel >= LogLevelError)
			LOG("[Error]:" << message);
	}
	static void Warn(const char* message)
	{
		if (m_LogLevel >= LogLevelWarning)
			LOG("[Warn]:" << message);
	}
	static void Info(const char* message)
	{
		if (m_LogLevel >= LogLevelInfo)
			LOG("[Info]:" << message);
	}
};

