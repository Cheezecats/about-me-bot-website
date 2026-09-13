import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import ts from 'typescript';
const catalog = JSON.parse(await readFile(new URL('../../data/chat_destinations.json', import.meta.url),'utf8'));
const source = (await readFile(new URL('../../src/lib/chat-destinations.ts', import.meta.url),'utf8')).replace(/import catalog from [^;]+;/, `const catalog = ${JSON.stringify(catalog)};`);
const js = ts.transpileModule(source, {compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext}}).outputText;
const {resolveDestinations, validDestination} = await import(`data:text/javascript;base64,${Buffer.from(js).toString('base64')}`);
test('unknown and duplicate destination IDs cannot create links',()=>{
  assert.deepEqual(resolveDestinations(['unknown','photography','photography']).map(x=>x.id),['photography']);
  assert.deepEqual(resolveDestinations(),[]);
});
test('internal routes remain relative to the router basename; external links use HTTPS',()=>{
  assert.equal(resolveDestinations(['authors-choice'])[0].href,'/photography#authors-choice');
  assert.equal(resolveDestinations(['song-spotify'])[0].kind,'external');
  for (const entry of catalog) assert.equal(validDestination(entry),true,entry.id);
  for (const href of ['javascript:alert(1)','https://evil.example','https://www.youtube.com.evil.example','https://user@www.youtube.com','//www.youtube.com']) {
    assert.equal(validDestination({kind:'external',href}),false);
  }
  assert.equal(validDestination({kind:'internal',href:'//evil.example'}),false);
});

test('every gallery thumbnail reserves its intrinsic dimensions', async () => {
  const sizes = JSON.parse(await readFile(new URL('../../data/photo_dimensions.json', import.meta.url),'utf8'));
  const content = (await readFile(new URL('../../src/data/content.ts', import.meta.url),'utf8')).replaceAll('import.meta.env.BASE_URL', JSON.stringify('/'));
  const compiled = ts.transpileModule(content,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext}}).outputText;
  const {photos} = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`);
  for (const photo of photos) {
    const size = sizes[decodeURIComponent(photo.thumb.split('/').at(-1))];
    assert.ok(size?.width > 0 && size?.height > 0, photo.thumb);
  }
});
