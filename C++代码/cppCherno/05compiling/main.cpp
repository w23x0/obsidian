void log(const char*);
int main()
{
    log("hello dream");
    return 0;
}

// 预处理器部分
    // 头文件#include <>   （系统）
    // 头文件#include ""   （用户自定义）   

// g++ -E *.cpp -o *.i
// 其他预处理指令
// #define 宏定义（搜索替换）
// #ifdef #ifndef 按照条件选择编译
// #pragma 编译指令



// cpp >> compiling编译 >> object(obj) >> linking连接 >> exe
// g++  -o *.exe *.cpp
// g++  -c *.cpp -o *.obj

// 1. 模拟“预处理到文件” (Preprocess to a File)
// 视频中他在菜单里点开关，在 Linux 终端里你只需要加一个 -E 参数：
// g++ -E main.cpp -o main.i
// 这会生成一个 main.i 文件，打开它，你会看到 #include 被展开后的样子（就像视频 10:22 处展示的那样）。

// 2. 模拟“输出汇编代码” (Assembly Output)
// 视频中他在属性里改“Assembler Output”，你在终端用 -S 参数：
// g++ -S main.cpp -o main.s
// 这会生成 main.s 汇编文件，你可以用文本编辑器（或 Obsidian）打开看 CPU 指令。

// 3. 模拟“开启/关闭优化” (Optimization)
// 他在下拉菜单选 Maximize Speed，你直接改参数：
// Debug 模式（无优化）: g++ -O0 main.cpp
// Release 模式（最高优化）: g++ -O3 main.cpp