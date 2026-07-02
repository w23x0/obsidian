#include <iostream>
#include "logclass.h"
#define LOG(x) std::cout << x << std::endl
int main()
{
	Log log;//实例化日志类对象
	log.SetLevel(log.LogLevelError);
	log.Warn("warn");
	log.Error("error");
	log.Info("info");
	LOG("-------------");
	log.SetLevel(log.LogLevelWarning);
	log.Warn("warn");
	log.Error("error");
	log.Info("info");
	LOG("-------------");
	log.SetLevel(log.LogLevelInfo);
	log.Warn("warn");
	log.Error("error");
	log.Info("info");
}