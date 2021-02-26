def sort(num, vals):
  min_idx = -1

  for i in range(0, num):
    min_idx = i
    for j in range(i + 1, num):
      if vals[j] < vals[min_idx]:
        min_idx = j
    if i != min_idx:
      tmp = vals[i]
      vals[i] = vals[min_idx]
      vals[min_idx] = tmp

  print(vals)

sort(10, [7, 2, 3, 0, 1, 9, 1, 6, 5, 4])
