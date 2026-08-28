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
function isRgb(v){return Array.isArray(v)&&v.length===3&&v.every(n=>Number.isInteger(n)&&n>=0&&n<=255)}
function schemaAt(schema,key){return schema?.properties?.[key]||null}

function makeControl(value,path,schema){
  const wrap=document.createElement("div");wrap.className="fieldControl";
  const update=v=>{setPath(currentData,path,v); if(rawMode) $("#rawEditor").value=JSON.stringify(currentData,null,2)};
  if(isRgb(value)){
    const box=document.createElement("div");box.className="rgbPicker";

    const visual=document.createElement("div");visual.className="rgbVisual";
    const picker=document.createElement("input");picker.type="color";picker.className="rgbSwatch";
    picker.setAttribute("aria-label","Choose color");
    picker.title="Click to choose a color";
    picker.value="#"+value.map(n=>n.toString(16).padStart(2,"0")).join("");

    const hex=document.createElement("div");hex.className="rgbHex";
    const rgbText=document.createElement("div");rgbText.className="rgbText muted";
    visual.append(picker,hex,rgbText);

    const channels=document.createElement("div");channels.className="rgbChannels";
    const names=["R","G","B"];
    const nums=value.map((n,i)=>{
      const field=document.createElement("label");field.className="rgbChannel";
      const caption=document.createElement("span");caption.textContent=names[i];
      const x=document.createElement("input");x.type="number";x.min=0;x.max=255;x.step=1;x.value=n;
      x.setAttribute("aria-label",`${names[i]} channel`);
      field.append(caption,x);channels.append(field);return x
    });

    const normalized=()=>nums.map(x=>Math.max(0,Math.min(255,Math.round(Number(x.value)||0))));
    const syncDisplay=v=>{
      const h="#"+v.map(n=>n.toString(16).padStart(2,"0")).join("");
      picker.value=h;
      hex.textContent=h.toUpperCase();
      rgbText.textContent=`RGB ${v[0]}, ${v[1]}, ${v[2]}`;
    };
    const applyNums=()=>{
      const v=normalized();
      nums.forEach((x,i)=>x.value=v[i]);
      syncDisplay(v);
      update(v);
    };
    picker.addEventListener("input",()=>{
      const h=picker.value.slice(1);
      const v=[0,1,2].map(i=>parseInt(h.slice(i*2,i*2+2),16));
      nums.forEach((x,i)=>x.value=v[i]);
      syncDisplay(v);
      update(v);
    });
    nums.forEach(x=>x.addEventListener("input",applyNums));
    syncDisplay(value);

    box.append(visual,channels);
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
    const x=document.createElement("input");x.type=(path.at(-1).toLowerCase().includes("apikey")?"password":"text");x.value=value;x.oninput=()=>update(x.value);wrap.append(x);return wrap;
  }
  // Arrays and unusual values remain editable without losing future schema compatibility.
  const x=document.createElement("textarea");x.value=JSON.stringify(value,null,2);
  x.onchange=()=>{try{update(JSON.parse(x.value));x.style.borderColor=""}catch(e){x.style.borderColor="#b94b59";toast(`Invalid JSON in ${path.join(".")}`,true)}};
  wrap.append(x);return wrap;
}

function renderObject(obj,schema,parent,path=[]){
  Object.entries(obj).forEach(([key,value])=>{
    if(key==="$schema") return;
    const s=schemaAt(schema,key);
    if(value && typeof value==="object" && !Array.isArray(value) && !isRgb(value)){
      const g=document.createElement("div");g.className="group";
      const h=document.createElement("div");h.className="groupHeader";h.textContent=s?.title||key;g.append(h);
      if(s?.description){const d=document.createElement("div");d.className="desc";d.textContent=s.description;g.append(d)}
      renderObject(value,s,g,[...path,key]);parent.append(g);return;
    }
    const row=document.createElement("div");row.className="field";
    const info=document.createElement("div");
    const name=document.createElement("div");name.className="fieldName";name.textContent=s?.title||key;info.append(name);
    if(s?.description){const d=document.createElement("div");d.className="desc";d.textContent=s.description;info.append(d)}
    row.append(info,makeControl(value,[...path,key],s));parent.append(row);
  });
}
function renderForm(){
  const host=$("#formEditor");host.innerHTML="";
  if(Array.isArray(currentData)){host.append(makeControl(currentData,[],currentSchema));return}
  renderObject(currentData,currentSchema,host,[]);
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
function switchView(name){$$(".view").forEach(v=>v.classList.add("hidden"));$("#"+name+"View").classList.remove("hidden");$$(".nav").forEach(b=>b.classList.toggle("active",b.dataset.view===name));if(name==="wifi")refreshWifi();if(name==="service")refreshService()}
async function init(){
  bootstrap=await api("/api/bootstrap?ts="+Date.now());
  const fs=$("#fileSelect");
  fs.innerHTML=bootstrap.files.map(f=>`<option value="${esc(f.id)}">${esc(f.label)}</option>`).join("");
  fs.addEventListener("change",async()=>{
    try{
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
