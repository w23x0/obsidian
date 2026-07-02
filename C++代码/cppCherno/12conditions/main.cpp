#include <iostream>
#include "log.h"

int main()
{
	int x = 5;
	bool a = x == 5;
	if (a)
	{
		Log("hi!");
	}

	//简化写法
	if (x == 5)
		Log("hello");
	//特殊用法，检查指针是否为0
	const char* ptr = nullptr;
	//指针知识

	if (ptr)//if只关心是否为0false,是就转跳
		Log(ptr);
	else
		Log("ptr is null");
	//非0可用!ptr
	if (!ptr)
		Log("is no nullptr");




	std::cin.get();
}