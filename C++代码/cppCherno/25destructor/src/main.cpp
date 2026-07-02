#include <iostream>

class Entity
{
public:
	float X, Y;
	Entity()
	{
		X = 0.0f;
		Y = 0.0f;
		std::cout << "类对象已创建" << std::endl;
	}
	~Entity ()
	{
		std::cout <<"类对象已删除"<< std::endl;
	}

	void Print()
	{
		std::cout << X << ", " << Y << std::endl;
	}
};


int main()
{
	

	Entity e;
	e.Print();



	std::cin.get();
}