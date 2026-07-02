#include <iostream>
//引用只不过是指针的语法糖
#define LOG(x) std::cout << x << std::endl;

void wang(int& b)
{
	b++;
}

int main()
{
	int a = 5;
	wang(a);

	LOG(a);

	std::cin.get();
}