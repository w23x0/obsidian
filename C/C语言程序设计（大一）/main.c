#include <stdio.h>

int gcd(int m,int n)
{
int i,t;
if(m>n)
t=m,m=n,n=t;
for(i=m;i>=1;i--)
if(m%i==0 && n%i==0)
break;
return i;
}

int  main()
{
int a,b,t;
printf("请输入两个正整数：");
scanf("%d%d",&a,&b);
t=gcd(a,b);
printf("最大公约数：%d\n",t);
}