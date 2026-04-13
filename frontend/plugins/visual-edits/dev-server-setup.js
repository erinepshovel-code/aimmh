// "lines of code":"10","lines of commented":"0"
const fs = require('fs');
const path = require('path');
const Module = require('module');

const PART_FILES = ['dev-server-setup.js.part01.txt', 'dev-server-setup.js.part02.txt', 'dev-server-setup.js.part03.txt'];
const EXEC_SOURCE = PART_FILES.map((name) => fs.readFileSync(path.join(__dirname, name), 'utf8')).join('');

const mod = new Module(__filename, module.parent);
mod.filename = __filename;
mod.paths = Module._nodeModulePaths(__dirname);
mod._compile(EXEC_SOURCE, __filename);
module.exports = mod.exports;
// "lines of code":"10","lines of commented":"0"
