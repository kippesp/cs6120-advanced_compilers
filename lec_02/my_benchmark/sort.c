#include <stdio.h>

void printTable(int n, int* table)
{
  for (int idx_i = 0; idx_i < n; idx_i++)
    printf("%i\n", table[idx_i]);
}

void sort(int n, int* table)
{
  for (int idx_i = 0; idx_i < n; idx_i++)
  {
    int min_idx = idx_i;

    for (int idx_j = idx_i + 1; idx_j < n; idx_j++)
    {
      int searchValue = table[idx_j];
      int minValue = table[min_idx];

      if (searchValue < minValue)
        min_idx = idx_j;
    }

    if (idx_i != min_idx)
    {
      int tmp = table[idx_i];
      table[idx_i] = table[min_idx];
      table[min_idx] = tmp;
    }
  }
}

int main()
{
  int table[10] = {7, 2, 3, 0, 1, 9, 1, 6, 5, 4};

  sort(10, table);
  printTable(10, table);

  return 0;
}
