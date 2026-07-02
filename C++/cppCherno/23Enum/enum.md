Enum是Enumeration（枚举）的缩写
简单来说，它就是给一堆整数起个可读的名字
static const int就相当于enum
作用是创建一个受限的、有名字的整数集合
在int里main函数输入Log::SetLevel(0);合法
但是enum LogLevel { Debug, Info, Warning, Error };就不合法了
Enum 的本质：它是“防呆”的