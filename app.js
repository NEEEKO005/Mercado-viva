let requests = [];
const $ = s => document.querySelector(s);
function toast(message){ const t=$('#toast'); t.textContent=message; t.classList.add('show'); setTimeout(()=>t.classList.remove('show'),3000); }
async function loadRequests(){
  try { const response = await fetch('/api/returns'); requests = await response.json(); render(); }
  catch { toast('No fue posible conectar con el servidor. Ejecuta python app.py'); }
}
function render(){
  const filter=$('#search').value.toLowerCase();
  const rows=requests.filter(r=>(r.order_number+r.product+r.email+r.code).toLowerCase().includes(filter));
  $('#total-count').textContent=requests.length;
  $('#pending-count').textContent=requests.filter(r=>r.status==='Pendiente').length;
  $('#processed-count').textContent=requests.filter(r=>r.status==='Procesada').length;
  $('#requests-body').innerHTML=rows.map(r=>`<tr><td><b class="request-id">${r.code}</b>${r.order_number}</td><td><b>${r.product}</b><small>${r.category}</small></td><td>${r.email}</td><td>${r.reason}</td><td><span class="status ${r.status}">${r.status}</span></td><td><select class="action-select" data-id="${r.id}"><option ${r.status==='Pendiente'?'selected':''}>Pendiente</option><option ${r.status==='Aprobada'?'selected':''}>Aprobada</option><option ${r.status==='Rechazada'?'selected':''}>Rechazada</option><option ${r.status==='Procesada'?'selected':''}>Procesada</option></select></td></tr>`).join('');
  $('#empty-state').hidden=rows.length>0;
}
document.querySelectorAll('[data-view]').forEach(button=>button.addEventListener('click',()=>{
  document.querySelectorAll('[data-view],.view').forEach(el=>el.classList.remove('active'));
  button.classList.add('active'); $('#'+button.dataset.view).classList.add('active');
  if(button.dataset.view==='employee') loadRequests();
}));
$('#category').addEventListener('change',e=>{
  const prohibited=e.target.value==='Alimento perecedero';
  $('#policy-message').classList.toggle('invalid',prohibited);
  $('#policy-message').textContent=prohibited?'Este producto no puede devolverse: los alimentos perecederos están excluidos por política de calidad.':'Solo aceptamos devoluciones de artículos tecnológicos. Los alimentos perecederos no son elegibles.';
});
$('#return-form').addEventListener('submit',async e=>{
  e.preventDefault(); const category=$('#category').value;
  if(category!=='Tecnología'){ toast(category==='Alimento perecedero'?'No podemos registrar alimentos perecederos.':'Solo se permiten devoluciones de tecnología.'); return; }
  try { const response=await fetch('/api/returns',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({order_number:$('#order').value.trim(),email:$('#email').value.trim(),product:$('#product').value.trim(),category,reason:$('#reason').value})}); const result=await response.json(); if(!response.ok) throw new Error(result.error); e.target.reset(); toast(`Solicitud ${result.code} registrada correctamente.`); await loadRequests(); } catch(error) { toast(error.message || 'No fue posible registrar la solicitud.'); }
});
$('#requests-body').addEventListener('change',async e=>{ if(!e.target.matches('.action-select'))return; try { const response=await fetch(`/api/returns/${e.target.dataset.id}`,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({status:e.target.value})}); if(!response.ok) throw new Error(); await loadRequests(); toast('Estado de la solicitud actualizado.'); } catch { toast('No fue posible actualizar el estado.'); } });
$('#search').addEventListener('input',render);
$('#seed-data').addEventListener('click',()=>{ loadRequests(); toast('Solicitudes actualizadas desde la base de datos.'); });
loadRequests();
