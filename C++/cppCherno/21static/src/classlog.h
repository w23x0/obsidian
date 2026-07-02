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
	int m_LogLevel = LogLevelInfo;

public:
	void SetLevel(int level)
	{
		m_LogLevel = level;
	}
	void Error(const char* message)
	{
		if (m_LogLevel >= LogLevelError)
			LOG("[Error]:" << message);
	}
	void Warn(const char* message)
	{
		if (m_LogLevel >= LogLevelWarning)
			LOG("[Warn]:" << message);
	}
	void Info(const char* message)
	{
		if (m_LogLevel >= LogLevelInfo)
			LOG("[Info]:" << message);
	}
};

