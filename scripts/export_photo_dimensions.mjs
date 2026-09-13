// Reserve gallery image space before lazy thumbnails load. No imaging dependency.
import { readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
const folder = new URL('../public/assets/thumbnails/', import.meta.url);
function dimensions(bytes, name) {
  if (bytes[0] !== 0xff || bytes[1] !== 0xd8) throw new Error(`Expected JPEG thumbnail: ${name}`);
  let offset = 2;
  while (offset + 8 < bytes.length) {
    if (bytes[offset++] !== 0xff) throw new Error(`Invalid JPEG marker: ${name}`);
    while (bytes[offset] === 0xff) offset++;
    const marker = bytes[offset++];
    const length = bytes.readUInt16BE(offset);
    if ([0xc0,0xc1,0xc2,0xc3,0xc5,0xc6,0xc7,0xc9,0xca,0xcb,0xcd,0xce,0xcf].includes(marker)) {
      return {width:bytes.readUInt16BE(offset + 5), height:bytes.readUInt16BE(offset + 3)};
    }
    if (length < 2) break;
    offset += length;
  }
  throw new Error(`No JPEG dimensions found: ${name}`);
}
const output = {};
for (const name of readdirSync(folder).filter(name => /\.jpe?g$/i.test(name)).sort()) {
  output[name] = dimensions(readFileSync(new URL(encodeURIComponent(name), folder)), name);
}
writeFileSync(new URL('../data/photo_dimensions.json', import.meta.url), JSON.stringify(output, null, 2) + '\n');
console.log(`[photo dimensions] ${Object.keys(output).length} thumbnails from ${fileURLToPath(folder)}`);
