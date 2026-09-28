(()=>{
  const repo='https://github.com/SondosBsharat/theormgate';
  const $=id=>document.getElementById(id);
  let launchSpecText='';
  let codexText='';
  let terminalText='';

  function intent(){return $('launchQuestion').value.trim()||'State my research idea, prompt, or question here.'}
  function launchSpec(){
    return {
      schema:'theoremgate.launch-summary.v1',
      backend:'codex',
      repository:repo,
      mode:$('launchMode').value,
      intent:intent(),
      model_preference:$('launchModel').value.trim()||null,
      constraints:$('launchConstraints').value.trim()||null,
      safety:{
        theory_first:true,
        require_evidence_route_before_writing:true,
        require_explicit_user_start:true
      }
    };
  }
  function render(){
    const value=launchSpec();
    launchSpecText=JSON.stringify(value,null,2);
    const mode=value.mode==='theory_first'?'theory':'full';
    const constraints=value.constraints?` \\\n  --constraints ${JSON.stringify(value.constraints)}`:'';
    const model=value.model_preference?` \\\n  --model ${JSON.stringify(value.model_preference)}`:'';
    codexText=`Use TheoremAudit for this research request.\n\nResearch question:\n${value.intent}\n\nMode: ${mode}\nConstraints: ${value.constraints||'none'}\n\nStart a governed run only through the TheoremAudit workflow. Do not treat generated proofs or manuscript text as accepted unless the required proof, audit, governance, and paper-routing artifacts support them.`;
    terminalText=`python3 plugins/theoremgate/scripts/theoremgate.py \\\n  --terminal \\\n  --workspace . \\\n  start \\\n  --mode ${mode} \\\n  --question ${JSON.stringify(value.intent)}${constraints}${model}`;
    $('launchSpecJson').textContent=launchSpecText;
    $('terminalPrompt').textContent=terminalText;
  }
  async function copy(text){try{await navigator.clipboard.writeText(text);toast('Copied')}catch{toast('Select and copy the text manually')}}
  function downloadLaunchSpec(){
    const blob=new Blob([launchSpecText+'\n'],{type:'application/json'});
    const link=document.createElement('a');
    link.href=URL.createObjectURL(blob);
    link.download='theoremgate-launch-summary.json';
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(()=>URL.revokeObjectURL(link.href),500);
    toast('Summary downloaded');
  }
  function toast(message){const el=$('toast');el.textContent=message;el.classList.add('show');setTimeout(()=>el.classList.remove('show'),1600)}
  async function checkStudio(){
    const status=$('studioStatus'),link=$('openStudio');
    try{
      const response=await fetch('/api/health',{cache:'no-store'});
      if(!response.ok)throw new Error('not ready');
      status.className='status ready';status.querySelector('span').textContent='Web interface ready';
      link.classList.remove('disabled');link.textContent='Open web interface';
    }catch{
      status.className='status offline';status.querySelector('span').textContent='Workspace not started yet';
      link.classList.add('disabled');link.textContent='Workspace unavailable';
    }
  }
  ['launchQuestion','launchMode','launchModel','launchConstraints'].forEach(id=>$(id).addEventListener('input',render));
  $('copyLaunchSpec').onclick=()=>copy(launchSpecText);
  $('copyCodex').onclick=()=>copy(codexText);
  $('copyTerminal').onclick=()=>copy(terminalText);
  $('downloadLaunchSpec').onclick=downloadLaunchSpec;
  render();checkStudio();
})();
