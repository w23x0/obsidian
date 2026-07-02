#include <iostream> 
#include <string>

class Entity
{
protected:
	int X, Y;
	void Print() {}
public:
	Entity()
	{
		X = 0;
		Print();
	}
};

class Player : public Entity
{
public:
	Player()
	{
		X = 0; 
		Print();
	}
};

int main()
{
	Entity e;
	e.X = 5;
	std::cin.get();
}