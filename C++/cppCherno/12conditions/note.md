反编译：启动后右键
！这只是debug模式下
编译器不优化
相反
常量折叠（在这里会使用的优化）
对于bool的if函数，只要非0即执行if否则跳过，无需添加判断
指针：
nullptr值就是0
if(ptr)即if(ptr==0)
if与else
else if 实际上是一个 else 后面紧跟着一个新的 if 语句
逻辑编程和数学编程
