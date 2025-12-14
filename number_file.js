const fs=require('fs');
const file=process.argv[1];
if (!file) {console.error('Usage: node number_file.js <file>');process.exit(1);}
const lines=fs.readFileSync(file,'utf8').split(/\r?\n/);
for (let i=0;i<lines.length;i++) {
  console.log((i+1)+':'+lines[i]);
}
