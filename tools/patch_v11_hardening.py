from pathlib import Path
import re

p=Path('model-processor-v11.html')
s=p.read_text(encoding='utf-8')

# UI copy: explain the real stable architecture instead of claiming the iPhone will repack 100+ MB GLBs in memory.
s=s.replace("Files above GitHub's 100 MB single-file limit are automatically repacked and their textures downscaled before upload. If they still cannot fit, they are skipped with a clear log instead of breaking the batch.","Small GLBs upload directly. FBX, BLEND, glTF packages, and larger GLBs are staged in small chunks. The FPS repository reconstructs and converts/optimizes them with Blender and glTF Transform, avoiding Safari memory reloads and GitHub's 100 MiB single-file limit.")
s=s.replace('ready runtime assets','prepared / uploadable')
s=s.replace('V11 stable rebuild · recursive folders/ZIPs · FBX/GLB processing · verified preview · organized FPS upload.','V11 hardened pipeline · recursive folders/ZIPs · stable iPhone preview · FBX/BLEND conversion in GitHub Actions · chunked large-file staging · organized FPS upload.')

# Make the runtime state capable of releasing object URLs created for external FBX/glTF textures.
s=s.replace("playing:true,uploading:false};","playing:true,uploading:false,objectURLs:[]};")

# Constants used by preparation, preview and chunked uploads.
needle="const MODEL=new Set(['fbx','glb','gltf']),DEPS=new Set(['png','jpg','jpeg','webp','exr','tga','bmp','ktx2','bin']),SUPPORTED=new Set(['zip','fbx','glb','gltf','blend',...DEPS]);"
replacement=needle+"const MiB=1024*1024,DIRECT_LIMIT=8*MiB,CHUNK_SIZE=4*MiB,PREVIEW_LIMIT=64*MiB;"
assert needle in s, 'constants anchor missing'
s=s.replace(needle,replacement,1)

# Dispose geometry, materials, textures and temporary object URLs between previews.
new_dispose="""function dispose(){if(S.mixer){S.mixer.stopAllAction();try{S.mixer.uncacheRoot(S.obj)}catch{}S.mixer=null}if(S.obj){S.scene.remove(S.obj);S.obj.traverse(o=>{o.geometry?.dispose?.();for(const m of(Array.isArray(o.material)?o.material:[o.material]).filter(Boolean)){for(const v of Object.values(m))if(v?.isTexture)v.dispose?.();m.dispose?.()}});S.obj=null}for(const u of(S.objectURLs||[]))URL.revokeObjectURL(u);S.objectURLs=[]}"""
s,n=re.subn(r"function dispose\(\)\{.*?\}(?=function fit)",new_dispose,s,count=1,flags=re.S)
assert n==1, 'dispose patch failed'

# Resolve external package textures by relative path or basename, but refuse huge browser previews that can make iOS kill/reload Safari.
new_load="""function previewManager(mainPath){const manager=new THREE.LoadingManager(),dir=mainPath.replaceAll('\\\\','/').split('/').slice(0,-1).join('/'),entries=[...S.files.entries()];manager.setURLModifier(url=>{try{const clean=decodeURIComponent(String(url).split('?')[0].split('#')[0]).replace(/^\\.\\//,''),candidate=(dir?dir+'/':'')+clean;let hit=entries.find(([p])=>p===candidate);if(!hit)hit=entries.find(([p])=>base(p).toLowerCase()===base(clean).toLowerCase());if(hit){const u=URL.createObjectURL(hit[1]);S.objectURLs.push(u);return u}}catch{}return url});return manager}
async function loadItem(i){setup();dispose();if(i.file.size>PREVIEW_LIMIT)throw new Error('Large preview skipped ('+bytes(i.file.size)+') to keep iPhone Safari stable. The asset remains uploadable and repository conversion will process it.');const e=ext(i.path),ab=await i.file.arrayBuffer(),manager=previewManager(i.path);let obj,anims=[];if(e==='fbx'){obj=new FBXLoader(manager).parse(ab,'');anims=obj.animations||[]}else if(e==='gltf'){const text=new TextDecoder().decode(ab),gltf=await new Promise((res,rej)=>new GLTFLoader(manager).parse(text,'',res,rej));obj=gltf.scene;anims=gltf.animations||[]}else{const gltf=await new Promise((res,rej)=>new GLTFLoader(manager).parse(ab,'',res,rej));obj=gltf.scene;anims=gltf.animations||[]}S.obj=obj;S.scene.add(obj);fit(obj);if(anims.length){S.mixer=new THREE.AnimationMixer(obj);S.mixer.clipAction(anims[0]).play()}$('#report').textContent=base(i.path)+'\\n'+metrics(obj,anims);return{obj,anims}}"""
s,n=re.subn(r"async function loadItem\(i\)\{.*?\}(?=async function exportGLB)",new_load,s,count=1,flags=re.S)
assert n==1, 'loadItem patch failed'

# Preparation no longer decodes/exports every FBX or huge GLB on the phone. It marks assets for direct upload or repository conversion.
new_prepare="""async function prepare(){if(S.busy||S.uploading)return;S.busy=true;stats();setStatus('Preparing assets without decoding heavy files…','busy');let done=0;try{for(const i of S.items){done++;phase('Preparing '+done+'/'+S.items.length+' · '+base(i.path),Math.round(done/S.items.length*100));i.error='';const e=ext(i.path);if(i.type==='dependency'){i.ready=false;await sleep(0);continue}if(e==='glb'){i.runtime=i.file;i.ready=true;i.mode=i.file.size<=DIRECT_LIMIT?'direct':'ci';log((i.mode==='direct'?'Direct-ready GLB: ':'Repository conversion ready: ')+base(i.path)+' · '+bytes(i.file.size),i.mode==='direct'?'ok':'warn')}else if(e==='fbx'||e==='blend'||e==='gltf'){i.runtime=i.file;i.ready=true;i.mode='ci';log('Repository conversion ready: '+base(i.path)+' · '+e.toUpperCase()+' · package textures preserved','warn')}else{i.ready=false;i.error='Unsupported source format';log('PREP SKIPPED '+base(i.path)+': unsupported source','err')}await sleep(0)}setStatus('Preparation complete. Heavy conversion was moved off iPhone. Ready/uploadable assets: '+S.items.filter(i=>i.ready).length,'good');phase('Preparation complete',100)}finally{S.busy=false;render();stats()}}"""
s,n=re.subn(r"async function prepare\(\)\{.*?\}(?=const b64=)",new_prepare,s,count=1,flags=re.S)
assert n==1, 'prepare patch failed'

# Stable, bounded-memory GitHub upload helpers. Sources are chunked at 4 MiB and converted by a single batch workflow trigger.
helpers="""const partB64=async(file,start,end)=>{const u=new Uint8Array(await file.slice(start,end).arrayBuffer());let out='';for(let i=0;i<u.length;i+=32768)out+=String.fromCharCode(...u.subarray(i,i+32768));return btoa(out)};
const textB64=text=>btoa(unescape(encodeURIComponent(text)));
function pkgRoot(i){const p=i.path.replaceAll('\\\\','/').split('/');p.pop();return p.join('/')}
function relatedDeps(i){const root=pkgRoot(i);return S.items.filter(d=>d.type==='dependency'&&(!root||d.path.startsWith(root+'/')))}
async function put(repo,branch,path,content,token,message){const api='https://api.github.com/repos/'+repo+'/contents/'+safePath(path).split('/').map(encodeURIComponent).join('/');let sha=null;try{const old=await gh(api+'?ref='+encodeURIComponent(branch),{method:'GET'},token);sha=old.sha||null}catch(e){if(!String(e.message).includes('404'))throw e}const body={message,content,branch};if(sha)body.sha=sha;return gh(api,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)},token)}
async function uploadChunks(repo,branch,root,file,token,onProgress){const count=Math.ceil(file.size/CHUNK_SIZE);for(let n=0;n<count;n++){onProgress?.(n+1,count);const content=await partB64(file,n*CHUNK_SIZE,Math.min(file.size,(n+1)*CHUNK_SIZE));await put(repo,branch,root+'/part-'+String(n).padStart(4,'0')+'.bin',content,token,'Project Strike chunk '+(n+1)+'/'+count+' for '+file.name);await sleep(25)}return count}"""
anchor="async function upload(){"
assert anchor in s, 'upload anchor missing'
s=s.replace(anchor,helpers+'\n'+anchor,1)

new_upload="""async function upload(){if(S.uploading||S.busy)return;const token=$('#token').value.trim(),repo=$('#repo').value.trim(),branch=$('#branch').value.trim()||'main';if(!token){setStatus('Paste a GitHub token with Contents read/write permission.','bad');return}if(!/^[^/\\s]+\\/[^/\\s]+$/.test(repo)){setStatus('Repository must be owner/name.','bad');return}if(branch.includes('/')||!branch){setStatus('Branch must be a branch name such as main — not a folder path.','bad');return}const ready=S.items.filter(i=>i.ready&&i.type!=='dependency');if(!ready.length){setStatus('No prepared assets are ready. Tap Prepare Everything first.','bad');return}S.uploading=true;stats();setStatus('Validating repository and starting stable upload…','busy');const job='v11-'+Date.now().toString(36);let ok=0,fail=0,packages=[];try{await gh('https://api.github.com/repos/'+repo+'/branches/'+encodeURIComponent(branch),{method:'GET'},token);log('Validated '+repo+' branch '+branch);for(let n=0;n<ready.length;n++){const i=ready[n],file=i.file,e=ext(i.path),pid=safePath(stem(i.path)).slice(0,45)+'-'+String(n+1).padStart(3,'0');try{if((i.mode==='direct'||(!i.mode&&e==='glb'&&file.size<=DIRECT_LIMIT))&&e==='glb'&&file.size<=DIRECT_LIMIT){phase('Direct upload '+(n+1)+'/'+ready.length+' · '+file.name,Math.round((n+1)/ready.length*90));const path='public/game-assets/'+i.dest+'/'+safePath(file.name);await put(repo,branch,path,await partB64(file,0,file.size),token,'Project Strike asset: '+file.name);ok++;log('UPLOADED '+path);continue}const root='assets-source/project-strike-inbox/'+job+'/'+pid,deps=relatedDeps(i);log('STAGING '+file.name+' in bounded chunks · '+deps.length+' dependency file(s)','warn');const count=await uploadChunks(repo,branch,root+'/chunks',file,token,(p,t)=>phase('Staging '+(n+1)+'/'+ready.length+' · '+file.name+' · chunk '+p+'/'+t,Math.round((n+(p/t))/ready.length*90)));const depMeta=[];for(const d of deps){const df=d.file;if(df.size<=DIRECT_LIMIT){const path=root+'/raw/'+safePath(d.path);await put(repo,branch,path,await partB64(df,0,df.size),token,'Project Strike dependency: '+base(d.path));depMeta.push({path:d.path,staged:path,size:df.size})}else{const depRoot=root+'/dependency-chunks/'+safePath(stem(d.path)),parts=await uploadChunks(repo,branch,depRoot,df,token);depMeta.push({path:d.path,chunkRoot:depRoot,parts,size:df.size})}}const manifest={version:11,jobId:job,packageId:pid,sourceName:base(i.path),sourcePath:i.path,sourceFormat:e,category:i.dest,runtimeName:stem(i.path),chunkCount:count,originalBytes:file.size,dependencies:depMeta};await put(repo,branch,root+'/package.json',textB64(JSON.stringify(manifest,null,2)),token,'Project Strike staged package: '+file.name);packages.push(pid);ok++;log('STAGED '+file.name+' for repository conversion')}catch(e){fail++;log('UPLOAD FAILED '+file.name+': '+e.message,'err')}await sleep(40)}if(packages.length){const marker={version:11,jobId:job,packages,createdAt:new Date().toISOString()};await put(repo,branch,'assets-source/project-strike-batches/'+job+'/ready.json',textB64(JSON.stringify(marker,null,2)),token,'Project Strike batch ready: '+job);log('BATCH READY '+job+' · '+packages.length+' package(s)')}setStatus(`Upload finished. ${ok} accepted, ${fail} failed.${packages.length?' Repository conversion queued.':''}`,fail?'bad':'good');phase('Upload complete',100)}catch(e){setStatus('Upload stopped: '+e.message,'bad');log('UPLOAD STOPPED: '+e.message,'err')}finally{S.uploading=false;stats()}}"""
s,n=re.subn(r"async function upload\(\)\{.*?\}(?=\$\('#filesBtn'\))",new_upload,s,count=1,flags=re.S)
assert n==1, 'upload patch failed'

# Ensure the picker remains unfiltered on iPhone and update the startup log.
s=s.replace("log('Project Strike Asset Processor V11 ready. FBX picker filter removed; >100 MB optimizer enabled.');","log('Project Strike Asset Processor V11 hardened: stable preview guard, bounded 4 MiB staging, repository conversion pipeline.');")

# Update README current architecture note if present.
r=Path('README.md')
if r.exists():
    text=r.read_text(encoding='utf-8')
    marker='## V11 hardened upload pipeline'
    note='''\n\n## V11 hardened upload pipeline\n\nV11 now keeps heavy FBX/BLEND and large-GLB conversion off iPhone Safari. Small GLBs can upload directly; other assets are staged in 4 MiB chunks with their package textures and a single batch marker. The FPS repository reconstructs, converts, optimizes, validates, and commits runtime GLBs through GitHub Actions. Browser preview is deliberately capped for very large models to prevent iOS memory reloads.\n'''
    if marker not in text:
        r.write_text(text.rstrip()+note+'\n',encoding='utf-8')

p.write_text(s,encoding='utf-8')
print('Patched V11 hardening successfully')
