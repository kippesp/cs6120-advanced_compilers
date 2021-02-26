# POC

a = 0x12345fedcba00077

hex = '0123456789abcdef'

s = [''] * 16

acc = a

R = list(range(0,16))
R.reverse()

for d in R:
  s[d] = hex[acc & 0xf]
  acc = acc >> 4

print("0x%x" % a)
print(''.join(s))
