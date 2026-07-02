#include <iostream> 

void Muandlog(int a, int b)
{
    int result = a * b;
    std::cout << result << std::endl;
}
int main() {
    Muandlog(2, 3);
    Muandlog(5, 6);
    Muandlog(10, 20);

    std::cin.get();



}
// 返回值强制性与特例
// 函数的返回值类型必须与函数声明中的返回值类型一致，否则会导致编译错误或运行时错误。
// 非viod必须执行return语句
// main函数是唯一不需要return