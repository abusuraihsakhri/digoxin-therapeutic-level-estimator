// Dependency-free smoke check of the browser calculator's DOM wiring.
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const html = fs.readFileSync(path.join(__dirname,"../web/index.html"),"utf8");
const source = html.match(/<script>([\s\S]*?)<\/script>/);
assert(source, "Inline calculator script must exist");

const defaults = {
  age:"70", weight:"70", scr:"1.4", dose:"125", interval:"24",
  sex:"male", route:"oral", indication:"heart_failure", "measured-level":""
};
const elements = new Map();
function get(id) {
  if (!elements.has(id)) {
    elements.set(id,{
      value:defaults[id] ?? "", textContent:"", hidden:false, disabled:false,
      handlers:{},
      addEventListener:function(name,fn){this.handlers[name]=fn;}
    });
  }
  return elements.get(id);
}
let downloadName = "";
const document = {
  getElementById:get,
  createElement:() => ({
    set download(v) {downloadName=v;},
    set href(v) {},
    click() {}, remove() {}
  }),
  body:{appendChild() {}}
};
vm.runInNewContext(source[1], {
  document, URL:{createObjectURL:()=> "blob:mock", revokeObjectURL() {}},
  Blob:class Blob {constructor(chunks){this.chunks=chunks;}},
  setTimeout:(fn)=>fn(), Number, Math, JSON, Error
},{timeout:3000});
assert.equal(get("error").hidden,true, "Default inputs should calculate");
assert.equal(get("result-crcl").textContent,"48.61");
assert.equal(get("result-cl").textContent,"103.34");
assert.equal(get("result-css").textContent,"0.59");
assert.equal(get("download").disabled,false);
get("download").handlers.click();
assert.equal(downloadName,"digoxin-research-estimate.json");

get("scr").value="0";
get("calculator").handlers.submit({preventDefault() {}});
assert.equal(get("error").hidden,false,"Invalid input must show an error");
assert.equal(get("download").disabled,true,"Invalid input must disable export");
get("scr").value="1.4";
get("measured-level").value="2.6";
get("calculator").handlers.submit({preventDefault() {}});
assert.equal(get("measured").hidden,false);
assert.match(get("interpretation").textContent,/clinical review/i);
console.log("Static calculator: default estimate, validation, level context, export controls OK");
