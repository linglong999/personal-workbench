/* eslint-env node */
module.exports = {
  root: true,
  env: { browser: true, es2022: true },
  parserOptions: { ecmaVersion: 'latest', sourceType: 'module', ecmaFeatures: { jsx: true } },
  plugins: ['react', 'react-hooks'],
  extends: ['eslint:recommended', 'plugin:react/recommended', 'plugin:react-hooks/recommended'],
  settings: { react: { version: 'detect' } },
  rules: {
    'react/prop-types': 'off',
    // GridStack 布局属性（gs-x/gs-y/gs-w/gs-h/gs-id）
    'react/no-unknown-property': ['error', { ignore: ['gs-x', 'gs-y', 'gs-w', 'gs-h', 'gs-id'] }],
  },
  ignorePatterns: ['dist', 'node_modules'],
}
