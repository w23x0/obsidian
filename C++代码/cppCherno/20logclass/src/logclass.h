#pragma once
#include <iostream>
//这节课设计日志类

class Log
{
public:
	const int LogLevelError = 0;//错误
	const int LogLevelWarning = 1;//警告
	const int LogLevelInfo = 2;//信息
	//const是为了保证这些值不被修改，防止误操作导致日志级别混乱

private:
	int m_LogLevel = LogLevelInfo;//默认日志级别为信息级别，输出所有日志

public:
	void SetLevel(int level)
	{
		m_LogLevel = level;
	}
	void Error(const char* message)
	{
		if (m_LogLevel >= LogLevelError)
			std::cout << "[Error]:" << message << std::endl;
	}
	void Warn(const char* message)//指向常量字符的指针,不能修改message指向的内容
	{
		if (m_LogLevel >= LogLevelWarning)
			std::cout << "[Warn]:" << message << std::endl;
	}
	void Info(const char* message)
	{
		if (m_LogLevel >= LogLevelInfo)
			std::cout << "[Info]:" << message << std::endl;
	}
};
//类结尾需要加分号