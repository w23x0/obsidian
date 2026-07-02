#include <iostream>

class Entity
{
public:
	float X, Y;

	Entity()
	{

	}
	Entity(float x, float y)
	{ 
		X = x;
		Y = y;
	}
	void Print()
	{
		std::cout << X << ", " << Y << std::endl;
	}
};

class Log
{
private://如果不想让外部创建Log对象，可以把构造函数私有化
	Log() {}
public:
	Log() = delete;//如果不想让外部创建Log对象，可以把构造函数删除掉
	static void Write()
	{
		 
	}
};

int main()
{
	Log::Write();
	Log e;


	Entity e(5.0f, 6.0f);
	e.Print();
	


	return 0;
}