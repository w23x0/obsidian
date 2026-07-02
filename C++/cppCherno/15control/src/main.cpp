//控制流（continue、break、return）
#include <iostream>

int main()
{
	//continue：跳过本次循环，继续下一次循环
	//break：跳出循环
	//return：结束函数，返回调用处

	for (int i = 0; i < 5; ++i)
	{
		if (i > 2)
			return 0;
		std::cout << "hello " << i << std::endl;
	}

	std::cin.get();//保持窗口，但return会跳过这个
}