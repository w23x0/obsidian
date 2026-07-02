#include <iostream>
#include <array>
#define print(x) std::cout << x << std::endl;

class Entity
{
public:
	static const int exampleSize = 5;
	int example[exampleSize];

	std::array<int, 5> another;
	Entity()
	{
		for (int i = 0; i < another.size(); i++)
			example[i] = i;
	}

int main()
{
	Entity e;
	
	std::cin.get();
}