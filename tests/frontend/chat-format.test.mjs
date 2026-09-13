import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import ts from 'typescript';
const source = await readFile(new URL('../../src/lib/chat-format.ts', import.meta.url), 'utf8');
const js = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } }).outputText;
const { parseChatBlocks, isNearBottom } = await import(`data:text/javascript;base64,${Buffer.from(js).toString('base64')}`);

test('numbered answers preserve ordinals and separate bullet lists', () => {
  assert.deepEqual(parseChatBlocks('3. Third\r\n4. Fourth\n- A\n- B'), [
    {kind:'list', ordered:true, start:3, items:['Third','Fourth']},
    {kind:'list', ordered:false, start:1, items:['A','B']},
  ]);
});
test('tables require a separator and preserve column content', () => {
  assert.deepEqual(parseChatBlocks('| Subject | Detail |\n| --- | :---: |\n| Camera | Nikon Z8 |')[0],
    {kind:'table',headers:['Subject','Detail'],rows:[['Camera','Nikon Z8']]});
  assert.equal(parseChatBlocks('This | is prose')[0].kind, 'paragraph');
});
test('code fences preserve literal content without interpreting markup', () => {
  assert.deepEqual(parseChatBlocks('```html\n<script>alert(1)</script>\n- literal\n```'),
    [{kind:'code',text:'<script>alert(1)</script>\n- literal'}]);
  assert.equal(parseChatBlocks('<img onerror="bad()">')[0].text, '<img onerror="bad()">');
});
test('auto-follow distinguishes reading history from being near the bottom', () => {
  assert.equal(isNearBottom(0, 1000, 500), false);
  assert.equal(isNearBottom(440, 1000, 500), true);
  assert.equal(isNearBottom(436, 1000, 500), false);
  assert.equal(isNearBottom(0, 200, 500), true);
});
