#pragma once
#include <iostream>
#define LOG(x) std::cout << x << std::endl
class Log
{
public:
	enum Level
	{
		LevelError, LevelWarning, LevelInfo
	};

private:
	inline static int m_LogLevel = LevelInfo;

public:
	static void SetLevel(Level level)
	{
		m_LogLevel = level;
	}
	static void Error(const char* message)
	{
		if (m_LogLevel >= LevelError)
			LOG("[Error]:" << message);
	}
	static void Warn(const char* message)
	{
		if (m_LogLevel >= LevelWarning)
			LOG("[Warn]:" << message);
	}
	static void Info(const char* message)
	{
		if (m_LogLevel >= LevelInfo)
			LOG("[Info]:" << message);
	}
};

