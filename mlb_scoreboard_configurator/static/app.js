const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];
let bootstrap = null, currentFile = "config", currentData = {}, currentSchema = null, rawMode = false;
let fileLoadSequence = 0;

const descriptions = {
  config: "Main scoreboard behavior, rotation, matrix, weather, standings and plugin options.",
  teams: "Team-specific colors. RGB arrays are rendered with visual color controls.",
  scoreboard: "General scoreboard display colors.",
  coordinates: "Pixel positions and layout values for the selected matrix dimensions."
};

function esc(s){return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]))}
function toast(msg,bad=false){const t=$("#toast");t.textContent=msg;t.className="toast"+(bad?" error":"");setTimeout(()=>t.classList.add("hidden"),3500)}
async function api(url, options={}) {
  const fetchOptions={
    cache:"no-store",
    headers:{"Content-Type":"application/json",...(options.headers||{})},
    ...options
  };
  const r=await fetch(url,fetchOptions);
  const data=await r.json().catch(()=>({}));
  if(!r.ok) throw new Error(data.error||data.message||(data.errors?.[0]?.message)||`HTTP ${r.status}`);
  return data;
}
function setPath(obj,path,value){let ref=obj;for(let i=0;i<path.length-1;i++)ref=ref[path[i]];ref[path.at(-1)]=value}
function isRgb(v){
  if(Array.isArray(v)) return v.length===3&&v.every(n=>Number.isFinite(Number(n))&&Number(n)>=0&&Number(n)<=255);
  if(v&&typeof v==="object"&&!Array.isArray(v)){
    const keys=Object.keys(v);
    return ["r","g","b"].every(k=>Number.isFinite(Number(v[k]))&&Number(v[k])>=0&&Number(v[k])<=255)
      && keys.every(k=>["r","g","b","a"].includes(k));
  }
  return false;
}
function rgbArray(v){
  return Array.isArray(v)
    ? v.map(n=>Math.max(0,Math.min(255,Math.round(Number(n)))))
    : ["r","g","b"].map(k=>Math.max(0,Math.min(255,Math.round(Number(v[k])))));
}
function rgbForOriginal(original,rgb){
  if(Array.isArray(original)) return [...rgb];
  const out={...original,r:rgb[0],g:rgb[1],b:rgb[2]};
  return out;
}
function schemaAt(schema,key){return schema?.properties?.[key]||null}

function getPath(obj,path){
  let ref=obj;
  for(const part of path) ref=ref?.[part];
  return ref;
}
function defaultForSchema(schema, fallbackType="string"){
  if(schema?.default!==undefined) return structuredClone(schema.default);
  if(schema?.const!==undefined) return structuredClone(schema.const);
  if(Array.isArray(schema?.enum) && schema.enum.length) return structuredClone(schema.enum[0]);

  const type=Array.isArray(schema?.type)?schema.type.find(t=>t!=="null"):schema?.type;
  switch(type||fallbackType){
    case "object": return {};
    case "array":
      if(schema?.minItems && schema?.items) return Array.from({length:schema.minItems},()=>defaultForSchema(schema.items));
      return [];
    case "number":
    case "integer": return schema?.minimum ?? 0;
    case "boolean": return false;
    case "string": return "";
    default: return "";
  }
}
function inferNewValue(container,schema,requestedType){
  if(requestedType==="rgb"){
    const sample=(container&&typeof container==="object")
      ? Object.values(container).find(isRgb)
      : null;
    return sample && !Array.isArray(sample)
      ? {r:255,g:255,b:255}
      : ((currentFile==="teams"||currentFile==="scoreboard") ? {r:255,g:255,b:255} : [255,255,255]);
  }
  const map={string:"string",number:"number",boolean:"boolean",object:"object",array:"array"};
  if(requestedType && map[requestedType]) return defaultForSchema(schema,map[requestedType]);
  if(schema) return defaultForSchema(schema);

  if(container && typeof container==="object" && !Array.isArray(container)){
    const vals=Object.values(container);
    if(vals.some(isRgb)){
      const sampleRgb=vals.find(isRgb);
      return Array.isArray(sampleRgb) ? [255,255,255] : {r:255,g:255,b:255};
    }
    const sample=vals.find(v=>v!==null && v!==undefined);
    if(Array.isArray(sample)) return [];
    if(typeof sample==="boolean") return false;
    if(typeof sample==="number") return 0;
    if(sample && typeof sample==="object") return {};
  }
  return "";
}
function syncRaw(){
  $("#rawEditor").value=JSON.stringify(currentData,null,2);
}

function makeControl(value,path,schema){
  const wrap=document.createElement("div");wrap.className="fieldControl";
  const update=v=>{setPath(currentData,path,v); syncRaw()};
  if(isRgb(value)){
    const box=document.createElement("div");box.className="rgbPicker";
    const clamp=(n,min,max)=>Math.max(min,Math.min(max,n));

    const rgbToHsv=([r,g,b])=>{
      r/=255;g/=255;b/=255;
      const max=Math.max(r,g,b),min=Math.min(r,g,b),d=max-min;
      let h=0;
      if(d){
        if(max===r) h=60*(((g-b)/d)%6);
        else if(max===g) h=60*(((b-r)/d)+2);
        else h=60*(((r-g)/d)+4);
      }
      if(h<0) h+=360;
      return [h,max===0?0:d/max,max];
    };
    const hsvToRgb=([h,s,v])=>{
      h=((h%360)+360)%360;s=clamp(s,0,1);v=clamp(v,0,1);
      const c=v*s,x=c*(1-Math.abs((h/60)%2-1)),m=v-c;
      let rp=0,gp=0,bp=0;
      if(h<60){rp=c;gp=x}
      else if(h<120){rp=x;gp=c}
      else if(h<180){gp=c;bp=x}
      else if(h<240){gp=x;bp=c}
      else if(h<300){rp=x;bp=c}
      else{rp=c;bp=x}
      return [Math.round((rp+m)*255),Math.round((gp+m)*255),Math.round((bp+m)*255)];
    };

    const originalRgbValue=value;
    const initialRgb=rgbArray(value);
    let hsv=rgbToHsv(initialRgb);

    const preview=document.createElement("div");preview.className="rgbVisual";
    const swatch=document.createElement("div");swatch.className="rgbSwatchPreview";
    const hex=document.createElement("div");hex.className="rgbHex";
    const rgbText=document.createElement("div");rgbText.className="rgbText muted";
    preview.append(swatch,hex,rgbText);

    const svWrap=document.createElement("div");svWrap.className="svWrap";
    const sv=document.createElement("div");sv.className="svPicker";sv.tabIndex=0;
    sv.setAttribute("role","slider");
    sv.setAttribute("aria-label","Saturation and brightness");
    const svPointer=document.createElement("div");svPointer.className="svPointer";
    sv.append(svPointer);
    svWrap.append(sv);

    const sliderPanel=document.createElement("div");sliderPanel.className="hsvPicker";
    const hueRow=document.createElement("label");hueRow.className="hsvRow";
    const hueTitle=document.createElement("span");hueTitle.textContent="Hue";
    const hue=document.createElement("input");hue.type="range";hue.min=0;hue.max=359;hue.step=1;hue.className="hueSlider";
    const hueVal=document.createElement("span");hueVal.className="sliderValue";
    hueRow.append(hueTitle,hue,hueVal);
    sliderPanel.append(hueRow);

    const channels=document.createElement("div");channels.className="rgbChannels";
    const names=["R","G","B"];
    const nums=initialRgb.map((n,i)=>{
      const field=document.createElement("label");field.className="rgbChannel";
      const caption=document.createElement("span");caption.textContent=names[i];
      const x=document.createElement("input");x.type="number";x.min=0;x.max=255;x.step=1;x.value=n;
      x.setAttribute("aria-label",`${names[i]} channel`);
      field.append(caption,x);channels.append(field);return x;
    });

    const syncAll=(rgb,fromHsv=false)=>{
      if(!fromHsv) hsv=rgbToHsv(rgb);
      const hexValue="#"+rgb.map(n=>n.toString(16).padStart(2,"0")).join("");
      const pureHue=hsvToRgb([hsv[0],1,1]);
      const pureHueCss=`rgb(${pureHue.join(",")})`;
      swatch.style.backgroundColor=hexValue;
      hex.textContent=hexValue.toUpperCase();
      rgbText.textContent=`RGB ${rgb[0]}, ${rgb[1]}, ${rgb[2]}`;
      nums.forEach((x,i)=>x.value=rgb[i]);
      hue.value=Math.round(hsv[0]);
      hueVal.textContent=`${Math.round(hsv[0])}°`;
      sv.style.setProperty("--picker-hue",pureHueCss);
      svPointer.style.left=`${hsv[1]*100}%`;
      svPointer.style.top=`${(1-hsv[2])*100}%`;
      sv.setAttribute("aria-valuetext",`Saturation ${Math.round(hsv[1]*100)}%, brightness ${Math.round(hsv[2]*100)}%`);
    };

    const commitHsv=()=>{
      const rgb=hsvToRgb(hsv);
      syncAll(rgb,true);
      update(rgbForOriginal(originalRgbValue,rgb));
      syncRaw();
    };

    const setSvFromPointer=e=>{
      const rect=sv.getBoundingClientRect();
      if(!rect.width||!rect.height) return;
      const x=clamp((e.clientX-rect.left)/rect.width,0,1);
      const y=clamp((e.clientY-rect.top)/rect.height,0,1);
      hsv=[hsv[0],x,1-y];
      commitHsv();
    };
    sv.addEventListener("pointerdown",e=>{
      sv.setPointerCapture?.(e.pointerId);
      setSvFromPointer(e);
    });
    sv.addEventListener("pointermove",e=>{
      if(e.buttons===1) setSvFromPointer(e);
    });
    sv.addEventListener("keydown",e=>{
      const step=e.shiftKey?.05:.01;
      let changed=true;
      if(e.key==="ArrowLeft") hsv[1]=clamp(hsv[1]-step,0,1);
      else if(e.key==="ArrowRight") hsv[1]=clamp(hsv[1]+step,0,1);
      else if(e.key==="ArrowUp") hsv[2]=clamp(hsv[2]+step,0,1);
      else if(e.key==="ArrowDown") hsv[2]=clamp(hsv[2]-step,0,1);
      else changed=false;
      if(changed){e.preventDefault();commitHsv()}
    });
    hue.addEventListener("input",()=>{
      hsv=[Number(hue.value),hsv[1],hsv[2]];
      commitHsv();
    });
    nums.forEach(x=>x.addEventListener("input",()=>{
      const rgb=nums.map(n=>clamp(Math.round(Number(n.value)||0),0,255));
      syncAll(rgb,false);
      update(rgbForOriginal(originalRgbValue,rgb));
      syncRaw();
    }));

    syncAll(initialRgb,false);
    box.append(preview,svWrap,sliderPanel,channels);
    wrap.append(box);
    return wrap;
  }
  if(typeof value==="boolean"){
    const x=document.createElement("input");x.type="checkbox";x.checked=value;x.onchange=()=>update(x.checked);wrap.append(x);return wrap;
  }
  if(typeof value==="number"){
    const x=document.createElement("input");x.type="number";x.value=value;
    if(schema?.minimum!==undefined)x.min=schema.minimum;if(schema?.maximum!==undefined)x.max=schema.maximum;
    x.oninput=()=>update(Number(x.value));wrap.append(x);return wrap;
  }
  if(typeof value==="string" && Array.isArray(schema?.enum)){
    const x=document.createElement("select");schema.enum.forEach(v=>{const o=document.createElement("option");o.value=v;o.textContent=v;o.selected=v===value;x.append(o)});x.onchange=()=>update(x.value);wrap.append(x);return wrap;
  }
  if(typeof value==="string"){
    const x=document.createElement("input");x.type=(String(path.at(-1)).toLowerCase().includes("apikey")?"password":"text");x.value=value;x.oninput=()=>update(x.value);wrap.append(x);return wrap;
  }
  // Arrays and unusual values remain editable without losing future schema compatibility.
  const x=document.createElement("textarea");x.value=JSON.stringify(value,null,2);
  x.onchange=()=>{try{update(JSON.parse(x.value));x.style.borderColor=""}catch(e){x.style.borderColor="#b94b59";toast(`Invalid JSON in ${path.join(".")}`,true)}};
  wrap.append(x);return wrap;
}

function makeAddItemPanel(container,schema,path,onDone){
  const panel=document.createElement("div");panel.className="addItemPanel";
  const isArray=Array.isArray(container);

  const keyInput=document.createElement("input");
  keyInput.type=isArray?"number":"text";
  keyInput.placeholder=isArray?"Index (optional)":"New key";
  if(isArray){keyInput.min=0;keyInput.max=container.length;keyInput.value=container.length}

  const missingProps=(!isArray && schema?.properties)
    ? Object.keys(schema.properties).filter(k=>!(k in container))
    : [];
  if(missingProps.length){
    const list=document.createElement("datalist");
    list.id="missing-"+Math.random().toString(36).slice(2);
    missingProps.forEach(k=>{
      const o=document.createElement("option");o.value=k;o.label=schema.properties[k]?.title||k;list.append(o);
    });
    keyInput.setAttribute("list",list.id);
    panel.append(list);
  }

  const type=document.createElement("select");
  [["string","Text"],["number","Number"],["boolean","Boolean"],["object","Section / object"],["array","List / array"],["rgb","RGB color"]]
    .forEach(([v,label])=>{const o=document.createElement("option");o.value=v;o.textContent=label;type.append(o)});

  const add=document.createElement("button");add.type="button";add.className="primary";add.textContent="Add";
  const cancel=document.createElement("button");cancel.type="button";cancel.className="secondary";cancel.textContent="Cancel";

  add.addEventListener("click",()=>{
    if(isArray){
      const index=clampIndex(Number(keyInput.value),container.length);
      const itemSchema=schema?.items||null;
      container.splice(index,0,inferNewValue(container,itemSchema,type.value));
    }else{
      const key=keyInput.value.trim();
      if(!key) return toast("Enter a key name.",true);
      if(Object.prototype.hasOwnProperty.call(container,key)) return toast(`"${key}" already exists.`,true);
      const itemSchema=schemaAt(schema,key) || schema?.additionalProperties || null;
      container[key]=inferNewValue(container,itemSchema,type.value);
    }
    syncRaw();
    renderForm();
    onDone?.();
  });
  cancel.addEventListener("click",()=>panel.remove());

  panel.append(keyInput,type,add,cancel);
  return panel;
}
function clampIndex(n,length){
  if(!Number.isFinite(n)) return length;
  return Math.max(0,Math.min(length,Math.round(n)));
}
function addSectionFooter(container,schema,parent,path){
  const footer=document.createElement("div");footer.className="sectionFooter";
  const btn=document.createElement("button");btn.type="button";btn.className="secondary addItemBtn";
  btn.textContent=Array.isArray(container)?"＋ Add list item":"＋ Add item";
  btn.addEventListener("click",()=>{
    const existing=footer.querySelector(".addItemPanel");
    if(existing){existing.remove();return}
    footer.append(makeAddItemPanel(container,schema,path));
    const first=footer.querySelector(".addItemPanel input");
    first?.focus();
  });
  footer.append(btn);
  parent.append(footer);
}
function renderArray(arr,schema,parent,path){
  if(isRgb(arr)){parent.append(makeControl(arr,path,schema));return}
  arr.forEach((value,index)=>{
    const itemSchema=schema?.items||null;
    if(value && typeof value==="object" && !isRgb(value)){
      const g=document.createElement("div");g.className="group";
      const h=document.createElement("div");h.className="groupHeaderRow";
      const title=document.createElement("div");title.className="groupHeader";title.textContent=`Item ${index+1}`;
      const remove=document.createElement("button");remove.type="button";remove.className="danger mini";remove.textContent="Remove";
      remove.onclick=()=>{arr.splice(index,1);syncRaw();renderForm()};
      h.append(title,remove);g.append(h);
      if(Array.isArray(value)) renderArray(value,itemSchema,g,[...path,index]);
      else renderObject(value,itemSchema,g,[...path,index]);
      parent.append(g);
    }else{
      const row=document.createElement("div");row.className="field";
      const info=document.createElement("div");
      const name=document.createElement("div");name.className="fieldName";name.textContent=`Item ${index+1}`;info.append(name);
      const controls=document.createElement("div");controls.className="inlineControls";
      controls.append(makeControl(value,[...path,index],itemSchema));
      const remove=document.createElement("button");remove.type="button";remove.className="danger mini";remove.textContent="Remove";
      remove.onclick=()=>{arr.splice(index,1);syncRaw();renderForm()};
      controls.append(remove);row.append(info,controls);parent.append(row);
    }
  });
  addSectionFooter(arr,schema,parent,path);
}
function renderObject(obj,schema,parent,path=[]){
  Object.entries(obj).forEach(([key,value])=>{
    const s=schemaAt(schema,key);
    if(value && typeof value==="object" && !isRgb(value)){
      const g=document.createElement("div");g.className="group";
      const h=document.createElement("div");h.className="groupHeaderRow";
      const title=document.createElement("div");title.className="groupHeader";title.textContent=s?.title||key;
      h.append(title);
      if(key!=="$schema" && key!=="format"){
        const remove=document.createElement("button");remove.type="button";remove.className="danger mini";remove.textContent="Remove";
        remove.onclick=()=>{
          if(!confirm(`Remove "${key}" from this configuration?`)) return;
          delete obj[key];syncRaw();renderForm();
        };
        h.append(remove);
      }
      g.append(h);
      if(s?.description){const d=document.createElement("div");d.className="desc";d.textContent=s.description;g.append(d)}
      if(Array.isArray(value)) renderArray(value,s,g,[...path,key]);
      else renderObject(value,s,g,[...path,key]);
      parent.append(g);return;
    }

    const row=document.createElement("div");row.className="field";
    const info=document.createElement("div");
    const name=document.createElement("div");name.className="fieldName";name.textContent=s?.title||key;info.append(name);
    if(s?.description){const d=document.createElement("div");d.className="desc";d.textContent=s.description;info.append(d)}

    const controls=document.createElement("div");controls.className="inlineControls";
    controls.append(makeControl(value,[...path,key],s));
    if(key!=="$schema" && key!=="format"){
      const remove=document.createElement("button");remove.type="button";remove.className="danger mini";remove.textContent="Remove";
      remove.onclick=()=>{
        if(!confirm(`Remove "${key}" from this configuration?`)) return;
        delete obj[key];syncRaw();renderForm();
      };
      controls.append(remove);
    }
    row.append(info,controls);parent.append(row);
  });
  addSectionFooter(obj,schema,parent,path);
}
function renderForm(){
  const host=$("#formEditor");host.innerHTML="";
  try{
    if(Array.isArray(currentData)){renderArray(currentData,currentSchema,host,[]);return}
    renderObject(currentData,currentSchema,host,[]);
  }catch(e){
    console.error("Structured editor render failed:",e);
    host.innerHTML="";
    const box=document.createElement("div");box.className="editorError";
    const title=document.createElement("strong");title.textContent="Structured editor error";
    const msg=document.createElement("div");msg.textContent=e?.message||String(e);
    const help=document.createElement("div");help.className="muted";help.textContent="The complete JSON is still available in Raw JSON mode.";
    box.append(title,msg,help);host.append(box);
    toast(`Editor error: ${e?.message||e}`,true);
  }
}
function showValidation(errors){
  const b=$("#validationBox");b.classList.remove("hidden","ok");
  if(!errors?.length){b.classList.add("ok");b.innerHTML="<strong>Valid.</strong> No schema errors found.";return}
  b.innerHTML="<strong>Validation errors:</strong><ul>"+errors.map(e=>`<li><code>${esc(e.path)}</code>: ${esc(e.message)}</li>`).join("")+"</ul>";
}
async function loadFile(id){
  const seq=++fileLoadSequence;
  const meta=bootstrap.files.find(f=>f.id===id);
  if(!meta) throw new Error(`Unknown configuration file: ${id}`);

  const fs=$("#fileSelect");
  fs.value=id;
  fs.disabled=true;

  $("#fileTitle").textContent=meta.label||id;
  $("#fileSubtitle").textContent="Loading…";
  $("#fileHelp").textContent=descriptions[meta.kind]||"";
  $("#formEditor").innerHTML='<p class="muted">Loading configuration…</p>';
  $("#validationBox").classList.add("hidden");

  try{
    const url="/api/file/"+id.split("/").map(encodeURIComponent).join("/")+"?ts="+Date.now();
    const x=await api(url);

    // Ignore an older request if the user changed files again before it finished.
    if(seq!==fileLoadSequence) return;

    currentFile=id;
    currentData=x.data;
    currentSchema=x.schema||null;
    $("#fileSubtitle").textContent=descriptions[meta.kind]||"JSON configuration.";
    $("#rawEditor").value=JSON.stringify(currentData,null,2);
    renderForm();
    showValidation(x.validation||[]);
  } finally {
    if(seq===fileLoadSequence) fs.disabled=false;
  }
}
async function save(){
  try{
    if(rawMode) currentData=JSON.parse($("#rawEditor").value);
    const x=await api("/api/file/"+encodeURI(currentFile),{method:"PUT",body:JSON.stringify(currentData)});
    showValidation([]);toast("Saved safely. A backup of the previous file was created.");renderForm();
  }catch(e){toast(e.message,true)}
}
async function validateCurrent(){
  try{if(rawMode)currentData=JSON.parse($("#rawEditor").value);const x=await api("/api/file/"+encodeURI(currentFile)+"/validate",{method:"POST",body:JSON.stringify(currentData)});showValidation(x.errors)}catch(e){toast(e.message,true)}
}
function toggleMode(){
  if(rawMode){
    try{currentData=JSON.parse($("#rawEditor").value)}catch(e){return toast("Fix JSON syntax before returning to form mode.",true)}
    renderForm();
  } else $("#rawEditor").value=JSON.stringify(currentData,null,2);
  rawMode=!rawMode;$("#rawEditor").classList.toggle("hidden",!rawMode);$("#formEditor").classList.toggle("hidden",rawMode);$("#modeBtn").textContent=rawMode?"Form editor":"Raw JSON";
}
async function showBackups(){
  try{
    const x=await api("/api/file/"+encodeURI(currentFile)+"/backups");$("#modalTitle").textContent="Backups — "+currentFile;
    $("#modalBody").innerHTML=x.backups.length?x.backups.map(b=>`<div class="backup"><div><b>${esc(b.mtime)}</b><div class="muted small">${esc(b.id)} · ${b.size} bytes</div></div><button data-restore="${esc(b.id)}">Restore</button></div>`).join(""):"<p>No backups yet.</p>";
    $$("[data-restore]").forEach(btn=>btn.onclick=async()=>{if(!confirm("Restore this backup? The current file will also be backed up."))return;await api("/api/file/"+encodeURI(currentFile)+"/restore",{method:"POST",body:JSON.stringify({backup_id:btn.dataset.restore})});$("#modal").classList.add("hidden");await loadFile(currentFile);toast("Backup restored.")});
    $("#modal").classList.remove("hidden");
  }catch(e){toast(e.message,true)}
}
function renderWifi(st){
  $("#wifiStatus").innerHTML=st.connected?`<p><b>Connected</b> on ${esc(st.connection.device)} via <b>${esc(st.connection.connection)}</b></p>`:`<p><b>Not connected to a Wi-Fi client network.</b></p>`;
  $("#wifiStatus").innerHTML+=`<p class="muted small">Fallback hotspot: ${st.hotspot_active?"active":"inactive"} · interface: ${esc(st.interface)}</p>`;
}
async function refreshWifi(){renderWifi(await api("/api/wifi/status"))}
async function scan(){
  $("#networks").innerHTML="<p class=muted>Scanning…</p>";
  try{const x=await api("/api/wifi/networks");$("#networks").innerHTML=x.networks.map(n=>`<div class=network><div><b>${esc(n.ssid)}</b><div class=networkMeta>${esc(n.security||"Open")} · signal ${esc(n.signal)}%</div></div><button data-ssid="${esc(n.ssid)}">Connect</button></div>`).join("")||"<p>No networks found.</p>";
  $$("[data-ssid]").forEach(b=>b.onclick=async()=>{const pw=prompt(`Password for ${b.dataset.ssid} (blank if open):`);if(pw===null)return;try{const x=await api("/api/wifi/connect",{method:"POST",body:JSON.stringify({ssid:b.dataset.ssid,password:pw})});toast("Wi-Fi connected.");renderWifi(x.status)}catch(e){toast(e.message,true)}})
  }catch(e){toast(e.message,true)}
}
async function saveHotspot(){try{const x=await api("/api/settings",{method:"PUT",body:JSON.stringify({hotspot_enabled:$("#hotspotEnabled").checked,hotspot_ssid:$("#hotspotSsid").value,hotspot_password:$("#hotspotPassword").value})});toast("Hotspot settings saved.")}catch(e){toast(e.message,true)}}
function renderService(st){
  $("#serviceBadge").textContent=`Scoreboard: ${st.active_state}/${st.sub_state}`;$("#serviceBadge").className="badge "+(st.active_state==="active"?"ok":"bad");
  $("#serviceDetails").innerHTML=`<p><b>Active state:</b> ${esc(st.active_state)}</p><p><b>Sub-state:</b> ${esc(st.sub_state)}</p><p><b>Enabled:</b> ${esc(st.unit_file_state)}</p>`;
}
async function refreshService(){renderService(await api("/api/service/status"))}
function switchView(name){
  const editorPage=$("#editorPage");
  const systemPage=$("#systemSettingsPage");

  $$(".view").forEach(v=>v.classList.add("hidden"));
  systemPage?.classList.add("hidden");

  if(name==="system"){
    editorPage?.classList.add("hidden");
    systemPage?.classList.remove("hidden");
    loadSystemSettings().catch(e=>toast(e.message||String(e),true));
  }else{
    editorPage?.classList.remove("hidden");
    const target=$("#"+name+"View");
    if(target) target.classList.remove("hidden");
    if(name==="wifi") refreshWifi();
    if(name==="service") refreshService();
  }

  $$(".nav").forEach(b=>b.classList.toggle("active",b.dataset.view===name));
}
async function init(){
  bootstrap=await api("/api/bootstrap?ts="+Date.now());
  const fs=$("#fileSelect");
  fs.innerHTML=bootstrap.files.map(f=>`<option value="${esc(f.id)}">${esc(f.label)}</option>`).join("");
  fs.addEventListener("change",async()=>{
    try{
      switchView("editor");
      await loadFile(fs.value);
    }catch(e){
      toast(e.message,true);
      fs.disabled=false;
      fs.value=currentFile;
      await loadFile(currentFile).catch(()=>{});
    }
  });
  renderWifi(bootstrap.wifi);
  renderService(bootstrap.service);
  const s=bootstrap.settings;
  $("#hotspotEnabled").checked=!!s.hotspot_enabled;
  $("#hotspotSsid").value=s.hotspot_ssid;
  $("#hotspotPassword").value=s.hotspot_password;
  await loadFile("config");
}
$$(".nav").forEach(b=>b.onclick=()=>switchView(b.dataset.view));
$("#saveBtn").onclick=save;$("#validateBtn").onclick=validateCurrent;$("#modeBtn").onclick=toggleMode;$("#backupsBtn").onclick=showBackups;
$("#modalClose").onclick=()=>$("#modal").classList.add("hidden");$("#scanBtn").onclick=scan;$("#saveHotspotBtn").onclick=saveHotspot;
$("#disconnectBtn").onclick=async()=>{if(!confirm("Disconnect Wi-Fi? The fallback hotspot may activate."))return;try{const x=await api("/api/wifi/disconnect",{method:"POST"});renderWifi(x.status);toast(x.message)}catch(e){toast(e.message,true)}};
$("#startHotspotBtn").onclick=async()=>{try{const x=await api("/api/wifi/hotspot/start",{method:"POST"});renderWifi(x.status);toast(x.message)}catch(e){toast(e.message,true)}};
$("#stopHotspotBtn").onclick=async()=>{try{const x=await api("/api/wifi/hotspot/stop",{method:"POST"});renderWifi(x.status);toast(x.message)}catch(e){toast(e.message,true)}};
$$("[data-service]").forEach(b=>b.onclick=async()=>{const a=b.dataset.service;if((a==="stop"||a==="restart")&&!confirm(`${a[0].toUpperCase()+a.slice(1)} mlb-led-scoreboard.service?`))return;try{const x=await api("/api/service/"+a,{method:"POST"});renderService(x.status);toast(`Scoreboard service ${a} command completed.`)}catch(e){toast(e.message,true)}})
init().catch(e=>toast(e.message,true));


async function loadSystemSettings(){
  const r=await api("/api/system/settings");
  $("#piHostname").value=r.hostname||"";
  $("#configAuthUsername").value=r.username||"";
  $("#configAuthPassword").value="";
  $("#configAuthPasswordConfirm").value="";
  $("#authRestartNotice").classList.add("hidden");
}

$("#saveHostname")?.addEventListener("click",async()=>{
  const hostname=$("#piHostname").value.trim();
  try{
    const r=await api("/api/system/hostname",{
      method:"PUT",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({hostname})
    });
    $("#piHostname").value=r.hostname||hostname;
    toast("Hostname updated.");
  }catch(e){toast(e.message||String(e),true)}
});

$("#saveConfiguratorAuth")?.addEventListener("click",async()=>{
  const username=$("#configAuthUsername").value.trim();
  const password=$("#configAuthPassword").value;
  const confirm_password=$("#configAuthPasswordConfirm").value;
  if(!username) return toast("Username cannot be empty.",true);
  if(!password) return toast("Enter a new password.",true);
  if(password!==confirm_password) return toast("Passwords do not match.",true);
  try{
    await api("/api/system/auth",{
      method:"PUT",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({username,password,confirm_password})
    });
    $("#authRestartNotice").classList.remove("hidden");
    toast("Credentials saved. Restart required.");
  }catch(e){toast(e.message||String(e),true)}
});

$("#restartConfiguratorAfterAuth")?.addEventListener("click",async()=>{
  const btn=$("#restartConfiguratorAfterAuth");
  btn.disabled=true;
  try{
    fetch("/api/system/restart-configurator",{method:"POST",cache:"no-store",credentials:"same-origin"});
    toast("Configurator is restarting. Reconnect using the new login.");
    setTimeout(()=>window.location.reload(),1800);
  }catch(e){
    btn.disabled=false;
    toast(e.message||String(e),true);
  }
});
