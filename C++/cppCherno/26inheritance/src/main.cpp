#include <iostream> 

class Entity {
public:
	float X , Y ;

	void Move (float xa, float ya) 
	{
		X += xa;
		Y += ya;
	}
};

class Player : public Entity
{
public:
	const char* Name;
	
	void PrintName ()
	{
		std::cout << Name << std::endl;
	}

	void PrintPosition ()
	{
		std::cout << X << ", " << Y << std::endl;
	}

};
int main () 
{
	Player player;
	player.Name = "John";
	player.PrintName();
	player.X = 0;
	player.Y = 0;
	player.Move(5, 5);
	player.PrintPosition();



	std::cin.get();
}
