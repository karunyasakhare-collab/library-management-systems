const globals = require("globals");

module.exports = [
  {
    files: ["static/script.js"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "script",
      globals: { ...globals.browser },
    },
    rules: {},
  },
];
