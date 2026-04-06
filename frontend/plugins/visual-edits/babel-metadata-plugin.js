const fs = require('fs');
const path = require('path');
const Module = require('module');

const PART_FILES = ['babel-metadata-plugin.js.part01.txt', 'babel-metadata-plugin.js.part02.txt', 'babel-metadata-plugin.js.part03.txt', 'babel-metadata-plugin.js.part04.txt', 'babel-metadata-plugin.js.part05.txt', 'babel-metadata-plugin.js.part06.txt', 'babel-metadata-plugin.js.part07.txt'];
const EXEC_SOURCE = PART_FILES.map((name) => fs.readFileSync(path.join(__dirname, name), 'utf8')).join('');

const mod = new Module(__filename, module.parent);
mod.filename = __filename;
mod.paths = Module._nodeModulePaths(__dirname);
mod._compile(EXEC_SOURCE, __filename);
module.exports = mod.exports;
