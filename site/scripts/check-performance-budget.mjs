import { readdir, stat } from 'node:fs/promises'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'

const DIST=fileURLToPath(new URL('../dist/assets/',import.meta.url))
const LIMITS={js:350*1024,css:100*1024}

async function files(dir){
  const out=[]
  for(const name of await readdir(dir)){
    const path=join(dir,name)
    const info=await stat(path)
    if(info.isDirectory())out.push(...await files(path))
    else out.push({name,path,bytes:info.size})
  }
  return out
}

const assets=await files(DIST)
const totals={js:0,css:0}
for(const asset of assets){
  if(asset.name.endsWith('.js'))totals.js+=asset.bytes
  if(asset.name.endsWith('.css'))totals.css+=asset.bytes
}
for(const [kind,limit] of Object.entries(LIMITS)){
  const actual=totals[kind]
  console.log(`${kind.toUpperCase()} bundle: ${(actual/1024).toFixed(1)} KiB / ${(limit/1024).toFixed(0)} KiB budget`)
  if(actual>limit){
    console.error(`${kind.toUpperCase()} performance budget exceeded`)
    process.exitCode=1
  }
}
