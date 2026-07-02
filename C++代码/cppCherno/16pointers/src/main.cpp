#include <iostream> 

#define LOG(x) std::cout << x << std::endl;

int main()
{
	int var = 8;
	int* ptr = &var;

	//解指针
	*ptr = 10;//1读地址2寻地址3写数据


	//堆内存管理
	char* buffer = new char[8];//申请8连续字节内存，new返回首地址
	//buffer在栈上，指向堆内存，buffer是一个指针变量，占用4字节（32位系统）或8字节（64位系统）
	memset(buffer, 0, 8);//8字节内存全部置0

	delete[] buffer;//释放8字节内存，之后buffer仍然存在，但指向的内存已经被释放，成为悬空指针





	std::cin.get();
}