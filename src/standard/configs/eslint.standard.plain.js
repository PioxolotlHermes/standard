// Shared ESLint flat config for plain-JavaScript repos (R8). Synced by `standard sync` as eslint.standard.js; do not edit
// in the consuming repo. Same rules as the TypeScript variant (eslint.standard.js shipped for repos with TypeScript),
// without typescript-eslint and svelte.
// Usage in eslint.config.js:  import { standardConfig } from './eslint.standard.js';
//                             export default standardConfig({ sources: ['app/**/*.js'], extra: [ /* repo rules */ ] });
// Options: ignores (extra ignore globs), sources (globs the R2/R3/R4 limits apply to), extra (more flat configs).
import js from '@eslint/js';
import globals from 'globals';

const XSS = 'XSS: text from data only via {expression} / textContent';
const SOURCES = ['src/**/*.js', 'src/**/*.mjs'];
const TESTS = ['**/*.test.js', '**/*.spec.js', 'tests/**/*.js', 'e2e*/**/*.js'];
const PHYSICAL = { skipBlankLines: false, skipComments: false };

export function standardConfig({ ignores = [], sources = SOURCES, extra = [] } = {}) {
	return [
		{ ignores: ['build/', 'node_modules/', ...ignores] },
		js.configs.recommended,
		{
			languageOptions: { ecmaVersion: 'latest', sourceType: 'module', globals: { ...globals.browser, ...globals.node } }
		},
		{
			files: sources,
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
				]
			}
		},
		{
			// tests: 300 lines, no per-function limit (describe blocks are long by nature)
			files: TESTS,
			rules: { 'max-lines': ['error', { max: 300, ...PHYSICAL }], 'max-lines-per-function': 'off' }
		},
		...extra
	];
}
