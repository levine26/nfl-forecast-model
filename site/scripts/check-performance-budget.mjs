import { readFile, readdir, stat } from 'node:fs/promises'
import { basename, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { gzipSync } from 'node:zlib'

const DIST_ROOT=fileURLToPath(new URL('../dist/',import.meta.url))
const ASSETS=join(DIST_ROOT,'assets')
const LIMITS={
  entryRaw:450*1024,
  entryGzip:140*1024,
  lazyRaw:300*1024,
  cssTotal:100*1024,
}

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

function fail(label,actual,limit){
  console.log(`${label}: ${(actual/1024).toFixed(1)} KiB / ${(limit/1024).toFixed(0)} KiB budget`)
  if(actual>limit){
    console.error(`${label} performance budget exceeded`)
    process.exitCode=1
  }
}

const html=await readFile(join(DIST_ROOT,'index.html'),'utf8')
const scriptMatch=html.match(/<script[^>]+type=["']module["'][^>]+src=["']([^"']+\.js)["']/i)
if(!scriptMatch)throw new Error('Could not identify initial module entry from dist/index.html')
const entryName=basename(scriptMatch[1])
const assets=await files(ASSETS)
const js=assets.filter(asset=>asset.name.endsWith('.js'))
const css=assets.filter(asset=>asset.name.endsWith('.css'))
const entry=js.find(asset=>asset.name===entryName)
if(!entry)throw new Error(`Initial entry chunk ${entryName} not found in dist/assets`)
const entryBody=await readFile(entry.path)
const lazy=js.filter(asset=>asset.name!==entryName)
const largestLazy=lazy.length?Math.max(...lazy.map(asset=>asset.bytes)):0
const cssTotal=css.reduce((sum,asset)=>sum+asset.bytes,0)

fail('Initial JS raw',entry.bytes,LIMITS.entryRaw)
fail('Initial JS gzip',gzipSync(entryBody).byteLength,LIMITS.entryGzip)
fail('Largest lazy JS chunk',largestLazy,LIMITS.lazyRaw)
fail('CSS total',cssTotal,LIMITS.cssTotal)
