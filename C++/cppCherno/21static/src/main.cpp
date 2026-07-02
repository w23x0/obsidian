#include "classlog.h"
#include <iostream>

int main()
{
	Log log;
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