#include <iostream>
#include <string>


class Team
{
	std::string name;

public:
	virtual void SetName(const std::string& N)
	{
		name = N;
	}
	virtual std::string GetName() { return "Team:" + name; }

};

class TeamPlay :public Team
{
	std::string Name;

public:
	void SetName(const std::string& name) override
	{
		Name = name;
	}

	std::string GetName() override { return "Play:" + Name; }


};
