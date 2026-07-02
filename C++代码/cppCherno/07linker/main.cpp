#include <iostream>

void Log(const char* message)

int Multiply(int a, int b)
{
    Log("Multiply");
    return a * b ;
}

// undefined reference to `WinMain'
// 找不到程序入口
int main()
{

    std::cout << Multiply(5, 8) << std::endl;
    std::cin.get();
}
// static library (.a)  静态库 只在此文件里有效，编译时会被复制到目标文件中
// dynamic library (.dll) 动态库 在运行时加载，多个程序可以共享同一个动态库，节省内存和磁盘空间


// 还没看懂算了