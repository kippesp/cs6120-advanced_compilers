var x: bigint = 0x0012345fedcba077n;
intToHex(x);

function intToHex(x: bigint) {
  //var hex = new String("0123456789abcdef"); 
  //var str = new Array(0);

  for (let i = 15; i >= 0n; i = i - 1n) {
    x = x * 16;
  }

  console.log(x);
}
