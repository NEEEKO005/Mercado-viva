let requests = [], customerToken = '', employeeToken = '', loginRole = 'customer', purchases = [];
const $ = s => document.querySelector(s);
function toast(message){const t=$('#toast');t.textContent=message;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),3000)}
async function api(path,options={}){const response=await fetch(path,options);const data=await response.json();if(!response.ok)throw new Error(data.error||'Ocurrió un error.');return data}
async function loadRequests(){if(!employeeToken)return;try{requests=await api('/api/returns',{headers:{Authorization:`Bearer ${employeeToken}`}});render()}catch(error){toast(error.message)}}
function render(){const filter=$('#search').value.toLowerCase(),rows=requests.filter(r=>(r.order_number+r.product+r.email+r.code).toLowerCase().includes(filter));$('#total-count').textContent=requests.length;$('#pending-count').textContent=requests.filter(r=>r.status==='Pendiente').length;$('#processed-count').textContent=requests.filter(r=>r.status==='Procesada').length;$('#requests-body').innerHTML=rows.map(r=>{const photos=JSON.parse(r.photos||'[]').map(path=>`<a href="/${path}" target="_blank">Ver foto</a>`).join('<br>')||'—';const detail=r.reason==='Otro'&&r.other_reason?`Otro: ${r.other_reason}`:r.reason;return `<tr><td><b class="request-id">${r.code}</b>${r.order_number}<small>${new Date(r.created_at).toLocaleString()}</small></td><td><b>${r.product}</b><small>${r.category}</small></td><td>${r.email}</td><td>${detail}</td><td>${photos}
<td>
  <span class="status ${r.status}">${r.status}</span>
  ${r.resolution ? `<small>${r.resolution}</small>` : ''}
</td>
<td>
  <select class="action-select" data-id="${r.id}">
    <option ${r.status==='Pendiente'?'selected':''}>Pendiente</option>
    <option ${r.status==='Aprobada'?'selected':''}>Aprobada</option>
    <option ${r.status==='Rechazada'?'selected':''}>Rechazada</option>
    <option ${r.status==='Procesada'?'selected':''}>Procesada</option>
  </select>
  <select class="resolution-select" data-id="${r.id}">
    <option value="">Elegir devolución/cambio</option>
    <option value="Devolución en efectivo" ${r.resolution==='Devolución en efectivo'?'selected':''}>💵 Devolución en efectivo</option>
    <option value="Cambio por la misma unidad" ${r.resolution==='Cambio por la misma unidad'?'selected':''}>🔄 Cambio por la misma unidad</option>
  </select>
</td></tr>`}).join('');$('#empty-state').hidden=rows.length>0}
async function loadPurchases(){purchases=await api('/api/purchases',{headers:{Authorization:`Bearer ${customerToken}`}});$('#recent-products').innerHTML=purchases.map(p=>`<option value="${p.product}">${p.product} — ${p.order_number}</option>`).join('');$('#purchases-help').textContent='Compras recientes disponibles: selecciona un producto para completar su orden automáticamente.'}
document.querySelectorAll('[data-view]').forEach(button=>button.addEventListener('click',()=>{if(button.dataset.view==='employee'&&!employeeToken){openLogin('employee');return}document.querySelectorAll('[data-view],.view').forEach(el=>el.classList.remove('active'));button.classList.add('active');$('#'+button.dataset.view).classList.add('active');if(button.dataset.view==='employee')loadRequests()}));
$('#customer-login').addEventListener('click',()=>openLogin('customer'));$('#close-login').addEventListener('click',()=>$('#login-dialog').close());
$('#login-form').addEventListener('submit',async event=>{event.preventDefault();try{const result=await api('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:$('#login-user').value,password:$('#login-password').value,role:loginRole})});$('#login-dialog').close();if(loginRole==='customer'){customerToken=result.token;$('#email').value=result.email;$('#email').readOnly=true;$('#customer-login').textContent='Sesión: '+result.name;await loadPurchases();toast('Compras recientes cargadas.')}else{employeeToken=result.token;document.querySelector('[data-view="employee"]').click();toast('Sesión de empleado iniciada.')}}catch(error){toast(error.message)}});
$('#product').addEventListener('input',event=>{const purchase=purchases.find(item=>item.product===event.target.value);if(purchase){$('#order').value=purchase.order_number;$('#category').value='technology';$('#category').dispatchEvent(new Event('change'))}});$('#reason').addEventListener('change',event=>{$('#other-reason-wrap').hidden=event.target.value!=='Otro';$('#other-reason').required=event.target.value==='Otro'});
$('#category').addEventListener('change',e=>{const prohibited=e.target.value==='perishable-food';$('#policy-message').classList.toggle('invalid',prohibited);$('#policy-message').textContent=prohibited?'Este producto no puede devolverse: los alimentos perecederos están excluidos por política de calidad.':'Solo aceptamos devoluciones de artículos tecnológicos. Los alimentos perecederos no son elegibles.'});
$('#return-form').addEventListener('submit',async e=>{e.preventDefault();const files=[...$('#photos').files];if(files.length>3){toast('Puedes cargar máximo 3 fotos.');return}const form=new FormData();['order','email','product','category','reason'].forEach(id=>form.append(id==='order'?'order_number':id,$('#'+id).value));form.append('other_reason',$('#other-reason').value);files.forEach(file=>form.append('photos',file));try{const result=await api('/api/returns',{method:'POST',headers:customerToken?{Authorization:`Bearer ${customerToken}`}:{},body:form});e.target.reset();toast(`Solicitud ${result.code} registrada correctamente.`)}catch(error){toast(error.message)}});
$('#requests-body').addEventListener('change',async e=>{
  if(!e.target.matches('.action-select')&&!e.target.matches('.resolution-select'))return;
  try{
    const row=e.target.closest('tr');
    const statusSelect=row.querySelector('.action-select');
    const resolutionSelect=row.querySelector('.resolution-select');
    await api(`/api/returns/${e.target.dataset.id}`,{
      method:'PATCH',
      headers:{'Content-Type':'application/json',Authorization:`Bearer ${employeeToken}`},
      body:JSON.stringify({
        status:statusSelect.value,
        resolution:resolutionSelect.value
      })
    });
    await loadRequests();
    toast('Solicitud actualizada.');
  }catch(error){toast(error.message)}
});
