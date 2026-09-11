/**
 * openapi-generator 7.9.0 emits `import { XToJSONTyped } from './X'` in every
 * model that references a oneOf/anyOf union, but never emits that function in
 * the union's own file, so a freshly generated client does not type-check and
 * `npm run build` fails at `tsc -b` before Vite runs.
 *
 * This adds the missing export. For a union it is exactly the untyped variant:
 * XToJSON already discriminates with the instanceOf helpers, and the
 * ignoreDiscriminator argument has nothing to act on.
 *
 * Run from the repo root, after the generator. Re-running it is a no-op.
 */

import { readdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const MODELS_DIR = "src_frontend/api-client/models";

const files = readdirSync(MODELS_DIR).filter((name) => name.endsWith(".ts"));
const sources = new Map(
  files.map((name) => [name, readFileSync(join(MODELS_DIR, name), "utf8")]),
);

const patched = [];

for (const [name, source] of sources) {
  const model = name.slice(0, -3);

  // A union model, i.e. `export type X = A | B;`
  if (!new RegExp(`^export type ${model} = [^;]*\\|`, "m").test(source))
    continue;
  if (source.includes(`export function ${model}ToJSONTyped`)) continue;

  // The shim delegates to ToJSON, so refuse to write one that would not
  // compile rather than trading a missing export for an undefined name.
  if (!source.includes(`export function ${model}ToJSON(`)) continue;

  // Word-boundary matched: a bare substring test would count FooToJSONTyped
  // as an import of ooToJSONTyped.
  const wanted = new RegExp(`\\b${model}ToJSONTyped\\b`);
  const importedElsewhere = [...sources].some(
    ([other, text]) => other !== name && wanted.test(text),
  );
  if (!importedElsewhere) continue;

  const shim = `
export function ${model}ToJSONTyped(value?: ${model} | null, ignoreDiscriminator: boolean = false): any {
    return ${model}ToJSON(value);
}
`;
  writeFileSync(join(MODELS_DIR, name), `${source.trimEnd()}\n${shim}`);
  patched.push(model);
}

console.log(
  patched.length
    ? `Patched missing ToJSONTyped on union model(s): ${patched.join(", ")}`
    : "No union models needed patching.",
);
