
1. 1. 类外部的 static
当你在类或结构体之外定义 static 变量或函数时
它的作用域被限制在当前的翻译单元（即当前的 .cpp 文件）内 
避免冲突：如果你在两个不同的文件里定义了同名的全局变量，链接器会报错
但如果加了 static，它们就不会互相干扰

2. 类内部的 static
共享内存：类内部的 static 变量在所有对象实例之间共享。
无论你创建了多少个 Log 对象，static 变量在内存中只有一份副本

无需实例访问：这就是你之前问的“为什么必须加 log.”
如果你把 LogLevelWarning 改为 static，你就可以直接用 Log::LogLevelWarning 访问，
而不需要创建一个 Log log; 对象