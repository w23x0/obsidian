#include <iostream>
#include "function.h"
#include <string>

void PrintName(Team* team)
{
	std::cout << team->GetName() << std::endl;
}


int main()
{
	std::string nameA1;
	std::cin >> nameA1;
	Team* A1 = new Team();
	A1->SetName(nameA1);

	std::string Name;
	std::cin >> Name;
	Team* A2 = new TeamPlay();
	A2->SetName(Name);

	PrintName(A1);
	PrintName(A2);

	std::cin.get();
}