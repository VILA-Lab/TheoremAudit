function describeExperimentActivity(run){
  const activity=run?.empirical?.activity;
  if(run?.current_paper_stage!=='empirical_validation'||!activity?.state)return '';
  const names={checking_resources:'Checking resources',awaiting_resources:'Awaiting resources',downloading:'Downloading resources',running:'Running experiment',awaiting_approval:'Awaiting approval',blocked:'Experiment blocked',ready:'Experiment resources ready',interrupted:'Experiment interrupted',unavailable:'Resource status unavailable'};
  return `${names[activity.state]||'Experiment status'}: ${activity.detail||''}`;
}
function describeRunExecution(run,runner){
  const idle={state:'idle',title:'No run selected',detail:'',canResume:false,showResume:false};
  if(!run)return idle;
  const theoryDone=run.theory_status==='completed'||run.current_theory_stage==='complete';
  const hasPaper=run.paper_status&&run.paper_status!=='not_started';
  const complete=theoryDone&&(run.paper_status==='completed'||(!hasPaper&&run.execution_contract?.requested_mode==='theory'));
  const paper=theoryDone&&hasPaper;
  const stageId=paper?run.current_paper_stage:theoryDone?'paper_initialization':run.current_theory_stage;
  const stages=paper?run.paper_stages:run.theory_stages;
  const stage=stages?.find(item=>item.id===stageId)?.label||String(stageId||'research setup').replaceAll('_',' ');
  if(!runner||runner.state_error)return {...idle,state:'unknown',title:'Execution status unavailable',detail:`Saved stage: ${stage}`,showResume:!complete};
  const active=(runner.jobs||[]).filter(job=>['starting','running','cancelling'].includes(job.status));
  const own=active.find(job=>job.run_id===run.run_id);
  if(own)return {...idle,state:'running',title:own.status==='cancelling'?'Stopping':'Running',detail:stage};
  if(run.current_paper_stage==='empirical_validation'&&['checking_resources','downloading','running'].includes(run.empirical?.activity?.state))return {...idle,state:'running',title:'Experiment operation active',detail:describeExperimentActivity(run)};
  if(complete)return {...idle,state:'completed',title:'Workflow completed',detail:'Review manuscript readiness separately.'};
  if((paper?run.paper_status:run.theory_status)==='blocked'||run.theory_status==='superseded_by_linked_revision'){
    return {...idle,state:'blocked',title:'Revision required',detail:`Saved stage: ${stage}. See Issues.`};
  }
  const busy=active.length>0||Boolean(runner.active_job_id&&!(runner.jobs||[]).some(job=>job.job_id===runner.active_job_id));
  return {state:'paused',title:'Awaiting resume',detail:`Saved stage: ${stage}. ${busy?'Another run is active.':runner.available?'No active Codex session.':'Codex CLI unavailable.'}`,canResume:Boolean(runner.available)&&!busy,showResume:true};
}
if(typeof module!=='undefined'&&module.exports)module.exports={describeRunExecution,describeExperimentActivity};
if(typeof document!=='undefined')(()=>{
  const $=id=>document.getElementById(id);
  const KIND_META={
    assumption:{label:'Assumptions',color:'#446f8a',column:'Evidence'},
    prior_work:{label:'Prior work',color:'#78658e',column:'Evidence'},
    target:{label:'Targets',color:'#718178',column:'Reasoning'},
    proof:{label:'Proofs',color:'#287256',column:'Reasoning'},
    theorem:{label:'Results',color:'#b06c25',column:'Claims'},
    finding:{label:'Findings',color:'#b64b45',column:'Pressure'},
    action:{label:'Actions',color:'#c08b2e',column:'Pressure'},
    section:{label:'Paper sections',color:'#52657c',column:'Paper'}
  };
  const COLUMNS=['Evidence','Reasoning','Claims','Pressure','Paper'];
  const PRESETS={
    core:['assumption','target','proof','theorem'],
    stress:['theorem','finding','action'],
    paper:['theorem','prior_work','section'],
    all:Object.keys(KIND_META)
  };
  const WORKFLOW_PHASES=[
    {id:'direction',number:'01',title:'Select direction',description:'Compare research options and select the strongest feasible direction within the research scope.',stages:['direction_generation','direction_selection']},
    {id:'result',number:'02',title:'Establish the result',description:'Formalize, prove, independently audit, and govern the mathematical claim.',stages:['discovery','exploration','proof_development','local_adversarial_audit','governance_review','theorem_synthesis','final_adversarial_audit','arbiter']},
    {id:'contribution',number:'03',title:'Assess contribution',description:'Verify novelty, significance, scope, and the publication route supported by evidence.',stages:['novelty_audit','significance_audit','contribution_assessment','theory_bundle']},
    {id:'paper',number:'04',title:'Develop the paper',description:'Study exemplars, validate evidence, write, compile, review, revise, and package.',paper:true,stages:['literature_audit','exemplar_study','venue_selection','content_architecture','empirical_validation','section_writing','compilation','independent_review','revision','final_package']}
  ];
  let state=null,current=null,selected=null,activeKinds=new Set(),activePreset='core',evidenceMode='overview',live=true,pollTimer=null;
  let runner=null,csrfToken='',viewedJobId=null,pendingAction=null,lastTerminalRefresh=null,runnerPollTimer=null,launchingRunId=null;
  let evidenceExpanded=false,evidenceNativeFullscreen=false;
  let evidenceTask=null,loadingRunId=null,pendingEvidenceLoad=null,runnerLoading=false;
  let requestedRunId=null;
  let selectedDiagnosticId=null;

  function setEvidenceExpanded(expanded){
    evidenceExpanded=expanded;
    document.documentElement.classList.toggle('evidence-fullscreen',expanded);
    const button=$('evidenceFullscreen');
    button.setAttribute('aria-pressed',String(expanded));
    const name=expanded?'Exit fullscreen':'Enter fullscreen';
    button.setAttribute('aria-label',name);button.title=name;
    requestAnimationFrame(()=>{
      if(current&&evidenceMode==='graph')drawEdges(new Set([...document.querySelectorAll('.graph-node')].map(node=>node.dataset.id)));
    });
    if(!expanded)button.focus({preventScroll:true});
  }

  async function exitEvidenceFullscreen(){
    try{
      if(evidenceNativeFullscreen&&document.fullscreenElement)await document.exitFullscreen();
    }catch{toast('Use Escape to leave browser fullscreen')}
    evidenceNativeFullscreen=false;setEvidenceExpanded(false);
  }

  async function toggleEvidenceFullscreen(){
    const button=$('evidenceFullscreen');button.disabled=true;
    try{
      if(evidenceExpanded){await exitEvidenceFullscreen();return}
      setEvidenceExpanded(true);
      // Keep the expanded workspace usable when native fullscreen is unsupported or denied.
      if(!document.fullscreenElement&&document.documentElement.requestFullscreen){
        try{await document.documentElement.requestFullscreen({navigationUI:'hide'});evidenceNativeFullscreen=true}
        catch{toast('Expanded view enabled; browser fullscreen is unavailable')}
      }
    }finally{button.disabled=false;button.focus({preventScroll:true})}
  }

  document.addEventListener('fullscreenchange',()=>{
    if(evidenceNativeFullscreen&&!document.fullscreenElement){evidenceNativeFullscreen=false;setEvidenceExpanded(false)}
  });
  document.addEventListener('keydown',event=>{
    if(event.key==='Escape'&&selectedDiagnosticId){closeIssueInspector();return}
    if(event.key==='Escape'&&evidenceExpanded){
      if($('commandDrawer').classList.contains('open')){closeCommand();return}
      void exitEvidenceFullscreen();
    }
  });
  $('evidenceFullscreen').onclick=toggleEvidenceFullscreen;

  function toast(message){const el=$('toast');el.textContent=message;el.classList.add('show');setTimeout(()=>el.classList.remove('show'),1800)}
  function label(value){return String(value??'').replaceAll('_',' ')}
  function compact(value,n=150){const text=String(value??'').replace(/\s+/g,' ').trim();return text.length>n?`${text.slice(0,n-1)}…`:text}
  function escapeHTML(value){return String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]))}
  function sync(mode,text){$('syncState').className=`sync ${mode}`;$('syncState').querySelector('span').textContent=text}
  function currentNode(id){return current?.graph?.nodes?.find(node=>node.id===id)}
  function terminal(status){return ['completed','failed','cancelled','interrupted'].includes(status)}
  function jobTime(job){return Date.parse(job.updated_at||job.completed_at||job.started_at||'')||0}
  function jobRank(job){
    if(job.job_id===runner?.active_job_id||!terminal(job.status))return 0;
    if(job.status==='completed')return 1;
    if((job.event_count||0)>0)return 2;
    return 3;
  }
  function runJobs(){return current?(runner?.jobs||[]).filter(job=>job.run_id===current.run_id).sort((a,b)=>jobRank(a)-jobRank(b)||jobTime(b)-jobTime(a)):[]}
  function selectedRunJob(){
    const jobs=runJobs(),active=jobs.find(job=>job.job_id===runner?.active_job_id)||jobs.find(job=>!terminal(job.status));
    if(active)return active;
    if(jobs.some(job=>job.job_id===viewedJobId))return jobs.find(job=>job.job_id===viewedJobId);
    return jobs.find(job=>job.status==='completed')||jobs[0]||null;
  }
  async function postJSON(path,payload,authorized=true){
    const headers={'Content-Type':'application/json'};if(authorized)headers['X-TheoremGate-Token']=csrfToken;
    const response=await fetch(path,{method:'POST',headers,body:JSON.stringify(payload)});const result=await response.json();
    if(!response.ok)throw new Error(result.error||'TheoremAudit request failed');return result;
  }

  function load(runId=null,quiet=false){
    runId=runId||null;
    if(runId!==requestedRunId){
      requestedRunId=runId;current=null;selected=null;selectedDiagnosticId=null;viewedJobId=null;lastTerminalRefresh=null;pendingAction=null;
      activeKinds.clear();activePreset='core';evidenceMode='overview';
      closeCommand();renderAll();
    }
    if(evidenceTask){
      // Coalesce refreshes, but retain the latest explicit run selection.
      if(runId!==loadingRunId||pendingEvidenceLoad)pendingEvidenceLoad={runId,quiet};
      return evidenceTask;
    }
    evidenceTask=(async()=>{
      let request={runId,quiet};
      while(request){
        loadingRunId=request.runId;pendingEvidenceLoad=null;
        await readEvidence(request.runId,request.quiet);
        request=pendingEvidenceLoad;
      }
    })().finally(()=>{evidenceTask=null;loadingRunId=null});
    return evidenceTask;
  }

  async function readEvidence(runId,quiet){
    if(!quiet)sync('','Reading evidence');
    try{
      const response=await fetch(`/api/state${runId?`?run=${encodeURIComponent(runId)}`:''}`,{cache:'no-store'});
      if(!response.ok)throw new Error((await response.json()).error||'Unable to read state');
      const nextState=await response.json();
      if(pendingEvidenceLoad)return;
      const previous=selected?.id;state=nextState;
      current=runId?state.runs.find(run=>run.run_id===runId)||null:null;
      if(runId&&!current)throw new Error('The selected research run is unavailable');
      renderAll();
      if(previous&&currentNode(previous))selectNode(previous);
      sync('live','Updated');
    }catch(error){if(pendingEvidenceLoad)return;sync('error',current?'Connection lost':'Unable to read evidence');if(!current)renderAll();if(!quiet)toast(error.message)}
  }

  function renderAll(){
    const runSelect=$('runSelect');runSelect.disabled=false;runSelect.innerHTML='<option value="">New research</option>';
    (state?.runs||[]).forEach(run=>{const option=document.createElement('option');option.value=run.run_id;option.textContent=`${run.run_id} — ${compact(run.question,70)}`;runSelect.appendChild(option)});runSelect.value=requestedRunId||'';
    document.querySelector('.app-shell').classList.toggle('new-research',!current);
    $('researchSummary').classList.toggle('hidden',!current);
    document.querySelectorAll('.nav-item').forEach(button=>{button.disabled=button.dataset.view!=='run'&&!current});
    if(!current){
      ['question','routeTier','routeMeta','kindFilters','resultsOverview','graphColumns','edgeLayer','diagnosticDecision','claimImpact','diagnosticsList','lineageSummary','workflowPhases','paperSections','objectTitle','objectSummary','objectDetails','objectRelations','objectSource'].forEach(id=>{$(id).textContent=''});
      $('diagnosticBadge').textContent='0';$('graphSearch').value='';$('paperEditInstructions').value='';
      $('issueInspector').classList.add('hidden');$('objectInspector').classList.add('hidden');$('emptyInspector').classList.remove('hidden');document.querySelector('.inspector').classList.remove('open');
      $('paperFrame').removeAttribute('src');delete $('paperFrame').dataset.run;
      $('openPdf').removeAttribute('href');$('openPdf').classList.add('hidden');$('manuscriptWorkspace').classList.add('hidden');$('revisePaper').disabled=true;
      if(!requestedRunId)switchView('run');renderRunner();return;
    }
    const selectedVenue=current.venue_templates?.selected||'venue pending';
    $('question').textContent=current.question;$('routeTier').textContent=label(current.route.manuscript_kind);$('routeMeta').textContent=current.venue_templates?.selected?`${label(selectedVenue)} format`:'Format not selected';
    $('diagnosticBadge').textContent=reviewIssues(current).length;
    renderFilters();renderResultsOverview();renderEvidenceMode();renderGraph();renderDiagnostics();renderManuscript();renderPipelines();renderRunner();
  }

  function linkedNodes(id){
    const ids=new Set();current.graph.edges.forEach(edge=>{if(edge.source===id)ids.add(edge.target);if(edge.target===id)ids.add(edge.source)});
    return [...ids].map(currentNode).filter(Boolean);
  }

  function resultExperiments(id){return (current.empirical?.experiments||[]).filter(item=>(item.claim_ids||[]).includes(id)||item.target_statement_id===id)}
  function evidenceMetric(labelText,count,stateName=''){return `<div class="evidence-metric ${stateName}"><b>${escapeHTML(count)}</b><span>${escapeHTML(labelText)}</span></div>`}
  function resultHeading(statement){
    const text=String(statement.informal||'Accepted research result').trim();const sentence=text.match(/^.*?[.!?](?:\s|$)/)?.[0]||text;
    return compact(sentence,150);
  }

  function renderResultsOverview(){
    const accepted=current.accepted_statements||[],proofs=current.graph.nodes.filter(node=>node.kind==='proof'),verified=current.graph.nodes.filter(node=>node.kind==='prior_work'&&node.status==='verified'),openFindings=current.graph.nodes.filter(node=>node.kind==='finding'&&node.status!=='resolved'),sections=current.manuscript?.sections||[],experiments=current.empirical?.experiments||[];
    const summary=`<section class="evidence-summary"><div><span class="kicker">At a glance</span><h4>${accepted.length?`${accepted.length} governed result${accepted.length===1?'':'s'}`:'No governed result yet'}</h4><p>${accepted.length?'Each result below is traced to its proof, positioning, empirical evidence, paper use, and unresolved pressure.':`The run is currently at ${escapeHTML(label(current.current_theory_stage||current.theory_status||'research setup'))}. Results will appear here after synthesis and governance.`}</p></div><div class="evidence-summary-metrics">${evidenceMetric('accepted',accepted.length,accepted.length?'good':'')}${evidenceMetric('proof records',proofs.length,proofs.length?'good':'')}${evidenceMetric('verified works',verified.length,verified.length?'good':'')}${evidenceMetric('experiments',experiments.length,experiments.length?'good':'')}${evidenceMetric('paper sections',sections.length,sections.length?'good':'')}${evidenceMetric('open issues',openFindings.length,openFindings.length?'warn':'good')}</div></section>`;
    if(!accepted.length){
      const retained=current.retained_nonfinal_statements||[];
      $('resultsOverview').innerHTML=summary+`<section class="evidence-empty"><div class="empty-glyph">⌁</div><h4>Evidence is still being developed</h4><p>${retained.length?`${retained.length} result${retained.length===1?' is':'s are'} retained for further work, but none has passed the acceptance gate.`:'The proof and audit teams have not produced an accepted result for this run yet.'}</p><button class="secondary-button" data-open-graph>Inspect research structure</button></section>`;
    }else{
      const cards=accepted.map((statement,index)=>{
        const node=currentNode(statement.id),related=node?linkedNodes(statement.id):[],nodeCount=kind=>related.filter(item=>item.kind===kind).length,proofCount=nodeCount('proof'),literatureCount=nodeCount('prior_work'),findingCount=related.filter(item=>item.kind==='finding'&&item.status!=='resolved').length,actionCount=nodeCount('action'),sectionCount=nodeCount('section'),claimExperiments=resultExperiments(statement.id),experimentCount=claimExperiments.length;
        const scope=statement.scope||node?.details?.proven_scope||'',caveats=statement.caveats||node?.details?.honest_caveats||'';
        return `<article class="result-card"><div class="result-card-head"><div class="result-number">${String(index+1).padStart(2,'0')}</div><div><div class="result-meta"><span>${escapeHTML(statement.id)}</span><em>${escapeHTML(label(statement.decision||node?.status||'accepted'))}</em></div><h4>${escapeHTML(resultHeading(statement))}</h4></div></div><p class="result-statement">${escapeHTML(statement.informal)}</p><div class="result-support">${evidenceMetric('proofs',proofCount,proofCount?'good':'warn')}${evidenceMetric('related works',literatureCount,literatureCount?'good':'')}${evidenceMetric('experiments',experimentCount,experimentCount?'good':'')}${evidenceMetric('paper sections',sectionCount,sectionCount?'good':'')}${evidenceMetric('open findings',findingCount,findingCount?'warn':'good')}${evidenceMetric('next actions',actionCount,actionCount?'warn':'')}</div>${scope?`<div class="result-scope"><b>Proved scope</b><p>${escapeHTML(scope)}</p></div>`:''}${caveats?`<details class="result-caveats"><summary>Limits and caveats</summary><p>${escapeHTML(caveats)}</p></details>`:''}<div class="result-actions"><button data-inspect-result="${escapeHTML(statement.id)}">Inspect evidence</button><button class="graph-link" data-graph-result="${escapeHTML(statement.id)}">Open in advanced graph →</button></div></article>`;
      }).join('');
      $('resultsOverview').innerHTML=summary+`<div class="result-list">${cards}</div>`;
    }
    document.querySelectorAll('[data-inspect-result]').forEach(button=>button.onclick=()=>selectNode(button.dataset.inspectResult));
    document.querySelectorAll('[data-graph-result]').forEach(button=>button.onclick=()=>{setEvidenceMode('graph');applyPreset('all');selectNode(button.dataset.graphResult)});
    document.querySelectorAll('[data-open-graph]').forEach(button=>button.onclick=()=>setEvidenceMode('graph'));
  }

  function renderEvidenceMode(){
    $('resultsOverview').classList.toggle('hidden',evidenceMode!=='overview');$('advancedGraph').classList.toggle('hidden',evidenceMode!=='graph');
    document.querySelectorAll('[data-evidence-mode]').forEach(button=>button.classList.toggle('active',button.dataset.evidenceMode===evidenceMode));
    if(evidenceMode==='graph')requestAnimationFrame(renderGraph);
  }
  function setEvidenceMode(mode){evidenceMode=mode==='graph'?'graph':'overview';renderEvidenceMode()}

  function renderFilters(){
    const counts=current.graph.kind_counts;const available=Object.keys(KIND_META).filter(kind=>counts[kind]);
    if(!activeKinds.size)PRESETS[activePreset].filter(kind=>available.includes(kind)).forEach(kind=>activeKinds.add(kind));
    activeKinds=new Set([...activeKinds].filter(kind=>available.includes(kind)));
    $('kindFilters').innerHTML=available.map(kind=>{const meta=KIND_META[kind];return `<button class="kind-filter ${activeKinds.has(kind)?'active':''}" data-kind="${kind}" style="--node-color:${meta.color}"><i></i><span>${meta.label}</span><em>${counts[kind]}</em></button>`}).join('');
    document.querySelectorAll('.kind-filter').forEach(button=>button.onclick=()=>{const kind=button.dataset.kind;activePreset='custom';document.querySelectorAll('[data-preset]').forEach(item=>item.classList.remove('active'));activeKinds.has(kind)?activeKinds.delete(kind):activeKinds.add(kind);button.classList.toggle('active');renderGraph()});
  }

  function renderGraph(){
    if(!current)return;
    const query=$('graphSearch').value.trim().toLowerCase();
    const visible=current.graph.nodes.filter(node=>activeKinds.has(node.kind)&&(!query||`${node.id} ${node.title} ${node.summary}`.toLowerCase().includes(query)));
    const visibleIds=new Set(visible.map(node=>node.id));
    $('graphColumns').innerHTML=COLUMNS.map(column=>{
      const nodes=visible.filter(node=>KIND_META[node.kind]?.column===column);
      return `<div class="graph-column" data-column="${column}"><div class="column-title">${column} · ${nodes.length}</div>${nodes.map(node=>nodeHTML(node)).join('')}</div>`;
    }).join('');
    document.querySelectorAll('.graph-node').forEach(button=>button.onclick=()=>selectNode(button.dataset.id));
    requestAnimationFrame(()=>{if(selected)selectNode(selected.id);else drawEdges(visibleIds)});
  }

  function nodeHTML(node){const meta=KIND_META[node.kind]||{color:'#68736d'};return `<button class="graph-node ${selected?.id===node.id?'selected':''}" data-id="${node.id}" style="--node-color:${meta.color}"><span class="node-top"><b>${node.id}</b><em>${label(node.status)}</em></span><p>${compact(node.summary||node.title,170)}</p></button>`}

  function drawEdges(visibleIds){
    const viewport=$('graphViewport'),layer=$('edgeLayer'),base=viewport.getBoundingClientRect();
    const width=$('graphColumns').scrollWidth,height=$('graphColumns').scrollHeight;layer.setAttribute('width',width);layer.setAttribute('height',height);layer.style.width=`${width}px`;layer.style.height=`${height}px`;
    layer.innerHTML=current.graph.edges.filter(edge=>visibleIds.has(edge.source)&&visibleIds.has(edge.target)).map(edge=>{
      const source=document.querySelector(`.graph-node[data-id="${CSS.escape(edge.source)}"]`),target=document.querySelector(`.graph-node[data-id="${CSS.escape(edge.target)}"]`);if(!source||!target)return '';
      const a=source.getBoundingClientRect(),b=target.getBoundingClientRect();const x1=a.right-base.left+viewport.scrollLeft,y1=a.top-base.top+viewport.scrollTop+a.height/2,x2=b.left-base.left+viewport.scrollLeft,y2=b.top-base.top+viewport.scrollTop+b.height/2;const bend=Math.max(28,(x2-x1)*.45);const active=selected&&(edge.source===selected.id||edge.target===selected.id);
      const muted=selected&&!active;return `<path class="edge ${active?'active':muted?'muted':''}" d="M ${x1} ${y1} C ${x1+bend} ${y1}, ${x2-bend} ${y2}, ${x2} ${y2}"><title>${edge.relation}</title></path>`;
    }).join('');
  }

  function selectNode(id){
    selected=currentNode(id);if(!selected)return;
    selectedDiagnosticId=null;$('issueInspector').classList.add('hidden');
    $('emptyInspector').classList.add('hidden');$('objectInspector').classList.remove('hidden');document.querySelector('.inspector').classList.add('open');
    $('objectKind').textContent=label(selected.kind);$('objectTitle').textContent=selected.title;$('objectStatus').textContent=[label(selected.status),selected.severity&&label(selected.severity)].filter(Boolean).join(' · ');$('objectSummary').textContent=selected.summary||'No summary recorded.';
    const relations=current.graph.edges.filter(edge=>edge.source===id||edge.target===id);$('objectRelations').innerHTML=relations.length?relations.map(edge=>{const other=edge.source===id?edge.target:edge.source;const direction=edge.source===id?'→':'←';return `<div class="relation"><span>${direction} ${label(edge.relation)}</span><button data-related="${other}">${other}</button></div>`}).join(''):'<div class="relation">No graph relation recorded.</div>';
    document.querySelectorAll('[data-related]').forEach(button=>button.onclick=()=>selectNode(button.dataset.related));
    $('objectDetails').innerHTML=Object.entries(selected.details||{}).filter(([,value])=>value!==''&&value!==null&&!(Array.isArray(value)&&!value.length)).map(([key,value])=>`<dl class="detail"><dt>${label(key)}</dt><dd>${typeof value==='object'?JSON.stringify(value,null,2):value}</dd></dl>`).join('');
    $('objectSource').textContent=selected.source_path?`Source · ${selected.source_path}`:'No source path recorded';const neighbors=new Set([id]);current.graph.edges.forEach(edge=>{if(edge.source===id)neighbors.add(edge.target);if(edge.target===id)neighbors.add(edge.source)});document.querySelectorAll('.graph-node').forEach(node=>{node.classList.toggle('selected',node.dataset.id===id);node.classList.toggle('dim',!neighbors.has(node.dataset.id))});drawEdges(new Set([...document.querySelectorAll('.graph-node')].map(node=>node.dataset.id)));
  }

  function closeIssueInspector(restoreFocus=true){
    const id=selectedDiagnosticId;selectedDiagnosticId=null;
    $('issueInspector').classList.add('hidden');$('emptyInspector').classList.remove('hidden');
    document.querySelector('.inspector').classList.remove('open');
    if(restoreFocus&&id)document.querySelector(`[data-diagnostic="${CSS.escape(id)}"]`)?.focus({preventScroll:true});
  }

  function inspectDiagnostic(id,focus=true){
    const diagnostic=current?.compiler?.diagnostics?.find(item=>item.id===id);
    if(!diagnostic){closeIssueInspector(false);return}
    selected=null;selectedDiagnosticId=id;
    $('emptyInspector').classList.add('hidden');$('objectInspector').classList.add('hidden');
    $('issueInspector').classList.remove('hidden');document.querySelector('.inspector').classList.add('open');
    $('issueTitle').textContent=diagnostic.title||diagnostic.id;
    $('issueStatus').textContent=[diagnostic.id,label(diagnostic.severity),label(diagnostic.category)].filter(Boolean).join(' · ');
    $('issueMessage').textContent=diagnostic.message||'No additional description supplied.';
    $('issueAction').textContent=diagnostic.action||'No next step supplied.';
    $('issueSource').textContent=diagnostic.source||'No source supplied.';
    const targets=[...new Set([...(diagnostic.target_ids||[]),...(currentNode(id)?[id]:[])])];
    $('issueTargets').innerHTML=targets.length?targets.map(target=>currentNode(target)
      ?`<button type="button" data-issue-target="${escapeHTML(target)}">${escapeHTML(target)}</button>`
      :`<span>${escapeHTML(target)} (not available in the evidence graph)</span>`).join(''):'No linked graph objects.';
    $('issueTargets').querySelectorAll('[data-issue-target]').forEach(button=>button.onclick=()=>{
      const target=button.dataset.issueTarget;
      switchView('map');$('graphSearch').value='';applyPreset('all');setEvidenceMode('graph');selectNode(target);
      requestAnimationFrame(()=>document.querySelector(`.graph-node[data-id="${CSS.escape(target)}"]`)?.scrollIntoView({block:'nearest',inline:'nearest'}));
    });
    if(focus){document.querySelector('.inspector').scrollTop=0;$('issueTitle').focus({preventScroll:true})}
  }

  function reviewIssues(run){
    return (run?.compiler?.diagnostics||[]).filter(item=>{
      if(['publication','development'].includes(item.group))return false;
      // Unlinked literature-file diagnostics remain in the run data, outside proof review.
      const literatureFile=item.group==='integrity'&&item.category==='artifact_integrity'
        &&(item.source||'').split('/').includes('literature')
        &&!(item.target_ids||[]).filter(Boolean).length;
      return !literatureFile;
    });
  }

  function renderDiagnostics(){
    const openGroups=new Map([...$('diagnosticsList').querySelectorAll('details[data-issue-group]')].map(group=>[group.dataset.issueGroup,group.open]));
    const compiler=current.compiler,items=reviewIssues(current),decision={...(compiler.decision_summary||{state:compiler.status,headline:'Review status',explanation:'Inspect the mathematical and manuscript findings below.',next_action:'Review the saved evidence.'})};
    const openCount=group=>items.filter(item=>(item.group||'mathematics')===group&&['error','warning'].includes(item.severity)).length;
    const metrics=[
      ['mathematics',openCount('mathematics'),'Math blockers'],
      ['integrity',openCount('integrity'),'Proof evidence'],
      ['manuscript',items.filter(item=>item.group==='manuscript').length,'Paper findings']
    ];
    if(decision.state==='evidence_attention'&&metrics[1][1]===0){
      decision.headline=metrics[2][1]?'Manuscript findings need attention':current.paper_status==='completed'?'Manuscript review is complete':'Review is not yet complete';
      decision.explanation='This view covers mathematical arguments, proof evidence, and manuscript review.';
      decision.next_action=items.length?'Inspect the findings below.':'Inspect the reviewed results or follow progress in Stages.';
    }
    const impacts=current.claim_impact||[];
    const compact=current.paper_status==='completed'&&metrics.every(([,count])=>count===0)
      &&impacts.length>0&&impacts.every(item=>item.status==='accepted'&&!(item.blocking_findings||[]).length);
    const claimsExpanded=$('claimImpact').querySelector('details')?.open??!compact;
    $('diagnosticDecision').className=`diagnostic-decision ${decision.state}`;$('diagnosticDecision').innerHTML=`<div class="decision-main"><span class="kicker">Assessment</span><h4>${escapeHTML(decision.headline)}</h4><p>${escapeHTML(decision.explanation)}</p><div class="decision-next"><b>Next step</b><span>${escapeHTML(decision.next_action)}</span></div></div><div class="decision-side"><div class="decision-metrics">${metrics.map(([group,count,title])=>`<div data-metric="${group}"><b>${count}</b><span>${title}</span></div>`).join('')}</div></div>`;
    if(compact){
      $('diagnosticDecision').className='diagnostic-decision mathematics-clear';
      $('diagnosticDecision').innerHTML=`<div class="decision-main"><h4>No unresolved mathematical blockers</h4><p>${impacts.length} result${impacts.length===1?' has':'s have'} passed the system's mathematical review.</p></div>`;
    }
    $('claimImpact').innerHTML=impacts.length?`<div class="claim-impact-head"><div><span class="kicker">Mathematical review</span><h4>Claim decisions and linked findings</h4></div><p>Findings follow each claim's assumptions and supporting proofs, including dependencies. Evidence-file checks are listed separately below.</p></div><div class="claim-impact-grid">${impacts.map(item=>{const salvage=item.status.startsWith('salvage'),blocked=item.status==='blocked_by_proof';return `<article class="claim-impact-card ${blocked?'blocked':salvage?'salvage':'accepted'}"><header><b>${escapeHTML(item.statement_id)}</b><span>${escapeHTML(label(item.status))}</span></header><dl><div><dt>Supporting proofs</dt><dd>${escapeHTML((item.proof_closure||[]).join(', ')||'No proof recorded')}</dd></div><div><dt>Original target</dt><dd>${escapeHTML((item.research_origin||[]).join(', ')||'Not recorded')} <em>research origin, not a proof dependency</em></dd></div><div><dt>Linked blockers</dt><dd>${escapeHTML((item.blocking_findings||[]).join(', ')||'None')}</dd></div><div><dt>Minor findings</dt><dd>${escapeHTML((item.minor_findings||[]).join(', ')||'None')}</dd></div></dl><p>${escapeHTML(item.recommendation||'')}</p></article>`}).join('')}</div>`:'';
    if(impacts.length)$('claimImpact').innerHTML=`<details class="claim-impact-details" ${claimsExpanded?'open':''}><summary>Reviewed results (${impacts.length})</summary>${$('claimImpact').innerHTML}</details>`;
    const groups=[
      {id:'mathematics',title:'Mathematical review findings',description:'Questions about arguments, assumptions, definitions, and supporting proofs.',open:true},
      {id:'integrity',title:'Proof evidence problems',description:'Missing, inconsistent, or unreadable supporting evidence.',open:true},
      {id:'manuscript',title:'Manuscript and review',description:'Writing, compilation, figures, reviewer findings, and researcher comments.'}
    ];
    const diagnosticHTML=item=>`<article class="diagnostic ${item.severity}"><i></i><div><small>${escapeHTML(label(item.category))} · ${escapeHTML(item.id)}</small><h4>${escapeHTML(item.title)}</h4><p>${escapeHTML(item.message)}</p><p><b>Next:</b> ${escapeHTML(item.action)}</p></div><button data-diagnostic="${escapeHTML(item.id)}">Inspect</button></article>`;
    const populated=groups.map(group=>({...group,items:items.filter(item=>(item.group||'mathematics')===group.id)})).filter(group=>group.items.length);
    const groupHTML=group=>`<details class="diagnostic-group ${group.id}" data-issue-group="${group.id}" ${(openGroups.get(group.id)??group.open)?'open':''}><summary><div><h4>${escapeHTML(group.title)}</h4><p>${escapeHTML(group.description)}</p></div><span>${group.items.length}</span></summary><div class="diagnostic-group-list">${group.items.map(diagnosticHTML).join('')}</div></details>`;
    $('diagnosticsList').innerHTML=populated.map(groupHTML).join('');
    document.querySelectorAll('[data-diagnostic]').forEach(button=>button.onclick=()=>inspectDiagnostic(button.dataset.diagnostic));
    if(selectedDiagnosticId){
      if(items.some(item=>item.id===selectedDiagnosticId))inspectDiagnostic(selectedDiagnosticId,false);
      else closeIssueInspector(false);
    }
  }

  function phaseStatus(items){if(!items.length)return 'locked';if(items.every(item=>['completed','skipped'].includes(item.status)))return 'completed';if(items.some(item=>item.status==='in_progress'))return 'in_progress';return 'pending'}
  function displayedStageStatus(status){if(status!=='in_progress')return status;const execution=describeRunExecution(current,runner);return execution.state==='running'?'in_progress':execution.state==='paused'?'awaiting_resume':execution.state==='blocked'?'blocked':'current_stage'}
  function stageItem(stage,index){const shown=displayedStageStatus(stage.status),history=stage.status==='skipped'?'not required for this completed package':stage.reopened?`completed in cycle ${stage.last_completed_cycle} · ${label(shown)}`:stage.ever_completed&&stage.status!=='completed'?`completed previously · ${label(shown)}`:label(shown);return `<div class="phase-stage ${shown} ${stage.reopened?'reopened':''}"><i>${stage.status==='completed'?'✓':stage.status==='skipped'?'—':stage.reopened?'↻':String(index+1).padStart(2,'0')}</i><div><b>${escapeHTML(stage.label)}</b><span>${escapeHTML(history)} · ${escapeHTML(label(stage.actor||'controller'))}</span></div></div>`}
  function renderPipelines(){
    const theoryById=Object.fromEntries((current.theory_stages||[]).map(item=>[item.id,item])),paperById=Object.fromEntries((current.paper_stages||[]).map(item=>[item.id,item]));
    const expanded=new Map([...$('workflowPhases').querySelectorAll('details[data-phase]')].map(item=>[item.dataset.phase,item.open]));
    $('workflowPhases').innerHTML=WORKFLOW_PHASES.map(phase=>{const source=phase.paper?paperById:theoryById,items=phase.stages.map(id=>source[id]).filter(Boolean),status=displayedStageStatus(phaseStatus(items)),open=expanded.get(phase.id)??status!=='locked';return `<details data-phase="${phase.id}" class="workflow-phase ${status}" ${open?'open':''}><summary title="Click to expand or collapse this phase"><i>${phase.number}</i><div><h4>${phase.title}</h4><p>${phase.description}</p></div><span>${label(status)}</span></summary><div class="phase-stages">${items.length?items.map(stageItem).join(''):'<p class="phase-locked">This phase opens when the preceding evidence gates are complete.</p>'}</div></details>`}).join('');
    const lineage=current.lineage||{},correction=current.correction_state||{},strengthening=current.strengthening_state||{},children=(state.runs||[]).filter(run=>run.parent_run_id===current.run_id),parent=lineage.parent_run_id;
    const correctionNote=correction.round?`<div class="automatic-state-strip"><span>Proof correction ${escapeHTML(correction.round)} of ${escapeHTML(correction.maximum_rounds||3)} · ${escapeHTML(label(correction.status||'in_progress'))}</span><span>${escapeHTML((correction.finding_ids||[]).join(', ')||'Audited finding')}</span></div>`:'';
    const previousRoute=strengthening.previous_tier||strengthening.previous_submission_readiness||'evidence_incomplete';
    const finalRoute=strengthening.final_submission_readiness||strengthening.publication_goal||current.execution_contract?.publication_goal||'goal';
    const strengtheningNote=strengthening.round?`<div class="automatic-state-strip"><span>Contribution strengthening ${escapeHTML(strengthening.round)} of ${escapeHTML(strengthening.maximum_rounds||2)} · ${escapeHTML(label(strengthening.status||'in_progress'))}</span><span>${escapeHTML(label(previousRoute))} → ${escapeHTML(label(finalRoute))}</span></div>`:'';
    $('lineageSummary').innerHTML=`<div><span class="kicker">Research history</span><h4>${parent?`Revision cycle ${lineage.revision_cycle||1}`:'Primary research run'}</h4><p>${parent?`This run preserves and revises evidence from ${escapeHTML(parent)}.`:'Failed proof and contribution passes are archived inside this run; major research changes create a linked revision.'}</p>${correctionNote}${strengtheningNote}</div><div class="lineage-links">${parent?`<button data-lineage-run="${escapeHTML(parent)}">View previous run</button>`:''}${children.map(child=>`<button data-lineage-run="${escapeHTML(child.run_id)}">View revision ${escapeHTML(child.run_id)}</button>`).join('')}${lineage.next_action?.startsWith('child_')?`<span class="lineage-alert">${lineage.next_action==='child_mathematical_repair'?'Revision recommended':'Extension recommended'}</span>`:''}</div>`;
    document.querySelectorAll('[data-lineage-run]').forEach(button=>button.onclick=()=>load(button.dataset.lineageRun));
  }
  function renderManuscript(){
    const manuscript=current.manuscript||{};const available=manuscript.pdf_available;
    $('noManuscript').classList.toggle('hidden',available);$('manuscriptWorkspace').classList.toggle('hidden',!available);$('openPdf').classList.toggle('hidden',!available);$('revisePaper').disabled=!available;
    const frame=$('paperFrame');
    if(frame.dataset.run&&(!available||frame.dataset.run!==current.run_id)){frame.src='about:blank';delete frame.dataset.run}
    if(!available)return;const url=`/api/paper.pdf?run=${encodeURIComponent(current.run_id)}#view=FitH`;
    if($('manuscriptView').classList.contains('active')&&frame.dataset.run!==current.run_id){frame.src=url;frame.dataset.run=current.run_id}
    $('openPdf').href=url;
    $('paperSections').innerHTML=manuscript.sections?.length?manuscript.sections.map(section=>`<button class="paper-section" data-section="SEC:${section.name}"><span>${section.title||label(section.name)}</span><em>${(section.claims_used||[]).length} claims</em></button>`).join(''):'<p>No section index recorded.</p>';
    document.querySelectorAll('[data-section]').forEach(button=>button.onclick=()=>{switchView('map');setEvidenceMode('graph');applyPreset('paper');selectNode(button.dataset.section)});
  }

  async function loadRunner(quiet=false){
    if(runnerLoading)return;
    runnerLoading=true;
    try{
      const response=await fetch('/api/runner',{cache:'no-store'});if(!response.ok)throw new Error('Runner unavailable');runner=await response.json();csrfToken=runner.csrf_token||csrfToken;
      const jobs=runJobs(),active=jobs.find(job=>job.job_id===runner.active_job_id)||jobs.find(job=>!terminal(job.status));
      if(active)viewedJobId=active.job_id;else if(!jobs.some(job=>job.job_id===viewedJobId))viewedJobId=jobs[0]?.job_id||null;
      renderRunner();if(current)renderPipelines();if(viewedJobId)await loadEvents(viewedJobId);
      const shown=selectedRunJob();if(shown&&terminal(shown.status)&&lastTerminalRefresh!==shown.job_id&&!evidenceTask){lastTerminalRefresh=shown.job_id;await load(current?.run_id||null,true)}
    }catch(error){runner={available:false,jobs:[],active_job_id:null,state_error:true};renderRunner();if(current)renderPipelines();if(!quiet)toast(error.message)}
    finally{runnerLoading=false}
  }

  async function loadEvents(jobId){
    const runId=current?.run_id;
    const stillSelected=()=>Boolean(runId&&current?.run_id===runId&&selectedRunJob()?.job_id===jobId);
    try{const response=await fetch(`/api/run/events?job=${encodeURIComponent(jobId)}&after=0`,{cache:'no-store'});const result=await response.json();if(!response.ok)throw new Error(result.error||'Could not read Codex events');if(stillSelected())renderEvents(result.events||[])}catch(error){if(stillSelected())renderEvents([],error.message)}
  }

  function renderRunner(){
    const empiricalActivity=describeExperimentActivity(current);
    $('experimentActivity').classList.toggle('hidden',!empiricalActivity);
    $('experimentActivity').textContent=empiricalActivity;
    const execution=describeRunExecution(current,runner),resuming=launchingRunId===current?.run_id;
    $('executionBar').classList.toggle('hidden',!current);$('executionBar').dataset.state=resuming?'starting':execution.state;
    $('executionStatus').textContent=resuming?'Starting':execution.title;$('executionDetail').textContent=execution.detail;
    $('resumeRun').classList.toggle('hidden',!execution.showResume&&!resuming);$('resumeRun').disabled=!execution.canResume||Boolean(launchingRunId);
    $('resumeRun').querySelector('b').textContent=resuming?'Starting...':'Resume run';$('resumeRun').title=execution.canResume?'Continue the selected run from its saved stage':execution.detail;
    if(!runner)return;const available=Boolean(runner.available),workspaceActive=runner.jobs?.find(job=>job.job_id===runner.active_job_id),jobs=runJobs(),active=jobs.find(job=>job.job_id===runner.active_job_id)||jobs.find(job=>!terminal(job.status)),shown=selectedRunJob();
    const availability=$('runnerAvailability');availability.className=`runner-availability ${available?'ready':'offline'}`;availability.querySelector('span').textContent=available?(active?'Codex is working on this run':workspaceActive?'Codex is working on another run':'Codex CLI ready'):'Codex CLI unavailable';
    $('runnerBadge').textContent=active?'live':jobs.length?'saved':available?'ready':'off';$('runnerBadge').className=active?'busy':'';$('startRun').disabled=!available||Boolean(workspaceActive);if(workspaceActive)$('startRun').textContent=active?'This research run is active':'Another research run is active';else syncLaunchMode();
    const history=$('jobHistory');history.innerHTML='';document.querySelector('.history-panel').classList.toggle('hidden',!current);jobs.forEach(job=>{const button=document.createElement('button');button.type='button';button.className=`history-job ${job.job_id===shown?.job_id?'active':''}`;const main=document.createElement('span');main.textContent=job.label||job.kind;const meta=document.createElement('small');meta.textContent=`${label(job.status)} · ${new Date(job.started_at).toLocaleString()}`;button.append(main,meta);button.onclick=()=>{viewedJobId=job.job_id;renderRunner();loadEvents(job.job_id)};history.appendChild(button)});if(!jobs.length&&current)history.innerHTML='<p>No Workspace-launched Codex session is attached to this run. Terminal work still appears in Stages and Evidence.</p>';
    $('consoleCard').classList.toggle('quiet',!active&&!shown);if(!shown){$('jobTitle').textContent='No active session';$('jobStatus').textContent='idle';$('jobStatus').className='job-status idle';$('jobMeta').textContent='Research activity will appear here after a run starts.';$('cancelJob').classList.add('hidden');$('jobOutcome').classList.add('hidden');renderEvents([]);return}
    $('jobTitle').textContent=shown.label||'Codex session';$('jobStatus').textContent=shown.status==='completed'?'Session ended':label(shown.status);$('jobStatus').className=`job-status ${shown.status}`;$('cancelJob').classList.toggle('hidden',terminal(shown.status));$('cancelJob').dataset.jobId=shown.job_id;
    const details=[shown.model?`model ${shown.model}`:'configured model',shown.mode&&label(shown.mode),shown.run_id&&`run ${shown.run_id}`,shown.thread_id&&`thread ${shown.thread_id}`].filter(Boolean);$('jobMeta').textContent=details.join(' · ');
    const outcome=shown.outcome,holder=$('jobOutcome');holder.classList.toggle('hidden',!outcome);if(outcome)$('jobOutcomeSummary').textContent=outcome.summary||`Execution ended at ${label(outcome.current_stage)}.`;
  }

  function renderEvents(events,error=''){
    const feed=$('eventFeed');feed.innerHTML='';if(error){const empty=document.createElement('div');empty.className='console-empty error';empty.textContent=error;feed.appendChild(empty);return}
    if(!events.length){feed.innerHTML=current?'<div class="console-empty"><span>⌁</span><p>No captured activity for this research run. Sessions launched here stream live; terminal-launched work is reflected through Stages and Evidence.</p></div>':'<div class="console-empty"><span>⌁</span><p>No research started</p></div>';return}
    events.slice(-250).forEach(event=>{const article=document.createElement('article');article.className=`console-event ${event.type?.replaceAll('.','-')||''}`;const marker=document.createElement('i');const content=document.createElement('div');const top=document.createElement('header');const title=document.createElement('b');title.textContent=event.title||label(event.type);const time=document.createElement('time');time.textContent=new Date(event.timestamp).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit',second:'2-digit'});top.append(title,time);content.appendChild(top);if(event.message){const message=document.createElement('pre');message.textContent=event.message;content.appendChild(message)}article.append(marker,content);feed.appendChild(article)});feed.scrollTop=feed.scrollHeight;
  }

  async function startPipeline(event){
    event.preventDefault();const mode='full',question=$('researchQuestion').value.trim();if(!question){toast('Add a research question first');$('researchQuestion').focus();return}
    try{$('startRun').disabled=true;const result=await postJSON('/api/run/start',{mode,question,constraints:$('runConstraints').value,run_id:null,parent_run_id:null,model:null,auto_repair:false,max_auto_repair_rounds:0});viewedJobId=result.job.job_id;lastTerminalRefresh=null;toast('New research run started');await load(result.run_id,true);await loadRunner();switchView('run')}catch(error){toast(error.message);renderRunner()}
  }

  async function resumePipeline(){
    if(launchingRunId||!describeRunExecution(current,runner).canResume)return;
    const runId=current.run_id;launchingRunId=runId;renderRunner();
    try{
      const result=await postJSON('/api/run/start',{mode:'resume',run_id:runId,question:'',constraints:'',model:null,auto_repair:false,max_auto_repair_rounds:0});
      viewedJobId=result.job.job_id;lastTerminalRefresh=null;toast('Resuming saved run');
      await load(runId,true);await loadRunner();switchView('run');
    }catch(error){toast(error.message)}finally{launchingRunId=null;renderRunner()}
  }

  $('resumeRun').onclick=resumePipeline;

  async function cancelJob(){const jobId=$('cancelJob').dataset.jobId;if(!jobId||!window.confirm('Stop this Codex session? Completed TheoremAudit artifacts will remain on disk.'))return;try{await postJSON('/api/run/cancel',{job_id:jobId});toast('Stopping Codex session');await loadRunner()}catch(error){toast(error.message)}}
  function switchView(name){if(!current&&name!=='run')name='run';if(name!=='diagnostics'&&selectedDiagnosticId)closeIssueInspector(false);if(name!=='map'&&evidenceExpanded)void exitEvidenceFullscreen();document.querySelectorAll('.nav-item').forEach(item=>item.classList.toggle('active',item.dataset.view===name));document.querySelectorAll('.view').forEach(view=>view.classList.toggle('active',view.id===`${name}View`));if(name==='manuscript'&&current)renderManuscript()}
  function syncLaunchMode(){$('workflowMode').value='full';$('executionIntent').textContent='A new full original-research attempt will be created';$('startRun').innerHTML='Start research <span>→</span>'}

  async function openCommand(action,nodeId=selected?.id,note=''){
    if(!current)return;
    const runId=current.run_id;
    try{const result=await postJSON('/api/prompt',{run_id:runId,action,node_id:nodeId,note});if(current?.run_id!==runId)return;pendingAction={run_id:runId,action,node_id:nodeId,note};$('commandTitle').textContent=`${label(action)} · ${nodeId||'run'}`;$('commandPrompt').value=result.prompt;$('copyState').textContent='Review before sending';$('runPrompt').disabled=Boolean(runner?.active_job_id)||!runner?.available;$('commandDrawer').classList.add('open');$('scrim').classList.add('show')}catch(error){toast(error.message)}
  }
  function submitPaperEdit(){
    const instructions=$('paperEditInstructions').value.trim();if(!instructions){toast('Describe the requested paper change');$('paperEditInstructions').focus();return}
    const note=[
      'Researcher-authored paper revision request.',
      `Exact request: ${instructions}`,
      'Use $research-revision to infer the edit type, scope, target, and earliest invalidated stage from the request before changing evidence. Route it as revise_manuscript, revise_literature, rerun_experiments, rewrite_manuscript, or repair_mathematics. For a paper-only change, persist the exact request once with manuscript_tools.py add-user-comment using the inferred --edit-type, --scope, --target, and --priority required. For a mathematical change, bind the exact request to the linked revision-router ledger and do not reopen the completed parent paper merely to store a comment. Preserve unaffected evidence, rebuild all invalidated downstream stages, compile the revised manuscript, and run a fresh independent review.'
    ].join('\n\n');
    return openCommand('revise',null,note);
  }
  function closeCommand(){$('commandDrawer').classList.remove('open');$('scrim').classList.remove('show')}
  async function copyPrompt(){try{await navigator.clipboard.writeText($('commandPrompt').value);$('copyState').textContent='Copied — paste into Codex';toast('Prompt copied')}catch{$('commandPrompt').select();document.execCommand('copy');$('copyState').textContent='Copied — paste into Codex'}}
  async function runPrompt(){if(!pendingAction)return;try{$('runPrompt').disabled=true;const result=await postJSON('/api/run/action',{...pendingAction,prompt:$('commandPrompt').value,model:$('actionModel').value});viewedJobId=result.job.job_id;lastTerminalRefresh=null;closeCommand();switchView('run');toast('Research action started in Codex');await loadRunner()}catch(error){toast(error.message);$('runPrompt').disabled=Boolean(runner?.active_job_id)||!runner?.available}}

  function applyPreset(name){activePreset=name;activeKinds=new Set(PRESETS[name]);if(selected&&!activeKinds.has(selected.kind)){$('objectInspector').classList.add('hidden');$('emptyInspector').classList.remove('hidden');selected=null}document.querySelectorAll('[data-preset]').forEach(button=>button.classList.toggle('active',button.dataset.preset===name));renderFilters();renderGraph()}
  $('closeIssueInspector').onclick=()=>closeIssueInspector();
  $('runSelect').onchange=async event=>{await load(event.target.value);await loadRunner(true)};$('refreshButton').onclick=()=>load(requestedRunId);$('graphSearch').oninput=renderGraph;$('closeInspector').onclick=()=>{selected=null;$('objectInspector').classList.add('hidden');$('emptyInspector').classList.remove('hidden');document.querySelector('.inspector').classList.remove('open');renderGraph()};
  document.querySelectorAll('.nav-item').forEach(item=>item.onclick=()=>switchView(item.dataset.view));document.querySelectorAll('[data-jump-view]').forEach(item=>item.onclick=()=>switchView(item.dataset.jumpView));document.querySelectorAll('[data-evidence-mode]').forEach(button=>button.onclick=()=>setEvidenceMode(button.dataset.evidenceMode));document.querySelectorAll('[data-preset]').forEach(button=>button.onclick=()=>applyPreset(button.dataset.preset));document.querySelectorAll('[data-action]').forEach(button=>button.onclick=()=>openCommand(button.dataset.action));$('revisePaper').onclick=()=>{$('paperEditPanel').scrollIntoView({behavior:'smooth',block:'center'});$('paperEditInstructions').focus()};$('submitPaperEdit').onclick=submitPaperEdit;$('closeCommand').onclick=closeCommand;$('scrim').onclick=closeCommand;$('copyPrompt').onclick=copyPrompt;$('runPrompt').onclick=runPrompt;$('newRunForm').onsubmit=startPipeline;$('cancelJob').onclick=cancelJob;$('liveToggle').onclick=()=>{live=!live;$('liveToggle').classList.toggle('on',live);toast(live?'Auto-refresh enabled':'Auto-refresh paused')};syncLaunchMode();window.addEventListener('resize',()=>{if(current&&evidenceMode==='graph')renderGraph()});
  pollTimer=setInterval(()=>{if(live&&!document.hidden&&!evidenceTask)load(requestedRunId,true)},5000);runnerPollTimer=setInterval(()=>{if(!document.hidden)loadRunner(true)},1800);Promise.all([load(new URLSearchParams(window.location.search).get('run')),loadRunner()]);
})();
