import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const FIXTURES_DIR = resolve(__dirname, "../../../tests/fixtures/purses");

export function purseFixturePath(name: string): string {
  return resolve(FIXTURES_DIR, `${name}.png`);
}

export const KNOWN_PURSES = [
  "tan-tote", "black-tote", "red-tote", "brown-tote",
  "tan-satchel", "black-satchel", "red-satchel", "green-satchel", "blue-satchel",
  "tan-clutch", "black-clutch", "red-clutch", "brown-clutch", "blue-clutch",
  "tan-hobo", "black-hobo", "green-hobo",
  "tan-backpack", "black-backpack", "blue-backpack",
] as const;

export type PurseName = typeof KNOWN_PURSES[number];
