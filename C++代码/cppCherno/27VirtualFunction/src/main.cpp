#include <iostream> 
#include <string>
//std::string：这是返回值类型。告诉编译器，这个函数运行完会吐出一个“文本”。

class Entity 
{
public:
	virtual std::string GetName() { return "Entity"; }

};

class Player : public Entity
{
private:
	std::string m_Name;
public:
	//构造函数 实例对象自动执行初始化
	Player(const std::string& name) //写法：初始化列表
		: m_Name(name) {}// 把传进来的参数存到变量里

	std::string GetName() override { return m_Name; }
	   
};

void PrintName(Entity* entity)
{
	std::cout << entity->GetName() << std::endl;
}

int main()
{
	Entity* e = new Entity();
	Player* p = new Player("John");

	PrintName(e);
	PrintName(p);

	std::cin.get();
}
