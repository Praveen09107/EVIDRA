'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Sidebar from '@/components/layout/Sidebar';
import TopHeader from '@/components/layout/TopHeader';
import StatusBadge from '@/components/shared/StatusBadge';
import ConfidenceBar from '@/components/shared/ConfidenceBar';
import { api } from '@/lib/api';
import { useCaseStore } from '@/lib/store';
import { Clock, Play, MapPin, User, FileText, AlertTriangle, BarChart3, Brain, Shield, BookOpen, Zap, Search, FlaskConical } from 'lucide-react';

const HYPO_COLORS = { HOMICIDE:'#F87171', SUICIDE:'#FBBF24', ACCIDENT:'#34D399', NATURAL:'#60A5FA', UNDETERMINED:'#9CA3AF' };
const TABS = [
  { id:'overview', label:'Overview', icon: BarChart3 },
  { id:'timeline', label:'Timeline', icon: Clock },
  { id:'tod', label:'TOD Analysis', icon: FlaskConical },
  { id:'anomalies', label:'Anomalies', icon: AlertTriangle },
  { id:'hypothesis', label:'Hypothesis', icon: Brain },
  { id:'evidence', label:'Evidence', icon: FileText },
  { id:'report', label:'Report', icon: BookOpen },
  { id:'replay', label:'Replay', icon: Zap },
];

export default function CaseWorkspacePage() {
  const { caseId } = useParams();
  const { activeTab, setActiveTab } = useCaseStore();
  const [caseData, setCaseData] = useState(null);
  const [pipeline, setPipeline] = useState(null);
  const [todResult, setTodResult] = useState(null);
  const [anomalies, setAnomalies] = useState([]);
  const [hypothesis, setHypothesis] = useState(null);
  const [events, setEvents] = useState([]);
  const [hotspots, setHotspots] = useState([]);
  const [replay, setReplay] = useState([]);
  const [files, setFiles] = useState([]);
  const [auditLog, setAuditLog] = useState([]);
  const [report, setReport] = useState(null);

  useEffect(() => {
    api.getCase(caseId).then(setCaseData);
    api.getPipelineStatus(caseId).then(setPipeline);
    api.getTodResult(caseId).then(setTodResult);
    api.getAnomalies(caseId).then(setAnomalies);
    api.getHypothesis(caseId).then(setHypothesis);
    api.getTimelineEvents(caseId).then(setEvents);
    api.getHotspots(caseId).then(setHotspots);
    api.getReplay(caseId).then(setReplay);
    api.getFiles(caseId).then(setFiles);
    api.getAuditLog(caseId).then(setAuditLog);
    api.getReport(caseId).then(setReport);
  }, [caseId]);

  if (!caseData) return <div className="app-layout"><Sidebar /><div className="main-content"><TopHeader title="Loading..." /><div className="scroll-area"><div className="skeleton" style={{height:200,borderRadius:12}}/></div></div></div>;

  return (
    <div className="app-layout">
      <Sidebar />
      <div className="main-content">
        <TopHeader title={caseData.case_number || 'Case'} />
        {/* Case Header */}
        <div style={{padding:'16px 24px',borderBottom:'1px solid var(--border-subtle)',background:'var(--bg-elevated)'}}>
          <div className="flex-between">
            <div>
              <h2 style={{fontSize:'1.25rem',fontWeight:600}}>{caseData.title}</h2>
              <div style={{display:'flex',gap:16,marginTop:6,fontSize:'0.8rem',color:'var(--text-muted)'}}>
                <span style={{display:'flex',alignItems:'center',gap:4}}><MapPin size={13}/>{caseData.location}</span>
                <span style={{display:'flex',alignItems:'center',gap:4}}><User size={13}/>{caseData.assigned_to}</span>
                <span style={{display:'flex',alignItems:'center',gap:4}}><FileText size={13}/>{caseData.evidence_count} files</span>
                <StatusBadge status={caseData.status} size="sm"/>
              </div>
            </div>
            <div style={{display:'flex',gap:8}}>
              {caseData.hypothesis?.slice(0,4).map(h=>(
                <span key={h.key} style={{padding:'4px 12px',borderRadius:9999,fontSize:'0.75rem',fontWeight:600,
                  background:`${HYPO_COLORS[h.key]}12`,color:HYPO_COLORS[h.key],border:`1px solid ${HYPO_COLORS[h.key]}30`}}>
                  {h.key} {Math.round(h.probability*100)}%
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Pipeline Strip */}
        <div className="pipeline-strip">
          {pipeline?.agents?.map((a,i)=>(
            <div key={a.agent_id} style={{display:'flex',alignItems:'center'}}>
              {i>0 && <div className={`pipeline-connector${a.status==='DONE'?' active':''}`}/>}
              <div className="pipeline-node">
                <div className={`pipeline-node-ring ${a.status?.toLowerCase()}`}>
                  {a.status==='DONE'?'✓':a.tier}
                </div>
                <span className="pipeline-node-label">{a.display_name?.split(' ')[0]}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Tab Bar */}
        <div className="tab-bar">
          {TABS.map(t=>(
            <button key={t.id} className={`tab-btn${activeTab===t.id?' active':''}`} onClick={()=>setActiveTab(t.id)}>
              <t.icon size={14} style={{marginRight:6,verticalAlign:'middle'}}/>{t.label}
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="scroll-area">
          {activeTab==='overview' && <OverviewTab caseData={caseData} todResult={todResult} hypothesis={hypothesis} anomalies={anomalies}/>}
          {activeTab==='timeline' && <TimelineTab events={events}/>}
          {activeTab==='tod' && <TodTab todResult={todResult}/>}
          {activeTab==='anomalies' && <AnomaliesTab anomalies={anomalies} hotspots={hotspots}/>}
          {activeTab==='hypothesis' && <HypothesisTab hypothesis={hypothesis}/>}
          {activeTab==='evidence' && <EvidenceTab files={files}/>}
          {activeTab==='report' && <ReportTab report={report}/>}
          {activeTab==='replay' && <ReplayTab steps={replay}/>}
        </div>
      </div>
    </div>
  );
}

/* ─── OVERVIEW TAB ─── */
function OverviewTab({caseData,todResult,hypothesis,anomalies}){
  return(<div className="grid-3 animate-in">
    <div className="card" style={{textAlign:'center',padding:24}}>
      <div style={{fontSize:'0.7rem',color:'var(--text-faint)',textTransform:'uppercase',marginBottom:8}}>Time of Death</div>
      <div style={{fontSize:'2rem',fontWeight:700,fontFamily:'var(--font-mono)',color:'var(--accent-cyan)'}}>
        {todResult?new Date(todResult.pointEstimate).toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit'}):'—'}
      </div>
      <div style={{fontSize:'0.8rem',color:'var(--text-muted)',marginTop:4}}>
        {todResult?.mode?.replace(/_/g,' ')}{todResult?.window95 ? ` • 95% CI: ${Math.round((new Date(todResult.window95.end) - new Date(todResult.window95.start))/3600000)}h` : ''}
      </div>
    </div>
    <div className="card" style={{textAlign:'center',padding:24}}>
      <div style={{fontSize:'0.7rem',color:'var(--text-faint)',textTransform:'uppercase',marginBottom:8}}>Primary Hypothesis</div>
      <div style={{fontSize:'2rem',fontWeight:700,color:HYPO_COLORS[hypothesis?.topHypothesis||'HOMICIDE']}}>
        {hypothesis?.topHypothesis||'—'}
      </div>
      <ConfidenceBar value={hypothesis?.topConfidence||0} label={`${Math.round((hypothesis?.topConfidence||0)*100)}%`}
        color={HYPO_COLORS[hypothesis?.topHypothesis||'HOMICIDE']}/>
    </div>
    <div className="card" style={{textAlign:'center',padding:24}}>
      <div style={{fontSize:'0.7rem',color:'var(--text-faint)',textTransform:'uppercase',marginBottom:8}}>Anomalies Detected</div>
      <div style={{fontSize:'2rem',fontWeight:700,fontFamily:'var(--font-mono)',color:'var(--anomaly-red)'}}>
        {anomalies?.length||0}
      </div>
      <div style={{fontSize:'0.8rem',color:'var(--text-muted)',marginTop:4}}>
        {anomalies?.filter(a=>a.severity==='CRITICAL').length||0} Critical
      </div>
    </div>
  </div>);
}

/* ─── TIMELINE TAB ─── */
function TimelineTab({events}){
  return(<div className="animate-in">
    <h3 style={{fontSize:'1.1rem',fontFamily:'var(--font-display)',marginBottom:16}}>Digital Event Timeline</h3>
    <div className="table-container"><table><thead><tr>
      <th>Time</th><th>Source</th><th>Type</th><th>Description</th><th>Anomaly</th>
    </tr></thead><tbody>
      {events.map(e=>(
        <tr key={e.id} style={e.anomalyScore>0.8?{background:'rgba(249,115,115,0.06)'}:{}}>
          <td style={{fontFamily:'var(--font-mono)',fontSize:'0.8rem',whiteSpace:'nowrap'}}>{new Date(e.timestamp).toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit'})}</td>
          <td><StatusBadge status={e.source} size="sm"/></td>
          <td style={{fontSize:'0.8rem'}}>{e.type.replace(/_/g,' ')}</td>
          <td style={{fontSize:'0.8rem',maxWidth:300,overflow:'hidden',textOverflow:'ellipsis'}}>{e.description}</td>
          <td>{e.anomalyScore!=null?<span style={{fontFamily:'var(--font-mono)',fontSize:'0.8rem',color:e.anomalyScore>0.8?'var(--anomaly-red)':e.anomalyScore>0.5?'var(--warning-amber)':'var(--text-faint)'}}>{e.anomalyScore.toFixed(2)}</span>:'—'}</td>
        </tr>
      ))}
    </tbody></table></div>
  </div>);
}

/* ─── TOD TAB ─── */
function TodTab({todResult}){
  if(!todResult) return <div style={{color:'var(--text-muted)'}}>No TOD data available.</div>;
  const pt=new Date(todResult.pointEstimate);
  return(<div className="animate-in">
    <div className="grid-3" style={{marginBottom:24}}>
      <div className="card" style={{textAlign:'center',padding:24}}>
        <div style={{fontSize:'0.7rem',color:'var(--text-faint)',textTransform:'uppercase',marginBottom:8}}>TOD Estimate</div>
        <div style={{fontSize:'2.5rem',fontWeight:800,fontFamily:'var(--font-mono)',color:'var(--accent-cyan)'}}>
          {pt.toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit'})}
        </div>
        <div style={{fontSize:'0.85rem',color:'var(--text-muted)'}}>{pt.toLocaleDateString('en-IN',{month:'short',day:'numeric',year:'numeric'})}</div>
        <StatusBadge status={todResult.mode} size="sm"/>
      </div>
      <div className="card" style={{padding:24}}>
        <div style={{fontSize:'0.7rem',color:'var(--text-faint)',textTransform:'uppercase',marginBottom:12}}>Postmortem Consistency</div>
        {Object.entries(todResult.consistency).map(([k,v])=>(
          <div key={k} style={{display:'flex',justifyContent:'space-between',alignItems:'center',padding:'6px 0',borderBottom:'1px solid var(--border-subtle)'}}>
            <span style={{fontSize:'0.85rem',textTransform:'capitalize'}}>{k}</span>
            <span style={{fontSize:'0.8rem',color:v==='CONSISTENT'?'var(--success-green)':'var(--anomaly-red)',fontWeight:600}}>
              {v==='CONSISTENT'?'✓':' ⚠'} {v}
            </span>
          </div>
        ))}
      </div>
      <div className="card" style={{padding:24}}>
        <div style={{fontSize:'0.7rem',color:'var(--text-faint)',textTransform:'uppercase',marginBottom:12}}>Component Weights</div>
        {todResult.componentContributions.map(c=>(
          <div key={c.component} style={{marginBottom:10}}>
            <div className="flex-between" style={{marginBottom:4}}>
              <span style={{fontSize:'0.8rem'}}>{c.component.replace(/_/g,' ')}</span>
              <span style={{fontSize:'0.75rem',fontFamily:'var(--font-mono)',color:'var(--text-muted)'}}>{Math.round(c.weight*100)}%</span>
            </div>
            <ConfidenceBar value={c.weight} compact color="var(--accent-indigo)"/>
          </div>
        ))}
      </div>
    </div>
    <div className="card" style={{padding:20}}>
      <div style={{fontSize:'0.7rem',color:'var(--text-faint)',textTransform:'uppercase',marginBottom:12}}>Henssge Inputs</div>
      <div className="grid-4">
        {Object.entries(todResult.henssgeInputs).map(([k,v])=>(
          <div key={k} style={{padding:8}}>
            <div style={{fontSize:'0.7rem',color:'var(--text-faint)',marginBottom:4}}>{k.replace(/([A-Z])/g,' $1')}</div>
            <div style={{fontFamily:'var(--font-mono)',fontSize:'0.9rem'}}>{typeof v==='string'&&v.includes('T')?new Date(v).toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit'}):String(v)}</div>
          </div>
        ))}
      </div>
    </div>
  </div>);
}

/* ─── ANOMALIES TAB ─── */
function AnomaliesTab({anomalies,hotspots}){
  const SEV_BORDER={CRITICAL:'var(--anomaly-red)',HIGH:'#FB923C',MEDIUM:'var(--warning-amber)',LOW:'var(--accent-blue)'};
  return(<div className="animate-in" style={{display:'grid',gridTemplateColumns:'1fr 340px',gap:20}}>
    <div>
      <div className="grid-3" style={{marginBottom:20}}>
        <div className="card" style={{padding:16,textAlign:'center'}}><div style={{fontSize:'1.5rem',fontWeight:700,fontFamily:'var(--font-mono)'}}>{anomalies.length}</div><div style={{fontSize:'0.75rem',color:'var(--text-muted)'}}>Total Anomalies</div></div>
        <div className="card" style={{padding:16,textAlign:'center'}}><div style={{fontSize:'1.5rem',fontWeight:700,fontFamily:'var(--font-mono)',color:'var(--anomaly-red)'}}>{anomalies.filter(a=>a.severity==='CRITICAL').length}</div><div style={{fontSize:'0.75rem',color:'var(--text-muted)'}}>Critical</div></div>
        <div className="card" style={{padding:16,textAlign:'center'}}><div style={{fontSize:'1.5rem',fontWeight:700,fontFamily:'var(--font-mono)',color:'var(--warning-amber)'}}>{anomalies.filter(a=>a.inTodWindow).length}</div><div style={{fontSize:'0.75rem',color:'var(--text-muted)'}}>In TOD Window</div></div>
      </div>
      {anomalies.map(a=>(
        <div key={a.id} className="card" style={{marginBottom:12,borderLeft:`4px solid ${SEV_BORDER[a.severity]}`,padding:16}}>
          <div className="flex-between" style={{marginBottom:8}}>
            <div style={{display:'flex',gap:8}}>
              <StatusBadge status={a.severity} size="sm"/>
              {a.inTodWindow&&<StatusBadge status="IN_ANALYSIS" size="sm"/>}
            </div>
            <span style={{fontFamily:'var(--font-mono)',fontSize:'0.85rem',color:a.score>0.8?'var(--anomaly-red)':'var(--warning-amber)',fontWeight:700}}>{a.score.toFixed(2)}</span>
          </div>
          <h4 style={{fontSize:'0.9rem',fontWeight:600,marginBottom:6}}>{a.title}</h4>
          <p style={{fontSize:'0.8rem',color:'var(--text-muted)',marginBottom:8}}>{a.detail}</p>
          <div style={{display:'flex',gap:6}}>
            {a.sources.map(s=><StatusBadge key={s} status={s} size="sm"/>)}
          </div>
        </div>
      ))}
    </div>
    <div>
      <h4 style={{fontSize:'0.85rem',fontWeight:600,marginBottom:12}}>Hotspot Windows</h4>
      {hotspots.map(h=>(
        <div key={h.id} className="card" style={{marginBottom:12,padding:16,borderLeft:`4px solid ${h.rank===1?'var(--anomaly-red)':'var(--warning-amber)'}`}}>
          <div style={{fontSize:'0.7rem',color:h.rank===1?'var(--anomaly-red)':'var(--warning-amber)',fontWeight:700,textTransform:'uppercase',marginBottom:6}}>
            {h.rank===1?'🔥 PRIMARY':'SECONDARY'} HOTSPOT
          </div>
          <div style={{fontSize:'0.8rem',fontWeight:600,marginBottom:4}}>{h.label}</div>
          <div style={{fontSize:'0.75rem',color:'var(--text-muted)',fontFamily:'var(--font-mono)',marginBottom:8}}>
            {new Date(h.timeWindow.start).toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit'})} — {new Date(h.timeWindow.end).toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit'})}
          </div>
          <div style={{display:'flex',gap:8}}>
            <span style={{fontSize:'0.7rem',color:'var(--text-muted)'}}>In TOD: {h.inTodBand?'✓ YES':'✗ NO'}</span>
            <span style={{fontSize:'0.7rem',color:'var(--text-muted)'}}>Anomalies: {h.anomalyCount}</span>
          </div>
        </div>
      ))}
    </div>
  </div>);
}

/* ─── HYPOTHESIS TAB ─── */
function HypothesisTab({hypothesis}){
  if(!hypothesis)return<div style={{color:'var(--text-muted)'}}>No hypothesis data.</div>;
  return(<div className="animate-in">
    <div className="grid-4" style={{marginBottom:24}}>
      {Object.entries(hypothesis.posteriors).map(([k,v])=>(
        <div key={k} className="card" style={{padding:20,textAlign:'center',borderTop:`3px solid ${HYPO_COLORS[k]}`}}>
          <div style={{fontSize:'0.7rem',color:'var(--text-faint)',textTransform:'uppercase',marginBottom:8}}>{k}</div>
          <div style={{fontSize:'2rem',fontWeight:800,color:HYPO_COLORS[k]}}>{Math.round(v*100)}%</div>
          <ConfidenceBar value={v} color={HYPO_COLORS[k]}/>
        </div>
      ))}
    </div>
    <div className="card" style={{padding:20}}>
      <h4 style={{fontSize:'0.9rem',fontWeight:600,marginBottom:16}}>Bayesian Evidence Signals</h4>
      <div className="table-container"><table><thead><tr>
        <th>Signal</th><th>Source</th><th>Value</th><th>LR</th><th>Direction</th><th>Confidence</th>
      </tr></thead><tbody>
        {hypothesis.signals.map((s,i)=>(
          <tr key={i} style={{background:s.direction==='HOMICIDE'?'rgba(248,113,113,0.04)':s.direction==='SUICIDE'?'rgba(251,191,36,0.04)':'transparent'}}>
            <td style={{fontWeight:500}}>{s.signal.replace(/_/g,' ')}</td>
            <td style={{fontSize:'0.8rem',color:'var(--text-muted)'}}>{s.source}</td>
            <td style={{fontFamily:'var(--font-mono)',fontSize:'0.8rem'}}>{s.value}</td>
            <td style={{fontFamily:'var(--font-mono)',fontSize:'0.8rem'}}>×{s.lr.toFixed(1)}</td>
            <td><span style={{color:HYPO_COLORS[s.direction]||'var(--text-muted)',fontWeight:600,fontSize:'0.8rem'}}>↑ {s.direction}</span></td>
            <td><ConfidenceBar value={s.confidence} label={`${Math.round(s.confidence*100)}%`} compact/></td>
          </tr>
        ))}
      </tbody></table></div>
    </div>
  </div>);
}

/* ─── EVIDENCE TAB ─── */
function EvidenceTab({files}){
  const TYPE_ICON={AUTOPSY_REPORT:'📄',CDR:'📞',FINANCIAL_RECORDS:'💰',DEVICE_DATA:'📱',WITNESS_STATEMENT:'🔍',OTHER:'📎'};
  return(<div className="animate-in">
    <h3 style={{fontSize:'1.1rem',fontFamily:'var(--font-display)',marginBottom:16}}>Evidence Files</h3>
    <div className="table-container"><table><thead><tr>
      <th>File</th><th>Type</th><th>Size</th><th>Status</th><th>Hash</th><th>Uploaded</th>
    </tr></thead><tbody>
      {files.map(f=>(
        <tr key={f.file_id}>
          <td style={{fontWeight:500}}>{TYPE_ICON[f.doc_type]||'📎'} {f.original_name}</td>
          <td><StatusBadge status={f.doc_type} size="sm"/></td>
          <td style={{fontFamily:'var(--font-mono)',fontSize:'0.8rem'}}>{(f.size_bytes/1024).toFixed(0)} KB</td>
          <td><StatusBadge status={f.status} size="sm"/></td>
          <td style={{fontFamily:'var(--font-mono)',fontSize:'0.75rem',color:'var(--text-faint)'}}>{f.checksum}</td>
          <td style={{fontSize:'0.8rem',color:'var(--text-muted)'}}>{new Date(f.uploaded_at).toLocaleString('en-IN',{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'})}</td>
        </tr>
      ))}
    </tbody></table></div>
  </div>);
}

/* ─── REPORT TAB ─── */
function ReportTab({report}){
  if(!report)return<div style={{color:'var(--text-muted)'}}>No report generated yet.</div>;
  return(<div className="animate-in" style={{display:'grid',gridTemplateColumns:'1fr 280px',gap:20}}>
    <div className="card" style={{padding:24,background:'#0c0d11'}}>
      <div style={{textAlign:'center',marginBottom:24}}>
        <div style={{fontSize:'0.65rem',color:'var(--text-faint)',textTransform:'uppercase',letterSpacing:'0.1em',marginBottom:8}}>CONFIDENTIAL</div>
        <h3 style={{fontSize:'1.2rem',fontWeight:700}}>AIVENTRA FORENSIC INTELLIGENCE REPORT</h3>
        <div style={{fontSize:'0.8rem',color:'var(--text-muted)',marginTop:8}}>Generated: {new Date(report.generatedAt).toLocaleString('en-IN')}</div>
        <div style={{display:'flex',justifyContent:'center',gap:8,marginTop:8}}>
          <StatusBadge status={report.chainValid?'COMPLETE':'FAILED'} size="sm"/>
          <span style={{fontSize:'0.7rem',color:'var(--text-faint)'}}>{report.chainValid?'Chain Verified':'Chain Error'}</span>
        </div>
      </div>
      <div style={{marginBottom:20}}>
        <h4 style={{fontSize:'0.9rem',fontWeight:600,marginBottom:8,color:'var(--accent-cyan)'}}>Executive Summary</h4>
        <p style={{fontSize:'0.85rem',color:'var(--text-secondary)',lineHeight:1.7}}>{report.executiveSummary}</p>
      </div>
      <div>
        <h4 style={{fontSize:'0.85rem',fontWeight:600,marginBottom:12}}>Report Sections</h4>
        {report.sections.map((s,i)=>(
          <div key={i} style={{padding:'10px 0',borderBottom:'1px solid var(--border-subtle)',display:'flex',alignItems:'center',gap:8}}>
            <span style={{color:'var(--success-green)',fontSize:'0.8rem'}}>✓</span>
            <span style={{fontSize:'0.85rem'}}>{i+1}. {s}</span>
          </div>
        ))}
      </div>
    </div>
    <div>
      <div className="card" style={{padding:16,marginBottom:12}}>
        <h4 style={{fontSize:'0.85rem',fontWeight:600,marginBottom:12}}>Export Report</h4>
        <button className="btn btn-primary" style={{width:'100%',marginBottom:8}}>Download PDF ↓</button>
        <button className="btn btn-secondary" style={{width:'100%'}}>Export JSON</button>
      </div>
    </div>
  </div>);
}

/* ─── REPLAY TAB ─── */
function ReplayTab({steps}){
  return(<div className="animate-in">
    <div className="flex-between" style={{marginBottom:16}}>
      <h3 style={{fontSize:'1.1rem',fontFamily:'var(--font-display)'}}>Reasoning Replay Chain</h3>
      <span style={{fontSize:'0.75rem',color:'var(--success-green)'}}>✓ {steps.length} steps verified</span>
    </div>
    <div className="table-container"><table><thead><tr>
      <th>#</th><th>Agent</th><th>Trigger</th><th>Input</th><th>Conclusion</th><th>Conf.</th><th>Time</th>
    </tr></thead><tbody>
      {steps.map(s=>(
        <tr key={s.seq} style={{background:s.confidence<0.8?'rgba(251,191,36,0.04)':'transparent'}}>
          <td style={{fontFamily:'var(--font-mono)',fontSize:'0.8rem',color:'var(--text-faint)'}}>{s.seq}</td>
          <td style={{fontWeight:500,fontSize:'0.8rem'}}>{s.agent_id.replace(/_/g,' ')}</td>
          <td><StatusBadge status={s.trigger} size="sm"/></td>
          <td style={{fontSize:'0.8rem',color:'var(--text-muted)',maxWidth:180,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{s.input}</td>
          <td style={{fontSize:'0.8rem',maxWidth:220,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{s.conclusion}</td>
          <td><ConfidenceBar value={s.confidence} label={`${Math.round(s.confidence*100)}%`} compact/></td>
          <td style={{fontFamily:'var(--font-mono)',fontSize:'0.75rem',color:'var(--text-faint)'}}>{(s.duration_ms/1000).toFixed(1)}s</td>
        </tr>
      ))}
    </tbody></table></div>
  </div>);
}
