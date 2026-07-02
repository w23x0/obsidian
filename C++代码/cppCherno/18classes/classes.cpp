//类
#include <iostream>
#define LOG(x) std::cout << x << std::endl

class Player
{
public:
//class默认不公开变量到其他函数

	int x=0, y=0;
	int speed=1;
	//类内部成员初始化,可以直接赋值

	void Move(int xa, int ya)
	{
		x += xa * speed;
		y += ya * speed;
	}
};

int main()
{
	Player player;//在栈分配内存，Player是类，player是对象，实例化了一个Player对象，player是Player类的一个实例
	//即像Player wzh;Player zlm;
	player.x = 5;//点操作符
	LOG(player.x);
	LOG(player.y);
	player.Move(1,1);

	LOG(player.x);
	LOG(player.y);



}