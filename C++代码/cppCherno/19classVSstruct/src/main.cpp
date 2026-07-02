//类
#include <iostream>

#define LOG(x) std::cout << x << std::endl

#define sturct class
//对于c与c++兼容性，可以通过哈希值替换


	struct Player
	{
	

		int x = 0, y = 0;
		int speed = 1;
	
		void Move(int xa, int ya)
		{
			x += xa * speed;
			y += ya * speed;
		}
	};

	struct Vec2
	{
		float x = 0, y = 0;

		void Add(const Vec2& other)
			//const是为了保证函数内部不修改other，为了安全不报错
			// &是为了避免复制整个Vec2对象，提高效率，
			// 相当于Ver2& other = v2,声明一个地址
			//const Vec2&高级只读模式，既保证安全又提高效率
		{
			x += other.x;
			y += other.y;
		}
	};



	int main()
	{
		Player wzh;
		wzh.x = 1;
		wzh.y = 1;
		wzh.Move(2, 2);
		LOG(wzh.x);
		LOG(wzh.y);

		Vec2 v1;
		v1.x = 1.3f, v1.y = 2.4f;
		Vec2 v2;
		v2.x = 3.5f, v2.y = 4.6f;
		v1.Add(v2);
		LOG(v1.x), LOG(v1.y);





	}
	


