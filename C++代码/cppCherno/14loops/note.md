	int a = ++i;
00007FF6A2201D1B  mov         eax,dword ptr [i]  
00007FF6A2201D1E  inc         eax  
00007FF6A2201D20  mov         dword ptr [i],eax  
00007FF6A2201D23  mov         eax,dword ptr [i]  
00007FF6A2201D26  mov         dword ptr [a],eax  
	int b = i++;
00007FF6A2201D29  mov         eax,dword ptr [i]  
00007FF6A2201D2C  mov         dword ptr [rbp+134h],eax  
00007FF6A2201D32  mov         eax,dword ptr [i]  
00007FF6A2201D35  inc         eax  
00007FF6A2201D37  mov         dword ptr [i],eax  
00007FF6A2201D3A  mov         eax,dword ptr [rbp+134h]  
00007FF6A2201D40  mov         dword ptr [b],eax  


性能在性能方面，前者（++i）通常比后者（i++）更快