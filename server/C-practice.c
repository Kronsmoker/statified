#include <stdio.h>

int main() {

	int x;
	int y;

	printf("Choose a number: ");
	scanf("%d", &x);

	printf("You chose %d\n", x);


	printf("Choose a number: ");
	scanf("%d", &y);

	printf("You chose %d\n", y);


	int sum = x + y;
	
	printf("Sum = %d\n", x + y);

	for (int i = 0; i <= sum; i++)
	{
		printf("%d\n", i);
	}

	return 0;
}
