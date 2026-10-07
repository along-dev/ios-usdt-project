import { generateDgaDomains } from '../plugins/channel/services/dga.js';
const [, , seed, countStr] = process.argv;
if (!seed) {
    console.error('Usage: npx tsx src/cli/generate-dga.ts <seed> [count]');
    process.exit(1);
}
const count = parseInt(countStr || '32');
const domains = generateDgaDomains(seed, count);
domains.forEach((d, i) => console.log(`${i + 1}. ${d}`));
//# sourceMappingURL=generate-dga.js.map