const hex=(h,s,l)=>{s/=100;l/=100;const k=n=>(n+h/30)%12,a=s*Math.min(l,1-l),f=n=>l-a*Math.max(-1,Math.min(k(n)-3,Math.min(9-k(n),1)));return '#'+[f(0),f(8),f(4)].map(v=>Math.round(v*255).toString(16).padStart(2,'0')).join('').toUpperCase()};
const lin=v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4;
const rgb=h=>[1,3,5].map(i=>parseInt(h.substr(i,2),16)/255);
const lum=h=>{const c=rgb(h).map(lin);return .2126*c[0]+.7152*c[1]+.0722*c[2]};
const LC={};const lab=h=>LC[h]||(LC[h]=lab0(h));const lab0=h=>{const [r,g,b]=rgb(h).map(lin);const f=t=>t>.008856?Math.cbrt(t):7.787*t+16/116;const x=f((.4124*r+.3576*g+.1805*b)/.95047),y=f(.2126*r+.7152*g+.0722*b),z=f((.0193*r+.1192*g+.9505*b)/1.08883);return [116*y-16,500*(x-y),200*(y-z)]};
const dE=(a,b)=>{const x=lab(a),y=lab(b);return Math.hypot(x[0]-y[0],x[1]-y[1],x[2]-y[2])};
const cr=(a,b)=>{const x=lum(a),y=lum(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05)};
const INK='#0B0E14',WHITE='#FFFFFF';
const okText=c=>Math.max(cr(c,INK),cr(c,WHITE))>=4.5;
const chroma=c=>{const l=lab(c);return Math.hypot(l[1],l[2])};
const hueOf=c=>{const l=lab(c);return (Math.atan2(l[2],l[1])*180/Math.PI+360)%360};
// blue shades only for docker
const BLUES=['#7C9CC9','#6F8FBF','#8AA8D3','#7A9AB8','#94AFD0','#6C8EBF','#84A3C7'];
// jewel actives
const JEWELS={Sapphire:'#5F82D9',Emerald:'#5FB08F',Ruby:'#C7566E',Amethyst:'#9B7FD1',Gold:'#D4B25C',Teal:'#5AAFB0',Coral:'#D9826B',Rose:'#D48AA5'};
// session hues (main colour): name, hue
const MAIN=[['Rose',345],['Coral',10],['Sunset',25],['Amber',40],['Gold',48],['Lime',85],['Fern',120],['Emerald',150],['Mint',165],['Teal',178],['Violet',262],['Purple',280],['Orchid',300],['Magenta',318],['Blush',335]];
const STY=[['Dusty',38,70],['Ash',28,74],['Muted',45,66],['Haze',22,78]];
const POOL0=[];for(const h of [0,25,45,60,90,130,155,175,270,290,310,335])for(const [s,l] of [[36,72],[44,66]])POOL0.push(hex(h,s,l));
const POOL=POOL0.filter(okText);
const INACT=['#8A93A3','#9A9FAA'];
const out=[];console.error("pool",POOL.length);
for(const [mn,mh] of MAIN)for(const [sn,S,L] of STY){
  const session=hex(mh,S,L);if(!okText(session))continue;
  for(const [jn,active] of Object.entries(JEWELS)){ let best=null;
    if(!okText(active))continue;
    if(dE(session,active)<28)continue;
    for(const docker of BLUES){ if(!okText(docker)||dE(docker,active)<26||dE(docker,session)<24)continue;
      for(const inact of INACT){
        const base=[session,active,docker,inact];
        // choose date/time greedily-best pair
        let bd=null;
        for(let i=0;i<POOL.length;i++){const d=POOL[i];const m1=Math.min(...base.map(b=>dE(b,d)));if(m1<22)continue;
          for(let j=i+1;j<POOL.length;j++){const t=POOL[j];const m2=Math.min(...base.map(b=>dE(b,t)),dE(d,t));if(m2<22)continue;
            const score=Math.min(m1,m2);if(!bd||score>bd.score)bd={d,t,score}}}
        if(!bd)continue;
        const m=Math.min(bd.score,dE(session,active),dE(session,docker),dE(active,docker),dE(active,inact),dE(session,inact),dE(docker,inact));
        const sc=m+ Math.min(dE(active,session),60)*.3+chroma(active)*.1;
        if(!best||sc>best.sc)best={sc,m,jn,active,docker,inact,d:bd.d,t:bd.t}
      }}
  if(best)out.push([`${mn} ${sn}`,session,best.active,best.inact,best.docker,best.d,best.t,+best.m.toFixed(0),best.jn]);}
}
const ORDER=['Sapphire','Emerald','Ruby','Amethyst','Gold','Teal','Coral','Rose'];
out.sort((a,b)=>b[7]-a[7]);
const seen=new Set();for(let i=0;i<out.length;i++){const k=out[i][0].split(' ')[0]+out[i][8];if(out[i][7]<22||seen.has(k)){out.splice(i--,1)}else seen.add(k)}
out.sort((a,b)=>ORDER.indexOf(a[8])-ORDER.indexOf(b[8])||b[7]-a[7]);
console.log(out.length);out.forEach((p,i)=>console.log(i+1,p[0],p[8],'minDE',p[7]));
if(process.argv[2]==='write'){const fs=require('fs');let s=fs.readFileSync('index2.html','utf8');s=s.replace(/const P=\[[\s\S]*?\];\n/,'const P='+JSON.stringify(out)+';\n');fs.writeFileSync('index2.html',s)}
