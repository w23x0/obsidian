#include <iostream> 
#include <string>

class Printable
{
public:
	virtual std::string GetClassName() = 0; 
};


class Entity :public Printable
{
public:
	std::string GetClassName() override { return "Entity"; }

	virtual std::string GetName() { return "Entity"; }
};


class Player : public Entity
{
private:
	std::string m_Name;
public:
	std::string GetClassName() override { return "Player"; }

	std::string GetName() override { return m_Name; }

	Player(const std::string& name) : m_Name(name) {}
};


class A :public Printable
{
public:
	std::string GetClassName() override { return "A"; }
};

void Print(Printable* obj)
{
	std::cout << obj->GetClassName() << std::endl;
}
void PrintName(Entity* entity)
{
	std::cout << entity->GetName() << std::endl;
}


int main()
{
	Printable* e = new Entity();
	Player* p = new Player("p");
	//PrintName(e);
	//PrintName(p);
	Print(e);
	Print(p);
	Print(new A());
	std::cin.get();
}
