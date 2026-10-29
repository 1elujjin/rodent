const $ = id => document.getElementById(id);
let current = 1, pages = 1, sequence = 0, controller;
let activeQuery = '', activeSource = '';
const number = n => n.toLocaleString();
function node(tag, text, cls) {const el=document.createElement(tag);el.textContent=text;if(cls)el.className=cls;return el;}
function flatten(value, prefix='') {
  if(value && typeof value==='object' && !Array.isArray(value)) return Object.entries(value).flatMap(([k,v])=>flatten(v,prefix?`${prefix}.${k}`:k));
  return [[prefix || 'value',typeof value==='object'?JSON.stringify(value):String(value)]];
}
async function load(page=1) {
  const seq=++sequence;
  controller?.abort();controller=new AbortController();
  $('status').textContent='Searching…';$('prev').disabled=$('next').disabled=true;
  try {
    const start=performance.now();
    const response=await fetch('/api/search?'+new URLSearchParams({q:activeQuery,source:activeSource,page}),{signal:controller.signal});
    const data=await response.json();if(!response.ok)throw Error(data.error);
    if(seq!==sequence)return;
    current=data.page;pages=data.pages;$('results').replaceChildren();
    for(const record of data.results){
      const card=node('article','','record'), top=node('div','','record-top');
      const pairs=flatten(record.data);
      const heading=pairs.find(([key])=>['title','name','project','asset'].includes(key));
      const identity=node('div','','record-identity');
      identity.append(node('h2',heading ? heading[1] : `Record ${record.id}`));
      identity.append(node('span',`${record.source} · line ${record.line}`,'record-source'));
      top.append(identity);
      const open=node('button','Details');open.onclick=()=>{ $('provenance').textContent=`${record.source} / line ${record.line} / record ${record.id}`;$('json').textContent=JSON.stringify(record.data,null,2);$('detail').showModal();};
      top.append(open);card.append(top);const grid=node('dl','','record-data');
      for(const [key,value] of pairs.filter(pair=>pair!==heading).slice(0,4)){
        const entry=node('div','','record-field');
        entry.append(node('dt',key),node('dd',value));grid.append(entry);
      }
      const remaining=pairs.length-(heading ? 1 : 0)-grid.children.length;
      open.setAttribute('aria-label',`View details for ${heading ? heading[1] : 'record '+record.id}`);
      if(remaining>0) open.title=`View complete record, including ${remaining} more fields`;
      card.append(grid);$('results').append(card);
    }
    if(!data.total)$('results').append(node('div','No matching records. Try fewer keywords or another dataset.','empty'));
    $('status').textContent=`${number(data.total)} records / ${Math.round(performance.now()-start)} ms`;
    $('page').textContent=`Page ${current} of ${pages}`;
  }catch(error){if(error.name==='AbortError')return;$('status').textContent=error.message || 'Search failed';$('results').replaceChildren(node('div','Could not load results. Check that the local server is running.','empty'));pages=0;}
  finally{if(seq===sequence){$('prev').disabled=current<=1 || !pages;$('next').disabled=current>=pages || !pages;}}
}
$('search').onsubmit=e=>{e.preventDefault();activeQuery=$('query').value.trim();activeSource=$('source').value;load();};
$('source').onchange=()=>{activeSource=$('source').value;activeQuery=$('query').value.trim();load();};
$('prev').onclick=()=>load(current-1);$('next').onclick=()=>load(current+1);
$('close').onclick=()=>$('detail').close();
document.addEventListener('keydown',e=>{if(e.key==='/' && !['INPUT','SELECT','TEXTAREA'].includes(document.activeElement.tagName) && !$('detail').open){e.preventDefault();$('query').focus();}});
(async()=>{try{const response=await fetch('/api/stats');if(!response.ok)throw Error('Index unavailable');const stats=await response.json();$('records').textContent=number(stats.records);$('datasets').textContent=number(stats.sources.length);$('fields').textContent=number(stats.fields.length);for(const source of stats.sources){const option=node('option',source);option.value=source;$('source').append(option);}$('schema-content').textContent='Fields\n'+stats.fields.join('\n')+'\n\nImport warnings (first 100)\n'+(stats.warnings.join('\n')||'None');await load();}catch(e){$('status').textContent=e.message;}})();


// Original side-view pixel rat. White squares only, mirrored without rotation.
(() => {
  const canvas=$('effects'), ctx=canvas.getContext('2d');
  if(!ctx) return;
  const toggle=$('animate');
  const fine=matchMedia('(pointer: fine)');
  let width=0,height=0,frame=0,last=0,mouse=null,rat=null,facing=1;
  const flakes=Array.from({length:42},()=>({x:Math.random(),y:Math.random(),size:Math.random()<.75?1:2,speed:12+Math.random()*24,phase:Math.random()*6.28}));
  const sprite=[
    '.........WWWWW..................',
    '......WWWWWWWWWW................',
    '....WWWWWWWWWWWWWW..WW..........',
    '...WWWWWWWWWWWWWWWWWWWW.........',
    '..WWWWWWWWWWWWWWWWWWWWWW........',
    '..WWWWWWWWWWWWWWWWWWWWWWW.......',
    '.WWWWWWWWWWWWWWWWWWWW..WWWW.....',
    '.WWWWWWWWWWWWWWWWWWWWWWW.WWWW...',
    '..WWWWWWWWWWWWWWWWWWWWWWWWWWWW..',
    '..WWWWWWWWWWWWWWWWWWWWWWWWWWWWW.',
    '...WWWWWWWWWWWWWWWWWWW.....WW...',
    '....WWWWWWWWWW..WWWWW...........',
    '.....WWWWW.......WWW............'
  ];
  function resize(){width=innerWidth;height=innerHeight;const dpr=Math.min(devicePixelRatio||1,2);canvas.width=Math.round(width*dpr);canvas.height=Math.round(height*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);ctx.imageSmoothingEnabled=false;}
  function draw(time){
    frame=0;if(!toggle.checked || document.hidden)return;
    const dt=Math.min((time-last)/1000 || .016,.05);last=time;
    ctx.clearRect(0,0,width,height);
    for(const flake of flakes){
      flake.y+=flake.speed*dt/height;if(flake.y>1.02){flake.y=-.02;flake.x=Math.random();}
      ctx.fillStyle=flake.size===1?'#ffffff50':'#ffffff70';
      ctx.fillRect(Math.round(flake.x*width+Math.sin(time/3000+flake.phase)*12),Math.round(flake.y*height),flake.size,flake.size);
    }
    if(mouse && fine.matches && !$('detail').open){
      if(!rat)rat={x:mouse.x-45,y:mouse.y+45};
      const dx=mouse.x-rat.x,dy=mouse.y-rat.y,dist=Math.hypot(dx,dy);
      if(dist>48){
        const step=(dist-48)*(1-Math.exp(-dt*10));
        rat.x+=dx/dist*step;rat.y+=dy/dist*step;
        if(Math.abs(dx)>8)facing=dx>0?1:-1;
      }
      // Movement renders every animation frame; paws use a four-frame run cycle.
      const pixels=new Map(), colors={W:'#fff'};
      const put=(x,y,color)=>pixels.set(`${x},${y}`,color);
      const tick=Math.floor(time/75), running=dist>51;
      for(let i=0;i<18;i++){
        const bend=Math.round(Math.sin(i*.17+(running?tick:0)*.3)*3);
        put(-14-i,2+bend,'W');
        if(i<6)put(-14-i,3+bend,'W');
      }
      sprite.forEach((row,y)=>[...row].forEach((pixel,x)=>{if(colors[pixel])put(x-15,y-7,pixel);}));
      const stride=running ? [-1,0,1,0][tick%4] : 0;
      for(const [leg,step] of [[-8,stride],[4,-stride]]){
        put(leg,5,'W');put(leg,6,'W');put(leg+step,7,'W');
        put(leg+step+1,7,'W');put(leg+step+2,7,'W');
        put(leg+step+2,6,'W');
      }
      // Integer physical pixels also stay sharp on fractional display scaling.
      const scale=canvas.width/width,block=Math.max(2,Math.round(2*scale));
      const originX=Math.round(rat.x*scale),originY=Math.round(rat.y*scale);
      ctx.save();ctx.setTransform(1,0,0,1,0,0);
      for(const [key,color] of pixels){
        const [x,y]=key.split(',').map(Number);
        const screenX=x*facing,screenY=y;
        ctx.fillStyle=colors[color];ctx.fillRect(originX+screenX*block,originY+screenY*block,block,block);
      }
      ctx.restore();
    }
    frame=requestAnimationFrame(draw);
  }
  function start(){cancelAnimationFrame(frame);frame=0;ctx.clearRect(0,0,width,height);last=0;if(toggle.checked&&!document.hidden)frame=requestAnimationFrame(draw);}
  addEventListener('resize',resize);
  addEventListener('pointermove',e=>{if(e.pointerType==='mouse')mouse={x:e.clientX,y:e.clientY};},{passive:true});
  document.documentElement.addEventListener('pointerleave',()=>{mouse=null;rat=null;});
  document.addEventListener('visibilitychange',start);
  toggle.addEventListener('change',start);
  toggle.checked=true;resize();start();
})();
