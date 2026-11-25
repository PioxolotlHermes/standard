// Shared ESLint flat config (R8). Synced by `standard sync`; do not edit in the consuming repo.
// Usage in eslint.config.js:  import { standardConfig } from './eslint.standard.js';
//                             export default standardConfig({ extra: [ /* repo-specific rules */ ] });
import js from '@eslint/js';
import globals from 'globals';
import ts from 'typescript-eslint';

// eslint-plugin-svelte is optional: used when installed.
let svelte = null;
try {
	svelte = (await import('eslint-plugin-svelte')).default;
} catch {
	svelte = null;
}

const XSS = 'XSS: text from data only via {expression} / textContent';
const SOURCES = ['src/**/*.ts', 'src/**/*.js', 'src/**/*.mjs', 'src/**/*.svelte'];
const TESTS = ['**/*.test.ts', '**/*.spec.ts', 'e2e*/**/*.ts'];
const PHYSICAL = { skipBlankLines: false, skipComments: false };

export function standardConfig({ ignores = [], extra = [] } = {}) {
	return ts.config(
		{ ignores: ['build/', '.svelte-kit/', 'node_modules/', ...ignores] },
		js.configs.recommended,
		...ts.configs.strict,
		...(svelte ? svelte.configs.recommended : []),
		{ languageOptions: { globals: { ...globals.browser, ...globals.node } } },
		...(svelte
			? [
					{
						files: ['**/*.svelte', '**/*.svelte.ts'],
						languageOptions: { parserOptions: { parser: ts.parser, extraFileExtensions: ['.svelte'] } }
					}
				]
			: []),
		{
			files: SOURCES,
			rules: {
				// R2 / R3 / R4: small files, small functions, low complexity
				'max-lines': ['error', { max: 200, ...PHYSICAL }],
				'max-lines-per-function': ['error', { max: 50, ...PHYSICAL }],
				complexity: ['error', 12],
				eqeqeq: ['error', 'always', { null: 'ignore' }],
				'no-implied-eval': 'error',
				'no-new-func': 'error',
				// zero HTML from data
				'no-restricted-properties': [
					'error',
					{ object: 'document', property: 'write', message: XSS },
					{ property: 'innerHTML', message: XSS },
					{ property: 'outerHTML', message: XSS },
					{ property: 'insertAdjacentHTML', message: XSS }
				],
				...(svelte ? { 'svelte/no-at-html-tags': 'error' } : {})
			}
		},
		{
			// tests: 300 lines, no per-function limit (describe blocks are long by nature)
			files: TESTS,
			rules: { 'max-lines': ['error', { max: 300, ...PHYSICAL }], 'max-lines-per-function': 'off' }
		},
		{
			// generated files only: named *.generated.* AND first line "// generated" (the checker verifies both)
			files: ['src/**/*.generated.ts'],
			rules: { 'max-lines': 'off' }
		},
		...extra
	);
}
