//类内部的 static
#include <iostream>
#include "log.h"

int main()
{
	Log log;
	Log log2;
	log.SetLevel(Log::LogLevelError);
	log.Warn("warn");
	log.Error("error");
	log.Info("info");
	log2.Warn("warn");
	log2.Error("error");
	log2.Info("info");
	LOG("-------------");
	log.SetLevel(Log::LogLevelWarning);
	log.Warn("warn");
	log.Error("error");
	log.Info("info");
	log2.Warn("warn");
	log2.Error("error");
	log2.Info("info");
	LOG("-------------");
	log.SetLevel(Log::LogLevelInfo);
	log.Warn("warn");
	log.Error("error");
	log.Info("info");
	log2.Warn("warn");
	log2.Error("error");
	log2.Info("info");

	LOG("-------------");
	Log::SetLevel(Log::LogLevelError);
	Log::Warn("warn");
	Log::Error("error");
	Log::Info("info");
	LOG("-------------");
	Log::SetLevel(Log::LogLevelWarning);
	Log::Warn("warn");
	Log::Error("error");
	Log::Info("info");
	LOG("-------------");
	Log::SetLevel(Log::LogLevelInfo);
	Log::Warn("warn");
	Log::Error("error");
	Log::Info("info");
}